from telethon import TelegramClient, events
from google import genai

# ===== TELEGRAM ACCOUNT =====
api_id = 36932151
api_hash = "ebf016352d64d62fd0b68993b1789f1e"

# ===== AI KEY =====
ai = genai.Client(api_key="AQ.Ab8RN6I7mVRNBzqGnp8OAz3LseqBgbG4ENXta7u-TrVH5uTmMA")

# session fayl
client = TelegramClient("ai_session", api_id, api_hash)

@client.on(events.NewMessage(incoming=True))
async def handler(event):
    try:
        text = event.raw_text

        if not text:
            return

        # AI javob
        response = ai.models.generate_content(
            model="gemini-2.5-flash",
            contents=text
        )

        await event.reply(response.text)

    except Exception:
        await event.reply("Xatolik chiqdi 😕")

print("🤖 AI userbot ishga tushdi...")
client.start()
client.run_until_disconnected()