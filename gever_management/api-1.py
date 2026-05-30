"""
Jabr AI Company Management System - api.py v3 FIXED
"""
from fastapi import FastAPI, HTTPException, Depends, Request
from fastapi.responses import HTMLResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBasic, HTTPBasicCredentials
import httpx, os, json, secrets
from datetime import datetime
from typing import Optional

# ── Config ────────────────────────────────────────────────────────────────────
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")
# Try both common Railway variable names
SUPABASE_URL      = os.getenv("SUPABASE_URL") or os.getenv("NEXT_PUBLIC_SUPABASE_URL", "")
SUPABASE_KEY      = os.getenv("SUPABASE_ANON_KEY") or os.getenv("SUPABASE_SERVICE_KEY") or os.getenv("NEXT_PUBLIC_SUPABASE_ANON_KEY", "")
COMPANY_NAME      = os.getenv("COMPANY_NAME", "גבר יזמות ייעוץ עסקי והשקעות")
DASHBOARD_USER    = os.getenv("DASHBOARD_USER", "chairman")
DASHBOARD_PASS    = os.getenv("DASHBOARD_PASSWORD", "Prime@2024!")
META_PAGE_TOKEN   = os.getenv("META_PAGE_TOKEN", "")
META_PAGE_ID      = os.getenv("META_PAGE_ID", "")
INSTAGRAM_ACCT_ID = os.getenv("INSTAGRAM_ACCOUNT_ID", "")
TIKTOK_TOKEN      = os.getenv("TIKTOK_ACCESS_TOKEN", "")
WHATSAPP_TOKEN    = os.getenv("WHATSAPP_TOKEN", "")
WHATSAPP_PHONE_ID = os.getenv("WHATSAPP_PHONE_ID", "")

app = FastAPI(title="Jabr Management System")
security = HTTPBasic()
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

# ── Auth ──────────────────────────────────────────────────────────────────────
def verify_auth(credentials: HTTPBasicCredentials = Depends(security)):
    ok_u = secrets.compare_digest(credentials.username.encode(), DASHBOARD_USER.encode())
    ok_p = secrets.compare_digest(credentials.password.encode(), DASHBOARD_PASS.encode())
    if not (ok_u and ok_p):
        raise HTTPException(status_code=401, headers={"WWW-Authenticate": "Basic"})
    return credentials.username

# ── Supabase ──────────────────────────────────────────────────────────────────
SB_HEADERS = lambda: {
    "apikey": SUPABASE_KEY,
    "Authorization": f"Bearer {SUPABASE_KEY}",
    "Content-Type": "application/json",
    "Prefer": "return=representation"
}

async def sb_get(table, params=""):
    if not SUPABASE_URL or not SUPABASE_KEY:
        return []
    url = f"{SUPABASE_URL}/rest/v1/{table}"
    if params:
        url += "?" + params
    try:
        async with httpx.AsyncClient() as c:
            r = await c.get(url, headers=SB_HEADERS(), timeout=15)
            if r.status_code == 200:
                return r.json()
            return []
    except Exception:
        return []

async def sb_insert(table, data):
    if not SUPABASE_URL or not SUPABASE_KEY:
        return {"id": "no-db", **data}
    try:
        async with httpx.AsyncClient() as c:
            r = await c.post(
                f"{SUPABASE_URL}/rest/v1/{table}",
                headers=SB_HEADERS(), json=data, timeout=15)
            res = r.json()
            if isinstance(res, list) and res:
                return res[0]
            return res if isinstance(res, dict) else {"id": "ok"}
    except Exception as e:
        return {"id": "error", "error": str(e)}

async def sb_update(table, row_id, data):
    if not SUPABASE_URL or not SUPABASE_KEY:
        return {}
    try:
        async with httpx.AsyncClient() as c:
            r = await c.patch(
                f"{SUPABASE_URL}/rest/v1/{table}?id=eq.{row_id}",
                headers=SB_HEADERS(), json=data, timeout=15)
            return r.json()
    except Exception:
        return {}

# ── Agents ────────────────────────────────────────────────────────────────────
AGENTS = {
    "ceo":        ("דניאל כהן",    "מנכ\"ל",              "אתה דניאל כהן, מנכ\"ל {co}. אתה מתאם מחלקות, מחלק משימות, מסכם תוצאות. מקצועי ותכליתי."),
    "cfo":        ("מיכאל לוי",   "מנהל כספים (CFO)",    "אתה מיכאל לוי, CFO של {co}. אתה עוסק בתזרים, תקציבים, ניתוח עלויות ודוחות פיננסיים."),
    "marketing":  ("נועה שפירא",  "מנהלת שיווק",         "את נועה שפירא, מנהלת שיווק {co}. אחראית על קמפיינים, תוכן שיווקי ואסטרטגיה."),
    "sales":      ("רון אברהם",   "מנהל מכירות",         "אתה רון אברהם, מנהל מכירות {co}. מנהל לקוחות, מוביל מכירות ומציע הצעות מחיר."),
    "legal":      ("עו\"ד תמר גולן", "יועמ\"ש",           "את עו\"ד תמר גולן, יועמ\"ש {co}. עוסקת בחוזים, רגולציה וייעוץ משפטי עסקי."),
    "cto":        ("אלון בן-דוד", "מנהל טכנולוגיה (CTO)","אתה אלון בן-דוד, CTO של {co}. אחראי על מערכות, פיתוח ותשתיות טכנולוגיות."),
    "content":    ("שיר מזרחי",   "מנהלת תוכן ועיצוב",   "את שיר מזרחי, מנהלת תוכן ועיצוב {co}. יוצרת פוסטים, עיצובים ומצגות."),
    "pr":         ("גיל פרץ",     "מנהל יח\"צ",           "אתה גיל פרץ, מנהל יח\"צ {co}. אחראי על תדמית, קשרי תקשורת ופרסומות."),
    "compliance": ("ד\"ר ענת רוזן","קצינת ציות",          "את ד\"ר ענת רוזן, קצינת ציות {co}. עוסקת בתקנות, בקרת סיכונים ואחריות תאגידית."),
    "hr":         ("יובל כץ",     "מנהל משאבי אנוש",     "אתה יובל כץ, מנהל HR של {co}. אחראי על גיוס, העסקה ורווחת עובדים."),
    "customer":   ("ליאת דביר",   "מנהלת שירות לקוחות",  "את ליאת דביר, מנהלת שירות לקוחות {co}. מטפלת בפניות, תלונות ושביעות רצון."),
    "chairman":   ("יו\"ר",       "יו\"ר דירקטוריון",     "אתה יו\"ר הדירקטוריון של {co}. מנחה אסטרטגיה ומפקח על הנהלה."),
}

DEPT_META = {
    "ceo":        {"name":"מנכ\"ל",              "icon":"👑","color":"#a78bfa"},
    "cfo":        {"name":"כספים",               "icon":"💰","color":"#f5c842"},
    "marketing":  {"name":"שיווק",               "icon":"📣","color":"#f87171"},
    "sales":      {"name":"מכירות",              "icon":"📈","color":"#22d3a0"},
    "legal":      {"name":"משפטי",               "icon":"⚖️","color":"#60a5fa"},
    "cto":        {"name":"טכנולוגיה",           "icon":"💻","color":"#34d399"},
    "content":    {"name":"תוכן ועיצוב",         "icon":"🎨","color":"#fb923c"},
    "pr":         {"name":"יח\"צ",               "icon":"📢","color":"#e879f9"},
    "compliance": {"name":"ציות",                "icon":"🛡️","color":"#94a3b8"},
    "hr":         {"name":"משאבי אנוש",          "icon":"👥","color":"#4ade80"},
    "customer":   {"name":"שירות לקוחות",        "icon":"🎧","color":"#38bdf8"},
}

# 5 employees per department
EMPLOYEES = []
for dept_id, meta in DEPT_META.items():
    ag = AGENTS.get(dept_id)
    if ag:
        EMPLOYEES.append({"id": f"{dept_id}-1", "name": ag[0], "role": ag[1],
                          "department": dept_id, "title": "מנהל מחלקה", "status": "active"})
    emp_names = {
        "ceo":       [("יעל מזרחי","עוזרת מנכ\"ל"),("אסף ברק","מנהל פרויקטים"),("מיה לוין","רכזת הנהלה"),("עומר שלום","אנליסט עסקי")],
        "cfo":       [("דנה כהן","חשבת"),("רועי פלד","אנליסט פיננסי"),("שרה לוי","גזברית"),("אמיר גל","מנהל תקציב")],
        "marketing": [("נדב ביטון","מנהל דיגיטל"),("טל שר","מעצב גרפי"),("יונית אור","כותבת תוכן"),("עידן רז","מנהל SEO")],
        "sales":     [("ליאל דוד","נציג מכירות"),("הילה ים","מנהלת תיקי לקוחות"),("בן גבע","אנליסט מכירות"),("מור שגיא","נציגת מכירות")],
        "legal":     [("ניר אלון","עו\"ד"),("שירה רן","פרלגל"),("גבי מור","יועץ רגולציה"),("לי בן","מזכירת משפטים")],
        "cto":       [("ירון נוי","מפתח Full Stack"),("הדר עם","מהנדסת DevOps"),("ליר שן","מפתח Backend"),("כרמל אל","מעצבת UX")],
        "content":   [("אביב כץ","צלם ועורך"),("ניל שר","מנהל סושיאל"),("עלמא פז","יוצרת תוכן"),("יאיר אף","מנהל YouTube")],
        "pr":        [("הילה דן","דוברת"),("רן שם","יחצ\"ן"),("שי לם","מנהל אירועים"),("מאיה ון","קשרי תקשורת")],
        "compliance":[("ורד נץ","קצינת ציות"),("תמר גן","מבקרת פנים"),("אלי קם","מנהל סיכונים"),("רינה שן","יועצת רגולציה")],
        "hr":        [("נועם בר","מגייסת"),("שלי גז","מנהלת רווחה"),("עמית לז","מנהל הכשרות"),("ציפי רם","יועצת ארגונית")],
        "customer":  [("ליאת דביר","מנהלת שירות"),("דור כהן","נציג שירות"),("עינת שמ","נציגת שירות"),("אלון בר","מנהל תלונות")],
    }
    for name, role in emp_names.get(dept_id, []):
        EMPLOYEES.append({"id": f"{dept_id}-{name}", "name": name, "role": role,
                          "department": dept_id, "title": "עובד", "status": "active"})

async def ask_claude(role: str, message: str, context: str = "") -> str:
    if not ANTHROPIC_API_KEY:
        return f"[{AGENTS.get(role,('AI','',''))[0]}]: מפתח API לא מוגדר ב-Railway"
    name, title, sys_tmpl = AGENTS.get(role, ("AI","עוזר","אתה עוזר מקצועי."))
    system = sys_tmpl.replace("{co}", COMPANY_NAME)
    if context:
        system += f"\n\nהקשר השיחה:\n{context}"
    try:
        async with httpx.AsyncClient() as c:
            r = await c.post("https://api.anthropic.com/v1/messages",
                headers={"x-api-key": ANTHROPIC_API_KEY,
                         "anthropic-version": "2023-06-01",
                         "content-type": "application/json"},
                json={"model": "claude-opus-4-6", "max_tokens": 1500,
                      "system": system, "messages": [{"role":"user","content":message}]},
                timeout=40)
            if r.status_code == 200:
                return r.json()["content"][0]["text"]
            return f"שגיאת Claude API {r.status_code}"
    except Exception as e:
        return f"שגיאת חיבור: {str(e)}"

