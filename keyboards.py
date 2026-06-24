from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from shop import SHOP_ITEMS, get_item

ITEMS_PER_PAGE = 5


def main_menu_kb(is_admin: bool = False, has_bonus: bool = False) -> InlineKeyboardMarkup:
    buttons = [
        [InlineKeyboardButton(text="🎮 Yangi o'yin", callback_data="menu_newgame"),
         InlineKeyboardButton(text="👤 Profilim", callback_data="menu_profile")],
        [InlineKeyboardButton(text="🏪 Do'kon", callback_data="shop_page_0"),
         InlineKeyboardButton(text="🏆 Reyting", callback_data="menu_top")],
        [InlineKeyboardButton(text="🎲 Mini-O'yinlar", callback_data="mini_games"),
         InlineKeyboardButton(text="🔮 Taqdir bashorat", callback_data="menu_fate")],
        [InlineKeyboardButton(text="📅 Kunlik vazifalar", callback_data="menu_missions"),
         InlineKeyboardButton(text="💡 Bugungi maslahat", callback_data="menu_dailytip")],
        [InlineKeyboardButton(text="🔥 Login seriyasi", callback_data="menu_loginstreak"),
         InlineKeyboardButton(text="💎 Haftalik bonus", callback_data="menu_weeklybonus")],
        [InlineKeyboardButton(text="🤝 Do'stlar", callback_data="menu_friends"),
         InlineKeyboardButton(text="🔍 O'yinchi qidirish", callback_data="menu_findplayer")],
        [InlineKeyboardButton(text="⚙️ Qo'shimcha", callback_data="menu_extra"),
         InlineKeyboardButton(text="❓ Yordam", callback_data="help_main")],
        [InlineKeyboardButton(text="📜 Qoidalar", callback_data="menu_rules")],
    ]
    if has_bonus:
        buttons.append([InlineKeyboardButton(text="🎁 Kunlik bonus olish! (+25💰)", callback_data="menu_dailybonus")])
    if is_admin:
        buttons.append([InlineKeyboardButton(text="👮 Admin panel", callback_data="admin_panel")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def group_main_menu_kb(is_admin: bool = False) -> InlineKeyboardMarkup:
    buttons = [
        [InlineKeyboardButton(text="🎮 Yangi o'yin boshlash", callback_data="menu_newgame")],
        [InlineKeyboardButton(text="🏆 Reyting", callback_data="menu_top"),
         InlineKeyboardButton(text="❓ Yordam", callback_data="help_main")],
        [InlineKeyboardButton(text="📜 Qoidalar", callback_data="menu_rules")],
    ]
    if is_admin:
        buttons.append([InlineKeyboardButton(text="👮 Admin panel", callback_data="group_admin_panel")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


# ==================== ADMIN KEYBOARDS ====================

def admin_panel_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📊 Statistika", callback_data="admin_stats"),
         InlineKeyboardButton(text="🚫 Ban ro'yxat", callback_data="admin_banlist")],
        [InlineKeyboardButton(text="🛑 O'yinni to'xtat", callback_data="admin_stop"),
         InlineKeyboardButton(text="💰 Coin berish", callback_data="admin_addcoins")],
        [InlineKeyboardButton(text="⚙️ Kengaytirilgan panel", callback_data="admin_extra_panel")],
        [InlineKeyboardButton(text="🔙 Orqaga", callback_data="menu_back")],
    ])


def group_admin_panel_kb(has_active_game: bool = False, game_waiting: bool = False) -> InlineKeyboardMarkup:
    buttons = []
    if has_active_game:
        buttons.append([InlineKeyboardButton(text="🛑 O'yinni to'xtatish", callback_data="gadmin_stop")])
    if game_waiting:
        buttons.append([InlineKeyboardButton(text="🤖 Bot qo'shish", callback_data="gadmin_addbots")])
    buttons.append([InlineKeyboardButton(text="🚫 Foydalanuvchi ban qilish", callback_data="gadmin_ban_menu")])
    buttons.append([InlineKeyboardButton(text="✅ Blokdan chiqarish", callback_data="gadmin_unban_menu")])
    buttons.append([InlineKeyboardButton(text="📊 Top o'yinchilar", callback_data="gadmin_top"),
                    InlineKeyboardButton(text="⚙️ Sozlamalar", callback_data="gadmin_settings")])
    buttons.append([InlineKeyboardButton(text="❌ Yopish", callback_data="gadmin_close")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def add_bots_count_kb() -> InlineKeyboardMarkup:
    buttons = []
    row = []
    for i in range(1, 11):
        row.append(InlineKeyboardButton(text=str(i), callback_data=f"addbots_{i}"))
        if len(row) == 5:
            buttons.append(row)
            row = []
    if row:
        buttons.append(row)
    buttons.append([InlineKeyboardButton(text="🔙 Orqaga", callback_data="group_admin_panel")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def ban_players_kb(players: list) -> InlineKeyboardMarkup:
    buttons = []
    for p in players:
        buttons.append([InlineKeyboardButton(
            text=f"🚫 {p['name']}",
            callback_data=f"gadmin_ban_{p['id']}_{p['name'][:20]}"
        )])
    buttons.append([InlineKeyboardButton(text="🔙 Orqaga", callback_data="group_admin_panel")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def ban_reason_kb(target_id: int) -> InlineKeyboardMarkup:
    reasons = [
        ("🤬 Haqorat", "haqorat"),
        ("🎭 Aldash/Spam", "spam"),
        ("🔞 Noma'qul xatti-harakat", "nomaqul"),
        ("🚫 Qoidabuzarlik", "qoidabuzarlik"),
        ("📝 Boshqa sabab", "boshqa"),
    ]
    buttons = []
    for label, reason_key in reasons:
        buttons.append([InlineKeyboardButton(
            text=label,
            callback_data=f"gadmin_banreason_{target_id}_{reason_key}"
        )])
    buttons.append([InlineKeyboardButton(text="🔙 Orqaga", callback_data="gadmin_ban_menu")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def confirm_ban_kb(target_id: int, reason: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(text="✅ Ha, banla", callback_data=f"gadmin_confirmban_{target_id}_{reason}"),
        InlineKeyboardButton(text="❌ Bekor", callback_data="gadmin_ban_menu")
    ]])


def unban_list_kb(banned: list) -> InlineKeyboardMarkup:
    buttons = []
    for uid, name, reason, _ in banned:
        short_name = name[:20] if name else f"ID:{uid}"
        short_reason = reason[:12] + "..." if len(reason) > 12 else reason
        buttons.append([InlineKeyboardButton(
            text=f"✅ {short_name} ({short_reason})",
            callback_data=f"gadmin_unban_{uid}"
        )])
    buttons.append([InlineKeyboardButton(text="🔙 Orqaga", callback_data="group_admin_panel")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def confirm_stop_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(text="🛑 Ha, to'xtat", callback_data="gadmin_confirmstop"),
        InlineKeyboardButton(text="❌ Bekor", callback_data="group_admin_panel")
    ]])


# ==================== HELP KEYBOARDS ====================

def help_menu_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🎮 Qanday o'ynash", callback_data="help_howto")],
        [InlineKeyboardButton(text="🎭 Rollar tavsifi", callback_data="help_roles")],
        [InlineKeyboardButton(text="🏪 Do'kon narsalari", callback_data="help_shop")],
        [InlineKeyboardButton(text="💰 Coin tizimi", callback_data="help_coins")],
        [InlineKeyboardButton(text="🔙 Orqaga", callback_data="menu_back")],
    ])


def help_back_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔙 Yordam menyusiga", callback_data="help_main")]
    ])


# ==================== GAME KEYBOARDS ====================

def join_game_kb(player_count: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=f"➕ Qo'shilish ({player_count} kishi)", callback_data="join_game"),
         InlineKeyboardButton(text="➖ Chiqish", callback_data="leave_game")],
        [InlineKeyboardButton(text="▶️ Hozir boshlash (Admin)", callback_data="force_start")],
        [InlineKeyboardButton(text="🤖 Bot qo'shish (Admin)", callback_data="gadmin_addbots")],
    ])


