import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application, CommandHandler, MessageHandler,
    CallbackQueryHandler, ContextTypes, filters
)
from config import settings
from database import db
from tasks import TaskManager
from meetings import MeetingRoom
from channels.publisher import SocialPublisher

logger = logging.getLogger(__name__)

task_manager = TaskManager()
meeting_room = MeetingRoom()
publisher = SocialPublisher()


def chairman_only(func):
    """Decorator: only allow the Chairman to use the bot."""
    async def wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE):
        if update.effective_user.id != settings.telegram_chairman_chat_id:
            await update.message.reply_text("⛔ גישה מורשית ליו\"ר בלבד.")
            return
        return await func(update, context)
    return wrapper


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Welcome message."""
    welcome = (
        "🏢 *ברוך הבא למערכת ניהול גבר יזמות*\n\n"
        "אני מנכ\"ל המערכת שלך. אתה יכול לתת לי הוראות ואני אנהל את הצוות.\n\n"
        "*פקודות זמינות:*\n"
        "/task - שלח משימה חדשה לצוות\n"
        "/review - ראה תוצרים ממתינים לאישור\n"
        "/meeting - כנס ישיבת הנהלה\n"
        "/consult - ייעוץ מהיר ממחלקה\n"
        "/status - מצב משימות פעילות\n"
        "/help - עזרה\n\n"
        "או פשוט כתוב לי הוראה בטבעית! 💬"
    )
    await update.message.reply_text(welcome, parse_mode="Markdown")


@chairman_only
async def new_task(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Receive a new task instruction."""
    if context.args:
        instruction = " ".join(context.args)
        await _process_instruction(update, context, instruction)
    else:
        await update.message.reply_text(
            "📝 *שלח לי את ההוראה שלך:*\n"
            "לדוגמה: צור קמפיין שיווקי לפסח",
            parse_mode="Markdown"
        )
        context.user_data["awaiting_task"] = True


