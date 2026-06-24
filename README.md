# 🛡️ Anti-Spam Bot

Telegram guruhingizni reklamadan himoya qiluvchi bot.

## O'rnatish

### 1. Node.js o'rnating
https://nodejs.org/ saytidan **LTS** versiyani yuklab o'rnating.

### 2. Loyihani oching
```
VS Code da antispam-bot papkasini oching
```

### 3. Paketlarni o'rnating
VS Code terminalida (Terminal → New Terminal):
```bash
npm install
```

### 4. Token sozlash
`.env.example` faylini nusxa ko'chiring, `.env` deb nomlang:
```
BOT_TOKEN=bu_yerga_tokeningizni_yozing
```

### 5. Ishga tushirish
```bash
npm run dev
```

## Guruhga qo'shish

1. Botni guruhingizga qo'shing
2. Botni **admin** qiling, quyidagi huquqlarni bering:
   - ✅ Xabarlarni o'chirish
   - ✅ Foydalanuvchilarni ban qilish
3. Guruhda `/start` yozing

## Admin buyruqlari

| Buyruq | Vazifasi |
|--------|---------|
| `/status` | Bot holati |
| `/warn` | Xabarga reply qilib — ogohlantirish |
| `/reset` | Xabarga reply qilib — ogohlantirishlarni tozalash |

## Sozlamalar

`src/bot.ts` faylini oching:
- `MAX_WARNINGS` — necha ogohlantirishdan keyin ban (hozir: 3)
- `SPAM_PATTERNS` — qaysi so'zlar/havolalar spam hisoblanadi

## Bot nima qiladi

| Holat | Harakat |
|-------|---------|
| Havola (link) yuborilsa | O'chiriladi + ogohlantirish |
| Kanal forward qilinsa | O'chiriladi + ogohlantirish |
| Reklama matni bo'lsa | O'chiriladi + ogohlantirish |
| 3 ta ogohlantirish | Guruhdan ban |
| Admin yuborsa | Hech narsa qilinmaydi |