def vote_kb(players: list, voter_id: int, extra_vote_users: set) -> InlineKeyboardMarkup:
    buttons = []
    for p in players:
        if p['id'] != voter_id:
            buttons.append([InlineKeyboardButton(
                text=f"🗳️ {p['name']}",
                callback_data=f"vote_{p['id']}"
            )])
    buttons.append([InlineKeyboardButton(text="🚫 O'tkazib yuborish", callback_data="vote_skip")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def night_target_kb(players: list, action: str, exclude_id: int = None) -> InlineKeyboardMarkup:
    buttons = []
    for p in players:
        if exclude_id and p['id'] == exclude_id:
            continue
        buttons.append([InlineKeyboardButton(
            text=f"🎯 {p['name']}",
            callback_data=f"{action}_{p['id']}"
        )])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


# ==================== SHOP KEYBOARDS ====================

def shop_page_kb(page: int, user_id: int) -> InlineKeyboardMarkup:
    import database as db
    inventory = db.get_inventory(user_id)
    owned_ids = {inv['item_id'] for inv in inventory}

    start = page * ITEMS_PER_PAGE
    end = start + ITEMS_PER_PAGE
    page_items = SHOP_ITEMS[start:end]
    total_pages = (len(SHOP_ITEMS) + ITEMS_PER_PAGE - 1) // ITEMS_PER_PAGE

    buttons = []
    for item in page_items:
        owned_mark = "✅ " if item['id'] in owned_ids and not item.get('consumable') else ""
        qty = next((inv['quantity'] for inv in inventory if inv['item_id'] == item['id']), 0)
        qty_mark = f" [{qty}]" if item.get('consumable') and qty > 0 else ""
        buttons.append([InlineKeyboardButton(
            text=f"{owned_mark}{item['name']} — {item['price']}💰{qty_mark}",
            callback_data=f"shop_item_{item['id']}"
        )])

    nav = []
    if page > 0:
        nav.append(InlineKeyboardButton(text="⬅️", callback_data=f"shop_page_{page - 1}"))
    nav.append(InlineKeyboardButton(text=f"{page + 1}/{total_pages}", callback_data="shop_noop"))
    if end < len(SHOP_ITEMS):
        nav.append(InlineKeyboardButton(text="➡️", callback_data=f"shop_page_{page + 1}"))
    buttons.append(nav)
    buttons.append([InlineKeyboardButton(text="🔙 Orqaga", callback_data="menu_back")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def shop_item_kb(item_id: int, page: int, user_id: int) -> InlineKeyboardMarkup:
    import database as db
    user = db.get_user(user_id)
    item = get_item(item_id)
    inventory = db.get_inventory(user_id)

    owned = any(inv['item_id'] == item_id for inv in inventory)
    already_owned_permanent = owned and not item.get('consumable')
    can_buy = user and user['coins'] >= item['price']

    buttons = []
    if already_owned_permanent:
        buttons.append([InlineKeyboardButton(text="✅ Allaqachon sotib olingan", callback_data="shop_noop")])
    elif can_buy:
        buttons.append([InlineKeyboardButton(
            text=f"💰 Sotib olish ({item['price']} coin)",
            callback_data=f"shop_buy_{item_id}"
        )])
    else:
        buttons.append([InlineKeyboardButton(text="❌ Mablag' yetarli emas", callback_data="shop_noop")])

    buttons.append([InlineKeyboardButton(text="🔙 Do'konga qaytish", callback_data=f"shop_page_{page}")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


# ==================== MINI-GAMES ====================

def mini_games_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🎰 Rulet", callback_data="mini_rulet"),
         InlineKeyboardButton(text="✊ Tosh-Qaychi-Qog'oz", callback_data="mini_tqq")],
        [InlineKeyboardButton(text="🃏 Blackjack (21)", callback_data="mini_blackjack"),
         InlineKeyboardButton(text="🎁 Sirli quticha", callback_data="mini_secretbox")],
        [InlineKeyboardButton(text="🎪 Spinning Wheel", callback_data="mini_wheel"),
         InlineKeyboardButton(text="🎯 Duello", callback_data="mini_duello")],
        [InlineKeyboardButton(text="💰 Jackpot", callback_data="mini_jackpot"),
         InlineKeyboardButton(text="🔮 Bugun omad", callback_data="mini_luck")],
        [InlineKeyboardButton(text="🎁 Coin sovg'a", callback_data="mini_sovga"),
         InlineKeyboardButton(text="🏆 Assassin TOP", callback_data="mini_killtop")],
        [InlineKeyboardButton(text="🔙 Orqaga", callback_data="menu_back")],
    ])


def rulet_bet_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="10 💰", callback_data="rulet_10"),
         InlineKeyboardButton(text="25 💰", callback_data="rulet_25"),
         InlineKeyboardButton(text="50 💰", callback_data="rulet_50")],
        [InlineKeyboardButton(text="100 💰", callback_data="rulet_100"),
         InlineKeyboardButton(text="250 💰", callback_data="rulet_250"),
         InlineKeyboardButton(text="500 💰", callback_data="rulet_500")],
        [InlineKeyboardButton(text="🔙 Orqaga", callback_data="mini_games")],
    ])


