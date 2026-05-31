"""
Jabr Management System - Clean Build
גבר יזמות ייעוץ עסקי והשקעות
"""
from fastapi import FastAPI, Depends, Request, HTTPException, Response
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.security import HTTPBasic, HTTPBasicCredentials
from fastapi.middleware.cors import CORSMiddleware
import httpx, os, json, secrets, base64
from datetime import datetime
from typing import Optional

# ── Config ────────────────────────────────────────────────────
ANTHROPIC_KEY = os.getenv("ANTHROPIC_API_KEY","")
SB_URL        = os.getenv("SUPABASE_URL","")
SB_KEY        = os.getenv("SUPABASE_ANON_KEY","")
USER          = os.getenv("DASHBOARD_USER","chairman")
PASS          = os.getenv("DASHBOARD_PASSWORD","Prime@2024!")
COMPANY       = os.getenv("COMPANY_NAME","גבר יזמות ייעוץ עסקי והשקעות")

app = FastAPI()
security = HTTPBasic()
app.add_middleware(CORSMiddleware,allow_origins=["*"],allow_methods=["*"],allow_headers=["*"])

# ── Auth ──────────────────────────────────────────────────────
def check_auth(creds: HTTPBasicCredentials = Depends(security)):
    if not (secrets.compare_digest(creds.username.encode(), USER.encode()) and
            secrets.compare_digest(creds.password.encode(), PASS.encode())):
        raise HTTPException(401, headers={"WWW-Authenticate":"Basic"})
    return creds.username

def check_cookie(request: Request):
    """Check auth from cookie - for page routes"""
    token = request.cookies.get("jabr_token","")
    if not token:
        return None
    try:
        decoded = base64.b64decode(token).decode()
        u, p = decoded.split(":",1)
        if secrets.compare_digest(u.encode(), USER.encode()) and \
           secrets.compare_digest(p.encode(), PASS.encode()):
            return u
    except:
        pass
    return None

# ── Supabase ──────────────────────────────────────────────────
def sb_headers():
    return {"apikey":SB_KEY,"Authorization":f"Bearer {SB_KEY}",
            "Content-Type":"application/json","Prefer":"return=representation"}

async def sb_get(table, params=""):
    if not SB_URL: return []
    try:
        async with httpx.AsyncClient() as c:
            url = f"{SB_URL}/rest/v1/{table}" + (f"?{params}" if params else "")
            r = await c.get(url, headers=sb_headers(), timeout=15)
            return r.json() if r.status_code == 200 else []
    except: return []

async def sb_ins(table, data):
    if not SB_URL: return {"id":"mock",**data}
    try:
        async with httpx.AsyncClient() as c:
            r = await c.post(f"{SB_URL}/rest/v1/{table}",
                headers=sb_headers(), json=data, timeout=15)
            res = r.json()
            return res[0] if isinstance(res,list) and res else \
                   res if isinstance(res,dict) else {"id":"ok"}
    except Exception as e: return {"id":"err","e":str(e)}

# ── Claude AI ─────────────────────────────────────────────────
AGENTS = {
    "ceo":        ("דניאל כהן",     "מנכ\"ל",           "אתה דניאל כהן מנכ\"ל {co}. מתאם מחלקות, מחלק משימות, מסכם תוצאות."),
    "cfo":        ("מיכאל לוי",     "CFO",               "אתה מיכאל לוי CFO {co}. תזרים, תקציבים, ניתוח עלויות."),
    "marketing":  ("נועה שפירא",    "מנהלת שיווק",       "את נועה שפירא מנהלת שיווק {co}. קמפיינים ואסטרטגיה."),
    "sales":      ("רון אברהם",     "מנהל מכירות",       "אתה רון אברהם מנהל מכירות {co}."),
    "legal":      ("עו\"ד תמר גולן","יועמ\"ש",           "את עו\"ד תמר גולן יועמ\"ש {co}."),
    "cto":        ("אלון בן-דוד",   "CTO",               "אתה אלון בן-דוד CTO {co}."),
    "content":    ("שיר מזרחי",     "מנהלת תוכן",        "את שיר מזרחי מנהלת תוכן {co}."),
    "pr":         ("גיל פרץ",       "מנהל יח\"צ",        "אתה גיל פרץ מנהל יח\"צ {co}."),
    "compliance": ("ד\"ר ענת רוזן", "קצינת ציות",        "את ד\"ר ענת רוזן קצינת ציות {co}."),
    "hr":         ("יובל כץ",       "מנהל HR",           "אתה יובל כץ מנהל HR {co}."),
    "customer":   ("ליאת דביר",     "מנהלת שירות",       "את ליאת דביר מנהלת שירות לקוחות {co}."),
}
DMETA = {
    "ceo":{"name":"מנכ\"ל","icon":"👑","color":"#a78bfa"},
    "cfo":{"name":"כספים","icon":"💰","color":"#f5c842"},
    "marketing":{"name":"שיווק","icon":"📣","color":"#f87171"},
    "sales":{"name":"מכירות","icon":"📈","color":"#22d3a0"},
    "legal":{"name":"משפטי","icon":"⚖️","color":"#60a5fa"},
    "cto":{"name":"טכנולוגיה","icon":"💻","color":"#34d399"},
    "content":{"name":"תוכן","icon":"🎨","color":"#fb923c"},
    "pr":{"name":"יח\"צ","icon":"📢","color":"#e879f9"},
    "compliance":{"name":"ציות","icon":"🛡️","color":"#94a3b8"},
    "hr":{"name":"HR","icon":"👥","color":"#4ade80"},
    "customer":{"name":"שירות לקוחות","icon":"🎧","color":"#38bdf8"},
}
EMPS = {
    "ceo":[("יעל מזרחי","עוזרת מנכ\"ל"),("אסף ברק","מנהל פרויקטים"),("מיה לוין","רכזת"),("עומר שלום","אנליסט")],
    "cfo":[("דנה כהן","חשבת"),("רועי פלד","אנליסט פיננסי"),("שרה לוי","גזברית"),("אמיר גל","מנהל תקציב")],
    "marketing":[("נדב ביטון","מנהל דיגיטל"),("טל שר","מעצב גרפי"),("יונית אור","כותבת תוכן"),("עידן רז","SEO")],
    "sales":[("ליאל דוד","נציג מכירות"),("הילה ים","מנהלת לקוחות"),("בן גבע","אנליסט"),("מור שגיא","נציגת מכירות")],
    "legal":[("ניר אלון","עו\"ד"),("שירה רן","פרלגל"),("גבי מור","יועץ רגולציה"),("לי בן","מזכירת משפטים")],
    "cto":[("ירון נוי","Full Stack"),("הדר עם","DevOps"),("ליר שן","Backend"),("כרמל אל","UX")],
    "content":[("אביב כץ","צלם ועורך"),("ניל שר","מנהל סושיאל"),("עלמא פז","יוצרת תוכן"),("יאיר אף","YouTube")],
    "pr":[("הילה דן","דוברת"),("רן שם","יחצ\"ן"),("שי לם","מנהל אירועים"),("מאיה ון","קשרי תקשורת")],
    "compliance":[("ורד נץ","קצינת ציות"),("תמר גן","מבקרת פנים"),("אלי קם","מנהל סיכונים"),("רינה שן","יועצת רגולציה")],
    "hr":[("נועם בר","מגייסת"),("שלי גז","מנהלת רווחה"),("עמית לז","מנהל הכשרות"),("ציפי רם","יועצת ארגונית")],
    "customer":[("דור כהן","נציג שירות"),("עינת שמ","נציגת שירות"),("אלון בר","מנהל תלונות"),("מרים כ","נציגת שירות")],
}

async def ai(role, msg, ctx=""):
    if not ANTHROPIC_KEY:
        return f"[{AGENTS.get(role,('AI','',''))[0]}]: מפתח API לא מוגדר ב-Railway"
    n,t,sys = AGENTS.get(role, ("AI","","אתה עוזר מקצועי."))
    system = sys.replace("{co}", COMPANY)
    if ctx: system += f"\n\nהקשר:\n{ctx}"
    try:
        async with httpx.AsyncClient() as c:
            r = await c.post("https://api.anthropic.com/v1/messages",
                headers={"x-api-key":ANTHROPIC_KEY,"anthropic-version":"2023-06-01","content-type":"application/json"},
                json={"model":"claude-opus-4-6","max_tokens":1500,"system":system,
                      "messages":[{"role":"user","content":msg}]}, timeout=40)
            return r.json()["content"][0]["text"] if r.status_code==200 else f"שגיאה {r.status_code}"
    except Exception as e: return f"שגיאת חיבור: {e}"

# ── Page Routes (cookie auth) ─────────────────────────────────
@app.get("/", response_class=HTMLResponse)
async def login_page(request: Request):
    # If already logged in, redirect to dashboard
    if check_cookie(request):
        return RedirectResponse("/dashboard", status_code=302)
    return HTMLResponse(get_login_html())

@app.post("/login")
async def do_login(request: Request):
    form = await request.form()
    u = form.get("username","")
    p = form.get("password","")
    if secrets.compare_digest(u.encode(), USER.encode()) and \
       secrets.compare_digest(p.encode(), PASS.encode()):
        token = base64.b64encode(f"{u}:{p}".encode()).decode()
        response = RedirectResponse("/dashboard", status_code=302)
        response.set_cookie("jabr_token", token, max_age=86400, httponly=False, samesite="lax")
        return response
    return HTMLResponse(get_login_html(error=True))

@app.get("/logout")
async def logout():
    response = RedirectResponse("/", status_code=302)
    response.delete_cookie("jabr_token")
    return response

@app.get("/dashboard", response_class=HTMLResponse)
async def dashboard(request: Request):
    user = check_cookie(request)
    if not user:
        return RedirectResponse("/", status_code=302)
    return HTMLResponse(get_dashboard_html())

# ── API Routes (Basic Auth) ───────────────────────────────────
@app.get("/api/health")
async def health():
    return {"status":"ok","anthropic":bool(ANTHROPIC_KEY),"supabase":bool(SB_URL and SB_KEY)}

@app.get("/api/me")
async def me(u=Depends(check_auth)):
    return {"ok":True,"user":u}

@app.get("/api/stats")
async def stats(u=Depends(check_auth)):
    t  = await sb_get("tasks","select=count")
    dn = await sb_get("tasks","select=count&status=eq.done")
    def cnt(x): return x[0].get("count",0) if isinstance(x,list) and x and isinstance(x[0],dict) else 0
    return {"tasks_total":cnt(t),"tasks_done":cnt(dn),"tasks_inprog":0,"tasks_pending":0,
            "departments":len(DMETA),"employees":sum(1+len(v) for v in EMPS.values())}

@app.get("/api/departments")
async def depts(u=Depends(check_auth)):
    return [{"id":k,"name":v["name"],"icon":v["icon"],"color":v["color"],
             "head":AGENTS[k][0],"title":AGENTS[k][1]} for k,v in DMETA.items()]

@app.get("/api/employees")
async def emps(dept: Optional[str]=None, u=Depends(check_auth)):
    result = []
    for did in ([dept] if dept else list(DMETA.keys())):
        if did not in DMETA: continue
        ag = AGENTS.get(did)
        if ag: result.append({"id":f"{did}-0","name":ag[0],"role":ag[1],"department":did,"title":"מנהל","status":"active"})
        for nm,rl in EMPS.get(did,[]):
            result.append({"id":f"{did}-{nm}","name":nm,"role":rl,"department":did,"title":"עובד","status":"active"})
    return result

@app.get("/api/tasks")
async def tasks(status: Optional[str]=None, dept: Optional[str]=None, u=Depends(check_auth)):
    q = "order=created_at.desc&limit=50"
    if status: q += f"&status=eq.{status}"
    if dept:   q += f"&department=eq.{dept}"
    return await sb_get("tasks", q)

@app.post("/api/tasks")
async def create_task(req: Request, u=Depends(check_auth)):
    b = await req.json()
    if not b.get("title","").strip(): raise HTTPException(400,"נא להזין כותרת")
    return await sb_ins("tasks",{"title":b["title"],"description":b.get("description",""),
        "department":b.get("department","ceo"),"priority":b.get("priority","medium"),
        "status":"pending","created_by":u,"created_at":datetime.utcnow().isoformat()})

@app.post("/api/tasks/{tid}/approve")
async def approve(tid: str, u=Depends(check_auth)):
    if SB_URL:
        async with httpx.AsyncClient() as c:
            await c.patch(f"{SB_URL}/rest/v1/tasks?id=eq.{tid}",
                headers=sb_headers(),json={"status":"approved"},timeout=10)
    return {"ok":True}

@app.post("/api/instruct")
async def instruct(req: Request, u=Depends(check_auth)):
    b = await req.json()
    inst = b.get("instruction","").strip()
    if not inst: raise HTTPException(400,"נא לכתוב הוראה")
    resp = await ai("ceo", f'קיבלת הוראה מיו"ר:\n"{inst}"\n\n1.נתח 2.אילו מחלקות? 3.תוכנית פעולה 4.ציר זמן')
    await sb_ins("instructions",{"text":inst,"ceo_response":resp,"status":"processing","created_at":datetime.utcnow().isoformat()})
    return {"instruction":inst,"ceo_response":resp}

@app.get("/api/instructions")
async def get_insts(u=Depends(check_auth)):
    return await sb_get("instructions","order=created_at.desc&limit=20")

@app.post("/api/chat/{dept}")
async def chat(dept: str, req: Request, u=Depends(check_auth)):
    b = await req.json()
    msg = b.get("message","")
    hist = b.get("history",[])
    ctx = "\n".join([f"{m['role']}: {m['content']}" for m in hist[-8:]])
    resp = await ai(dept, msg, ctx)
    await sb_ins("chat_messages",{"department":dept,"user_message":msg,"ai_response":resp,"created_at":datetime.utcnow().isoformat()})
    ag = AGENTS.get(dept,("AI","",""))
    return {"response":resp,"agent":ag[0],"title":ag[1]}

@app.post("/api/meetings")
async def meeting(req: Request, u=Depends(check_auth)):
    b = await req.json()
    topic = b.get("topic",""); agenda = b.get("agenda",""); dpts = b.get("departments",["ceo"])
    rs = {}
    for d in dpts[:5]:
        rs[d] = await ai(d, f'ישיבה: {topic}\nסדר יום: {agenda}\nמה עמדתך?')
    await sb_ins("meetings",{"topic":topic,"agenda":agenda,"responses":json.dumps(rs,ensure_ascii=False),"status":"completed","created_at":datetime.utcnow().isoformat()})
    return {"responses":rs}

@app.get("/api/meetings")
async def get_meetings(u=Depends(check_auth)):
    return await sb_get("meetings","order=created_at.desc&limit=20")

@app.post("/api/reports/generate")
async def gen_rep(req: Request, u=Depends(check_auth)):
    b = await req.json(); dept = b.get("department","ceo"); rt = b.get("type","weekly")
    dn = DMETA.get(dept,{}).get("name",dept)
    content = await ai(dept, f'צור דוח {rt} למחלקת {dn}. כלול: סיכום, הישגים, אתגרים, תוכנית.')
    r = {"title":f'דוח {rt} – {dn}',"department":dept,"content":content,"type":rt,"created_at":datetime.utcnow().isoformat()}
    await sb_ins("reports",r)
    return {"report":r}

@app.get("/api/reports")
async def get_reps(u=Depends(check_auth)):
    return await sb_get("reports","order=created_at.desc&limit=20")

@app.get("/api/approvals")
async def approvals(u=Depends(check_auth)):
    return await sb_get("tasks","status=eq.pending_approval&order=created_at.desc")

@app.post("/api/strategy/goals")
async def set_goals(req: Request, u=Depends(check_auth)):
    b = await req.json(); goals = b.get("goals","").strip()
    if not goals: raise HTTPException(400,"נא להזין יעדים")
    plan = await ai("ceo", f'יו"ר הציב יעדים:\n{goals}\n\nצור תוכנית: 1.פירוט 2.לו"ז 3.KPIs 4.סיכונים 5.תקציב')
    await sb_ins("strategic_goals",{"goals":goals,"plan":plan,"status":"active","created_at":datetime.utcnow().isoformat()})
    return {"goals":goals,"plan":plan}

