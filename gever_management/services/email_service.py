"""
Email notification service.
Priority: Resend API (no password, supports business domains) → Gmail SMTP fallback.

Setup (choose ONE):
  Option A – Resend (recommended):
    1. Sign up free at https://resend.com
    2. Add RESEND_API_KEY to Railway env vars
    3. Optionally verify your domain to send from @primels.co.il
    4. Set SENDER_EMAIL to your business email
    5. Set CHAIRMAN_EMAIL to where you want to receive alerts

  Option B – Gmail:
    1. Go to myaccount.google.com/apppasswords
    2. Create app password (NOT your regular password)
    3. Set GMAIL_USER + GMAIL_APP_PASSWORD in Railway
"""
import logging
import smtplib
import ssl
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from config import settings

logger = logging.getLogger(__name__)
PORTAL_URL = "https://app.primels.co.il"


# ── HTML Template ─────────────────────────────────────────────────────────────

def _html(title: str, rows: list[tuple], cta: str = "פתח דשבורד") -> str:
    rows_html = "".join(
        f'<tr><td style="padding:7px 0;color:#94a3b8;font-size:0.87rem;width:140px;">{k}</td>'
        f'<td style="padding:7px 0;color:#e2e8f0;font-size:0.87rem;">{v}</td></tr>'
        for k, v in rows
    )
    return f"""<!DOCTYPE html>
<html dir="rtl" lang="he">
<head><meta charset="UTF-8"></head>
<body style="margin:0;padding:0;background:#0a0f1e;font-family:Arial,sans-serif;direction:rtl;">
<div style="max-width:580px;margin:0 auto;padding:24px 16px;">
  <div style="background:linear-gradient(135deg,#1e3a8a,#5b21b6);border-radius:14px;padding:22px;margin-bottom:14px;text-align:center;">
    <div style="font-size:2rem;margin-bottom:6px;">🏢</div>
    <div style="color:white;font-size:1.1rem;font-weight:700;">גבר יזמות ייעוץ עסקי והשקעות</div>
    <div style="color:rgba(255,255,255,0.65);font-size:0.78rem;margin-top:3px;">AI Management Platform</div>
  </div>
  <div style="background:#111827;border:1px solid #1e2d45;border-radius:14px;padding:22px;margin-bottom:14px;">
    <h2 style="color:#e2e8f0;font-size:1.05rem;margin:0 0 14px;">{title}</h2>
    <table style="width:100%;border-collapse:collapse;">{rows_html}</table>
  </div>
  <div style="text-align:center;margin-bottom:12px;">
    <a href="{PORTAL_URL}" style="display:inline-block;background:linear-gradient(135deg,#1e40af,#6d28d9);
       color:white;text-decoration:none;padding:11px 28px;border-radius:8px;font-weight:700;font-size:0.9rem;">{cta}</a>
  </div>
  <div style="text-align:center;color:#475569;font-size:0.72rem;">גבר יזמות • AI Management Platform</div>
</div></body></html>"""


# ── Send Engines ──────────────────────────────────────────────────────────────

def _send_resend(subject: str, html: str, to: str) -> bool:
    api_key = getattr(settings, "resend_api_key", "")
    if not api_key:
        return False
    try:
        import urllib.request, urllib.error, json as _json
        payload = _json.dumps({
            "from": getattr(settings, "sender_email", "notifications@resend.dev"),
            "to": [to],
            "subject": subject,
            "html": html,
        }).encode()
        req = urllib.request.Request(
            "https://api.resend.com/emails",
            data=payload,
            headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=15) as r:
            result = _json.loads(r.read())
            logger.info("[EMAIL/Resend] Sent id=%s → %s", result.get("id"), to)
            return True
    except Exception as e:
        logger.error("[EMAIL/Resend] Failed: %s", e)
        return False


def _send_gmail(subject: str, html: str, to: str) -> bool:
    user = getattr(settings, "gmail_user", "")
    pw = getattr(settings, "gmail_app_password", "")
    if not user or not pw:
        return False
    try:
        msg = MIMEMultipart("alternative")
        msg["Subject"] = subject
        msg["From"] = f"גבר ניהול <{user}>"
        msg["To"] = to
        msg.attach(MIMEText(html, "html", "utf-8"))
        ctx = ssl.create_default_context()
        with smtplib.SMTP_SSL("smtp.gmail.com", 465, context=ctx) as s:
            s.login(user, pw)
            s.sendmail(user, to, msg.as_string())
        logger.info("[EMAIL/Gmail] Sent: %s → %s", subject, to)
        return True
    except Exception as e:
        logger.error("[EMAIL/Gmail] Failed: %s", e)
        return False


def _send(subject: str, html: str) -> bool:
    to = getattr(settings, "chairman_email", "farukjaber34@gmail.com")
    if _send_resend(subject, html, to):
        return True
    if _send_gmail(subject, html, to):
        return True
    logger.info("[EMAIL] Not configured – skipping: %s", subject)
    return False


# ── Notification Helpers ──────────────────────────────────────────────────────

def notify_task_completed(task_title: str, departments: list, task_id: str = ""):
    _send(
        subject=f"✅ משימה הושלמה – {task_title}",
        html=_html(
            "כל המחלקות השלימו ✓ – ממתין לאישורך",
            [("משימה", task_title),
             ("מחלקות שעבדו", " • ".join(departments)),
             ("סטטוס", "ממתין לאישור יו\"ר")],
            cta="לאישור בדשבורד",
        ),
    )


def notify_deliverable_ready(task_title: str, department: str, employee_name: str):
    _send(
        subject=f"📋 תוצר ממתין לאישורך – {department}",
        html=_html(
            "תוצר חדש ממחלקה – ממתין לאישורך",
            [("משימה", task_title),
             ("מחלקה", department),
             ("הוכן על ידי", employee_name),
             ("פעולה", "עיין ואשר/דחה בדשבורד")],
            cta="לאישור בדשבורד",
        ),
    )


def notify_published(task_title: str, platform: str, post_id: str = ""):
    _send(
        subject=f"🚀 פורסם בהצלחה – {platform}",
        html=_html(
            f"פרסום בוצע בהצלחה ב-{platform}",
            [("משימה", task_title),
             ("פלטפורמה", platform),
             ("מזהה פוסט", post_id or "—"),
             ("סטטוס", "✅ פורסם")],
        ),
    )


def notify_publish_ready(task_title: str, platform: str):
    _send(
        subject=f"📦 תוכן מוכן להורדה – {platform}",
        html=_html(
            "אין חיבור API – התוכן מוכן להורדה ידנית",
            [("משימה", task_title),
             ("פלטפורמה", platform),
             ("הוראה", "היכנס לדשבורד → תוצרים → ⬇️ הורד → פרסם ידנית")],
            cta="הורד תוכן",
        ),
    )


def notify_employee_change(action: str, employee_name: str, details: str = ""):
    _send(
        subject=f"👤 שינוי עובד – {action} – {employee_name}",
        html=_html(
            f"שינוי כוח אדם: {action}",
            [("עובד", employee_name),
             ("פעולה", action),
             ("פרטים", details or "—")],
        ),
    )