def tqq_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✊ Tosh", callback_data="tqq_tosh"),
         InlineKeyboardButton(text="✌️ Qaychi", callback_data="tqq_qaychi"),
         InlineKeyboardButton(text="🖐 Qog'oz", callback_data="tqq_qogoz")],
        [InlineKeyboardButton(text="🔙 Orqaga", callback_data="mini_games")],
    ])


def tqq_bet_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="10 💰", callback_data="tqqbet_10"),
         InlineKeyboardButton(text="25 💰", callback_data="tqqbet_25"),
         InlineKeyboardButton(text="50 💰", callback_data="tqqbet_50")],
        [InlineKeyboardButton(text="Pulisiz o'ynash", callback_data="tqqbet_0")],
        [InlineKeyboardButton(text="🔙 Orqaga", callback_data="mini_games")],
    ])


def top_type_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🏆 Umumiy TOP", callback_data="menu_top"),
         InlineKeyboardButton(text="🗡️ Assassin TOP", callback_data="mini_killtop")],
        [InlineKeyboardButton(text="🔙 Orqaga", callback_data="mini_games")],
    ])


def game_settings_kb(settings: dict) -> InlineKeyboardMarkup:
    jt = settings['join_time']
    nt = settings['night_time']
    dt = settings['discuss_time']
    vt = settings['vote_time']
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=f"⏱ Qo'shilish: {jt}s", callback_data="gset_join"),
         InlineKeyboardButton(text=f"🌙 Tun: {nt}s", callback_data="gset_night")],
        [InlineKeyboardButton(text=f"☀️ Kun: {dt}s", callback_data="gset_discuss"),
         InlineKeyboardButton(text=f"🗳️ Ovoz: {vt}s", callback_data="gset_vote")],
        [InlineKeyboardButton(text="🔄 Standartga qaytarish", callback_data="gset_reset")],
        [InlineKeyboardButton(text="🔙 Orqaga", callback_data="group_admin_panel")],
    ])