# ── Social Media ──────────────────────────────────────────────────────────────
async def publish_facebook(text, image_url=""):
    if not META_PAGE_TOKEN or not META_PAGE_ID:
        return {"ok": False, "error": "חסר META_PAGE_TOKEN ו-META_PAGE_ID ב-Railway"}
    async with httpx.AsyncClient() as c:
        data = {"message": text, "access_token": META_PAGE_TOKEN}
        if image_url:
            r = await c.post(f"https://graph.facebook.com/v19.0/{META_PAGE_ID}/photos",
                             data={**data, "url": image_url}, timeout=20)
        else:
            r = await c.post(f"https://graph.facebook.com/v19.0/{META_PAGE_ID}/feed",
                             data=data, timeout=20)
        res = r.json()
        return {"ok": "id" in res, "post_id": res.get("id"), "error": res.get("error",{}).get("message")}

async def publish_instagram(caption, image_url):
    if not META_PAGE_TOKEN or not INSTAGRAM_ACCT_ID:
        return {"ok": False, "error": "חסר INSTAGRAM_ACCOUNT_ID ב-Railway"}
    if not image_url:
        return {"ok": False, "error": "אינסטגרם דורש תמונה (image_url)"}
    async with httpx.AsyncClient() as c:
        r1 = await c.post(f"https://graph.facebook.com/v19.0/{INSTAGRAM_ACCT_ID}/media",
            data={"image_url": image_url, "caption": caption, "access_token": META_PAGE_TOKEN}, timeout=20)
        media_id = r1.json().get("id")
        if not media_id:
            return {"ok": False, "error": r1.json().get("error",{}).get("message","שגיאה")}
        r2 = await c.post(f"https://graph.facebook.com/v19.0/{INSTAGRAM_ACCT_ID}/media_publish",
            data={"creation_id": media_id, "access_token": META_PAGE_TOKEN}, timeout=20)
        res = r2.json()
        return {"ok": "id" in res, "post_id": res.get("id"), "error": res.get("error",{}).get("message")}

async def send_whatsapp(phone, message):
    if not WHATSAPP_TOKEN or not WHATSAPP_PHONE_ID:
        return {"ok": False, "error": "חסר WHATSAPP_TOKEN ב-Railway"}
    async with httpx.AsyncClient() as c:
        r = await c.post(
            f"https://graph.facebook.com/v19.0/{WHATSAPP_PHONE_ID}/messages",
            headers={"Authorization": f"Bearer {WHATSAPP_TOKEN}", "Content-Type": "application/json"},
            json={"messaging_product":"whatsapp","to":phone,
                  "type":"text","text":{"body":message}}, timeout=20)
        res = r.json()
        return {"ok": "messages" in res, "error": res.get("error",{}).get("message")}

# ── API Routes ────────────────────────────────────────────────────────────────
@app.get("/api/health")
async def health():
    return {"status":"ok","anthropic":bool(ANTHROPIC_API_KEY),"supabase":bool(SUPABASE_URL and SUPABASE_KEY),
            "facebook":bool(META_PAGE_TOKEN),"instagram":bool(INSTAGRAM_ACCT_ID),
            "tiktok":bool(TIKTOK_TOKEN),"whatsapp":bool(WHATSAPP_TOKEN)}

@app.get("/api/stats")
async def get_stats(user=Depends(verify_auth)):
    tasks   = await sb_get("tasks","select=count")
    done    = await sb_get("tasks","select=count&status=eq.done")
    inprog  = await sb_get("tasks","select=count&status=eq.in_progress")
    pending = await sb_get("tasks","select=count&status=eq.pending_approval")
    def cnt(x): return x[0].get("count",0) if isinstance(x,list) and x and isinstance(x[0],dict) else 0
    return {"tasks_total":cnt(tasks),"tasks_done":cnt(done),"tasks_inprog":cnt(inprog),
            "tasks_pending":cnt(pending),"departments":len(DEPT_META),"employees":len(EMPLOYEES)}

@app.get("/api/departments")
async def get_departments(user=Depends(verify_auth)):
    return [{"id":k,"name":v["name"],"icon":v["icon"],"color":v["color"],
             "head":AGENTS[k][0],"title":AGENTS[k][1]} for k,v in DEPT_META.items()]

@app.get("/api/employees")
async def get_employees(dept: Optional[str]=None, user=Depends(verify_auth)):
    if dept:
        return [e for e in EMPLOYEES if e["department"]==dept]
    return EMPLOYEES

@app.get("/api/tasks")
async def get_tasks(status: Optional[str]=None, dept: Optional[str]=None, user=Depends(verify_auth)):
    q = "order=created_at.desc&limit=50"
    if status: q += f"&status=eq.{status}"
    if dept:   q += f"&department=eq.{dept}"
    return await sb_get("tasks", q)

@app.post("/api/tasks")
async def create_task(req: Request, user=Depends(verify_auth)):
    body = await req.json()
    if not body.get("title","").strip():
        raise HTTPException(400,"נא להזין כותרת")
    row = {"title":body.get("title"),"description":body.get("description",""),
           "department":body.get("department","ceo"),"priority":body.get("priority","medium"),
           "status":"pending","created_by":user,"created_at":datetime.utcnow().isoformat()}
    return await sb_insert("tasks", row)

@app.post("/api/tasks/{tid}/approve")
async def approve_task(tid: str, user=Depends(verify_auth)):
    await sb_update("tasks", tid, {"status":"approved","approved_at":datetime.utcnow().isoformat()})
    return {"ok":True}

@app.post("/api/instruct")
async def send_instruction(req: Request, user=Depends(verify_auth)):
    body = await req.json()
    inst = body.get("instruction","").strip()
    if not inst: raise HTTPException(400,"נא לכתוב הוראה")
    ceo_resp = await ask_claude("ceo",
        f'קיבלת הוראה/יעד מיו"ר הדירקטוריון:\n"{inst}"\n\n'
        '1. נתח את ההוראה\n2. אילו מחלקות צריכות לטפל?\n3. תוכנית פעולה מפורטת\n4. ציר זמן')
    await sb_insert("instructions",{"text":inst,"ceo_response":ceo_resp,
                                    "status":"processing","created_at":datetime.utcnow().isoformat()})
    return {"instruction":inst,"ceo_response":ceo_resp}

@app.get("/api/instructions")
async def get_instructions(user=Depends(verify_auth)):
    return await sb_get("instructions","order=created_at.desc&limit=20")

@app.post("/api/chat/{dept}")
async def dept_chat(dept: str, req: Request, user=Depends(verify_auth)):
    body = await req.json()
    msg  = body.get("message","")
    hist = body.get("history",[])
    ctx  = "\n".join([f"{m['role']}: {m['content']}" for m in hist[-8:]])
    resp = await ask_claude(dept, msg, ctx)
    await sb_insert("chat_messages",{"department":dept,"user_message":msg,
                                     "ai_response":resp,"created_at":datetime.utcnow().isoformat()})
    ag = AGENTS.get(dept,("AI","",""))
    return {"response":resp,"agent":ag[0],"title":ag[1]}

@app.post("/api/meetings")
async def create_meeting(req: Request, user=Depends(verify_auth)):
    body  = await req.json()
    topic = body.get("topic","")
    agenda= body.get("agenda","")
    depts = body.get("departments", list(DEPT_META.keys())[:4])
    responses = {}
    for d in depts[:6]:
        responses[d] = await ask_claude(d,
            f'ישיבת הנהלה – נושא: {topic}\nסדר יום: {agenda}\nמה עמדתך ותרומתך?')
    meeting = {"topic":topic,"agenda":agenda,
               "responses":json.dumps(responses,ensure_ascii=False),
               "status":"completed","created_at":datetime.utcnow().isoformat()}
    result = await sb_insert("meetings",meeting)
    return {"meeting":result,"responses":responses}

@app.get("/api/meetings")
async def get_meetings(user=Depends(verify_auth)):
    return await sb_get("meetings","order=created_at.desc&limit=20")

@app.post("/api/reports/generate")
async def generate_report(req: Request, user=Depends(verify_auth)):
    body  = await req.json()
    dept  = body.get("department","ceo")
    rtype = body.get("type","weekly")
    dname = DEPT_META.get(dept,{}).get("name",dept)
    content = await ask_claude(dept,
        f'צור דוח {rtype} מקיף למחלקת {dname}. כלול: סיכום פעילות, הישגים, אתגרים, תוכנית לתקופה הבאה, המלצות.')
    report = {"title":f'דוח {rtype} – {dname}',"department":dept,"content":content,
              "type":rtype,"created_at":datetime.utcnow().isoformat()}
    await sb_insert("reports",report)
    return {"report":report}

@app.get("/api/reports")
async def get_reports(user=Depends(verify_auth)):
    return await sb_get("reports","order=created_at.desc&limit=20")

@app.get("/api/approvals")
async def get_approvals(user=Depends(verify_auth)):
    return await sb_get("tasks","status=eq.pending_approval&order=created_at.desc")

@app.post("/api/strategy/goals")
async def set_goals(req: Request, user=Depends(verify_auth)):
    body  = await req.json()
    goals = body.get("goals","").strip()
    if not goals: raise HTTPException(400,"נא להזין יעדים")
    plan = await ask_claude("ceo",
        f'יו"ר הציב יעדים אסטרטגיים:\n{goals}\n\n'
        'צור תוכנית אסטרטגית מפורטת: 1.פירוט יעדים למחלקות 2.לוח זמנים 3.KPIs 4.סיכונים 5.תקציב מוצע')
    await sb_insert("strategic_goals",{"goals":goals,"plan":plan,
                                       "status":"active","created_at":datetime.utcnow().isoformat()})
    return {"goals":goals,"plan":plan}

@app.get("/api/strategy/goals")
async def get_goals(user=Depends(verify_auth)):
    return await sb_get("strategic_goals","order=created_at.desc&limit=10")

@app.get("/api/cashflow")
async def get_cashflow(user=Depends(verify_auth)):
    return await sb_get("cashflow","order=date.desc&limit=200")

@app.post("/api/cashflow")
async def add_cashflow(req: Request, user=Depends(verify_auth)):
    body = await req.json()
    try:
        amount = float(body.get("amount",0))
    except (ValueError, TypeError):
        raise HTTPException(400,"סכום לא תקין")
    row = {"date":body.get("date",datetime.utcnow().date().isoformat()),
           "description":body.get("description",""),"amount":amount,
           "type":body.get("type","income"),"category":body.get("category","כללי"),
           "client_id":body.get("client_id",""),"created_at":datetime.utcnow().isoformat()}
    return await sb_insert("cashflow",row)

@app.post("/api/cashflow/analyze")
async def analyze_cashflow(user=Depends(verify_auth)):
    rows = await sb_get("cashflow","order=date.desc&limit=100")
    if not rows:
        return {"analysis":"אין נתוני תזרים מזומנים עדיין. הוסף הכנסות והוצאות כדי לקבל ניתוח.","rows":[]}
    total_in  = sum(float(r.get("amount",0)) for r in rows if r.get("type")=="income")
    total_out = sum(float(r.get("amount",0)) for r in rows if r.get("type")=="expense")
    data_str  = json.dumps(rows[:30],ensure_ascii=False,default=str)
    analysis  = await ask_claude("cfo",
        f'נתוני תזרים מזומנים:\n{data_str}\n\n'
        f'סיכום: הכנסות={total_in:,.0f}₪, הוצאות={total_out:,.0f}₪, יתרה={total_in-total_out:,.0f}₪\n\n'
        'נתח את התזרים, זהה מגמות, המלץ על פעולות לשיפור, והצג תחזית.')
    return {"analysis":analysis,"rows":rows,"summary":{"income":total_in,"expense":total_out,"balance":total_in-total_out}}