@app.get("/api/strategy/goals")
async def get_goals(u=Depends(check_auth)):
    return await sb_get("strategic_goals","order=created_at.desc&limit=10")

@app.get("/api/cashflow")
async def get_cf(u=Depends(check_auth)):
    return await sb_get("cashflow","order=date.desc&limit=200")

@app.post("/api/cashflow")
async def add_cf(req: Request, u=Depends(check_auth)):
    b = await req.json()
    try: amt = float(b.get("amount",0))
    except: raise HTTPException(400,"סכום לא תקין")
    return await sb_ins("cashflow",{"date":b.get("date",datetime.utcnow().date().isoformat()),
        "description":b.get("description",""),"amount":amt,"type":b.get("type","income"),
        "category":b.get("category","כללי"),"client_id":b.get("client_id",""),
        "created_at":datetime.utcnow().isoformat()})

@app.post("/api/cashflow/analyze")
async def analyze_cf(u=Depends(check_auth)):
    rows = await sb_get("cashflow","order=date.desc&limit=100")
    if not rows: return {"analysis":"אין נתוני תזרים עדיין.","rows":[]}
    ti = sum(float(r.get("amount",0)) for r in rows if r.get("type")=="income")
    to = sum(float(r.get("amount",0)) for r in rows if r.get("type")=="expense")
    a = await ai("cfo", f'תזרים: הכנסות={ti:,.0f}₪ הוצאות={to:,.0f}₪ יתרה={ti-to:,.0f}₪\nנתח ותן המלצות.')
    return {"analysis":a,"rows":rows,"summary":{"income":ti,"expense":to,"balance":ti-to}}

@app.post("/api/social/generate")
async def gen_post(req: Request, u=Depends(check_auth)):
    b = await req.json()
    p = await ai("content", f'כתוב פוסט לסושיאל בנושא: {b.get("topic","")}\nכלול כותרת, גוף, CTA, האשטגים.')
    return {"post":p}

@app.post("/api/social/publish")
async def pub_post(req: Request, u=Depends(check_auth)):
    b = await req.json()
    if not b.get("text",""): raise HTTPException(400,"נא לכתוב תוכן")
    await sb_ins("social_posts",{"text":b["text"],"platforms":json.dumps(b.get("platforms",[])),"status":"pending","created_at":datetime.utcnow().isoformat()})
    return {"text":b["text"],"results":{"info":"חבר API keys ב-Railway לפרסום אמיתי"}}

@app.get("/api/social/posts")
async def get_posts(u=Depends(check_auth)):
    return await sb_get("social_posts","order=created_at.desc&limit=30")


# ── HTML ──────────────────────────────────────────────────────
def get_login_html(error=False):
    return f'''<!DOCTYPE html>
<html lang="he" dir="rtl"><head>
<meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>גבר – כניסה</title>
<style>
*{{box-sizing:border-box;margin:0;padding:0}}
body{{font-family:Arial,sans-serif;min-height:100vh;display:flex;align-items:center;justify-content:center;
  background:radial-gradient(ellipse at 20% 50%,#1a0a4a,#0d1a3a 40%,#060b18)}}
.card{{background:rgba(22,25,33,.95);border:1px solid rgba(167,139,250,.2);border-radius:18px;
  padding:36px 28px;width:100%;max-width:360px;box-shadow:0 0 60px rgba(108,99,255,.2)}}
.logo{{text-align:center;margin-bottom:22px}}
.ico{{width:60px;height:60px;background:linear-gradient(135deg,#6c63ff,#a78bfa);border-radius:14px;
  display:inline-flex;align-items:center;justify-content:center;font-size:28px;margin-bottom:9px}}
.nm{{font-size:17px;font-weight:800;color:#e8eaf0}}
.sb{{font-size:11px;color:#8892a4}}
.fld{{margin-bottom:12px}}
label{{display:block;font-size:11px;color:#8892a4;margin-bottom:4px;font-weight:600;text-transform:uppercase}}
input{{width:100%;background:rgba(13,15,20,.8);border:1px solid rgba(167,139,250,.2);border-radius:8px;
  color:#e8eaf0;font-family:Arial;font-size:14px;padding:10px 12px;direction:rtl;outline:none}}
input:focus{{border-color:#6c63ff}}
.btn{{width:100%;background:linear-gradient(135deg,#6c63ff,#8b5cf6);color:#fff;border:none;
  border-radius:8px;font-family:Arial;font-size:15px;font-weight:700;padding:12px;cursor:pointer;margin-top:4px}}
.err{{background:rgba(248,113,113,.1);border:1px solid rgba(248,113,113,.3);border-radius:7px;
  padding:8px 12px;font-size:12px;color:#f87171;margin-top:8px;text-align:center;
  {"display:block" if error else "display:none"}}}
</style></head>
<body>
<div class="card">
  <div class="logo">
    <div class="ico">🏢</div>
    <div class="nm">גבר יזמות ייעוץ עסקי</div>
    <div class="sb">AI Company Management System</div>
  </div>
  <form method="POST" action="/login">
    <div class="fld"><label>שם משתמש</label><input name="username" placeholder="chairman" autocomplete="username"></div>
    <div class="fld"><label>סיסמה</label><input name="password" type="password" placeholder="••••••••"></div>
    <button class="btn" type="submit">🔐 כניסה למערכת</button>
  </form>
  <div class="err">שם משתמש או סיסמה שגויים</div>
</div>
</body></html>'''