def gset_time_kb(key: str) -> InlineKeyboardMarkup:
    options = {
        'join': [('30s', 30), ('45s', 45), ('60s', 60), ('90s', 90), ('120s', 120)],
        'night': [('25s', 25), ('40s', 40), ('60s', 60), ('90s', 90)],
        'discuss': [('60s', 60), ('90s', 90), ('120s', 120), ('180s', 180)],
        'vote': [('30s', 30), ('45s', 45), ('60s', 60), ('90s', 90)],
    }
    choices = options.get(key, [])
    buttons = [[InlineKeyboardButton(text=label, callback_data=f"gset_{key}_{val}") for label, val in choices]]
    buttons.append([InlineKeyboardButton(text="🔙 Orqaga", callback_data="gadmin_settings")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def fate_result_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔄 Yana bir bor", callback_data="menu_fate")],
        [InlineKeyboardButton(text="🔙 Orqaga", callback_data="menu_back")],
    ])


def streak_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="👤 Profilim", callback_data="menu_profile"),
         InlineKeyboardButton(text="🔙 Orqaga", callback_data="menu_back")],
    ])


# ==================== BLACKJACK ====================

def blackjack_bet_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="10 💰", callback_data="bj_bet_10"),
         InlineKeyboardButton(text="25 💰", callback_data="bj_bet_25"),
         InlineKeyboardButton(text="50 💰", callback_data="bj_bet_50")],
        [InlineKeyboardButton(text="100 💰", callback_data="bj_bet_100"),
         InlineKeyboardButton(text="250 💰", callback_data="bj_bet_250")],
        [InlineKeyboardButton(text="🔙 Orqaga", callback_data="mini_games")],
    ])


