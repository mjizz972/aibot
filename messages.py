from game import Role, ROLE_EMOJI


ROLE_DESCRIPTIONS = {
    Role.MAFIA: (
        "🔫 <b>Siz — MAFIA!</b>\n\n"
        "🌙 Tunda fuqarolarni o'ldirish uchun nishon tanlaysiz.\n"
        "👥 Mafia jamoasi: <b>{mates}</b>\n\n"
        "⚠️ Agar Ayg'oqchi sizni bloklasa — siz o'lasiz!\n"
        "🏆 G'alaba: Mafia soni ≥ fuqarolar soni"
    ),
    Role.DONN: (
        "👑 <b>Siz — DONN (Bosh Mafia)!</b>\n\n"
        "🌙 Tunda nishon tanlaysiz (mafia bilan birga).\n"
        "🔍 Sherif sizi tekshirsa — tinch kishi ko'rinadi!\n"
        "🤫 Siz bir kishiga o'z kimligingizni oshkor qila olasiz.\n"
        "👥 Mafia jamoasi: <b>{mates}</b>\n\n"
        "⚠️ Agar Ayg'oqchi sizni bloklasa — siz o'lasiz!\n"
        "🏆 G'alaba: Mafia soni ≥ fuqarolar soni"
    ),
    Role.SHERIFF: (
        "🔍 <b>Siz — SHERIF!</b>\n\n"
        "🌙 Tunda bir kishini tekshirasiz.\n"
        "☠️ Agar u MAFIA bo'lsa — u o'sha kecha o'ladi!\n"
        "⚠️ Donn tekshirilsa — tinch kishi ko'rinadi (o'lmaydi)!\n"
        "⚠️ Agar Ayg'oqchi sizni bloklasa — tekshira olmaysiz!\n\n"
        "💡 Ehtiyotkor bo'ling — mafia sizi birinchi o'ldiradi!\n"
        "🏆 G'alaba: Barcha mafiyani toping"
    ),
    Role.DOCTOR: (
        "💉 <b>Siz — DOKTOR!</b>\n\n"
        "🌙 Tunda bir kishini davolaysiz — mafia o'ldirolmaydi!\n"
        "🏠 O'zingizni faqat <b>1 marta</b> davolay olasiz.\n"
        "⚠️ Agar Ayg'oqchi sizni bloklasa — davola olmaysiz!\n\n"
        "💡 Sherifni yoki boshqa muhim o'yinchini himoya qiling!\n"
        "🏆 G'alaba: Barcha mafiyani yo'q qiling"
    ),
    Role.SPY: (
        "💋 <b>Siz — AYG'OQCHI!</b>\n\n"
        "🌙 Tunda bir kishini bloklaysiz:\n"
        "   🔒 Bloklangan kishi o'z harakatini bajara olmaydi\n"
        "   🛡️ Mafia bloklangan kishini o'ldira olmaydi!\n"
        "   ☠️ Agar mafia a'zosini bloklasangiz — U O'LADI!\n"
        "🙋 O'zingizni faqat <b>1 marta</b> bloklash mumkin\n\n"
        "💡 Mafiyani bloklang va uni yo'q qiling!\n"
        "🏆 G'alaba: Barcha mafiyani yo'q qiling"
    ),
    Role.CIVILIAN: (
        "👥 <b>Siz — FUQARO!</b>\n\n"
        "☀️ Kunduz kunda muhokama qiling va mafiyani toping.\n"
        "🗳️ Ovoz berishda diqqatli bo'ling!\n\n"
        "💡 Sherifga ishoning, lekin hamma gapga ham emas.\n"
        "🏆 G'alaba: Barcha mafiyani yo'q qiling"
    ),
}


def get_role_message(role: Role, game=None) -> str:
    template = ROLE_DESCRIPTIONS.get(role, "❓ Noma'lum rol")
    if role in (Role.MAFIA, Role.DONN) and game:
        return template.format(mates=game.get_mafia_mates_text())
    return template


def get_role_emoji(role: Role) -> str:
    return ROLE_EMOJI.get(role, "❓")


WINNER_MESSAGES = {
    "mafia": (
        "🔫 <b>MAFIA G'ALABA QOZONDI!</b>\n\n"
        "Shahar mafiyaning qo'liga o'tdi... 😈"
    ),
    "civilian": (
        "🎊 <b>TINCH AHOLI G'ALABA QOZONDI!</b>\n\n"
        "Shahar tozalandi! Mafia tamomila yo'q qilindi! 🏆"
    ),
}