@app.post("/api/social/generate")
async def generate_post(req: Request, user=Depends(verify_auth)):
    body  = await req.json()
    topic = body.get("topic","")
    dept  = body.get("dept","content")
    post  = await ask_claude(dept,
        f'כתוב פוסט מקצועי ומושך לסושיאל מדיה בנושא: {topic}\n'
        'כלול: כותרת מושכת, גוף 2-3 משפטים, קריאה לפעולה, 5 האשטגים.')
    return {"post":post}

@app.post("/api/social/publish")
async def social_publish(req: Request, user=Depends(verify_auth)):
    body      = await req.json()
    text      = body.get("text","")
    image_url = body.get("image_url","")
    platforms = body.get("platforms",[])
    if not text: raise HTTPException(400,"נא לכתוב תוכן")
    results = {}
    if "facebook"  in platforms: results["facebook"]  = await publish_facebook(text,image_url)
    if "instagram" in platforms: results["instagram"] = await publish_instagram(text,image_url)
    if "whatsapp"  in platforms:
        phone = body.get("whatsapp_phone","")
        results["whatsapp"] = await send_whatsapp(phone,text) if phone else {"ok":False,"error":"נא להזין מספר טלפון"}
    await sb_insert("social_posts",{"text":text,"image_url":image_url,
        "platforms":json.dumps(platforms),"results":json.dumps(results,ensure_ascii=False),
        "status":"published" if any(r.get("ok") for r in results.values()) else "failed",
        "created_at":datetime.utcnow().isoformat()})
    return {"text":text,"results":results}

@app.get("/api/social/posts")
async def get_social_posts(user=Depends(verify_auth)):
    return await sb_get("social_posts","order=created_at.desc&limit=30")


# ── Login HTML ────────────────────────────────────────────────────────────────
LOGIN_HTML = '''<!DOCTYPE html>
<html lang="he" dir="rtl">
<head>
<meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>גבר – כניסה</title>
<style>
@import url('https://fonts.googleapis.com/css2?family=Heebo:wght@300;400;600;700;800&display=swap');
*{box-sizing:border-box;margin:0;padding:0}
body{font-family:'Heebo',sans-serif;min-height:100vh;display:flex;align-items:center;justify-content:center;
  background:radial-gradient(ellipse at 20% 50%,#1a0a4a,#0d1a3a 40%,#060b18);overflow:hidden}
.stars{position:fixed;inset:0;pointer-events:none;z-index:0}
.star{position:absolute;border-radius:50%;background:#fff;animation:tw var(--d) ease-in-out infinite}
@keyframes tw{0%,100%{opacity:.1}50%{opacity:.7}}
.card{position:relative;z-index:1;background:rgba(22,25,33,.9);backdrop-filter:blur(20px);
  border:1px solid rgba(167,139,250,.2);border-radius:24px;padding:44px 36px;
  width:100%;max-width:400px;box-shadow:0 0 80px rgba(108,99,255,.2)}
.logo{text-align:center;margin-bottom:28px}
.logo-icon{width:68px;height:68px;background:linear-gradient(135deg,#6c63ff,#a78bfa);border-radius:18px;
  display:inline-flex;align-items:center;justify-content:center;font-size:32px;margin-bottom:12px;
  box-shadow:0 8px 32px rgba(108,99,255,.4)}
.logo-name{font-size:20px;font-weight:800;color:#e8eaf0}
.logo-sub{font-size:12px;color:#8892a4;margin-top:3px}
.field{margin-bottom:16px}
label{display:block;font-size:11px;color:#8892a4;margin-bottom:6px;font-weight:600;text-transform:uppercase;letter-spacing:.5px}
input{width:100%;background:rgba(13,15,20,.7);border:1px solid rgba(167,139,250,.2);border-radius:10px;
  color:#e8eaf0;font-family:'Heebo',sans-serif;font-size:14px;padding:12px 14px;direction:rtl;outline:none;transition:border-color .2s}
input:focus{border-color:#6c63ff;box-shadow:0 0 0 3px rgba(108,99,255,.12)}
.btn{width:100%;background:linear-gradient(135deg,#6c63ff,#8b5cf6);color:#fff;border:none;
  border-radius:10px;font-family:'Heebo',sans-serif;font-size:15px;font-weight:700;
  padding:14px;cursor:pointer;margin-top:6px;box-shadow:0 4px 20px rgba(108,99,255,.4);transition:opacity .2s}
.btn:hover{opacity:.88}
.err{background:rgba(248,113,113,.1);border:1px solid rgba(248,113,113,.3);border-radius:8px;
  padding:9px 12px;font-size:12px;color:#f87171;margin-top:10px;display:none}
.badges{display:flex;gap:6px;justify-content:center;flex-wrap:wrap;margin-top:18px}
.badge{background:rgba(108,99,255,.1);border:1px solid rgba(108,99,255,.2);border-radius:20px;
  padding:4px 10px;font-size:11px;color:#a78bfa}
</style>
</head>
<body>
<div class="stars" id="st"></div>
<div class="card">
  <div class="logo">
    <div class="logo-icon">🏢</div>
    <div class="logo-name">גבר יזמות ייעוץ עסקי</div>
    <div class="logo-sub">AI Company Management System</div>
  </div>
  <div class="field"><label>שם משתמש</label><input id="u" type="text" placeholder="chairman" autocomplete="username"></div>
  <div class="field"><label>סיסמה</label><input id="p" type="password" placeholder="••••••••" onkeydown="if(event.key==='Enter')login()"></div>
  <button class="btn" id="btn" onclick="login()">🔐 כניסה למערכת</button>
  <div class="err" id="err">שם משתמש או סיסמה שגויים</div>
  <div class="badges"><span class="badge">👑 11 מנהלי AI</span><span class="badge">🤖 Claude</span><span class="badge">🔒 מאובטח</span></div>
</div>
<script>
const s=document.getElementById('st');
for(let i=0;i<70;i++){const d=document.createElement('div');d.className='star';
  const z=Math.random()*2.5+.5;
  d.style.cssText=`width:${z}px;height:${z}px;top:${Math.random()*100}%;left:${Math.random()*100}%;--d:${Math.random()*3+2}s;animation-delay:${Math.random()*3}s`;
  s.appendChild(d);}
async function login(){
  const u=document.getElementById('u').value,p=document.getElementById('p').value;
  if(!u||!p)return;
  const btn=document.getElementById('btn');btn.textContent='...מתחבר';
  document.getElementById('err').style.display='none';
  const r=await fetch('/api/health',{headers:{Authorization:'Basic '+btoa(u+':'+p)}});
  if(r.ok){sessionStorage.setItem('jabr_auth',btoa(u+':'+p));window.location.href='/dashboard';}
  else{document.getElementById('err').style.display='block';btn.textContent='🔐 כניסה למערכת';}
}
</script>
</body></html>'''


