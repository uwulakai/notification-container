from pydantic import BaseModel
from typing import Optional


class MessageSchema(BaseModel):
    chat_id: int
    text: Optional[str] = None
    chat_user_name: Optional[str] = None