RULES_TEXT = (
    "📜 <b>MAFIA QOIDALARI</b>\n\n"
    "<b>🎭 Rollar:</b>\n"
    "🔫 <b>Mafia (1-2)</b> — tunda o'ldiradi, jamoada ishlaydi\n"
    "👑 <b>Donn (1)</b> — Sherif tekshirganda tinch ko'rinadi!\n"
    "🔍 <b>Sherif (1)</b> — tunda MAFIA topsa, o'sha kecha o'ladi!\n"
    "💉 <b>Doktor (1)</b> — tunda birini davolaydi, o'zini 1 marta\n"
    "💋 <b>Ayg'oqchi (1)</b> — tunda birini bloklaydi:\n"
    "   • Bloklangan kishi harakatini bajara olmaydi\n"
    "   • Mafia bloklangan kishini o'ldira olmaydi\n"
    "   • Mafiyani bloklasang — mafia O'LADI!\n"
    "👥 <b>Fuqaro</b> — ovoz beradi va mafiyani topadi\n\n"
    "<b>⚙️ O'yin tartibi:</b>\n"
    "1️⃣ 🌙 <b>Tun</b> — maxsus rollar harakatlanadi (40 sek)\n"
    "2️⃣ ☀️ <b>Kun</b> — muhokama (90 sek)\n"
    "3️⃣ 🗳️ <b>Ovoz</b> — kim chiqarilsin (45 sek)\n\n"
    "<b>🏆 G'alaba:</b>\n"
    "• Tinchlar: barcha mafia o'lsa\n"
    "• Mafia: soni ≥ tinch aholi soni bo'lsa\n\n"
    "<b>💰 Mukofot:</b>\n"
    "• Tinch g'oliblar: 100 💰\n"
    "• Mafia g'oliblar: 150 💰\n"
    "• Tirik qolish: +30 💰\n"
    "• Har bir o'ldirish: +20 💰"
)

HELP_HOW_TO_PLAY = (
    "🎮 <b>QANDAY O'YNASH KERAK?</b>\n\n"
    "<b>1️⃣ O'yinni boshlash:</b>\n"
    "Guruhda 'Yangi o'yin' tugmasini bos.\n"
    "Boshqalar '➕ Qo'shilish' tugmasini bosadi.\n"
    "Kamida 5 kishi to'plangach '▶️ Hozir boshlash' bosing.\n\n"
    "<b>2️⃣ Rol olish:</b>\n"
    "O'yin boshlananda bot har bir o'yinchiga\n"
    "<b>shaxsiy xabar</b> orqali rol yuboradi.\n"
    "⚠️ Buning uchun oldin botga /start bosing!\n\n"
    "<b>3️⃣ Tun bosqichi:</b>\n"
    "Hamma mute bo'ladi. Maxsus rollar\n"
    "shaxsiy xabarda tugma orqali harakatlanadi:\n"
    "• 🔫 Mafia — o'ldirish uchun nishon tanlaydi\n"
    "• 🔍 Sherif — kimni tekshirishni tanlaydi\n"
    "• 💉 Doktor — kimni davolashni tanlaydi\n"
    "• 💋 Ayg'oqchi — kimni bloklashni tanlaydi\n"
    "• 👑 Donn — kimga o'zini oshkor qilishni tanlaydi\n\n"
    "<b>4️⃣ Kun bosqichi:</b>\n"
    "Hamma unmute bo'ladi. 90 soniya muhokama!\n"
    "Kim mafia? Kim yolg'on gapiryapti?\n\n"
    "<b>5️⃣ Ovoz berish:</b>\n"
    "Guruhda tugma orqali kim chiqarilsinni\n"
    "ovoz berasiz. Eng ko'p ovoz olgan chiqadi.\n\n"
    "<b>6️⃣ G'alaba:</b>\n"
    "🎊 Tinchlar: barcha mafiyani o'ldirsa\n"
    "🔫 Mafia: soni tinchlar soniga tengla\n\n"
    "<b>💰 G'oliblar coin oladi va do'konda xarid qiladi!</b>"
)

HELP_ROLES = (
    "🎭 <b>BARCHA ROLLAR TAVSIFI</b>\n\n"
    "🔫 <b>MAFIA</b>\n"
    "Tunda bir kishini o'ldiradi. Mafia jamoasida.\n"
    "Kunduz kunda oddiy fuqaro kabi ko'rinadi.\n\n"
    "👑 <b>DONN (Bosh Mafia)</b>\n"
    "Mafia jamoasida. Sherif tekshirganda TINCH\n"
    "kishi ko'rinadi — eng xavfli rol!\n"
    "Bir kishiga o'z kimligini oshkor qila oladi.\n\n"
    "🔍 <b>SHERIF</b>\n"
    "Tunda bir kishini tekshiradi.\n"
    "Agar u MAFIA bo'lsa — o'sha kecha o'ladi!\n"
    "Donn tekshirilsa — tinch ko'rinadi (aldaydi).\n\n"
    "💉 <b>DOKTOR</b>\n"
    "Tunda bir kishini davolaydi.\n"
    "Davolangan kishi o'lmaydi (mafia ham o'ldira olmaydi).\n"
    "O'zini faqat 1 marta davolay oladi.\n\n"
    "💋 <b>AYG'OQCHI</b>\n"
    "Tunda bir kishini bloklaydi:\n"
    "• Bloklangan kishi harakatini bajara olmaydi\n"
    "• Mafia bloklangan kishini o'ldira olmaydi!\n"
    "• Mafiyani bloklasang — mafia O'LADI!\n"
    "O'zini 1 marta bloklash mumkin (himoya).\n\n"
    "👥 <b>FUQARO</b>\n"
    "Maxsus kuchi yo'q. Muhokama va ovoz berish.\n"
    "Mafiyani topib, chiqarib yuborish kerak!"
)

