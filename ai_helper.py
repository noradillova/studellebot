import os
import anthropic

client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))

SYSTEM_PROMPT = """You are a helpful AI assistant in the StudyBot Telegram bot.
You help students with any questions they have - studying, programming, math, 
English, productivity, or any other topic.
Keep answers clear and concise (max 3-4 paragraphs), use examples when helpful.
Reply in the same language the question was asked in."""

def ask_ai(question: str, user) -> str:
    try:
        from core.models import Message
        history = Message.objects.filter(user=user).order_by("-created_at")[:6]
        messages = []
        for msg in reversed(list(history)):
            role = "user" if msg.is_from_user else "assistant"
            messages.append({"role": role, "content": msg.text})
        messages.append({"role": "user", "content": question})

        response = client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=600,
            system=SYSTEM_PROMPT,
            messages=messages,
        )
        return response.content[0].text

    except anthropic.AuthenticationError:
        return "⚠️ API key error. Contact the administrator."
    except anthropic.RateLimitError:
        return "⚠️ Too many requests. Please try again in a minute."
    except anthropic.APIConnectionError:
        return "⚠️ No connection to AI. Check your internet."
    except Exception as e:
        return f"⚠️ Error: {str(e)[:100]}"