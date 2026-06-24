====================================================
  AUTO-REPLY USERBOT — O'RNATISH YO'RIQNOMASI
====================================================

1-QADAM: API ID va API HASH olish
--------------------------------------------------
1. Brauzerda oching: https://my.telegram.org
2. Telefon raqamingizni kiriting va kiring
3. "API development tools" ga bosing
4. App name: AutoReply (istalgan nom)
5. API_ID va API_HASH ni nusxa oling

2-QADAM: autoreply.py faylini tahrirlash
--------------------------------------------------
Faylni oching va quyidagi qatorlarni to'ldiring:

  API_ID = 12345678        ← my.telegram.org dan
  API_HASH = "abcdef..."   ← my.telegram.org dan
  PHONE = "+998901234567"  ← sizning raqamingiz

3-QADAM: Python kutubxonasini o'rnatish
--------------------------------------------------
CMD yoki Terminalni oching va yozing:

  pip install telethon

4-QADAM: Botni ishga tushirish
--------------------------------------------------
CMD da bot fayli joylashgan papkaga o'ting:

  cd C:\Users\777\Desktop\autoreply_bot

Keyin ishga tushiring:

  python autoreply.py

5-QADAM: Birinchi kirish
--------------------------------------------------
- Telefon raqamingizni so'raydi (avtomatik)
- Telegramdan kod keladi — kiring
- Agar 2FA bo'lsa — parolni kiriting
- Tayyor! Endi session fayl saqlanadi

KEYINGI SAFAR:
--------------------------------------------------
Faqat: python autoreply.py
(kod so'ramaydi, to'g'ri ishga tushadi)

TO'XTATISH:
--------------------------------------------------
Ctrl+C tugmasini bosing

====================================================
  QANDAY ISHLAYDI?
====================================================

✅ Kimdir sizga yozsa → avtomatik javob
✅ Har bir odamga faqat 1 marta javob
✅ Siz o'sha odamga javob yozsangiz → keyingi safar yana avtomatik ishlaydi
✅ Bot ishlayotganda ekranda loglari ko'rinadi

====================================================
