# ============================================================
#  Jabr AI Management System
#  גבר יזמות ייעוץ עסקי והשקעות
# ============================================================
import os, json, secrets, httpx
from fastapi import FastAPI, Request, HTTPException, Depends
from fastapi.responses import HTMLResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBasic, HTTPBasicCredentials
from typing import Optional
from datetime import datetime

# ── Environment ──────────────────────────────────────────────
ANTHROPIC_KEY   = os.getenv("ANTHROPIC_API_KEY", "")
SB_URL          = os.getenv("SUPABASE_URL", "")
SB_KEY          = os.getenv("SUPABASE_ANON_KEY", "")
APP_USER        = os.getenv("DASHBOARD_USER", "chairman")
APP_PASS        = os.getenv("DASHBOARD_PASSWORD", "")
COMPANY         = os.getenv("COMPANY_NAME", "גבר יזמות ייעוץ עסקי והשקעות")
FB_PAGE_TOKEN   = os.getenv("META_PAGE_TOKEN", "")
FB_PAGE_ID      = os.getenv("META_PAGE_ID", "")
IG_ACCOUNT_ID   = os.getenv("INSTAGRAM_ACCOUNT_ID", "")
WA_TOKEN        = os.getenv("WHATSAPP_TOKEN", "")
WA_PHONE_ID     = os.getenv("WHATSAPP_PHONE_ID", "")

# ── App ───────────────────────────────────────────────────────
app = FastAPI(title="Jabr Management", docs_url=None, redoc_url=None)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], allow_methods=["*"], allow_headers=["*"]
)
_security = HTTPBasic(auto_error=False)

# ── Auth ──────────────────────────────────────────────────────
def auth(creds: Optional[HTTPBasicCredentials] = Depends(_security)) -> str:
    """
    No WWW-Authenticate header → browser never shows native auth popup.
    Password must be set via DASHBOARD_PASSWORD env var in Railway.
    """
    ok = (
        creds is not None and
        APP_PASS != "" and
        secrets.compare_digest(creds.username.encode(), APP_USER.encode()) and
        secrets.compare_digest(creds.password.encode(), APP_PASS.encode())
    )
    if not ok:
        raise HTTPException(status_code=401, detail="Unauthorized")
    return creds.username

# ── Supabase helpers ──────────────────────────────────────────
def _sb_hdrs():
    return {
        "apikey": SB_KEY,
        "Authorization": f"Bearer {SB_KEY}",
        "Content-Type": "application/json",
        "Prefer": "return=representation",
    }

async def db_get(table: str, qs: str = "") -> list:
    if not SB_URL:
        return []
    url = f"{SB_URL}/rest/v1/{table}" + (f"?{qs}" if qs else "")
    try:
        async with httpx.AsyncClient() as c:
            r = await c.get(url, headers=_sb_hdrs(), timeout=15)
            return r.json() if r.status_code == 200 else []
    except Exception:
        return []

async def db_ins(table: str, data: dict) -> dict:
    if not SB_URL:
        return {"id": "demo", **data}
    try:
        async with httpx.AsyncClient() as c:
            r = await c.post(f"{SB_URL}/rest/v1/{table}",
                             headers=_sb_hdrs(), json=data, timeout=15)
            res = r.json()
            if isinstance(res, list) and res:
                return res[0]
            if isinstance(res, dict):
                return res
            return {"id": "ok"}
    except Exception as e:
        return {"error": str(e)}

async def db_patch(table: str, match: str, data: dict):
    if not SB_URL:
        return
    async with httpx.AsyncClient() as c:
        await c.patch(f"{SB_URL}/rest/v1/{table}?{match}",
                      headers=_sb_hdrs(), json=data, timeout=10)

# ── AI Agents ─────────────────────────────────────────────────
AGENTS = {
    "ceo":        ("דניאל כהן",      "מנכ\"ל",        "אתה דניאל כהן מנכ\"ל {co}. אתה מתאם מחלקות, מחלק משימות ומסכם תוצאות."),
    "cfo":        ("מיכאל לוי",      "CFO",            "אתה מיכאל לוי CFO ב{co}. אתה אחראי על תזרים, תקציבים וניתוח עלויות."),
    "marketing":  ("נועה שפירא",     "מנהלת שיווק",   "את נועה שפירא מנהלת שיווק ב{co}. אחראית על קמפיינים ואסטרטגיה שיווקית."),
    "sales":      ("רון אברהם",      "מנהל מכירות",   "אתה רון אברהם מנהל מכירות ב{co}. אחראי על לידים, עסקאות וצמיחת הכנסות."),
    "legal":      ("עו\"ד תמר גולן", "יועמ\"ש",       "את עו\"ד תמר גולן היועמ\"ש של {co}. מטפלת בחוזים, רגולציה וסיכונים משפטיים."),
    "cto":        ("אלון בן-דוד",    "CTO",            "אתה אלון בן-דוד CTO ב{co}. אחראי על טכנולוגיה, פיתוח ותשתיות."),
    "content":    ("שיר מזרחי",      "מנהלת תוכן",    "את שיר מזרחי מנהלת תוכן ב{co}. יוצרת תוכן שיווקי, פוסטים וסרטונים."),
    "pr":         ("גיל פרץ",        "מנהל יח\"צ",    "אתה גיל פרץ מנהל יחסי הציבור של {co}. מטפל במוניטין, תקשורת ומדיה."),
    "compliance": ("ד\"ר ענת רוזן",  "קצינת ציות",    "את ד\"ר ענת רוזן קצינת הציות של {co}. מוודאת עמידה ברגולציה ותקנות."),
    "hr":         ("יובל כץ",        "מנהל HR",        "אתה יובל כץ מנהל משאבי האנוש של {co}. אחראי על גיוס, רווחה והדרכות."),
    "customer":   ("ליאת דביר",      "מנהלת שירות",   "את ליאת דביר מנהלת שירות הלקוחות של {co}. מטפלת בפניות, תלונות ושביעות רצון."),
}

DEPTS = {
    "ceo":        {"name": "מנכ\"ל",         "icon": "👑", "color": "#a78bfa"},
    "cfo":        {"name": "כספים",           "icon": "💰", "color": "#f5c842"},
    "marketing":  {"name": "שיווק",           "icon": "📣", "color": "#f87171"},
    "sales":      {"name": "מכירות",          "icon": "📈", "color": "#22d3a0"},
    "legal":      {"name": "משפטי",           "icon": "⚖️", "color": "#60a5fa"},
    "cto":        {"name": "טכנולוגיה",       "icon": "💻", "color": "#34d399"},
    "content":    {"name": "תוכן",            "icon": "🎨", "color": "#fb923c"},
    "pr":         {"name": "יח\"צ",           "icon": "📢", "color": "#e879f9"},
    "compliance": {"name": "ציות",            "icon": "🛡️", "color": "#94a3b8"},
    "hr":         {"name": "HR",              "icon": "👥", "color": "#4ade80"},
    "customer":   {"name": "שירות לקוחות",    "icon": "🎧", "color": "#38bdf8"},
}

STAFF = {
    "ceo":        [("יעל מזרחי","עוזרת מנכ\"ל"),("אסף ברק","מנהל פרויקטים"),("מיה לוין","רכזת"),("עומר שלום","אנליסט")],
    "cfo":        [("דנה כהן","חשבת"),("רועי פלד","אנליסט פיננסי"),("שרה לוי","גזברית"),("אמיר גל","מנהל תקציב")],
    "marketing":  [("נדב ביטון","מנהל דיגיטל"),("טל שר","מעצב גרפי"),("יונית אור","כותבת תוכן"),("עידן רז","SEO")],
    "sales":      [("ליאל דוד","נציג מכירות"),("הילה ים","מנהלת לקוחות"),("בן גבע","אנליסט"),("מור שגיא","נציגת מכירות")],
    "legal":      [("ניר אלון","עו\"ד"),("שירה רן","פרלגל"),("גבי מור","יועץ רגולציה"),("לי בן","מזכירת משפטים")],
    "cto":        [("ירון נוי","Full Stack"),("הדר עם","DevOps"),("ליר שן","Backend"),("כרמל אל","UX/UI")],
    "content":    [("אביב כץ","צלם ועורך"),("ניל שר","מנהל סושיאל"),("עלמא פז","יוצרת תוכן"),("יאיר אף","YouTube")],
    "pr":         [("הילה דן","דוברת"),("רן שם","יחצ\"ן"),("שי לם","מנהל אירועים"),("מאיה ון","קשרי תקשורת")],
    "compliance": [("ורד נץ","קצינת ציות"),("תמר גן","מבקרת פנים"),("אלי קם","מנהל סיכונים"),("רינה שן","יועצת רגולציה")],
    "hr":         [("נועם בר","מגייסת"),("שלי גז","מנהלת רווחה"),("עמית לז","מנהל הכשרות"),("ציפי רם","יועצת ארגונית")],
    "customer":   [("דור כהן","נציג שירות"),("עינת שמ","נציגת שירות"),("אלון בר","מנהל תלונות"),("מרים כ","נציגת שירות")],
}

