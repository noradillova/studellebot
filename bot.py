import os
import logging
import time
import random
from datetime import date

import django
from dotenv import load_dotenv
from ai_helper import ask_ai

load_dotenv()

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "djangoproject.settings")
django.setup()

import telebot
from telebot.types import ReplyKeyboardMarkup, InlineKeyboardMarkup, InlineKeyboardButton, KeyboardButton
from core.models import Course, User, Task, Quiz, Note, Message

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.FileHandler("bot.log"), logging.StreamHandler()],
)
logger = logging.getLogger(__name__)

TOKEN = os.getenv("TOKEN")
if not TOKEN:
    raise ValueError("TOKEN not found in .env file!")

bot = telebot.TeleBot(TOKEN)

user_states = {}
current_quiz = {}
asked_quizzes = {}

QUOTES = [
    "Keep going, you are doing great! 🚀",
    "Small progress is still progress 📚",
    "Discipline beats motivation 💪",
    "Study now, shine later ✨",
    "Every day is a new chance 🌸",
]

LEVEL_NAMES = {1:"🌱 Beginner", 2:"📖 Student", 3:"🎓 Scholar", 4:"🔬 Researcher", 5:"🏆 Master"}
DIFFICULTY_EMOJI = {"easy":"🟢", "medium":"🟡", "hard":"🔴"}

def get_level_name(level):
    return LEVEL_NAMES.get(level, f"⭐ Level {level}")

def get_or_create_user(msg):
    tg_id = str(msg.chat.id)
    username = msg.from_user.username or ""
    first_name = msg.from_user.first_name or ""
    user, created = User.objects.get_or_create(
        telegram_id=tg_id,
        defaults={"username": username, "first_name": first_name},
    )
    if not created:
        user.username = username
        user.first_name = first_name
        user.save(update_fields=["username", "first_name"])
    if created:
        seed_tasks(user)
    return user

def save_message(user, text, is_from_user=True):
    Message.objects.create(user=user, text=text[:500], is_from_user=is_from_user)

def seed_courses():
    courses = [
        ("Programming", "💻"),
        ("Math", "📐"),
        ("English", "🇬🇧"),
        ("Productivity", "🧠"),
    ]
    for name, emoji in courses:
        Course.objects.get_or_create(name=name, defaults={"emoji": emoji})

def seed_quizzes():
    quizzes = [
        ("Programming", "What does HTML stand for?", "HyperText Markup Language", "High Tech Modern Language", "Home Tool Markup Language", "HyperText Markup Language"),
        ("Programming", "Which symbol is used for comments in Python?", "#", "//", "/*", "#"),
        ("Programming", "What is a variable?", "A container for storing data", "A type of loop", "A function", "A container for storing data"),
        ("Programming", "What does CSS stand for?", "Cascading Style Sheets", "Computer Style System", "Creative Style Sheets", "Cascading Style Sheets"),
        ("Programming", "Which of these is a Python data type?", "list", "table", "array", "list"),
        ("Math", "What is 15% of 200?", "30", "25", "35", "30"),
        ("Math", "What is the square root of 144?", "12", "14", "11", "12"),
        ("Math", "What is 2 to the power of 8?", "256", "128", "512", "256"),
        ("Math", "How many degrees are in a triangle?", "180", "360", "90", "180"),
        ("Math", "What is the value of Pi (2 decimal places)?", "3.14", "3.12", "3.16", "3.14"),
        ("English", "Which is the correct sentence?", "She don't like coffee", "She doesn't like coffee", "She not like coffee", "She doesn't like coffee"),
        ("English", "What is the past tense of 'go'?", "went", "goed", "gone", "went"),
        ("English", "Which word means 'happy'?", "joyful", "angry", "sad", "joyful"),
        ("English", "What is the plural of 'child'?", "children", "childs", "childen", "children"),
        ("English", "Which is a preposition?", "under", "run", "happy", "under"),
        ("Productivity", "What is the Pomodoro technique?", "25 min work + 5 min break", "1 hour work + 10 min break", "45 min work + 15 min break", "25 min work + 5 min break"),
        ("Productivity", "What does SMART goal stand for?", "Specific Measurable Achievable Relevant Time-bound", "Simple Modern Adaptable Real Timely", "Strong Motivated Accurate Reliable Tested", "Specific Measurable Achievable Relevant Time-bound"),
        ("Productivity", "What is time blocking?", "Scheduling specific tasks for specific times", "Blocking social media", "Taking breaks", "Scheduling specific tasks for specific times"),
    ]
    for course_name, question, opt1, opt2, opt3, answer in quizzes:
        course = Course.objects.filter(name=course_name).first()
        if course:
            Quiz.objects.get_or_create(
                question=question,
                course=course,
                defaults={
                    "option1": opt1,
                    "option2": opt2,
                    "option3": opt3,
                    "answer": answer,
                }
            )