def get_dashboard_html():
    return '''<!DOCTYPE html>
<html lang="he" dir="rtl"><head>
<meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>גבר – ניהול AI</title>
<style>
@import url('https://fonts.googleapis.com/css2?family=Heebo:wght@400;500;600;700;800&display=swap');
:root{--bg:#0d0f14;--sur:#161921;--card:#1c2030;--bdr:#252a3a;--ac:#6c63ff;--ac2:#a78bfa;
  --gld:#f5c842;--grn:#22d3a0;--red:#f87171;--org:#fb923c;--tx:#e8eaf0;--mt:#8892a4;--r:10px}
*{box-sizing:border-box;margin:0;padding:0}
body{font-family:'Heebo',Arial,sans-serif;background:var(--bg);color:var(--tx);min-height:100vh}
.hdr{background:linear-gradient(135deg,#1a0a4a,#0d1a3a);border-bottom:1px solid var(--bdr);
  padding:0 16px;display:flex;align-items:center;justify-content:space-between;height:54px;
  position:sticky;top:0;z-index:100}
.hl{display:flex;align-items:center;gap:8px}
.hic{width:32px;height:32px;background:linear-gradient(135deg,var(--ac),var(--ac2));
  border-radius:8px;display:flex;align-items:center;justify-content:center;font-size:16px}
.ht{font-weight:700;font-size:13px}.hs{font-size:9px;color:var(--mt)}
.tabs{background:var(--sur);border-bottom:1px solid var(--bdr);padding:0 14px;
  display:flex;overflow-x:auto;scrollbar-width:none}
.tabs::-webkit-scrollbar{display:none}
.tb{background:none;border:none;color:var(--mt);font-family:inherit;font-size:11px;
  padding:10px 9px;cursor:pointer;white-space:nowrap;border-bottom:2px solid transparent;transition:all .2s}
.tb:hover{color:var(--tx)}.tb.active{color:var(--ac2);border-bottom-color:var(--ac2)}
.wrap{padding:14px;max-width:1400px;margin:0 auto}
.panel{display:none}.panel.active{display:block}
.stats{display:grid;grid-template-columns:repeat(3,1fr);gap:7px;margin-bottom:12px}
.stat{background:var(--card);border:1px solid var(--bdr);border-radius:var(--r);padding:12px 8px;text-align:center}
.sn{font-size:22px;font-weight:800;color:var(--ac2);line-height:1;margin-bottom:3px}
.sl{font-size:10px;color:var(--mt)}
.card{background:var(--card);border:1px solid var(--bdr);border-radius:var(--r);padding:14px;margin-bottom:11px}
.ct{font-size:13px;font-weight:700;margin-bottom:11px;display:flex;align-items:center;gap:5px}
textarea,input[type=text],select{width:100%;background:var(--sur);border:1px solid var(--bdr);
  border-radius:7px;color:var(--tx);font-family:inherit;font-size:12px;padding:8px 10px;direction:rtl;outline:none}
textarea:focus,input[type=text]:focus,select:focus{border-color:var(--ac)}
textarea{resize:vertical;min-height:70px}select option{background:var(--card)}
label{display:block;font-size:10px;color:var(--mt);margin-bottom:3px}
.fg{margin-bottom:9px}.fr{display:grid;grid-template-columns:1fr 1fr;gap:8px}
.btn{display:inline-flex;align-items:center;gap:4px;background:linear-gradient(135deg,var(--ac),#8b5cf6);
  color:#fff;border:none;border-radius:7px;padding:7px 13px;font-family:inherit;font-size:12px;font-weight:700;cursor:pointer}
.btn:hover{opacity:.85}.btn:disabled{opacity:.5;cursor:not-allowed}
.bsm{padding:5px 9px;font-size:11px}
.bg{background:linear-gradient(135deg,#059669,var(--grn))}
.bo{background:none;border:1px solid var(--bdr);color:var(--tx)}.bo:hover{border-color:var(--ac);color:var(--ac2)}
.rb{background:var(--sur);border:1px solid var(--bdr);border-radius:7px;padding:11px;margin-top:9px;
  font-size:12px;line-height:1.7;white-space:pre-wrap;display:none}
.rb.show{display:block}
.rl{font-size:9px;color:var(--ac2);font-weight:700;margin-bottom:5px;text-transform:uppercase}
.dg{display:grid;grid-template-columns:repeat(auto-fill,minmax(120px,1fr));gap:7px}
.dc{background:var(--sur);border:1px solid var(--bdr);border-radius:var(--r);padding:10px;cursor:pointer;transition:all .2s;text-align:center}
.dc:hover{transform:translateY(-2px);border-color:var(--ac)}
.di{font-size:20px;margin-bottom:4px}.dn{font-size:11px;font-weight:700}
.dh{font-size:9px;color:var(--mt);margin-top:2px}.dt{font-size:9px;color:var(--ac2)}
.chat-w{display:grid;grid-template-columns:145px 1fr;gap:9px;height:540px}
.cs{background:var(--sur);border:1px solid var(--bdr);border-radius:var(--r);overflow-y:auto}
.ca{width:100%;background:none;border:none;border-bottom:1px solid var(--bdr);color:var(--tx);
  font-family:inherit;font-size:10px;padding:7px 8px;cursor:pointer;text-align:right;
  display:flex;flex-direction:column;align-items:flex-end;transition:background .15s}
.ca:hover{background:rgba(108,99,255,.08)}.ca.active{background:rgba(167,139,250,.12);color:var(--ac2)}
.can{font-weight:700;font-size:11px}.car{font-size:9px;color:var(--mt)}
.cm{background:var(--sur);border:1px solid var(--bdr);border-radius:var(--r);display:flex;flex-direction:column;overflow:hidden}
.ch{padding:9px 12px;border-bottom:1px solid var(--bdr);font-weight:700;font-size:12px;flex-shrink:0}
.msgs{flex:1;overflow-y:auto;padding:9px;display:flex;flex-direction:column;gap:6px;min-height:0}
.msg{padding:7px 10px;border-radius:9px;font-size:11px;line-height:1.6;max-width:88%;word-wrap:break-word}
.mu{background:linear-gradient(135deg,var(--ac),#8b5cf6);align-self:flex-start;border-radius:9px 9px 9px 2px}
.ma{background:var(--card);border:1px solid var(--bdr);align-self:flex-end;border-radius:9px 9px 2px 9px}
.mn{font-size:9px;color:var(--ac2);font-weight:700;margin-bottom:2px}
.cin{padding:8px;border-top:1px solid var(--bdr);display:flex;gap:6px;flex-shrink:0}
.ci{flex:1;background:var(--card);border:1px solid var(--bdr);border-radius:7px;color:var(--tx);
  font-family:inherit;font-size:12px;padding:7px 9px;direction:rtl;outline:none;resize:none;height:34px}
.ci:focus{border-color:var(--ac)}
.ti{background:var(--sur);border:1px solid var(--bdr);border-radius:8px;padding:9px 11px;margin-bottom:5px;display:flex;align-items:center;gap:7px}
.tdot{width:6px;height:6px;border-radius:50%;flex-shrink:0}
.dp{background:var(--org)}.di2{background:var(--ac2)}.dd{background:var(--grn)}.da{background:var(--gld)}
.tii{flex:1;min-width:0}
.tit{font-size:12px;font-weight:600;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
.tim{font-size:10px;color:var(--mt);margin-top:1px}
.tag{background:rgba(108,99,255,.15);color:var(--ac2);border:1px solid rgba(108,99,255,.3);border-radius:5px;padding:1px 6px;font-size:10px;white-space:nowrap;flex-shrink:0}
.tg{background:rgba(34,211,160,.15);color:var(--grn);border-color:rgba(34,211,160,.3)}
.to{background:rgba(251,146,60,.15);color:var(--org);border-color:rgba(251,146,60,.3)}
.ty{background:rgba(245,200,66,.15);color:var(--gld);border-color:rgba(245,200,66,.3)}
.et{width:100%;border-collapse:collapse;font-size:11px}
.et th{background:var(--sur);padding:7px 8px;text-align:right;font-weight:600;color:var(--mt);font-size:9px;border-bottom:1px solid var(--bdr)}
.et td{padding:7px 8px;border-bottom:1px solid rgba(37,42,58,.3)}
.av{width:22px;height:22px;border-radius:50%;background:linear-gradient(135deg,var(--ac),var(--ac2));display:inline-flex;align-items:center;justify-content:center;font-size:9px;font-weight:700;margin-left:5px}
.pb{background:var(--sur);border:1px solid var(--bdr);border-radius:7px;padding:7px 11px;cursor:pointer;font-family:inherit;font-size:11px;color:var(--mt);display:flex;align-items:center;gap:4px}
.pb.sel{border-color:var(--ac2);color:var(--ac2);background:rgba(167,139,250,.08)}
.cfs{display:grid;grid-template-columns:repeat(3,1fr);gap:7px;margin-bottom:10px}
.cfc{background:var(--sur);border:1px solid var(--bdr);border-radius:8px;padding:9px;text-align:center}
.cfn{font-size:17px;font-weight:800;margin-bottom:2px}.cfl{font-size:9px;color:var(--mt)}
.cft{width:100%;border-collapse:collapse;font-size:11px}
.cft th{background:var(--sur);padding:6px 8px;text-align:right;font-weight:600;color:var(--mt);font-size:9px;border-bottom:1px solid var(--bdr)}
.cft td{padding:6px 8px;border-bottom:1px solid rgba(37,42,58,.3)}
.cin2{color:var(--grn)}.cout{color:var(--red)}
.dr{border-right:3px solid var(--ac);padding:5px 8px;margin-bottom:5px;background:rgba(108,99,255,.04);border-radius:0 5px 5px 0;font-size:11px;line-height:1.5}
.drn{font-size:9px;color:var(--ac2);font-weight:700;margin-bottom:2px}
.sp{display:inline-block;width:12px;height:12px;border:2px solid rgba(167,139,250,.3);border-top-color:var(--ac2);border-radius:50%;animation:spin .7s linear infinite}
@keyframes spin{to{transform:rotate(360deg)}}
.cr{padding:8px 10px;background:var(--sur);border:1px solid var(--bdr);border-radius:7px;display:flex;justify-content:space-between;margin-bottom:5px;font-size:11px}
@media(max-width:600px){
  .fr{grid-template-columns:1fr}
  .chat-w{grid-template-columns:1fr;height:auto}
  .cs{display:flex;overflow-x:auto;height:42px;border-radius:8px}
  .ca{flex-direction:row;border-bottom:none;border-left:1px solid var(--bdr);white-space:nowrap;flex-shrink:0;padding:5px 7px}
  .car{display:none}.cm{height:400px}.cfs{grid-template-columns:1fr}
}
</style></head>
<body>
<div class="hdr">
  <div class="hl">
    <div class="hic">🏢</div>
    <div><div class="ht">גבר יזמות ייעוץ עסקי</div><div class="hs">AI Company Management System</div></div>
  </div>
  <div style="display:flex;align-items:center;gap:7px">
    <span style="background:rgba(34,211,160,.15);color:#22d3a0;border:1px solid rgba(34,211,160,.3);border-radius:20px;padding:2px 9px;font-size:10px">● מחובר</span>
    <a href="/logout" style="background:rgba(248,113,113,.15);color:#f87171;border:1px solid rgba(248,113,113,.3);border-radius:7px;padding:4px 10px;font-size:11px;text-decoration:none">↩ יציאה</a>
  </div>
</div>
<div class="tabs">
  <button class="tb active" onclick="T(\'home\',this)">🏠 ראשי</button>
  <button class="tb" onclick="T(\'instruct\',this)">📋 הוראות</button>
  <button class="tb" onclick="T(\'tasks\',this)">⚙️ משימות</button>
  <button class="tb" onclick="T(\'employees\',this)">👥 עובדים</button>
  <button class="tb" onclick="T(\'chat\',this)">💬 צ׳אט</button>
  <button class="tb" onclick="T(\'depts\',this)">🏬 מחלקות</button>
  <button class="tb" onclick="T(\'meetings\',this)">📅 ישיבות</button>
  <button class="tb" onclick="T(\'social\',this)">📱 סושיאל</button>
  <button class="tb" onclick="T(\'cashflow\',this)">💰 תזרים</button>
  <button class="tb" onclick="T(\'reports\',this)">📊 דוחות</button>
  <button class="tb" onclick="T(\'strategy\',this)">🎯 יעדים</button>
  <button class="tb" onclick="T(\'approvals\',this)">👁 אישורים</button>
  <button class="tb" onclick="T(\'settings\',this)">⚙ הגדרות</button>
</div>
<div class="wrap">

<div class="panel active" id="p-home">
  <div class="stats">
    <div class="stat"><div class="sn" id="sd">—</div><div class="sl">מחלקות</div></div>
    <div class="stat"><div class="sn" id="se">—</div><div class="sl">עובדים</div></div>
    <div class="stat"><div class="sn" id="st">—</div><div class="sl">משימות</div></div>
    <div class="stat"><div class="sn" id="sdn">—</div><div class="sl">הושלמו</div></div>
    <div class="stat"><div class="sn" id="sip">—</div><div class="sl">בעבודה</div></div>
    <div class="stat"><div class="sn" id="spa">—</div><div class="sl">לאישור</div></div>
  </div>
  <div class="card">
    <div class="ct">📋 שלח יעד או הוראה לצוות</div>
    <textarea id="hInst" placeholder="לדוגמה: השבוע נפרסם 5 פוסטים לקמפיין פסח..."></textarea>
    <div style="margin-top:7px;display:flex;gap:7px;align-items:center">
      <button class="btn" id="bHI" onclick="sendInst()">🚀 שלח למנכ&quot;ל</button>
      <span id="lHI" style="display:none"><span class="sp"></span></span>
    </div>
    <div class="rb" id="rHI"><div class="rl">👑 דניאל כהן – מנכ&quot;ל</div><div id="tHI"></div></div>
  </div>
  <div class="card"><div class="ct">👁 ממתינים לאישורך</div><div id="hAppr"><div style="color:var(--mt);font-size:12px">אין תוצרים</div></div></div>
  <div class="card"><div class="ct">🏬 מחלקות החברה</div><div class="dg" id="hDepts"></div></div>
</div>

<div class="panel" id="p-instruct">
  <div class="card">
    <div class="ct">📋 הוראה / יעד למנכ&quot;ל</div>
    <textarea id="mInst" placeholder="תאר בפירוט..." style="min-height:95px"></textarea>
    <div style="margin-top:7px;display:flex;gap:7px;align-items:center">
      <button class="btn" id="bMI" onclick="sendMInst()">🚀 שלח</button>
      <span id="lMI" style="display:none"><span class="sp"></span></span>
    </div>
    <div class="rb" id="rMI"><div class="rl">👑 תוכנית – דניאל כהן</div><div id="tMI" style="white-space:pre-wrap"></div></div>
  </div>
  <div class="card"><div class="ct">📜 היסטוריה</div><div id="iHist"></div></div>
</div>

<div class="panel" id="p-tasks">
  <div style="display:flex;gap:5px;margin-bottom:9px;flex-wrap:wrap;align-items:center">
    <button class="btn bsm" onclick="showNTF()">+ משימה</button>
    <button class="btn bsm bo" onclick="loadTasks()">↻</button>
    <select id="fs" style="width:auto;padding:4px 7px;font-size:11px" onchange="loadTasks()">
      <option value="">כל הסטטוסים</option><option value="pending">ממתין</option>
      <option value="in_progress">בעבודה</option><option value="done">הושלם</option>
    </select>
  </div>
  <div class="card" id="ntf" style="display:none">
    <div class="ct">+ משימה חדשה</div>
    <div class="fg"><label>כותרת</label><input type="text" id="tT" placeholder="כותרת..."></div>
    <div class="fr">
      <div class="fg"><label>מחלקה</label><select id="tD"></select></div>
      <div class="fg"><label>עדיפות</label><select id="tP"><option value="low">נמוך</option><option value="medium" selected>בינוני</option><option value="high">גבוה</option><option value="urgent">דחוף</option></select></div>
    </div>
    <div class="fg"><label>תיאור</label><textarea id="tDesc" style="min-height:50px"></textarea></div>
    <div style="display:flex;gap:5px"><button class="btn bsm bg" onclick="createTask()">✓ צור</button><button class="btn bsm bo" onclick="hideNTF()">ביטול</button></div>
  </div>
  <div id="tList"></div>
</div>

<div class="panel" id="p-employees">
  <div style="display:flex;gap:6px;margin-bottom:9px;align-items:center;flex-wrap:wrap">
    <select id="edf" style="width:auto;padding:4px 7px;font-size:11px" onchange="loadEmp()"><option value="">כל המחלקות</option></select>
    <span id="eCnt" style="font-size:10px;color:var(--mt)"></span>
  </div>
  <div class="card" style="overflow-x:auto">
    <table class="et"><thead><tr><th>שם</th><th>תפקיד</th><th>מחלקה</th><th>סטטוס</th></tr></thead>
    <tbody id="eBody"></tbody></table>
  </div>
</div>

<div class="panel" id="p-chat">
  <div class="chat-w">
    <div class="cs" id="cSide"></div>
    <div class="cm">
      <div class="ch" id="cHdr">💬 שיחה עם הצוות</div>
      <div class="msgs" id="cMsgs"><div class="msg ma"><div class="mn">דניאל כהן – מנכ&quot;ל</div>שלום! איך אוכל לעזור?</div></div>
      <div class="cin">
        <button class="btn bsm" id="bChat" onclick="sendChat()">שלח</button>
        <textarea class="ci" id="ci" placeholder="כתוב... (Enter=שלח)" onkeydown="if(event.key===\'Enter\'&&!event.shiftKey){event.preventDefault();sendChat()}"></textarea>
      </div>
    </div>
  </div>
</div>

<div class="panel" id="p-depts">
  <div class="dg" id="dGrid" style="margin-bottom:11px"></div>
  <div class="card" id="dDet" style="display:none"><div class="ct" id="dDetT"></div><div id="dDetC"></div></div>
</div>

<div class="panel" id="p-meetings">
  <div class="card">
    <div class="ct">📅 כינוס ישיבה</div>
    <div class="fg"><label>נושא</label><input type="text" id="mtT" placeholder="נושא..."></div>
    <div class="fg"><label>סדר יום</label><textarea id="mtA" style="min-height:50px" placeholder="פרט..."></textarea></div>
    <div class="fg"><label>מחלקות (עד 5)</label>
      <div style="display:flex;flex-wrap:wrap;gap:5px;margin-top:3px" id="mtD">
        <label style="display:flex;align-items:center;gap:3px;font-size:11px;color:var(--tx);cursor:pointer"><input type="checkbox" value="ceo" checked> 👑 דניאל</label>
        <label style="display:flex;align-items:center;gap:3px;font-size:11px;color:var(--tx);cursor:pointer"><input type="checkbox" value="cfo"> 💰 מיכאל</label>
        <label style="display:flex;align-items:center;gap:3px;font-size:11px;color:var(--tx);cursor:pointer"><input type="checkbox" value="marketing"> 📣 נועה</label>
        <label style="display:flex;align-items:center;gap:3px;font-size:11px;color:var(--tx);cursor:pointer"><input type="checkbox" value="sales"> 📈 רון</label>
        <label style="display:flex;align-items:center;gap:3px;font-size:11px;color:var(--tx);cursor:pointer"><input type="checkbox" value="legal"> ⚖️ תמר</label>
        <label style="display:flex;align-items:center;gap:3px;font-size:11px;color:var(--tx);cursor:pointer"><input type="checkbox" value="cto"> 💻 אלון</label>
        <label style="display:flex;align-items:center;gap:3px;font-size:11px;color:var(--tx);cursor:pointer"><input type="checkbox" value="content"> 🎨 שיר</label>
        <label style="display:flex;align-items:center;gap:3px;font-size:11px;color:var(--tx);cursor:pointer"><input type="checkbox" value="pr"> 📢 גיל</label>
        <label style="display:flex;align-items:center;gap:3px;font-size:11px;color:var(--tx);cursor:pointer"><input type="checkbox" value="compliance"> 🛡️ ענת</label>
        <label style="display:flex;align-items:center;gap:3px;font-size:11px;color:var(--tx);cursor:pointer"><input type="checkbox" value="hr"> 👥 יובל</label>
        <label style="display:flex;align-items:center;gap:3px;font-size:11px;color:var(--tx);cursor:pointer"><input type="checkbox" value="customer"> 🎧 ליאת</label>
      </div>
    </div>
    <button class="btn" id="bMt" onclick="doMeeting()">📅 כנס</button>
    <span id="lMt" style="display:none;margin-right:7px"><span class="sp"></span> ~30 שניות...</span>
    <div class="rb" id="rMt"></div>
  </div>
  <div class="card"><div class="ct">📜 ישיבות קודמות</div><div id="mtList"></div></div>
</div>

<div class="panel" id="p-social">
  <div class="card">
    <div class="ct">📱 פרסום לרשתות</div>
    <div class="fg"><label>פלטפורמות</label>
      <div style="display:flex;gap:5px;flex-wrap:wrap">
        <button class="pb" onclick="togP(\'facebook\',this)">📘 פייסבוק</button>
        <button class="pb" onclick="togP(\'instagram\',this)">📸 אינסטגרם</button>
        <button class="pb" onclick="togP(\'tiktok\',this)">🎵 טיקטוק</button>
        <button class="pb" onclick="togP(\'whatsapp\',this)">💬 וואטסאפ</button>
      </div>
    </div>
    <div style="display:flex;gap:5px;margin-bottom:8px;align-items:center">
      <button class="btn bsm bo" id="bGP" onclick="genPost()">✨ AI כותב</button>
      <input type="text" id="ptopic" placeholder="נושא..." style="flex:1">
    </div>
    <div class="fg"><label>תוכן</label><textarea id="ptxt" style="min-height:90px" placeholder="תוכן הפוסט..."></textarea></div>
    <div style="display:flex;gap:6px;align-items:center">
      <button class="btn" id="bPub" onclick="pubPost()">🚀 פרסם</button>
      <span id="lPub" style="display:none"><span class="sp"></span></span>
    </div>
    <div class="rb" id="rPub"></div>
  </div>
  <div class="card"><div class="ct">📜 פוסטים</div><div id="pList"></div></div>
</div>

<div class="panel" id="p-cashflow">
  <div style="display:flex;gap:5px;margin-bottom:9px;flex-wrap:wrap">
    <button class="btn bsm" onclick="showCFF()">+ תנועה</button>
    <button class="btn bsm bo" onclick="loadCF()">↻</button>
    <button class="btn bsm" style="background:linear-gradient(135deg,#f59e0b,#d97706)" onclick="analyzeCF()">🤖 מיכאל מנתח</button>
  </div>
  <div class="cfs">
    <div class="cfc"><div class="cfn cin2" id="cfi">—</div><div class="cfl">הכנסות</div></div>
    <div class="cfc"><div class="cfn cout" id="cfo2">—</div><div class="cfl">הוצאות</div></div>
    <div class="cfc"><div class="cfn" id="cfb">—</div><div class="cfl">יתרה</div></div>
  </div>
  <div class="card" id="cff" style="display:none">
    <div class="ct">+ תנועה חדשה</div>
    <div class="fr">
      <div class="fg"><label>תאריך</label><input type="text" id="cfD" placeholder="2025-01-15"></div>
      <div class="fg"><label>סוג</label><select id="cfTy"><option value="income">הכנסה</option><option value="expense">הוצאה</option></select></div>
    </div>
    <div class="fr">
      <div class="fg"><label>סכום (₪)</label><input type="text" id="cfA" placeholder="1000"></div>
      <div class="fg"><label>קטגוריה</label><select id="cfC"><option>שיווק</option><option>שכר</option><option>פרסום</option><option>ציוד</option><option>לקוח</option><option>כללי</option></select></div>
    </div>
    <div class="fg"><label>תיאור</label><input type="text" id="cfDe" placeholder="תיאור..."></div>
    <div style="display:flex;gap:5px"><button class="btn bsm bg" onclick="addCF()">✓ הוסף</button><button class="btn bsm bo" onclick="hideCFF()">ביטול</button></div>
  </div>
  <div class="card">
    <div class="rb" id="cfAn"></div>
    <div style="overflow-x:auto"><table class="cft"><thead><tr><th>תאריך</th><th>תיאור</th><th>קטגוריה</th><th>סוג</th><th>סכום</th></tr></thead>
    <tbody id="cfBody"></tbody></table></div>
  </div>
</div>

<div class="panel" id="p-reports">
  <div class="card">
    <div class="ct">📊 הפק דוח</div>
    <div class="fr">
      <div class="fg"><label>מחלקה</label><select id="rD"></select></div>
      <div class="fg"><label>סוג</label><select id="rT"><option value="weekly">שבועי</option><option value="monthly">חודשי</option><option value="quarterly">רבעוני</option><option value="summary">סיכום</option></select></div>
    </div>
    <button class="btn" id="bRep" onclick="genRep()">📊 הפק</button>
    <span id="lRep" style="display:none;margin-right:7px"><span class="sp"></span></span>
    <div class="rb" id="rRep"><div class="rl" id="rRL">דוח</div><div id="rRT" style="white-space:pre-wrap"></div></div>
  </div>
  <div class="card"><div class="ct">📁 דוחות קודמים</div><div id="repList"></div></div>
</div>

<div class="panel" id="p-strategy">
  <div class="card">
    <div class="ct">🎯 יעדים אסטרטגיים</div>
    <textarea id="stratG" placeholder="לדוגמה: עד סוף הרבעון 100 לקוחות..." style="min-height:85px"></textarea>
    <div style="margin-top:7px;display:flex;gap:6px;align-items:center">
      <button class="btn" id="bGoals" onclick="setGoals()">🎯 שלח</button>
      <span id="lGoals" style="display:none"><span class="sp"></span></span>
    </div>
    <div class="rb" id="rGoals"><div class="rl">📋 תוכנית</div><div id="tGoals" style="white-space:pre-wrap"></div></div>
  </div>
  <div class="card"><div class="ct">📌 יעדים קודמים</div><div id="gList"></div></div>
</div>

<div class="panel" id="p-approvals">
  <div class="card"><div class="ct">👁 ממתינים לאישורך</div><div id="aList"></div></div>
</div>

<div class="panel" id="p-settings">
  <div class="card"><div class="ct">⚙ חיבורי מערכת</div><div id="cSt"></div></div>
  <div class="card">
    <div class="ct">🗄 SQL – Supabase</div>
    <p style="font-size:10px;color:var(--mt);margin-bottom:6px">הרץ ב-SQL Editor:</p>
    <pre style="background:var(--sur);border:1px solid var(--bdr);border-radius:7px;padding:8px;font-size:9px;overflow-x:auto;color:var(--ac2);white-space:pre;direction:ltr;text-align:left">CREATE TABLE IF NOT EXISTS tasks(id uuid DEFAULT gen_random_uuid() PRIMARY KEY,title text,description text,department text,status text DEFAULT \'pending\',priority text DEFAULT \'medium\',created_by text,created_at timestamptz DEFAULT now(),approved_at timestamptz);
CREATE TABLE IF NOT EXISTS instructions(id uuid DEFAULT gen_random_uuid() PRIMARY KEY,text text,ceo_response text,status text,created_at timestamptz DEFAULT now());
CREATE TABLE IF NOT EXISTS meetings(id uuid DEFAULT gen_random_uuid() PRIMARY KEY,topic text,agenda text,responses jsonb,status text,created_at timestamptz DEFAULT now());
CREATE TABLE IF NOT EXISTS reports(id uuid DEFAULT gen_random_uuid() PRIMARY KEY,title text,department text,content text,type text,created_at timestamptz DEFAULT now());
CREATE TABLE IF NOT EXISTS chat_messages(id uuid DEFAULT gen_random_uuid() PRIMARY KEY,department text,user_message text,ai_response text,created_at timestamptz DEFAULT now());
CREATE TABLE IF NOT EXISTS strategic_goals(id uuid DEFAULT gen_random_uuid() PRIMARY KEY,goals text,plan text,status text,created_at timestamptz DEFAULT now());
CREATE TABLE IF NOT EXISTS cashflow(id uuid DEFAULT gen_random_uuid() PRIMARY KEY,date date,description text,amount numeric,type text,category text,client_id text,created_at timestamptz DEFAULT now());
CREATE TABLE IF NOT EXISTS social_posts(id uuid DEFAULT gen_random_uuid() PRIMARY KEY,text text,platforms jsonb,status text,created_at timestamptz DEFAULT now());</pre>
  </div>
</div>

</div>
<script>
// ═══════════════════════════════════════════
// AUTH – cookie-based, no token needed in JS
// The server sets the cookie on login.
// All API calls go to /api/* with Basic Auth
// extracted from the cookie automatically.
// ═══════════════════════════════════════════
function getCookie(n){
  var m=document.cookie.match(new RegExp('(?:^|; )'+n+'=([^;]*)'));
  return m?decodeURIComponent(m[1]):'';
}
var TOKEN=getCookie('jabr_token');
function AH(){return{'Content-Type':'application/json','Authorization':TOKEN?'Basic '+TOKEN:''};}

async function api(m,p,b){
  var o={method:m,headers:AH()};
  if(b)o.body=JSON.stringify(b);
  var r=await fetch('/api'+p,o);
  if(r.status===401){window.location.href='/';return null;}
  if(!r.ok){var e=await r.text();throw new Error(e);}
  return r.json();
}
function fd(d){if(!d)return'';try{return new Date(d).toLocaleDateString('he-IL',{day:'2-digit',month:'2-digit',year:'2-digit',hour:'2-digit',minute:'2-digit'})}catch{return d}}
function fN(n){return Number(n||0).toLocaleString('he-IL')}
function busy(b,l,on){var be=document.getElementById(b),le=document.getElementById(l);if(be)be.disabled=on;if(le)le.style.display=on?'inline-flex':'none';}

// ─── Tabs ───────────────────────────────────
var tmap={home:iHome,instruct:iInstruct,tasks:loadTasks,employees:loadEmp,chat:buildChat,
  depts:loadDepts,meetings:loadMeetings,social:iSocial,cashflow:loadCF,
  reports:iReports,strategy:loadGoals,approvals:loadApprls,settings:checkConn};
function T(n,btn){
  document.querySelectorAll('.panel').forEach(function(p){p.classList.remove('active');});
  document.querySelectorAll('.tb').forEach(function(b){b.classList.remove('active');});
  var pnl=document.getElementById('p-'+n);if(pnl)pnl.classList.add('active');
  if(btn)btn.classList.add('active');
  if(tmap[n])tmap[n]();
}

// ─── Dept cache ─────────────────────────────
var DC=[];
async function gD(){if(!DC.length){var d=await api('GET','/departments');DC=d||[];}return DC;}

// ─── Stats ──────────────────────────────────
async function loadStats(){
  try{var s=await api('GET','/stats');if(!s)return;
    ['sd','se','st','sdn','sip','spa'].forEach(function(k,i){
      var v=[s.departments,s.employees,s.tasks_total,s.tasks_done,s.tasks_inprog,s.tasks_pending];
      var e=document.getElementById(k);if(e)e.textContent=v[i]||'0';
    });
  }catch(e){}
}

// ─── Home ────────────────────────────────────
async function iHome(){
  loadStats();
  var depts=await gD();
  var g=document.getElementById('hDepts');
  if(g)g.innerHTML=depts.map(function(d){return '<div class="dc" style="border-top:3px solid '+d.color+'" onclick="T(\'chat\',null);selAgent(\''+d.id+'\',\''+d.name+'\',\''+d.head+'\',\''+d.title+'\')">'+'<div class="di">'+d.icon+'</div><div class="dn">'+d.name+'</div><div class="dh">'+d.head+'</div><div class="dt">'+d.title+'</div></div>';}).join('');
  try{var a=await api('GET','/approvals');if(!a)return;var el=document.getElementById('hAppr');if(el)el.innerHTML=a.length?a.slice(0,3).map(tHTML).join(''):'<div style="color:var(--mt);font-size:12px">אין תוצרים</div>';}catch(e){}
}

// ─── Instruct ────────────────────────────────
async function sendInst(){
  var t=document.getElementById('hInst').value.trim();if(!t){alert('נא לכתוב הוראה');return;}
  busy('bHI','lHI',true);
  try{var r=await api('POST','/instruct',{instruction:t});if(!r)return;
    document.getElementById('rHI').classList.add('show');document.getElementById('tHI').textContent=r.ceo_response;
  }catch(e){alert('שגיאה: '+e.message);}
  busy('bHI','lHI',false);
}
async function sendMInst(){
  var t=document.getElementById('mInst').value.trim();if(!t){alert('נא לכתוב');return;}
  busy('bMI','lMI',true);
  try{var r=await api('POST','/instruct',{instruction:t});if(!r)return;
    document.getElementById('rMI').classList.add('show');document.getElementById('tMI').textContent=r.ceo_response;
    iInstruct();
  }catch(e){alert('שגיאה: '+e.message);}
  busy('bMI','lMI',false);
}
async function iInstruct(){
  try{var items=await api('GET','/instructions');if(!items)return;
    var el=document.getElementById('iHist');if(!el)return;
    if(!items.length){el.innerHTML='<div style="color:var(--mt);font-size:12px">אין היסטוריה</div>';return;}
    el.innerHTML=items.map(function(i){return '<div class="ti"><div class="tdot di2"></div><div class="tii"><div class="tit">'+i.text+'</div><div class="tim">'+fd(i.created_at)+'</div>'+(i.ceo_response?'<div style="font-size:10px;color:var(--mt);margin-top:4px;max-height:55px;overflow:hidden">'+i.ceo_response.substring(0,200)+'</div>':'')+'</div></div>';}).join('');
  }catch(e){}
}

// ─── Tasks ───────────────────────────────────
var PM={pending:'dp',in_progress:'di2',done:'dd',pending_approval:'da'};
var TM={pending:'to',in_progress:'tag',done:'tg',pending_approval:'ty'};
var LM={pending:'ממתין',in_progress:'בעבודה',done:'הושלם',pending_approval:'לאישור'};
function tHTML(t){return '<div class="ti"><div class="tdot '+(PM[t.status]||'dp')+'"></div><div class="tii"><div class="tit">'+(t.title||'')+'</div><div class="tim">'+(t.department||'')+' • '+fd(t.created_at)+'</div></div><span class="tag '+(TM[t.status]||'')+'">'+(LM[t.status]||t.status)+'</span>'+(t.status==='pending_approval'?'<button class="btn bsm bg" onclick="approveT(\''+t.id+'\')">✓</button>':'')+'</div>';}
async function loadTasks(){
  var st=document.getElementById('fs')?document.getElementById('fs').value:'';
  try{var items=await api('GET','/tasks'+(st?'?status='+st:''));if(!items)return;
    var el=document.getElementById('tList');if(!el)return;
    el.innerHTML=items.length?'<div class="card">'+items.map(tHTML).join('')+'</div>':'<div class="card"><div style="color:var(--mt);font-size:12px">אין משימות</div></div>';
    var df=document.getElementById('tD');if(df&&!df.options.length){var depts=await gD();depts.forEach(function(d){var o=document.createElement('option');o.value=d.id;o.textContent=d.name;df.appendChild(o);});}
  }catch(e){}
}
async function createTask(){
  var title=document.getElementById('tT').value.trim();if(!title){alert('נא להזין כותרת');return;}
  try{await api('POST','/tasks',{title:title,description:document.getElementById('tDesc').value,department:document.getElementById('tD').value,priority:document.getElementById('tP').value});hideNTF();loadTasks();}
  catch(e){alert('שגיאה: '+e.message);}
}
async function approveT(id){try{await api('POST','/tasks/'+id+'/approve');loadTasks();}catch(e){}}
async function showNTF(){document.getElementById('ntf').style.display='block';var d=document.getElementById('tD');if(d&&!d.options.length){var depts=await gD();depts.forEach(function(dep){var o=document.createElement('option');o.value=dep.id;o.textContent=dep.name;d.appendChild(o);});}}
function hideNTF(){document.getElementById('ntf').style.display='none';}

// ─── Employees ───────────────────────────────
async function loadEmp(){
  var dept=document.getElementById('edf')?document.getElementById('edf').value:'';
  try{var items=await api('GET','/employees'+(dept?'?dept='+dept:''));if(!items)return;
    var cnt=document.getElementById('eCnt');if(cnt)cnt.textContent='סה"כ: '+items.length+' עובדים';
    var body=document.getElementById('eBody');if(!body)return;
    var depts=await gD();var dm={};depts.forEach(function(d){dm[d.id]=d;});
    body.innerHTML=items.map(function(e){var d=dm[e.department]||{};var ini=(e.name||'').split(' ').map(function(w){return w[0];}).join('').substring(0,2);return'<tr><td style="display:flex;align-items:center"><div class="av">'+ini+'</div>'+e.name+'</td><td>'+e.role+'</td><td>'+(d.icon||'')+' '+(d.name||e.department)+'</td><td><span class="tag tg">פעיל</span></td></tr>';}).join('');
    var df=document.getElementById('edf');if(df&&df.options.length<=1){depts.forEach(function(d){var o=document.createElement('option');o.value=d.id;o.textContent=d.icon+' '+d.name;df.appendChild(o);});}
  }catch(e){}
}

// ─── Chat ────────────────────────────────────
var cAg='ceo',cH=[],cN='דניאל כהן',cT='מנכ"ל';
async function buildChat(){
  var depts=await gD();var sb=document.getElementById('cSide');if(!sb)return;
  sb.innerHTML=depts.map(function(d,i){return'<button class="ca'+(i===0?' active':'')+'" onclick="selAgent(\''+d.id+'\',\''+d.name+'\',\''+d.head+'\',\''+d.title+'\',this)"><span class="can">'+d.icon+' '+d.head+'</span><span class="car">'+d.title+'</span></button>';}).join('');
}
function selAgent(id,dn,head,title,btn){
  cAg=id;cN=head;cT=title;cH=[];
  document.querySelectorAll('.ca').forEach(function(b){b.classList.remove('active');});if(btn)btn.classList.add('active');
  var h=document.getElementById('cHdr');if(h)h.textContent='💬 '+head+' – '+title;
  var m=document.getElementById('cMsgs');if(m)m.innerHTML='<div class="msg ma"><div class="mn">'+head+' – '+title+'</div>שלום! אני '+head+'. איך אוכל לעזור?</div>';
}
async function sendChat(){
  var inp=document.getElementById('ci');var msg=inp.value.trim();if(!msg)return;inp.value='';
  var msgs=document.getElementById('cMsgs');
  msgs.innerHTML+='<div class="msg mu">'+msg.replace(/\n/g,'<br>')+'</div>';
  msgs.innerHTML+='<div class="msg ma" id="typing"><div class="mn">'+cN+'</div><span class="sp"></span></div>';
  msgs.scrollTop=msgs.scrollHeight;cH.push({role:'user',content:msg});
  document.getElementById('bChat').disabled=true;
  try{var r=await api('POST','/chat/'+cAg,{message:msg,history:cH});if(!r)return;
    var t=document.getElementById('typing');if(t)t.remove();
    msgs.innerHTML+='<div class="msg ma"><div class="mn">'+(r.agent||cN)+' – '+(r.title||cT)+'</div>'+r.response.replace(/\n/g,'<br>')+'</div>';
    cH.push({role:'assistant',content:r.response});msgs.scrollTop=msgs.scrollHeight;
  }catch(e){var t=document.getElementById('typing');if(t)t.innerHTML='<div class="mn">שגיאה</div>'+e.message;}
  document.getElementById('bChat').disabled=false;
}

// ─── Departments ─────────────────────────────
async function loadDepts(){
  var depts=await gD();var g=document.getElementById('dGrid');if(!g)return;
  g.innerHTML=depts.map(function(d){return'<div class="dc" style="border-top:3px solid '+d.color+'" onclick="showDD(\''+d.id+'\',\''+d.name+'\',\''+d.icon+'\')">'+'<div class="di">'+d.icon+'</div><div class="dn">'+d.name+'</div><div class="dh">'+d.head+'</div><div class="dt">'+d.title+'</div></div>';}).join('');
}
async function showDD(id,name,icon){
  document.getElementById('dDet').style.display='block';document.getElementById('dDetT').textContent=icon+' '+name;
  document.getElementById('dDetC').innerHTML='<div style="color:var(--mt)">טוען...</div>';
  try{var emps=await api('GET','/employees?dept='+id);var tasks=await api('GET','/tasks?dept='+id);
    document.getElementById('dDetC').innerHTML='<div style="display:grid;grid-template-columns:1fr 1fr;gap:10px"><div><div style="font-size:9px;color:var(--mt);margin-bottom:5px">צוות ('+emps.length+')</div>'+emps.map(function(e){return'<div class="ti"><div class="tdot '+(e.title==="מנהל"?'da':'dd')+'"></div><div class="tii"><div class="tit">'+e.name+'</div><div class="tim">'+e.role+'</div></div></div>';}).join('')+'</div><div><div style="font-size:9px;color:var(--mt);margin-bottom:5px">משימות ('+tasks.length+')</div>'+(tasks.slice(0,4).map(tHTML).join('')||'<div style="color:var(--mt);font-size:11px">אין</div>')+'</div></div>';
  }catch(e){}
}

// ─── Meetings ────────────────────────────────
async function doMeeting(){
  var topic=document.getElementById('mtT').value.trim();if(!topic){alert('נא להזין נושא');return;}
  var dpts=Array.from(document.querySelectorAll('#mtD input:checked')).map(function(i){return i.value;});
  if(!dpts.length){alert('נא לבחור מחלקה');return;}
  busy('bMt','lMt',true);
  try{var r=await api('POST','/meetings',{topic:topic,agenda:document.getElementById('mtA').value,departments:dpts});if(!r)return;
    var box=document.getElementById('rMt');box.classList.add('show');
    var dm={};(await gD()).forEach(function(d){dm[d.id]=d;});
    var html='<div class="rl">📅 '+topic+'</div>';
    Object.entries(r.responses||{}).forEach(function(kv){var info=dm[kv[0]]||{};html+='<div class="dr"><div class="drn">'+(info.icon||'')+' '+(info.head||kv[0])+'</div>'+kv[1]+'</div>';});
    box.innerHTML=html;loadMeetings();
  }catch(e){alert('שגיאה: '+e.message);}
  busy('bMt','lMt',false);
}
async function loadMeetings(){
  try{var items=await api('GET','/meetings');if(!items)return;
    var el=document.getElementById('mtList');if(!el)return;
    if(!items.length){el.innerHTML='<div style="color:var(--mt);font-size:12px">אין ישיבות</div>';return;}
    var dm={};(await gD()).forEach(function(d){dm[d.id]=d;});
    el.innerHTML=items.map(function(m){var rs='';try{var obj=typeof m.responses==='string'?JSON.parse(m.responses):m.responses;Object.entries(obj||{}).forEach(function(kv){var info=dm[kv[0]]||{};rs+='<div class="dr"><div class="drn">'+(info.icon||'')+' '+(info.head||kv[0])+'</div>'+kv[1].substring(0,150)+'...</div>';});}catch(e){}return'<div class="card" style="margin-bottom:7px"><div style="font-weight:700;margin-bottom:3px">'+m.topic+'</div><div style="font-size:10px;color:var(--mt)">'+fd(m.created_at)+'</div>'+(rs?'<div style="margin-top:7px">'+rs+'</div>':'')+'</div>';}).join('');
  }catch(e){}
}

// ─── Social ──────────────────────────────────
var selP={};
function togP(p,btn){if(selP[p]){delete selP[p];btn.classList.remove('sel');}else{selP[p]=true;btn.classList.add('sel');}}
async function genPost(){
  var t=document.getElementById('ptopic').value.trim();if(!t){alert('נא להזין נושא');return;}
  var b=document.getElementById('bGP');b.disabled=true;b.textContent='...';
  try{var r=await api('POST','/social/generate',{topic:t});if(r)document.getElementById('ptxt').value=r.post;}
  catch(e){alert('שגיאה: '+e.message);}
  b.disabled=false;b.textContent='✨ AI כותב';
}
async function pubPost(){
  var txt=document.getElementById('ptxt').value.trim();if(!txt){alert('נא לכתוב תוכן');return;}
  if(!Object.keys(selP).length){alert('נא לבחור פלטפורמה');return;}
  busy('bPub','lPub',true);
  try{var r=await api('POST','/social/publish',{text:txt,platforms:Object.keys(selP)});if(!r)return;
    var box=document.getElementById('rPub');box.classList.add('show');box.innerHTML='<div class="rl">פורסם</div>'+JSON.stringify(r.results,null,2);
    loadPosts();
  }catch(e){alert('שגיאה: '+e.message);}
  busy('bPub','lPub',false);
}
async function loadPosts(){
  try{var items=await api('GET','/social/posts');if(!items)return;
    var el=document.getElementById('pList');if(!el)return;
    if(!items.length){el.innerHTML='<div style="color:var(--mt);font-size:12px">אין פוסטים</div>';return;}
    el.innerHTML=items.map(function(p){var plats=typeof p.platforms==='string'?JSON.parse(p.platforms):p.platforms||[];return'<div class="ti"><div class="tdot dd"></div><div class="tii"><div class="tit">'+(p.text||'').substring(0,70)+'...</div><div class="tim">'+plats.join(', ')+' • '+fd(p.created_at)+'</div></div></div>';}).join('');
  }catch(e){}
}
async function iSocial(){loadPosts();}

// ─── Cashflow ────────────────────────────────
async function loadCF(){
  try{var items=await api('GET','/cashflow');if(!items)return;
    var body=document.getElementById('cfBody');if(!body)return;
    if(!items.length){body.innerHTML='<tr><td colspan="5" style="color:var(--mt);text-align:center;padding:10px">אין נתונים</td></tr>';return;}
    var ti=0,to=0;
    body.innerHTML=items.map(function(r){var inc=r.type==='income';if(inc)ti+=Number(r.amount||0);else to+=Number(r.amount||0);return'<tr><td>'+r.date+'</td><td>'+r.description+'</td><td>'+r.category+'</td><td><span class="tag '+(inc?'tg':'to')+'">'+(inc?'הכנסה':'הוצאה')+'</span></td><td class="'+(inc?'cin2':'cout')+'">'+(inc?'+':'-')+fN(r.amount)+' ₪</td></tr>';}).join('');
    document.getElementById('cfi').textContent=fN(ti)+' ₪';document.getElementById('cfo2').textContent=fN(to)+' ₪';
    var bal=ti-to;var be=document.getElementById('cfb');be.textContent=fN(bal)+' ₪';be.className='cfn '+(bal>=0?'cin2':'cout');
  }catch(e){}
}
async function addCF(){
  var amt=parseFloat(document.getElementById('cfA').value);if(!amt||isNaN(amt)){alert('נא להזין סכום');return;}
  try{await api('POST','/cashflow',{date:document.getElementById('cfD').value||new Date().toISOString().split('T')[0],description:document.getElementById('cfDe').value,amount:amt,type:document.getElementById('cfTy').value,category:document.getElementById('cfC').value});hideCFF();loadCF();}
  catch(e){alert('שגיאה: '+e.message);}
}
async function analyzeCF(){
  var el=document.getElementById('cfAn');el.classList.add('show');el.innerHTML='<span class="sp"></span> מיכאל לוי מנתח...';
  try{var r=await api('POST','/cashflow/analyze');el.innerHTML='<div class="rl">💰 ניתוח – מיכאל לוי CFO</div>'+r.analysis.replace(/\n/g,'<br>');}
  catch(e){el.innerHTML='שגיאה: '+e.message;}
}
function showCFF(){document.getElementById('cff').style.display='block';}function hideCFF(){document.getElementById('cff').style.display='none';}

// ─── Reports ─────────────────────────────────
async function iReports(){
  loadRepList();var d=document.getElementById('rD');
  if(d&&!d.options.length){var depts=await gD();depts.forEach(function(dep){var o=document.createElement('option');o.value=dep.id;o.textContent=dep.name;d.appendChild(o);});}
}
async function genRep(){
  busy('bRep','lRep',true);
  try{var r=await api('POST','/reports/generate',{department:document.getElementById('rD').value,type:document.getElementById('rT').value});if(!r)return;
    document.getElementById('rRep').classList.add('show');document.getElementById('rRL').textContent=r.report.title;document.getElementById('rRT').textContent=r.report.content;
    loadRepList();
  }catch(e){alert('שגיאה: '+e.message);}
  busy('bRep','lRep',false);
}
async function loadRepList(){
  try{var items=await api('GET','/reports');if(!items)return;
    var el=document.getElementById('repList');if(!el)return;
    if(!items.length){el.innerHTML='<div style="color:var(--mt);font-size:12px">אין דוחות</div>';return;}
    el.innerHTML=items.map(function(r){return'<div class="ti"><div class="tdot dd"></div><div class="tii"><div class="tit">'+r.title+'</div><div class="tim">'+r.type+' • '+fd(r.created_at)+'</div></div></div>';}).join('');
  }catch(e){}
}

// ─── Strategy ────────────────────────────────
async function setGoals(){
  var g=document.getElementById('stratG').value.trim();if(!g){alert('נא להזין יעדים');return;}
  busy('bGoals','lGoals',true);
  try{var r=await api('POST','/strategy/goals',{goals:g});if(!r)return;
    document.getElementById('rGoals').classList.add('show');document.getElementById('tGoals').textContent=r.plan;
    loadGoals();
  }catch(e){alert('שגיאה: '+e.message);}
  busy('bGoals','lGoals',false);
}
async function loadGoals(){
  try{var items=await api('GET','/strategy/goals');if(!items)return;
    var el=document.getElementById('gList');if(!el)return;
    if(!items.length){el.innerHTML='<div style="color:var(--mt);font-size:12px">אין יעדים</div>';return;}
    el.innerHTML=items.map(function(g){return'<div class="card" style="margin-bottom:6px"><div style="font-size:12px;font-weight:600">'+g.goals+'</div>'+(g.plan?'<div style="font-size:10px;color:var(--mt);margin-top:5px;max-height:120px;overflow:hidden">'+g.plan.substring(0,350)+'</div>':'')+'<div style="font-size:9px;color:var(--mt);margin-top:4px">'+fd(g.created_at)+'</div></div>';}).join('');
  }catch(e){}
}

// ─── Approvals ───────────────────────────────
async function loadApprls(){
  try{var items=await api('GET','/approvals');if(!items)return;
    var el=document.getElementById('aList');if(!el)return;
    el.innerHTML=items.length?items.map(tHTML).join(''):'<div style="color:var(--mt);font-size:12px">אין תוצרים</div>';
  }catch(e){}
}

// ─── Settings ────────────────────────────────
async function checkConn(){
  try{var h=await api('GET','/health');if(!h)return;
    var el=document.getElementById('cSt');if(!el)return;
    var rows=[['🤖 Claude AI',h.anthropic],['🗄 Supabase',h.supabase]];
    el.innerHTML=rows.map(function(x){return'<div class="cr"><span>'+x[0]+'</span><span style="color:'+(x[1]?'var(--grn)':'var(--red)')+'">'+(x[1]?'✅ מחובר':'❌ לא מוגדר')+'</span></div>';}).join('');
  }catch(e){}
}

// ─── Init ────────────────────────────────────
window.addEventListener('load',async function(){
  await gD();
  buildChat();
  iHome();
});
</script>
</body></html>'''
    res=[]
    for did in([dept]if dept else DMETA):
        ag=AGENTS.get(did)
        if ag:res.append({"id":f"{did}-0","name":ag[0],"role":ag[1],"department":did,"title":"מנהל","status":"active"})
        for nm,rl in EMPS.get(did,[]):res.append({"id":f"{did}-{nm}","name":nm,"role":rl,"department":did,"title":"עובד","status":"active"})
    return res

