"""Jabr Management System – גבר יזמות ייעוץ עסקי והשקעות"""
import os, json, secrets, base64, httpx
from fastapi import FastAPI, Request, HTTPException, Depends
from fastapi.responses import HTMLResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBasic, HTTPBasicCredentials
from typing import Optional
from datetime import datetime

# ── Config ────────────────────────────────────────────────────
ANTHROPIC_KEY   = os.getenv("ANTHROPIC_API_KEY", "")
SB_URL          = os.getenv("SUPABASE_URL", "")
SB_KEY          = os.getenv("SUPABASE_ANON_KEY", "")
USER            = os.getenv("DASHBOARD_USER", "chairman")
PASS            = os.getenv("DASHBOARD_PASSWORD", "")
COMPANY         = os.getenv("COMPANY_NAME", "גבר יזמות ייעוץ עסקי והשקעות")
META_PAGE_TOKEN = os.getenv("META_PAGE_TOKEN", "")
META_PAGE_ID    = os.getenv("META_PAGE_ID", "")
INSTAGRAM_ID    = os.getenv("INSTAGRAM_ACCOUNT_ID", "")
WHATSAPP_TOKEN  = os.getenv("WHATSAPP_TOKEN", "")
WHATSAPP_PHONE  = os.getenv("WHATSAPP_PHONE_ID", "")

# ── App ───────────────────────────────────────────────────────
app = FastAPI(title="Jabr Management")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])
security = HTTPBasic(auto_error=False)

# ── Auth ──────────────────────────────────────────────────────
def verify_auth(creds: Optional[HTTPBasicCredentials] = Depends(security)) -> str:
    # auto_error=False + no WWW-Authenticate header = no browser native auth popup
    if creds and PASS and \
       secrets.compare_digest(creds.username.encode(), USER.encode()) and \
       secrets.compare_digest(creds.password.encode(), PASS.encode()):
        return creds.username
    raise HTTPException(status_code=401, detail="Unauthorized")

# ── Supabase ──────────────────────────────────────────────────
def sb_headers():
    return {"apikey": SB_KEY, "Authorization": f"Bearer {SB_KEY}",
            "Content-Type": "application/json", "Prefer": "return=representation"}

async def sb_get(table, params=""):
    if not SB_URL: return []
    try:
        async with httpx.AsyncClient() as c:
            url = f"{SB_URL}/rest/v1/{table}" + (f"?{params}" if params else "")
            r = await c.get(url, headers=sb_headers(), timeout=15)
            return r.json() if r.status_code == 200 else []
    except: return []

async def sb_ins(table, data):
    if not SB_URL: return {"id": "mock", **data}
    try:
        async with httpx.AsyncClient() as c:
            r = await c.post(f"{SB_URL}/rest/v1/{table}",
                headers=sb_headers(), json=data, timeout=15)
            res = r.json()
            return res[0] if isinstance(res, list) and res else \
                   res if isinstance(res, dict) else {"id": "ok"}
    except Exception as e: return {"id": "err", "e": str(e)}

# ── AI Agents ─────────────────────────────────────────────────
AGENTS = {
    "ceo":        ("דניאל כהן",      "מנכ\"ל",          "אתה דניאל כהן מנכ\"ל {co}. מתאם מחלקות, מחלק משימות, מסכם תוצאות."),
    "cfo":        ("מיכאל לוי",      "CFO",              "אתה מיכאל לוי CFO {co}. תזרים, תקציבים, ניתוח עלויות."),
    "marketing":  ("נועה שפירא",     "מנהלת שיווק",      "את נועה שפירא מנהלת שיווק {co}. קמפיינים ואסטרטגיה."),
    "sales":      ("רון אברהם",      "מנהל מכירות",      "אתה רון אברהם מנהל מכירות {co}."),
    "legal":      ("עו\"ד תמר גולן", "יועמ\"ש",          "את עו\"ד תמר גולן יועמ\"ש {co}."),
    "cto":        ("אלון בן-דוד",    "CTO",              "אתה אלון בן-דוד CTO {co}."),
    "content":    ("שיר מזרחי",      "מנהלת תוכן",       "את שיר מזרחי מנהלת תוכן {co}."),
    "pr":         ("גיל פרץ",        "מנהל יח\"צ",       "אתה גיל פרץ מנהל יח\"צ {co}."),
    "compliance": ("ד\"ר ענת רוזן",  "קצינת ציות",       "את ד\"ר ענת רוזן קצינת ציות {co}."),
    "hr":         ("יובל כץ",        "מנהל HR",          "אתה יובל כץ מנהל HR {co}."),
    "customer":   ("ליאת דביר",      "מנהלת שירות",      "את ליאת דביר מנהלת שירות לקוחות {co}."),
}
DMETA = {
    "ceo":        {"name": "מנכ\"ל",        "icon": "👑", "color": "#a78bfa"},
    "cfo":        {"name": "כספים",          "icon": "💰", "color": "#f5c842"},
    "marketing":  {"name": "שיווק",          "icon": "📣", "color": "#f87171"},
    "sales":      {"name": "מכירות",         "icon": "📈", "color": "#22d3a0"},
    "legal":      {"name": "משפטי",          "icon": "⚖️", "color": "#60a5fa"},
    "cto":        {"name": "טכנולוגיה",      "icon": "💻", "color": "#34d399"},
    "content":    {"name": "תוכן",           "icon": "🎨", "color": "#fb923c"},
    "pr":         {"name": "יח\"צ",          "icon": "📢", "color": "#e879f9"},
    "compliance": {"name": "ציות",           "icon": "🛡️", "color": "#94a3b8"},
    "hr":         {"name": "HR",             "icon": "👥", "color": "#4ade80"},
    "customer":   {"name": "שירות לקוחות",   "icon": "🎧", "color": "#38bdf8"},
}
EMPS = {
    "ceo":        [("יעל מזרחי","עוזרת מנכ\"ל"),("אסף ברק","מנהל פרויקטים"),("מיה לוין","רכזת"),("עומר שלום","אנליסט")],
    "cfo":        [("דנה כהן","חשבת"),("רועי פלד","אנליסט פיננסי"),("שרה לוי","גזברית"),("אמיר גל","מנהל תקציב")],
    "marketing":  [("נדב ביטון","מנהל דיגיטל"),("טל שר","מעצב גרפי"),("יונית אור","כותבת תוכן"),("עידן רז","SEO")],
    "sales":      [("ליאל דוד","נציג מכירות"),("הילה ים","מנהלת לקוחות"),("בן גבע","אנליסט"),("מור שגיא","נציגת מכירות")],
    "legal":      [("ניר אלון","עו\"ד"),("שירה רן","פרלגל"),("גבי מור","יועץ רגולציה"),("לי בן","מזכירת משפטים")],
    "cto":        [("ירון נוי","Full Stack"),("הדר עם","DevOps"),("ליר שן","Backend"),("כרמל אל","UX")],
    "content":    [("אביב כץ","צלם ועורך"),("ניל שר","מנהל סושיאל"),("עלמא פז","יוצרת תוכן"),("יאיר אף","YouTube")],
    "pr":         [("הילה דן","דוברת"),("רן שם","יחצ\"ן"),("שי לם","מנהל אירועים"),("מאיה ון","קשרי תקשורת")],
    "compliance": [("ורד נץ","קצינת ציות"),("תמר גן","מבקרת פנים"),("אלי קם","מנהל סיכונים"),("רינה שן","יועצת רגולציה")],
    "hr":         [("נועם בר","מגייסת"),("שלי גז","מנהלת רווחה"),("עמית לז","מנהל הכשרות"),("ציפי רם","יועצת ארגונית")],
    "customer":   [("דור כהן","נציג שירות"),("עינת שמ","נציגת שירות"),("אלון בר","מנהל תלונות"),("מרים כ","נציגת שירות")],
}

async def ai(role, msg, ctx=""):
    if not ANTHROPIC_KEY:
        return f"[{AGENTS.get(role, ('AI','',''))[0]}]: מפתח API לא מוגדר ב-Railway"
    n, t, sys_prompt = AGENTS.get(role, ("AI", "", "אתה עוזר מקצועי."))
    system = sys_prompt.replace("{co}", COMPANY)
    if ctx: system += f"\n\nהקשר:\n{ctx}"
    try:
        async with httpx.AsyncClient() as c:
            r = await c.post("https://api.anthropic.com/v1/messages",
                headers={"x-api-key": ANTHROPIC_KEY, "anthropic-version": "2023-06-01",
                         "content-type": "application/json"},
                json={"model": "claude-opus-4-6", "max_tokens": 1500,
                      "system": system, "messages": [{"role": "user", "content": msg}]},
                timeout=40)
            return r.json()["content"][0]["text"] if r.status_code == 200 else f"שגיאה {r.status_code}"
    except Exception as e: return f"שגיאת חיבור: {e}"

