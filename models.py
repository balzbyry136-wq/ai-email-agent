"""
نماذج الجداول في قاعدة البيانات
"""
from sqlalchemy import Column, Integer, String, Text, DateTime, Boolean, ForeignKey
from sqlalchemy.orm import relationship
from datetime import datetime
from database import Base


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True)
    # تخزين tokens بشكل مشفر في تطبيق إنتاجي حقيقي - هنا مبسط للتطوير المحلي
    google_token = Column(Text, nullable=True)
    google_refresh_token = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    emails = relationship("Email", back_populates="owner")


class Email(Base):
    __tablename__ = "emails"

    id = Column(Integer, primary_key=True, index=True)
    gmail_id = Column(String, unique=True, index=True)
    owner_id = Column(Integer, ForeignKey("users.id"))

    sender = Column(String)
    subject = Column(String)
    snippet = Column(Text)
    body = Column(Text)
    received_at = Column(DateTime, default=datetime.utcnow)

    # نتائج تحليل الذكاء الاصطناعي
    category = Column(String, default="uncategorized")  # urgent/normal/spam/needs_reply
    priority = Column(String, default="normal")  # high/medium/low
    summary = Column(Text, nullable=True)
    ai_processed = Column(Boolean, default=False)

    owner = relationship("User", back_populates="emails")
    action_items = relationship("ActionItem", back_populates="email")
    draft_reply = relationship("DraftReply", back_populates="email", uselist=False)


class ActionItem(Base):
    __tablename__ = "action_items"

    id = Column(Integer, primary_key=True, index=True)
    email_id = Column(Integer, ForeignKey("emails.id"))
    description = Column(Text)
    due_hint = Column(String, nullable=True)  # نص وصفي مثل "الثلاثاء القادم"
    completed = Column(Boolean, default=False)

    email = relationship("Email", back_populates="action_items")


class DraftReply(Base):
    __tablename__ = "draft_replies"

    id = Column(Integer, primary_key=True, index=True)
    email_id = Column(Integer, ForeignKey("emails.id"))
    content = Column(Text)
    status = Column(String, default="pending_review")  # pending_review/approved/rejected/sent
    created_at = Column(DateTime, default=datetime.utcnow)

    email = relationship("Email", back_populates="draft_reply")


class AuditLog(Base):
    __tablename__ = "audit_log"

    id = Column(Integer, primary_key=True, index=True)
    action = Column(String)  # مثال: "reply_sent", "email_classified"
    details = Column(Text)
    timestamp = Column(DateTime, default=datetime.utcnow)