@app.get("/api/tasks")
async def tasks(status:Optional[str]=None,dept:Optional[str]=None,u=Depends(verify_auth)):
    q="order=created_at.desc&limit=50"
    if status:q+=f"&status=eq.{status}"
    if dept:q+=f"&department=eq.{dept}"
    return await sb_get("tasks",q)

@app.post("/api/tasks")
async def create_task(req:Request,u=Depends(verify_auth)):
    b=await req.json()
    if not b.get("title","").strip():raise HTTPException(400,"נא להזין כותרת")
    return await sb_ins("tasks",{"title":b["title"],"description":b.get("description",""),"department":b.get("department","ceo"),"priority":b.get("priority","medium"),"status":"pending","created_by":u,"created_at":datetime.utcnow().isoformat()})

@app.post("/api/tasks/{tid}/approve")
async def approve(tid:str,u=Depends(verify_auth)):
    if SUPABASE_URL:
        async with httpx.AsyncClient() as c:
            await c.patch(f"{SUPABASE_URL}/rest/v1/tasks?id=eq.{tid}",headers=SBH(),json={"status":"approved"},timeout=10)
    return{"ok":True}

@app.post("/api/instruct")
async def instruct(req:Request,u=Depends(verify_auth)):
    b=await req.json();inst=b.get("instruction","").strip()
    if not inst:raise HTTPException(400,"נא לכתוב הוראה")
    resp=await claude("ceo",f'קיבלת הוראה מיו"ר:\n"{inst}"\n\n1.נתח 2.אילו מחלקות? 3.תוכנית פעולה 4.ציר זמן')
    await sb_ins("instructions",{"text":inst,"ceo_response":resp,"status":"processing","created_at":datetime.utcnow().isoformat()})
    return{"instruction":inst,"ceo_response":resp}