HELP_SHOP = (
    "🏪 <b>DO'KON NARSALARI TAVSIFI</b>\n\n"
    "<b>🎖️ DOIMIY NARSALAR</b> (bir marta olasiz)\n\n"
    "🏅 <b>Bronza nishon</b> — 80💰\n"
    "Profilingizda bronza nishon ko'rinadi.\n\n"
    "🥈 <b>Kumush nishon</b> — 200💰\n"
    "Profilingizda kumush nishon ko'rinadi.\n\n"
    "🥇 <b>Oltin nishon</b> — 450💰\n"
    "Profilingizda oltin nishon ko'rinadi.\n\n"
    "💎 <b>Olmosli nishon</b> — 900💰\n"
    "Profilingizda olmosli nishon ko'rinadi.\n\n"
    "👑 <b>Qirol toji</b> — 2500💰\n"
    "Eng noyob unvon — faqat chempionlar uchun!\n\n"
    "🎭 <b>Mafia Ustasi unvoni</b> — 350💰\n"
    "Profilingizda 'Mafia Ustasi' yozuvi ko'rinadi.\n\n"
    "🔍 <b>Sherif Ustasi unvoni</b> — 350💰\n"
    "Profilingizda 'Sherif Ustasi' yozuvi ko'rinadi.\n\n"
    "🌟 <b>VIP Status</b> — 600💰\n"
    "Profilingizda '🌟 VIP' belgisi ko'rinadi.\n"
    "━━━━━━━━━━━━━━━━━━\n"
    "<b>⚡ 1 MARTALIK NARSALAR</b>\n\n"
    "🛡️ <b>Himoya qalqoni</b> — 120💰\n"
    "O'sha tunda mafia sizni o'ldira olmaydi.\n"
    "Avtomatik ishga tushadi.\n\n"
    "🎲 <b>Omad kubigi</b> — 60💰\n"
    "Mafia o'ldirmoqchi bo'lsa 50% ehtimollik\n"
    "bilan omon qolasiz. Baxt bo'lsa — yashasiz!\n\n"
    "💊 <b>Tibbiy komplet</b> — 110💰\n"
    "Tun davomida bir kishini davolaysiz\n"
    "(Doktor kabi). Shaxsiy xabarda tugma chiqadi.\n\n"
    "🔮 <b>Yashirin niqob</b> — 80💰\n"
    "O'lganda yoki chiqarilganda rolingiz\n"
    "'❓ ?' ko'rinadi — hech kim bilmaydi.\n\n"
    "🗳️ <b>Qo'shimcha ovoz</b> — 70💰\n"
    "Ovoz berishda 2 ta ovoz berasiz.\n"
    "Bir o'yinda 1 marta.\n\n"
    "📢 <b>Anonim xabar</b> — 50💰\n"
    "O'yin paytida guruhga nomi ko'rinmasdan\n"
    "xabar yubora olasiz. /anon buyrug'i bilan.\n\n"
    "🕵️ <b>Josus komplet</b> — 200💰\n"
    "Tun boshida bir mafia a'zosining ismini\n"
    "shaxsiy xabarda bilib olasiz.\n\n"
    "🧪 <b>Zahar</b> — 180💰\n"
    "Tun davomida kimnidir zaharla — u kishi\n"
    "keyingi tun albatta o'ladi.\n\n"
    "🔔 <b>Xavf signali</b> — 90💰\n"
    "Mafia sizi nishon qilsa, siz oldindan\n"
    "shaxsiy xabarda xabar olasiz.\n\n"
    "🎯 <b>Aniq nishon</b> — 150💰\n"
    "Mafia uchun: bu tun hujumingiz himoya\n"
    "qalqoni va davolashdan o'tadi.\n\n"
    "🎰 <b>Lucky Ticket</b> — 40💰\n"
    "O'yin boshida kafolatlangan Lucky Event!\n\n"
    "💰 <b>Coin paketi x2</b> — 100💰\n"
    "Keyingi g'alabangizda coin ikki barobar\n"
    "bo'ladi. Masalan: 150💰 → 300💰"
)
