import os
from dotenv import load_dotenv
import gspread
from google.oauth2.service_account import Credentials

load_dotenv()

GOOGLE_SHEET_ID = os.getenv("GOOGLE_SHEET_ID")

SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets"
]

credentials = Credentials.from_service_account_file(
    "google-service-account.json",
    scopes=SCOPES
)

client = gspread.authorize(credentials)

sheet = client.open_by_key(GOOGLE_SHEET_ID).sheet1


def append_lead_to_sheet(lead):
    row = [
        lead.name or "",
        lead.email or "",
        lead.mobile or "",
        lead.whatsapp_number or "",
        lead.service_title or "",
        lead.preferred_datetime or "",
        lead.status or ""
    ]

    sheet.append_row(row)

def get_all_leads_from_sheet():
    records = sheet.get_all_records()

    return records


def get_leads_by_status(status):
    records = sheet.get_all_records()

    filtered = []

    for record in records:
        if str(record.get("Status", "")).lower() == status:
            filtered.append(record)

    return filtered