@app.get("/api/instructions")
async def get_insts(u=Depends(verify_auth)):return await sb_get("instructions","order=created_at.desc&limit=20")

@app.post("/api/chat/{dept}")
async def chat(dept:str,req:Request,u=Depends(verify_auth)):
    b=await req.json();msg=b.get("message","");hist=b.get("history",[])
    ctx="\n".join([f"{m['role']}: {m['content']}"for m in hist[-8:]])
    resp=await claude(dept,msg,ctx)
    await sb_ins("chat_messages",{"department":dept,"user_message":msg,"ai_response":resp,"created_at":datetime.utcnow().isoformat()})
    ag=AGENTS.get(dept,("AI","",""))
    return{"response":resp,"agent":ag[0],"title":ag[1]}

@app.post("/api/meetings")
async def meeting(req:Request,u=Depends(verify_auth)):
    b=await req.json();topic=b.get("topic","");agenda=b.get("agenda","");dpts=b.get("departments",["ceo"])
    rs={}
    for d in dpts[:5]:rs[d]=await claude(d,f'ישיבה: {topic}\nסדר יום: {agenda}\nמה עמדתך?')
    await sb_ins("meetings",{"topic":topic,"agenda":agenda,"responses":json.dumps(rs,ensure_ascii=False),"status":"completed","created_at":datetime.utcnow().isoformat()})
    return{"responses":rs}

@app.get("/api/meetings")
async def get_meetings(u=Depends(verify_auth)):return await sb_get("meetings","order=created_at.desc&limit=20")

@app.post("/api/reports/generate")
async def gen_rep(req:Request,u=Depends(verify_auth)):
    b=await req.json();dept=b.get("department","ceo");rt=b.get("type","weekly")
    dn=DMETA.get(dept,{}).get("name",dept)
    c=await claude(dept,f'צור דוח {rt} למחלקת {dn}. כלול: סיכום, הישגים, אתגרים, תוכנית.')
    r={"title":f'דוח {rt} – {dn}',"department":dept,"content":c,"type":rt,"created_at":datetime.utcnow().isoformat()}
    await sb_ins("reports",r)
    return{"report":r}

@app.get("/api/reports")
async def get_reps(u=Depends(verify_auth)):return await sb_get("reports","order=created_at.desc&limit=20")

@app.get("/api/approvals")
async def approvals(u=Depends(verify_auth)):return await sb_get("tasks","status=eq.pending_approval&order=created_at.desc")

@app.post("/api/strategy/goals")
async def set_goals(req:Request,u=Depends(verify_auth)):
    b=await req.json();goals=b.get("goals","").strip()
    if not goals:raise HTTPException(400,"נא להזין יעדים")
    plan=await claude("ceo",f'יו"ר הציב יעדים:\n{goals}\n\nצור תוכנית: 1.פירוט 2.לו"ז 3.KPIs 4.סיכונים 5.תקציב')
    await sb_ins("strategic_goals",{"goals":goals,"plan":plan,"status":"active","created_at":datetime.utcnow().isoformat()})
    return{"goals":goals,"plan":plan}

@app.get("/api/strategy/goals")
async def get_goals(u=Depends(verify_auth)):return await sb_get("strategic_goals","order=created_at.desc&limit=10")

@app.get("/api/cashflow")
async def get_cf(u=Depends(verify_auth)):return await sb_get("cashflow","order=date.desc&limit=200")

@app.post("/api/cashflow")
async def add_cf(req:Request,u=Depends(verify_auth)):
    b=await req.json()
    try:amt=float(b.get("amount",0))
    except:raise HTTPException(400,"סכום לא תקין")
    return await sb_ins("cashflow",{"date":b.get("date",datetime.utcnow().date().isoformat()),"description":b.get("description",""),"amount":amt,"type":b.get("type","income"),"category":b.get("category","כללי"),"client_id":b.get("client_id",""),"created_at":datetime.utcnow().isoformat()})

@app.post("/api/cashflow/analyze")
async def analyze_cf(u=Depends(verify_auth)):
    rows=await sb_get("cashflow","order=date.desc&limit=100")
    if not rows:return{"analysis":"אין נתוני תזרים עדיין.","rows":[]}
    ti=sum(float(r.get("amount",0))for r in rows if r.get("type")=="income")
    to=sum(float(r.get("amount",0))for r in rows if r.get("type")=="expense")
    a=await claude("cfo",f'תזרים: הכנסות={ti:,.0f}₪ הוצאות={to:,.0f}₪ יתרה={ti-to:,.0f}₪\nנתח ותן המלצות.')
    return{"analysis":a,"rows":rows,"summary":{"income":ti,"expense":to,"balance":ti-to}}

@app.post("/api/social/generate")
async def gen_post(req:Request,u=Depends(verify_auth)):
    b=await req.json()
    p=await claude("content",f'כתוב פוסט לסושיאל בנושא: {b.get("topic","")}\nכלול כותרת, גוף, CTA, האשטגים.')
    return{"post":p}

