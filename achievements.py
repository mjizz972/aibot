ACHIEVEMENTS = [
    {
        "id": 1,
        "name": "🎮 Birinchi qadam",
        "desc": "Birinchi o'yiningizni o'ynading",
        "reward": 10,
        "check": lambda u: u['games_played'] >= 1,
    },
    {
        "id": 2,
        "name": "🏆 G'olib",
        "desc": "Birinchi marta g'alaba qozonding",
        "reward": 30,
        "check": lambda u: u['games_won'] >= 1,
    },
    {
        "id": 3,
        "name": "🔫 Qotil",
        "desc": "Jami 5 ta o'yinchini o'ldirding",
        "reward": 50,
        "check": lambda u: u['kills'] >= 5,
    },
    {
        "id": 4,
        "name": "💀 Jasur",
        "desc": "10 ta o'yinda o'lding (mard jangchi!)",
        "reward": 20,
        "check": lambda u: u['deaths'] >= 10,
    },
    {
        "id": 5,
        "name": "🎭 Mafia Afsonasi",
        "desc": "Mafia sifatida 10 ta o'yin o'ynading",
        "reward": 80,
        "check": lambda u: u['mafia_games'] >= 10,
    },
    {
        "id": 6,
        "name": "🔍 Sherif Afsonasi",
        "desc": "Sherif sifatida 10 ta o'yin o'ynading",
        "reward": 80,
        "check": lambda u: u['sheriff_games'] >= 10,
    },
    {
        "id": 7,
        "name": "🎯 Ishonchli",
        "desc": "50% dan yuqori win rate bilan 10 ta o'yin",
        "reward": 100,
        "check": lambda u: u['games_played'] >= 10 and (u['games_won'] / u['games_played']) >= 0.5,
    },
    {
        "id": 8,
        "name": "⚡ Veteran",
        "desc": "Jami 25 ta o'yin o'ynading",
        "reward": 150,
        "check": lambda u: u['games_played'] >= 25,
    },
    {
        "id": 9,
        "name": "💎 Chempion",
        "desc": "Jami 20 ta g'alaba qozonding",
        "reward": 200,
        "check": lambda u: u['games_won'] >= 20,
    },
    {
        "id": 10,
        "name": "👑 Legenda",
        "desc": "Jami 50 ta o'yin o'ynading",
        "reward": 500,
        "check": lambda u: u['games_played'] >= 50,
    },
]

ACHIEVEMENT_BY_ID = {a['id']: a for a in ACHIEVEMENTS}


def get_achievement(ach_id: int) -> dict | None:
    return ACHIEVEMENT_BY_ID.get(ach_id)


def check_new_achievements(user_data: dict, owned_ids: set) -> list[dict]:
    """Yangi ochilgan yutuqlarni qaytaradi"""
    new_ones = []
    for ach in ACHIEVEMENTS:
        if ach['id'] not in owned_ids:
            try:
                if ach['check'](user_data):
                    new_ones.append(ach)
            except Exception:
                pass
    return new_ones