# ── API Routes ────────────────────────────────────────────────

@app.get("/api/verify")
async def verify(u=Depends(verify_auth)):
    return {"ok": True, "user": u}

@app.get("/api/health")
async def health():
    return {"status": "ok", "anthropic": bool(ANTHROPIC_KEY), "supabase": bool(SB_URL and SB_KEY)}

@app.get("/api/stats")
async def stats(u=Depends(verify_auth)):
    t  = await sb_get("tasks", "select=count")
    dn = await sb_get("tasks", "select=count&status=eq.done")
    def cnt(x): return x[0].get("count", 0) if isinstance(x, list) and x and isinstance(x[0], dict) else 0
    return {"tasks_total": cnt(t), "tasks_done": cnt(dn), "tasks_inprog": 0, "tasks_pending": 0,
            "departments": len(DMETA), "employees": sum(1 + len(v) for v in EMPS.values())}

@app.get("/api/departments")
async def depts(u=Depends(verify_auth)):
    return [{"id": k, "name": v["name"], "icon": v["icon"], "color": v["color"],
             "head": AGENTS[k][0], "title": AGENTS[k][1]} for k, v in DMETA.items()]

@app.get("/api/employees")
async def emps(dept: Optional[str] = None, u=Depends(verify_auth)):
    result = []
    for did in ([dept] if dept else list(DMETA.keys())):
        if did not in DMETA: continue
        ag = AGENTS.get(did)
        if ag: result.append({"id": f"{did}-0", "name": ag[0], "role": ag[1],
                               "department": did, "title": "מנהל", "status": "active"})
        for nm, rl in EMPS.get(did, []):
            result.append({"id": f"{did}-{nm}", "name": nm, "role": rl,
                           "department": did, "title": "עובד", "status": "active"})
    return result

@app.get("/api/tasks")
async def get_tasks(status: Optional[str] = None, dept: Optional[str] = None, u=Depends(verify_auth)):
    q = "order=created_at.desc&limit=50"
    if status: q += f"&status=eq.{status}"
    if dept:   q += f"&department=eq.{dept}"
    return await sb_get("tasks", q)

@app.post("/api/tasks")
async def create_task(req: Request, u=Depends(verify_auth)):
    b = await req.json()
    if not b.get("title", "").strip(): raise HTTPException(400, "נא להזין כותרת")
    return await sb_ins("tasks", {"title": b["title"], "description": b.get("description", ""),
        "department": b.get("department", "ceo"), "priority": b.get("priority", "medium"),
        "status": "pending", "created_by": u, "created_at": datetime.utcnow().isoformat()})

@app.post("/api/tasks/{tid}/approve")
async def approve(tid: str, u=Depends(verify_auth)):
    if SB_URL:
        async with httpx.AsyncClient() as c:
            await c.patch(f"{SB_URL}/rest/v1/tasks?id=eq.{tid}",
                headers=sb_headers(), json={"status": "approved"}, timeout=10)
    return {"ok": True}

@app.post("/api/instruct")
async def instruct(req: Request, u=Depends(verify_auth)):
    b = await req.json()
    inst = b.get("instruction", "").strip()
    if not inst: raise HTTPException(400, "נא לכתוב הוראה")
    resp = await ai("ceo", f'קיבלת הוראה מיו"ר:\n"{inst}"\n\n1.נתח 2.אילו מחלקות? 3.תוכנית פעולה 4.ציר זמן')
    await sb_ins("instructions", {"text": inst, "ceo_response": resp,
                                  "status": "processing", "created_at": datetime.utcnow().isoformat()})
    return {"instruction": inst, "ceo_response": resp}

@app.get("/api/instructions")
async def get_insts(u=Depends(verify_auth)):
    return await sb_get("instructions", "order=created_at.desc&limit=20")

@app.post("/api/chat/{dept}")
async def chat(dept: str, req: Request, u=Depends(verify_auth)):
    b = await req.json()
    msg  = b.get("message", "")
    hist = b.get("history", [])
    ctx  = "\n".join([f"{m['role']}: {m['content']}" for m in hist[-8:]])
    resp = await ai(dept, msg, ctx)
    await sb_ins("chat_messages", {"department": dept, "user_message": msg,
                                   "ai_response": resp, "created_at": datetime.utcnow().isoformat()})
    ag = AGENTS.get(dept, ("AI", "", ""))
    return {"response": resp, "agent": ag[0], "title": ag[1]}

@app.post("/api/meetings")
async def meeting(req: Request, u=Depends(verify_auth)):
    b     = await req.json()
    topic = b.get("topic", "")
    agenda = b.get("agenda", "")
    dpts  = b.get("departments", ["ceo"])
    rs = {}
    for d in dpts[:5]:
        rs[d] = await ai(d, f'ישיבה: {topic}\nסדר יום: {agenda}\nמה עמדתך?')
    await sb_ins("meetings", {"topic": topic, "agenda": agenda,
                              "responses": json.dumps(rs, ensure_ascii=False),
                              "status": "completed", "created_at": datetime.utcnow().isoformat()})
    return {"responses": rs}

@app.get("/api/meetings")
async def get_meetings(u=Depends(verify_auth)):
    return await sb_get("meetings", "order=created_at.desc&limit=20")

@app.post("/api/reports/generate")
async def gen_rep(req: Request, u=Depends(verify_auth)):
    b    = await req.json()
    dept = b.get("department", "ceo")
    rt   = b.get("type", "weekly")
    dn   = DMETA.get(dept, {}).get("name", dept)
    content = await ai(dept, f'צור דוח {rt} למחלקת {dn}. כלול: סיכום, הישגים, אתגרים, תוכנית.')
    r = {"title": f'דוח {rt} – {dn}', "department": dept, "content": content,
         "type": rt, "created_at": datetime.utcnow().isoformat()}
    await sb_ins("reports", r)
    return {"report": r}

@app.get("/api/reports")
async def get_reps(u=Depends(verify_auth)):
    return await sb_get("reports", "order=created_at.desc&limit=20")

@app.get("/api/approvals")
async def approvals(u=Depends(verify_auth)):
    return await sb_get("tasks", "status=eq.pending_approval&order=created_at.desc")

@app.post("/api/strategy/goals")
async def set_goals(req: Request, u=Depends(verify_auth)):
    b     = await req.json()
    goals = b.get("goals", "").strip()
    if not goals: raise HTTPException(400, "נא להזין יעדים")
    plan = await ai("ceo", f'יו"ר הציב יעדים:\n{goals}\n\nצור תוכנית: 1.פירוט 2.לו"ז 3.KPIs 4.סיכונים 5.תקציב')
    await sb_ins("strategic_goals", {"goals": goals, "plan": plan,
                                     "status": "active", "created_at": datetime.utcnow().isoformat()})
    return {"goals": goals, "plan": plan}

@app.get("/api/strategy/goals")
async def get_goals(u=Depends(verify_auth)):
    return await sb_get("strategic_goals", "order=created_at.desc&limit=10")

@app.get("/api/cashflow")
async def get_cf(u=Depends(verify_auth)):
    return await sb_get("cashflow", "order=date.desc&limit=200")

@app.post("/api/cashflow")
async def add_cf(req: Request, u=Depends(verify_auth)):
    b = await req.json()
    try: amt = float(b.get("amount", 0))
    except: raise HTTPException(400, "סכום לא תקין")
    return await sb_ins("cashflow", {
        "date":        b.get("date", datetime.utcnow().date().isoformat()),
        "description": b.get("description", ""),
        "amount":      amt,
        "type":        b.get("type", "income"),
        "category":    b.get("category", "כללי"),
        "client_id":   b.get("client_id", ""),
        "created_at":  datetime.utcnow().isoformat()
    })

