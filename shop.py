SHOP_ITEMS = [
    {
        "id": 1,
        "name": "🏅 Bronza nishon",
        "desc": "Profilingizda bronza nishon ko'rsatiladi",
        "price": 80,
        "type": "badge",
        "consumable": False,
        "badge_text": "🏅",
    },
    {
        "id": 2,
        "name": "🥈 Kumush nishon",
        "desc": "Profilingizda kumush nishon ko'rsatiladi",
        "price": 200,
        "type": "badge",
        "consumable": False,
        "badge_text": "🥈",
    },
    {
        "id": 3,
        "name": "🥇 Oltin nishon",
        "desc": "Profilingizda oltin nishon ko'rsatiladi",
        "price": 450,
        "type": "badge",
        "consumable": False,
        "badge_text": "🥇",
    },
    {
        "id": 4,
        "name": "💎 Olmosli nishon",
        "desc": "Profilingizda olmosli nishon ko'rsatiladi",
        "price": 900,
        "type": "badge",
        "consumable": False,
        "badge_text": "💎",
    },
    {
        "id": 5,
        "name": "👑 Qirol toji",
        "desc": "Eng noyob unvon — faqat chempionlar uchun!",
        "price": 2500,
        "type": "badge",
        "consumable": False,
        "badge_text": "👑",
    },
    {
        "id": 6,
        "name": "🎭 Mafia Ustasi unvoni",
        "desc": "Profilingizda 'Mafia Ustasi' unvoni ko'rinadi",
        "price": 350,
        "type": "title",
        "consumable": False,
        "title_text": "🎭 Mafia Ustasi",
    },
    {
        "id": 7,
        "name": "🔍 Sherif Ustasi unvoni",
        "desc": "Profilingizda 'Sherif Ustasi' unvoni ko'rinadi",
        "price": 350,
        "type": "title",
        "consumable": False,
        "title_text": "🔍 Sherif Ustasi",
    },
    {
        "id": 8,
        "name": "🛡️ Himoya qalqoni",
        "desc": "Bir tun uchun: mafia hujumidan himoya (1 martalik)",
        "price": 120,
        "type": "shield",
        "consumable": True,
    },
    {
        "id": 9,
        "name": "🎲 Omad kubigi",
        "desc": "50% ehtimollik bilan o'ldirish hujumidan omon qolish (1 martalik)",
        "price": 60,
        "type": "lucky",
        "consumable": True,
    },
    {
        "id": 10,
        "name": "💊 Tibbiy komplet",
        "desc": "Tun davrida bir kishini davolash (Doktor kabi, 1 martalik)",
        "price": 110,
        "type": "medkit",
        "consumable": True,
    },
    {
        "id": 11,
        "name": "🔮 Yashirin niqob",
        "desc": "Bu o'yinda rollingiz o'limda oshkor bo'lmaydi (1 martalik)",
        "price": 80,
        "type": "mask",
        "consumable": True,
    },
    {
        "id": 12,
        "name": "🗳️ Qo'shimcha ovoz",
        "desc": "Ovoz berishda 2 ta ovoz berasiz (1 martalik)",
        "price": 70,
        "type": "extra_vote",
        "consumable": True,
    },
    {
        "id": 13,
        "name": "📢 Anonim xabar",
        "desc": "O'yin chatiga anonim xabar yuboring (1 martalik)",
        "price": 50,
        "type": "anon_msg",
        "consumable": True,
    },
    {
        "id": 14,
        "name": "🕵️ Josus komplet",
        "desc": "Bir mafia a'zosining ismini bilib olasiz (1 martalik)",
        "price": 200,
        "type": "spy_kit",
        "consumable": True,
    },
    {
        "id": 15,
        "name": "🧪 Zahar",
        "desc": "Bir o'yinchini zaharla — keyingi tun albatta o'ladi (1 martalik)",
        "price": 180,
        "type": "poison",
        "consumable": True,
    },
    {
        "id": 16,
        "name": "🔔 Xavf signali",
        "desc": "Agar siz tunda nishon bo'lsangiz, oldindan xabar olasiz (1 martalik)",
        "price": 90,
        "type": "alarm",
        "consumable": True,
    },
    {
        "id": 17,
        "name": "🎯 Aniq nishon",
        "desc": "Mafia uchun: bu tun hujum himoyadan o'tadi (1 martalik)",
        "price": 150,
        "type": "precise",
        "consumable": True,
    },
    {
        "id": 18,
        "name": "🎰 Lucky Ticket",
        "desc": "O'yinda kafolatlangan Lucky Event! (1 martalik)",
        "price": 40,
        "type": "lucky_ticket",
        "consumable": True,
    },
    {
        "id": 19,
        "name": "🌟 VIP Status",
        "desc": "Profilingizda VIP belgisi ko'rinadi (doimiy)",
        "price": 600,
        "type": "badge",
        "consumable": False,
        "badge_text": "🌟 VIP",
    },
    {
        "id": 20,
        "name": "💰 Coin paketi x2",
        "desc": "Keyingi g'alaba mukofotini 2 barobar olasiz (1 martalik)",
        "price": 100,
        "type": "coin_boost",
        "consumable": True,
    },
]

ITEM_BY_ID = {item['id']: item for item in SHOP_ITEMS}


def get_item(item_id: int) -> dict | None:
    return ITEM_BY_ID.get(item_id)


def get_user_badge(inventory: list[dict]) -> str:
    """Inventorydan eng yaxshi nishonni qaytaradi"""
    badge_priority = {19: "🌟 VIP", 5: "👑", 4: "💎", 3: "🥇", 2: "🥈", 1: "🏅"}
    owned_ids = {inv['item_id'] for inv in inventory}
    for item_id, badge in badge_priority.items():
        if item_id in owned_ids:
            return badge
    return ""


def get_user_title(inventory: list[dict]) -> str:
    """Inventorydan unvonni qaytaradi"""
    title_items = {6: "🎭 Mafia Ustasi", 7: "🔍 Sherif Ustasi"}
    owned_ids = {inv['item_id'] for inv in inventory}
    for item_id, title in title_items.items():
        if item_id in owned_ids:
            return title
    return ""