@app.post("/api/social/publish")
async def pub_post(req:Request,u=Depends(verify_auth)):
    b=await req.json()
    if not b.get("text",""):raise HTTPException(400,"נא לכתוב תוכן")
    results={}
    txt=b["text"];img=b.get("image_url","");plats=b.get("platforms",[])
    if "facebook" in plats and META_PAGE_TOKEN and META_PAGE_ID:
        async with httpx.AsyncClient() as c:
            r=await c.post(f"https://graph.facebook.com/v19.0/{META_PAGE_ID}/feed",data={"message":txt,"access_token":META_PAGE_TOKEN},timeout=20)
            res=r.json();results["facebook"]={"ok":"id"in res,"post_id":res.get("id"),"error":res.get("error",{}).get("message")}
    elif "facebook" in plats:
        results["facebook"]={"ok":False,"error":"חסר META_PAGE_TOKEN ב-Railway"}
    if "instagram" in plats and META_PAGE_TOKEN and INSTAGRAM_ID and img:
        async with httpx.AsyncClient() as c:
            r1=await c.post(f"https://graph.facebook.com/v19.0/{INSTAGRAM_ID}/media",data={"image_url":img,"caption":txt,"access_token":META_PAGE_TOKEN},timeout=20)
            mid=r1.json().get("id")
            if mid:
                r2=await c.post(f"https://graph.facebook.com/v19.0/{INSTAGRAM_ID}/media_publish",data={"creation_id":mid,"access_token":META_PAGE_TOKEN},timeout=20)
                res=r2.json();results["instagram"]={"ok":"id"in res,"post_id":res.get("id")}
            else:results["instagram"]={"ok":False,"error":r1.json().get("error",{}).get("message","שגיאה")}
    elif "instagram" in plats:
        results["instagram"]={"ok":False,"error":"חסר INSTAGRAM_ACCOUNT_ID או תמונה"}
    if "whatsapp" in plats:
        phone=b.get("whatsapp_phone","")
        if phone and WHATSAPP_TOKEN and WHATSAPP_PHONE:
            async with httpx.AsyncClient() as c:
                r=await c.post(f"https://graph.facebook.com/v19.0/{WHATSAPP_PHONE}/messages",headers={"Authorization":f"Bearer {WHATSAPP_TOKEN}","Content-Type":"application/json"},json={"messaging_product":"whatsapp","to":phone,"type":"text","text":{"body":txt}},timeout=20)
                res=r.json();results["whatsapp"]={"ok":"messages"in res,"error":res.get("error",{}).get("message")}
        else:results["whatsapp"]={"ok":False,"error":"חסר WHATSAPP_TOKEN או מספר"}
    await sb_ins("social_posts",{"text":txt,"image_url":img,"platforms":json.dumps(plats),"results":json.dumps(results,ensure_ascii=False),"status":"published"if any(r.get("ok")for r in results.values())else"pending","created_at":datetime.utcnow().isoformat()})
    return{"text":txt,"results":results}

@app.get("/api/social/posts")
async def get_posts(u=Depends(verify_auth)):return await sb_get("social_posts","order=created_at.desc&limit=30")


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

<div class="panel active" id="panel-home">
  <div class="stats">
    <div class="stat"><div class="sn" id="sd">—</div><div class="sl">מחלקות</div></div>
    <div class="stat"><div class="sn" id="se">—</div><div class="sl">עובדים</div></div>
    <div class="stat"><div class="sn" id="st">—</div><div class="sl">משימות</div></div>
    <div class="stat"><div class="sn" id="sdn">—</div><div class="sl">הושלמו</div></div>
    <div class="stat"><div class="sn" id="sip">—</div><div class="sl">בעבודה</div></div>
    <div class="stat"><div class="sn" id="spa">—</div><div class="sl">לאישור</div></div>
  </div>
  <div class="card">
    <div class="ct">📋 שלח יעד או הוראה לצוות</div>
    <textarea id="homeInst" placeholder="לדוגמה: השבוע נפרסם 5 פוסטים לקמפיין פסח. תכין תוכנית."></textarea>
    <div style="margin-top:8px;display:flex;gap:7px;align-items:center">
      <button class="btn" id="bHI" onclick="sendInst()">🚀 שלח למנכ&quot;ל</button>
      <span id="lHI" style="display:none"><span class="sp"></span> מטפל...</span>
    </div>
    <div class="rb" id="rHI"><div class="rl">👑 דניאל כהן – מנכ&quot;ל</div><div id="tHI"></div></div>
  </div>
  <div class="card"><div class="ct">👁 ממתינים לאישורך</div><div id="homeAppr"><div style="color:var(--mt);font-size:12px">אין תוצרים</div></div></div>
  <div class="card"><div class="ct">🏬 מחלקות החברה</div><div class="dg" id="homeDepts"></div></div>
</div>

<div class="panel" id="panel-instruct">
  <div class="card">
    <div class="ct">📋 הוראה / יעד למנכ&quot;ל</div>
    <p style="font-size:11px;color:var(--mt);margin-bottom:9px">כתוב כל הוראה או יעד. המנכ&quot;ל יחלק למחלקות.</p>
    <textarea id="mainInst" placeholder="תאר בפירוט..." style="min-height:100px"></textarea>
    <div style="margin-top:8px;display:flex;gap:7px;align-items:center">
      <button class="btn" id="bMI" onclick="sendMainInst()">🚀 שלח</button>
      <span id="lMI" style="display:none"><span class="sp"></span></span>
    </div>
    <div class="rb" id="rMI"><div class="rl">👑 תוכנית – דניאל כהן</div><div id="tMI" style="white-space:pre-wrap"></div></div>
  </div>
  <div class="card"><div class="ct">📜 היסטוריה</div><div id="instHist"><div style="color:var(--mt);font-size:12px">טוען...</div></div></div>
</div>

<div class="panel" id="panel-tasks">
  <div style="display:flex;gap:6px;margin-bottom:10px;flex-wrap:wrap;align-items:center">
    <button class="btn bsm" onclick="showNTF()">+ משימה</button>
    <button class="btn bsm bo" onclick="loadTasks()">↻</button>
    <select id="fs" style="width:auto;padding:5px 8px;font-size:11px" onchange="loadTasks()">
      <option value="">כל הסטטוסים</option><option value="pending">ממתין</option>
      <option value="in_progress">בעבודה</option><option value="done">הושלם</option>
    </select>
  </div>
  <div class="card" id="ntf" style="display:none">
    <div class="ct">+ משימה חדשה</div>
    <div class="fg"><label>כותרת</label><input type="text" id="tT" placeholder="כותרת..."></div>
    <div class="fr">
      <div class="fg"><label>מחלקה</label><select id="tD"></select></div>
      <div class="fg"><label>עדיפות</label><select id="tP"><option value="low">נמוך</option><option value="medium" selected>בינוני</option><option value="high">גבוה</option><option value="urgent">דחוף</option></select></div>
    </div>
    <div class="fg"><label>תיאור</label><textarea id="tDesc" style="min-height:55px" placeholder="פרט..."></textarea></div>
    <div style="display:flex;gap:6px"><button class="btn bsm bg" onclick="createTask()">✓ צור</button><button class="btn bsm bo" onclick="hideNTF()">ביטול</button></div>
  </div>
  <div id="tasksList"><div style="color:var(--mt);font-size:12px">טוען...</div></div>
</div>

<div class="panel" id="panel-employees">
  <div style="display:flex;gap:7px;margin-bottom:10px;align-items:center;flex-wrap:wrap">
    <select id="edf" style="width:auto;padding:5px 8px;font-size:11px" onchange="loadEmp()"><option value="">כל המחלקות</option></select>
    <span id="eCount" style="font-size:11px;color:var(--mt)"></span>
  </div>
  <div class="card" style="overflow-x:auto">
    <table class="etbl"><thead><tr><th>שם</th><th>תפקיד</th><th>מחלקה</th><th>סטטוס</th></tr></thead>
    <tbody id="eBody"><tr><td colspan="4" style="color:var(--mt);text-align:center;padding:16px">טוען...</td></tr></tbody></table>
  </div>
</div>

<div class="panel" id="panel-chat">
  <div class="chat-wrap">
    <div class="chat-side" id="chatSide"></div>
    <div class="chat-main">
      <div class="chat-hdr" id="chatHdr">💬 שיחה עם הצוות</div>
      <div class="chat-msgs" id="chatMsgs">
        <div class="msg ma"><div class="mn">דניאל כהן – מנכ&quot;ל</div>שלום! אני דניאל כהן. איך אוכל לעזור?</div>
      </div>
      <div class="chat-in">
        <button class="btn bsm" id="bChat" onclick="sendChat()">שלח</button>
        <textarea class="ci" id="ci" placeholder="כתוב... (Enter=שלח, Shift+Enter=שורה)"
          onkeydown="if(event.key==='Enter'&&!event.shiftKey){event.preventDefault();sendChat()}"></textarea>
      </div>
    </div>
  </div>
</div>

<div class="panel" id="panel-depts">
  <div class="dg" id="deptsGrid" style="margin-bottom:12px"></div>
  <div class="card" id="deptDet" style="display:none"><div class="ct" id="deptDetT"></div><div id="deptDetC"></div></div>
</div>

<div class="panel" id="panel-meetings">
  <div class="card">
    <div class="ct">📅 כינוס ישיבה</div>
    <div class="fg"><label>נושא</label><input type="text" id="mtT" placeholder="נושא..."></div>
    <div class="fg"><label>סדר יום</label><textarea id="mtA" placeholder="פרט..." style="min-height:55px"></textarea></div>
    <div class="fg">
      <label>מחלקות (עד 5)</label>
      <div style="display:flex;flex-wrap:wrap;gap:6px;margin-top:3px" id="mtD">
        <label style="display:flex;align-items:center;gap:3px;font-size:11px;color:var(--tx);cursor:pointer"><input type="checkbox" value="ceo" checked> 👑 דניאל</label>
        <label style="display:flex;align-items:center;gap:3px;font-size:11px;color:var(--tx);cursor:pointer"><input type="checkbox" value="cfo"> 💰 מיכאל</label>
        <label style="display:flex;align-items:center;gap:3px;font-size:11px;color:var(--tx);cursor:pointer"><input type="checkbox" value="marketing"> 📣 נועה</label>
        <label style="display:flex;align-items:center;gap:3px;font-size:11px;color:var(--tx);cursor:pointer"><input type="checkbox" value="sales"> 📈 רון</label>
        <label style="display:flex;align-items:center;gap:3px;font-size:11px;color:var(--tx);cursor:pointer"><input type="checkbox" value="legal"> ⚖️ תמר</label>
        <label style="display:flex;align-items:center;gap:3px;font-size:11px;color:var(--tx);cursor:pointer"><input type="checkbox" value="cto"> 💻 אלון</label>
        <label style="display:flex;align-items:center;gap:3px;font-size:11px;color:var(--tx);cursor:pointer"><input type="checkbox" value="content"> 🎨 שיר</label>
        <label style="display:flex;align-items:center;gap:3px;font-size:11px;color:var(--tx);cursor:pointer"><input type="checkbox" value="pr"> 📢 גיל</label>
        <label style="display:flex;align-items:center;gap:3px;font-size:11px;color:var(--tx);cursor:pointer"><input type="checkbox" value="compliance"> 🛡️ ענת</label>
        <label style="display:flex;align-items:center;gap:3px;font-size:11px;color:var(--tx);cursor:pointer"><input type="checkbox" value="hr"> 👥 יובל</label>
        <label style="display:flex;align-items:center;gap:3px;font-size:11px;color:var(--tx);cursor:pointer"><input type="checkbox" value="customer"> 🎧 ליאת</label>
      </div>
    </div>
    <button class="btn" id="bMt" onclick="createMeeting()">📅 כנס</button>
    <span id="lMt" style="display:none;margin-right:8px"><span class="sp"></span> ~30 שניות...</span>
    <div class="rb" id="rMt"></div>
  </div>
  <div class="card"><div class="ct">📜 ישיבות קודמות</div><div id="mtList"><div style="color:var(--mt);font-size:12px">טוען...</div></div></div>
</div>

<div class="panel" id="panel-social">
  <div class="card">
    <div class="ct">📱 פרסום לרשתות</div>
    <div class="fg"><label>פלטפורמות</label>
      <div style="display:flex;gap:6px;flex-wrap:wrap">
        <button class="pb" id="fb-b" onclick="togP('facebook',this)">📘 פייסבוק</button>
        <button class="pb" id="ig-b" onclick="togP('instagram',this)">📸 אינסטגרם</button>
        <button class="pb" id="tt-b" onclick="togP('tiktok',this)">🎵 טיקטוק</button>
        <button class="pb" id="wa-b" onclick="togP('whatsapp',this)">💬 וואטסאפ</button>
      </div>
    </div>
    <div id="waP" style="display:none" class="fg"><label>מספר וואטסאפ</label><input type="text" id="waNum" placeholder="972501234567"></div>
    <div style="display:flex;gap:6px;margin-bottom:9px;align-items:center">
      <button class="btn bsm bo" id="bGP" onclick="genPost()">✨ AI כותב</button>
      <input type="text" id="postTopic" placeholder="נושא הפוסט..." style="flex:1">
    </div>
    <div class="fg"><label>תוכן</label><textarea id="postTxt" style="min-height:100px" placeholder="תוכן הפוסט..."></textarea></div>
    <div class="fg"><label>קישור תמונה (נדרש לאינסטגרם)</label><input type="text" id="postImg" placeholder="https://..."></div>
    <div style="display:flex;gap:7px;align-items:center">
      <button class="btn" id="bPub" onclick="publishPost()">🚀 פרסם</button>
      <span id="lPub" style="display:none"><span class="sp"></span></span>
    </div>
    <div class="rb" id="rPub"></div>
  </div>
  <div class="card"><div class="ct">⚙ חיבור רשתות</div><div id="socialSt" style="font-size:11px;color:var(--mt)">טוען...</div>
    <div style="margin-top:10px;background:var(--sur);border:1px solid var(--bdr);border-radius:7px;padding:10px;font-size:10px;direction:ltr;text-align:left;color:var(--ac2)">META_PAGE_TOKEN=...<br>META_PAGE_ID=...<br>INSTAGRAM_ACCOUNT_ID=...<br>WHATSAPP_TOKEN=...<br>WHATSAPP_PHONE_ID=...</div>
  </div>
  <div class="card"><div class="ct">📜 פוסטים</div><div id="postsList"><div style="color:var(--mt);font-size:12px">טוען...</div></div></div>
</div>

<div class="panel" id="panel-cashflow">
  <div style="display:flex;gap:6px;margin-bottom:10px;flex-wrap:wrap">
    <button class="btn bsm" onclick="showCFF()">+ תנועה</button>
    <button class="btn bsm bo" onclick="loadCF()">↻</button>
    <button class="btn bsm" style="background:linear-gradient(135deg,#f59e0b,#d97706)" onclick="analyzeCF()">🤖 מיכאל מנתח</button>
  </div>
  <div class="cf-s">
    <div class="cfs"><div class="cfn cin" id="cfi">—</div><div class="cfl">הכנסות</div></div>
    <div class="cfs"><div class="cfn cout" id="cfo2">—</div><div class="cfl">הוצאות</div></div>
    <div class="cfs"><div class="cfn" id="cfb">—</div><div class="cfl">יתרה</div></div>
  </div>
  <div class="card" id="cff" style="display:none">
    <div class="ct">+ תנועה חדשה</div>
    <div class="fr">
      <div class="fg"><label>תאריך</label><input type="text" id="cfDate" placeholder="2025-01-15"></div>
      <div class="fg"><label>סוג</label><select id="cfType"><option value="income">הכנסה</option><option value="expense">הוצאה</option></select></div>
    </div>
    <div class="fr">
      <div class="fg"><label>סכום (₪)</label><input type="text" id="cfAmt" placeholder="1000"></div>
      <div class="fg"><label>קטגוריה</label><select id="cfCat"><option>שיווק</option><option>שכר</option><option>פרסום</option><option>ציוד</option><option>לקוח</option><option>השקעה</option><option>כללי</option></select></div>
    </div>
    <div class="fg"><label>תיאור</label><input type="text" id="cfDesc" placeholder="תיאור..."></div>
    <div class="fg"><label>מזהה לקוח</label><input type="text" id="cfCli" placeholder="אופציונלי..."></div>
    <div style="display:flex;gap:6px"><button class="btn bsm bg" onclick="addCF()">✓ הוסף</button><button class="btn bsm bo" onclick="hideCFF()">ביטול</button></div>
  </div>
  <div class="card">
    <div class="rb" id="cfAnal"></div>
    <div style="overflow-x:auto"><table class="cft"><thead><tr><th>תאריך</th><th>תיאור</th><th>קטגוריה</th><th>סוג</th><th>סכום</th></tr></thead>
    <tbody id="cfBody"><tr><td colspan="5" style="color:var(--mt);text-align:center;padding:12px">אין נתונים</td></tr></tbody></table></div>
  </div>