def blackjack_play_kb(total: int, can_double: bool = False) -> InlineKeyboardMarkup:
    row = [InlineKeyboardButton(text="🃏 Hit (Yana karta)", callback_data="bj_hit"),
           InlineKeyboardButton(text="🛑 Stand (To'xta)", callback_data="bj_stand")]
    buttons = [row]
    if can_double:
        buttons.append([InlineKeyboardButton(text="💥 Double Down (2x tikish)", callback_data="bj_double")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


# ==================== SIRLI QUTICHA ====================

def sirli_quticha_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📦 Kichik quticha (50 💰)", callback_data="box_50"),
         InlineKeyboardButton(text="📦 O'rta quticha (100 💰)", callback_data="box_100")],
        [InlineKeyboardButton(text="💎 Katta quticha (200 💰)", callback_data="box_200")],
        [InlineKeyboardButton(text="🔙 Orqaga", callback_data="mini_games")],
    ])


# ==================== SPINNING WHEEL ====================

def spinning_wheel_kb(jackpot_amount: int = 100) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=f"🎪 Aylantirgich (20 💰) | Jackpot: {jackpot_amount}💰",
                              callback_data="wheel_spin")],
        [InlineKeyboardButton(text="🔙 Orqaga", callback_data="mini_games")],
    ])


# ==================== DUELLO ====================

def duello_bet_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="20 💰", callback_data="duel_bet_20"),
         InlineKeyboardButton(text="50 💰", callback_data="duel_bet_50"),
         InlineKeyboardButton(text="100 💰", callback_data="duel_bet_100")],
        [InlineKeyboardButton(text="200 💰", callback_data="duel_bet_200"),
         InlineKeyboardButton(text="500 💰", callback_data="duel_bet_500")],
        [InlineKeyboardButton(text="🔙 Orqaga", callback_data="mini_games")],
    ])


# ==================== JACKPOT ====================

def jackpot_kb(amount: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=f"🎰 Jackpotda ishtirok (50 💰) | Fond: {amount}💰",
                              callback_data="jackpot_play")],
        [InlineKeyboardButton(text="🔙 Orqaga", callback_data="mini_games")],
    ])


# ==================== DAILY MISSIONS ====================