async def ask_ai(dept: str, prompt: str, context: str = "") -> str:
    if not ANTHROPIC_KEY:
        name = AGENTS.get(dept, ("AI", "", ""))[0]
        return f"[{name}]: הגדר ANTHROPIC_API_KEY ב-Railway כדי להפעיל את ה-AI."
    name, title, sys_tpl = AGENTS.get(dept, ("AI", "עוזר", "אתה עוזר מקצועי."))
    system = sys_tpl.replace("{co}", COMPANY)
    if context:
        system += f"\n\nהקשר שיחה:\n{context}"
    try:
        async with httpx.AsyncClient() as c:
            r = await c.post(
                "https://api.anthropic.com/v1/messages",
                headers={
                    "x-api-key": ANTHROPIC_KEY,
                    "anthropic-version": "2023-06-01",
                    "content-type": "application/json",
                },
                json={
                    "model": "claude-opus-4-6",
                    "max_tokens": 1500,
                    "system": system,
                    "messages": [{"role": "user", "content": prompt}],
                },
                timeout=45,
            )
            if r.status_code == 200:
                return r.json()["content"][0]["text"]
            return f"שגיאת AI: {r.status_code}"
    except Exception as e:
        return f"שגיאת חיבור: {e}"

def now() -> str:
    return datetime.utcnow().isoformat()

# ════════════════════════════════════════════════════════════════
#  API ROUTES
# ════════════════════════════════════════════════════════════════

@app.get("/api/verify")
async def verify(u: str = Depends(auth)):
    return {"ok": True, "user": u}

@app.get("/api/health")
async def health():
    return {
        "status": "ok",
        "anthropic": bool(ANTHROPIC_KEY),
        "supabase": bool(SB_URL and SB_KEY),
        "env": os.getenv("ENVIRONMENT", "production"),
    }

@app.get("/api/stats")
async def stats(u: str = Depends(auth)):
    tasks = await db_get("tasks", "select=count")
    done  = await db_get("tasks", "select=count&status=eq.done")
    def cnt(x):
        return x[0].get("count", 0) if x and isinstance(x[0], dict) else 0
    return {
        "tasks_total":   cnt(tasks),
        "tasks_done":    cnt(done),
        "departments":   len(DEPTS),
        "employees":     sum(1 + len(v) for v in STAFF.values()),
    }

@app.get("/api/departments")
async def departments(u: str = Depends(auth)):
    return [
        {
            "id":    k,
            "name":  v["name"],
            "icon":  v["icon"],
            "color": v["color"],
            "head":  AGENTS[k][0],
            "title": AGENTS[k][1],
        }
        for k, v in DEPTS.items()
    ]

@app.get("/api/employees")
async def employees(dept: Optional[str] = None, u: str = Depends(auth)):
    rows = []
    for did in ([dept] if dept else list(DEPTS)):
        if did not in DEPTS:
            continue
        ag = AGENTS[did]
        rows.append({"id": f"{did}-0", "name": ag[0], "role": ag[1],
                     "department": did, "is_head": True,  "status": "active"})
        for name, role in STAFF.get(did, []):
            rows.append({"id": f"{did}-{name}", "name": name, "role": role,
                         "department": did, "is_head": False, "status": "active"})
    return rows

@app.get("/api/tasks")
async def get_tasks(status: Optional[str] = None, dept: Optional[str] = None,
                    u: str = Depends(auth)):
    qs = "order=created_at.desc&limit=50"
    if status: qs += f"&status=eq.{status}"
    if dept:   qs += f"&department=eq.{dept}"
    return await db_get("tasks", qs)

@app.post("/api/tasks")
async def create_task(req: Request, u: str = Depends(auth)):
    b = await req.json()
    if not b.get("title", "").strip():
        raise HTTPException(400, "נא להזין כותרת")
    return await db_ins("tasks", {
        "title":       b["title"],
        "description": b.get("description", ""),
        "department":  b.get("department", "ceo"),
        "priority":    b.get("priority", "medium"),
        "status":      "pending",
        "created_by":  u,
        "created_at":  now(),
    })

@app.post("/api/tasks/{tid}/approve")
async def approve_task(tid: str, u: str = Depends(auth)):
    await db_patch("tasks", f"id=eq.{tid}", {"status": "approved"})
    return {"ok": True}

@app.post("/api/instruct")
async def instruct(req: Request, u: str = Depends(auth)):
    b = await req.json()
    text = b.get("instruction", "").strip()
    if not text:
        raise HTTPException(400, "נא לכתוב הוראה")
    reply = await ask_ai(
        "ceo",
        f'קיבלת הוראה מיו"ר הדירקטוריון:\n"{text}"\n\n'
        "1. נתח את ההוראה\n2. אילו מחלקות מעורבות?\n"
        "3. תוכנית פעולה\n4. ציר זמן מוצע",
    )
    await db_ins("instructions", {
        "text": text, "ceo_response": reply,
        "status": "processing", "created_at": now(),
    })
    return {"instruction": text, "ceo_response": reply}

@app.get("/api/instructions")
async def get_instructions(u: str = Depends(auth)):
    return await db_get("instructions", "order=created_at.desc&limit=20")

@app.post("/api/chat/{dept}")
async def chat(dept: str, req: Request, u: str = Depends(auth)):
    b    = await req.json()
    msg  = b.get("message", "")
    hist = b.get("history", [])
    ctx  = "\n".join(f"{m['role']}: {m['content']}" for m in hist[-8:])
    reply = await ask_ai(dept, msg, ctx)
    await db_ins("chat_messages", {
        "department": dept, "user_message": msg,
        "ai_response": reply, "created_at": now(),
    })
    ag = AGENTS.get(dept, ("AI", "", ""))
    return {"response": reply, "agent": ag[0], "title": ag[1]}

@app.post("/api/meetings")
async def create_meeting(req: Request, u: str = Depends(auth)):
    b      = await req.json()
    topic  = b.get("topic", "")
    agenda = b.get("agenda", "")
    depts  = b.get("departments", ["ceo"])[:5]
    responses = {}
    for d in depts:
        responses[d] = await ask_ai(
            d, f"ישיבה בנושא: {topic}\nסדר יום: {agenda}\nמה עמדתך ותרומתך?"
        )
    await db_ins("meetings", {
        "topic": topic, "agenda": agenda,
        "responses": json.dumps(responses, ensure_ascii=False),
        "status": "completed", "created_at": now(),
    })
    return {"responses": responses}

@app.get("/api/meetings")
async def get_meetings(u: str = Depends(auth)):
    return await db_get("meetings", "order=created_at.desc&limit=20")

@app.post("/api/reports/generate")
async def generate_report(req: Request, u: str = Depends(auth)):
    b    = await req.json()
    dept = b.get("department", "ceo")
    kind = b.get("type", "weekly")
    dn   = DEPTS.get(dept, {}).get("name", dept)
    content = await ask_ai(
        dept,
        f"צור דוח {kind} מקצועי למחלקת {dn}.\n"
        "כלול: סיכום מנהלים, הישגים עיקריים, אתגרים, תוכנית לתקופה הבאה.",
    )
    rec = {
        "title": f"דוח {kind} – {dn}", "department": dept,
        "content": content, "type": kind, "created_at": now(),
    }
    await db_ins("reports", rec)
    return {"report": rec}

@app.get("/api/reports")
async def get_reports(u: str = Depends(auth)):
    return await db_get("reports", "order=created_at.desc&limit=20")

@app.get("/api/approvals")
async def get_approvals(u: str = Depends(auth)):
    return await db_get("tasks", "status=eq.pending_approval&order=created_at.desc")

@app.post("/api/strategy/goals")
async def set_goals(req: Request, u: str = Depends(auth)):
    b     = await req.json()
    goals = b.get("goals", "").strip()
    if not goals:
        raise HTTPException(400, "נא להזין יעדים")
    plan = await ask_ai(
        "ceo",
        f'יו"ר הציב יעדים אסטרטגיים:\n{goals}\n\n'
        "צור תוכנית: 1.פירוט יעדים 2.לוח זמנים 3.KPIs 4.סיכונים 5.תקציב נדרש",
    )
    await db_ins("strategic_goals", {
        "goals": goals, "plan": plan,
        "status": "active", "created_at": now(),
    })
    return {"goals": goals, "plan": plan}

@app.get("/api/strategy/goals")
async def get_goals(u: str = Depends(auth)):
    return await db_get("strategic_goals", "order=created_at.desc&limit=10")

@app.get("/api/cashflow")
async def get_cashflow(u: str = Depends(auth)):
    return await db_get("cashflow", "order=date.desc&limit=200")

@app.post("/api/cashflow")
async def add_cashflow(req: Request, u: str = Depends(auth)):
    b = await req.json()
    try:
        amount = float(b.get("amount", 0))
    except (ValueError, TypeError):
        raise HTTPException(400, "סכום לא תקין")
    return await db_ins("cashflow", {
        "date":        b.get("date", datetime.utcnow().date().isoformat()),
        "description": b.get("description", ""),
        "amount":      amount,
        "type":        b.get("type", "income"),
        "category":    b.get("category", "כללי"),
        "client_id":   b.get("client_id", ""),
        "created_at":  now(),
    })

