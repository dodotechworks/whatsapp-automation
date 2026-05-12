from sqlalchemy import Column, Integer, String
from database import Base

class Service(Base):
    __tablename__ = "services"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String)
    description = Column(String)
    pdf_link = Column(String)

class ChatbotSetting(Base):
    __tablename__ = "chatbot_settings"

    id = Column(Integer, primary_key=True, index=True)

    key = Column(String, unique=True)

    value = Column(String)

class UserSession(Base):
    __tablename__ = "user_sessions"

    id = Column(Integer, primary_key=True, index=True)
    phone = Column(String, unique=True, index=True)
    current_step = Column(String)
    selected_service_id = Column(Integer, nullable=True)

    temp_name = Column(String, nullable=True)
    temp_email = Column(String, nullable=True)
    temp_mobile = Column(String, nullable=True)
    temp_datetime = Column(String, nullable=True)


class Lead(Base):
    __tablename__ = "leads"

    id = Column(Integer, primary_key=True, index=True)

    name = Column(String, nullable=True)
    email = Column(String, nullable=True)
    mobile = Column(String, nullable=True)
    whatsapp_number = Column(String)

    service_title = Column(String, nullable=True)
    preferred_datetime = Column(String, nullable=True)

    status = Column(String)  # converted / dropped