"""
Schemas تُستخدم للتحقق من صحة البيانات وتحديد شكل استجابات الـ API
"""
from pydantic import BaseModel
from datetime import datetime
from typing import Optional


class ActionItemOut(BaseModel):
    id: int
    description: str
    due_hint: Optional[str] = None
    completed: bool

    class Config:
        from_attributes = True


class DraftReplyOut(BaseModel):
    id: int
    content: str
    status: str

    class Config:
        from_attributes = True


class EmailOut(BaseModel):
    id: int
    sender: str
    subject: str
    snippet: str
    category: str
    priority: str
    summary: Optional[str] = None
    ai_processed: bool
    received_at: datetime
    action_items: list[ActionItemOut] = []
    draft_reply: Optional[DraftReplyOut] = None

    class Config:
        from_attributes = True


class ApproveReplyRequest(BaseModel):
    draft_id: int
    edited_content: Optional[str] = None  # لو المستخدم عدّل الرد قبل الموافقة
