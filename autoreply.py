from telethon import TelegramClient, events
from telethon.tl.functions.users import GetFullUserRequest
from datetime import datetime
import asyncio

# ==================== SOZLAMALAR ====================
API_ID = 36932151         # my.telegram.org dan oling
API_HASH ="ebf016352d64d62fd0b68993b1789f1e"       # my.telegram.org dan oling
PHONE = "+998509008412"          # +998901234567 formatda

OWNER_NAME = "Muhriddin"

AUTO_REPLY_TEXT = (
    f"👋 Assalomu alaykum!\n\n"
    f"🙍‍♂️ <b>{OWNER_NAME}</b> Men Qahramonov Muhriddin 💻 hozir onlayn emas edi.\n"
    f"⏰ Onlayn bo'lishi bilan javob yozadi!\n\n"
    f"🙏 Sabr qiling, tez orada bog'lanadi."
)

# ==================== BOT ====================

client = TelegramClient("autoreply_session", API_ID, API_HASH)

# Kim javob olganligi esda tutiladi (spam bo'lmasligi uchun)
replied_users: set = set()


@client.on(events.NewMessage(incoming=True, func=lambda e: e.is_private))
async def auto_reply(event):
    sender_id = event.sender_id

    # O'z akkauntingizdan kelgan xabar bo'lsa o'tkazib yuborish
    me = await client.get_me()
    if sender_id == me.id:
        return

    # Har bir odamga faqat 1 marta avtomatik javob
    if sender_id in replied_users:
        return

    # Onlayn holatni tekshirish
    try:
        full = await client(GetFullUserRequest(me.id))
        # Agar status mavjud bo'lsa
    except Exception:
        pass

    replied_users.add(sender_id)
    await asyncio.sleep(1)  # biroz kuting, tabiiyroq ko'rinsin

    await event.respond(AUTO_REPLY_TEXT, parse_mode="html")

    sender = await event.get_sender()
    sender_name = getattr(sender, 'first_name', 'Noma\'lum')
    print(f"[{datetime.now().strftime('%H:%M:%S')}] ✅ Javob yuborildi → {sender_name} (ID: {sender_id})")


@client.on(events.NewMessage(outgoing=True, func=lambda e: e.is_private))
async def clear_replied(event):
    # Siz javob yozganingizda, o'sha odamni listdan o'chirish
    peer_id = event.peer_id
    if hasattr(peer_id, 'user_id'):
        replied_users.discard(peer_id.user_id)


async def main():
    print("=" * 40)
    print("🤖 AUTO-REPLY USERBOT")
    print("=" * 40)
    await client.start(phone=PHONE)
    me = await client.get_me()
    print(f"✅ Kirish muvaffaqiyatli: {me.first_name} (@{me.username})")
    print(f"📩 Avtomatik javob yoqildi!")
    print(f"⏹  To'xtatish uchun: Ctrl+C")
    print("=" * 40)
    await client.run_until_disconnected()


if __name__ == "__main__":
    asyncio.run(main())