</div>

<div class="panel" id="panel-reports">
  <div class="card">
    <div class="ct">📊 הפק דוח</div>
    <div class="fr">
      <div class="fg"><label>מחלקה</label><select id="rD"></select></div>
      <div class="fg"><label>סוג</label><select id="rT"><option value="weekly">שבועי</option><option value="monthly">חודשי</option><option value="quarterly">רבעוני</option><option value="summary">סיכום</option></select></div>
    </div>
    <button class="btn" id="bRep" onclick="genRep()">📊 הפק</button>
    <span id="lRep" style="display:none;margin-right:8px"><span class="sp"></span></span>
    <div class="rb" id="rRep"><div class="rl" id="rRepL">דוח</div><div id="rRepT" style="white-space:pre-wrap"></div></div>
  </div>
  <div class="card"><div class="ct">📁 דוחות קודמים</div><div id="repList"><div style="color:var(--mt);font-size:12px">טוען...</div></div></div>
</div>

<div class="panel" id="panel-strategy">
  <div class="card">
    <div class="ct">🎯 יעדים אסטרטגיים</div>
    <p style="font-size:11px;color:var(--mt);margin-bottom:9px">המנכ&quot;ל יבנה תוכנית עם KPIs ולו&quot;ז.</p>
    <textarea id="stratG" placeholder="לדוגמה: עד סוף הרבעון 100 לקוחות..." style="min-height:90px"></textarea>
    <div style="margin-top:8px;display:flex;gap:6px;align-items:center">
      <button class="btn" id="bGoals" onclick="setGoals()">🎯 שלח</button>
      <span id="lGoals" style="display:none"><span class="sp"></span></span>
    </div>
    <div class="rb" id="rGoals"><div class="rl">📋 תוכנית – דניאל כהן</div><div id="tGoals" style="white-space:pre-wrap"></div></div>
  </div>
  <div class="card"><div class="ct">📌 יעדים קודמים</div><div id="goalsList"><div style="color:var(--mt);font-size:12px">טוען...</div></div></div>
</div>

<div class="panel" id="panel-approvals">
  <div class="card"><div class="ct">👁 ממתינים לאישורך</div><div id="apprList"><div style="color:var(--mt);font-size:12px">טוען...</div></div></div>
</div>

<div class="panel" id="panel-settings">
  <div class="card"><div class="ct">⚙ חיבורי מערכת</div><div id="connSt"></div></div>
  <div class="card">
    <div class="ct">🗄 SQL – Supabase</div>
    <p style="font-size:10px;color:var(--mt);margin-bottom:7px">הרץ ב-SQL Editor:</p>
    <pre style="background:var(--sur);border:1px solid var(--bdr);border-radius:7px;padding:9px;font-size:9px;overflow-x:auto;color:var(--ac2);white-space:pre;direction:ltr;text-align:left">CREATE TABLE IF NOT EXISTS tasks(id uuid DEFAULT gen_random_uuid() PRIMARY KEY,title text,description text,department text,status text DEFAULT 'pending',priority text DEFAULT 'medium',created_by text,created_at timestamptz DEFAULT now(),approved_at timestamptz);
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
// ══════════════════════════════════════════════
// AUTH – קרא token מה-hash או sessionStorage
// ══════════════════════════════════════════════
var AUTH = '';
(function(){
  var h = location.hash;
  if(h && h.length > 1){
    AUTH = h.substring(1);
    try{ sessionStorage.setItem('jauth', AUTH); }catch(e){}
    history.replaceState(null, null, location.pathname);
  } else {
    try{ AUTH = sessionStorage.getItem('jauth') || ''; }catch(e){}
  }
})();

function getHeaders(){
  return {'Content-Type':'application/json','Authorization': AUTH ? 'Basic '+AUTH : ''};
}

function logout(){
  try{ sessionStorage.removeItem('jauth'); }catch(e){}
  AUTH = '';
  window.location.replace('/');
}

// ══════════════════════════════════════════════
// API
// ══════════════════════════════════════════════
async function api(method, path, body){
  var opts = {method: method, headers: getHeaders()};
  if(body) opts.body = JSON.stringify(body);
  try{
    var r = await fetch('/api' + path, opts);
    if(r.status === 401){ logout(); return null; }
    if(!r.ok){ throw new Error(await r.text()); }
    return await r.json();
  } catch(e){
    console.error('API', method, path, e.message);
    throw e;
  }
}

function fd(d){
  if(!d) return '';
  try{ return new Date(d).toLocaleDateString('he-IL',{day:'2-digit',month:'2-digit',year:'2-digit',hour:'2-digit',minute:'2-digit'}); }
  catch(e){ return d; }
}
function fmtN(n){ return Number(n||0).toLocaleString('he-IL'); }
function busy(b,l,on){
  var be=document.getElementById(b), le=document.getElementById(l);
  if(be) be.disabled=on;
  if(le) le.style.display=on?'inline-flex':'none';
}

// ══════════════════════════════════════════════
// TABS
// ══════════════════════════════════════════════
var tabLoaders = {
  home: initHome, instruct: function(){ loadInstHist(); },
  tasks: loadTasks, employees: loadEmp, chat: buildChatSide,
  depts: loadDepts, meetings: loadMeetings, social: initSocial,
  cashflow: loadCF, reports: initReports, strategy: loadGoals,
  approvals: loadApprls, settings: checkConn
};
function T(name, btn){
  document.querySelectorAll('.panel').forEach(function(p){ p.classList.remove('active'); });
  document.querySelectorAll('.tb').forEach(function(b){ b.classList.remove('active'); });
  var panel = document.getElementById('panel-'+name);
  if(panel) panel.classList.add('active');
  if(btn) btn.classList.add('active');
  if(tabLoaders[name]) tabLoaders[name]();
}

// ══════════════════════════════════════════════
// DEPT CACHE
// ══════════════════════════════════════════════
var DEPTS = [];
async function getDepts(){
  if(!DEPTS.length){ var d = await api('GET','/departments'); DEPTS = d || []; }
  return DEPTS;
}

// ══════════════════════════════════════════════
// STATS
// ══════════════════════════════════════════════
async function loadStats(){
  try{
    var s = await api('GET','/stats'); if(!s) return;
    document.getElementById('sd').textContent = s.departments || '—';
    document.getElementById('se').textContent = s.employees || '—';
    document.getElementById('st').textContent = s.tasks_total || '0';
    document.getElementById('sdn').textContent = s.tasks_done || '0';
    document.getElementById('sip').textContent = s.tasks_inprog || '0';
    document.getElementById('spa').textContent = s.tasks_pending || '0';
  }catch(e){}
}

// ══════════════════════════════════════════════
// HOME
// ══════════════════════════════════════════════
async function initHome(){
  loadStats();
  var depts = await getDepts();
  var g = document.getElementById('homeDepts');
  if(g) g.innerHTML = depts.map(function(d){
    return '<div class="dc" style="border-top:3px solid '+d.color+'" onclick="T(\'chat\',null);selAgent(\''+d.id+'\',\''+d.name+'\',\''+d.head+'\',\''+d.title+'\')">'
      +'<div class="di">'+d.icon+'</div><div class="dn">'+d.name+'</div>'
      +'<div class="dh">'+d.head+'</div><div class="dt">'+d.title+'</div></div>';
  }).join('');
  try{
    var a = await api('GET','/approvals'); if(!a) return;
    var el = document.getElementById('homeAppr');
    if(el) el.innerHTML = a.length ? a.slice(0,3).map(tHTML).join('') : '<div style="color:var(--mt);font-size:12px">אין תוצרים</div>';
  }catch(e){}
}

// ══════════════════════════════════════════════
// INSTRUCT
// ══════════════════════════════════════════════
async function sendInst(){
  var t = document.getElementById('homeInst').value.trim();
  if(!t){ alert('נא לכתוב הוראה'); return; }
  busy('bHI','lHI',true);
  try{
    var r = await api('POST','/instruct',{instruction:t}); if(!r) return;
    document.getElementById('rHI').classList.add('show');
    document.getElementById('tHI').textContent = r.ceo_response;
  }catch(e){ alert('שגיאה: '+e.message); }
  busy('bHI','lHI',false);
}
async function sendMainInst(){
  var t = document.getElementById('mainInst').value.trim();
  if(!t){ alert('נא לכתוב הוראה'); return; }
  busy('bMI','lMI',true);
  try{
    var r = await api('POST','/instruct',{instruction:t}); if(!r) return;
    document.getElementById('rMI').classList.add('show');
    document.getElementById('tMI').textContent = r.ceo_response;
    loadInstHist();
  }catch(e){ alert('שגיאה: '+e.message); }
  busy('bMI','lMI',false);
}
async function loadInstHist(){
  try{
    var items = await api('GET','/instructions'); if(!items) return;
    var el = document.getElementById('instHist'); if(!el) return;
    if(!items.length){ el.innerHTML='<div style="color:var(--mt);font-size:12px">אין היסטוריה</div>'; return; }
    el.innerHTML = items.map(function(i){
      return '<div class="ti"><div class="tdot di2"></div><div class="ti-i">'
        +'<div class="ti-t">'+i.text+'</div><div class="ti-m">'+fd(i.created_at)+'</div>'
        +(i.ceo_response?'<div style="font-size:10px;color:var(--mt);margin-top:4px;max-height:60px;overflow:hidden">'+i.ceo_response.substring(0,200)+'...</div>':'')
        +'</div></div>';
    }).join('');
  }catch(e){}
}

// ══════════════════════════════════════════════
// TASKS
// ══════════════════════════════════════════════
var PMAP={pending:'dp',in_progress:'di2',done:'dd',pending_approval:'da'};
var TMAP={pending:'to',in_progress:'tag',done:'tg',pending_approval:'ty'};
var LMAP={pending:'ממתין',in_progress:'בעבודה',done:'הושלם',pending_approval:'לאישור'};
function tHTML(t){
  return '<div class="ti"><div class="tdot '+(PMAP[t.status]||'dp')+'"></div>'
    +'<div class="ti-i"><div class="ti-t">'+(t.title||'')+'</div>'
    +'<div class="ti-m">'+(t.department||'')+' • '+fd(t.created_at)+'</div></div>'
    +'<span class="tag '+(TMAP[t.status]||'')+'">'+(LMAP[t.status]||t.status)+'</span>'
    +(t.status==='pending_approval'?'<button class="btn bsm bg" onclick="approveT(\''+t.id+'\')">✓</button>':'')
    +'</div>';
}
async function loadTasks(){
  var st = document.getElementById('fs') ? document.getElementById('fs').value : '';
  try{
    var items = await api('GET','/tasks'+(st?'?status='+st:'')); if(!items) return;
    var el = document.getElementById('tasksList'); if(!el) return;
    el.innerHTML = items.length ? '<div class="card">'+items.map(tHTML).join('')+'</div>'
      : '<div class="card"><div style="color:var(--mt);font-size:12px">אין משימות</div></div>';
    var df = document.getElementById('tD');
    if(df && !df.options.length){ var depts=await getDepts(); depts.forEach(function(d){ var o=document.createElement('option');o.value=d.id;o.textContent=d.name;df.appendChild(o); }); }
  }catch(e){}
}
async function createTask(){
  var title = document.getElementById('tT').value.trim();
  if(!title){ alert('נא להזין כותרת'); return; }
  try{
    await api('POST','/tasks',{title:title,description:document.getElementById('tDesc').value,
      department:document.getElementById('tD').value,priority:document.getElementById('tP').value});
    hideNTF(); loadTasks();
  }catch(e){ alert('שגיאה: '+e.message); }
}
async function approveT(id){
  try{ await api('POST','/tasks/'+id+'/approve'); loadTasks(); }catch(e){}
}
async function showNTF(){
  document.getElementById('ntf').style.display='block';
  var d=document.getElementById('tD');
  if(d&&!d.options.length){ var depts=await getDepts(); depts.forEach(function(dep){ var o=document.createElement('option');o.value=dep.id;o.textContent=dep.name;d.appendChild(o); }); }
}
function hideNTF(){ document.getElementById('ntf').style.display='none'; }

// ══════════════════════════════════════════════
// EMPLOYEES
// ══════════════════════════════════════════════
async function loadEmp(){
  var dept = document.getElementById('edf') ? document.getElementById('edf').value : '';
  try{
    var items = await api('GET','/employees'+(dept?'?dept='+dept:'')); if(!items) return;
    var cnt = document.getElementById('eCount');
    if(cnt) cnt.textContent = 'סה"כ: '+items.length+' עובדים';
    var body = document.getElementById('eBody'); if(!body) return;
    var depts = await getDepts();
    var dm = {};
    depts.forEach(function(d){ dm[d.id]=d; });
    body.innerHTML = items.map(function(e){
      var d = dm[e.department]||{};
      var ini = (e.name||'AI').split(' ').map(function(w){ return w[0]; }).join('').substring(0,2);
      return '<tr><td style="display:flex;align-items:center"><div class="av">'+ini+'</div>'+e.name+'</td>'
        +'<td>'+e.role+'</td><td>'+(d.icon||'')+' '+(d.name||e.department)+'</td>'
        +'<td><span class="tag tg">פעיל</span></td></tr>';
    }).join('');
    var df = document.getElementById('edf');
    if(df && df.options.length<=1){ depts.forEach(function(d){ var o=document.createElement('option');o.value=d.id;o.textContent=d.icon+' '+d.name;df.appendChild(o); }); }
  }catch(e){}
}

// ══════════════════════════════════════════════
// CHAT
// ══════════════════════════════════════════════
var cAgent='ceo', cHist=[], cName='דניאל כהן', cTitle='מנכ"ל';
async function buildChatSide(){
  var depts = await getDepts();
  var sb = document.getElementById('chatSide'); if(!sb) return;
  sb.innerHTML = depts.map(function(d,i){
    return '<button class="ca'+(i===0?' active':'')+'" onclick="selAgent(\''+d.id+'\',\''+d.name+'\',\''+d.head+'\',\''+d.title+'\',this)">'
      +'<span class="ca-n">'+d.icon+' '+d.head+'</span><span class="ca-r">'+d.title+'</span></button>';
  }).join('');
}
function selAgent(id,dname,head,title,btn){
  cAgent=id; cName=head; cTitle=title; cHist=[];
  document.querySelectorAll('.ca').forEach(function(b){ b.classList.remove('active'); });
  if(btn) btn.classList.add('active');
  var hdr = document.getElementById('chatHdr');
  if(hdr) hdr.textContent = '💬 '+head+' – '+title;
  var msgs = document.getElementById('chatMsgs');
  if(msgs) msgs.innerHTML = '<div class="msg ma"><div class="mn">'+head+' – '+title+'</div>שלום! אני '+head+'. איך אוכל לעזור?</div>';
}
async function sendChat(){
  var inp = document.getElementById('ci');
  var msg = inp.value.trim(); if(!msg) return;
  inp.value = '';
  var msgs = document.getElementById('chatMsgs');
  msgs.innerHTML += '<div class="msg mu">'+msg.replace(/\n/g,'<br>')+'</div>';
  msgs.innerHTML += '<div class="msg ma" id="typing"><div class="mn">'+cName+'</div><span class="sp"></span></div>';
  msgs.scrollTop = msgs.scrollHeight;
  cHist.push({role:'user',content:msg});
  document.getElementById('bChat').disabled = true;
  try{
    var r = await api('POST','/chat/'+cAgent,{message:msg,history:cHist}); if(!r) return;
    var t = document.getElementById('typing'); if(t) t.remove();
    msgs.innerHTML += '<div class="msg ma"><div class="mn">'+(r.agent||cName)+' – '+(r.title||cTitle)+'</div>'+r.response.replace(/\n/g,'<br>')+'</div>';
    cHist.push({role:'assistant',content:r.response});
    msgs.scrollTop = msgs.scrollHeight;
  }catch(e){
    var t = document.getElementById('typing');
    if(t) t.innerHTML = '<div class="mn">שגיאה</div>'+e.message;
  }
  document.getElementById('bChat').disabled = false;
}