def seed_tasks(user):
    default_tasks = [
        ("Finish Python basics", "Programming", "easy"),
        ("Build simple calculator", "Programming", "medium"),
        ("Solve 5 LeetCode problems", "Programming", "hard"),
        ("Create Telegram bot", "Programming", "medium"),
        ("Solve 3 algebra problems", "Math", "easy"),
        ("Complete derivative exercises", "Math", "medium"),
        ("Study integrals for exam", "Math", "hard"),
        ("Learn 10 English words", "English", "easy"),
        ("Practice speaking 20 min", "English", "medium"),
        ("Write short English essay", "English", "medium"),
        ("Plan your study schedule", "Productivity", "easy"),
        ("Complete Pomodoro session", "Productivity", "medium"),
        ("Organize study notes", "Productivity", "easy"),
    ]
    for title, course_name, difficulty in default_tasks:
        course = Course.objects.filter(name=course_name).first()
        if course:
            Task.objects.get_or_create(
                title=title, course=course, user=user,
                defaults={"difficulty": difficulty},
            )

def award_xp(user, task):
    user.xp += task.xp_reward
    leveled_up = False
    if user.xp >= user.level * 50:
        user.level += 1
        leveled_up = True
    today = date.today()
    if user.last_completed:
        diff = (today - user.last_completed).days
        user.streak = user.streak + 1 if diff == 1 else (1 if diff > 1 else user.streak)
    else:
        user.streak = 1
    user.last_completed = today
    user.save()
    return task.xp_reward, leveled_up

def main_menu():
    kb = ReplyKeyboardMarkup(resize_keyboard=True)
    kb.row(KeyboardButton("📚 Courses"), KeyboardButton("📝 Tasks"))
    kb.row(KeyboardButton("🧠 Quizzes"), KeyboardButton("📒 Notes"))
    kb.row(KeyboardButton("📈 Progress"), KeyboardButton("👤 Profile"))
    kb.row(KeyboardButton("📅 Today Plan"), KeyboardButton("🏆 Top Users"))
    kb.row(KeyboardButton("🤖 AI Help"), KeyboardButton("❓ Help"))
    return kb

def back_kb():
    kb = ReplyKeyboardMarkup(resize_keyboard=True)
    kb.add(KeyboardButton("🔙 Back"))
    return kb

def category_kb():
    kb = ReplyKeyboardMarkup(resize_keyboard=True)
    kb.row("💻 Programming", "📐 Math")
    kb.row("🇬🇧 English", "🧠 Productivity")
    kb.add("🔙 Back")
    return kb

@bot.message_handler(commands=["start"])
def cmd_start(msg):
    try:
        user = get_or_create_user(msg)
        save_message(user, "/start")
        quote = random.choice(QUOTES)
        text = (
            f"👋 Welcome, *{msg.from_user.first_name}*!\n\n"
            f"{get_level_name(user.level)} · {user.xp} XP · 🔥 {user.streak} days\n\n"
            f"_{quote}_\n\nChoose an option 👇"
        )
        bot.send_message(msg.chat.id, text, parse_mode="Markdown", reply_markup=main_menu())
    except Exception as e:
        logger.error(f"Error in /start: {e}")
        bot.send_message(msg.chat.id, "⚠️ Something went wrong. Try again.")

@bot.message_handler(commands=["help"])
@bot.message_handler(func=lambda m: m.text == "❓ Help")
def cmd_help(msg):
    text = (
        "📖 *StudyBot — Help*\n\n"
        "/start\n"
        "/help\n"
        "/ask\n"
        "/stats\n"
        "/history\n\n"
        "📚 Courses · 📝 Tasks · 🧠 Quizzes\n"
        "📒 Notes · 📈 Progress · 👤 Profile\n"
        "📅 Today Plan · 🏆 Top Users · 🤖 AI Help"
    )
    bot.send_message(msg.chat.id, text, parse_mode="Markdown", reply_markup=main_menu())

