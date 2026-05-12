from pydantic import BaseModel

class ServiceCreate(BaseModel):
    title: str
    description: str
    pdf_link: str

class ServiceUpdate(BaseModel):
    title: str
    description: str
    pdf_link: str

class ChatbotSettingCreate(BaseModel):
    key: str
    value: str