def daily_missions_kb(games_done: int, rulet_done: int, bonus_done: int) -> InlineKeyboardMarkup:
    g = "✅" if games_done >= 1 else f"🎯 {games_done}/1"
    r = "✅" if rulet_done >= 2 else f"🎯 {rulet_done}/2"
    b = "✅" if bonus_done >= 1 else f"🎯 {bonus_done}/1"
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=f"{g} Vazifa 1: O'yin o'yna → +30💰", callback_data="dm_claim_1")],
        [InlineKeyboardButton(text=f"{r} Vazifa 2: Rulet x2 → +20💰", callback_data="dm_claim_2")],
        [InlineKeyboardButton(text=f"{b} Vazifa 3: Bonusni ol → +10💰", callback_data="dm_claim_3")],
        [InlineKeyboardButton(text="🔙 Orqaga", callback_data="menu_back")],
    ])


# ==================== FRIENDS ====================

def friends_menu_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="➕ Do'st qo'shish", callback_data="friend_add"),
         InlineKeyboardButton(text="👥 Do'stlarim", callback_data="friend_list")],
        [InlineKeyboardButton(text="🔙 Orqaga", callback_data="menu_back")],
    ])


# ==================== EMOJI FRAME ====================

PROFILE_EMOJIS = ['🎭', '🐺', '🦁', '🦅', '🔥', '⚡', '👑', '💎', '🌟', '🎯']

def emoji_frame_kb() -> InlineKeyboardMarkup:
    rows = []
    for i in range(0, len(PROFILE_EMOJIS), 5):
        row = [InlineKeyboardButton(text=e, callback_data=f"emoji_{e}")
               for e in PROFILE_EMOJIS[i:i+5]]
        rows.append(row)
    rows.append([InlineKeyboardButton(text="🔙 Orqaga", callback_data="menu_back")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


# ==================== FAVORITE ROLE ====================

def fav_role_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔴 Mafia", callback_data="favrol_mafia"),
         InlineKeyboardButton(text="👮 Sherif", callback_data="favrol_sheriff")],
        [InlineKeyboardButton(text="💚 Shifokor", callback_data="favrol_doctor"),
         InlineKeyboardButton(text="🕵️ Josus", callback_data="favrol_spy")],
        [InlineKeyboardButton(text="👤 Fuqaro", callback_data="favrol_civilian"),
         InlineKeyboardButton(text="🃏 Jokker", callback_data="favrol_joker")],
        [InlineKeyboardButton(text="🔙 Orqaga", callback_data="menu_back")],
    ])


# ==================== PROFILE EXTRA ====================

def profile_extra_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📝 Bio o'rnatish", callback_data="profile_setbio"),
         InlineKeyboardButton(text="🌈 Ramka tanlash", callback_data="profile_emoji")],
        [InlineKeyboardButton(text="🌟 Sevimli rol", callback_data="profile_favrol"),
         InlineKeyboardButton(text="🤝 Do'stlar", callback_data="menu_friends")],
        [InlineKeyboardButton(text="📊 Batafsil statistika", callback_data="profile_stats"),
         InlineKeyboardButton(text="🎮 Rekordlarim", callback_data="profile_records")],
        [InlineKeyboardButton(text="🔙 Orqaga", callback_data="menu_back")],
    ])


# ==================== ADMIN EXTRA ====================

def admin_extra_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📢 E'lon yuborish", callback_data="admin_announce"),
         InlineKeyboardButton(text="🎊 2x Coin kuni", callback_data="admin_double")],
        [InlineKeyboardButton(text="⚡ Tez o'yin rejimi", callback_data="admin_speedmode"),
         InlineKeyboardButton(text="👥 Guruh statistikasi", callback_data="admin_groupstats")],
        [InlineKeyboardButton(text="🔙 Orqaga", callback_data="admin_panel")],
    ])


# ==================== MISC ====================

def back_kb(callback_data: str = "menu_back") -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔙 Orqaga", callback_data=callback_data)]
    ])
