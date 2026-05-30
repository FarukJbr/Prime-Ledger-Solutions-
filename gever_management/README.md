# גבר יזמות ייעוץ עסקי והשקעות
## Jabr Entrepreneurship Business Consulting and Investments
### AI Company Management System

---

## מבנה הפרויקט

```
gever_management/
├── main.py              # נקודת כניסה
├── config.py            # הגדרות
├── api.py               # Dashboard (FastAPI)
├── requirements.txt     # תלויות Python
├── .env.example         # תבנית משתני סביבה
│
├── agents/              # סוכני AI לכל מחלקה
│   ├── base_agent.py    # מחלקת בסיס
│   ├── ceo.py           # מנכ"ל (Orchestrator)
│   ├── cfo.py           # מנהל כספים
│   ├── marketing.py     # מנהל שיווק
│   ├── sales.py         # מנהל מכירות
│   ├── legal.py         # יועץ משפטי
│   ├── cto.py           # מנהל טכנולוגיה
│   ├── content.py       # מנהל תוכן ועיצוב
│   ├── pr.py            # מנהל יח"צ
│   └── compliance.py    # קצין ציות
│
├── database/
│   ├── schema.sql       # הרץ ב-Supabase SQL Editor
│   └── supabase_client.py
│
├── meetings/
│   └── meeting_room.py  # ניהול ישיבות הנהלה
│
├── board/
│   └── board_room.py    # ישיבות דירקטוריון + הצבעות
│
├── tasks/
│   └── task_manager.py  # מנוע ניהול משימות
│
└── channels/
    ├── telegram_bot.py  # בוט טלגרם (ממשק ראשי)
    └── publisher.py     # פרסום לסושיאל מדיה
```

---

## התקנה

### 1. הכנת הסביבה

```bash
cd gever_management
pip install -r requirements.txt
cp .env.example .env
# ערוך את .env עם הפרטים שלך
```

### 2. הגדרת Supabase

1. היכנס ל-[supabase.com](https://supabase.com)
2. צור פרויקט חדש
3. לך ל-**SQL Editor**
4. הרץ את כל הקוד מ-`database/schema.sql`
5. העתק את ה-URLs וה-Keys ל-`.env`

### 3. הגדרת Telegram Bot

1. חפש `@BotFather` בטלגרם
2. שלח `/newbot`
3. שם: `Gever Management`
4. Username: `GeverManagementBot`
5. העתק את ה-TOKEN ל-`.env`
6. מצא את ה-Chat ID שלך עם `@userinfobot`

### 4. הפעלה

```bash
# רק Telegram Bot
python main.py bot

# רק Dashboard (http://localhost:8000)
python main.py api

# שניהם ביחד
python main.py both
```

---

## איך להשתמש

### דרך טלגרם (מומלץ)
```
/start     - התחל
/task      - שלח משימה חדשה
/review    - ראה תוצרים לאישור
/meeting   - כנס ישיבת הנהלה
/consult   - ייעוץ מהיר
/status    - מצב משימות
```

**או פשוט כתוב הוראה:**
> "צור קמפיין שיווקי לרגל חג הפסח עם פוסטים לפייסבוק, אינסטגרם וטיקטוק"

### דרך Dashboard
פתח: `http://localhost:8000`

---

## מבנה ארגוני

| תפקיד | מחלקה | תיאור |
|-------|-------|-------|
| יו"ר | chairman | אתה - מאשר ומכוון |
| מנכ"ל | ceo | מתאם ומחלק משימות |
| מנהל כספים | cfo | ניתוח פיננסי |
| מנהל שיווק | marketing | קמפיינים ואסטרטגיה |
| מנהל מכירות | sales | מכירות ולקוחות |
| יועץ משפטי | legal | ייעוץ משפטי |
| מנהל טכנולוגיה | cto | פתרונות טכנולוגיים |
| מנהל תוכן | content | יצירת תוכן |
| מנהל יח"צ | pr | יחסי ציבור |
| קצין ציות | compliance | רגולציה וציות |

---

## הוספת פרסום סושיאל

### Meta (Facebook + Instagram)
1. היכנס ל-[developers.facebook.com](https://developers.facebook.com)
2. צור App
3. הוסף Facebook Login + Pages API
4. קבל Page Access Token
5. הכנס ל-`.env`

### TikTok
1. היכנס ל-[developers.tiktok.com](https://developers.tiktok.com)
2. צור App
3. הפעל Content Posting API
4. קבל Access Token
5. הכנס ל-`.env`
