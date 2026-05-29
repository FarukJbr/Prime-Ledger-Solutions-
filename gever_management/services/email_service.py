"""
Email notification service – sends alerts to the Chairman.
Uses Gmail SMTP. Requires GMAIL_USER + GMAIL_APP_PASSWORD env vars.
Get app password at: https://myaccount.google.com/apppasswords
"""
import smtplib
import ssl
import logging
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from config import settings

logger = logging.getLogger(__name__)

PORTAL_URL = "https://app.primels.co.il"


def _template(title: str, rows: list[tuple], cta: str = "פתח דשבורד") -> str:
    rows_html = "".join(
        f'<tr><td style="padding:6px 0;color:#94a3b8;font-size:0.88rem;width:140px;">{k}</td>'
        f'<td style="padding:6px 0;color:#e2e8f0;font-size:0.88rem;">{v}</td></tr>'
        for k, v in rows
    )
    return f"""<!DOCTYPE html>
<html dir="rtl" lang="he">
<head><meta charset="UTF-8"></head>
<body style="margin:0;padding:0;background:#0a0f1e;font-family:Arial,sans-serif;direction:rtl;">
<div style="max-width:580px;margin:0 auto;padding:24px 16px;">
  <div style="background:linear-gradient(135deg,#1e3a8a,#5b21b6);border-radius:14px;padding:22px 24px;margin-bottom:14px;text-align:center;">
    <div style="font-size:2rem;margin-bottom:6px;">🏢</div>
    <div style="color:white;font-size:1.15rem;font-weight:700;">גבר יזמות ייעוץ עסקי והשקעות</div>
    <div style="color:rgba(255,255,255,0.65);font-size:0.8rem;margin-top:3px;">AI Management Platform</div>
  </div>
  <div style="background:#111827;border:1px solid #1e2d45;border-radius:14px;padding:22px 24px;margin-bottom:14px;">
    <h2 style="color:#e2e8f0;font-size:1.05rem;margin:0 0 16px;">{title}</h2>
    <table style="width:100%;border-collapse:collapse;">{rows_html}</table>
  </div>
  <div style="text-align:center;margin-bottom:12px;">
    <a href="{PORTAL_URL}" style="display:inline-block;background:linear-gradient(135deg,#1e40af,#6d28d9);
       color:white;text-decoration:none;padding:11px 26px;border-radius:8px;font-weight:700;font-size:0.9rem;">{cta}</a>
  </div>
  <div style="text-align:center;color:#475569;font-size:0.72rem;">גבר יזמות • AI Management Platform</div>
</div>
</body></html>"""


def _send(subject: str, html: str) -> bool:
    to = settings.chairman_email
    user = getattr(settings, "gmail_user", "")
    pw = getattr(settings, "gmail_app_password", "")
    if not user or not pw:
        logger.info("[EMAIL] Not configured – skipping: %s", subject)
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
        logger.info("[EMAIL] Sent: %s → %s", subject, to)
        return True
    except Exception as e:
        logger.error("[EMAIL] Failed: %s", e)
        return False


def notify_task_completed(task_title: str, departments: list, task_id: str):
    _send(
        subject=f"✅ משימה הושלמה – {task_title}",
        html=_template(
            "כל המחלקות השלימו את עבודתן ומחכות לאישורך",
            [
                ("משימה", task_title),
                ("מחלקות", " • ".join(departments)),
                ("סטטוס", "ממתין לאישור יו\"ר"),
            ],
            cta="לאישור בדשבורד",
        ),
    )


def notify_deliverable_ready(task_title: str, department: str, employee_name: str):
    _send(
        subject=f"📋 תוצר ממתין לאישורך – {department}",
        html=_template(
            "תוצר חדש הוגש ומחכה לאישורך",
            [
                ("משימה", task_title),
                ("מחלקה", department),
                ("הוכן על ידי", employee_name),
                ("פעולה נדרשת", "עיין ואשר/דחה בדשבורד"),
            ],
            cta="לאישור בדשבורד",
        ),
    )


def notify_published(task_title: str, platform: str, post_id: str = ""):
    _send(
        subject=f"🚀 פורסם בהצלחה – {platform}",
        html=_template(
            f"פרסום בוצע בהצלחה ב-{platform}",
            [
                ("משימה", task_title),
                ("פלטפורמה", platform),
                ("מזהה פוסט", post_id or "—"),
                ("סטטוס", "פורסם"),
            ],
        ),
    )


def notify_publish_ready(task_title: str, platform: str):
    """When API not available – content is ready for manual publishing."""
    _send(
        subject=f"📦 תוכן מוכן להורדה ופרסום – {platform}",
        html=_template(
            "התוכן מוכן – הורד ופרסם ידנית",
            [
                ("משימה", task_title),
                ("פלטפורמה", platform),
                ("הוראה", "היכנס לדשבורד, לחץ על התוצר ולחץ ⬇️ הורד"),
            ],
            cta="הורד תוכן",
        ),
    )
