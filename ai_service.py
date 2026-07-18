"""
خدمة تحليل الإيميلات باستخدام Claude API:
- تصنيف الإيميل (عاجل/عادي/سبام/يحتاج رد)
- تلخيص المحتوى
- استخراج المهام (Action Items)
- توليد مسودة رد مقترحة
"""
import os
import json
from anthropic import Anthropic

client = Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))

MODEL = "claude-sonnet-5"  # يمكنك تغييره لـ claude-haiku-4-5-20251001 لتكلفة أقل وسرعة أعلى

ANALYSIS_SYSTEM_PROMPT = """أنت مساعد يحلل رسائل البريد الإلكتروني. مهمتك إرجاع تحليل بصيغة JSON فقط، بدون أي نص إضافي أو علامات markdown.

الصيغة المطلوبة بالضبط:
{
  "category": "urgent" | "normal" | "spam" | "needs_reply" | "notification_only",
  "priority": "high" | "medium" | "low",
  "summary": "ملخص من جملة أو جملتين للإيميل",
  "action_items": ["وصف مهمة 1", "وصف مهمة 2"],
  "suggested_reply": "نص رد مقترح مناسب ومحترف، أو null إذا لم يكن الرد مطلوباً"
}

لا تكتب أي شيء خارج كائن الـ JSON."""


def analyze_email(subject: str, sender: str, body: str) -> dict:
    """يرسل الإيميل لـ Claude ويرجع تحليل منظم (JSON)"""
    user_content = f"المرسل: {sender}\nالموضوع: {subject}\n\nالمحتوى:\n{body[:4000]}"

    response = client.messages.create(
        model=MODEL,
        max_tokens=1024,
        system=ANALYSIS_SYSTEM_PROMPT,
        messages=[{"role": "user", "content": user_content}],
    )

    raw_text = "".join(
        block.text for block in response.content if block.type == "text"
    )

    # تنظيف احتياطي لو رجع بأسوار markdown رغم التعليمات
    cleaned = raw_text.strip().removeprefix("```json").removeprefix("```").removesuffix("```").strip()

    try:
        result = json.loads(cleaned)
    except json.JSONDecodeError:
        # fallback آمن لو فشل التحليل
        result = {
            "category": "normal",
            "priority": "medium",
            "summary": "تعذر تحليل الإيميل تلقائياً.",
            "action_items": [],
            "suggested_reply": None,
        }
    return result