@app.post("/api/cashflow/analyze")
async def analyze_cashflow(u: str = Depends(auth)):
    rows = await db_get("cashflow", "order=date.desc&limit=100")
    if not rows:
        return {"analysis": "אין נתוני תזרים עדיין.", "rows": [], "summary": {}}
    income  = sum(float(r.get("amount", 0)) for r in rows if r.get("type") == "income")
    expense = sum(float(r.get("amount", 0)) for r in rows if r.get("type") == "expense")
    analysis = await ask_ai(
        "cfo",
        f"תזרים מזומנים:\n"
        f"• הכנסות: ₪{income:,.0f}\n"
        f"• הוצאות: ₪{expense:,.0f}\n"
        f"• יתרה:   ₪{income - expense:,.0f}\n\n"
        "נתח את התזרים ותן המלצות קונקרטיות לשיפור.",
    )
    return {
        "analysis": analysis,
        "rows":     rows,
        "summary":  {"income": income, "expense": expense, "balance": income - expense},
    }

@app.post("/api/social/generate")
async def generate_post(req: Request, u: str = Depends(auth)):
    b     = await req.json()
    topic = b.get("topic", "")
    post  = await ask_ai(
        "content",
        f"כתוב פוסט מקצועי לרשתות חברתיות בנושא: {topic}\n"
        "כלול: כותרת מושכת, גוף הפוסט, CTA ברור, האשטגים רלוונטיים.",
    )
    return {"post": post}

@app.post("/api/social/publish")
async def publish_post(req: Request, u: str = Depends(auth)):
    b = await req.json()
    if not b.get("text", "").strip():
        raise HTTPException(400, "נא להזין תוכן לפרסום")
    text      = b["text"]
    image_url = b.get("image_url", "")
    platforms = b.get("platforms", [])
    results   = {}

    # Facebook
    if "facebook" in platforms:
        if FB_PAGE_TOKEN and FB_PAGE_ID:
            async with httpx.AsyncClient() as c:
                r = await c.post(
                    f"https://graph.facebook.com/v19.0/{FB_PAGE_ID}/feed",
                    data={"message": text, "access_token": FB_PAGE_TOKEN},
                    timeout=20,
                )
                res = r.json()
                results["facebook"] = {
                    "ok":      "id" in res,
                    "post_id": res.get("id"),
                    "error":   res.get("error", {}).get("message"),
                }
        else:
            results["facebook"] = {"ok": False, "error": "הגדר META_PAGE_TOKEN ו-META_PAGE_ID ב-Railway"}

    # Instagram
    if "instagram" in platforms:
        if FB_PAGE_TOKEN and IG_ACCOUNT_ID and image_url:
            async with httpx.AsyncClient() as c:
                r1 = await c.post(
                    f"https://graph.facebook.com/v19.0/{IG_ACCOUNT_ID}/media",
                    data={"image_url": image_url, "caption": text, "access_token": FB_PAGE_TOKEN},
                    timeout=20,
                )
                mid = r1.json().get("id")
                if mid:
                    r2 = await c.post(
                        f"https://graph.facebook.com/v19.0/{IG_ACCOUNT_ID}/media_publish",
                        data={"creation_id": mid, "access_token": FB_PAGE_TOKEN},
                        timeout=20,
                    )
                    res2 = r2.json()
                    results["instagram"] = {"ok": "id" in res2, "post_id": res2.get("id")}
                else:
                    results["instagram"] = {"ok": False, "error": r1.json().get("error", {}).get("message", "שגיאה")}
        else:
            results["instagram"] = {"ok": False, "error": "הגדר INSTAGRAM_ACCOUNT_ID + תמונה ב-Railway"}

    # WhatsApp
    if "whatsapp" in platforms:
        phone = b.get("whatsapp_phone", "")
        if phone and WA_TOKEN and WA_PHONE_ID:
            async with httpx.AsyncClient() as c:
                r = await c.post(
                    f"https://graph.facebook.com/v19.0/{WA_PHONE_ID}/messages",
                    headers={"Authorization": f"Bearer {WA_TOKEN}", "Content-Type": "application/json"},
                    json={"messaging_product": "whatsapp", "to": phone,
                          "type": "text", "text": {"body": text}},
                    timeout=20,
                )
                res = r.json()
                results["whatsapp"] = {"ok": "messages" in res, "error": res.get("error", {}).get("message")}
        else:
            results["whatsapp"] = {"ok": False, "error": "הגדר WHATSAPP_TOKEN + מספר טלפון"}

    published = any(v.get("ok") for v in results.values())
    await db_ins("social_posts", {
        "text":       text,
        "image_url":  image_url,
        "platforms":  json.dumps(platforms),
        "results":    json.dumps(results, ensure_ascii=False),
        "status":     "published" if published else "pending",
        "created_at": now(),
    })
    return {"text": text, "results": results}

@app.get("/api/social/posts")
async def get_posts(u: str = Depends(auth)):
    return await db_get("social_posts", "order=created_at.desc&limit=30")

# ════════════════════════════════════════════════════════════════
#  HTML PAGES
# ════════════════════════════════════════════════════════════════

LOGIN_HTML = """<!DOCTYPE html>
<html lang="he" dir="rtl">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>גבר – כניסה</title>
<style>
@import url('https://fonts.googleapis.com/css2?family=Heebo:wght@400;600;700;800&display=swap');
*{box-sizing:border-box;margin:0;padding:0}
body{font-family:'Heebo',sans-serif;min-height:100vh;display:flex;align-items:center;
     justify-content:center;background:radial-gradient(ellipse at 20% 50%,#1a0a4a,#0d1a3a 40%,#060b18)}
.card{background:rgba(22,25,33,.93);backdrop-filter:blur(24px);
      border:1px solid rgba(167,139,250,.2);border-radius:22px;
      padding:44px 36px;width:100%;max-width:390px;box-shadow:0 0 80px rgba(108,99,255,.2)}
.logo{text-align:center;margin-bottom:28px}
.logo-icon{width:68px;height:68px;background:linear-gradient(135deg,#6c63ff,#a78bfa);
           border-radius:18px;display:inline-flex;align-items:center;
           justify-content:center;font-size:32px;margin-bottom:12px}
.logo-name{font-size:19px;font-weight:800;color:#e8eaf0}
.logo-sub{font-size:11px;color:#8892a4;margin-top:2px}
.field{margin-bottom:16px}
label{display:block;font-size:11px;color:#8892a4;margin-bottom:5px;
      font-weight:600;letter-spacing:.05em;text-transform:uppercase}
input{width:100%;background:rgba(13,15,20,.7);border:1px solid rgba(167,139,250,.2);
      border-radius:10px;color:#e8eaf0;font-family:'Heebo',sans-serif;
      font-size:14px;padding:12px 14px;direction:rtl;outline:none;transition:border-color .2s}
input:focus{border-color:#6c63ff}
.btn{width:100%;background:linear-gradient(135deg,#6c63ff,#8b5cf6);color:#fff;
     border:none;border-radius:10px;font-family:'Heebo',sans-serif;font-size:15px;
     font-weight:700;padding:14px;cursor:pointer;margin-top:4px;transition:opacity .2s}
.btn:hover{opacity:.88}
.btn:disabled{opacity:.5;cursor:not-allowed}
.err{background:rgba(248,113,113,.1);border:1px solid rgba(248,113,113,.3);
     border-radius:8px;padding:9px 13px;font-size:12px;color:#f87171;
     margin-top:10px;display:none;text-align:center}
</style>
</head>
<body>
<div class="card">
  <div class="logo">
    <div class="logo-icon">🏢</div>
    <div class="logo-name">גבר יזמות ייעוץ עסקי</div>
    <div class="logo-sub">AI Company Management System</div>
  </div>
  <div class="field">
    <label>שם משתמש</label>
    <input id="u" type="text" placeholder="chairman" autocomplete="username">
  </div>
  <div class="field">
    <label>סיסמה</label>
    <input id="p" type="password" placeholder="••••••••"
           onkeydown="if(event.key==='Enter')login()">
  </div>
  <button class="btn" id="btn" onclick="login()">🔐 כניסה למערכת</button>
  <div class="err" id="err"></div>
</div>
<script>
async function login() {
  const u = document.getElementById('u').value.trim();
  const p = document.getElementById('p').value.trim();
  if (!u || !p) return;
  const btn = document.getElementById('btn');
  const err = document.getElementById('err');
  btn.disabled = true;
  btn.textContent = '...מתחבר';
  err.style.display = 'none';
  try {
    const token = btoa(u + ':' + p);
    const r = await fetch('/api/verify', {
      headers: { 'Authorization': 'Basic ' + token }
    });
    if (r.ok) {
      sessionStorage.setItem('jauth', token);
      location.replace('/dashboard#' + token);
    } else {
      err.textContent = 'שם משתמש או סיסמה שגויים';
      err.style.display = 'block';
    }
  } catch (e) {
    err.textContent = 'שגיאת חיבור — נסה שוב';
    err.style.display = 'block';
  }
  btn.disabled = false;
  btn.textContent = '🔐 כניסה למערכת';
}
</script>
</body>
</html>"""

