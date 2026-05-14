from fastapi import FastAPI, Depends
import re
from sqlalchemy.orm import Session
from fastapi.middleware.cors import CORSMiddleware
from database import engine, get_db
from models import Base, Service, ChatbotSetting, UserSession, Lead
from schemas import (
    ServiceCreate,
    ServiceUpdate,
    ChatbotSettingCreate
)
from services.whatsapp import (
    send_whatsapp_message,
    send_button_message,
    send_service_list_message
)

from fastapi import Request
from services.google_sheets import (
    append_lead_to_sheet,
    get_all_leads_from_sheet,
    get_leads_by_status
)
import os
from dotenv import load_dotenv
load_dotenv()

app = FastAPI()

ACCESS_TOKEN = os.getenv(
    "WHATSAPP_ACCESS_TOKEN"
)

PHONE_NUMBER_ID = os.getenv(
    "PHONE_NUMBER_ID"
)

VERIFY_TOKEN = os.getenv(
    "VERIFY_TOKEN"
)

DOCTOR_WHATSAPP_NUMBER = os.getenv(
    "DOCTOR_WHATSAPP_NUMBER"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

Base.metadata.create_all(bind=engine)

@app.get("/")
def home():
    return {"message": "Backend Running"}

@app.get("/send-test")
def send_test():

    response = send_whatsapp_message(
        "918122016648",
        "Hello from FastAPI 🚀"
    )

    return response

@app.get("/check-env")
def check_env():
    return {
        "phone_number_id": PHONE_NUMBER_ID,
        "token_loaded": ACCESS_TOKEN is not None
    }

@app.get("/reset-session/{phone}")
def reset_session(phone: str, db: Session = Depends(get_db)):
    session = db.query(UserSession).filter(
        UserSession.phone == phone
    ).first()

    if session:
        db.delete(session)
        db.commit()
        return {"message": "Session reset"}

    return {"message": "No session found"}

# CREATE SERVICE
@app.post("/services")
def create_service(service: ServiceCreate, db: Session = Depends(get_db)):
    
    new_service = Service(
        title=service.title,
        description=service.description,
        pdf_link=service.pdf_link
    )

    db.add(new_service)
    db.commit()
    db.refresh(new_service)

    

    return {
        "message": "Service Created",
        "data": new_service
    }


# GET ALL SERVICES
@app.get("/services")
def get_services(db: Session = Depends(get_db)):

    services = db.query(Service).all()

    return services

# Update Services
@app.put("/services/{service_id}")
def update_service(
    service_id: int,
    updated_service: ServiceUpdate,
    db: Session = Depends(get_db)
):

    service = db.query(Service).filter(Service.id == service_id).first()

    if not service:
        return {"message": "Service Not Found"}

    service.title = updated_service.title
    service.description = updated_service.description
    service.pdf_link = updated_service.pdf_link

    db.commit()
    db.refresh(service)

    return {
        "message": "Service Updated",
        "data": service
    }

@app.delete("/services/{service_id}")
def delete_service(
    service_id: int,
    db: Session = Depends(get_db)
):

    service = db.query(Service).filter(Service.id == service_id).first()

    if not service:
        return {"message": "Service Not Found"}

    db.delete(service)
    db.commit()

    return {"message": "Service Deleted"}

@app.post("/chatbot-settings")
def save_chatbot_setting(
    setting: ChatbotSettingCreate,
    db: Session = Depends(get_db)
):

    existing_setting = db.query(ChatbotSetting).filter(
        ChatbotSetting.key == setting.key
    ).first()

    if existing_setting:

        existing_setting.value = setting.value

        db.commit()

        db.refresh(existing_setting)

        return {
            "message": "Setting Updated",
            "data": existing_setting
        }

    new_setting = ChatbotSetting(
        key=setting.key,
        value=setting.value
    )

    db.add(new_setting)

    db.commit()

    db.refresh(new_setting)

    return {
        "message": "Setting Saved",
        "data": new_setting
    }


@app.get("/chatbot-settings")
def get_chatbot_settings(
    db: Session = Depends(get_db)
):

    settings = db.query(ChatbotSetting).all()

    return settings

#Leads API
@app.get("/leads")
def get_leads():
    return get_all_leads_from_sheet()


@app.get("/leads/converted")
def get_converted_leads():
    return get_leads_by_status("converted")


@app.get("/leads/dropped")
def get_dropped_leads():
    return get_leads_by_status("dropped")

#Helper Function
def get_setting(db, key, default_value=""):
    setting = db.query(ChatbotSetting).filter(
        ChatbotSetting.key == key
    ).first()

    if setting:
        return setting.value

    return default_value

@app.get("/webhook")
async def verify_webhook(request: Request):

    hub_mode = request.query_params.get("hub.mode")

    hub_verify_token = request.query_params.get(
        "hub.verify_token"
    )

    hub_challenge = request.query_params.get(
        "hub.challenge"
    )

    if (
        hub_mode == "subscribe"
        and hub_verify_token == VERIFY_TOKEN
    ):

        return int(hub_challenge)

    return {
        "message": "Webhook verification failed"
    }


#Webhook
@app.post("/webhook")
async def whatsapp_webhook(
    request: Request,
    db: Session = Depends(get_db)
):

    body = await request.json()

    print("WHATSAPP WEBHOOK DATA:", body, flush=True)

    try:
        value = body["entry"][0]["changes"][0]["value"]

        if "messages" not in value:
            return {"status": "no message"}

        message_data = value["messages"][0]

        phone = message_data["from"]
        message_type = message_data["type"]

        user_message = ""

        if message_type == "text":
            user_message = message_data["text"]["body"].strip()

        elif message_type == "interactive":
            interactive_data = message_data["interactive"]

            if interactive_data["type"] == "list_reply":
                user_message = interactive_data["list_reply"]["id"]

            elif interactive_data["type"] == "button_reply":
                user_message = interactive_data["button_reply"]["id"]

        else:
            return {"status": "unsupported message type"}

        print("USER PHONE:", phone, flush=True)
        print("USER MESSAGE:", user_message, flush=True)

        session = db.query(UserSession).filter(
            UserSession.phone == phone
        ).first()

        if not session:
            session = UserSession(
                phone=phone,
                current_step="select_service"
            )

            db.add(session)
            db.commit()
            db.refresh(session)

        services = db.query(Service).all()

        # STEP 1 - SERVICE SELECTION
        if session.current_step == "select_service":

            welcome_message = get_setting(
                db,
                "welcome_message",
                "Welcome! Please select a service:"
            )

            # FIRST TIME → SHOW LIST
            if user_message == "" or user_message.lower() == "hi":

                response = send_service_list_message(
                    phone,
                    welcome_message,
                    services
                )

                print("SEND RESPONSE:", response, flush=True)

            # USER SELECTED SERVICE
            elif user_message.startswith("service_"):

                service_id = int(
                    user_message.replace("service_", "")
                )

                selected_service = db.query(Service).filter(
                    Service.id == service_id
                ).first()

                if not selected_service:

                    response = send_whatsapp_message(
                        phone,
                        "Invalid service selection."
                    )

                    print("SEND RESPONSE:", response, flush=True)

                else:

                    session.selected_service_id = (
                        selected_service.id
                    )

                    session.current_step = "booking_choice"

                    db.commit()

                    booking_message = get_setting(
                        db,
                        "booking_message",
                        "Would you like to book now?"
                    )

                    reply_message = (
                        f"{selected_service.title}\n\n"
                        f"{selected_service.description}\n\n"
                        f"{selected_service.pdf_link}\n\n"
                        f"{booking_message}"
                    )

                    response = send_button_message(
                        phone,
                        reply_message,
                        [
                            {
                                "id": "book_now",
                                "title": "Book Now"
                            },
                            {
                                "id": "later",
                                "title": "Later"
                            }
                        ]
                    )

                    print("SEND RESPONSE:", response, flush=True)

            else:

                response = send_service_list_message(
                    phone,
                    welcome_message,
                    services
                )

                print("SEND RESPONSE:", response, flush=True)

        # STEP 2 - BOOK OR LATER
        elif session.current_step == "booking_choice":

            if user_message == "book_now":

                session.current_step = "ask_name"
                db.commit()

                reply_message = "Please enter your name."

            elif user_message == "later":

                selected_service = db.query(Service).filter(
                    Service.id == session.selected_service_id
                ).first()

                drop_lead = Lead(
                    whatsapp_number=phone,
                    service_title=selected_service.title if selected_service else None,
                    status="dropped"
                )

                append_lead_to_sheet(drop_lead)

                db.delete(session)
                db.commit()
                
                reply_message = "No problem. We will contact you later."

            else:
                reply_message = "Please select Book Now or Later from the buttons."

            response = send_whatsapp_message(phone, reply_message)
            print("SEND RESPONSE:", response, flush=True)


        # STEP 3 - ASK NAME
        elif session.current_step == "ask_name":

            if not re.match(r"^[A-Za-z ]{2,}$", user_message):
                reply_message = "Please enter a valid name. Example: Divakar"
            else:
                session.temp_name = user_message
                session.current_step = "ask_email"
                db.commit()

                reply_message = "Please enter your email address."

            response = send_whatsapp_message(phone, reply_message)
            print("SEND RESPONSE:", response, flush=True)


        # STEP 4 - ASK EMAIL
        elif session.current_step == "ask_email":

            if not re.match(r"^[\w\.-]+@[\w\.-]+\.\w+$", user_message):
                reply_message = "Please enter a valid email. Example: name@gmail.com"
            else:
                session.temp_email = user_message
                session.current_step = "ask_mobile"
                db.commit()

                reply_message = "Please enter your 10-digit mobile number."

            response = send_whatsapp_message(phone, reply_message)
            print("SEND RESPONSE:", response, flush=True)


        # STEP 5 - ASK MOBILE
        elif session.current_step == "ask_mobile":

            if not re.match(r"^[0-9]{10}$", user_message):
                reply_message = "Please enter a valid 10-digit mobile number."
            else:
                session.temp_mobile = user_message
                session.current_step = "ask_datetime"
                db.commit()

                datetime_message = get_setting(
                    db,
                    "datetime_message",
                    "Please enter preferred date and time.\nFormat: DD-MM-YYYY HH:MM AM/PM\nAvailable: Mon-Fri 9AM to 9PM"
                )

                reply_message = datetime_message

            response = send_whatsapp_message(phone, reply_message)
            print("SEND RESPONSE:", response, flush=True)


        # STEP 6 - ASK DATE TIME
        elif session.current_step == "ask_datetime":

            datetime_pattern = r"^\d{2}-\d{2}-\d{4} \d{2}:\d{2} (AM|PM|am|pm)$"

            if not re.match(datetime_pattern, user_message):
                reply_message = (
                    "Please enter date and time in this format:\n"
                    "10-05-2026 05:30 PM"
                )
            else:
                selected_service = db.query(Service).filter(
                    Service.id == session.selected_service_id
                ).first()

                new_lead = Lead(
                    name=session.temp_name,
                    email=session.temp_email,
                    mobile=session.temp_mobile,
                    whatsapp_number=phone,
                    service_title=selected_service.title if selected_service else None,
                    preferred_datetime=user_message,
                    status="converted"
                )

                append_lead_to_sheet(new_lead)

                db.delete(session)
                db.commit()
                doctor_message = (
                    f"📢 New Booking Lead\n\n"
                    f"Name: {new_lead.name}\n"
                    f"Email: {new_lead.email}\n"
                    f"Mobile: {new_lead.mobile}\n"
                    f"WhatsApp: {new_lead.whatsapp_number}\n"
                    f"Service: {new_lead.service_title}\n"
                    f"Preferred Time: {new_lead.preferred_datetime}"
                )

                doctor_response = send_whatsapp_message(
                    DOCTOR_WHATSAPP_NUMBER,
                    doctor_message
                )

                print(
                    "DOCTOR NOTIFICATION:",
                    doctor_response,
                    flush=True
                )

                thankyou_message = get_setting(
                    db,
                    "thankyou_message",
                    "Thanks for booking. Our team will contact you shortly."
                )

                reply_message = thankyou_message

            response = send_whatsapp_message(phone, reply_message)
            print("SEND RESPONSE:", response, flush=True)

    except Exception as e:
        print("Webhook error:", e, flush=True)

    return {"status": "received"}   