@app.post("/api/cashflow/analyze")
async def analyze_cf(u=Depends(verify_auth)):
    rows = await sb_get("cashflow", "order=date.desc&limit=100")
    if not rows: return {"analysis": "אין נתוני תזרים עדיין.", "rows": []}
    ti = sum(float(r.get("amount", 0)) for r in rows if r.get("type") == "income")
    to = sum(float(r.get("amount", 0)) for r in rows if r.get("type") == "expense")
    a  = await ai("cfo", f'תזרים: הכנסות={ti:,.0f}₪ הוצאות={to:,.0f}₪ יתרה={ti-to:,.0f}₪\nנתח ותן המלצות.')
    return {"analysis": a, "rows": rows, "summary": {"income": ti, "expense": to, "balance": ti - to}}

@app.post("/api/social/generate")
async def gen_post(req: Request, u=Depends(verify_auth)):
    b = await req.json()
    p = await ai("content", f'כתוב פוסט לסושיאל בנושא: {b.get("topic","")}\nכלול כותרת, גוף, CTA, האשטגים.')
    return {"post": p}

@app.post("/api/social/publish")
async def pub_post(req: Request, u=Depends(verify_auth)):
    b = await req.json()
    if not b.get("text", ""): raise HTTPException(400, "נא לכתוב תוכן")
    results = {}
    txt   = b["text"]
    img   = b.get("image_url", "")
    plats = b.get("platforms", [])
    if "facebook" in plats and META_PAGE_TOKEN and META_PAGE_ID:
        async with httpx.AsyncClient() as c:
            r = await c.post(f"https://graph.facebook.com/v19.0/{META_PAGE_ID}/feed",
                data={"message": txt, "access_token": META_PAGE_TOKEN}, timeout=20)
            res = r.json()
            results["facebook"] = {"ok": "id" in res, "post_id": res.get("id"),
                                   "error": res.get("error", {}).get("message")}
    elif "facebook" in plats:
        results["facebook"] = {"ok": False, "error": "חסר META_PAGE_TOKEN ב-Railway"}
    if "instagram" in plats and META_PAGE_TOKEN and INSTAGRAM_ID and img:
        async with httpx.AsyncClient() as c:
            r1 = await c.post(f"https://graph.facebook.com/v19.0/{INSTAGRAM_ID}/media",
                data={"image_url": img, "caption": txt, "access_token": META_PAGE_TOKEN}, timeout=20)
            mid = r1.json().get("id")
            if mid:
                r2 = await c.post(f"https://graph.facebook.com/v19.0/{INSTAGRAM_ID}/media_publish",
                    data={"creation_id": mid, "access_token": META_PAGE_TOKEN}, timeout=20)
                res = r2.json()
                results["instagram"] = {"ok": "id" in res, "post_id": res.get("id")}
            else:
                results["instagram"] = {"ok": False,
                                        "error": r1.json().get("error", {}).get("message", "שגיאה")}
    elif "instagram" in plats:
        results["instagram"] = {"ok": False, "error": "חסר INSTAGRAM_ACCOUNT_ID או תמונה"}
    if "whatsapp" in plats:
        phone = b.get("whatsapp_phone", "")
        if phone and WHATSAPP_TOKEN and WHATSAPP_PHONE:
            async with httpx.AsyncClient() as c:
                r = await c.post(f"https://graph.facebook.com/v19.0/{WHATSAPP_PHONE}/messages",
                    headers={"Authorization": f"Bearer {WHATSAPP_TOKEN}",
                             "Content-Type": "application/json"},
                    json={"messaging_product": "whatsapp", "to": phone,
                          "type": "text", "text": {"body": txt}}, timeout=20)
                res = r.json()
                results["whatsapp"] = {"ok": "messages" in res,
                                       "error": res.get("error", {}).get("message")}
        else:
            results["whatsapp"] = {"ok": False, "error": "חסר WHATSAPP_TOKEN או מספר"}
    await sb_ins("social_posts", {
        "text": txt, "image_url": img, "platforms": json.dumps(plats),
        "results": json.dumps(results, ensure_ascii=False),
        "status": "published" if any(r.get("ok") for r in results.values()) else "pending",
        "created_at": datetime.utcnow().isoformat()
    })
    return {"text": txt, "results": results}

@app.get("/api/social/posts")
async def get_posts(u=Depends(verify_auth)):
    return await sb_get("social_posts", "order=created_at.desc&limit=30")

LOGIN_HTML = '''<!DOCTYPE html>
<html lang="he" dir="rtl"><head>
<meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>גבר – כניסה</title>
<style>
@import url('https://fonts.googleapis.com/css2?family=Heebo:wght@400;600;700;800&display=swap');
*{box-sizing:border-box;margin:0;padding:0}
body{font-family:'Heebo',sans-serif;min-height:100vh;display:flex;align-items:center;justify-content:center;
  background:radial-gradient(ellipse at 20% 50%,#1a0a4a,#0d1a3a 40%,#060b18)}
.card{background:rgba(22,25,33,.92);backdrop-filter:blur(20px);border:1px solid rgba(167,139,250,.2);
  border-radius:20px;padding:40px 32px;width:100%;max-width:380px;box-shadow:0 0 60px rgba(108,99,255,.2)}
.logo{text-align:center;margin-bottom:24px}
.logo-ic{width:64px;height:64px;background:linear-gradient(135deg,#6c63ff,#a78bfa);border-radius:16px;
  display:inline-flex;align-items:center;justify-content:center;font-size:30px;margin-bottom:10px}
.logo-n{font-size:18px;font-weight:800;color:#e8eaf0}
.logo-s{font-size:11px;color:#8892a4}
.field{margin-bottom:14px}
label{display:block;font-size:11px;color:#8892a4;margin-bottom:5px;font-weight:600;text-transform:uppercase}
input{width:100%;background:rgba(13,15,20,.7);border:1px solid rgba(167,139,250,.2);border-radius:9px;
  color:#e8eaf0;font-family:'Heebo',sans-serif;font-size:14px;padding:11px 13px;direction:rtl;outline:none}
input:focus{border-color:#6c63ff}
.btn{width:100%;background:linear-gradient(135deg,#6c63ff,#8b5cf6);color:#fff;border:none;
  border-radius:9px;font-family:'Heebo',sans-serif;font-size:15px;font-weight:700;
  padding:13px;cursor:pointer;margin-top:4px}
.btn:hover{opacity:.88}
.err{background:rgba(248,113,113,.1);border:1px solid rgba(248,113,113,.3);border-radius:7px;
  padding:8px 12px;font-size:12px;color:#f87171;margin-top:8px;display:none;text-align:center}
</style></head>
<body>
<div class="card">
  <div class="logo">
    <div class="logo-ic">🏢</div>
    <div class="logo-n">גבר יזמות ייעוץ עסקי</div>
    <div class="logo-s">AI Company Management System</div>
  </div>
  <div class="field"><label>שם משתמש</label>
    <input id="u" type="text" placeholder="chairman" autocomplete="username"></div>
  <div class="field"><label>סיסמה</label>
    <input id="p" type="password" placeholder="••••••••"
      onkeydown="if(event.key==='Enter')doLogin()"></div>
  <button class="btn" id="btn" onclick="doLogin()">🔐 כניסה למערכת</button>
  <div class="err" id="err"></div>
</div>
<script>
async function doLogin(){
  const u=document.getElementById('u').value.trim();
  const p=document.getElementById('p').value.trim();
  if(!u||!p)return;
  const btn=document.getElementById('btn');
  btn.textContent='...מתחבר';btn.disabled=true;
  document.getElementById('err').style.display='none';
  try{
    const token=btoa(u+':'+p);
    const r=await fetch('/api/verify',{headers:{Authorization:'Basic '+token}});
    if(r.ok){
      sessionStorage.setItem('jauth',token);
      window.location.replace('/dashboard#'+token);
    }else{
      document.getElementById('err').textContent='שם משתמש או סיסמה שגויים';
      document.getElementById('err').style.display='block';
    }
  }catch(e){
    document.getElementById('err').textContent='שגיאת חיבור: '+e.message;
    document.getElementById('err').style.display='block';
  }
  btn.textContent='🔐 כניסה למערכת';btn.disabled=false;
}
</script>
</body></html>'''