// ══════════════════════════════════════════════
// DEPARTMENTS
// ══════════════════════════════════════════════
async function loadDepts(){
  var depts = await getDepts();
  var g = document.getElementById('deptsGrid'); if(!g) return;
  g.innerHTML = depts.map(function(d){
    return '<div class="dc" style="border-top:3px solid '+d.color+'" onclick="showDeptDet(\''+d.id+'\',\''+d.name+'\',\''+d.icon+'\')">'
      +'<div class="di">'+d.icon+'</div><div class="dn">'+d.name+'</div>'
      +'<div class="dh">'+d.head+'</div><div class="dt">'+d.title+'</div></div>';
  }).join('');
}
async function showDeptDet(id,name,icon){
  document.getElementById('deptDet').style.display='block';
  document.getElementById('deptDetT').textContent=icon+' '+name;
  document.getElementById('deptDetC').innerHTML='<div style="color:var(--mt)">טוען...</div>';
  try{
    var emps = await api('GET','/employees?dept='+id);
    var tasks = await api('GET','/tasks?dept='+id);
    document.getElementById('deptDetC').innerHTML =
      '<div style="display:grid;grid-template-columns:1fr 1fr;gap:12px">'
      +'<div><div style="font-size:10px;color:var(--mt);margin-bottom:6px">צוות ('+emps.length+')</div>'
      +emps.map(function(e){ return '<div class="ti"><div class="tdot '+(e.title==="מנהל"?'da':'dd')+'"></div><div class="ti-i"><div class="ti-t">'+e.name+'</div><div class="ti-m">'+e.role+'</div></div>'+(e.title==="מנהל"?'<span class="tag ty">מנהל</span>':'')+'</div>'; }).join('')+'</div>'
      +'<div><div style="font-size:10px;color:var(--mt);margin-bottom:6px">משימות ('+tasks.length+')</div>'
      +(tasks.slice(0,5).map(tHTML).join('')||'<div style="color:var(--mt);font-size:11px">אין משימות</div>')+'</div></div>';
  }catch(e){}
}

// ══════════════════════════════════════════════
// MEETINGS
// ══════════════════════════════════════════════
async function createMeeting(){
  var topic = document.getElementById('mtT').value.trim();
  if(!topic){ alert('נא להזין נושא'); return; }
  var depts = Array.from(document.querySelectorAll('#mtD input:checked')).map(function(i){ return i.value; });
  if(!depts.length){ alert('נא לבחור מחלקה'); return; }
  busy('bMt','lMt',true);
  try{
    var r = await api('POST','/meetings',{topic:topic,agenda:document.getElementById('mtA').value,departments:depts}); if(!r) return;
    var box = document.getElementById('rMt'); box.classList.add('show');
    var dm = {}; (await getDepts()).forEach(function(d){ dm[d.id]=d; });
    var html = '<div class="rl">📅 '+topic+'</div>';
    Object.entries(r.responses||{}).forEach(function(kv){
      var info = dm[kv[0]]||{};
      html += '<div class="dr"><div class="drn">'+(info.icon||'')+' '+(info.head||kv[0])+'</div>'+kv[1]+'</div>';
    });
    box.innerHTML = html;
    loadMeetings();
  }catch(e){ alert('שגיאה: '+e.message); }
  busy('bMt','lMt',false);
}
async function loadMeetings(){
  try{
    var items = await api('GET','/meetings'); if(!items) return;
    var el = document.getElementById('mtList'); if(!el) return;
    if(!items.length){ el.innerHTML='<div style="color:var(--mt);font-size:12px">אין ישיבות</div>'; return; }
    var dm = {}; (await getDepts()).forEach(function(d){ dm[d.id]=d; });
    el.innerHTML = items.map(function(m){
      var rs='';
      try{
        var obj = typeof m.responses==='string'?JSON.parse(m.responses):m.responses;
        Object.entries(obj||{}).forEach(function(kv){
          var info=dm[kv[0]]||{};
          rs += '<div class="dr"><div class="drn">'+(info.icon||'')+' '+(info.head||kv[0])+'</div>'+kv[1].substring(0,200)+'...</div>';
        });
      }catch(e){}
      return '<div class="card" style="margin-bottom:8px"><div style="font-weight:700;margin-bottom:4px">'+(m.topic||'')+'</div>'
        +'<div style="font-size:10px;color:var(--mt)">'+fd(m.created_at)+'</div>'
        +(rs?'<div style="margin-top:8px">'+rs+'</div>':'')+'</div>';
    }).join('');
  }catch(e){}
}

// ══════════════════════════════════════════════
// SOCIAL
// ══════════════════════════════════════════════
var selP = {};
function togP(p,btn){
  if(selP[p]){ delete selP[p]; btn.classList.remove('sel'); }
  else{ selP[p]=true; btn.classList.add('sel'); }
  document.getElementById('waP').style.display = selP['whatsapp']?'block':'none';
}
async function genPost(){
  var t = document.getElementById('postTopic').value.trim();
  if(!t){ alert('נא להזין נושא'); return; }
  var b = document.getElementById('bGP'); b.disabled=true; b.textContent='...';
  try{
    var r = await api('POST','/social/generate',{topic:t});
    if(r) document.getElementById('postTxt').value = r.post;
  }catch(e){ alert('שגיאה: '+e.message); }
  b.disabled=false; b.textContent='✨ AI כותב';
}
async function publishPost(){
  var txt = document.getElementById('postTxt').value.trim();
  if(!txt){ alert('נא לכתוב תוכן'); return; }
  if(!Object.keys(selP).length){ alert('נא לבחור פלטפורמה'); return; }
  busy('bPub','lPub',true);
  try{
    var r = await api('POST','/social/publish',{text:txt,image_url:document.getElementById('postImg').value,platforms:Object.keys(selP),whatsapp_phone:document.getElementById('waNum')?document.getElementById('waNum').value:''});
    if(!r) return;
    var box = document.getElementById('rPub'); box.classList.add('show');
    var html = '<div class="rl">תוצאות פרסום</div>';
    Object.entries(r.results||{}).forEach(function(kv){
      var res=kv[1];
      html += '<div style="padding:6px;margin-bottom:4px;background:rgba('+(res.ok?'34,211,160':'248,113,113')+',.07);border-radius:5px;border:1px solid rgba('+(res.ok?'34,211,160':'248,113,113')+',.2);font-size:11px">'
        +(res.ok?'✅':'❌')+' <strong>'+kv[0]+'</strong>: '+(res.ok?'פורסם'+(res.post_id?' – '+res.post_id:''):res.error||'שגיאה')+'</div>';
    });
    box.innerHTML = html; loadPosts();
  }catch(e){ alert('שגיאה: '+e.message); }
  busy('bPub','lPub',false);
}
async function loadPosts(){
  try{
    var items = await api('GET','/social/posts'); if(!items) return;
    var el = document.getElementById('postsList'); if(!el) return;
    if(!items.length){ el.innerHTML='<div style="color:var(--mt);font-size:12px">אין פוסטים</div>'; return; }
    el.innerHTML = items.map(function(p){
      var plats = typeof p.platforms==='string'?JSON.parse(p.platforms):p.platforms||[];
      return '<div class="ti"><div class="tdot '+(p.status==='published'?'dd':'dp')+'"></div>'
        +'<div class="ti-i"><div class="ti-t">'+(p.text||'').substring(0,70)+'...</div>'
        +'<div class="ti-m">'+plats.join(', ')+' • '+fd(p.created_at)+'</div></div>'
        +'<span class="tag '+(p.status==='published'?'tg':'to')+'">'+(p.status==='published'?'פורסם':'ממתין')+'</span></div>';
    }).join('');
  }catch(e){}
}
async function initSocial(){
  loadPosts();
  try{
    var h = await api('GET','/health'); if(!h) return;
    var el = document.getElementById('socialSt'); if(!el) return;
    var items = [['📘 פייסבוק',h.facebook,'META_PAGE_TOKEN'],['📸 אינסטגרם',h.instagram,'INSTAGRAM_ACCOUNT_ID'],['🎵 טיקטוק',h.tiktok,'TIKTOK_ACCESS_TOKEN'],['💬 וואטסאפ',h.whatsapp,'WHATSAPP_TOKEN']];
    el.innerHTML = items.map(function(x){
      return '<div style="display:flex;justify-content:space-between;margin-bottom:4px;font-size:11px"><span>'+x[0]+'</span><span style="color:'+(x[1]?'var(--grn)':'var(--red)')+'">'+(x[1]?'✅ מחובר':'❌ חסר '+x[2])+'</span></div>';
    }).join('');
  }catch(e){}
}

// ══════════════════════════════════════════════
// CASHFLOW
// ══════════════════════════════════════════════
async function loadCF(){
  try{
    var items = await api('GET','/cashflow'); if(!items) return;
    var body = document.getElementById('cfBody'); if(!body) return;
    if(!items.length){ body.innerHTML='<tr><td colspan="5" style="color:var(--mt);text-align:center;padding:10px">אין נתונים</td></tr>'; return; }
    var ti=0,to=0;
    body.innerHTML = items.map(function(r){
      var inc=r.type==='income'; if(inc)ti+=Number(r.amount||0); else to+=Number(r.amount||0);
      return '<tr><td>'+r.date+'</td><td>'+r.description+'</td><td>'+r.category+'</td>'
        +'<td><span class="tag '+(inc?'tg':'to')+'">'+(inc?'הכנסה':'הוצאה')+'</span></td>'
        +'<td class="'+(inc?'cin':'cout')+'">'+(inc?'+':'-')+fmtN(r.amount)+' ₪</td></tr>';
    }).join('');
    document.getElementById('cfi').textContent = fmtN(ti)+' ₪';
    document.getElementById('cfo2').textContent = fmtN(to)+' ₪';
    var bal=ti-to; var be=document.getElementById('cfb');
    be.textContent=fmtN(bal)+' ₪'; be.className='cfn '+(bal>=0?'cin':'cout');
  }catch(e){}
}
async function addCF(){
  var amt = parseFloat(document.getElementById('cfAmt').value);
  if(!amt||isNaN(amt)){ alert('נא להזין סכום'); return; }
  try{
    await api('POST','/cashflow',{
      date:document.getElementById('cfDate').value||new Date().toISOString().split('T')[0],
      description:document.getElementById('cfDesc').value,amount:amt,
      type:document.getElementById('cfType').value,category:document.getElementById('cfCat').value,
      client_id:document.getElementById('cfCli').value});
    hideCFF(); loadCF();
  }catch(e){ alert('שגיאה: '+e.message); }
}
async function analyzeCF(){
  var el=document.getElementById('cfAnal'); el.classList.add('show');
  el.innerHTML='<span class="sp"></span> מיכאל לוי מנתח...';
  try{
    var r=await api('POST','/cashflow/analyze');
    el.innerHTML='<div class="rl">💰 ניתוח – מיכאל לוי CFO</div>'+r.analysis.replace(/\n/g,'<br>');
  }catch(e){ el.innerHTML='שגיאה: '+e.message; }
}
function showCFF(){ document.getElementById('cff').style.display='block'; }
function hideCFF(){ document.getElementById('cff').style.display='none'; }

// ══════════════════════════════════════════════
// REPORTS
// ══════════════════════════════════════════════
async function initReports(){
  loadRepList();
  var d=document.getElementById('rD');
  if(d&&!d.options.length){ var depts=await getDepts(); depts.forEach(function(dep){ var o=document.createElement('option');o.value=dep.id;o.textContent=dep.name;d.appendChild(o); }); }
}
async function genRep(){
  busy('bRep','lRep',true);
  try{
    var r=await api('POST','/reports/generate',{department:document.getElementById('rD').value,type:document.getElementById('rT').value}); if(!r) return;
    document.getElementById('rRep').classList.add('show');
    document.getElementById('rRepL').textContent=r.report.title;
    document.getElementById('rRepT').textContent=r.report.content;
    loadRepList();
  }catch(e){ alert('שגיאה: '+e.message); }
  busy('bRep','lRep',false);
}
async function loadRepList(){
  try{
    var items=await api('GET','/reports'); if(!items) return;
    var el=document.getElementById('repList'); if(!el) return;
    if(!items.length){ el.innerHTML='<div style="color:var(--mt);font-size:12px">אין דוחות</div>'; return; }
    el.innerHTML=items.map(function(r){ return '<div class="ti"><div class="tdot dd"></div><div class="ti-i"><div class="ti-t">'+r.title+'</div><div class="ti-m">'+r.type+' • '+fd(r.created_at)+'</div></div></div>'; }).join('');
  }catch(e){}
}

// ══════════════════════════════════════════════
// STRATEGY
// ══════════════════════════════════════════════
async function setGoals(){
  var g=document.getElementById('stratG').value.trim();
  if(!g){ alert('נא להזין יעדים'); return; }
  busy('bGoals','lGoals',true);
  try{
    var r=await api('POST','/strategy/goals',{goals:g}); if(!r) return;
    document.getElementById('rGoals').classList.add('show');
    document.getElementById('tGoals').textContent=r.plan;
    loadGoals();
  }catch(e){ alert('שגיאה: '+e.message); }
  busy('bGoals','lGoals',false);
}
async function loadGoals(){
  try{
    var items=await api('GET','/strategy/goals'); if(!items) return;
    var el=document.getElementById('goalsList'); if(!el) return;
    if(!items.length){ el.innerHTML='<div style="color:var(--mt);font-size:12px">אין יעדים</div>'; return; }
    el.innerHTML=items.map(function(g){ return '<div class="card" style="margin-bottom:7px"><div style="font-size:12px;font-weight:600">'+g.goals+'</div>'+(g.plan?'<div style="font-size:10px;color:var(--mt);margin-top:6px;white-space:pre-wrap;max-height:140px;overflow:hidden">'+g.plan.substring(0,400)+'...</div>':'')+'<div style="font-size:10px;color:var(--mt);margin-top:5px">'+fd(g.created_at)+'</div></div>'; }).join('');
  }catch(e){}
}

// ══════════════════════════════════════════════
// APPROVALS
// ══════════════════════════════════════════════
async function loadApprls(){
  try{
    var items=await api('GET','/approvals'); if(!items) return;
    var el=document.getElementById('apprList'); if(!el) return;
    el.innerHTML=items.length?items.map(tHTML).join(''):'<div style="color:var(--mt);font-size:12px">אין תוצרים</div>';
  }catch(e){}
}

// ══════════════════════════════════════════════
// SETTINGS
// ══════════════════════════════════════════════
async function checkConn(){
  try{
    var h=await api('GET','/health'); if(!h) return;
    var el=document.getElementById('connSt'); if(!el) return;
    var rows=[['🤖 Claude AI',h.anthropic],['🗄 Supabase',h.supabase],['📘 פייסבוק',h.facebook],['📸 אינסטגרם',h.instagram],['💬 וואטסאפ',h.whatsapp]];
    el.innerHTML=rows.map(function(x){ return '<div class="conn-r"><span>'+x[0]+'</span><span style="color:'+(x[1]?'var(--grn)':'var(--red)')+'">'+(x[1]?'✅ מחובר':'❌ לא מוגדר')+'</span></div>'; }).join('');
  }catch(e){}
}

// ══════════════════════════════════════════════
// INIT
// ══════════════════════════════════════════════
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
