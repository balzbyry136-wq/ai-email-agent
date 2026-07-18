"""
التطبيق الرئيسي - نقطة الدخول لتشغيل السيرفر
تشغيل: uvicorn main:app --reload
"""
import os
from dotenv import load_dotenv
load_dotenv()

from fastapi import FastAPI, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session

import models
import schemas
import gmail_service
import ai_service
from database import engine, get_db, SessionLocal

models.Base.metadata.create_all(bind=engine)

app = FastAPI(title="AI Email Agent")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # للتطوير المحلي فقط - قيّدها في الإنتاج
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------------------------------------------------------------------------
# مصادقة Google (OAuth2)
# ---------------------------------------------------------------------------

@app.get("/auth/login")
def login():
    """يرجع رابط تسجيل الدخول عبر Google - افتحه بالمتصفح"""
    auth_url, _ = gmail_service.get_authorization_url()
    return {"auth_url": auth_url}


@app.get("/auth/callback")
def auth_callback(code: str, db: Session = Depends(get_db)):
    """Google يرجع هنا بعد موافقة المستخدم - يخزن الـ tokens"""
    creds = gmail_service.exchange_code_for_tokens(code)

    # نجيب إيميل المستخدم من Gmail عشان نحفظه كمعرّف
    service = gmail_service.get_gmail_service(creds.token, creds.refresh_token)
    profile = service.users().getProfile(userId="me").execute()
    user_email = profile["emailAddress"]

    user = db.query(models.User).filter(models.User.email == user_email).first()
    if not user:
        user = models.User(email=user_email)
        db.add(user)

    user.google_token = creds.token
    user.google_refresh_token = creds.refresh_token
    db.commit()

    return RedirectResponse(url="http://localhost:5500/index.html?connected=1")


# ---------------------------------------------------------------------------
# مزامنة ومعالجة الإيميلات
# ---------------------------------------------------------------------------

@app.post("/emails/sync")
def sync_emails(user_email: str, db: Session = Depends(get_db)):
    """يجلب آخر الإيميلات من Gmail، يحللها بالـ AI، ويخزنها"""
    user = db.query(models.User).filter(models.User.email == user_email).first()
    if not user:
        raise HTTPException(404, "المستخدم غير موجود - سجّل الدخول أولاً عبر /auth/login")

    service = gmail_service.get_gmail_service(user.google_token, user.google_refresh_token)
    raw_emails = gmail_service.fetch_recent_emails(service, max_results=10)

    new_count = 0
    for raw in raw_emails:
        existing = db.query(models.Email).filter(
            models.Email.gmail_id == raw["gmail_id"]
        ).first()
        if existing:
            continue

        analysis = ai_service.analyze_email(raw["subject"], raw["sender"], raw["body"])

        email_record = models.Email(
            gmail_id=raw["gmail_id"],
            owner_id=user.id,
            sender=raw["sender"],
            subject=raw["subject"],
            snippet=raw["snippet"],
            body=raw["body"],
            category=analysis.get("category", "normal"),
            priority=analysis.get("priority", "medium"),
            summary=analysis.get("summary"),
            ai_processed=True,
        )
        db.add(email_record)
        db.flush()  # عشان نحصل على email_record.id

        for item_desc in analysis.get("action_items", []):
            db.add(models.ActionItem(email_id=email_record.id, description=item_desc))

        if analysis.get("suggested_reply"):
            db.add(models.DraftReply(
                email_id=email_record.id,
                content=analysis["suggested_reply"],
                status="pending_review",
            ))

        db.add(models.AuditLog(
            action="email_classified",
            details=f"Email {raw['gmail_id']} classified as {analysis.get('category')}",
        ))
        new_count += 1

    db.commit()
    return {"synced": len(raw_emails), "new": new_count}


@app.get("/emails", response_model=list[schemas.EmailOut])
def list_emails(user_email: str, db: Session = Depends(get_db)):
    """يرجع كل الإيميلات المعالجة لعرضها بالـ Dashboard"""
    user = db.query(models.User).filter(models.User.email == user_email).first()
    if not user:
        raise HTTPException(404, "المستخدم غير موجود")
    return db.query(models.Email).filter(
        models.Email.owner_id == user.id
    ).order_by(models.Email.received_at.desc()).all()


# ---------------------------------------------------------------------------
# الموافقة على الردود وإرسالها (Human-in-the-loop)
# ---------------------------------------------------------------------------

@app.post("/replies/approve")
def approve_reply(req: schemas.ApproveReplyRequest, user_email: str, db: Session = Depends(get_db)):
    """المستخدم يوافق (أو يعدّل) على رد مقترح فيُرسل فعلياً"""
    draft = db.query(models.DraftReply).filter(models.DraftReply.id == req.draft_id).first()
    if not draft:
        raise HTTPException(404, "المسودة غير موجودة")

    user = db.query(models.User).filter(models.User.email == user_email).first()
    email_record = draft.email

    final_content = req.edited_content or draft.content

    service = gmail_service.get_gmail_service(user.google_token, user.google_refresh_token)
    sender_address = email_record.sender

    gmail_service.send_reply(
        service,
        to=sender_address,
        subject=email_record.subject,
        body=final_content,
    )

    draft.status = "sent"
    draft.content = final_content
    db.add(models.AuditLog(
        action="reply_sent",
        details=f"Reply sent for email {email_record.gmail_id}",
    ))
    db.commit()
    return {"status": "sent"}


@app.post("/replies/reject")
def reject_reply(draft_id: int, db: Session = Depends(get_db)):
    """رفض مسودة رد مقترحة"""
    draft = db.query(models.DraftReply).filter(models.DraftReply.id == draft_id).first()
    if not draft:
        raise HTTPException(404, "المسودة غير موجودة")
    draft.status = "rejected"
    db.commit()
    return {"status": "rejected"}


@app.get("/health")
def health():
    return {"status": "ok"}