DASHBOARD_HTML = '''<!DOCTYPE html>
<html lang="he" dir="rtl"><head>
<meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>גבר – ניהול AI</title>
<style>
@import url('https://fonts.googleapis.com/css2?family=Heebo:wght@300;400;500;600;700;800&display=swap');
:root{--bg:#0d0f14;--sur:#161921;--card:#1c2030;--bdr:#252a3a;--ac:#6c63ff;--ac2:#a78bfa;
  --gld:#f5c842;--grn:#22d3a0;--red:#f87171;--org:#fb923c;--tx:#e8eaf0;--mt:#8892a4;--r:11px}
*{box-sizing:border-box;margin:0;padding:0}
body{font-family:'Heebo',sans-serif;background:var(--bg);color:var(--tx);min-height:100vh}
.hdr{background:linear-gradient(135deg,#1a0a4a,#0d1a3a,#0a1520);border-bottom:1px solid var(--bdr);
  padding:0 16px;display:flex;align-items:center;justify-content:space-between;height:56px;position:sticky;top:0;z-index:100}
.hl{display:flex;align-items:center;gap:9px}
.hic{width:34px;height:34px;background:linear-gradient(135deg,var(--ac),var(--ac2));border-radius:8px;display:flex;align-items:center;justify-content:center;font-size:17px}
.ht{font-weight:700;font-size:14px}.hs{font-size:10px;color:var(--mt)}
.bon{background:rgba(34,211,160,.15);color:var(--grn);border:1px solid rgba(34,211,160,.3);border-radius:20px;padding:3px 9px;font-size:11px}
.bex{background:rgba(248,113,113,.15);color:var(--red);border:1px solid rgba(248,113,113,.3);border-radius:7px;padding:4px 11px;font-size:11px;cursor:pointer;font-family:inherit}
.tabs{background:var(--sur);border-bottom:1px solid var(--bdr);padding:0 16px;display:flex;gap:0;overflow-x:auto;scrollbar-width:none}
.tabs::-webkit-scrollbar{display:none}
.tb{background:none;border:none;color:var(--mt);font-family:inherit;font-size:11px;font-weight:500;
  padding:11px 10px;cursor:pointer;white-space:nowrap;border-bottom:2px solid transparent;transition:all .2s}
.tb:hover{color:var(--tx)}.tb.active{color:var(--ac2);border-bottom-color:var(--ac2)}
.wrap{padding:16px;max-width:1400px;margin:0 auto}
.panel{display:none}.panel.active{display:block}
.stats{display:grid;grid-template-columns:repeat(3,1fr);gap:8px;margin-bottom:14px}
.stat{background:var(--card);border:1px solid var(--bdr);border-radius:var(--r);padding:13px 10px;text-align:center}
.sn{font-size:24px;font-weight:800;color:var(--ac2);line-height:1;margin-bottom:3px}
.sl{font-size:10px;color:var(--mt)}
.card{background:var(--card);border:1px solid var(--bdr);border-radius:var(--r);padding:15px;margin-bottom:12px}
.ct{font-size:13px;font-weight:700;margin-bottom:12px;display:flex;align-items:center;gap:6px}
textarea,input[type=text],select{width:100%;background:var(--sur);border:1px solid var(--bdr);
  border-radius:7px;color:var(--tx);font-family:inherit;font-size:13px;padding:9px 11px;direction:rtl;outline:none}
textarea:focus,input[type=text]:focus,select:focus{border-color:var(--ac)}
textarea{resize:vertical;min-height:75px}
select option{background:var(--card)}
label{display:block;font-size:11px;color:var(--mt);margin-bottom:4px}
.fg{margin-bottom:10px}
.fr{display:grid;grid-template-columns:1fr 1fr;gap:8px}
.btn{display:inline-flex;align-items:center;gap:4px;background:linear-gradient(135deg,var(--ac),#8b5cf6);
  color:#fff;border:none;border-radius:7px;padding:8px 14px;font-family:inherit;font-size:12px;font-weight:700;cursor:pointer}
.btn:hover{opacity:.85}.btn:disabled{opacity:.5;cursor:not-allowed}
.bsm{padding:5px 10px;font-size:11px}
.bg{background:linear-gradient(135deg,#059669,var(--grn))}
.bo{background:none;border:1px solid var(--bdr);color:var(--tx)}
.bo:hover{border-color:var(--ac);color:var(--ac2)}
.rb{background:var(--sur);border:1px solid var(--bdr);border-radius:7px;padding:12px;margin-top:10px;
  font-size:12px;line-height:1.7;white-space:pre-wrap;display:none}
.rb.show{display:block}
.rl{font-size:10px;color:var(--ac2);font-weight:700;margin-bottom:6px;text-transform:uppercase}
.dg{display:grid;grid-template-columns:repeat(auto-fill,minmax(130px,1fr));gap:8px}
.dc{background:var(--sur);border:1px solid var(--bdr);border-radius:var(--r);padding:11px;cursor:pointer;transition:all .2s;text-align:center}
.dc:hover{transform:translateY(-2px);border-color:var(--ac)}
.di{font-size:22px;margin-bottom:5px}.dn{font-size:11px;font-weight:700}
.dh{font-size:10px;color:var(--mt);margin-top:2px}.dt{font-size:9px;color:var(--ac2);margin-top:1px}
.chat-wrap{display:grid;grid-template-columns:155px 1fr;gap:10px;height:560px}
.chat-side{background:var(--sur);border:1px solid var(--bdr);border-radius:var(--r);overflow-y:auto}
.ca{width:100%;background:none;border:none;border-bottom:1px solid var(--bdr);color:var(--tx);
  font-family:inherit;font-size:11px;padding:8px 9px;cursor:pointer;text-align:right;
  display:flex;flex-direction:column;align-items:flex-end;gap:1px;transition:background .15s}
.ca:hover{background:rgba(108,99,255,.08)}.ca.active{background:rgba(167,139,250,.12);color:var(--ac2)}
.ca-n{font-weight:700;font-size:11px}.ca-r{font-size:9px;color:var(--mt)}
.chat-main{background:var(--sur);border:1px solid var(--bdr);border-radius:var(--r);display:flex;flex-direction:column;overflow:hidden}
.chat-hdr{padding:10px 13px;border-bottom:1px solid var(--bdr);font-weight:700;font-size:12px;flex-shrink:0}
.chat-msgs{flex:1;overflow-y:auto;padding:10px;display:flex;flex-direction:column;gap:7px;min-height:0}
.msg{padding:8px 11px;border-radius:10px;font-size:12px;line-height:1.6;max-width:88%;word-wrap:break-word}
.mu{background:linear-gradient(135deg,var(--ac),#8b5cf6);align-self:flex-start;border-radius:10px 10px 10px 2px}
.ma{background:var(--card);border:1px solid var(--bdr);align-self:flex-end;border-radius:10px 10px 2px 10px}
.mn{font-size:9px;color:var(--ac2);font-weight:700;margin-bottom:2px}
.chat-in{padding:9px;border-top:1px solid var(--bdr);display:flex;gap:6px;flex-shrink:0}
.ci{flex:1;background:var(--card);border:1px solid var(--bdr);border-radius:7px;color:var(--tx);
  font-family:inherit;font-size:12px;padding:8px 10px;direction:rtl;outline:none;resize:none;height:36px}
.ci:focus{border-color:var(--ac)}
.ti{background:var(--sur);border:1px solid var(--bdr);border-radius:8px;padding:10px 12px;margin-bottom:6px;display:flex;align-items:center;gap:8px}
.tdot{width:7px;height:7px;border-radius:50%;flex-shrink:0}
.dp{background:var(--org)}.di2{background:var(--ac2)}.dd{background:var(--grn)}.da{background:var(--gld)}
.ti-i{flex:1;min-width:0}
.ti-t{font-size:12px;font-weight:600;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
.ti-m{font-size:10px;color:var(--mt);margin-top:2px}
.tag{background:rgba(108,99,255,.15);color:var(--ac2);border:1px solid rgba(108,99,255,.3);border-radius:5px;padding:1px 6px;font-size:10px;white-space:nowrap;flex-shrink:0}
.tg{background:rgba(34,211,160,.15);color:var(--grn);border-color:rgba(34,211,160,.3)}
.to{background:rgba(251,146,60,.15);color:var(--org);border-color:rgba(251,146,60,.3)}
.ty{background:rgba(245,200,66,.15);color:var(--gld);border-color:rgba(245,200,66,.3)}
.etbl{width:100%;border-collapse:collapse;font-size:11px}
.etbl th{background:var(--sur);padding:8px 9px;text-align:right;font-weight:600;color:var(--mt);font-size:10px;border-bottom:1px solid var(--bdr)}
.etbl td{padding:8px 9px;border-bottom:1px solid rgba(37,42,58,.3)}
.etbl tr:hover td{background:rgba(108,99,255,.03)}
.av{width:24px;height:24px;border-radius:50%;background:linear-gradient(135deg,var(--ac),var(--ac2));display:inline-flex;align-items:center;justify-content:center;font-size:10px;font-weight:700;margin-left:6px;flex-shrink:0}
.pb{background:var(--sur);border:1px solid var(--bdr);border-radius:8px;padding:8px 12px;cursor:pointer;font-family:inherit;font-size:12px;color:var(--mt);display:flex;align-items:center;gap:5px}
.pb.sel{border-color:var(--ac2);color:var(--ac2);background:rgba(167,139,250,.08)}
.cf-s{display:grid;grid-template-columns:repeat(3,1fr);gap:8px;margin-bottom:12px}
.cfs{background:var(--sur);border:1px solid var(--bdr);border-radius:8px;padding:10px;text-align:center}
.cfn{font-size:18px;font-weight:800;margin-bottom:2px}
.cfl{font-size:10px;color:var(--mt)}
.cft{width:100%;border-collapse:collapse;font-size:11px}
.cft th{background:var(--sur);padding:7px 9px;text-align:right;font-weight:600;color:var(--mt);font-size:9px;border-bottom:1px solid var(--bdr)}
.cft td{padding:7px 9px;border-bottom:1px solid rgba(37,42,58,.3)}
.cin{color:var(--grn)}.cout{color:var(--red)}
.dr{border-right:3px solid var(--ac);padding:6px 9px;margin-bottom:5px;background:rgba(108,99,255,.04);border-radius:0 5px 5px 0;font-size:11px;line-height:1.6}
.drn{font-size:9px;color:var(--ac2);font-weight:700;margin-bottom:2px}
.sp{display:inline-block;width:13px;height:13px;border:2px solid rgba(167,139,250,.3);border-top-color:var(--ac2);border-radius:50%;animation:spin .7s linear infinite}
@keyframes spin{to{transform:rotate(360deg)}}
.conn-r{padding:9px 11px;background:var(--sur);border:1px solid var(--bdr);border-radius:7px;display:flex;justify-content:space-between;margin-bottom:6px;font-size:12px}
@media(max-width:600px){
  .fr{grid-template-columns:1fr}
  .chat-wrap{grid-template-columns:1fr;height:auto}
  .chat-side{display:flex;overflow-x:auto;height:44px;border-radius:8px}
  .ca{flex-direction:row;border-bottom:none;border-left:1px solid var(--bdr);white-space:nowrap;flex-shrink:0;padding:6px 8px}
  .ca-r{display:none}.chat-main{height:420px}
  .cf-s{grid-template-columns:1fr}
}
</style></head>
<body>
<div class="hdr">
  <div class="hl">
    <div class="hic">🏢</div>
    <div><div class="ht">גבר יזמות ייעוץ עסקי</div><div class="hs">AI Company Management System</div></div>
  </div>
  <div style="display:flex;align-items:center;gap:7px">
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
  <button class="tb" onclick="T('depts',this)">🏢 מחלקות</button>
  <button class="tb" onclick="T('meetings',this)">📅 ישיבות</button>
  <button class="tb" onclick="T('social',this)">📱 סושיאל</button>
  <button class="tb" onclick="T('cashflow',this)">💳 תזרים</button>
  <button class="tb" onclick="T('reports',this)">📊 דוחות</button>
  <button class="tb" onclick="T('strategy',this)">🎯 אסטרטגיה</button>
  <button class="tb" onclick="T('approvals',this)">✅ אישורים</button>
  <button class="tb" onclick="T('settings',this)">⚙️ הגדרות</button>
</div>

<div class="wrap">

<!-- HOME -->
<div id="p-home" class="panel active">
  <div class="stats">
    <div class="stat"><div class="sn" id="s-tasks">–</div><div class="sl">משימות</div></div>
    <div class="stat"><div class="sn" id="s-depts">11</div><div class="sl">מחלקות</div></div>
    <div class="stat"><div class="sn" id="s-emps">–</div><div class="sl">עובדים</div></div>
  </div>
  <div class="card">
    <div class="ct">📡 סטטוס מערכת</div>
    <div id="conn-status">בודק חיבורים...</div>
  </div>
  <div class="card">
    <div class="ct">🏢 מחלקות פעילות</div>
    <div class="dg" id="home-depts"></div>
  </div>
</div>

<!-- INSTRUCT -->
<div id="p-instruct" class="panel">
  <div class="card">
    <div class="ct">📋 הוראה ליו"ר</div>
    <div class="fg"><label>הוראה למנכ"ל</label>
      <textarea id="inst-txt" placeholder="כתוב הוראה..."></textarea></div>
    <button class="btn" onclick="sendInst()">📤 שלח הוראה</button>
    <div class="rb" id="inst-resp"><div class="rl">תגובת המנכ"ל</div><div id="inst-resp-txt"></div></div>
  </div>
  <div class="card">
    <div class="ct">📜 היסטוריית הוראות</div>
    <div id="inst-hist"></div>
  </div>
</div>

<!-- TASKS -->
<div id="p-tasks" class="panel">
  <div class="card">
    <div class="ct">➕ משימה חדשה</div>
    <div class="fr">
      <div class="fg"><label>כותרת</label><input type="text" id="t-title" placeholder="כותרת המשימה"></div>
      <div class="fg"><label>מחלקה</label>
        <select id="t-dept"><option value="ceo">מנכ"ל</option><option value="cfo">כספים</option>
          <option value="marketing">שיווק</option><option value="sales">מכירות</option>
          <option value="legal">משפטי</option><option value="cto">טכנולוגיה</option>
          <option value="content">תוכן</option><option value="pr">יח"צ</option>
          <option value="compliance">ציות</option><option value="hr">HR</option>
          <option value="customer">שירות לקוחות</option></select></div>
    </div>
    <div class="fg"><label>תיאור</label><textarea id="t-desc" placeholder="תיאור..."></textarea></div>
    <div class="fr">
      <div class="fg"><label>עדיפות</label>
        <select id="t-pri"><option value="high">גבוהה</option><option value="medium" selected>בינונית</option><option value="low">נמוכה</option></select></div>
    </div>
    <button class="btn" onclick="createTask()">➕ צור משימה</button>
  </div>
  <div class="card">
    <div class="ct">📋 משימות</div>
    <div id="tasks-list"></div>
  </div>
</div>

<!-- EMPLOYEES -->
<div id="p-employees" class="panel">
  <div class="card">
    <div class="ct">👥 עובדים לפי מחלקה</div>
    <div class="fg"><label>סנן לפי מחלקה</label>
      <select id="emp-dept-filter" onchange="loadEmp()">
        <option value="">כל המחלקות</option>
        <option value="ceo">מנכ"ל</option><option value="cfo">כספים</option>
        <option value="marketing">שיווק</option><option value="sales">מכירות</option>
        <option value="legal">משפטי</option><option value="cto">טכנולוגיה</option>
        <option value="content">תוכן</option><option value="pr">יח"צ</option>
        <option value="compliance">ציות</option><option value="hr">HR</option>
        <option value="customer">שירות לקוחות</option>
      </select></div>
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
      <div class="chat-in">
        <textarea class="ci" id="chat-inp" placeholder="כתוב הודעה..." rows="1"
          onkeydown="if(event.key==='Enter'&&!event.shiftKey){event.preventDefault();sendChat()}"></textarea>
        <button class="btn bsm" onclick="sendChat()">⬆</button>
      </div>
    </div>
  </div>
</div>

<!-- DEPTS -->
<div id="p-depts" class="panel">
  <div class="card">
    <div class="ct">🏢 מחלקות החברה</div>
    <div class="dg" id="depts-grid"></div>
  </div>
</div>

<!-- MEETINGS -->
<div id="p-meetings" class="panel">
  <div class="card">
    <div class="ct">📅 ישיבה חדשה</div>
    <div class="fg"><label>נושא הישיבה</label><input type="text" id="m-topic" placeholder="נושא..."></div>
    <div class="fg"><label>סדר יום</label><textarea id="m-agenda" placeholder="פרט את סדר היום..."></textarea></div>
    <div class="fg"><label>מחלקות משתתפות</label>
      <div style="display:flex;flex-wrap:wrap;gap:6px;margin-top:4px" id="m-depts">
        <button class="pb sel" data-d="ceo" onclick="toggleDept(this)">👑 מנכ"ל</button>
        <button class="pb" data-d="cfo" onclick="toggleDept(this)">💰 כספים</button>
        <button class="pb" data-d="marketing" onclick="toggleDept(this)">📣 שיווק</button>
        <button class="pb" data-d="sales" onclick="toggleDept(this)">📈 מכירות</button>
        <button class="pb" data-d="legal" onclick="toggleDept(this)">⚖️ משפטי</button>
        <button class="pb" data-d="cto" onclick="toggleDept(this)">💻 טכנולוגיה</button>
      </div></div>
    <button class="btn" onclick="createMeeting()">📅 כנס ישיבה</button>
    <div class="rb" id="meeting-resp"><div class="rl">סיכום הישיבה</div><div id="meeting-resp-txt"></div></div>
  </div>
  <div class="card">
    <div class="ct">📜 ישיבות קודמות</div>
    <div id="meetings-list"></div>
  </div>
</div>

<!-- SOCIAL -->
<div id="p-social" class="panel">
  <div class="card">
    <div class="ct">✍️ צור פוסט</div>
    <div class="fg"><label>נושא הפוסט</label><input type="text" id="soc-topic" placeholder="נושא..."></div>
    <button class="btn" onclick="genPost()">🤖 צור פוסט AI</button>
    <div class="rb" id="post-gen"><div class="rl">פוסט שנוצר</div>
      <textarea id="post-txt" style="background:transparent;border:none;width:100%;color:var(--tx);font-family:inherit;font-size:12px;line-height:1.7;resize:none;outline:none;min-height:120px"></textarea></div>
  </div>
  <div class="card">
    <div class="ct">📤 פרסם פוסט</div>
    <div class="fg"><label>פלטפורמות</label>
      <div style="display:flex;gap:8px;flex-wrap:wrap;margin-top:4px">
        <button class="pb" data-p="facebook" onclick="togglePlat(this)">📘 Facebook</button>
        <button class="pb" data-p="instagram" onclick="togglePlat(this)">📷 Instagram</button>
        <button class="pb" data-p="whatsapp" onclick="togglePlat(this)">💬 WhatsApp</button>
      </div></div>
    <div class="fg" id="wa-phone-wrap" style="display:none">
      <label>מספר WhatsApp</label><input type="text" id="wa-phone" placeholder="+972501234567"></div>
    <div class="fg"><label>URL תמונה (אופציונלי)</label><input type="text" id="post-img" placeholder="https://..."></div>
    <button class="btn bg" onclick="publishPost()">📤 פרסם</button>
    <div class="rb" id="pub-result"><div class="rl">תוצאות פרסום</div><div id="pub-txt"></div></div>
  </div>
  <div class="card">
    <div class="ct">📋 פוסטים שפורסמו</div>
    <div id="posts-list"></div>
  </div>
</div>

<!-- CASHFLOW -->
<div id="p-cashflow" class="panel">
  <div class="cf-s">
    <div class="cfs"><div class="cfn cin" id="cf-in">₪0</div><div class="cfl">הכנסות</div></div>
    <div class="cfs"><div class="cfn cout" id="cf-out">₪0</div><div class="cfl">הוצאות</div></div>
    <div class="cfs"><div class="cfn" id="cf-bal">₪0</div><div class="cfl">יתרה</div></div>
  </div>
  <div class="card">
    <div class="ct">➕ הוסף תנועה</div>
    <div class="fr">
      <div class="fg"><label>תיאור</label><input type="text" id="cf-desc" placeholder="תיאור..."></div>
      <div class="fg"><label>סכום (₪)</label><input type="text" id="cf-amt" placeholder="0"></div>
    </div>
    <div class="fr">
      <div class="fg"><label>סוג</label>
        <select id="cf-type"><option value="income">הכנסה</option><option value="expense">הוצאה</option></select></div>
      <div class="fg"><label>קטגוריה</label><input type="text" id="cf-cat" placeholder="כללי"></div>
    </div>
    <div class="fg"><label>תאריך</label><input type="text" id="cf-date" placeholder="YYYY-MM-DD"></div>
    <button class="btn" onclick="addCF()">➕ הוסף</button>
  </div>
  <div class="card">
    <div class="ct">📊 ניתוח AI</div>
    <button class="btn" onclick="analyzeCF()">🤖 נתח תזרים</button>
    <div class="rb" id="cf-analysis"><div class="rl">ניתוח CFO</div><div id="cf-anal-txt"></div></div>
  </div>
  <div class="card">
    <div class="ct">📋 תנועות</div>
    <table class="cft"><thead><tr>
      <th>תאריך</th><th>תיאור</th><th>סוג</th><th>סכום</th>
    </tr></thead><tbody id="cf-rows"></tbody></table>
  </div>
</div>

<!-- REPORTS -->
<div id="p-reports" class="panel">
  <div class="card">
    <div class="ct">📊 צור דוח</div>
    <div class="fr">
      <div class="fg"><label>מחלקה</label>
        <select id="r-dept"><option value="ceo">מנכ"ל</option><option value="cfo">כספים</option>
          <option value="marketing">שיווק</option><option value="sales">מכירות</option>
          <option value="legal">משפטי</option><option value="cto">טכנולוגיה</option>
          <option value="content">תוכן</option><option value="pr">יח"צ</option>
          <option value="compliance">ציות</option><option value="hr">HR</option>
          <option value="customer">שירות לקוחות</option></select></div>
      <div class="fg"><label>סוג דוח</label>
        <select id="r-type"><option value="weekly">שבועי</option><option value="monthly">חודשי</option>
          <option value="quarterly">רבעוני</option><option value="annual">שנתי</option></select></div>
    </div>
    <button class="btn" onclick="genRep()">📊 צור דוח</button>
    <div class="rb" id="rep-result"><div class="rl">דוח שנוצר</div><div id="rep-txt"></div></div>
  </div>
  <div class="card">
    <div class="ct">📁 דוחות קודמים</div>
    <div id="reports-list"></div>
  </div>
</div>

<!-- STRATEGY -->
<div id="p-strategy" class="panel">
  <div class="card">
    <div class="ct">🎯 יעדים אסטרטגיים</div>
    <div class="fg"><label>יעדים</label>
      <textarea id="goals-txt" placeholder="פרט את היעדים האסטרטגיים..." style="min-height:100px"></textarea></div>
    <button class="btn" onclick="setGoals()">🎯 הגדר יעדים</button>
    <div class="rb" id="goals-resp"><div class="rl">תוכנית אסטרטגית</div><div id="goals-txt2"></div></div>
  </div>
  <div class="card">
    <div class="ct">📜 יעדים קיימים</div>
    <div id="goals-list"></div>
  </div>
</div>

<!-- APPROVALS -->
<div id="p-approvals" class="panel">
  <div class="card">
    <div class="ct">✅ ממתינים לאישור</div>
    <div id="approvals-list"></div>
  </div>
</div>

<!-- SETTINGS -->
<div id="p-settings" class="panel">
  <div class="card">
    <div class="ct">⚙️ הגדרות מערכת</div>
    <div id="settings-conn"></div>
  </div>
  <div class="card">
    <div class="ct">👤 פרטי חשבון</div>
    <div style="font-size:12px;line-height:2;color:var(--mt)">
      <div>חברה: <span style="color:var(--tx)">גבר יזמות ייעוץ עסקי והשקעות</span></div>
      <div>תפקיד: <span style="color:var(--tx)">יו"ר הדירקטוריון</span></div>
      <div>מערכת: <span style="color:var(--tx)">AI Company Management v2.0</span></div>
    </div>
    <button class="btn bo" style="margin-top:12px" onclick="logout()">↩ יציאה</button>
  </div>
</div>

</div><!-- /wrap -->
<script>
let AUTH='',DEPTS=[],chatDept='',chatHist=[];
window.addEventListener('DOMContentLoaded',async function(){
  AUTH=location.hash.slice(1)||sessionStorage.getItem('jauth')||'';
  if(!AUTH){location.replace('/');return}
  sessionStorage.setItem('jauth',AUTH);
  history.replaceState(null,'','/dashboard');
  await getDepts();
  initHome();
  buildChatSide();
});
function logout(){sessionStorage.removeItem('jauth');location.replace('/')}
async function api(m,p,b){
  const o={method:m,headers:{Authorization:'Basic '+AUTH,'Content-Type':'application/json'}};
  if(b)o.body=JSON.stringify(b);
  const r=await fetch(p,o);
  if(r.status===401){logout();return null}
  return r.json();
}
function T(name,btn){
  document.querySelectorAll('.panel').forEach(function(el){el.classList.remove('active')});
  document.querySelectorAll('.tb').forEach(function(el){el.classList.remove('active')});
  var panel=document.getElementById('p-'+name);
  if(panel)panel.classList.add('active');
  if(btn)btn.classList.add('active');
  var loaders={home:initHome,instruct:loadInsts,tasks:loadTasks,employees:loadEmp,
    depts:loadDepts,meetings:loadMeetings,social:loadPosts,cashflow:loadCF,
    reports:loadReps,strategy:loadGoals,approvals:loadApprls,settings:checkConn};
  if(loaders[name])loaders[name]();
}
async function getDepts(){
  var d=await api('GET','/api/departments');
  if(d)DEPTS=d;
}
async function initHome(){
  var s=await api('GET','/api/stats');
  if(s){
    document.getElementById('s-tasks').textContent=s.tasks_total||0;
    document.getElementById('s-emps').textContent=s.employees||0;
  }
  var hd=document.getElementById('home-depts');hd.innerHTML='';
  DEPTS.forEach(function(d){
    hd.innerHTML+='<div class="dc" onclick="T(\'chat\',null);selectChat(\''+d.id+'\')" style="border-color:'+d.color+'33">'+
      '<div class="di">'+d.icon+'</div><div class="dn">'+d.name+'</div>'+
      '<div class="dh">'+d.head+'</div><div class="dt">'+d.title+'</div></div>';
  });
  checkConn();
}
async function checkConn(){
  var h=await api('GET','/api/health');
  var el=document.getElementById('conn-status');
  var sel=document.getElementById('settings-conn');
  if(!h)return;
  var rows=[
    {n:'Claude AI',ok:h.anthropic,detail:h.anthropic?'מחובר':'הגדר ANTHROPIC_API_KEY ב-Railway'},
    {n:'Supabase DB',ok:h.supabase,detail:h.supabase?'מחובר':'הגדר SUPABASE_URL ו-SUPABASE_ANON_KEY'},
  ];
  var html=rows.map(function(r){return '<div class="conn-r"><span>'+r.n+'</span><span style="color:'+(r.ok?'var(--grn)':'var(--red)')+'">'+
    (r.ok?'✅ ':'❌ ')+r.detail+'</span></div>'}).join('');
  if(el)el.innerHTML=html;
  if(sel)sel.innerHTML=html;
}
async function sendInst(){
  var t=document.getElementById('inst-txt').value.trim();if(!t)return;
  document.getElementById('inst-resp').classList.remove('show');
  document.getElementById('inst-resp-txt').textContent='שולח...';
  document.getElementById('inst-resp').classList.add('show');
  var r=await api('POST','/api/instruct',{instruction:t});
  if(r){document.getElementById('inst-resp-txt').textContent=r.ceo_response||'';loadInsts();}
}
async function loadInsts(){
  var data=await api('GET','/api/instructions');
  var el=document.getElementById('inst-hist');if(!el)return;
  if(!data||!data.length){el.innerHTML='<div style="color:var(--mt);font-size:12px">אין הוראות</div>';return;}
  el.innerHTML=data.map(function(i){return '<div class="dr"><div class="drn">'+
    (i.created_at?i.created_at.slice(0,10):'')+' | '+i.status+'</div>'+
    '<strong>'+i.text+'</strong><br><span style="color:var(--mt)">'+i.ceo_response+'</span></div>'}).join('');
}
async function loadTasks(){
  var data=await api('GET','/api/tasks');
  var el=document.getElementById('tasks-list');if(!el)return;
  if(!data||!data.length){el.innerHTML='<div style="color:var(--mt);font-size:12px">אין משימות</div>';return;}
  el.innerHTML=data.map(function(t){
    var dot=t.priority==='high'?'dp':t.priority==='medium'?'di2':'dd';
    return '<div class="ti"><div class="tdot '+dot+'"></div><div class="ti-i">'+
      '<div class="ti-t">'+t.title+'</div><div class="ti-m">'+(t.department||'')+'</div></div>'+
      '<span class="tag '+(t.status==='done'?'tg':t.status==='approved'?'tg':'to')+'">'+t.status+'</span></div>';
  }).join('');
}
async function createTask(){
  var ti=document.getElementById('t-title').value.trim();if(!ti)return;
  await api('POST','/api/tasks',{title:ti,description:document.getElementById('t-desc').value,
    department:document.getElementById('t-dept').value,priority:document.getElementById('t-pri').value});
  document.getElementById('t-title').value='';document.getElementById('t-desc').value='';
  loadTasks();
}
async function loadEmp(){
  var dept=document.getElementById('emp-dept-filter').value;
  var url='/api/employees'+(dept?'?dept='+dept:'');
  var data=await api('GET',url);
  var el=document.getElementById('emp-table');if(!el)return;
  if(!data||!data.length){el.innerHTML='<div style="color:var(--mt);font-size:12px">אין עובדים</div>';return;}
  el.innerHTML='<table class="etbl"><thead><tr><th>שם</th><th>תפקיד</th><th>מחלקה</th><th>סטטוס</th></tr></thead><tbody>'+
    data.map(function(e){return '<tr><td><div style="display:flex;align-items:center">'+
      '<div class="av">'+e.name.charAt(0)+'</div>'+e.name+'</div></td><td>'+e.role+'</td>'+
      '<td>'+e.department+'</td><td><span class="tag tg">'+e.status+'</span></td></tr>'}).join('')+'</tbody></table>';
}
function buildChatSide(){
  var side=document.getElementById('chat-side');side.innerHTML='';
  DEPTS.forEach(function(d){
    side.innerHTML+='<button class="ca" data-id="'+d.id+'" onclick="selectChat(\''+d.id+'\')">'+
      '<span class="ca-n">'+d.icon+' '+d.name+'</span><span class="ca-r">'+d.head+'</span></button>';
  });
}
function selectChat(id){
  chatDept=id;chatHist=[];
  document.querySelectorAll('.ca').forEach(function(b){b.classList.toggle('active',b.dataset.id===id)});
  var d=DEPTS.find(function(x){return x.id===id});
  document.getElementById('chat-hdr').textContent=(d?d.icon+' '+d.head+' – '+d.name:'');
  document.getElementById('chat-msgs').innerHTML='';
  if(document.getElementById('p-chat').classList.contains('active')){}
  T('chat',document.querySelector('[onclick*="T(\'chat\'"]'));
}
function addMsg(role,text,name){
  var msgs=document.getElementById('chat-msgs');
  var d=document.createElement('div');
  if(name){var n=document.createElement('div');n.className='mn';n.textContent=name;d.appendChild(n);}
  var m=document.createElement('div');m.className='msg '+(role==='user'?'mu':'ma');m.textContent=text;
  d.appendChild(m);msgs.appendChild(d);msgs.scrollTop=msgs.scrollHeight;
}
async function sendChat(){
  if(!chatDept)return;
  var inp=document.getElementById('chat-inp');var msg=inp.value.trim();if(!msg)return;
  inp.value='';chatHist.push({role:'user',content:msg});addMsg('user',msg,'');
  var sp=document.createElement('div');sp.innerHTML='<div class="sp"></div>';
  document.getElementById('chat-msgs').appendChild(sp);
  var r=await api('POST','/api/chat/'+chatDept,{message:msg,history:chatHist});
  sp.remove();
  if(r){chatHist.push({role:'assistant',content:r.response});addMsg('ai',r.response,r.agent);}
}
async function loadDepts(){
  var el=document.getElementById('depts-grid');if(!el)return;el.innerHTML='';
  DEPTS.forEach(function(d){
    el.innerHTML+='<div class="dc" style="border-color:'+d.color+'33">'+
      '<div class="di">'+d.icon+'</div><div class="dn">'+d.name+'</div>'+
      '<div class="dh">'+d.head+'</div><div class="dt">'+d.title+'</div></div>';
  });
}
function toggleDept(btn){btn.classList.toggle('sel')}
function togglePlat(btn){
  btn.classList.toggle('sel');
  var wa=Array.from(document.querySelectorAll('#m-depts .pb.sel,.pb[data-p].sel')).some(function(b){return b.dataset.p==='whatsapp'});
  var wp=document.getElementById('wa-phone-wrap');if(wp)wp.style.display=wa?'block':'none';
}
async function createMeeting(){
  var topic=document.getElementById('m-topic').value.trim();if(!topic)return;
  var depts=Array.from(document.querySelectorAll('#m-depts .pb.sel')).map(function(b){return b.dataset.d});
  document.getElementById('meeting-resp').classList.remove('show');
  document.getElementById('meeting-resp-txt').textContent='מכנס ישיבה...';
  document.getElementById('meeting-resp').classList.add('show');
  var r=await api('POST','/api/meetings',{topic:topic,agenda:document.getElementById('m-agenda').value,departments:depts});
  if(r&&r.responses){
    var html=Object.keys(r.responses).map(function(k){
      return '<div class="dr"><div class="drn">'+k+'</div>'+r.responses[k]+'</div>';
    }).join('');
    document.getElementById('meeting-resp-txt').innerHTML=html;loadMeetings();
  }
}
async function loadMeetings(){
  var data=await api('GET','/api/meetings');
  var el=document.getElementById('meetings-list');if(!el)return;
  if(!data||!data.length){el.innerHTML='<div style="color:var(--mt);font-size:12px">אין ישיבות</div>';return;}
  el.innerHTML=data.map(function(m){return '<div class="dr"><div class="drn">'+(m.created_at?m.created_at.slice(0,10):'')+
    '</div><strong>'+m.topic+'</strong></div>'}).join('');
}
async function genPost(){
  var t=document.getElementById('soc-topic').value.trim();if(!t)return;
  document.getElementById('post-gen').classList.remove('show');
  document.getElementById('post-txt').value='יוצר פוסט...';
  document.getElementById('post-gen').classList.add('show');
  var r=await api('POST','/api/social/generate',{topic:t});
  if(r)document.getElementById('post-txt').value=r.post||'';
}
async function publishPost(){
  var text=document.getElementById('post-txt').value.trim();if(!text)return;
  var plats=Array.from(document.querySelectorAll('.pb[data-p].sel')).map(function(b){return b.dataset.p});
  var img=document.getElementById('post-img').value.trim();
  var wa=document.getElementById('wa-phone').value.trim();
  document.getElementById('pub-result').classList.remove('show');
  document.getElementById('pub-txt').textContent='מפרסם...';
  document.getElementById('pub-result').classList.add('show');
  var r=await api('POST','/api/social/publish',{text:text,platforms:plats,image_url:img,whatsapp_phone:wa});
  if(r){
    var html=Object.keys(r.results||{}).map(function(k){
      var v=r.results[k];return '<div style="margin-bottom:4px"><strong>'+k+':</strong> '+(v.ok?'✅ פורסם':'❌ '+v.error)+'</div>';
    }).join('');
    document.getElementById('pub-txt').innerHTML=html||'בוצע';loadPosts();
  }
}
async function loadPosts(){
  var data=await api('GET','/api/social/posts');
  var el=document.getElementById('posts-list');if(!el)return;
  if(!data||!data.length){el.innerHTML='<div style="color:var(--mt);font-size:12px">אין פוסטים</div>';return;}
  el.innerHTML=data.map(function(p){return '<div class="dr"><div class="drn">'+(p.created_at?p.created_at.slice(0,10):'')+
    ' | '+p.status+'</div>'+p.text.slice(0,80)+'...</div>'}).join('');
}
async function loadCF(){
  var data=await api('GET','/api/cashflow');
  if(!data)return;
  var inc=0,exp=0;
  data.forEach(function(r){var a=parseFloat(r.amount)||0;if(r.type==='income')inc+=a;else exp+=a;});
  var fmt=function(n){return '₪'+n.toLocaleString('he-IL',{maximumFractionDigits:0})};
  document.getElementById('cf-in').textContent=fmt(inc);
  document.getElementById('cf-out').textContent=fmt(exp);
  var bal=document.getElementById('cf-bal');bal.textContent=fmt(inc-exp);
  bal.style.color=inc-exp>=0?'var(--grn)':'var(--red)';
  var tbody=document.getElementById('cf-rows');if(!tbody)return;
  tbody.innerHTML=data.slice(0,50).map(function(r){return '<tr><td>'+(r.date||'').slice(0,10)+'</td>'+
    '<td>'+r.description+'</td><td class="'+(r.type==='income'?'cin':'cout')+'">'+(r.type==='income'?'הכנסה':'הוצאה')+'</td>'+
    '<td class="'+(r.type==='income'?'cin':'cout')+'">'+fmt(parseFloat(r.amount)||0)+'</td></tr>'}).join('');
}
async function addCF(){
  var desc=document.getElementById('cf-desc').value.trim();
  var amt=parseFloat(document.getElementById('cf-amt').value);
  if(!desc||isNaN(amt))return;
  await api('POST','/api/cashflow',{description:desc,amount:amt,
    type:document.getElementById('cf-type').value,
    category:document.getElementById('cf-cat').value||'כללי',
    date:document.getElementById('cf-date').value||new Date().toISOString().slice(0,10)});
  document.getElementById('cf-desc').value='';document.getElementById('cf-amt').value='';
  loadCF();
}
async function analyzeCF(){
  document.getElementById('cf-analysis').classList.remove('show');
  document.getElementById('cf-anal-txt').textContent='מנתח...';
  document.getElementById('cf-analysis').classList.add('show');
  var r=await api('POST','/api/cashflow/analyze');
  if(r)document.getElementById('cf-anal-txt').textContent=r.analysis||'';
}
async function loadReps(){
  var data=await api('GET','/api/reports');
  var el=document.getElementById('reports-list');if(!el)return;
  if(!data||!data.length){el.innerHTML='<div style="color:var(--mt);font-size:12px">אין דוחות</div>';return;}
  el.innerHTML=data.map(function(r){return '<div class="dr"><div class="drn">'+(r.created_at?r.created_at.slice(0,10):'')+
    '</div><strong>'+r.title+'</strong></div>'}).join('');
}
async function genRep(){
  document.getElementById('rep-result').classList.remove('show');
  document.getElementById('rep-txt').textContent='יוצר דוח...';
  document.getElementById('rep-result').classList.add('show');
  var r=await api('POST','/api/reports/generate',{department:document.getElementById('r-dept').value,type:document.getElementById('r-type').value});
  if(r&&r.report){document.getElementById('rep-txt').textContent=r.report.content||'';loadReps();}
}
async function setGoals(){
  var g=document.getElementById('goals-txt').value.trim();if(!g)return;
  document.getElementById('goals-resp').classList.remove('show');
  document.getElementById('goals-txt2').textContent='יוצר תוכנית...';
  document.getElementById('goals-resp').classList.add('show');
  var r=await api('POST','/api/strategy/goals',{goals:g});
  if(r)document.getElementById('goals-txt2').textContent=r.plan||'';loadGoals();
}
async function loadGoals(){
  var data=await api('GET','/api/strategy/goals');
  var el=document.getElementById('goals-list');if(!el)return;
  if(!data||!data.length){el.innerHTML='<div style="color:var(--mt);font-size:12px">אין יעדים</div>';return;}
  el.innerHTML=data.map(function(g){return '<div class="dr"><div class="drn">'+(g.created_at?g.created_at.slice(0,10):'')+
    '</div><strong>'+g.goals+'</strong></div>'}).join('');
}
async function loadApprls(){
  var data=await api('GET','/api/approvals');
  var el=document.getElementById('approvals-list');if(!el)return;
  if(!data||!data.length){el.innerHTML='<div style="color:var(--mt);font-size:12px">אין פריטים לאישור</div>';return;}
  el.innerHTML=data.map(function(t){return '<div class="ti"><div class="tdot dp"></div><div class="ti-i">'+
    '<div class="ti-t">'+t.title+'</div><div class="ti-m">'+t.department+'</div></div>'+
    '<button class="btn bsm bg" onclick="approveTask(\''+t.id+'\')">✅ אשר</button></div>'}).join('');
}
async function approveTask(id){
  await api('POST','/api/tasks/'+id+'/approve');loadApprls();
}
window.addEventListener('DOMContentLoaded', async function(){
  await getDepts();
  initHome();
  buildChatSide();
});
</script>
</body></html>'''

@app.get("/", response_class=HTMLResponse)
async def login_page():
    return HTMLResponse(LOGIN_HTML)

@app.get("/dashboard", response_class=HTMLResponse)
async def dashboard():
    return HTMLResponse(DASHBOARD_HTML)

@app.get("/health")
async def health_pub():
    return {"status": "ok"}