@chairman_only
async def review_deliverables(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show pending deliverables for review."""
    pending = task_manager.get_pending_reviews()

    if not pending:
        await update.message.reply_text("✅ אין תוצרים ממתינים לאישור כרגע.")
        return

    await update.message.reply_text(
        f"📋 *{len(pending)} תוצרים ממתינים לאישור:*",
        parse_mode="Markdown"
    )

    for item in pending[:5]:  # Show up to 5 at a time
        task_title = item.get("tasks", {}).get("title", "Unknown Task") if isinstance(item.get("tasks"), dict) else "Unknown"
        text = (
            f"🏷 *{task_title}*\n"
            f"מחלקה: {item['department']}\n"
            f"תפקיד: {item['agent_role']}\n\n"
            f"{item['content'][:800]}{'...' if len(item['content']) > 800 else ''}"
        )

        keyboard = [
            [
                InlineKeyboardButton("✅ אשר", callback_data=f"approve_{item['id']}"),
                InlineKeyboardButton("❌ דחה", callback_data=f"reject_{item['id']}"),
                InlineKeyboardButton("🔄 תיקון", callback_data=f"revise_{item['id']}"),
            ],
            [
                InlineKeyboardButton("📤 אשר + פרסם", callback_data=f"approve_publish_{item['id']}"),
            ]
        ]
        await update.message.reply_text(
            text,
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )


@chairman_only
async def call_meeting(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Hold a management meeting."""
    topic = " ".join(context.args) if context.args else None

    if not topic:
        await update.message.reply_text(
            "💼 *כנס ישיבת הנהלה*\n"
            "שלח: /meeting <נושא הישיבה>\n"
            "לדוגמה: /meeting אסטרטגיה שיווקית לרבעון הבא",
            parse_mode="Markdown"
        )
        return

    await update.message.reply_text(
        f"🏛 *פותח ישיבת הנהלה...*\n\nנושא: {topic}",
        parse_mode="Markdown"
    )

    result = meeting_room.hold_meeting(
        title=f"ישיבת הנהלה - {topic}",
        topic=topic,
        participants=["ceo", "cfo", "marketing", "sales", "legal", "cto"],
        meeting_type="management"
    )

    # Send transcript summary
    transcript_text = "📋 *תמליל הישיבה:*\n\n"
    for entry in result["transcript"]:
        transcript_text += f"*{entry['role']}:* {entry['message']}\n\n"

    decisions_text = "⚖️ *החלטות:*\n" + "\n".join([f"• {d}" for d in result["decisions"]])
    actions_text = "✅ *משימות שנפתחו:*\n" + "\n".join([
        f"• {a['item']} ({a.get('responsible', '?')})"
        for a in result["action_items"]
    ])

    for text in [transcript_text[:4000], decisions_text, actions_text]:
        if text.strip():
            await update.message.reply_text(text, parse_mode="Markdown")


@chairman_only
async def quick_consult(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Quick consultation from specific departments."""
    if not context.args:
        await update.message.reply_text(
            "💡 *ייעוץ מהיר*\n"
            "שלח: /consult <שאלה>\n"
            "לדוגמה: /consult האם כדאי להשקיע ברשתות החברתיות עכשיו?",
            parse_mode="Markdown"
        )
        return

    question = " ".join(context.args)
    await update.message.reply_text("🔍 אוסף חוות דעת מהמחלקות...")

    responses = meeting_room.quick_consult(
        question,
        ["cfo", "marketing", "legal", "compliance"]
    )

    text = f"💬 *ייעוץ מהיר:* {question}\n\n"
    for dept, response in responses.items():
        text += f"*{dept.upper()}:* {response}\n\n"

    await update.message.reply_text(text[:4000], parse_mode="Markdown")


@chairman_only
async def status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show active tasks status."""
    in_progress = db.get_tasks_by_status("in_progress")
    review = db.get_tasks_by_status("review")

    text = "📊 *מצב משימות:*\n\n"
    text += f"⚙️ *בעבודה:* {len(in_progress)}\n"
    for t in in_progress[:3]:
        text += f"  • {t['title']} ({t['assigned_to']})\n"

    text += f"\n👁 *ממתין לאישור:* {len(review)}\n"
    for t in review[:3]:
        text += f"  • {t['title']}\n"

    await update.message.reply_text(text, parse_mode="Markdown")


@chairman_only
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle free-form text messages as instructions."""
    text = update.message.text

    if context.user_data.get("awaiting_task"):
        context.user_data["awaiting_task"] = False
        await _process_instruction(update, context, text)
        return

    if context.user_data.get("awaiting_feedback"):
        deliverable_id = context.user_data.pop("awaiting_feedback")
        action = context.user_data.pop("feedback_action", "reject")

        if action == "reject":
            task_manager.reject_deliverable(deliverable_id, text)
            await update.message.reply_text("❌ תוצר נדחה עם הערות.")
        else:
            task_manager.request_revision(deliverable_id, text)
            await update.message.reply_text("🔄 בקשת תיקון נשלחה לצוות.")
        return

    # Treat any message as a new instruction
    await _process_instruction(update, context, text)


async def _process_instruction(update: Update,
                                 context: ContextTypes.DEFAULT_TYPE,
                                 instruction: str):
    """Process a chairman instruction through the full workflow."""
    await update.message.reply_text(
        f"✅ *קיבלתי את ההוראה:*\n_{instruction}_\n\nמעביר לצוות...",
        parse_mode="Markdown"
    )

    saved = db.save_instruction(instruction)
    instruction_id = saved["id"]

    progress_messages = []

    def on_progress(msg):
        progress_messages.append(msg)

    try:
        result = task_manager.process_chairman_instruction(
            instruction, instruction_id, on_progress
        )

        summary = (
            f"🎯 *עבודת הצוות הושלמה!*\n\n"
            f"📌 משימה: {result['task_title']}\n"
            f"🏢 מחלקות: {', '.join(result['departments_involved'])}\n\n"
            f"*סיכום מנכ\"ל:*\n{result['final_report'][:1500]}"
        )

        keyboard = [[
            InlineKeyboardButton("📋 ראה תוצרים", callback_data=f"view_task_{result['task_id']}"),
            InlineKeyboardButton("✅ אשר הכל", callback_data=f"approve_all_{result['task_id']}"),
        ]]

        await update.message.reply_text(
            summary[:4000],
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )

    except Exception as e:
        logger.error(f"Error processing instruction: {e}")
        await update.message.reply_text(
            f"⚠️ שגיאה בעיבוד ההוראה: {str(e)[:200]}"
        )


async def handle_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle inline keyboard button presses."""
    query = update.callback_query
    await query.answer()
    data = query.data

    if data.startswith("approve_publish_"):
        deliverable_id = data.replace("approve_publish_", "")
        task_manager.approve_deliverable(deliverable_id)

        keyboard = [[
            InlineKeyboardButton("📘 Facebook", callback_data=f"pub_fb_{deliverable_id}"),
            InlineKeyboardButton("📸 Instagram", callback_data=f"pub_ig_{deliverable_id}"),
            InlineKeyboardButton("🎵 TikTok", callback_data=f"pub_tt_{deliverable_id}"),
            InlineKeyboardButton("🌐 הכל", callback_data=f"pub_all_{deliverable_id}"),
        ]]
        await query.edit_message_reply_markup(InlineKeyboardMarkup(keyboard))
        await query.message.reply_text("✅ אושר! בחר לאיזה פלטפורמה לפרסם:")

    elif data.startswith("approve_"):
        deliverable_id = data.replace("approve_", "")
        task_manager.approve_deliverable(deliverable_id)
        await query.edit_message_reply_markup(None)
        await query.message.reply_text("✅ תוצר אושר ונשמר.")

    elif data.startswith("reject_"):
        deliverable_id = data.replace("reject_", "")
        context.user_data["awaiting_feedback"] = deliverable_id
        context.user_data["feedback_action"] = "reject"
        await query.message.reply_text("📝 כתוב את הסיבה לדחייה:")

    elif data.startswith("revise_"):
        deliverable_id = data.replace("revise_", "")
        context.user_data["awaiting_feedback"] = deliverable_id
        context.user_data["feedback_action"] = "revise"
        await query.message.reply_text("📝 כתוב מה צריך לתקן:")

    elif data.startswith("pub_"):
        parts = data.split("_", 2)
        platform_code = parts[1]
        deliverable_id = parts[2]

        platform_map = {"fb": "facebook", "ig": "instagram", "tt": "tiktok", "all": "all"}
        platform = platform_map.get(platform_code, platform_code)
        platforms = ["facebook", "instagram", "tiktok"] if platform == "all" else [platform]

        deliverables = db.get_deliverables_for_task(
            db._client.table("deliverables")
            .select("task_id")
            .eq("id", deliverable_id)
            .single()
            .execute()
            .data["task_id"]
        )

        content = next((d["content"] for d in deliverables if d["id"] == deliverable_id), "")

        pub = db.schedule_publication(
            deliverable_id=deliverable_id,
            task_id="",
            platform=platform,
            content=content[:2000]
        )

        await query.message.reply_text(
            f"📤 מפרסם ל: {', '.join(platforms)}..."
        )

        import asyncio
        results = await publisher.publish_to_platforms(pub["id"], platforms, content)

        result_text = "\n".join([
            f"{'✅' if r['success'] else '❌'} {r['platform']}: "
            f"{'פורסם!' if r['success'] else r.get('error', 'שגיאה')}"
            for r in results
        ])
        await query.message.reply_text(f"*תוצאות פרסום:*\n{result_text}", parse_mode="Markdown")


class GeverTelegramBot:
    def __init__(self):
        self.app = Application.builder().token(settings.telegram_bot_token).build()
        self._register_handlers()

    def _register_handlers(self):
        self.app.add_handler(CommandHandler("start", start))
        self.app.add_handler(CommandHandler("task", new_task))
        self.app.add_handler(CommandHandler("review", review_deliverables))
        self.app.add_handler(CommandHandler("meeting", call_meeting))
        self.app.add_handler(CommandHandler("consult", quick_consult))
        self.app.add_handler(CommandHandler("status", status))
        self.app.add_handler(CallbackQueryHandler(handle_callback))
        self.app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    def run(self):
        logger.info("Starting Gever Management Telegram Bot...")
        self.app.run_polling(allowed_updates=Update.ALL_TYPES)