# ── Dashboard HTML ────────────────────────────────────────────────────────────
DASHBOARD_HTML = '''<!DOCTYPE html>
<html lang="he" dir="rtl">
<head>
<meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>גבר – מערכת ניהול AI</title>
<style>
@import url('https://fonts.googleapis.com/css2?family=Heebo:wght@300;400;500;600;700;800&display=swap');
:root{--bg:#0d0f14;--sur:#161921;--card:#1c2030;--bdr:#252a3a;
  --ac:#6c63ff;--ac2:#a78bfa;--gld:#f5c842;--grn:#22d3a0;--red:#f87171;
  --org:#fb923c;--blue:#60a5fa;--pink:#e879f9;--tx:#e8eaf0;--mt:#8892a4;--r:12px}
*{box-sizing:border-box;margin:0;padding:0}
body{font-family:'Heebo',sans-serif;background:var(--bg);color:var(--tx);min-height:100vh}

/* Header */
.hdr{background:linear-gradient(135deg,#1a0a4a,#0d1a3a,#0a1520);border-bottom:1px solid var(--bdr);
  padding:0 20px;display:flex;align-items:center;justify-content:space-between;height:60px;
  position:sticky;top:0;z-index:100}
.hdr-l{display:flex;align-items:center;gap:10px}
.hdr-ic{width:36px;height:36px;background:linear-gradient(135deg,var(--ac),var(--ac2));
  border-radius:9px;display:flex;align-items:center;justify-content:center;font-size:18px}
.hdr-t{font-weight:700;font-size:15px}.hdr-s{font-size:10px;color:var(--mt)}
.bon{background:rgba(34,211,160,.15);color:var(--grn);border:1px solid rgba(34,211,160,.3);
  border-radius:20px;padding:3px 10px;font-size:11px}
.bex{background:rgba(248,113,113,.15);color:var(--red);border:1px solid rgba(248,113,113,.3);
  border-radius:8px;padding:5px 12px;font-size:12px;cursor:pointer;font-family:inherit}

/* Tabs */
.tabs{background:var(--sur);border-bottom:1px solid var(--bdr);padding:0 20px;
  display:flex;gap:1px;overflow-x:auto;scrollbar-width:none}
.tabs::-webkit-scrollbar{display:none}
.tb{background:none;border:none;color:var(--mt);font-family:inherit;font-size:12px;
  font-weight:500;padding:12px 12px;cursor:pointer;white-space:nowrap;
  border-bottom:2px solid transparent;transition:all .2s;display:flex;align-items:center;gap:4px}
.tb:hover{color:var(--tx)}.tb.active{color:var(--ac2);border-bottom-color:var(--ac2)}

/* Wrap */
.wrap{padding:20px;max-width:1400px;margin:0 auto}
.panel{display:none}.panel.active{display:block}

/* Stats */
.stats{display:grid;grid-template-columns:repeat(auto-fit,minmax(120px,1fr));gap:10px;margin-bottom:18px}
.stat{background:var(--card);border:1px solid var(--bdr);border-radius:var(--r);padding:16px 12px;text-align:center}
.sn{font-size:28px;font-weight:800;color:var(--ac2);line-height:1;margin-bottom:4px}
.sl{font-size:11px;color:var(--mt)}

/* Card */
.card{background:var(--card);border:1px solid var(--bdr);border-radius:var(--r);padding:18px;margin-bottom:14px}
.ct{font-size:14px;font-weight:600;margin-bottom:14px;display:flex;align-items:center;gap:7px}

/* Inputs */
textarea,input[type=text],select{width:100%;background:var(--sur);border:1px solid var(--bdr);
  border-radius:8px;color:var(--tx);font-family:inherit;font-size:13px;padding:10px 12px;
  direction:rtl;outline:none;transition:border-color .2s}
textarea:focus,input[type=text]:focus,select:focus{border-color:var(--ac)}
textarea{resize:vertical;min-height:80px}
select option{background:var(--card)}
label{display:block;font-size:11px;color:var(--mt);margin-bottom:5px;font-weight:500}
.fg{margin-bottom:12px}
.fr{display:grid;grid-template-columns:1fr 1fr;gap:10px;margin-bottom:10px}

/* Buttons */
.btn{display:inline-flex;align-items:center;gap:5px;background:linear-gradient(135deg,var(--ac),#8b5cf6);
  color:#fff;border:none;border-radius:8px;padding:9px 16px;font-family:inherit;
  font-size:13px;font-weight:600;cursor:pointer;transition:opacity .2s}
.btn:hover{opacity:.85}.btn:disabled{opacity:.5;cursor:not-allowed}
.bsm{padding:6px 12px;font-size:12px}
.bg{background:linear-gradient(135deg,#059669,var(--grn))}
.bo{background:none;border:1px solid var(--bdr);color:var(--tx)}
.bo:hover{border-color:var(--ac);color:var(--ac2)}

/* Response box */
.rb{background:var(--sur);border:1px solid var(--bdr);border-radius:8px;
  padding:14px;margin-top:12px;font-size:13px;line-height:1.7;white-space:pre-wrap;display:none}
.rb.show{display:block}
.rl{font-size:10px;color:var(--ac2);font-weight:700;margin-bottom:7px;text-transform:uppercase;letter-spacing:.5px}

/* Dept grid */
.dg{display:grid;grid-template-columns:repeat(auto-fill,minmax(145px,1fr));gap:9px}
.dc{background:var(--sur);border:1px solid var(--bdr);border-radius:var(--r);
  padding:13px;cursor:pointer;transition:all .2s;text-align:center}
.dc:hover{transform:translateY(-2px);border-color:var(--ac);background:rgba(108,99,255,.07)}
.di{font-size:24px;margin-bottom:6px}.dn{font-size:12px;font-weight:700}
.dh{font-size:10px;color:var(--mt);margin-top:2px}.dt{font-size:10px;color:var(--ac2);margin-top:1px}

/* Chat - IMPROVED */
.chat-wrap{display:grid;grid-template-columns:170px 1fr;gap:12px;height:620px}
.chat-side{background:var(--sur);border:1px solid var(--bdr);border-radius:var(--r);overflow-y:auto}
.ca{width:100%;background:none;border:none;border-bottom:1px solid var(--bdr);
  color:var(--tx);font-family:inherit;font-size:11px;padding:9px 10px;cursor:pointer;
  text-align:right;transition:background .15s;display:flex;flex-direction:column;align-items:flex-end;gap:1px}
.ca:hover{background:rgba(108,99,255,.08)}.ca.active{background:rgba(167,139,250,.12);color:var(--ac2)}
.ca-n{font-weight:700;font-size:12px}.ca-r{font-size:10px;color:var(--mt)}
.chat-main{background:var(--sur);border:1px solid var(--bdr);border-radius:var(--r);
  display:flex;flex-direction:column;overflow:hidden}
.chat-hdr{padding:11px 14px;border-bottom:1px solid var(--bdr);font-weight:700;font-size:13px;
  display:flex;align-items:center;gap:7px;flex-shrink:0}
.chat-msgs{flex:1;overflow-y:auto;padding:12px;display:flex;flex-direction:column;gap:8px;
  min-height:0}
.msg{padding:9px 13px;border-radius:12px;font-size:13px;line-height:1.65;
  max-width:88%;word-wrap:break-word}
.mu{background:linear-gradient(135deg,var(--ac),#8b5cf6);align-self:flex-start;
  border-radius:12px 12px 12px 3px}
.ma{background:var(--card);border:1px solid var(--bdr);align-self:flex-end;
  border-radius:12px 12px 3px 12px}
.mn{font-size:10px;color:var(--ac2);font-weight:700;margin-bottom:3px}
.chat-in{padding:10px;border-top:1px solid var(--bdr);display:flex;gap:7px;flex-shrink:0}
.ci{flex:1;background:var(--card);border:1px solid var(--bdr);border-radius:8px;
  color:var(--tx);font-family:inherit;font-size:13px;padding:9px 12px;
  direction:rtl;outline:none;resize:none;height:38px;overflow:hidden}
.ci:focus{border-color:var(--ac)}

/* Task items */
.ti{background:var(--sur);border:1px solid var(--bdr);border-radius:9px;
  padding:11px 13px;margin-bottom:7px;display:flex;align-items:center;gap:9px}
.tdot{width:7px;height:7px;border-radius:50%;flex-shrink:0}
.dp{background:var(--org)}.di2{background:var(--ac2)}.dd{background:var(--grn)}.da{background:var(--gld)}
.ti-i{flex:1;min-width:0}
.ti-t{font-size:13px;font-weight:600;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.ti-m{font-size:10px;color:var(--mt);margin-top:2px}
.tag{background:rgba(108,99,255,.15);color:var(--ac2);border:1px solid rgba(108,99,255,.3);
  border-radius:5px;padding:2px 7px;font-size:10px;white-space:nowrap;flex-shrink:0}
.tg{background:rgba(34,211,160,.15);color:var(--grn);border-color:rgba(34,211,160,.3)}
.to{background:rgba(251,146,60,.15);color:var(--org);border-color:rgba(251,146,60,.3)}
.ty{background:rgba(245,200,66,.15);color:var(--gld);border-color:rgba(245,200,66,.3)}

/* Employees table */
.etable{width:100%;border-collapse:collapse;font-size:12px}
.etable th{background:var(--sur);padding:9px 10px;text-align:right;font-weight:600;
  color:var(--mt);font-size:10px;border-bottom:1px solid var(--bdr)}
.etable td{padding:9px 10px;border-bottom:1px solid rgba(37,42,58,.4)}
.etable tr:hover td{background:rgba(108,99,255,.03)}
.eavatar{width:28px;height:28px;border-radius:50%;background:linear-gradient(135deg,var(--ac),var(--ac2));
  display:inline-flex;align-items:center;justify-content:center;font-size:12px;font-weight:700;
  flex-shrink:0;margin-left:8px}

/* Social */
.plat-row{display:flex;gap:7px;flex-wrap:wrap;margin-bottom:12px}
.pb{background:var(--sur);border:1px solid var(--bdr);border-radius:9px;padding:9px 14px;
  cursor:pointer;font-family:inherit;font-size:12px;color:var(--mt);
  transition:all .2s;display:flex;align-items:center;gap:6px}
.pb.sel{border-color:var(--ac2);color:var(--ac2);background:rgba(167,139,250,.08)}

/* Cashflow */
.cf-s{display:grid;grid-template-columns:repeat(3,1fr);gap:10px;margin-bottom:14px}
.cfs{background:var(--sur);border:1px solid var(--bdr);border-radius:9px;padding:12px;text-align:center}
.cfn{font-size:20px;font-weight:800;margin-bottom:3px}
.cfl{font-size:10px;color:var(--mt)}
.cft{width:100%;border-collapse:collapse;font-size:12px}
.cft th{background:var(--sur);padding:8px 10px;text-align:right;font-weight:600;
  color:var(--mt);font-size:10px;border-bottom:1px solid var(--bdr)}
.cft td{padding:8px 10px;border-bottom:1px solid rgba(37,42,58,.3)}
.cin{color:var(--grn)}.cout{color:var(--red)}

/* Meeting dept response */
.dr{border-right:3px solid var(--ac);padding:7px 10px;margin-bottom:6px;
  background:rgba(108,99,255,.04);border-radius:0 6px 6px 0;font-size:12px;line-height:1.6}
.drn{font-size:10px;color:var(--ac2);font-weight:700;margin-bottom:3px}

/* Spinner */
.sp{display:inline-block;width:14px;height:14px;border:2px solid rgba(167,139,250,.3);
  border-top-color:var(--ac2);border-radius:50%;animation:spin .7s linear infinite}
@keyframes spin{to{transform:rotate(360deg)}}

/* Priority */
.pu{color:var(--red);font-weight:700}.ph{color:var(--org)}.pm{color:var(--ac2)}.pl{color:var(--mt)}

/* Connections status */
.conn-row{padding:10px 12px;background:var(--sur);border:1px solid var(--bdr);border-radius:8px;
  display:flex;justify-content:space-between;align-items:center;margin-bottom:7px;font-size:13px}

@media(max-width:768px){
  .wrap{padding:12px}.fr{grid-template-columns:1fr}
  .chat-wrap{grid-template-columns:1fr;height:auto}
  .chat-side{display:flex;overflow-x:auto;height:50px;border-radius:9px}
  .ca{flex-direction:row;border-bottom:none;border-left:1px solid var(--bdr);
    white-space:nowrap;flex-shrink:0;padding:7px 10px}
  .ca-r{display:none}
  .chat-main{height:460px}.dg{grid-template-columns:repeat(3,1fr)}
  .cf-s{grid-template-columns:1fr}
  .stats{grid-template-columns:repeat(3,1fr)}
}
</style>
</head>
<body>

<div class="hdr">
  <div class="hdr-l">
    <div class="hdr-ic">🏢</div>
    <div><div class="hdr-t">גבר יזמות ייעוץ עסקי</div><div class="hdr-s">AI Company Management System</div></div>
  </div>
  <div style="display:flex;align-items:center;gap:8px">
    <div class="bon">● מחובר</div>
    <button class="bex" onclick="logout()">↩ יציאה</button>
  </div>
</div>

<div class="tabs">
  <button class="tb active" onclick="T('home',this)">🏠 ראשי</button>
  <button class="tb" onclick="T('instruct',this)">📋 הוראות</button>
  <button class="tb" onclick="T('tasks',this)">⚙️ משימות</button>
  <button class="tb" onclick="T('employees',this)">👥 עובדים</button>
  <button class="tb" onclick="T('chat',this)">💬 צ׳אט</button>
  <button class="tb" onclick="T('depts',this)">🏬 מחלקות</button>
  <button class="tb" onclick="T('meetings',this)">📅 ישיבות</button>
  <button class="tb" onclick="T('social',this)">📱 סושיאל</button>
  <button class="tb" onclick="T('cashflow',this)">💰 תזרים</button>
  <button class="tb" onclick="T('reports',this)">📊 דוחות</button>
  <button class="tb" onclick="T('strategy',this)">🎯 יעדים</button>
  <button class="tb" onclick="T('approvals',this)">👁 אישורים</button>
  <button class="tb" onclick="T('settings',this)">⚙ הגדרות</button>
</div>

<div class="wrap">

<!-- HOME -->
<div class="panel active" id="panel-home">
  <div class="stats">
    <div class="stat"><div class="sn" id="s-d">—</div><div class="sl">מחלקות</div></div>
    <div class="stat"><div class="sn" id="s-e">—</div><div class="sl">עובדים AI</div></div>
    <div class="stat"><div class="sn" id="s-t">—</div><div class="sl">משימות</div></div>
    <div class="stat"><div class="sn" id="s-dn">—</div><div class="sl">הושלמו</div></div>
    <div class="stat"><div class="sn" id="s-ip">—</div><div class="sl">בעבודה</div></div>
    <div class="stat"><div class="sn" id="s-pa">—</div><div class="sl">לאישור</div></div>
  </div>
  <div class="card">
    <div class="ct">📋 שלח יעד או הוראה לצוות</div>
    <textarea id="homeInst" placeholder="לדוגמה: השבוע נפרסם 5 פוסטים לקמפיין פסח. תכין תוכנית."></textarea>
    <div style="margin-top:9px;display:flex;gap:8px;align-items:center">
      <button class="btn" onclick="sendInst()" id="bHI">🚀 שלח למנכ&quot;ל</button>
      <span id="lHI" style="display:none"><span class="sp"></span> מטפל...</span>
    </div>
    <div class="rb" id="rHI"><div class="rl">👑 דניאל כהן – מנכ&quot;ל</div><div id="tHI"></div></div>
  </div>
  <div class="card">
    <div class="ct">👁 ממתינים לאישורך</div>
    <div id="homeAppr"><div style="color:var(--mt);font-size:13px">אין תוצרים ממתינים</div></div>
  </div>
  <div class="card">
    <div class="ct">🏬 מחלקות החברה</div>
    <div class="dg" id="homeDepts"></div>
  </div>
</div>

<!-- INSTRUCT -->
<div class="panel" id="panel-instruct">
  <div class="card">
    <div class="ct">📋 שליחת הוראה / יעד למנכ&quot;ל</div>
    <p style="font-size:12px;color:var(--mt);margin-bottom:10px">כתוב כאן כל הוראה, יעד, או משימה. המנכ&quot;ל יחלק למחלקות ויחזיר תוכנית.</p>
    <textarea id="mainInst" placeholder="תאר בפירוט..." style="min-height:110px"></textarea>
    <div style="margin-top:9px;display:flex;gap:8px;align-items:center">
      <button class="btn" onclick="sendMainInst()" id="bMI">🚀 שלח</button>
      <span id="lMI" style="display:none"><span class="sp"></span></span>
    </div>
    <div class="rb" id="rMI">
      <div class="rl">👑 תוכנית – דניאל כהן מנכ&quot;ל</div>
      <div id="tMI" style="white-space:pre-wrap"></div>
    </div>
  </div>
  <div class="card">
    <div class="ct">📜 היסטוריית הוראות</div>
    <div id="instHist"><div style="color:var(--mt);font-size:13px">טוען...</div></div>
  </div>
</div>

<!-- TASKS -->
<div class="panel" id="panel-tasks">
  <div style="display:flex;gap:7px;margin-bottom:12px;flex-wrap:wrap;align-items:center">
    <button class="btn bsm" onclick="showNTF()">+ משימה</button>
    <button class="btn bsm bo" onclick="loadTasks()">↻</button>
    <select id="fs" style="width:auto;padding:6px 9px;font-size:12px" onchange="loadTasks()">
      <option value="">כל הסטטוסים</option><option value="pending">ממתין</option>
      <option value="in_progress">בעבודה</option><option value="done">הושלם</option>
      <option value="pending_approval">לאישור</option>
    </select>
    <select id="fd" style="width:auto;padding:6px 9px;font-size:12px" onchange="loadTasks()">
      <option value="">כל המחלקות</option>
    </select>
  </div>
  <div class="card" id="ntf" style="display:none">
    <div class="ct">+ משימה חדשה</div>
    <div class="fg"><label>כותרת</label><input type="text" id="tT" placeholder="כותרת המשימה..."></div>
    <div class="fr">
      <div class="fg"><label>מחלקה</label><select id="tD"></select></div>
      <div class="fg"><label>עדיפות</label>
        <select id="tP"><option value="low">נמוך</option><option value="medium" selected>בינוני</option>
          <option value="high">גבוה</option><option value="urgent">דחוף</option></select>
      </div>
    </div>
    <div class="fg"><label>תיאור</label><textarea id="tDesc" style="min-height:60px" placeholder="פרט..."></textarea></div>
    <div style="display:flex;gap:7px">
      <button class="btn bsm bg" onclick="createTask()">✓ צור</button>
      <button class="btn bsm bo" onclick="hideNTF()">ביטול</button>
    </div>
  </div>
  <div id="tasksList"><div style="color:var(--mt);font-size:13px">טוען...</div></div>
</div>

<!-- EMPLOYEES -->
<div class="panel" id="panel-employees">
  <div style="display:flex;gap:7px;margin-bottom:12px;align-items:center;flex-wrap:wrap">
    <select id="empDeptFilter" style="width:auto;padding:6px 9px;font-size:12px" onchange="loadEmp()">
      <option value="">כל המחלקות</option>
    </select>
    <span id="empCount" style="font-size:12px;color:var(--mt)"></span>
  </div>
  <div class="card" style="overflow-x:auto">
    <table class="etable" id="empTable">
      <thead><tr><th>שם</th><th>תפקיד</th><th>מחלקה</th><th>סטטוס</th></tr></thead>
      <tbody id="empBody"><tr><td colspan="4" style="color:var(--mt);text-align:center;padding:20px">טוען...</td></tr></tbody>
    </table>
  </div>
</div>

<!-- CHAT - IMPROVED -->
<div class="panel" id="panel-chat">
  <div class="chat-wrap">
    <div class="chat-side" id="chatSide"></div>
    <div class="chat-main">
      <div class="chat-hdr" id="chatHdr">💬 שיחה עם הצוות</div>
      <div class="chat-msgs" id="chatMsgs">
        <div class="msg ma"><div class="mn">דניאל כהן – מנכ&quot;ל</div>שלום! אני דניאל כהן, מנכ&quot;ל החברה. מה ברצונך לדון?</div>
      </div>
      <div class="chat-in">
        <button class="btn bsm" onclick="sendChat()" id="bChat">שלח</button>
        <textarea class="ci" id="ci" placeholder="כתוב הודעה... (Enter לשליחה, Shift+Enter לשורה חדשה)"
          onkeydown="if(event.key==='Enter'&&!event.shiftKey){event.preventDefault();sendChat()}"></textarea>
      </div>
    </div>
  </div>
</div>

<!-- DEPARTMENTS -->
<div class="panel" id="panel-depts">
  <div class="dg" id="deptsGrid" style="margin-bottom:14px"></div>
  <div class="card" id="deptDet" style="display:none">
    <div class="ct" id="deptDetT"></div>
    <div id="deptDetC"></div>
  </div>
</div>

<!-- MEETINGS -->
<div class="panel" id="panel-meetings">
  <div class="card">
    <div class="ct">📅 כינוס ישיבה</div>
    <div class="fg"><label>נושא</label><input type="text" id="mtT" placeholder="נושא הישיבה..."></div>
    <div class="fg"><label>סדר יום</label><textarea id="mtA" placeholder="פרט סדר יום..." style="min-height:65px"></textarea></div>
    <div class="fg">
      <label>מחלקות משתתפות (בחר עד 6 – כל נוסף מאריך את הזמן)</label>
      <div style="display:flex;flex-wrap:wrap;gap:7px;margin-top:4px" id="mtDepts">
        <label style="display:flex;align-items:center;gap:4px;font-size:12px;color:var(--tx);cursor:pointer"><input type="checkbox" value="ceo" checked> 👑 דניאל כהן</label>
        <label style="display:flex;align-items:center;gap:4px;font-size:12px;color:var(--tx);cursor:pointer"><input type="checkbox" value="cfo"> 💰 מיכאל לוי</label>
        <label style="display:flex;align-items:center;gap:4px;font-size:12px;color:var(--tx);cursor:pointer"><input type="checkbox" value="marketing"> 📣 נועה שפירא</label>
        <label style="display:flex;align-items:center;gap:4px;font-size:12px;color:var(--tx);cursor:pointer"><input type="checkbox" value="sales"> 📈 רון אברהם</label>
        <label style="display:flex;align-items:center;gap:4px;font-size:12px;color:var(--tx);cursor:pointer"><input type="checkbox" value="legal"> ⚖️ תמר גולן</label>
        <label style="display:flex;align-items:center;gap:4px;font-size:12px;color:var(--tx);cursor:pointer"><input type="checkbox" value="cto"> 💻 אלון בן-דוד</label>
        <label style="display:flex;align-items:center;gap:4px;font-size:12px;color:var(--tx);cursor:pointer"><input type="checkbox" value="content"> 🎨 שיר מזרחי</label>
        <label style="display:flex;align-items:center;gap:4px;font-size:12px;color:var(--tx);cursor:pointer"><input type="checkbox" value="pr"> 📢 גיל פרץ</label>
        <label style="display:flex;align-items:center;gap:4px;font-size:12px;color:var(--tx);cursor:pointer"><input type="checkbox" value="compliance"> 🛡️ ענת רוזן</label>
        <label style="display:flex;align-items:center;gap:4px;font-size:12px;color:var(--tx);cursor:pointer"><input type="checkbox" value="hr"> 👥 יובל כץ</label>
        <label style="display:flex;align-items:center;gap:4px;font-size:12px;color:var(--tx);cursor:pointer"><input type="checkbox" value="customer"> 🎧 ליאת דביר</label>
      </div>
    </div>
    <button class="btn" onclick="createMeeting()" id="bMt">📅 כנס ישיבה</button>
    <span id="lMt" style="display:none;margin-right:9px"><span class="sp"></span> כ-30 שניות...</span>
    <div class="rb" id="rMt"></div>
  </div>
  <div class="card"><div class="ct">📜 ישיבות קודמות</div>
    <div id="mtList"><div style="color:var(--mt);font-size:13px">טוען...</div></div>
  </div>
</div>

<!-- SOCIAL -->
<div class="panel" id="panel-social">
  <div class="card">
    <div class="ct">📱 פרסום לרשתות</div>
    <div class="fg">
      <label>פלטפורמות</label>
      <div class="plat-row">
        <button class="pb" id="fb-b" onclick="togP('facebook',this)">📘 פייסבוק</button>
        <button class="pb" id="ig-b" onclick="togP('instagram',this)">📸 אינסטגרם</button>
        <button class="pb" id="tt-b" onclick="togP('tiktok',this)">🎵 טיקטוק</button>
        <button class="pb" id="wa-b" onclick="togP('whatsapp',this)">💬 וואטסאפ</button>
      </div>
    </div>
    <div id="waPhone" style="display:none;margin-bottom:10px">
      <div class="fg"><label>מספר וואטסאפ (עם קידומת מדינה)</label>
        <input type="text" id="waNum" placeholder="972501234567"></div>
    </div>
    <div style="display:flex;gap:7px;margin-bottom:10px;align-items:center">
      <button class="btn bsm bo" onclick="genPost()" id="bGP">✨ AI כותב</button>
      <input type="text" id="postTopic" placeholder="נושא הפוסט..." style="flex:1;min-width:150px">
    </div>
    <div class="fg"><label>תוכן הפוסט</label><textarea id="postTxt" placeholder="תוכן הפוסט..." style="min-height:110px"></textarea></div>
    <div class="fg"><label>קישור תמונה (נדרש לאינסטגרם)</label>
      <input type="text" id="postImg" placeholder="https://..."></div>
    <div style="display:flex;gap:7px;align-items:center">
      <button class="btn" onclick="publishPost()" id="bPub">🚀 פרסם</button>
      <span id="lPub" style="display:none"><span class="sp"></span></span>
    </div>
    <div class="rb" id="rPub"></div>
  </div>
  <div class="card">
    <div class="ct">⚙ חיבור רשתות</div>
    <div id="socialSt" style="font-size:12px;color:var(--mt)">טוען...</div>
    <div style="margin-top:12px;background:var(--sur);border:1px solid var(--bdr);border-radius:8px;padding:12px;font-size:11px;direction:ltr;text-align:left;color:var(--ac2)">
META_PAGE_TOKEN=your_token<br>
META_PAGE_ID=your_page_id<br>
INSTAGRAM_ACCOUNT_ID=your_ig_id<br>
WHATSAPP_TOKEN=your_wa_token<br>
WHATSAPP_PHONE_ID=your_phone_id
    </div>
  </div>
  <div class="card"><div class="ct">📜 פוסטים שפורסמו</div>
    <div id="postsList"><div style="color:var(--mt);font-size:13px">טוען...</div></div>
  </div>
</div>

<!-- CASHFLOW -->
<div class="panel" id="panel-cashflow">
  <div style="display:flex;gap:7px;margin-bottom:12px;flex-wrap:wrap">
    <button class="btn bsm" onclick="showCFF()">+ הוסף תנועה</button>
    <button class="btn bsm bo" onclick="loadCF()">↻ רענן</button>
    <button class="btn bsm" style="background:linear-gradient(135deg,#f59e0b,#d97706)" onclick="analyzeCF()">🤖 מיכאל מנתח</button>
  </div>
  <div class="cf-s">
    <div class="cfs"><div class="cfn cin" id="cf-i">—</div><div class="cfl">הכנסות</div></div>
    <div class="cfs"><div class="cfn cout" id="cf-o">—</div><div class="cfl">הוצאות</div></div>
    <div class="cfs"><div class="cfn" id="cf-b">—</div><div class="cfl">יתרה</div></div>
  </div>
  <div class="card" id="cff" style="display:none">
    <div class="ct">+ תנועה חדשה</div>
    <div class="fr">
      <div class="fg"><label>תאריך</label><input type="text" id="cfDate" placeholder="2025-01-15"></div>
      <div class="fg"><label>סוג</label><select id="cfType"><option value="income">הכנסה</option><option value="expense">הוצאה</option></select></div>
    </div>
    <div class="fr">
      <div class="fg"><label>סכום (₪)</label><input type="text" id="cfAmt" placeholder="1000"></div>
      <div class="fg"><label>קטגוריה</label>
        <select id="cfCat"><option>שיווק</option><option>שכר</option><option>פרסום</option><option>ציוד</option><option>לקוח</option><option>השקעה</option><option>כללי</option></select>
      </div>
    </div>
    <div class="fg"><label>תיאור</label><input type="text" id="cfDesc" placeholder="תיאור..."></div>
    <div class="fg"><label>מזהה לקוח (אופציונלי)</label><input type="text" id="cfClient" placeholder="client_id..."></div>
    <div style="display:flex;gap:7px">
      <button class="btn bsm bg" onclick="addCF()">✓ הוסף</button>
      <button class="btn bsm bo" onclick="hideCFF()">ביטול</button>
    </div>
  </div>
  <div class="card">
    <div class="rb" id="cfAnal"></div>
    <div style="overflow-x:auto">
      <table class="cft" id="cfTbl">
        <thead><tr><th>תאריך</th><th>תיאור</th><th>קטגוריה</th><th>סוג</th><th>סכום</th></tr></thead>
        <tbody id="cfBody"><tr><td colspan="5" style="color:var(--mt);text-align:center;padding:16px">אין נתונים</td></tr></tbody>
      </table>
    </div>
  </div>
</div>

<!-- REPORTS -->
<div class="panel" id="panel-reports">
  <div class="card">
    <div class="ct">📊 הפק דוח</div>
    <div class="fr">
      <div class="fg"><label>מחלקה</label><select id="rD"></select></div>
      <div class="fg"><label>סוג</label><select id="rT">
        <option value="weekly">שבועי</option><option value="monthly">חודשי</option>
        <option value="quarterly">רבעוני</option><option value="summary">סיכום</option>
      </select></div>
    </div>
    <button class="btn" onclick="genRep()" id="bRep">📊 הפק</button>
    <span id="lRep" style="display:none;margin-right:9px"><span class="sp"></span></span>
    <div class="rb" id="rRep">
      <div class="rl" id="rRepL">דוח</div>
      <div id="rRepT" style="white-space:pre-wrap"></div>
    </div>
  </div>
  <div class="card"><div class="ct">📁 דוחות קודמים</div>
    <div id="repList"><div style="color:var(--mt);font-size:13px">טוען...</div></div>
  </div>
</div>

<!-- STRATEGY -->
<div class="panel" id="panel-strategy">
  <div class="card">
    <div class="ct">🎯 יעדים אסטרטגיים</div>
    <p style="font-size:12px;color:var(--mt);margin-bottom:10px">יעדים לטווח ארוך. המנכ&quot;ל יבנה תוכנית עם KPIs ולוח זמנים.</p>
    <textarea id="stratG" placeholder="לדוגמה: עד סוף הרבעון להגיע ל-100 לקוחות..." style="min-height:100px"></textarea>
    <div style="margin-top:9px;display:flex;gap:7px;align-items:center">
      <button class="btn" onclick="setGoals()" id="bGoals">🎯 שלח לתכנון</button>
      <span id="lGoals" style="display:none"><span class="sp"></span></span>
    </div>
    <div class="rb" id="rGoals">
      <div class="rl">📋 תוכנית – דניאל כהן מנכ&quot;ל</div>
      <div id="tGoals" style="white-space:pre-wrap"></div>
    </div>
  </div>
  <div class="card"><div class="ct">📌 יעדים קודמים</div>
    <div id="goalsList"><div style="color:var(--mt);font-size:13px">טוען...</div></div>
  </div>
</div>

<!-- APPROVALS -->
<div class="panel" id="panel-approvals">
  <div class="card"><div class="ct">👁 ממתינים לאישורך</div>
    <div id="apprList"><div style="color:var(--mt);font-size:13px">טוען...</div></div>
  </div>
</div>

<!-- SETTINGS -->
<div class="panel" id="panel-settings">
  <div class="card"><div class="ct">⚙ חיבורי מערכת</div><div id="connSt"></div></div>
  <div class="card">
    <div class="ct">🗄 SQL – צור טבלאות Supabase</div>
    <p style="font-size:11px;color:var(--mt);margin-bottom:8px">הרץ ב-SQL Editor:</p>
    <pre style="background:var(--sur);border:1px solid var(--bdr);border-radius:8px;padding:10px;font-size:9px;overflow-x:auto;color:var(--ac2);white-space:pre;direction:ltr;text-align:left">CREATE TABLE IF NOT EXISTS tasks(id uuid DEFAULT gen_random_uuid() PRIMARY KEY,title text,description text,department text,status text DEFAULT 'pending',priority text DEFAULT 'medium',created_by text,created_at timestamptz DEFAULT now(),approved_at timestamptz);
CREATE TABLE IF NOT EXISTS instructions(id uuid DEFAULT gen_random_uuid() PRIMARY KEY,text text,ceo_response text,status text DEFAULT 'processing',created_at timestamptz DEFAULT now());
CREATE TABLE IF NOT EXISTS meetings(id uuid DEFAULT gen_random_uuid() PRIMARY KEY,topic text,agenda text,responses jsonb,status text,created_at timestamptz DEFAULT now());
CREATE TABLE IF NOT EXISTS reports(id uuid DEFAULT gen_random_uuid() PRIMARY KEY,title text,department text,content text,type text,created_at timestamptz DEFAULT now());
CREATE TABLE IF NOT EXISTS chat_messages(id uuid DEFAULT gen_random_uuid() PRIMARY KEY,department text,user_message text,ai_response text,created_at timestamptz DEFAULT now());
CREATE TABLE IF NOT EXISTS strategic_goals(id uuid DEFAULT gen_random_uuid() PRIMARY KEY,goals text,plan text,status text DEFAULT 'active',created_at timestamptz DEFAULT now());
CREATE TABLE IF NOT EXISTS cashflow(id uuid DEFAULT gen_random_uuid() PRIMARY KEY,date date,description text,amount numeric,type text,category text,client_id text,created_at timestamptz DEFAULT now());
CREATE TABLE IF NOT EXISTS social_posts(id uuid DEFAULT gen_random_uuid() PRIMARY KEY,text text,image_url text,platforms jsonb,results jsonb,status text,created_at timestamptz DEFAULT now());</pre>
  </div>
</div>

</div>

<script>
const AUTH=sessionStorage.getItem('jabr_auth')||'';
const AH={'Content-Type':'application/json','Authorization':AUTH?'Basic '+AUTH:''};
async function api(m,p,b){
  const o={method:m,headers:AH};if(b)o.body=JSON.stringify(b);
  const r=await fetch('/api'+p,o);
  if(r.status===401){window.location.href='/';return null;}
  if(!r.ok){const e=await r.text();throw new Error(e);}
  return r.json();
}
function logout(){sessionStorage.removeItem('jabr_auth');window.location.href='/';}
function fd(d){if(!d)return'';try{return new Date(d).toLocaleDateString('he-IL',{day:'2-digit',month:'2-digit',year:'2-digit',hour:'2-digit',minute:'2-digit'})}catch{return d}}
function fmtN(n){return Number(n||0).toLocaleString('he-IL')}
function busy(b,l,on){const be=document.getElementById(b),le=document.getElementById(l);if(be)be.disabled=on;if(le)le.style.display=on?'inline-flex':'none';}

// ── Tabs ──────────────────────────────────────────────────────
function T(name,btn){
  document.querySelectorAll('.panel').forEach(p=>p.classList.remove('active'));
  document.querySelectorAll('.tb').forEach(b=>b.classList.remove('active'));
  const panel=document.getElementById('panel-'+name);
  if(panel)panel.classList.add('active');
  if(btn)btn.classList.add('active');
  const m={home:initHome,instruct:()=>loadInstHist(),tasks:loadTasks,employees:loadEmp,
    chat:buildChatSide,depts:loadDepts,meetings:loadMeetings,social:initSocial,
    cashflow:loadCF,reports:initReports,strategy:loadGoals,approvals:loadApprls,settings:checkConn};
  if(m[name])m[name]();
}

// ── Dept data ─────────────────────────────────────────────────
let DEPTS=[];
async function getDepts(){
  if(!DEPTS.length)DEPTS=await api('GET','/departments')||[];
  return DEPTS;
}

// ── Stats ─────────────────────────────────────────────────────
async function loadStats(){
  try{const s=await api('GET','/stats');
    ['d','e','t','dn','ip','pa'].forEach((k,i)=>{
      const vals=[s.departments,s.employees,s.tasks_total,s.tasks_done,s.tasks_inprog,s.tasks_pending];
      const el=document.getElementById('s-'+k);if(el)el.textContent=vals[i]??'—';
    });
  }catch(e){}
}

// ── Home ──────────────────────────────────────────────────────
async function initHome(){
  loadStats();
  const depts=await getDepts();
  const g=document.getElementById('homeDepts');
  if(g)g.innerHTML=depts.map(d=>`
    <div class="dc" style="border-top:3px solid ${d.color}" onclick="T('chat',null);selAgent('${d.id}','${d.name}','${d.head}','${d.title}')">
      <div class="di">${d.icon}</div>
      <div class="dn">${d.name}</div>
      <div class="dh">${d.head}</div>
      <div class="dt">${d.title}</div>
    </div>`).join('');
  try{const a=await api('GET','/approvals');
    const el=document.getElementById('homeAppr');
    if(el)el.innerHTML=a&&a.length?a.slice(0,3).map(tHTML).join(''):'<div style="color:var(--mt);font-size:13px">אין תוצרים ממתינים</div>';
  }catch(e){}
}

// ── Instructions ──────────────────────────────────────────────
async function sendInst(){
  const t=document.getElementById('homeInst').value.trim();
  if(!t)return alert('נא לכתוב הוראה');
  busy('bHI','lHI',true);
  try{const r=await api('POST','/instruct',{instruction:t});
    document.getElementById('rHI').classList.add('show');
    document.getElementById('tHI').textContent=r.ceo_response;
  }catch(e){alert('שגיאה: '+e.message);}
  busy('bHI','lHI',false);
}
async function sendMainInst(){
  const t=document.getElementById('mainInst').value.trim();
  if(!t)return alert('נא לכתוב הוראה');
  busy('bMI','lMI',true);
  try{const r=await api('POST','/instruct',{instruction:t});
    document.getElementById('rMI').classList.add('show');
    document.getElementById('tMI').textContent=r.ceo_response;
    loadInstHist();
  }catch(e){alert('שגיאה: '+e.message);}
  busy('bMI','lMI',false);
}
async function loadInstHist(){
  try{const items=await api('GET','/instructions');
    const el=document.getElementById('instHist');if(!el)return;
    if(!items||!items.length){el.innerHTML='<div style="color:var(--mt);font-size:13px">אין היסטוריה</div>';return;}
    el.innerHTML=items.map(i=>`
      <div class="ti">
        <div class="tdot di2"></div>
        <div class="ti-i">
          <div class="ti-t">${i.text||''}</div>
          <div class="ti-m">${fd(i.created_at)}</div>
          ${i.ceo_response?`<div style="font-size:11px;color:var(--mt);margin-top:5px;line-height:1.5;max-height:70px;overflow:hidden">${i.ceo_response.substring(0,250)}...</div>`:''}
        </div>
      </div>`).join('');
  }catch(e){}
}

// ── Tasks ─────────────────────────────────────────────────────
const PMAP={pending:'dp',in_progress:'di2',done:'dd',pending_approval:'da'};
const TMAP={pending:'to',in_progress:'tag',done:'tg',pending_approval:'ty'};
const LMAP={pending:'ממתין',in_progress:'בעבודה',done:'הושלם',pending_approval:'לאישור'};
const PRMAP={low:'pl',medium:'pm',high:'ph',urgent:'pu'};
const PRLAB={low:'נמוך',medium:'בינוני',high:'גבוה',urgent:'דחוף!'};
function tHTML(t){
  return`<div class="ti">
    <div class="tdot ${PMAP[t.status]||'dp'}"></div>
    <div class="ti-i">
      <div class="ti-t">${t.title||''}</div>
      <div class="ti-m">${t.department||''} • ${fd(t.created_at)} • <span class="${PRMAP[t.priority]||'pm'}">${PRLAB[t.priority]||t.priority||''}</span></div>
    </div>
    <span class="tag ${TMAP[t.status]||''}">${LMAP[t.status]||t.status}</span>
    ${t.status==='pending_approval'?`<button class="btn bsm bg" onclick="approveT('${t.id}')">✓</button>`:''}
  </div>`;}
async function loadTasks(){
  const st=document.getElementById('fs')?.value||'';
  const dp=document.getElementById('fd')?.value||'';
  let q='';if(st)q+=`?status=${st}`;if(dp)q+=`${q?'&':'?'}dept=${dp}`;
  try{const items=await api('GET','/tasks'+q);
    const el=document.getElementById('tasksList');if(!el)return;
    el.innerHTML=items&&items.length?'<div class="card">'+items.map(tHTML).join('')+'</div>':'<div class="card"><div style="color:var(--mt);font-size:13px">אין משימות עדיין</div></div>';
    const df=document.getElementById('fd');
    if(df&&df.options.length<=1){const depts=await getDepts();depts.forEach(d=>{const o=document.createElement('option');o.value=d.id;o.textContent=d.name;df.appendChild(o)});}
  }catch(e){}
}
async function createTask(){
  const title=document.getElementById('tT').value.trim();if(!title)return alert('נא להזין כותרת');
  try{await api('POST','/tasks',{title,description:document.getElementById('tDesc').value,
    department:document.getElementById('tD').value,priority:document.getElementById('tP').value});
    hideNTF();loadTasks();
  }catch(e){alert('שגיאה: '+e.message);}
}
async function approveT(id){try{await api('POST','/tasks/'+id+'/approve');loadTasks();}catch(e){}}
async function showNTF(){
  document.getElementById('ntf').style.display='block';
  const d=document.getElementById('tD');
  if(d&&!d.options.length){const depts=await getDepts();depts.forEach(dep=>{const o=document.createElement('option');o.value=dep.id;o.textContent=dep.name;d.appendChild(o)});}
}
function hideNTF(){document.getElementById('ntf').style.display='none';}

// ── Employees ─────────────────────────────────────────────────
async function loadEmp(){
  const dept=document.getElementById('empDeptFilter')?.value||'';
  const url=dept?'/employees?dept='+dept:'/employees';
  try{const items=await api('GET',url);
    const cnt=document.getElementById('empCount');
    if(cnt)cnt.textContent=`סה"כ: ${items.length} עובדים`;
    const body=document.getElementById('empBody');if(!body)return;
    const depts=await getDepts();
    const deptMap=Object.fromEntries(depts.map(d=>[d.id,d]));
    body.innerHTML=items.map(e=>{
      const dm=deptMap[e.department]||{};
      const initials=(e.name||'AI').split(' ').map(w=>w[0]).join('').substring(0,2);
      return`<tr>
        <td style="display:flex;align-items:center;gap:0">
          <div class="eavatar">${initials}</div>${e.name||''}
        </td>
        <td>${e.role||''}</td>
        <td><span style="display:inline-flex;align-items:center;gap:4px">${dm.icon||''} ${dm.name||e.department}</span></td>
        <td><span class="tag tg">פעיל</span></td>
      </tr>`}).join('');
    // Populate dept filter
    const df=document.getElementById('empDeptFilter');
    if(df&&df.options.length<=1){depts.forEach(d=>{const o=document.createElement('option');o.value=d.id;o.textContent=d.icon+' '+d.name;df.appendChild(o)});}
  }catch(e){}
}

// ── Chat ──────────────────────────────────────────────────────
let cAgent='ceo',cHist=[],cAgentName='דניאל כהן',cAgentTitle='מנכ"ל';
async function buildChatSide(){
  const depts=await getDepts();const sb=document.getElementById('chatSide');if(!sb)return;
  sb.innerHTML=depts.map((d,i)=>`
    <button class="ca${i===0?' active':''}" onclick="selAgent('${d.id}','${d.name}','${d.head}','${d.title}',this)">
      <span class="ca-n">${d.icon} ${d.head}</span>
      <span class="ca-r">${d.title}</span>
    </button>`).join('');
}
function selAgent(id,dname,head,title,btn){
  cAgent=id;cAgentName=head;cAgentTitle=title;cHist=[];
  document.querySelectorAll('.ca').forEach(b=>b.classList.remove('active'));
  if(btn)btn.classList.add('active');
  const hdr=document.getElementById('chatHdr');
  if(hdr)hdr.textContent='💬 '+head+' – '+title;
  const msgs=document.getElementById('chatMsgs');
  if(msgs)msgs.innerHTML=`<div class="msg ma"><div class="mn">${head} – ${title}</div>שלום! אני ${head}. איך אוכל לעזור?</div>`;
}
async function sendChat(){
  const inp=document.getElementById('ci');const msg=inp.value.trim();if(!msg)return;
  inp.value='';inp.style.height='38px';
  const msgs=document.getElementById('chatMsgs');
  msgs.innerHTML+=`<div class="msg mu">${msg.replace(/\n/g,'<br>')}</div>`;
  msgs.innerHTML+=`<div class="msg ma" id="typing"><div class="mn">${cAgentName}</div><span class="sp"></span></div>`;
  msgs.scrollTop=msgs.scrollHeight;
  cHist.push({role:'user',content:msg});
  document.getElementById('bChat').disabled=true;
  try{const r=await api('POST','/chat/'+cAgent,{message:msg,history:cHist});
    const t=document.getElementById('typing');if(t)t.remove();
    msgs.innerHTML+=`<div class="msg ma"><div class="mn">${r.agent||cAgentName} – ${r.title||cAgentTitle}</div>${r.response.replace(/\n/g,'<br>')}</div>`;
    cHist.push({role:'assistant',content:r.response});
    msgs.scrollTop=msgs.scrollHeight;
  }catch(e){const t=document.getElementById('typing');if(t)t.innerHTML=`<div class="mn">שגיאה</div>${e.message}`;}
  document.getElementById('bChat').disabled=false;
}

// ── Departments ───────────────────────────────────────────────
async function loadDepts(){
  const depts=await getDepts();
  const g=document.getElementById('deptsGrid');if(!g)return;
  g.innerHTML=depts.map(d=>`
    <div class="dc" style="border-top:3px solid ${d.color}" onclick="showDeptDet('${d.id}','${d.name}','${d.icon}')">
      <div class="di">${d.icon}</div><div class="dn">${d.name}</div>
      <div class="dh">${d.head}</div><div class="dt">${d.title}</div>
    </div>`).join('');
}
async function showDeptDet(id,name,icon){
  document.getElementById('deptDet').style.display='block';
  document.getElementById('deptDetT').textContent=icon+' '+name;
  document.getElementById('deptDetC').innerHTML='<div style="color:var(--mt)">טוען...</div>';
  try{const [emps,tasks]=await Promise.all([api('GET','/employees?dept='+id),api('GET','/tasks?dept='+id)]);
    document.getElementById('deptDetC').innerHTML=`
      <div style="display:grid;grid-template-columns:1fr 1fr;gap:14px">
        <div>
          <div style="font-size:10px;color:var(--mt);margin-bottom:7px">צוות (${emps.length})</div>
          ${emps.map(e=>`<div class="ti"><div class="tdot ${e.title==='מנהל מחלקה'?'da':'dd'}"></div>
            <div class="ti-i"><div class="ti-t">${e.name}</div><div class="ti-m">${e.role}</div></div>
            ${e.title==='מנהל מחלקה'?'<span class="tag ty">מנהל</span>':''}
          </div>`).join('')}
        </div>
        <div>
          <div style="font-size:10px;color:var(--mt);margin-bottom:7px">משימות (${tasks.length})</div>
          ${tasks.slice(0,5).map(tHTML).join('')||'<div style="color:var(--mt);font-size:12px">אין משימות</div>'}
        </div>
      </div>`;
  }catch(e){}
}

// ── Meetings ──────────────────────────────────────────────────
async function createMeeting(){
  const topic=document.getElementById('mtT').value.trim();if(!topic)return alert('נא להזין נושא');
  const depts=[...document.querySelectorAll('#mtDepts input:checked')].map(i=>i.value);
  if(!depts.length)return alert('נא לבחור לפחות מחלקה');
  busy('bMt','lMt',true);
  try{const r=await api('POST','/meetings',{topic,agenda:document.getElementById('mtA').value,departments:depts});
    const box=document.getElementById('rMt');box.classList.add('show');
    let html=`<div class="rl">📅 ${topic}</div>`;
    const dm=Object.fromEntries((await getDepts()).map(d=>[d.id,d]));
    for(const [d,resp] of Object.entries(r.responses||{})){
      const info=dm[d]||{};
      html+=`<div class="dr"><div class="drn">${info.icon||''} ${info.head||d} – ${info.title||''}</div>${resp}</div>`;
    }
    box.innerHTML=html;loadMeetings();
  }catch(e){alert('שגיאה: '+e.message);}
  busy('bMt','lMt',false);
}
async function loadMeetings(){
  try{const items=await api('GET','/meetings');
    const el=document.getElementById('mtList');if(!el)return;
    if(!items||!items.length){el.innerHTML='<div style="color:var(--mt);font-size:13px">אין ישיבות</div>';return;}
    const dm=Object.fromEntries((await getDepts()).map(d=>[d.id,d]));
    el.innerHTML=items.map(m=>{
      let rs='';
      try{const obj=typeof m.responses==='string'?JSON.parse(m.responses):m.responses;
        for(const [d,resp] of Object.entries(obj||{})){
          const info=dm[d]||{};
          rs+=`<div class="dr"><div class="drn">${info.icon||''} ${info.head||d}</div>${resp.substring(0,200)}...</div>`;
        }
      }catch(e){}
      return`<div class="card" style="margin-bottom:10px">
        <div style="font-weight:700;margin-bottom:5px">${m.topic||''}</div>
        <div style="font-size:10px;color:var(--mt)">${fd(m.created_at)}</div>
        ${rs?'<div style="margin-top:10px">'+rs+'</div>':''}</div>`;
    }).join('');
  }catch(e){}
}

// ── Social ────────────────────────────────────────────────────
let selP=new Set();
function togP(p,btn){
  if(selP.has(p)){selP.delete(p);btn.classList.remove('sel');}else{selP.add(p);btn.classList.add('sel');}
  document.getElementById('waPhone').style.display=selP.has('whatsapp')?'block':'none';
}
async function genPost(){
  const t=document.getElementById('postTopic').value.trim();if(!t)return alert('נא להזין נושא');
  const b=document.getElementById('bGP');b.disabled=true;b.textContent='...';
  try{const r=await api('POST','/social/generate',{topic:t,dept:'content'});
    document.getElementById('postTxt').value=r.post;
  }catch(e){alert('שגיאה: '+e.message);}
  b.disabled=false;b.textContent='✨ AI כותב';
}
async function publishPost(){
  const txt=document.getElementById('postTxt').value.trim();
  if(!txt)return alert('נא לכתוב תוכן');if(!selP.size)return alert('נא לבחור פלטפורמה');
  busy('bPub','lPub',true);
  try{const r=await api('POST','/social/publish',{text:txt,
    image_url:document.getElementById('postImg').value,
    platforms:[...selP],whatsapp_phone:document.getElementById('waNum')?.value||''});
    const box=document.getElementById('rPub');box.classList.add('show');
    let html='<div class="rl">תוצאות פרסום</div>';
    for(const [plat,res] of Object.entries(r.results||{})){
      html+=`<div style="padding:7px;margin-bottom:5px;background:rgba(${res.ok?'34,211,160':'248,113,113'},.07);border-radius:6px;border:1px solid rgba(${res.ok?'34,211,160':'248,113,113'},.2);font-size:12px">
        ${res.ok?'✅':'❌'} <strong>${plat}</strong>: ${res.ok?'פורסם בהצלחה'+(res.post_id?' – ID: '+res.post_id:''):res.error||'שגיאה'}</div>`;
    }
    box.innerHTML=html;loadPosts();
  }catch(e){alert('שגיאה: '+e.message);}
  busy('bPub','lPub',false);
}
async function loadPosts(){
  try{const items=await api('GET','/social/posts');
    const el=document.getElementById('postsList');if(!el)return;
    if(!items||!items.length){el.innerHTML='<div style="color:var(--mt);font-size:13px">אין פוסטים</div>';return;}
    el.innerHTML=items.map(p=>{
      const plats=typeof p.platforms==='string'?JSON.parse(p.platforms):p.platforms||[];
      return`<div class="ti"><div class="tdot ${p.status==='published'?'dd':'dp'}"></div>
        <div class="ti-i"><div class="ti-t">${(p.text||'').substring(0,70)}...</div>
        <div class="ti-m">${plats.join(', ')} • ${fd(p.created_at)}</div></div>
        <span class="tag ${p.status==='published'?'tg':'to'}">${p.status==='published'?'פורסם':'נכשל'}</span>
      </div>`;}).join('');
  }catch(e){}
}
async function initSocial(){
  loadPosts();
  try{const h=await api('GET','/health');
    const el=document.getElementById('socialSt');if(!el)return;
    const items=[['📘 פייסבוק',h.facebook,'META_PAGE_TOKEN'],['📸 אינסטגרם',h.instagram,'INSTAGRAM_ACCOUNT_ID'],
      ['🎵 טיקטוק',h.tiktok,'TIKTOK_ACCESS_TOKEN'],['💬 וואטסאפ',h.whatsapp,'WHATSAPP_TOKEN']];
    el.innerHTML=items.map(([n,ok,key])=>
      `<div style="display:flex;justify-content:space-between;margin-bottom:5px;font-size:12px">
        <span>${n}</span><span style="color:${ok?'var(--grn)':'var(--red)'}">${ok?'✅ מחובר':'❌ חסר '+key}</span>
      </div>`).join('');
  }catch(e){}
}

// ── Cashflow ──────────────────────────────────────────────────
async function loadCF(){
  try{const items=await api('GET','/cashflow');
    const body=document.getElementById('cfBody');if(!body)return;
    if(!items||!items.length){body.innerHTML='<tr><td colspan="5" style="color:var(--mt);text-align:center;padding:14px">אין נתונים</td></tr>';return;}
    let ti=0,to=0;
    body.innerHTML=items.map(r=>{
      const inc=r.type==='income';if(inc)ti+=Number(r.amount||0);else to+=Number(r.amount||0);
      return`<tr>
        <td>${r.date||''}</td><td>${r.description||''}</td><td>${r.category||''}</td>
        <td><span class="tag ${inc?'tg':'to'}">${inc?'הכנסה':'הוצאה'}</span></td>
        <td class="${inc?'cin':'cout'}">${inc?'+':'-'}${fmtN(r.amount)} ₪</td>
      </tr>`}).join('');
    document.getElementById('cf-i').textContent=fmtN(ti)+' ₪';
    document.getElementById('cf-o').textContent=fmtN(to)+' ₪';
    const bal=ti-to;const be=document.getElementById('cf-b');
    be.textContent=fmtN(bal)+' ₪';be.className='cfn '+(bal>=0?'cin':'cout');
  }catch(e){}
}
async function addCF(){
  const amt=parseFloat(document.getElementById('cfAmt').value);
  if(!amt||isNaN(amt))return alert('נא להזין סכום');
  try{await api('POST','/cashflow',{
    date:document.getElementById('cfDate').value||new Date().toISOString().split('T')[0],
    description:document.getElementById('cfDesc').value,amount:amt,
    type:document.getElementById('cfType').value,category:document.getElementById('cfCat').value,
    client_id:document.getElementById('cfClient').value});
    hideCFF();loadCF();
  }catch(e){alert('שגיאה: '+e.message);}
}
async function analyzeCF(){
  const el=document.getElementById('cfAnal');el.classList.add('show');
  el.innerHTML='<span class="sp"></span> מיכאל לוי מנתח...';
  try{const r=await api('POST','/cashflow/analyze');
    el.innerHTML=`<div class="rl">💰 ניתוח – מיכאל לוי CFO</div>${r.analysis.replace(/\n/g,'<br>')}`;
  }catch(e){el.innerHTML='שגיאה: '+e.message;}
}
function showCFF(){document.getElementById('cff').style.display='block';}
function hideCFF(){document.getElementById('cff').style.display='none';}

// ── Reports ───────────────────────────────────────────────────
async function initReports(){
  loadRepList();
  const d=document.getElementById('rD');if(d&&!d.options.length){
    const depts=await getDepts();depts.forEach(dep=>{const o=document.createElement('option');o.value=dep.id;o.textContent=dep.name;d.appendChild(o)});}
}
async function genRep(){
  busy('bRep','lRep',true);
  try{const r=await api('POST','/reports/generate',{department:document.getElementById('rD').value,type:document.getElementById('rT').value});
    document.getElementById('rRep').classList.add('show');
    document.getElementById('rRepL').textContent=r.report?.title||'דוח';
    document.getElementById('rRepT').textContent=r.report?.content||'';
    loadRepList();
  }catch(e){alert('שגיאה: '+e.message);}
  busy('bRep','lRep',false);
}
async function loadRepList(){
  try{const items=await api('GET','/reports');
    const el=document.getElementById('repList');if(!el)return;
    if(!items||!items.length){el.innerHTML='<div style="color:var(--mt);font-size:13px">אין דוחות</div>';return;}
    el.innerHTML=items.map(r=>`<div class="ti"><div class="tdot dd"></div>
      <div class="ti-i"><div class="ti-t">${r.title||''}</div>
      <div class="ti-m">${r.type||''} • ${fd(r.created_at)}</div></div></div>`).join('');
  }catch(e){}
}

// ── Strategy ──────────────────────────────────────────────────
async function setGoals(){
  const g=document.getElementById('stratG').value.trim();if(!g)return alert('נא להזין יעדים');
  busy('bGoals','lGoals',true);
  try{const r=await api('POST','/strategy/goals',{goals:g});
    document.getElementById('rGoals').classList.add('show');
    document.getElementById('tGoals').textContent=r.plan;
    loadGoals();
  }catch(e){alert('שגיאה: '+e.message);}
  busy('bGoals','lGoals',false);
}
async function loadGoals(){
  try{const items=await api('GET','/strategy/goals');
    const el=document.getElementById('goalsList');if(!el)return;
    if(!items||!items.length){el.innerHTML='<div style="color:var(--mt);font-size:13px">אין יעדים</div>';return;}
    el.innerHTML=items.map(g=>`<div class="card" style="margin-bottom:8px">
      <div style="font-size:13px;font-weight:600">${g.goals||''}</div>
      ${g.plan?`<div style="font-size:11px;color:var(--mt);margin-top:7px;white-space:pre-wrap;max-height:160px;overflow:hidden">${g.plan.substring(0,500)}...</div>`:''}
      <div style="font-size:10px;color:var(--mt);margin-top:6px">${fd(g.created_at)}</div>
    </div>`).join('');
  }catch(e){}
}

// ── Approvals ─────────────────────────────────────────────────
async function loadApprls(){
  try{const items=await api('GET','/approvals');
    const el=document.getElementById('apprList');if(!el)return;
    el.innerHTML=items&&items.length?items.map(tHTML).join(''):'<div style="color:var(--mt);font-size:13px">אין תוצרים ממתינים</div>';
  }catch(e){}
}

// ── Settings ──────────────────────────────────────────────────
async function checkConn(){
  try{const h=await api('GET','/health');
    const el=document.getElementById('connSt');if(!el)return;
    const rows=[['🤖 Claude AI',h.anthropic],['🗄 Supabase',h.supabase],
      ['📘 פייסבוק',h.facebook],['📸 אינסטגרם',h.instagram],['🎵 טיקטוק',h.tiktok],['💬 וואטסאפ',h.whatsapp]];
    el.innerHTML=rows.map(([n,ok])=>`<div class="conn-row"><span>${n}</span>
      <span style="color:${ok?'var(--grn)':'var(--red)'}">${ok?'✅ מחובר':'❌ לא מוגדר'}</span></div>`).join('');
  }catch(e){}
}

// ── Init ──────────────────────────────────────────────────────
document.addEventListener('DOMContentLoaded',async()=>{
  await getDepts();
  initHome();
});
</script>
</body></html>'''

# ── Routes ────────────────────────────────────────────────────────────────────
@app.get("/", response_class=HTMLResponse)
async def login_page():
    return HTMLResponse(LOGIN_HTML)

@app.get("/dashboard", response_class=HTMLResponse)
async def dashboard(user=Depends(verify_auth)):
    return HTMLResponse(DASHBOARD_HTML)

@app.get("/health")
async def health_pub():
    return {"status": "ok"}