@bot.message_handler(func=lambda m: m.text == "🔙 Back")
def go_back(msg):
    user_states.pop(msg.chat.id, None)
    bot.send_message(msg.chat.id, "🏠 Main menu", reply_markup=main_menu())

MATERIALS = {
    "💻 Programming": {"text": "💻 *Programming*\n\n📖 roadmap.sh\n📖 freecodecamp.org\n📖 cs50.harvard.edu\n\n🏋 leetcode.com\n🏋 codewars.com\n\n📱 SoloLearn, Mimo", "course": "Programming"},
    "📐 Math":        {"text": "📐 *Math*\n\n📖 khanacademy.org\n📖 brilliant.org\n\n🏋 symbolab.com\n🏋 wolframalpha.com\n\n📱 Photomath, Cymath", "course": "Math"},
    "🇬🇧 English":    {"text": "🇬🇧 *English*\n\n📖 duolingo.com\n📖 bbc.co.uk/learningenglish\n\n🏋 quizlet.com\n🏋 test-english.com\n\n📱 Duolingo, EWA, Elsa", "course": "English"},
    "🧠 Productivity": {"text": "🧠 *Productivity*\n\n📖 notion.so\n📖 todoist.com\n\n🏋 Pomodoro\n🏋 Time blocking\n\n📱 Notion, Forest, Todoist", "course": "Productivity"},
}

@bot.message_handler(func=lambda m: m.text == "📚 Courses")
def show_courses(msg):
    bot.send_message(msg.chat.id, "📚 Choose category:", reply_markup=category_kb())

@bot.message_handler(func=lambda m: m.text in MATERIALS)
def show_material(msg):
    info = MATERIALS[msg.text]
    kb = InlineKeyboardMarkup()
    kb.add(InlineKeyboardButton("📋 Tasks", callback_data=f"tasks_{info['course']}"))
    kb.add(InlineKeyboardButton("🧠 Quiz", callback_data=f"quiz_{info['course']}"))
    bot.send_message(msg.chat.id, info["text"], parse_mode="Markdown", reply_markup=kb)

TASK_MAP = {"💻 Programming Tasks":"Programming","📐 Math Tasks":"Math","🇬🇧 English Tasks":"English","🧠 Productivity Tasks":"Productivity"}

@bot.message_handler(func=lambda m: m.text == "📝 Tasks")
def show_task_menu(msg):
    kb = ReplyKeyboardMarkup(resize_keyboard=True)
    kb.add("💻 Programming Tasks")
    kb.add("📐 Math Tasks")
    kb.add("🇬🇧 English Tasks")
    kb.add("🧠 Productivity Tasks")
    kb.add("🔙 Back")
    bot.send_message(msg.chat.id, "📝 Choose category:", reply_markup=kb)

@bot.message_handler(func=lambda m: m.text in TASK_MAP)
def show_tasks(msg):
    try:
        user = get_or_create_user(msg)
        category = TASK_MAP[msg.text]
        tasks = Task.objects.filter(user=user, course__name=category, is_active=True).order_by("difficulty")[:6]
        if not tasks.exists():
            bot.send_message(msg.chat.id, f"🎉 All {category} tasks done!", reply_markup=main_menu())
            return
        bot.send_message(msg.chat.id, f"📝 *{category} Tasks:*", parse_mode="Markdown")
        for t in tasks:
            kb = InlineKeyboardMarkup()
            kb.add(InlineKeyboardButton(f"✅ Complete (+{t.xp_reward} XP)", callback_data=f"done_{t.id}"))
            bot.send_message(msg.chat.id,
                f"{DIFFICULTY_EMOJI.get(t.difficulty,'⚪')} *{t.title}*\n+{t.xp_reward} XP",
                parse_mode="Markdown", reply_markup=kb)
    except Exception as e:
        logger.error(f"Error in show_tasks: {e}")
        bot.send_message(msg.chat.id, "⚠️ Error loading tasks.")