DASHBOARD_HTML = """<!DOCTYPE html>
<html lang="he" dir="rtl">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>גבר – ניהול AI</title>
<style>
@import url('https://fonts.googleapis.com/css2?family=Heebo:wght@300;400;500;600;700;800&display=swap');
:root{
  --bg:#0d0f14;--sur:#161921;--card:#1c2030;--bdr:#252a3a;
  --ac:#6c63ff;--ac2:#a78bfa;--gld:#f5c842;--grn:#22d3a0;
  --red:#f87171;--org:#fb923c;--tx:#e8eaf0;--mt:#8892a4;--r:11px
}
*{box-sizing:border-box;margin:0;padding:0}
body{font-family:'Heebo',sans-serif;background:var(--bg);color:var(--tx);min-height:100vh}

/* Header */
.hdr{background:linear-gradient(135deg,#1a0a4a,#0d1a3a,#0a1520);
     border-bottom:1px solid var(--bdr);padding:0 18px;display:flex;
     align-items:center;justify-content:space-between;height:58px;
     position:sticky;top:0;z-index:100}
.hdr-l{display:flex;align-items:center;gap:10px}
.hdr-ic{width:36px;height:36px;background:linear-gradient(135deg,var(--ac),var(--ac2));
        border-radius:9px;display:flex;align-items:center;justify-content:center;font-size:18px}
.hdr-title{font-weight:700;font-size:14px}
.hdr-sub{font-size:10px;color:var(--mt)}
.badge-on{background:rgba(34,211,160,.15);color:var(--grn);
          border:1px solid rgba(34,211,160,.3);border-radius:20px;padding:3px 10px;font-size:11px}
.btn-exit{background:rgba(248,113,113,.12);color:var(--red);
          border:1px solid rgba(248,113,113,.3);border-radius:7px;
          padding:5px 12px;font-size:11px;cursor:pointer;font-family:inherit}

/* Tabs */
.tabs{background:var(--sur);border-bottom:1px solid var(--bdr);
      padding:0 18px;display:flex;overflow-x:auto;scrollbar-width:none}
.tabs::-webkit-scrollbar{display:none}
.tab{background:none;border:none;color:var(--mt);font-family:inherit;font-size:11px;
     font-weight:500;padding:12px 11px;cursor:pointer;white-space:nowrap;
     border-bottom:2px solid transparent;transition:all .18s}
.tab:hover{color:var(--tx)}
.tab.on{color:var(--ac2);border-bottom-color:var(--ac2)}

/* Layout */
.wrap{padding:18px;max-width:1400px;margin:0 auto}
.panel{display:none}.panel.on{display:block}

/* Cards */
.card{background:var(--card);border:1px solid var(--bdr);
      border-radius:var(--r);padding:16px;margin-bottom:13px}
.card-title{font-size:13px;font-weight:700;margin-bottom:13px;
            display:flex;align-items:center;gap:7px}

/* Stats */
.stats{display:grid;grid-template-columns:repeat(3,1fr);gap:9px;margin-bottom:15px}
.stat{background:var(--card);border:1px solid var(--bdr);border-radius:var(--r);
      padding:14px 10px;text-align:center}
.stat-n{font-size:26px;font-weight:800;color:var(--ac2);line-height:1;margin-bottom:4px}
.stat-l{font-size:10px;color:var(--mt)}

/* Forms */
.fg{margin-bottom:11px}
label{display:block;font-size:11px;color:var(--mt);margin-bottom:4px}
textarea,input[type=text],select{
  width:100%;background:var(--sur);border:1px solid var(--bdr);
  border-radius:8px;color:var(--tx);font-family:inherit;font-size:13px;
  padding:9px 12px;direction:rtl;outline:none;transition:border-color .2s}
textarea:focus,input[type=text]:focus,select:focus{border-color:var(--ac)}
textarea{resize:vertical;min-height:78px}
select option{background:var(--card)}
.fr2{display:grid;grid-template-columns:1fr 1fr;gap:9px}

/* Buttons */
.btn{display:inline-flex;align-items:center;gap:5px;
     background:linear-gradient(135deg,var(--ac),#8b5cf6);color:#fff;
     border:none;border-radius:8px;padding:9px 16px;font-family:inherit;
     font-size:12px;font-weight:700;cursor:pointer;transition:opacity .2s}
.btn:hover{opacity:.85}
.btn:disabled{opacity:.5;cursor:not-allowed}
.btn-sm{padding:5px 11px;font-size:11px}
.btn-green{background:linear-gradient(135deg,#059669,var(--grn))}
.btn-ghost{background:none;border:1px solid var(--bdr);color:var(--tx)}
.btn-ghost:hover{border-color:var(--ac);color:var(--ac2)}

/* Result box */
.result{background:var(--sur);border:1px solid var(--bdr);border-radius:8px;
        padding:13px;margin-top:11px;font-size:12px;line-height:1.75;
        white-space:pre-wrap;display:none}
.result.show{display:block}
.result-lbl{font-size:10px;color:var(--ac2);font-weight:700;
            margin-bottom:7px;text-transform:uppercase;letter-spacing:.05em}

/* Dept grid */
.dg{display:grid;grid-template-columns:repeat(auto-fill,minmax(135px,1fr));gap:9px}
.dc{background:var(--sur);border:1px solid var(--bdr);border-radius:var(--r);
    padding:12px;cursor:pointer;transition:all .2s;text-align:center}
.dc:hover{transform:translateY(-2px);border-color:var(--ac)}
.dc-icon{font-size:24px;margin-bottom:6px}
.dc-name{font-size:11px;font-weight:700}
.dc-head{font-size:10px;color:var(--mt);margin-top:3px}
.dc-title{font-size:9px;color:var(--ac2);margin-top:2px}

/* Chat */
.chat-wrap{display:grid;grid-template-columns:160px 1fr;gap:11px;height:570px}
.chat-side{background:var(--sur);border:1px solid var(--bdr);
           border-radius:var(--r);overflow-y:auto}
.ca{width:100%;background:none;border:none;border-bottom:1px solid var(--bdr);
    color:var(--tx);font-family:inherit;font-size:11px;padding:9px 10px;
    cursor:pointer;text-align:right;display:flex;flex-direction:column;
    align-items:flex-end;gap:2px;transition:background .15s}
.ca:hover{background:rgba(108,99,255,.07)}
.ca.on{background:rgba(167,139,250,.12);color:var(--ac2)}
.ca-name{font-weight:700;font-size:11px}
.ca-role{font-size:9px;color:var(--mt)}
.chat-main{background:var(--sur);border:1px solid var(--bdr);
           border-radius:var(--r);display:flex;flex-direction:column;overflow:hidden}
.chat-hdr{padding:11px 14px;border-bottom:1px solid var(--bdr);
          font-weight:700;font-size:12px;flex-shrink:0}
.chat-msgs{flex:1;overflow-y:auto;padding:11px;
           display:flex;flex-direction:column;gap:8px;min-height:0}
.msg{padding:9px 12px;border-radius:11px;font-size:12px;line-height:1.65;
     max-width:88%;word-wrap:break-word}
.msg-user{background:linear-gradient(135deg,var(--ac),#8b5cf6);
          align-self:flex-start;border-radius:11px 11px 11px 2px}
.msg-ai{background:var(--card);border:1px solid var(--bdr);
        align-self:flex-end;border-radius:11px 11px 2px 11px}
.msg-name{font-size:9px;color:var(--ac2);font-weight:700;margin-bottom:3px}
.chat-inp-wrap{padding:10px;border-top:1px solid var(--bdr);
               display:flex;gap:7px;flex-shrink:0}
.chat-inp{flex:1;background:var(--card);border:1px solid var(--bdr);
          border-radius:8px;color:var(--tx);font-family:inherit;font-size:12px;
          padding:8px 11px;direction:rtl;outline:none;resize:none;height:38px}
.chat-inp:focus{border-color:var(--ac)}

/* Task items */
.ti{background:var(--sur);border:1px solid var(--bdr);border-radius:9px;
    padding:11px 13px;margin-bottom:7px;display:flex;align-items:center;gap:9px}
.tdot{width:8px;height:8px;border-radius:50%;flex-shrink:0}
.tc-high{background:var(--red)}.tc-med{background:var(--ac2)}.tc-low{background:var(--grn)}
.ti-body{flex:1;min-width:0}
.ti-title{font-size:12px;font-weight:600;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.ti-meta{font-size:10px;color:var(--mt);margin-top:2px}
.tag{background:rgba(108,99,255,.15);color:var(--ac2);
     border:1px solid rgba(108,99,255,.3);border-radius:5px;
     padding:2px 7px;font-size:10px;white-space:nowrap;flex-shrink:0}
.tag-g{background:rgba(34,211,160,.15);color:var(--grn);border-color:rgba(34,211,160,.3)}
.tag-o{background:rgba(251,146,60,.15);color:var(--org);border-color:rgba(251,146,60,.3)}

/* Employees table */
.etbl{width:100%;border-collapse:collapse;font-size:12px}
.etbl th{background:var(--sur);padding:9px 10px;text-align:right;font-weight:600;
         color:var(--mt);font-size:10px;border-bottom:1px solid var(--bdr)}
.etbl td{padding:9px 10px;border-bottom:1px solid rgba(37,42,58,.3)}
.etbl tr:hover td{background:rgba(108,99,255,.025)}
.av{width:26px;height:26px;border-radius:50%;
    background:linear-gradient(135deg,var(--ac),var(--ac2));
    display:inline-flex;align-items:center;justify-content:center;
    font-size:11px;font-weight:700;margin-left:7px;flex-shrink:0}

/* Platform toggle */
.plat-btn{background:var(--sur);border:1px solid var(--bdr);border-radius:9px;
          padding:9px 13px;cursor:pointer;font-family:inherit;font-size:12px;
          color:var(--mt);display:inline-flex;align-items:center;gap:6px;transition:all .2s}
.plat-btn.on{border-color:var(--ac2);color:var(--ac2);background:rgba(167,139,250,.08)}

/* Cashflow */
.cf-sum{display:grid;grid-template-columns:repeat(3,1fr);gap:9px;margin-bottom:13px}
.cfs{background:var(--sur);border:1px solid var(--bdr);
     border-radius:9px;padding:11px;text-align:center}
.cfs-n{font-size:20px;font-weight:800;margin-bottom:3px}
.cfs-l{font-size:10px;color:var(--mt)}
.cft{width:100%;border-collapse:collapse;font-size:11px}
.cft th{background:var(--sur);padding:8px 10px;text-align:right;
        font-weight:600;color:var(--mt);font-size:9px;border-bottom:1px solid var(--bdr)}
.cft td{padding:8px 10px;border-bottom:1px solid rgba(37,42,58,.3)}
.income-c{color:var(--grn)}.expense-c{color:var(--red)}

/* History item */
.hi{border-right:3px solid var(--ac);padding:7px 10px;margin-bottom:6px;
    background:rgba(108,99,255,.03);border-radius:0 6px 6px 0;font-size:11px;line-height:1.65}
.hi-meta{font-size:9px;color:var(--ac2);font-weight:700;margin-bottom:3px}

/* Spinner */
.spin{display:inline-block;width:14px;height:14px;border:2px solid rgba(167,139,250,.3);
      border-top-color:var(--ac2);border-radius:50%;animation:sp .7s linear infinite}
@keyframes sp{to{transform:rotate(360deg)}}

/* Connection status */
.conn-row{padding:10px 12px;background:var(--sur);border:1px solid var(--bdr);
          border-radius:8px;display:flex;justify-content:space-between;
          margin-bottom:7px;font-size:12px}

@media(max-width:640px){
  .fr2{grid-template-columns:1fr}
  .chat-wrap{grid-template-columns:1fr;height:auto}
  .chat-side{display:flex;overflow-x:auto;height:46px;border-radius:9px}
  .ca{flex-direction:row;border-bottom:none;border-left:1px solid var(--bdr);
      white-space:nowrap;flex-shrink:0;padding:7px 9px}
  .ca-role{display:none}
  .chat-main{height:430px}
  .cf-sum{grid-template-columns:1fr}
  .stats{grid-template-columns:1fr 1fr}
}
</style>
</head>
<body>

<div class="hdr">
  <div class="hdr-l">
    <div class="hdr-ic">🏢</div>
    <div>
      <div class="hdr-title">גבר יזמות ייעוץ עסקי</div>
      <div class="hdr-sub">AI Company Management System</div>
    </div>
  </div>
  <div style="display:flex;align-items:center;gap:8px">
    <div class="badge-on">● מחובר</div>
    <button class="btn-exit" onclick="logout()">↩ יציאה</button>
  </div>
</div>

<div class="tabs">
  <button class="tab on"  onclick="T('home',this)">🏠 ראשי</button>
  <button class="tab"     onclick="T('instruct',this)">📋 הוראות</button>
  <button class="tab"     onclick="T('tasks',this)">⚙️ משימות</button>
  <button class="tab"     onclick="T('employees',this)">👥 עובדים</button>
  <button class="tab"     onclick="T('chat',this)">💬 צ׳אט AI</button>
  <button class="tab"     onclick="T('depts',this)">🏢 מחלקות</button>
  <button class="tab"     onclick="T('meetings',this)">📅 ישיבות</button>
  <button class="tab"     onclick="T('social',this)">📱 סושיאל</button>
  <button class="tab"     onclick="T('cashflow',this)">💳 תזרים</button>
  <button class="tab"     onclick="T('reports',this)">📊 דוחות</button>
  <button class="tab"     onclick="T('strategy',this)">🎯 אסטרטגיה</button>
  <button class="tab"     onclick="T('approvals',this)">✅ אישורים</button>
  <button class="tab"     onclick="T('settings',this)">⚙️ הגדרות</button>
</div>

<div class="wrap">

<!-- HOME -->
<div id="p-home" class="panel on">
  <div class="stats">
    <div class="stat"><div class="stat-n" id="s-tasks">–</div><div class="stat-l">משימות</div></div>
    <div class="stat"><div class="stat-n" id="s-depts">11</div><div class="stat-l">מחלקות</div></div>
    <div class="stat"><div class="stat-n" id="s-emps">–</div><div class="stat-l">עובדים</div></div>
  </div>
  <div class="card">
    <div class="card-title">📡 סטטוס מערכת</div>
    <div id="sys-status">בודק...</div>
  </div>
  <div class="card">
    <div class="card-title">🏢 מחלקות פעילות</div>
    <div class="dg" id="home-depts"></div>
  </div>
</div>

<!-- INSTRUCT -->
<div id="p-instruct" class="panel">
  <div class="card">
    <div class="card-title">📋 הוראה למנכ"ל</div>
    <div class="fg">
      <label>הוראה</label>
      <textarea id="inst-in" placeholder='כתוב הוראה ליו"ר → מנכ"ל...'></textarea>
    </div>
    <button class="btn" onclick="sendInst()">📤 שלח הוראה</button>
    <div class="result" id="inst-out">
      <div class="result-lbl">תגובת המנכ"ל</div>
      <div id="inst-out-txt"></div>
    </div>
  </div>
  <div class="card">
    <div class="card-title">📜 היסטוריה</div>
    <div id="inst-hist"></div>
  </div>
</div>

<!-- TASKS -->
<div id="p-tasks" class="panel">
  <div class="card">
    <div class="card-title">➕ משימה חדשה</div>
    <div class="fr2">
      <div class="fg"><label>כותרת</label><input type="text" id="t-title" placeholder="כותרת המשימה"></div>
      <div class="fg"><label>מחלקה</label>
        <select id="t-dept">
          <option value="ceo">👑 מנכ"ל</option><option value="cfo">💰 כספים</option>
          <option value="marketing">📣 שיווק</option><option value="sales">📈 מכירות</option>
          <option value="legal">⚖️ משפטי</option><option value="cto">💻 טכנולוגיה</option>
          <option value="content">🎨 תוכן</option><option value="pr">📢 יח"צ</option>
          <option value="compliance">🛡️ ציות</option><option value="hr">👥 HR</option>
          <option value="customer">🎧 שירות לקוחות</option>
        </select>
      </div>
    </div>
    <div class="fg"><label>תיאור</label><textarea id="t-desc" placeholder="תיאור..."></textarea></div>
    <div class="fr2">
      <div class="fg"><label>עדיפות</label>
        <select id="t-pri">
          <option value="high">🔴 גבוהה</option>
          <option value="medium" selected>🟡 בינונית</option>
          <option value="low">🟢 נמוכה</option>
        </select>
      </div>
    </div>
    <button class="btn" onclick="createTask()">➕ צור משימה</button>
  </div>
  <div class="card">
    <div class="card-title">📋 רשימת משימות</div>
    <div id="tasks-list"></div>
  </div>
</div>

<!-- EMPLOYEES -->
<div id="p-employees" class="panel">
  <div class="card">
    <div class="card-title">👥 עובדים</div>
    <div class="fg"><label>סנן לפי מחלקה</label>
      <select id="emp-filter" onchange="loadEmp()">
        <option value="">כל המחלקות</option>
        <option value="ceo">👑 מנכ"ל</option><option value="cfo">💰 כספים</option>
        <option value="marketing">📣 שיווק</option><option value="sales">📈 מכירות</option>
        <option value="legal">⚖️ משפטי</option><option value="cto">💻 טכנולוגיה</option>
        <option value="content">🎨 תוכן</option><option value="pr">📢 יח"צ</option>
        <option value="compliance">🛡️ ציות</option><option value="hr">👥 HR</option>
        <option value="customer">🎧 שירות לקוחות</option>
      </select>
    </div>
    <div id="emp-table"></div>
  </div>
</div>

<!-- CHAT -->
<div id="p-chat" class="panel">
  <div class="chat-wrap">
    <div class="chat-side" id="chat-side"></div>
    <div class="chat-main">
      <div class="chat-hdr" id="chat-hdr">בחר מחלקה לשיחה</div>
      <div class="chat-msgs" id="chat-msgs"></div>
      <div class="chat-inp-wrap">
        <textarea class="chat-inp" id="chat-inp" placeholder="כתוב הודעה..."
          onkeydown="if(event.key==='Enter'&&!event.shiftKey){event.preventDefault();sendChat()}"></textarea>
        <button class="btn btn-sm" onclick="sendChat()">⬆</button>
      </div>
    </div>
  </div>
</div>

<!-- DEPTS -->
<div id="p-depts" class="panel">
  <div class="card">
    <div class="card-title">🏢 מחלקות החברה</div>
    <div class="dg" id="depts-grid"></div>
  </div>
</div>

<!-- MEETINGS -->
<div id="p-meetings" class="panel">
  <div class="card">
    <div class="card-title">📅 כינוס ישיבה</div>
    <div class="fg"><label>נושא</label><input type="text" id="m-topic" placeholder="נושא הישיבה..."></div>
    <div class="fg"><label>סדר יום</label><textarea id="m-agenda" placeholder="פרט את סדר היום..."></textarea></div>
    <div class="fg"><label>מחלקות משתתפות</label>
      <div style="display:flex;flex-wrap:wrap;gap:7px;margin-top:5px" id="m-depts">
        <button class="plat-btn on" data-d="ceo"        onclick="toggleBtn(this)">👑 מנכ"ל</button>
        <button class="plat-btn"    data-d="cfo"        onclick="toggleBtn(this)">💰 כספים</button>
        <button class="plat-btn"    data-d="marketing"  onclick="toggleBtn(this)">📣 שיווק</button>
        <button class="plat-btn"    data-d="sales"      onclick="toggleBtn(this)">📈 מכירות</button>
        <button class="plat-btn"    data-d="legal"      onclick="toggleBtn(this)">⚖️ משפטי</button>
        <button class="plat-btn"    data-d="cto"        onclick="toggleBtn(this)">💻 טכנולוגיה</button>
      </div>
    </div>
    <button class="btn" onclick="createMeeting()">📅 כנס ישיבה</button>
    <div class="result" id="meeting-out">
      <div class="result-lbl">סיכום הישיבה</div>
      <div id="meeting-out-txt"></div>
    </div>
  </div>
  <div class="card">
    <div class="card-title">📜 ישיבות קודמות</div>
    <div id="meetings-list"></div>
  </div>
</div>

<!-- SOCIAL -->
<div id="p-social" class="panel">
  <div class="card">
    <div class="card-title">✍️ צור פוסט AI</div>
    <div class="fg"><label>נושא</label><input type="text" id="soc-topic" placeholder="נושא הפוסט..."></div>
    <button class="btn" onclick="genPost()">🤖 צור פוסט</button>
    <div class="result" id="post-gen">
      <div class="result-lbl">פוסט שנוצר</div>
      <textarea id="post-txt" style="background:transparent;border:none;width:100%;
        color:var(--tx);font-family:inherit;font-size:12px;line-height:1.75;
        resize:none;outline:none;min-height:120px"></textarea>
    </div>
  </div>
  <div class="card">
    <div class="card-title">📤 פרסם</div>
    <div class="fg"><label>פלטפורמות</label>
      <div style="display:flex;gap:8px;flex-wrap:wrap;margin-top:5px">
        <button class="plat-btn" data-p="facebook"  onclick="togglePlat(this)">📘 Facebook</button>
        <button class="plat-btn" data-p="instagram" onclick="togglePlat(this)">📷 Instagram</button>
        <button class="plat-btn" data-p="whatsapp"  onclick="togglePlat(this)">💬 WhatsApp</button>
      </div>
    </div>
    <div class="fg" id="wa-wrap" style="display:none">
      <label>מספר WhatsApp</label>
      <input type="text" id="wa-phone" placeholder="+972501234567">
    </div>
    <div class="fg">
      <label>URL תמונה (Instagram)</label>
      <input type="text" id="post-img" placeholder="https://...">
    </div>
    <button class="btn btn-green" onclick="publishPost()">📤 פרסם עכשיו</button>
    <div class="result" id="pub-out">
      <div class="result-lbl">תוצאות פרסום</div>
      <div id="pub-txt"></div>
    </div>
  </div>
  <div class="card">
    <div class="card-title">📋 פוסטים שפורסמו</div>
    <div id="posts-list"></div>
  </div>
</div>

<!-- CASHFLOW -->
<div id="p-cashflow" class="panel">
  <div class="cf-sum">
    <div class="cfs"><div class="cfs-n income-c" id="cf-inc">₪0</div><div class="cfs-l">הכנסות</div></div>
    <div class="cfs"><div class="cfs-n expense-c" id="cf-exp">₪0</div><div class="cfs-l">הוצאות</div></div>
    <div class="cfs"><div class="cfs-n" id="cf-bal">₪0</div><div class="cfs-l">יתרה</div></div>
  </div>
  <div class="card">
    <div class="card-title">➕ הוסף תנועה</div>
    <div class="fr2">
      <div class="fg"><label>תיאור</label><input type="text" id="cf-desc" placeholder="תיאור..."></div>
      <div class="fg"><label>סכום (₪)</label><input type="text" id="cf-amt" placeholder="0"></div>
    </div>
    <div class="fr2">
      <div class="fg"><label>סוג</label>
        <select id="cf-type">
          <option value="income">📈 הכנסה</option>
          <option value="expense">📉 הוצאה</option>
        </select>
      </div>
      <div class="fg"><label>קטגוריה</label><input type="text" id="cf-cat" placeholder="כללי"></div>
    </div>
    <div class="fg"><label>תאריך</label><input type="text" id="cf-date" placeholder="YYYY-MM-DD"></div>
    <button class="btn" onclick="addCF()">➕ הוסף</button>
  </div>
  <div class="card">
    <div class="card-title">📊 ניתוח AI</div>
    <button class="btn" onclick="analyzeCF()">🤖 נתח תזרים</button>
    <div class="result" id="cf-anal">
      <div class="result-lbl">ניתוח CFO</div>
      <div id="cf-anal-txt"></div>
    </div>
  </div>
  <div class="card">
    <div class="card-title">📋 תנועות</div>
    <table class="cft">
      <thead><tr><th>תאריך</th><th>תיאור</th><th>סוג</th><th>סכום</th></tr></thead>
      <tbody id="cf-rows"></tbody>
    </table>
  </div>
</div>

<!-- REPORTS -->
<div id="p-reports" class="panel">
  <div class="card">
    <div class="card-title">📊 צור דוח</div>
    <div class="fr2">
      <div class="fg"><label>מחלקה</label>
        <select id="r-dept">
          <option value="ceo">👑 מנכ"ל</option><option value="cfo">💰 כספים</option>
          <option value="marketing">📣 שיווק</option><option value="sales">📈 מכירות</option>
          <option value="legal">⚖️ משפטי</option><option value="cto">💻 טכנולוגיה</option>
          <option value="content">🎨 תוכן</option><option value="pr">📢 יח"צ</option>
          <option value="compliance">🛡️ ציות</option><option value="hr">👥 HR</option>
          <option value="customer">🎧 שירות לקוחות</option>
        </select>
      </div>
      <div class="fg"><label>סוג</label>
        <select id="r-type">
          <option value="weekly">שבועי</option><option value="monthly">חודשי</option>
          <option value="quarterly">רבעוני</option><option value="annual">שנתי</option>
        </select>
      </div>
    </div>
    <button class="btn" onclick="genReport()">📊 צור דוח</button>
    <div class="result" id="rep-out">
      <div class="result-lbl">דוח שנוצר</div>
      <div id="rep-txt"></div>
    </div>
  </div>
  <div class="card">
    <div class="card-title">📁 דוחות קודמים</div>
    <div id="reports-list"></div>
  </div>
</div>

<!-- STRATEGY -->
<div id="p-strategy" class="panel">
  <div class="card">
    <div class="card-title">🎯 יעדים אסטרטגיים</div>
    <div class="fg">
      <label>יעדים</label>
      <textarea id="goals-in" placeholder="פרט את היעדים האסטרטגיים לשנה הקרובה..." style="min-height:110px"></textarea>
    </div>
    <button class="btn" onclick="setGoals()">🎯 הגדר יעדים</button>
    <div class="result" id="goals-out">
      <div class="result-lbl">תוכנית אסטרטגית</div>
      <div id="goals-out-txt"></div>
    </div>
  </div>
  <div class="card">
    <div class="card-title">📜 יעדים קיימים</div>
    <div id="goals-list"></div>
  </div>
</div>

<!-- APPROVALS -->
<div id="p-approvals" class="panel">
  <div class="card">
    <div class="card-title">✅ ממתינים לאישור</div>
    <div id="approvals-list"></div>
  </div>
</div>

<!-- SETTINGS -->
<div id="p-settings" class="panel">
  <div class="card">
    <div class="card-title">📡 חיבורי מערכת</div>
    <div id="settings-status"></div>
  </div>
  <div class="card">
    <div class="card-title">👤 פרטי חשבון</div>
    <div style="font-size:12px;line-height:2.2;color:var(--mt)">
      <div>חברה: <span style="color:var(--tx)">גבר יזמות ייעוץ עסקי והשקעות</span></div>
      <div>תפקיד: <span style="color:var(--tx)">יו"ר הדירקטוריון</span></div>
      <div>גרסה: <span style="color:var(--tx)">v2.0 — Clean Build</span></div>
    </div>
    <button class="btn btn-ghost" style="margin-top:14px" onclick="logout()">↩ יציאה</button>
  </div>
</div>

</div><!-- /wrap -->

<script>
'use strict';
var AUTH = '', DEPTS = [], chatDept = '', chatHist = [];

window.addEventListener('DOMContentLoaded', function() {
  AUTH = location.hash.slice(1) || sessionStorage.getItem('jauth') || '';
  if (!AUTH) { location.replace('/'); return; }
  sessionStorage.setItem('jauth', AUTH);
  history.replaceState(null, '', '/dashboard');
  boot();
});

function logout() {
  sessionStorage.removeItem('jauth');
  location.replace('/');
}

async function api(method, path, body) {
  var opts = {
    method: method,
    headers: { 'Authorization': 'Basic ' + AUTH, 'Content-Type': 'application/json' }
  };
  if (body) opts.body = JSON.stringify(body);
  try {
    var r = await fetch(path, opts);
    if (r.status === 401) { logout(); return null; }
    return await r.json();
  } catch(e) {
    return null;
  }
}

// Tab switcher
var tabLoaders = {
  home: loadHome, instruct: loadInsts, tasks: loadTasks,
  employees: loadEmp, depts: loadDepts, meetings: loadMeetings,
  social: loadPosts, cashflow: loadCF, reports: loadReports,
  strategy: loadGoals, approvals: loadApprovals, settings: loadSettings
};

function T(name, btn) {
  document.querySelectorAll('.panel').forEach(function(el) { el.classList.remove('on'); });
  document.querySelectorAll('.tab').forEach(function(el) { el.classList.remove('on'); });
  var p = document.getElementById('p-' + name);
  if (p) p.classList.add('on');
  if (btn) btn.classList.add('on');
  if (tabLoaders[name]) tabLoaders[name]();
}

async function boot() {
  var d = await api('GET', '/api/departments');
  if (d) DEPTS = d;
  buildChatSide();
  loadHome();
}

// ── HOME ──────────────────────────────────────────────────────
async function loadHome() {
  var s = await api('GET', '/api/stats');
  if (s) {
    document.getElementById('s-tasks').textContent = s.tasks_total || 0;
    document.getElementById('s-emps').textContent  = s.employees   || 0;
  }
  var hd = document.getElementById('home-depts');
  hd.innerHTML = '';
  DEPTS.forEach(function(d) {
    hd.innerHTML += '<div class="dc" onclick="goChat(\'' + d.id + '\')" style="border-color:' + d.color + '44">' +
      '<div class="dc-icon">' + d.icon + '</div>' +
      '<div class="dc-name">' + d.name + '</div>' +
      '<div class="dc-head">' + d.head + '</div>' +
      '<div class="dc-title">' + d.title + '</div></div>';
  });
  loadSettings();
}

function goChat(id) {
  selectChat(id);
  T('chat', document.querySelector('.tab:nth-child(5)'));
}

// ── SETTINGS / HEALTH ─────────────────────────────────────────
async function loadSettings() {
  var h = await api('GET', '/api/health');
  if (!h) return;
  var rows = [
    { n: 'Claude AI (Anthropic)', ok: h.anthropic, tip: h.anthropic ? 'מחובר' : 'הגדר ANTHROPIC_API_KEY' },
    { n: 'Supabase DB',           ok: h.supabase,  tip: h.supabase  ? 'מחובר' : 'הגדר SUPABASE_URL + SUPABASE_ANON_KEY' },
  ];
  var html = rows.map(function(r) {
    return '<div class="conn-row"><span>' + r.n + '</span>' +
      '<span style="color:' + (r.ok ? 'var(--grn)' : 'var(--red)') + '">' +
      (r.ok ? '✅ ' : '❌ ') + r.tip + '</span></div>';
  }).join('');
  var a = document.getElementById('sys-status');
  var b = document.getElementById('settings-status');
  if (a) a.innerHTML = html;
  if (b) b.innerHTML = html;
}

// ── INSTRUCTIONS ──────────────────────────────────────────────
async function sendInst() {
  var t = document.getElementById('inst-in').value.trim();
  if (!t) return;
  var out = document.getElementById('inst-out');
  var txt = document.getElementById('inst-out-txt');
  out.classList.remove('show');
  txt.innerHTML = '<span class="spin"></span> שולח...';
  out.classList.add('show');
  var r = await api('POST', '/api/instruct', { instruction: t });
  if (r) { txt.textContent = r.ceo_response || ''; loadInsts(); }
}

async function loadInsts() {
  var data = await api('GET', '/api/instructions');
  var el = document.getElementById('inst-hist');
  if (!el) return;
  if (!data || !data.length) { el.innerHTML = empty('אין הוראות'); return; }
  el.innerHTML = data.map(function(i) {
    return '<div class="hi"><div class="hi-meta">' + fmt_date(i.created_at) + ' | ' + (i.status || '') + '</div>' +
      '<strong>' + i.text + '</strong><br><span style="color:var(--mt)">' + i.ceo_response + '</span></div>';
  }).join('');
}

// ── TASKS ─────────────────────────────────────────────────────
async function loadTasks() {
  var data = await api('GET', '/api/tasks');
  var el = document.getElementById('tasks-list');
  if (!el) return;
  if (!data || !data.length) { el.innerHTML = empty('אין משימות'); return; }
  el.innerHTML = data.map(function(t) {
    var dot = t.priority === 'high' ? 'tc-high' : t.priority === 'medium' ? 'tc-med' : 'tc-low';
    var tagCls = (t.status === 'done' || t.status === 'approved') ? 'tag-g' : 'tag-o';
    return '<div class="ti"><div class="tdot ' + dot + '"></div>' +
      '<div class="ti-body"><div class="ti-title">' + t.title + '</div>' +
      '<div class="ti-meta">' + (t.department || '') + '</div></div>' +
      '<span class="tag ' + tagCls + '">' + t.status + '</span></div>';
  }).join('');
}

async function createTask() {
  var title = document.getElementById('t-title').value.trim();
  if (!title) return;
  await api('POST', '/api/tasks', {
    title:       title,
    description: document.getElementById('t-desc').value,
    department:  document.getElementById('t-dept').value,
    priority:    document.getElementById('t-pri').value,
  });
  document.getElementById('t-title').value = '';
  document.getElementById('t-desc').value  = '';
  loadTasks();
}

// ── EMPLOYEES ─────────────────────────────────────────────────
async function loadEmp() {
  var dept = document.getElementById('emp-filter').value;
  var data = await api('GET', '/api/employees' + (dept ? '?dept=' + dept : ''));
  var el = document.getElementById('emp-table');
  if (!el) return;
  if (!data || !data.length) { el.innerHTML = empty('אין עובדים'); return; }
  el.innerHTML = '<table class="etbl"><thead><tr><th>שם</th><th>תפקיד</th><th>מחלקה</th><th>סטטוס</th></tr></thead><tbody>' +
    data.map(function(e) {
      return '<tr><td><div style="display:flex;align-items:center">' +
        '<div class="av">' + e.name.charAt(0) + '</div>' + e.name +
        (e.is_head ? ' <span class="tag" style="margin-right:5px">ראש מחלקה</span>' : '') +
        '</div></td><td>' + e.role + '</td><td>' + e.department + '</td>' +
        '<td><span class="tag tag-g">פעיל</span></td></tr>';
    }).join('') + '</tbody></table>';
}

// ── CHAT ──────────────────────────────────────────────────────
function buildChatSide() {
  var side = document.getElementById('chat-side');
  side.innerHTML = '';
  DEPTS.forEach(function(d) {
    side.innerHTML += '<button class="ca" data-id="' + d.id + '" onclick="selectChat(\'' + d.id + '\')">' +
      '<span class="ca-name">' + d.icon + ' ' + d.name + '</span>' +
      '<span class="ca-role">' + d.head + '</span></button>';
  });
}

function selectChat(id) {
  chatDept = id; chatHist = [];
  document.querySelectorAll('.ca').forEach(function(b) {
    b.classList.toggle('on', b.dataset.id === id);
  });
  var d = DEPTS.find(function(x) { return x.id === id; });
  document.getElementById('chat-hdr').textContent = d ? d.icon + ' ' + d.head + ' – ' + d.name : '';
  document.getElementById('chat-msgs').innerHTML = '';
}

function addMsg(role, text, name) {
  var msgs = document.getElementById('chat-msgs');
  var wrap = document.createElement('div');
  if (name) {
    var n = document.createElement('div');
    n.className = 'msg-name'; n.textContent = name;
    wrap.appendChild(n);
  }
  var m = document.createElement('div');
  m.className = 'msg ' + (role === 'user' ? 'msg-user' : 'msg-ai');
  m.textContent = text;
  wrap.appendChild(m);
  msgs.appendChild(wrap);
  msgs.scrollTop = msgs.scrollHeight;
}

async function sendChat() {
  if (!chatDept) return;
  var inp = document.getElementById('chat-inp');
  var msg = inp.value.trim();
  if (!msg) return;
  inp.value = '';
  chatHist.push({ role: 'user', content: msg });
  addMsg('user', msg, '');
  var sp = document.createElement('div');
  sp.innerHTML = '<span class="spin"></span>';
  document.getElementById('chat-msgs').appendChild(sp);
  var r = await api('POST', '/api/chat/' + chatDept, { message: msg, history: chatHist });
  sp.remove();
  if (r) {
    chatHist.push({ role: 'assistant', content: r.response });
    addMsg('ai', r.response, r.agent);
  }
}

// ── DEPTS ─────────────────────────────────────────────────────
function loadDepts() {
  var el = document.getElementById('depts-grid');
  el.innerHTML = '';
  DEPTS.forEach(function(d) {
    el.innerHTML += '<div class="dc" style="border-color:' + d.color + '44">' +
      '<div class="dc-icon">' + d.icon + '</div>' +
      '<div class="dc-name">' + d.name + '</div>' +
      '<div class="dc-head">' + d.head + '</div>' +
      '<div class="dc-title">' + d.title + '</div></div>';
  });
}

// ── MEETINGS ──────────────────────────────────────────────────
function toggleBtn(btn) { btn.classList.toggle('on'); }

async function createMeeting() {
  var topic = document.getElementById('m-topic').value.trim();
  if (!topic) return;
  var depts = Array.from(document.querySelectorAll('#m-depts .plat-btn.on'))
                   .map(function(b) { return b.dataset.d; });
  var out = document.getElementById('meeting-out');
  var txt = document.getElementById('meeting-out-txt');
  out.classList.remove('show');
  txt.innerHTML = '<span class="spin"></span> מכנס ישיבה...';
  out.classList.add('show');
  var r = await api('POST', '/api/meetings', {
    topic: topic, agenda: document.getElementById('m-agenda').value, departments: depts
  });
  if (r && r.responses) {
    txt.innerHTML = Object.keys(r.responses).map(function(k) {
      return '<div class="hi"><div class="hi-meta">' + k + '</div>' + r.responses[k] + '</div>';
    }).join('');
    loadMeetings();
  }
}

async function loadMeetings() {
  var data = await api('GET', '/api/meetings');
  var el = document.getElementById('meetings-list');
  if (!el) return;
  if (!data || !data.length) { el.innerHTML = empty('אין ישיבות'); return; }
  el.innerHTML = data.map(function(m) {
    return '<div class="hi"><div class="hi-meta">' + fmt_date(m.created_at) + '</div>' +
      '<strong>' + m.topic + '</strong></div>';
  }).join('');
}

// ── SOCIAL ────────────────────────────────────────────────────
function togglePlat(btn) {
  btn.classList.toggle('on');
  var hasWA = Array.from(document.querySelectorAll('.plat-btn[data-p].on'))
                   .some(function(b) { return b.dataset.p === 'whatsapp'; });
  document.getElementById('wa-wrap').style.display = hasWA ? 'block' : 'none';
}

async function genPost() {
  var topic = document.getElementById('soc-topic').value.trim();
  if (!topic) return;
  var out = document.getElementById('post-gen');
  out.classList.remove('show');
  document.getElementById('post-txt').value = '';
  out.classList.add('show');
  var r = await api('POST', '/api/social/generate', { topic: topic });
  if (r) document.getElementById('post-txt').value = r.post || '';
}

async function publishPost() {
  var text = document.getElementById('post-txt').value.trim();
  if (!text) return;
  var plats = Array.from(document.querySelectorAll('.plat-btn[data-p].on'))
                   .map(function(b) { return b.dataset.p; });
  var out = document.getElementById('pub-out');
  out.classList.remove('show');
  document.getElementById('pub-txt').innerHTML = '<span class="spin"></span> מפרסם...';
  out.classList.add('show');
  var r = await api('POST', '/api/social/publish', {
    text:          text,
    platforms:     plats,
    image_url:     document.getElementById('post-img').value.trim(),
    whatsapp_phone: document.getElementById('wa-phone').value.trim(),
  });
  if (r) {
    document.getElementById('pub-txt').innerHTML = Object.keys(r.results || {}).map(function(k) {
      var v = r.results[k];
      return '<div style="margin-bottom:5px"><strong>' + k + ':</strong> ' +
        (v.ok ? '✅ פורסם' : '❌ ' + (v.error || 'שגיאה')) + '</div>';
    }).join('') || 'בוצע';
    loadPosts();
  }
}

async function loadPosts() {
  var data = await api('GET', '/api/social/posts');
  var el = document.getElementById('posts-list');
  if (!el) return;
  if (!data || !data.length) { el.innerHTML = empty('אין פוסטים'); return; }
  el.innerHTML = data.map(function(p) {
    return '<div class="hi"><div class="hi-meta">' + fmt_date(p.created_at) + ' | ' + (p.status || '') + '</div>' +
      (p.text || '').slice(0, 90) + '...</div>';
  }).join('');
}

// ── CASHFLOW ──────────────────────────────────────────────────
async function loadCF() {
  var data = await api('GET', '/api/cashflow');
  if (!data) return;
  var inc = 0, exp = 0;
  data.forEach(function(r) {
    var a = parseFloat(r.amount) || 0;
    if (r.type === 'income') inc += a; else exp += a;
  });
  var fmt = function(n) { return '₪' + n.toLocaleString('he-IL', { maximumFractionDigits: 0 }); };
  document.getElementById('cf-inc').textContent = fmt(inc);
  document.getElementById('cf-exp').textContent = fmt(exp);
  var bal = document.getElementById('cf-bal');
  bal.textContent = fmt(inc - exp);
  bal.style.color = (inc - exp) >= 0 ? 'var(--grn)' : 'var(--red)';
  var tbody = document.getElementById('cf-rows');
  tbody.innerHTML = data.slice(0, 50).map(function(r) {
    var cls = r.type === 'income' ? 'income-c' : 'expense-c';
    var label = r.type === 'income' ? 'הכנסה' : 'הוצאה';
    return '<tr><td>' + (r.date || '').slice(0, 10) + '</td>' +
      '<td>' + (r.description || '') + '</td>' +
      '<td class="' + cls + '">' + label + '</td>' +
      '<td class="' + cls + '">' + fmt(parseFloat(r.amount) || 0) + '</td></tr>';
  }).join('');
}

async function addCF() {
  var desc = document.getElementById('cf-desc').value.trim();
  var amt  = parseFloat(document.getElementById('cf-amt').value);
  if (!desc || isNaN(amt)) return;
  await api('POST', '/api/cashflow', {
    description: desc, amount: amt,
    type:        document.getElementById('cf-type').value,
    category:    document.getElementById('cf-cat').value  || 'כללי',
    date:        document.getElementById('cf-date').value || new Date().toISOString().slice(0, 10),
  });
  document.getElementById('cf-desc').value = '';
  document.getElementById('cf-amt').value  = '';
  loadCF();
}

async function analyzeCF() {
  var out = document.getElementById('cf-anal');
  out.classList.remove('show');
  document.getElementById('cf-anal-txt').innerHTML = '<span class="spin"></span> מנתח...';
  out.classList.add('show');
  var r = await api('POST', '/api/cashflow/analyze');
  if (r) document.getElementById('cf-anal-txt').textContent = r.analysis || '';
}

// ── REPORTS ───────────────────────────────────────────────────
async function genReport() {
  var out = document.getElementById('rep-out');
  out.classList.remove('show');
  document.getElementById('rep-txt').innerHTML = '<span class="spin"></span> יוצר דוח...';
  out.classList.add('show');
  var r = await api('POST', '/api/reports/generate', {
    department: document.getElementById('r-dept').value,
    type:       document.getElementById('r-type').value,
  });
  if (r && r.report) { document.getElementById('rep-txt').textContent = r.report.content || ''; loadReports(); }
}

async function loadReports() {
  var data = await api('GET', '/api/reports');
  var el = document.getElementById('reports-list');
  if (!el) return;
  if (!data || !data.length) { el.innerHTML = empty('אין דוחות'); return; }
  el.innerHTML = data.map(function(r) {
    return '<div class="hi"><div class="hi-meta">' + fmt_date(r.created_at) + '</div>' +
      '<strong>' + r.title + '</strong></div>';
  }).join('');
}

// ── STRATEGY ──────────────────────────────────────────────────
async function setGoals() {
  var goals = document.getElementById('goals-in').value.trim();
  if (!goals) return;
  var out = document.getElementById('goals-out');
  out.classList.remove('show');
  document.getElementById('goals-out-txt').innerHTML = '<span class="spin"></span> יוצר תוכנית...';
  out.classList.add('show');
  var r = await api('POST', '/api/strategy/goals', { goals: goals });
  if (r) { document.getElementById('goals-out-txt').textContent = r.plan || ''; loadGoals(); }
}

async function loadGoals() {
  var data = await api('GET', '/api/strategy/goals');
  var el = document.getElementById('goals-list');
  if (!el) return;
  if (!data || !data.length) { el.innerHTML = empty('אין יעדים'); return; }
  el.innerHTML = data.map(function(g) {
    return '<div class="hi"><div class="hi-meta">' + fmt_date(g.created_at) + '</div>' +
      '<strong>' + g.goals + '</strong></div>';
  }).join('');
}

// ── APPROVALS ─────────────────────────────────────────────────
async function loadApprovals() {
  var data = await api('GET', '/api/approvals');
  var el = document.getElementById('approvals-list');
  if (!el) return;
  if (!data || !data.length) { el.innerHTML = empty('אין פריטים לאישור'); return; }
  el.innerHTML = data.map(function(t) {
    return '<div class="ti"><div class="tdot tc-high"></div>' +
      '<div class="ti-body"><div class="ti-title">' + t.title + '</div>' +
      '<div class="ti-meta">' + (t.department || '') + '</div></div>' +
      '<button class="btn btn-sm btn-green" onclick="approveTask(\'' + t.id + '\')">✅ אשר</button></div>';
  }).join('');
}

async function approveTask(id) {
  await api('POST', '/api/tasks/' + id + '/approve');
  loadApprovals();
}

// ── UTILS ─────────────────────────────────────────────────────
function empty(msg) {
  return '<div style="color:var(--mt);font-size:12px;padding:8px 0">' + msg + '</div>';
}
function fmt_date(s) {
  return s ? s.slice(0, 10) : '';
}
</script>
</body>
</html>"""

# ── Page Routes ───────────────────────────────────────────────

@app.get("/", response_class=HTMLResponse)
async def login_page():
    return HTMLResponse(LOGIN_HTML)

@app.get("/dashboard", response_class=HTMLResponse)
async def dashboard_page():
    return HTMLResponse(DASHBOARD_HTML)

@app.get("/health")
async def public_health():
    return {"status": "ok"}