@bot.callback_query_handler(func=lambda c: c.data.startswith("done_"))
def complete_task(call):
    try:
        task = Task.objects.get(id=int(call.data.split("_")[1]))
        user = User.objects.get(telegram_id=str(call.from_user.id))
        if not task.is_active:
            bot.answer_callback_query(call.id, "Already completed!")
            return
        if task.user != user:
            bot.answer_callback_query(call.id, "❌ Not your task!")
            return
        from django.utils import timezone
        task.is_active = False
        task.completed_at = timezone.now()
        task.save()
        xp, leveled_up = award_xp(user, task)
        level_msg = f"\n🎉 *LEVEL UP! Level {user.level}!*" if leveled_up else ""
        bot.answer_callback_query(call.id, f"✅ +{xp} XP!")
        bot.edit_message_text(
            f"✅ *{task.title}*\n+{xp} XP · Total: {user.xp} · Streak: {user.streak} 🔥{level_msg}",
            call.message.chat.id, call.message.message_id, parse_mode="Markdown")
    except Exception as e:
        logger.error(f"Error completing task: {e}")

@bot.callback_query_handler(func=lambda c: c.data.startswith("tasks_"))
def tasks_from_course(call):
    try:
        user = User.objects.get(telegram_id=str(call.from_user.id))
        category = call.data.split("_")[1]
        tasks = Task.objects.filter(user=user, course__name=category, is_active=True)[:5]
        if not tasks.exists():
            bot.send_message(call.message.chat.id, f"🎉 All {category} tasks done!")
            return
        for t in tasks:
            kb = InlineKeyboardMarkup()
            kb.add(InlineKeyboardButton(f"✅ Complete (+{t.xp_reward} XP)", callback_data=f"done_{t.id}"))
            bot.send_message(call.message.chat.id,
                f"{DIFFICULTY_EMOJI.get(t.difficulty,'⚪')} *{t.title}*",
                parse_mode="Markdown", reply_markup=kb)
    except Exception as e:
        logger.error(f"Error tasks_from_course: {e}")

@bot.message_handler(func=lambda m: m.text == "🧠 Quizzes")
def show_quiz_menu(msg):
    kb = InlineKeyboardMarkup()
    kb.add(InlineKeyboardButton("💻 Programming", callback_data="quiz_Programming"))
    kb.add(InlineKeyboardButton("📐 Math", callback_data="quiz_Math"))
    kb.row(InlineKeyboardButton("🇬🇧 English", callback_data="quiz_English"),
           InlineKeyboardButton("🧠 Productivity", callback_data="quiz_Productivity"))
    kb.add(InlineKeyboardButton("🎲 Random", callback_data="quiz_random"))
    bot.send_message(msg.chat.id, "🧠 *Choose quiz category:*", parse_mode="Markdown", reply_markup=kb)

@bot.callback_query_handler(func=lambda c: c.data.startswith("quiz_"))
def start_quiz(call):
    try:
        category = call.data.split("_")[1]
        quizzes = list(Quiz.objects.all() if category == "random" else Quiz.objects.filter(course__name=category))
        if not quizzes:
            bot.answer_callback_query(call.id)
            bot.send_message(call.message.chat.id, "❌ No quizzes yet. Add them in admin panel.")
            return
        bot.answer_callback_query(call.id)
        chat_id = call.message.chat.id
already_asked = asked_quizzes.get(chat_id, [])
remaining = [q for q in quizzes if q.id not in already_asked]
if not remaining:
    asked_quizzes[chat_id] = []
    remaining = quizzes
q = random.choice(remaining)
asked_quizzes[chat_id] = already_asked + [q.id]
current_quiz[chat_id] = q
        options = [q.option1, q.option2, q.option3]
        random.shuffle(options)
        kb = InlineKeyboardMarkup()
        for opt in options:
            kb.add(InlineKeyboardButton(opt, callback_data=f"ans_{opt}"))
        bot.send_message(call.message.chat.id, f"🧠 *{q.question}*", parse_mode="Markdown", reply_markup=kb)
    except Exception as e:
        logger.error(f"Error in quiz: {e}")

@bot.callback_query_handler(func=lambda c: c.data.startswith("ans_"))
def check_answer(call):
    q = current_quiz.get(call.message.chat.id)
    if not q:
        bot.answer_callback_query(call.id, "Quiz expired.")
        return
    answer = call.data[4:]
    correct = answer == q.answer
    bot.answer_callback_query(call.id, "✅ Correct!" if correct else f"❌ Wrong! Answer: {q.answer}")
    kb = InlineKeyboardMarkup()
    kb.add(InlineKeyboardButton("🔄 Next", callback_data=f"quiz_{q.course.name}"))
    result = "✅ *Correct!*" if correct else f"❌ *Wrong!*\n\nCorrect: *{q.answer}*"
    bot.edit_message_text(f"🧠 *{q.question}*\n\n{result}",
        call.message.chat.id, call.message.message_id, parse_mode="Markdown", reply_markup=kb)
    current_quiz.pop(call.message.chat.id, None)

@bot.message_handler(func=lambda m: m.text == "📒 Notes")
def notes_menu(msg):
    kb = InlineKeyboardMarkup()
    kb.add(InlineKeyboardButton("✍️ Add note", callback_data="note_add"))
    kb.add(InlineKeyboardButton("📋 View notes", callback_data="note_view"))
    kb.add(InlineKeyboardButton("🗑 Delete note", callback_data="note_delete_menu"))
    bot.send_message(msg.chat.id, "📒 *Notes*", parse_mode="Markdown", reply_markup=kb)

@bot.callback_query_handler(func=lambda c: c.data == "note_add")
def note_add(call):
    bot.answer_callback_query(call.id)
    user_states[call.message.chat.id] = "note_writing"
    bot.send_message(call.message.chat.id, "✍️ Write your note:", reply_markup=back_kb())

@bot.callback_query_handler(func=lambda c: c.data == "note_view")
def note_view(call):
    bot.answer_callback_query(call.id)
    try:
        user = User.objects.get(telegram_id=str(call.from_user.id))
        notes = Note.objects.filter(user=user).order_by("-created_at")[:10]
        if not notes.exists():
            bot.send_message(call.message.chat.id, "📭 No notes yet.")
            return
        text = "📒 *Your Notes:*\n\n"
        for i, n in enumerate(notes, 1):
            text += f"*{i}.* {n.text}\n_{n.created_at.strftime('%d.%m %H:%M')}_\n\n"
        bot.send_message(call.message.chat.id, text, parse_mode="Markdown")
    except Exception as e:
        logger.error(f"Error viewing notes: {e}")

@bot.callback_query_handler(func=lambda c: c.data == "note_delete_menu")
def note_delete_menu(call):
    try:
        bot.answer_callback_query(call.id)
        user = User.objects.get(telegram_id=str(call.from_user.id))
        notes = Note.objects.filter(user=user).order_by("-created_at")[:10]
        if not notes.exists():
            bot.send_message(call.message.chat.id, "📭 No notes to delete.")
            return
        kb = InlineKeyboardMarkup()
        for i, n in enumerate(notes, 1):
            short = n.text[:30] + "..." if len(n.text) > 30 else n.text
            kb.add(InlineKeyboardButton(f"🗑 {i}. {short}", callback_data=f"del_note_{n.id}"))
        bot.send_message(call.message.chat.id, "Choose note to delete:", reply_markup=kb)
    except Exception as e:
        logger.error(f"Error delete menu: {e}")

@bot.callback_query_handler(func=lambda c: c.data.startswith("del_note_"))
def delete_note(call):
    try:
        note = Note.objects.get(id=int(call.data.split("_")[2]))
        user = User.objects.get(telegram_id=str(call.from_user.id))
        if note.user != user:
            bot.answer_callback_query(call.id, "❌ Not your note!")
            return
        note.delete()
        bot.answer_callback_query(call.id, "🗑 Deleted!")
        bot.edit_message_text("🗑 Note deleted.", call.message.chat.id, call.message.message_id)
    except Exception as e:
        logger.error(f"Error deleting note: {e}")

@bot.message_handler(func=lambda m: m.text == "📈 Progress")
@bot.message_handler(commands=["stats"])
def show_progress(msg):
    try:
        user = User.objects.get(telegram_id=str(msg.from_user.id))
        total = Task.objects.filter(user=user).count()
        done = Task.objects.filter(user=user, is_active=False).count()
        percent = int((done / total) * 100) if total > 0 else 0
        bar = "█" * int(percent/10) + "░" * (10 - int(percent/10))
        xp_next = user.level * 50
        xp_bar = "█" * int((user.xp % xp_next) / xp_next * 10) + "░" * (10 - int((user.xp % xp_next) / xp_next * 10))
        text = (
            f"📈 *Progress*\n\n"
            f"{get_level_name(user.level)}\n\n"
            f"✅ Tasks: {done}/{total}\n[{bar}] {percent}%\n\n"
            f"⭐ XP: {user.xp}\n[{xp_bar}] → Level {user.level+1}\n\n"
            f"🔥 Streak: {user.streak} days"
        )
        bot.send_message(msg.chat.id, text, parse_mode="Markdown")
    except User.DoesNotExist:
        bot.send_message(msg.chat.id, "⚠️ Send /start first.")

@bot.message_handler(func=lambda m: m.text == "👤 Profile")
def show_profile(msg):
    try:
        user = User.objects.get(telegram_id=str(msg.from_user.id))
        done = Task.objects.filter(user=user, is_active=False).count()
        notes_count = Note.objects.filter(user=user).count()
        text = (
            f"👤 *Profile*\n\n"
            f"🏷 {user.first_name or user.username or 'Unknown'}\n\n"
            f"🏆 {get_level_name(user.level)}\n"
            f"⭐ XP: {user.xp}\n"
            f"🔥 Streak: {user.streak}\n"
            f"✅ Tasks done: {done}\n"
            f"📒 Notes: {notes_count}\n\n"
            f"📅 Joined: {user.created_at.strftime('%d.%m.%Y')}"
        )
        bot.send_message(msg.chat.id, text, parse_mode="Markdown")
    except User.DoesNotExist:
        bot.send_message(msg.chat.id, "⚠️ Send /start first.")

@bot.message_handler(func=lambda m: m.text == "📅 Today Plan")
def today_plan(msg):
    try:
        user = User.objects.get(telegram_id=str(msg.from_user.id))
        tasks = Task.objects.filter(user=user, is_active=True).order_by("?")[:3]
        done_today = Task.objects.filter(user=user, is_active=False, completed_at__date=date.today()).count()
        text = (
            f"📅 *Today's Plan*\n\n"
            f"🔥 Streak: {user.streak} · ⭐ XP: {user.xp}\n"
            f"✅ Done today: {done_today}\n\n"
        )
        if tasks.exists():
            text += "📌 *Focus on:*\n"
            for t in tasks:
                text += f"{DIFFICULTY_EMOJI.get(t.difficulty,'⚪')} {t.title}\n"
        else:
            text += "🎉 All tasks done today!"
        text += f"\n\n✨ _{random.choice(QUOTES)}_"
        bot.send_message(msg.chat.id, text, parse_mode="Markdown")
    except User.DoesNotExist:
        bot.send_message(msg.chat.id, "⚠️ Send /start first.")

@bot.message_handler(func=lambda m: m.text == "🏆 Top Users")
def top_users(msg):
    users = User.objects.order_by("-xp")[:10]
    medals = ["🥇","🥈","🥉"]
    text = "🏆 *Top Learners*\n\n"
    for i, u in enumerate(users, 1):
        medal = medals[i-1] if i <= 3 else f"{i}."
        name = u.username or u.first_name or "Anonymous"
        text += f"{medal} @{name} — {u.xp} XP · Lvl {u.level}\n"
    bot.send_message(msg.chat.id, text, parse_mode="Markdown")

@bot.message_handler(commands=["history"])
def show_history(msg):
    try:
        user = User.objects.get(telegram_id=str(msg.from_user.id))
        messages = Message.objects.filter(user=user).order_by("-created_at")[:10]
        if not messages.exists():
            bot.send_message(msg.chat.id, "📭 No history yet.")
            return
        text = "📜 *Recent History:*\n\n"
        for m in reversed(list(messages)):
            direction = "You" if m.is_from_user else "Bot"
            short = m.text[:50] + "..." if len(m.text) > 50 else m.text
            text += f"[{m.created_at.strftime('%H:%M')}] *{direction}:* {short}\n"
        bot.send_message(msg.chat.id, text, parse_mode="Markdown")
    except User.DoesNotExist:
        bot.send_message(msg.chat.id, "⚠️ Send /start first.")


@bot.message_handler(func=lambda m: m.text == "🤖 AI Help")
def ai_menu(msg):
    kb = InlineKeyboardMarkup()
    kb.add(InlineKeyboardButton("💻 Programming", callback_data="ai_topic_programming"))
    kb.add(InlineKeyboardButton("📐 Math",        callback_data="ai_topic_math"))
    kb.add(InlineKeyboardButton("🇬🇧 English",    callback_data="ai_topic_english"))
    kb.add(InlineKeyboardButton("🧠 Productivity", callback_data="ai_topic_productivity"))
    kb.add(InlineKeyboardButton("❓ Free question", callback_data="ai_topic_free"))
    bot.send_message(msg.chat.id,
        "🤖 *AI Assistant*\n\nAsk any academic question:",
        parse_mode="Markdown", reply_markup=kb)

@bot.callback_query_handler(func=lambda c: c.data.startswith("ai_topic_"))
def ai_topic_selected(call):
    bot.answer_callback_query(call.id)
    prompts = {
        "programming": "💻 Write a question about programming:",
        "math":        "📐 Write a question about math:",
        "english":     "🇬🇧 Write a question about English:",
        "productivity":"🧠 Write a question about productivity:",
        "free":        "❓ Write any academic question:",
    }
    topic = call.data.split("_")[2]
    user_states[call.message.chat.id] = f"ai_question_{topic}"
    bot.send_message(call.message.chat.id, prompts.get(topic, "❓ Write a question:"), reply_markup=back_kb())

@bot.message_handler(commands=["ask"])
def cmd_ask(msg):
    question = msg.text.replace("/ask", "").strip()
    if not question:
        bot.send_message(msg.chat.id, "Example: `/ask How does recursion work?`", parse_mode="Markdown")
        return
    _handle_ai_question(msg.chat.id, msg.from_user.id, question)

@bot.message_handler(func=lambda m: isinstance(user_states.get(m.chat.id), str) and user_states[m.chat.id].startswith("ai_question_"))
def handle_ai_input(msg):
    user_states.pop(msg.chat.id, None)
    _handle_ai_question(msg.chat.id, msg.from_user.id, msg.text)

def _handle_ai_question(chat_id, tg_user_id, question):
    if not question or len(question.strip()) < 3:
        bot.send_message(chat_id, "⚠️ The question is too short.")
        return
    try:
        user = User.objects.get(telegram_id=str(tg_user_id))
    except User.DoesNotExist:
        bot.send_message(chat_id, "⚠️ Send /start first.")
        return
    typing_msg = bot.send_message(chat_id, "🤖 AI thinks...")
    save_message(user, question, is_from_user=True)
    answer = ask_ai(question, user)
    try:
        bot.delete_message(chat_id, typing_msg.message_id)
    except Exception:
        pass
    kb = InlineKeyboardMarkup()
    kb.add(InlineKeyboardButton("🔄 One more question", callback_data="ai_topic_free"))
    bot.send_message(chat_id, f"🤖 *AI:*\n\n{answer}", parse_mode="Markdown", reply_markup=kb)
    save_message(user, answer, is_from_user=False)


@bot.message_handler(func=lambda m: user_states.get(m.chat.id) == "note_writing")
def handle_note_input(msg):
    if not msg.text or not msg.text.strip():
        bot.send_message(msg.chat.id, "⚠️ Note cannot be empty.")
        return
    try:
        user = User.objects.get(telegram_id=str(msg.from_user.id))
        Note.objects.create(user=user, text=msg.text.strip())
        user_states.pop(msg.chat.id, None)
        bot.send_message(msg.chat.id, "✅ *Note saved!*", parse_mode="Markdown", reply_markup=main_menu())
    except Exception as e:
        logger.error(f"Error saving note: {e}")
        bot.send_message(msg.chat.id, "⚠️ Error saving note.")

@bot.message_handler(func=lambda m: True)
def unknown_message(msg):
    try:
        user = User.objects.get(telegram_id=str(msg.from_user.id))
        save_message(user, msg.text or "")
    except Exception:
        pass
    bot.send_message(msg.chat.id,
        "❓ I don't understand the command. Type /help or use the menu 👇",
        reply_markup=main_menu())

if __name__ == "__main__":
    logger.info("StudyBot starting...")
    seed_courses()
    seed_quizzes()
    while True:
        try:
            logger.info("Bot is running...")
            bot.infinity_polling(skip_pending=True, timeout=60)
        except Exception as e:
            logger.error(f"Bot crashed: {e}. Restarting in 5 sec...")
            time.sleep(5)