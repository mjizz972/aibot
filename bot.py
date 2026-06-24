import asyncio
import logging
import random
from datetime import datetime

from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.types import CallbackQuery, ChatPermissions, Message
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup

from config import (
    BOT_TOKEN, ADMIN_IDS, JOIN_TIME, DISCUSS_TIME, VOTE_TIME,
    NIGHT_TIME, MIN_PLAYERS, MAX_PLAYERS, WIN_COINS, SURVIVE_BONUS, KILL_BONUS
)
from game import MafiaGame, GameState, Role, MAFIA_ROLES, ROLE_EMOJI
from messages import (
    get_role_message, get_role_emoji, WINNER_MESSAGES, RULES_TEXT,
    HELP_HOW_TO_PLAY, HELP_ROLES, HELP_SHOP
)
from keyboards import (
    main_menu_kb, group_main_menu_kb, join_game_kb,
    vote_kb, night_target_kb, shop_page_kb, shop_item_kb,
    admin_panel_kb, back_kb, help_menu_kb, help_back_kb,
    group_admin_panel_kb, ban_players_kb, ban_reason_kb,
    confirm_ban_kb, unban_list_kb, confirm_stop_kb,
    add_bots_count_kb,
    mini_games_kb, rulet_bet_kb, tqq_kb, tqq_bet_kb,
    game_settings_kb, gset_time_kb, fate_result_kb, streak_kb,
    blackjack_bet_kb, blackjack_play_kb,
    sirli_quticha_kb, spinning_wheel_kb, duello_bet_kb,
    jackpot_kb, daily_missions_kb, friends_menu_kb,
    emoji_frame_kb, fav_role_kb, profile_extra_kb,
    admin_extra_kb, PROFILE_EMOJIS
)
from shop import get_item, get_user_badge, get_user_title, SHOP_ITEMS
from achievements import ACHIEVEMENTS, check_new_achievements, get_achievement
import database as db

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher(storage=MemoryStorage())

games: dict[int, MafiaGame] = {}

# user_id → chat_id: o'yin davomida mafia chatini aniqlash uchun
user_game_map: dict[int, int] = {}

# Oxirgi so'z kutayotgan o'yinchilar: user_id → (chat_id, name)
last_words_pending: dict[int, tuple] = {}

# ==================== BOT PLAYERS ====================

BOT_NAMES = [
    "Alibek", "Jasur", "Dilnoza", "Sherzod", "Nilufar",
    "Bobur", "Malika", "Sardor", "Zulfiya", "Kamol",
    "Feruza", "Ulugbek", "Shahnoza", "Mirzo", "Mohira",
    "Jahongir", "Barno", "Firdavs", "Munira", "Sanjar",
    "Hamza", "Lola", "Doniyor", "Nasiba", "Ibrohim",
]

_bot_id_counter = -100000

# chat_id → join xabar message_id (botlar qo'shilganda yangilash uchun)
join_messages: dict[int, int] = {}


def _next_bot_id() -> int:
    global _bot_id_counter
    _bot_id_counter -= 1
    return _bot_id_counter


def is_bot_player(user_id: int) -> bool:
    return user_id < 0


class BotStates(StatesGroup):
    waiting_addcoins_id = State()
    waiting_addcoins_amount = State()
    waiting_anon_msg = State()
    waiting_last_words = State()
    waiting_sovga_id = State()
    waiting_sovga_amount = State()
    waiting_tqq_choice = State()
    # Yangi holatlar
    waiting_bio = State()
    waiting_announce_target = State()
    waiting_announce_text = State()
    waiting_find_player = State()
    waiting_duello_id = State()
    waiting_duello_amount = State()
    waiting_friend_id = State()
    # Blackjack holi
    bj_playing = State()


# Globallarga: double event, speed mode
_double_event_chats: set = set()
_speed_mode_chats: set = set()

# Blackjack o'yinlari: user_id → {'bet', 'player_cards', 'dealer_cards'}
_bj_sessions: dict = {}


# ==================== HELPERS ====================

def is_admin(user_id: int) -> bool:
    return user_id in ADMIN_IDS


async def mute_user(chat_id: int, user_id: int):
    try:
        await bot.restrict_chat_member(
            chat_id, user_id,
            permissions=ChatPermissions(can_send_messages=False)
        )
    except Exception as e:
        logger.warning(f"Mute xatosi {user_id}: {e}")


async def unmute_user(chat_id: int, user_id: int):
    try:
        await bot.restrict_chat_member(
            chat_id, user_id,
            permissions=ChatPermissions(
                can_send_messages=True,
                can_send_media_messages=True,
                can_send_other_messages=True,
                can_add_web_page_previews=True
            )
        )
    except Exception as e:
        logger.warning(f"Unmute xatosi {user_id}: {e}")


async def unmute_all(chat_id: int, game: MafiaGame):
    for p in game.players:
        await unmute_user(chat_id, p['id'])


async def safe_dm(user_id: int, text: str, **kwargs) -> bool:
    try:
        await bot.send_message(user_id, text, **kwargs)
        return True
    except Exception:
        return False


def format_player_list(players: list) -> str:
    return "\n".join([f"  {i+1}. {p['name']}" for i, p in enumerate(players)])


def format_alive_list(players: list) -> str:
    alive = [p for p in players if p['alive']]
    return "\n".join([f"  • {p['name']}" for p in alive])


async def notify_achievements(user_id: int, chat_id: int = None):
    """Yangi yutuqlarni tekshiradi va xabar beradi"""
    user_data = db.get_user(user_id)
    if not user_data:
        return
    owned = db.get_user_achievements(user_id)
    new_achs = check_new_achievements(user_data, owned)
    for ach in new_achs:
        db.add_achievement(user_id, ach['id'])
        if ach['reward'] > 0:
            db.update_stat(user_id, coins=ach['reward'])
        await safe_dm(
            user_id,
            f"🏆 <b>YANGI YUTUQ!</b>\n\n"
            f"{ach['name']}\n"
            f"<i>{ach['desc']}</i>\n\n"
            f"{'💰 Mukofot: +' + str(ach['reward']) + ' coin!' if ach['reward'] > 0 else ''}",
            parse_mode="HTML"
        )


# ==================== START & MAIN MENU ====================

@dp.message(Command("bekor"))
async def cmd_bekor(message: Message, state: FSMContext):
    current = await state.get_state()
    if current:
        await state.clear()
        await message.answer("✅ Amal bekor qilindi.")
    else:
        await message.answer("ℹ️ Bekor qilish uchun hech narsa yo'q.")


@dp.message(Command("start"))
async def cmd_start(message: Message):
    user = message.from_user
    db.ensure_user(user.id, user.full_name)

    if message.chat.type == "private":
        inv = db.get_inventory(user.id)
        badge = get_user_badge(inv)
        user_data = db.get_user(user.id)

        # Kunlik bonus tekshirish
        bonus_text = ""
        if db.can_claim_bonus(user.id):
            bonus_text = "\n\n🎁 <b>Kunlik bonus tayyor!</b> Quyidagi tugmani bosing!"

        await message.answer(
            f"🎭 <b>MAFIA BOT</b> {badge}\n\n"
            f"Salom, <b>{user.full_name}</b>!\n"
            f"💰 Coinlaringiz: <b>{user_data['coins']}</b>{bonus_text}\n\n"
            f"Quyidagi menyudan tanlang:",
            parse_mode="HTML",
            reply_markup=main_menu_kb(is_admin(user.id), db.can_claim_bonus(user.id))
        )
        # Yutuqlarni tekshir
        await notify_achievements(user.id)
    else:
        await message.answer(
            "🎭 <b>MAFIA BOT</b>\n\n"
            "Quyidagi menyudan tanlang:",
            parse_mode="HTML",
            reply_markup=group_main_menu_kb(is_admin(user.id))
        )


@dp.callback_query(F.data == "menu_back")
async def cb_menu_back(callback: CallbackQuery):
    user = callback.from_user
    db.ensure_user(user.id, user.full_name)
    inv = db.get_inventory(user.id)
    badge = get_user_badge(inv)
    user_data = db.get_user(user.id)
    bonus_text = ""
    if db.can_claim_bonus(user.id):
        bonus_text = "\n\n🎁 <b>Kunlik bonus tayyor!</b>"
    await callback.message.edit_text(
        f"🎭 <b>MAFIA BOT</b> {badge}\n\n"
        f"Salom, <b>{user.full_name}</b>!\n"
        f"💰 Coinlaringiz: <b>{user_data['coins']}</b>{bonus_text}\n\n"
        f"Quyidagi menyudan tanlang:",
        parse_mode="HTML",
        reply_markup=main_menu_kb(is_admin(user.id), db.can_claim_bonus(user.id))
    )
    await callback.answer()


# ==================== DAILY BONUS ====================

@dp.callback_query(F.data == "menu_dailybonus")
async def cb_daily_bonus(callback: CallbackQuery):
    user = callback.from_user
    db.ensure_user(user.id, user.full_name)

    # Streak hisoblash (oddiy: har kuni +5 bonus bonus)
    user_data = db.get_user(user.id)
    base = 25
    bonus_amount = base

    if db.claim_bonus(user.id, bonus_amount):
        # Kunlik vazifa: bonus_done
        db.update_daily_mission(user.id, 'bonus_done')
        # Login seriyasi
        login_streak, is_new_login = db.update_login_streak(user.id)
        user_data = db.get_user(user.id)
        login_note = ""
        if is_new_login:
            if login_streak % 7 == 0:
                extra = 50; db.add_coins(user.id, extra)
                login_note = f"\n🎊 7 kunlik login seriyasi! +{extra}💰 bonus!"
            elif login_streak % 3 == 0:
                extra = 20; db.add_coins(user.id, extra)
                login_note = f"\n🎉 3 kunlik login seriyasi! +{extra}💰 bonus!"
        await callback.message.edit_text(
            f"🎁 <b>KUNLIK BONUS OLINDI!</b>\n\n"
            f"✅ +<b>{bonus_amount} 💰</b> coin qo'shildi!\n\n"
            f"🔥 Login seriyasi: <b>{login_streak}</b> kun{login_note}\n\n"
            f"💰 Jami coinlaringiz: <b>{user_data['coins']}</b>\n\n"
            f"📅 Ertaga yana keling!",
            parse_mode="HTML",
            reply_markup=back_kb("menu_back")
        )
        await callback.answer(f"🎁 +{bonus_amount} coin!")
    else:
        await callback.answer("⏰ Bugun allaqachon oldingiz! Ertaga keling.", show_alert=True)


# ==================== HELP MENU ====================

@dp.callback_query(F.data == "help_main")
async def cb_help_main(callback: CallbackQuery):
    await callback.message.edit_text(
        "❓ <b>YORDAM MENYUSI</b>\n\nQuyidagilardan birini tanlang:",
        parse_mode="HTML",
        reply_markup=help_menu_kb()
    )
    await callback.answer()


@dp.callback_query(F.data == "help_howto")
async def cb_help_howto(callback: CallbackQuery):
    await callback.message.edit_text(HELP_HOW_TO_PLAY, parse_mode="HTML", reply_markup=help_back_kb())
    await callback.answer()


@dp.callback_query(F.data == "help_roles")
async def cb_help_roles(callback: CallbackQuery):
    await callback.message.edit_text(HELP_ROLES, parse_mode="HTML", reply_markup=help_back_kb())
    await callback.answer()


@dp.callback_query(F.data == "help_shop")
async def cb_help_shop_info(callback: CallbackQuery):
    await callback.message.edit_text(HELP_SHOP, parse_mode="HTML", reply_markup=help_back_kb())
    await callback.answer()


@dp.callback_query(F.data == "help_coins")
async def cb_help_coins(callback: CallbackQuery):
    await callback.message.edit_text(
        "💰 <b>COIN TIZIMI</b>\n\n"
        "<b>Qanday coin olasiz?</b>\n\n"
        "🎊 G'alaba (tinch) → <b>+100 💰</b>\n"
        "🔫 G'alaba (mafia) → <b>+150 💰</b>\n"
        "🏃 Tirik qolish → <b>+30 💰</b>\n"
        "💀 Har bir o'ldirish → <b>+20 💰</b>\n"
        "🎁 Kunlik bonus → <b>+25 💰</b>\n"
        "🏆 Yutuq mukofoti → <b>+10–500 💰</b>\n"
        "💰 Coin paketi x2 aktiv → <b>×2 barcha</b>\n\n"
        "<b>Misol:</b> Mafia, 2 kishi o'ldirdi, tirik qoldi:\n"
        "<code>150 + 30 + (2×20) = 220 💰</code>\n\n"
        "<b>Eng qimmat narsalar:</b>\n"
        "👑 Qirol toji — 2500 💰\n"
        "🌟 VIP Status — 600 💰\n"
        "💎 Olmosli nishon — 900 💰",
        parse_mode="HTML",
        reply_markup=help_back_kb()
    )
    await callback.answer()


# ==================== RULES ====================

@dp.callback_query(F.data == "menu_rules")
async def cb_rules(callback: CallbackQuery):
    await callback.message.edit_text(RULES_TEXT, parse_mode="HTML", reply_markup=back_kb("menu_back"))
    await callback.answer()


# ==================== TOP ====================

@dp.callback_query(F.data == "menu_top")
async def cb_top(callback: CallbackQuery):
    rows = db.get_top(10)
    if not rows:
        await callback.answer("📊 Hali statistika yo'q!", show_alert=True)
        return
    medals = ["🥇", "🥈", "🥉"] + ["🏅"] * 7
    text = "🏆 <b>TOP 10 O'YINCHILAR</b>\n\n"
    for i, (name, played, won, coins, winrate) in enumerate(rows):
        text += f"{medals[i]} <b>{name}</b>\n   {won}/{played} o'yin • {winrate}% • {coins}💰\n"
    await callback.message.edit_text(text, parse_mode="HTML", reply_markup=back_kb("menu_back"))
    await callback.answer()


# ==================== PROFILE & ACHIEVEMENTS ====================

@dp.callback_query(F.data == "menu_profile")
async def cb_profile(callback: CallbackQuery):
    user = callback.from_user
    db.ensure_user(user.id, user.full_name)
    data = db.get_user(user.id)
    inv = db.get_inventory(user.id)
    badge = get_user_badge(inv)
    title = get_user_title(inv)
    owned_achs = db.get_user_achievements(user.id)

    winrate = round(data['games_won'] * 100 / data['games_played'], 1) if data['games_played'] else 0
    title_line = f"\n🏷️ Unvon: <b>{title}</b>" if title else ""
    inv_count = sum(i['quantity'] for i in inv)
    ach_count = len(owned_achs)
    streak = db.get_win_streak(user.id)
    streak_line = f"\n🌟 G'alaba seriyasi: <b>{streak}</b> 🔥" if streak >= 2 else (f"\n🌟 G'alaba seriyasi: <b>{streak}</b>" if streak == 1 else "")

    from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=f"🏆 Yutuqlar ({ach_count}/{len(ACHIEVEMENTS)})", callback_data="menu_achievements")],
        [InlineKeyboardButton(text="🌟 G'alaba seriyasi", callback_data="menu_streak"),
         InlineKeyboardButton(text="🎲 Mini-O'yinlar", callback_data="mini_games")],
        [InlineKeyboardButton(text="🔙 Orqaga", callback_data="menu_back")],
    ])

    await callback.message.edit_text(
        f"👤 <b>{user.full_name}</b> {badge}{title_line}{streak_line}\n\n"
        f"💰 Coinlar: <b>{data['coins']}</b>\n\n"
        f"🎮 O'yinlar: <b>{data['games_played']}</b>\n"
        f"🏆 G'alabalar: <b>{data['games_won']}</b>\n"
        f"📈 Win rate: <b>{winrate}%</b>\n"
        f"💀 O'ldirishlar: <b>{data['kills']}</b>\n"
        f"☠️ O'limlar: <b>{data['deaths']}</b>\n\n"
        f"🎭 Rol statistikasi:\n"
        f"  🔫 Mafia: {data['mafia_games']}ta\n"
        f"  👑 Donn: {data['donn_games']}ta\n"
        f"  🔍 Sherif: {data['sheriff_games']}ta\n"
        f"  💉 Doktor: {data['doctor_games']}ta\n"
        f"  💋 Ayg'oqchi: {data['spy_games']}ta\n\n"
        f"🎒 Inventar: {inv_count} ta narsa\n"
        f"🏆 Yutuqlar: {ach_count}/{len(ACHIEVEMENTS)}",
        parse_mode="HTML",
        reply_markup=kb
    )
    await callback.answer()


@dp.callback_query(F.data == "menu_achievements")
async def cb_achievements(callback: CallbackQuery):
    user = callback.from_user
    owned = db.get_user_achievements(user.id)
    text = "🏆 <b>YUTUQLAR</b>\n\n"
    for ach in ACHIEVEMENTS:
        mark = "✅" if ach['id'] in owned else "🔒"
        reward = f" (+{ach['reward']}💰)" if ach['reward'] > 0 else ""
        text += f"{mark} <b>{ach['name']}</b>{reward}\n<i>  {ach['desc']}</i>\n\n"
    await callback.message.edit_text(text, parse_mode="HTML", reply_markup=back_kb("menu_profile"))
    await callback.answer()


# ==================== GAME CREATION ====================

@dp.callback_query(F.data == "menu_newgame")
async def cb_newgame(callback: CallbackQuery):
    chat_id = callback.message.chat.id
    user = callback.from_user

    if callback.message.chat.type == "private":
        await callback.answer(
            "❌ O'yin faqat guruhda boshlanadi!\nMeni guruhga qo'shing va u yerda boshlang.",
            show_alert=True
        )
        return

    # Faqat adminlar o'yin boshlaydi
    if not is_admin(user.id):
        await callback.answer("❌ Faqat adminlar o'yin boshlashi mumkin!", show_alert=True)
        return

    if db.is_banned(user.id):
        await callback.answer("🚫 Siz bloklanganSIZ!", show_alert=True)
        return

    if chat_id in games and games[chat_id].state not in (GameState.WAITING, GameState.ENDED):
        await callback.answer("⚠️ O'yin ketmoqda! Avval tugashini kuting.", show_alert=True)
        return

    db.ensure_user(user.id, user.full_name)
    game = MafiaGame(chat_id)
    game.add_player(user.id, user.full_name, user.username)
    games[chat_id] = game

    sent = await callback.message.edit_text(
        f"🎭 <b>MAFIA O'YINI — Ro'yxat ochildi!</b>\n\n"
        f"👥 O'yinchilar: <b>1</b>/{MAX_PLAYERS}\n\n"
        f"1. {user.full_name}\n\n"
        f"⏱ Ro'yxat <b>{JOIN_TIME} soniya</b> ochiq\n"
        f"📌 Kamida <b>{MIN_PLAYERS}</b> kishi kerak",
        parse_mode="HTML",
        reply_markup=join_game_kb(1)
    )
    if sent:
        join_messages[chat_id] = sent.message_id
    await callback.answer()
    asyncio.create_task(auto_start_timer(chat_id, game))


async def auto_start_timer(chat_id: int, game: MafiaGame):
    await asyncio.sleep(JOIN_TIME)
    if chat_id in games and games[chat_id] is game and game.state == GameState.WAITING:
        if len(game.players) < MIN_PLAYERS:
            await bot.send_message(
                chat_id,
                f"⏰ Vaqt tugadi! O'yinchilar yetarli emas ({len(game.players)}/{MIN_PLAYERS}).\nO'yin bekor qilindi."
            )
            games.pop(chat_id, None)
        else:
            await start_game(chat_id, game)


@dp.callback_query(F.data == "join_game")
async def cb_join(callback: CallbackQuery):
    chat_id = callback.message.chat.id
    user = callback.from_user

    if db.is_banned(user.id):
        await callback.answer("🚫 Siz bloklanganSIZ!", show_alert=True)
        return
    if chat_id not in games:
        await callback.answer("❌ O'yin topilmadi!", show_alert=True)
        return

    game = games[chat_id]
    if game.state != GameState.WAITING:
        await callback.answer("❌ O'yin boshlangan!", show_alert=True)
        return
    if game.is_player(user.id):
        await callback.answer("✅ Allaqachon qo'shilgansiz!", show_alert=True)
        return
    if len(game.players) >= MAX_PLAYERS:
        await callback.answer(f"❌ To'ldi! (max {MAX_PLAYERS})", show_alert=True)
        return

    db.ensure_user(user.id, user.full_name)
    game.add_player(user.id, user.full_name, user.username)
    count = len(game.players)
    names = format_player_list(game.players)
    try:
        await callback.message.edit_text(
            f"🎭 <b>MAFIA — Ro'yxat</b>\n\n"
            f"👥 O'yinchilar: <b>{count}</b>/{MAX_PLAYERS}\n\n{names}",
            parse_mode="HTML",
            reply_markup=join_game_kb(count)
        )
    except Exception:
        pass
    await callback.answer(f"✅ {user.full_name} qo'shildi!")


@dp.callback_query(F.data == "leave_game")
async def cb_leave(callback: CallbackQuery):
    chat_id = callback.message.chat.id
    user = callback.from_user

    if chat_id not in games:
        await callback.answer("❌ O'yin yo'q!", show_alert=True)
        return
    game = games[chat_id]
    if game.state != GameState.WAITING:
        await callback.answer("❌ O'yin boshlangan, chiqib bo'lmaydi!", show_alert=True)
        return
    if not game.is_player(user.id):
        await callback.answer("❌ Siz ro'yxatda emassiz!", show_alert=True)
        return

    game.remove_player(user.id)
    await callback.answer(f"👋 {user.full_name} chiqdi!")

    if not game.players:
        games.pop(chat_id, None)
        await callback.message.edit_text("❌ Barcha o'yinchilar chiqdi. O'yin bekor qilindi.")
        return

    count = len(game.players)
    names = format_player_list(game.players)
    try:
        await callback.message.edit_text(
            f"🎭 <b>MAFIA — Ro'yxat</b>\n\n"
            f"👥 O'yinchilar: <b>{count}</b>/{MAX_PLAYERS}\n\n{names}",
            parse_mode="HTML",
            reply_markup=join_game_kb(count)
        )
    except Exception:
        pass


@dp.callback_query(F.data == "force_start")
async def cb_force_start(callback: CallbackQuery):
    chat_id = callback.message.chat.id
    user = callback.from_user

    # Faqat adminlar force start qila oladi
    if not is_admin(user.id):
        await callback.answer("❌ Faqat adminlar o'yinni boshlay oladi!", show_alert=True)
        return
    if chat_id not in games:
        await callback.answer("❌ O'yin yo'q!", show_alert=True)
        return
    game = games[chat_id]
    if game.state != GameState.WAITING:
        await callback.answer("❌ O'yin boshlangan!", show_alert=True)
        return
    if len(game.players) < MIN_PLAYERS:
        await callback.answer(f"❌ Kamida {MIN_PLAYERS} kishi kerak! Hozir: {len(game.players)}", show_alert=True)
        return

    await callback.answer()
    await start_game(chat_id, game)


# ==================== GAME START ====================

async def start_game(chat_id: int, game: MafiaGame):
    game.assign_roles()
    game.state = GameState.NIGHT
    join_messages.pop(chat_id, None)

    for p in game.players:
        if is_bot_player(p['id']):
            user_game_map[p['id']] = chat_id
            continue
        db.ensure_user(p['id'], p['name'])
        db.update_stat(p['id'], games_played=1)
        user_game_map[p['id']] = chat_id
        role = p['role']
        if role == Role.MAFIA:
            db.update_stat(p['id'], mafia_games=1)
        elif role == Role.DONN:
            db.update_stat(p['id'], donn_games=1)
        elif role == Role.SHERIFF:
            db.update_stat(p['id'], sheriff_games=1)
        elif role == Role.DOCTOR:
            db.update_stat(p['id'], doctor_games=1)
        elif role == Role.SPY:
            db.update_stat(p['id'], spy_games=1)

        if db.has_item(p['id'], 8):
            game.shield_users.add(p['id'])
        if db.has_item(p['id'], 9):
            game.lucky_users.add(p['id'])
        if db.has_item(p['id'], 12):
            game.extra_vote_users.add(p['id'])
        if db.has_item(p['id'], 16):
            game.alarm_users.add(p['id'])
        if db.has_item(p['id'], 17):
            game.precise_users.add(p['id'])
        if db.has_item(p['id'], 14):
            game.spy_kit_users.add(p['id'])

    failed = []
    for p in game.players:
        if is_bot_player(p['id']):
            continue
        msg = get_role_message(p['role'], game)
        ok = await safe_dm(p['id'], msg, parse_mode="HTML")
        if not ok:
            failed.append(p['name'])

    players_list = format_player_list(game.players)
    warn = ""
    if failed:
        warn = (
            f"\n\n⚠️ Quyidagilar bilan shaxsiy chat yo'q:\n"
            f"<i>{', '.join(failed)}</i>\n(oldin botga /start bosishlari kerak)"
        )

    await bot.send_message(
        chat_id,
        f"🎭 <b>O'YIN BOSHLANDI!</b>\n\n"
        f"👥 O'yinchilar ({len(game.players)} kishi):\n{players_list}\n\n"
        f"📩 Rol shaxsiy xabar orqali yuborildi!\n"
        f"🌙 <b>1-TUN boshlanmoqda...</b>{warn}",
        parse_mode="HTML"
    )

    # Lucky ticket triggerini tunda amalga oshiramiz
    await asyncio.sleep(3)
    await run_night(chat_id, game)


# ==================== NIGHT PHASE ====================

async def run_night(chat_id: int, game: MafiaGame):
    game.state = GameState.NIGHT
    game.night_actions = {}
    game.spy_blocked_id = None
    alive = game.get_alive_players()

    # Lucky ticket voqealari
    for p in alive:
        if db.has_item(p['id'], 18):
            await trigger_lucky_ticket(p['id'], chat_id, game)
            db.use_item(p['id'], 18)

    await bot.send_message(
        chat_id,
        f"🌙 <b>TUN — {game.round}-TUR</b>\n\n"
        f"Shahar uxlayapti... 😴\n"
        f"Tirik: <b>{len(alive)}</b> kishi\n\n"
        f"🔇 Barcha mute qilindi.\n"
        f"⏱ Harakatlar uchun {NIGHT_TIME} soniya!\n\n"
        f"<i>🌙 Mafia a'zolari botga yozib bir-biri bilan gaplasha oladi!</i>",
        parse_mode="HTML"
    )

    for p in alive:
        await mute_user(chat_id, p['id'])

    mafia_list = [p for p in alive if p['role'] in MAFIA_ROLES]
    targets_for_mafia = [p for p in alive if p['role'] not in MAFIA_ROLES]

    # Mafia / Donn → o'ldirish
    for mp in mafia_list:
        precise = "⚡ <b>Aniq nishon aktiv!</b> Himoyadan o'tadi.\n\n" if mp['id'] in game.precise_users else ""
        mafia_mates = [x['name'] for x in mafia_list if x['id'] != mp['id']]
        mates_line = f"🤝 Jamoangiz: {', '.join(mafia_mates)}\n\n" if mafia_mates else ""
        await safe_dm(
            mp['id'],
            f"🔫 <b>Mafia vakti!</b>\n\n"
            f"{mates_line}"
            f"{precise}"
            f"O'ldirish uchun nishon tanlang:\n"
            f"<i>💬 Siz shu tunda botga yozib mafia jamoangiz bilan gaplasha olasiz!</i>",
            parse_mode="HTML",
            reply_markup=night_target_kb(targets_for_mafia, "mk")
        )

    for p in alive:
        if p['role'] == Role.SHERIFF:
            others = [x for x in alive if x['id'] != p['id']]
            await safe_dm(
                p['id'],
                "🔍 <b>Sherif vakti!</b>\n\nKimni tekshirmoqchisiz?\n"
                "⚠️ MAFIA bo'lsa — o'sha kecha o'ladi!\n"
                "⚠️ Donn bo'lsa — tinch ko'rinadi (aldaydi).",
                parse_mode="HTML",
                reply_markup=night_target_kb(others, "sh")
            )

    for p in alive:
        if p['role'] == Role.DOCTOR:
            self_note = ("\n🚫 O'zingizni bu safar davolay olmaysiz!"
                         if game.doctor_self_heal_used
                         else "\n✅ O'zingizni davolash mumkin (1 marta)")
            all_targets = (alive if not game.doctor_self_heal_used
                           else [x for x in alive if x['id'] != p['id']])
            await safe_dm(
                p['id'],
                f"💉 <b>Doktor vakti!</b>\n\nKimni davolaysiz?{self_note}",
                parse_mode="HTML",
                reply_markup=night_target_kb(
                    all_targets, "doc",
                    exclude_id=p['id'] if game.doctor_self_heal_used else None
                )
            )

    for p in alive:
        if p['role'] == Role.SPY:
            self_note = ("\n🚫 O'zingizni bloklash imkoni tugagan!"
                         if game.spy_self_block_used
                         else "\n✅ O'zingizni bloklash mumkin (1 marta, himoya uchun)")
            spy_targets = (alive if not game.spy_self_block_used
                           else [x for x in alive if x['id'] != p['id']])
            await safe_dm(
                p['id'],
                f"💋 <b>Ayg'oqchi vakti!</b>\n\n"
                f"Kimni bloklaysiz?\n\n"
                f"🔒 Bloklangan kishi harakatsiz qoladi\n"
                f"🛡️ Mafia uni o'ldira olmaydi\n"
                f"☠️ Mafiyani bloklasang — U O'LADI!{self_note}",
                parse_mode="HTML",
                reply_markup=night_target_kb(spy_targets, "spy")
            )

    for p in alive:
        if p['role'] == Role.DONN and not game.donn_reveal_used:
            others = [x for x in alive if x['id'] != p['id']]
            await safe_dm(
                p['id'],
                "👑 <b>Donn vakti!</b>\n\nBir kishiga o'z kimligingizni oshkor qila olasiz.",
                parse_mode="HTML",
                reply_markup=night_target_kb(others, "donn_reveal")
            )

    for p in alive:
        if db.has_item(p['id'], 10) and p['role'] != Role.DOCTOR:
            others = [x for x in alive if x['id'] != p['id']]
            await safe_dm(
                p['id'],
                "💊 <b>Tibbiy komplet!</b>\n\nKimni davolaysiz? (1 martalik)",
                parse_mode="HTML",
                reply_markup=night_target_kb(others, "medkit")
            )

    for p in alive:
        if db.has_item(p['id'], 15):
            others = [x for x in alive if x['id'] != p['id']]
            await safe_dm(
                p['id'],
                "🧪 <b>Zahar!</b>\n\nKimni zaharlamoqchisiz?\n⚠️ U kishi keyingi tun albatta o'ladi!",
                parse_mode="HTML",
                reply_markup=night_target_kb(others, "poison")
            )

    # Josus komplet
    for p in alive:
        if p['id'] in game.spy_kit_users:
            mafia_names = [x['name'] for x in alive if x['role'] in MAFIA_ROLES]
            if mafia_names:
                reveal = random.choice(mafia_names)
                await safe_dm(
                    p['id'],
                    f"🕵️ <b>Josus komplet natijasi:</b>\n\nMafia a'zolaridan biri: <b>{reveal}</b>!",
                    parse_mode="HTML"
                )
            db.use_item(p['id'], 14)
            game.spy_kit_users.discard(p['id'])

    asyncio.create_task(bot_auto_night_actions(chat_id, game))
    await asyncio.sleep(NIGHT_TIME)
    await process_night(chat_id, game)


# ==================== LUCKY TICKET ====================

async def trigger_lucky_ticket(user_id: int, chat_id: int, game: MafiaGame):
    """Lucky Ticket — 6 xil tasodifiy hodisa"""
    events = [
        ("💰 Baxtli coin yomg'iri!", lambda: db.update_stat(user_id, coins=75)),
        ("🛡️ Sehrli himoya!", lambda: game.shield_users.add(user_id)),
        ("🗳️ Ikki ovoz kuchi!", lambda: game.extra_vote_users.add(user_id)),
        ("🔍 Josuslik imkoni!", lambda: game.spy_kit_users.add(user_id)),
        ("⚡ Aniq nishon kuchi!", lambda: game.precise_users.add(user_id)),
        ("🎲 Omad kuchaydi!", lambda: game.lucky_users.add(user_id)),
    ]
    event_name, action = random.choice(events)

    descriptions = {
        "💰 Baxtli coin yomg'iri!": "Bu o'yin uchun +75 💰 coin oldingiz!",
        "🛡️ Sehrli himoya!": "Bu tun mafia sizni o'ldira olmaydi!",
        "🗳️ Ikki ovoz kuchi!": "Ovozda 2 ta ovoz berasiz!",
        "🔍 Josuslik imkoni!": "Bir mafia a'zosining ismi shivirlandi...",
        "⚡ Aniq nishon kuchi!": "Sizning hujumingiz (Mafia uchun) himoyadan o'tadi!",
        "🎲 Omad kuchaydi!": "O'yin davomida o'limdan omon qolish ehtimoli 50%!",
    }
    desc = descriptions.get(event_name, "")
    action()

    await safe_dm(
        user_id,
        f"🎰 <b>LUCKY TICKET ISHLADI!</b>\n\n"
        f"✨ <b>{event_name}</b>\n\n"
        f"{desc}",
        parse_mode="HTML"
    )
    await bot.send_message(
        chat_id,
        f"🎰 <b>LUCKY EVENT!</b>\n\n"
        f"Bir o'yinchiga <b>{event_name}</b> taqdim etildi!",
        parse_mode="HTML"
    )


# ==================== MAFIA NIGHT CHAT ====================

@dp.message(F.chat.type == "private")
async def private_message_handler(message: Message, state: FSMContext):
    """Shaxsiy xabarlarni qayta ishlash — mafia chat, last words, va boshqalar"""
    user_id = message.from_user.id
    current_state = await state.get_state()

    # Last words holati
    if user_id in last_words_pending:
        chat_id, name = last_words_pending.pop(user_id)
        await state.clear()
        if message.text:
            await bot.send_message(
                chat_id,
                f"💬 <b>{name}ning oxirgi so'zlari:</b>\n\n<i>«{message.text}»</i>",
                parse_mode="HTML"
            )
        return

    # Anonim xabar holati
    if current_state == BotStates.waiting_anon_msg:
        data = await state.get_data()
        chat_id = data.get('chat_id')
        if not db.use_item(user_id, 13):
            await message.answer("❌ Narsa ishlatilmadi!")
            await state.clear()
            return
        await bot.send_message(
            chat_id,
            f"📢 <b>Anonim xabar:</b>\n\n{message.text}",
            parse_mode="HTML"
        )
        await message.answer("✅ Anonim xabar yuborildi!")
        await state.clear()
        return

    # Coin sovg'a holatlari
    if current_state == BotStates.waiting_sovga_id:
        try:
            target_id = int(message.text.strip())
            target = db.get_user(target_id)
            if not target:
                await message.answer(
                    "❌ Bu ID da foydalanuvchi topilmadi!\n"
                    "Faqat botga /start bosgan o'yinchilar mavjud.\n\n"
                    "Qaytadan ID yuboring yoki /bekor buyrug'ini bering:"
                )
                return
            await state.update_data(sovga_target_id=target_id, sovga_target_name=target['name'])
            await state.set_state(BotStates.waiting_sovga_amount)
            user_data = db.get_user(user_id)
            await message.answer(
                f"🎁 <b>{target['name']}</b> ga coin yubormoqchisiz.\n\n"
                f"💰 Sizda: <b>{user_data['coins']}</b> coin\n\n"
                f"Qancha coin yubormoqchisiz? (raqam yozing):"
            )
        except ValueError:
            await message.answer("❌ Noto'g'ri format! Faqat raqam yozing (masalan: 123456789):")
        return

    if current_state == BotStates.waiting_sovga_amount:
        try:
            amount = int(message.text.strip())
            if amount <= 0:
                await message.answer("❌ Miqdor 0 dan katta bo'lishi kerak!")
                return
            data = await state.get_data()
            target_id = data['sovga_target_id']
            target_name = data['sovga_target_name']
            success = db.transfer_coins(user_id, target_id, amount)
            await state.clear()
            if success:
                user_data = db.get_user(user_id)
                await message.answer(
                    f"✅ <b>Muvaffaqiyatli!</b>\n\n"
                    f"🎁 <b>{amount}💰</b> coin <b>{target_name}</b> ga yuborildi!\n\n"
                    f"💰 Sizda qoldi: <b>{user_data['coins']}</b> coin",
                    parse_mode="HTML",
                    reply_markup=back_kb("mini_games")
                )
                await safe_dm(
                    target_id,
                    f"🎁 <b>Sizga sovg'a!</b>\n\n"
                    f"<b>{message.from_user.full_name}</b> sizga <b>{amount}💰</b> coin yubordi!",
                    parse_mode="HTML"
                )
            else:
                user_data = db.get_user(user_id)
                await message.answer(
                    f"❌ Mablag' yetarli emas!\n"
                    f"💰 Sizda: <b>{user_data['coins']}</b> coin, "
                    f"kerak: <b>{amount}</b> coin",
                    parse_mode="HTML"
                )
        except ValueError:
            await message.answer("❌ Noto'g'ri miqdor! Faqat raqam yozing:")
        return

    # Admin coin berish holatlari
    if current_state == BotStates.waiting_addcoins_id:
        if not is_admin(user_id):
            return
        try:
            uid = int(message.text.strip())
            await state.update_data(target_id=uid)
            await state.set_state(BotStates.waiting_addcoins_amount)
            await message.answer(f"💰 ID:{uid} ga qancha coin bermoqchisiz?")
        except ValueError:
            await message.answer("❌ Noto'g'ri ID!")
            await state.clear()
        return

    if current_state == BotStates.waiting_addcoins_amount:
        if not is_admin(user_id):
            return
        try:
            amount = int(message.text.strip())
            data = await state.get_data()
            uid = data['target_id']
            db.update_stat(uid, coins=amount)
            await message.answer(f"✅ ID:{uid} ga {amount} 💰 coin berildi!")
        except ValueError:
            await message.answer("❌ Noto'g'ri miqdor!")
        await state.clear()
        return

    # 🌙 MAFIA NIGHT CHAT
    if user_id in user_game_map:
        chat_id = user_game_map[user_id]
        if chat_id in games:
            game = games[chat_id]
            player = game.get_player(user_id)
            if (player and player['alive']
                    and player['role'] in MAFIA_ROLES
                    and game.state == GameState.NIGHT
                    and message.text):
                # Barcha tirik mafia a'zolariga yuborish
                mafia_alive = [p for p in game.players if p['alive'] and p['role'] in MAFIA_ROLES]
                sender_name = player['name']
                role_emoji = "👑" if player['role'] == Role.DONN else "🔫"
                for mp in mafia_alive:
                    if mp['id'] != user_id:
                        await safe_dm(
                            mp['id'],
                            f"🌙 <b>Mafia chat:</b>\n"
                            f"{role_emoji} <b>{sender_name}:</b> {message.text}"
                        )
                await message.answer(f"✅ Xabar mafia jamoangizga yetkazildi")
                return


# ==================== NIGHT CALLBACKS ====================

@dp.callback_query(F.data.startswith("mk_"))
async def cb_mafia_kill(callback: CallbackQuery):
    target_id = int(callback.data.split("_")[1])
    user_id = callback.from_user.id
    for _, game in games.items():
        p = game.get_player(user_id)
        if p and p['role'] in MAFIA_ROLES and p['alive'] and game.state == GameState.NIGHT:
            game.night_actions['mafia'] = target_id
            t = game.get_player(target_id)
            await callback.answer(f"🎯 Nishon: {t['name'] if t else '?'}", show_alert=True)
            return
    await callback.answer("❌ Xato!", show_alert=True)


@dp.callback_query(F.data.startswith("sh_"))
async def cb_sheriff(callback: CallbackQuery):
    target_id = int(callback.data.split("_")[1])
    user_id = callback.from_user.id
    for _, game in games.items():
        p = game.get_player(user_id)
        if p and p['role'] == Role.SHERIFF and p['alive'] and game.state == GameState.NIGHT:
            game.night_actions['sheriff'] = target_id
            t = game.get_player(target_id)
            await callback.answer(f"🔍 Tekshirilmoqda: {t['name'] if t else '?'}", show_alert=True)
            return
    await callback.answer("❌ Xato!", show_alert=True)


@dp.callback_query(F.data.startswith("doc_"))
async def cb_doctor(callback: CallbackQuery):
    target_id = int(callback.data.split("_")[1])
    user_id = callback.from_user.id
    for _, game in games.items():
        p = game.get_player(user_id)
        if p and p['role'] == Role.DOCTOR and p['alive'] and game.state == GameState.NIGHT:
            if target_id == user_id and not game.doctor_self_heal_used:
                game.doctor_self_heal_used = True
            game.night_actions['doctor'] = target_id
            t = game.get_player(target_id)
            await callback.answer(f"💉 Davolanadi: {t['name'] if t else '?'}", show_alert=True)
            return
    await callback.answer("❌ Xato!", show_alert=True)


@dp.callback_query(F.data.startswith("spy_"))
async def cb_spy(callback: CallbackQuery):
    target_id = int(callback.data.split("_")[1])
    user_id = callback.from_user.id
    for _, game in games.items():
        p = game.get_player(user_id)
        if p and p['role'] == Role.SPY and p['alive'] and game.state == GameState.NIGHT:
            if target_id == user_id:
                game.spy_self_block_used = True
            game.night_actions['spy'] = target_id
            game.spy_blocked_id = target_id
            t = game.get_player(target_id)
            await callback.answer(f"💋 Bloklandi: {t['name'] if t else '?'}", show_alert=True)
            return
    await callback.answer("❌ Xato!", show_alert=True)


@dp.callback_query(F.data.startswith("donn_reveal_"))
async def cb_donn_reveal(callback: CallbackQuery):
    parts = callback.data.split("_")
    target_id = int(parts[2])
    user_id = callback.from_user.id
    for _, game in games.items():
        p = game.get_player(user_id)
        if p and p['role'] == Role.DONN and p['alive'] and game.state == GameState.NIGHT and not game.donn_reveal_used:
            game.donn_reveal_used = True
            t = game.get_player(target_id)
            if t:
                await safe_dm(
                    target_id,
                    f"🤫 <b>Maxfiy xabar!</b>\n\n"
                    f"DONN kim ekanligini bilasiz:\n👑 <b>{p['name']}</b> — DONN!",
                    parse_mode="HTML"
                )
                await callback.answer(f"✅ {t['name']}ga oshkor qilindi!", show_alert=True)
            return
    await callback.answer("❌ Xato!", show_alert=True)


@dp.callback_query(F.data.startswith("medkit_"))
async def cb_medkit(callback: CallbackQuery):
    target_id = int(callback.data.split("_")[1])
    user_id = callback.from_user.id
    for _, game in games.items():
        p = game.get_player(user_id)
        if p and p['alive'] and game.state == GameState.NIGHT:
            if db.use_item(user_id, 10):
                medkit_list = game.night_actions.get('medkit', [])
                if not isinstance(medkit_list, list):
                    medkit_list = []
                medkit_list.append(target_id)
                game.night_actions['medkit'] = medkit_list
                t = game.get_player(target_id)
                await callback.answer(f"💊 Davolanadi: {t['name'] if t else '?'}", show_alert=True)
                return
    await callback.answer("❌ Xato!", show_alert=True)


@dp.callback_query(F.data.startswith("poison_"))
async def cb_poison(callback: CallbackQuery):
    target_id = int(callback.data.split("_")[1])
    user_id = callback.from_user.id
    for _, game in games.items():
        p = game.get_player(user_id)
        if p and p['alive'] and game.state == GameState.NIGHT:
            if db.use_item(user_id, 15):
                game.poison_targets[target_id] = True
                t = game.get_player(target_id)
                await callback.answer(f"🧪 Zaharlanadi: {t['name'] if t else '?'}", show_alert=True)
                return
    await callback.answer("❌ Xato!", show_alert=True)


# ==================== PROCESS NIGHT ====================

async def process_night(chat_id: int, game: MafiaGame):
    actions = game.night_actions
    heal_target = actions.get('doctor')
    medkit_targets = actions.get('medkit', [])
    if not isinstance(medkit_targets, list):
        medkit_targets = [medkit_targets]
    all_healed = set(medkit_targets)
    if heal_target:
        all_healed.add(heal_target)

    spy_block = game.spy_blocked_id
    mafia_target = actions.get('mafia')
    sheriff_target = actions.get('sheriff')
    results = []

    # Xavf signali
    if mafia_target and mafia_target in game.alarm_users:
        alarm_p = game.get_player(mafia_target)
        if alarm_p and alarm_p['alive']:
            await safe_dm(
                mafia_target,
                "🔔 <b>Xavf signali!</b>\n\nSiz bu tun mafia tomonidan nishon qilindingiz!",
                parse_mode="HTML"
            )
            db.use_item(mafia_target, 16)
            game.alarm_users.discard(mafia_target)

    # Zahar
    for ptarget_id in list(game.poison_targets.keys()):
        victim = game.get_player(ptarget_id)
        if victim and victim['alive']:
            victim['alive'] = False
            results.append(f"🧪 <b>{victim['name']}</b> zahar ta'siridan halok bo'ldi!")
            db.update_stat(victim['id'], deaths=1)
        game.poison_targets.pop(ptarget_id, None)

    # Ayg'oqchi bloklash
    if spy_block is not None:
        spy_victim = game.get_player(spy_block)
        if spy_victim and spy_victim['alive'] and spy_victim['role'] in MAFIA_ROLES:
            spy_victim['alive'] = False
            results.append(
                f"💋 Ayg'oqchi <b>{spy_victim['name']}</b>ni (Mafia) blokladi — <b>U HALOK BO'LDI!</b>"
            )
            db.update_stat(spy_victim['id'], deaths=1)
            spy_p = next((p for p in game.players if p['role'] == Role.SPY and p['alive']), None)
            if spy_p:
                db.update_stat(spy_p['id'], kills=1)
        elif spy_victim and spy_victim['role'] not in MAFIA_ROLES:
            results.append(f"💋 Ayg'oqchi bir kishini blokladi — u harakatsiz qoldi.")

    # Sherif tekshirishi
    if sheriff_target:
        if sheriff_target == spy_block:
            results.append("🔍 Sherif bloklandi — bu kecha tekshira olmadi!")
        else:
            sheriff_victim = game.get_player(sheriff_target)
            if sheriff_victim and sheriff_victim['alive']:
                if sheriff_victim['role'] == Role.MAFIA:
                    sheriff_victim['alive'] = False
                    results.append(
                        f"🔍 Sherif tekshirdi: <b>{sheriff_victim['name']}</b> — <b>MAFIA!</b> O'ldirildi!"
                    )
                    db.update_stat(sheriff_victim['id'], deaths=1)
                    sherif_p = next((p for p in game.players if p['role'] == Role.SHERIFF and p['alive']), None)
                    if sherif_p:
                        db.update_stat(sherif_p['id'], kills=1)
                elif sheriff_victim['role'] == Role.DONN:
                    results.append(f"🔍 Sherif tekshirdi: <b>{sheriff_victim['name']}</b> — tinch kishi (aslida Donn)!")
                else:
                    results.append(f"🔍 Sherif tekshirdi: <b>{sheriff_victim['name']}</b> — tinch kishi.")

    # Mafia o'ldirishi
    if mafia_target:
        if (spy_block is not None
                and mafia_target == spy_block
                and game.get_player(spy_block)
                and game.get_player(spy_block)['role'] not in MAFIA_ROLES):
            results.append("💋 Mafia nishonini o'ldira olmadi — Ayg'oqchi himoya qildi!")
        else:
            victim = game.get_player(mafia_target)
            if victim and victim['alive']:
                precise_active = any(
                    mp['id'] in game.precise_users
                    for mp in game.players if mp['role'] in MAFIA_ROLES
                )
                if not precise_active and mafia_target in all_healed:
                    results.append(f"💉 Doktor: <b>{victim['name']}</b> qutqarib qolindi!")
                elif not precise_active and victim['id'] in game.shield_users:
                    results.append(f"🛡️ Himoya qalqoni: <b>{victim['name']}</b> omon qoldi!")
                    db.use_item(victim['id'], 8)
                    game.shield_users.discard(victim['id'])
                elif not precise_active and victim['id'] in game.lucky_users:
                    if random.random() < 0.5:
                        results.append(f"🎲 Omad kubigi: <b>{victim['name']}</b> omon qoldi! (50/50)")
                    else:
                        victim['alive'] = False
                        results.append(
                            f"🔫 <b>{victim['name']}</b> o'ldirildi!\n   <i>(Omad kubigi ishlamadi...)</i>"
                        )
                        db.update_stat(victim['id'], deaths=1)
                        for mp in game.players:
                            if mp['role'] in MAFIA_ROLES and mp['alive']:
                                db.update_stat(mp['id'], kills=1)
                    db.use_item(victim['id'], 9)
                    game.lucky_users.discard(victim['id'])
                else:
                    victim['alive'] = False
                    results.append(f"🔫 <b>{victim['name']}</b> mafia tomonidan o'ldirildi!")
                    db.update_stat(victim['id'], deaths=1)
                    for mp in game.players:
                        if mp['role'] in MAFIA_ROLES and mp['alive']:
                            db.update_stat(mp['id'], kills=1)
                    if precise_active:
                        for mp in game.players:
                            if mp['role'] in MAFIA_ROLES and mp['id'] in game.precise_users:
                                db.use_item(mp['id'], 17)
                                game.precise_users.discard(mp['id'])

    if not results:
        results.append("🌟 Bu kecha hech kim halok bo'lmadi!")

    msg = "☀️ <b>TONG OTDI!</b>\n\n" + "\n".join(results)

    all_dead_now = [p for p in game.players if not p['alive']]
    if all_dead_now:
        msg += "\n\n<b>☠️ O'lganlar:</b>\n"
        for dead_p in all_dead_now:
            role_text = "❓ ?" if db.has_item(dead_p['id'], 11) else f"{get_role_emoji(dead_p['role'])} {dead_p['role'].value}"
            msg += f"  • {dead_p['name']} — {role_text}\n"

    await bot.send_message(chat_id, msg, parse_mode="HTML")

    for p in game.players:
        if not p['alive']:
            await mute_user(chat_id, p['id'])

    winner = game.check_winner()
    if winner:
        await announce_winner(chat_id, game, winner)
        return

    await asyncio.sleep(3)
    await run_day(chat_id, game)


# ==================== DAY PHASE ====================

async def run_day(chat_id: int, game: MafiaGame):
    game.state = GameState.DAY
    alive = game.get_alive_players()
    for p in alive:
        await unmute_user(chat_id, p['id'])

    names = format_alive_list(game.players)
    await bot.send_message(
        chat_id,
        f"☀️ <b>KUN — {game.round}-TUR</b>\n\n"
        f"Tirik o'yinchilar ({len(alive)}):\n{names}\n\n"
        f"💬 Muhokama qiling! Kim mafia?\n"
        f"⏱ <b>{DISCUSS_TIME} soniya</b> muhokama vaqti.",
        parse_mode="HTML"
    )

    await asyncio.sleep(DISCUSS_TIME)

    game.state = GameState.VOTING
    game.votes = {}
    alive = game.get_alive_players()

    await bot.send_message(
        chat_id,
        f"🗳️ <b>OVOZ BERISH VAQTI!</b>\n\nKim o'yindan chiqarilsin?\n⏱ <b>{VOTE_TIME} soniya</b>",
        parse_mode="HTML",
        reply_markup=vote_kb(alive, 0, game.extra_vote_users)
    )

    asyncio.create_task(bot_auto_votes(chat_id, game))
    await asyncio.sleep(VOTE_TIME)
    await process_votes(chat_id, game)


@dp.callback_query(F.data.startswith("vote_"))
async def cb_vote(callback: CallbackQuery):
    data = callback.data
    user_id = callback.from_user.id
    chat_id = callback.message.chat.id

    if chat_id not in games:
        await callback.answer("❌ O'yin topilmadi!", show_alert=True)
        return
    game = games[chat_id]
    if game.state != GameState.VOTING:
        await callback.answer("❌ Ovoz berish vaqti emas!", show_alert=True)
        return
    p = game.get_player(user_id)
    if not p or not p['alive']:
        await callback.answer("❌ Siz ovoz bera olmaysiz!", show_alert=True)
        return

    if data == "vote_skip":
        if user_id in game.votes:
            await callback.answer("❌ Allaqachon ovoz berdingiz!", show_alert=True)
            return
        game.votes[user_id] = "skip"
        await callback.answer("✅ O'tkazib yubordingiz")
        await bot.send_message(chat_id, f"🗳️ {callback.from_user.full_name} — <b>o'tkazib yubordi</b>", parse_mode="HTML")
        return

    target_id = int(data.split("_")[1])
    extra = user_id in game.extra_vote_users

    if user_id not in game.votes:
        game.votes[user_id] = []
    vote_list = game.votes[user_id]
    if not isinstance(vote_list, list):
        await callback.answer("❌ Allaqachon ovoz berdingiz!", show_alert=True)
        return
    max_v = 2 if extra else 1
    if len(vote_list) >= max_v:
        await callback.answer("❌ Ovozlaringiz tugadi!", show_alert=True)
        return

    vote_list.append(target_id)
    if extra and len(vote_list) == 1:
        db.use_item(user_id, 12)
        game.extra_vote_users.discard(user_id)

    t = game.get_player(target_id)
    if t:
        await callback.answer(f"✅ {t['name']}ga ovoz berdingiz")
        await bot.send_message(chat_id, f"🗳️ {callback.from_user.full_name} → <b>{t['name']}</b>", parse_mode="HTML")


async def process_votes(chat_id: int, game: MafiaGame):
    vote_count: dict[int, int] = {}
    for user_id, v in game.votes.items():
        if isinstance(v, list):
            for tid in v:
                vote_count[tid] = vote_count.get(tid, 0) + 1
        elif v != "skip":
            vote_count[v] = vote_count.get(v, 0) + 1

    if not vote_count:
        await bot.send_message(chat_id, "🤷 Hech kim ovoz bermadi! O'yin davom etadi...")
    else:
        max_votes = max(vote_count.values())
        candidates = [pid for pid, cnt in vote_count.items() if cnt == max_votes]
        eliminated_id = random.choice(candidates)
        eliminated = game.get_player(eliminated_id)

        if eliminated:
            eliminated['alive'] = False
            if not is_bot_player(eliminated['id']):
                db.update_stat(eliminated['id'], deaths=1)
            await mute_user(chat_id, eliminated['id'])

            vote_text = "🗳️ <b>OVOZ NATIJASI:</b>\n"
            for pid, cnt in sorted(vote_count.items(), key=lambda x: -x[1]):
                pp = game.get_player(pid)
                if pp:
                    vote_text += f"  • {pp['name']}: {cnt} ovoz\n"

            role_text = "❓ ?" if db.has_item(eliminated['id'], 11) else f"{get_role_emoji(eliminated['role'])} {eliminated['role'].value}"
            vote_text += f"\n❌ <b>{eliminated['name']}</b> o'yindan chiqarildi!\nRol: {role_text}"
            await bot.send_message(chat_id, vote_text, parse_mode="HTML")

            # 💬 OXIRGI SO'Z — 30 soniya (botlar uchun emas)
            if not is_bot_player(eliminated['id']):
                last_words_pending[eliminated['id']] = (chat_id, eliminated['name'])
                await safe_dm(
                    eliminated['id'],
                    f"💬 <b>Oxirgi so'z!</b>\n\n"
                    f"Siz o'yindan chiqarildingiz.\n"
                    f"Guruhga <b>30 soniya</b> ichida oxirgi xabaringizni yuboring!\n\n"
                    f"<i>Hozir menga yozing — guruhga o'tkaziladi.</i>",
                    parse_mode="HTML"
                )
                await bot.send_message(
                    chat_id,
                    f"⏳ <b>{eliminated['name']}</b> oxirgi so'z aytish uchun 30 soniya oldi...",
                    parse_mode="HTML"
                )
                await asyncio.sleep(30)
                last_words_pending.pop(eliminated['id'], None)
                await notify_achievements(eliminated['id'])

    winner = game.check_winner()
    if winner:
        await announce_winner(chat_id, game, winner)
        return

    game.round += 1
    await asyncio.sleep(2)
    await run_night(chat_id, game)


# ==================== WINNER ====================

async def announce_winner(chat_id: int, game: MafiaGame, winner: str):
    game.state = GameState.ENDED
    await unmute_all(chat_id, game)

    base_coins = WIN_COINS.get(winner, 100)
    # 2x Coin kuni tekshiruvi
    if chat_id in _double_event_chats:
        base_coins *= 2
    winner_lines = []

    # Guruh statistikasini yangilash
    db.increment_group_games(chat_id)

    streak_bonus_lines = []
    for p in game.players:
        role_group = game.get_role_group(p['role'])
        won_this_game = (role_group == winner)
        if won_this_game:
            coins = base_coins
            if p['alive']:
                coins += SURVIVE_BONUS
            coins += p.get('kills', 0) * KILL_BONUS
            if not is_bot_player(p['id']):
                if db.has_item(p['id'], 20):
                    coins *= 2
                    db.use_item(p['id'], 20)
                db.update_stat(p['id'], games_won=1, coins=coins)
                # Kunlik vazifalarni yangilash: games_done
                db.update_daily_mission(p['id'], 'games_done')
                new_streak = db.update_win_streak(p['id'], True)
                if new_streak >= 2:
                    streak_bonus = new_streak * 15
                    db.update_stat(p['id'], coins=streak_bonus)
                    streak_bonus_lines.append(
                        f"  🌟 {p['name']} — {new_streak} ketma-ket g'alaba! +{streak_bonus}💰"
                    )
            winner_lines.append(f"  {get_role_emoji(p['role'])} {p['name']} → +{coins}💰")
        else:
            if not is_bot_player(p['id']):
                db.update_win_streak(p['id'], False)

        user_game_map.pop(p['id'], None)
        if not is_bot_player(p['id']):
            asyncio.create_task(notify_achievements(p['id']))

    roles_text = "\n".join([
        f"  {'✅' if p['alive'] else '❌'} {p['name']} — {get_role_emoji(p['role'])} {p['role'].value}"
        for p in game.players
    ])

    msg = WINNER_MESSAGES.get(winner, "🎮 O'yin yakunlandi!")
    coins_text = "\n".join(winner_lines) if winner_lines else "  —"
    streak_text = ""
    if streak_bonus_lines:
        streak_text = f"\n\n🌟 <b>G'alaba seriyasi bonusi:</b>\n" + "\n".join(streak_bonus_lines)

    total_rounds = game.round - 1
    game_summary = f"\n\n📊 <b>O'yin xulosasi:</b>\n  🔄 Turlar: {total_rounds}\n  👥 O'yinchilar: {len(game.players)}"

    await bot.send_message(
        chat_id,
        f"{msg}\n\n"
        f"<b>💰 G'oliblar va mukofotlar:</b>\n{coins_text}{streak_text}\n\n"
        f"<b>👥 Barcha o'yinchilar:</b>\n{roles_text}"
        f"{game_summary}\n\n"
        f"🏪 Coinlarni do'konda sarflang!\n"
        f"🎁 Kunlik bonus uchun /start bosing!",
        parse_mode="HTML"
    )

    games.pop(chat_id, None)


# ==================== SHOP ====================

@dp.callback_query(F.data.startswith("shop_page_"))
async def cb_shop_page(callback: CallbackQuery):
    page = int(callback.data.split("_")[2])
    user = callback.from_user
    db.ensure_user(user.id, user.full_name)
    user_data = db.get_user(user.id)
    try:
        await callback.message.edit_text(
            f"🏪 <b>DO'KON</b>\n\n💰 Sizning coinlaringiz: <b>{user_data['coins']}</b>\n\nNarsani tanlang:",
            parse_mode="HTML",
            reply_markup=shop_page_kb(page, user.id)
        )
    except Exception:
        pass
    await callback.answer()


@dp.callback_query(F.data.startswith("shop_item_"))
async def cb_shop_item(callback: CallbackQuery):
    item_id = int(callback.data.split("_")[2])
    item = get_item(item_id)
    if not item:
        await callback.answer("❌ Narsa topilmadi!", show_alert=True)
        return
    user = callback.from_user
    db.ensure_user(user.id, user.full_name)
    user_data = db.get_user(user.id)
    inv = db.get_inventory(user.id)
    qty = next((i['quantity'] for i in inv if i['item_id'] == item_id), 0)
    type_tag = "♻️ Qayta sotib olish mumkin" if item.get('consumable') else "🔒 Doimiy narsa"
    qty_line = f"\n📦 Qo'lingizdagi: <b>{qty}</b> ta" if item.get('consumable') else ""
    await callback.message.edit_text(
        f"🏪 <b>{item['name']}</b>\n\n📝 {item['desc']}\n\n"
        f"💰 Narx: <b>{item['price']}</b> coin\n{type_tag}{qty_line}\n\n"
        f"💳 Sizda: <b>{user_data['coins']}</b> coin",
        parse_mode="HTML",
        reply_markup=shop_item_kb(item_id, 0, user.id)
    )
    await callback.answer()


@dp.callback_query(F.data.startswith("shop_buy_"))
async def cb_shop_buy(callback: CallbackQuery):
    item_id = int(callback.data.split("_")[2])
    user = callback.from_user
    db.ensure_user(user.id, user.full_name)
    item = get_item(item_id)
    if not item:
        await callback.answer("❌ Narsa topilmadi!", show_alert=True)
        return
    user_data = db.get_user(user.id)
    if user_data['coins'] < item['price']:
        await callback.answer("❌ Mablag' yetarli emas!", show_alert=True)
        return
    inv = db.get_inventory(user.id)
    if not item.get('consumable') and any(i['item_id'] == item_id for i in inv):
        await callback.answer("✅ Bu narsa allaqachon siz bilan!", show_alert=True)
        return
    db.update_stat(user.id, coins=-item['price'])
    db.add_item(user.id, item_id)
    await callback.answer(f"✅ {item['name']} sotib olindi!", show_alert=True)
    user_data = db.get_user(user.id)
    inv = db.get_inventory(user.id)
    qty = next((i['quantity'] for i in inv if i['item_id'] == item_id), 0)
    type_tag = "♻️ Qayta sotib olish mumkin" if item.get('consumable') else "🔒 Doimiy narsa"
    qty_line = f"\n📦 Qo'lingizdagi: <b>{qty}</b> ta" if item.get('consumable') else ""
    try:
        await callback.message.edit_text(
            f"🏪 <b>{item['name']}</b>\n\n📝 {item['desc']}\n\n"
            f"💰 Narx: <b>{item['price']}</b> coin\n{type_tag}{qty_line}\n\n"
            f"💳 Sizda: <b>{user_data['coins']}</b> coin",
            parse_mode="HTML",
            reply_markup=shop_item_kb(item_id, 0, user.id)
        )
    except Exception:
        pass


@dp.callback_query(F.data == "shop_noop")
async def cb_shop_noop(callback: CallbackQuery):
    await callback.answer()


# ==================== ADMIN (PRIVATE) ====================

@dp.callback_query(F.data == "admin_panel")
async def cb_admin_panel(callback: CallbackQuery):
    if not is_admin(callback.from_user.id):
        await callback.answer("❌ Ruxsat yo'q!", show_alert=True)
        return
    active = len([g for g in games.values() if g.state != GameState.ENDED])
    await callback.message.edit_text(
        f"👮 <b>ADMIN PANEL</b>\n\n🎮 Aktiv o'yinlar: <b>{active}</b>\n👥 Guruhlar: <b>{len(games)}</b>",
        parse_mode="HTML",
        reply_markup=admin_panel_kb()
    )
    await callback.answer()


@dp.callback_query(F.data == "admin_stats")
async def cb_admin_stats(callback: CallbackQuery):
    if not is_admin(callback.from_user.id):
        await callback.answer("❌ Ruxsat yo'q!", show_alert=True)
        return
    rows = db.get_top(5)
    text = "📊 <b>TOP 5 O'YINCHILAR</b>\n\n"
    for i, (name, played, won, coins, winrate) in enumerate(rows):
        text += f"{i+1}. <b>{name}</b> — {won}/{played} • {winrate}% • {coins}💰\n"
    await callback.message.edit_text(text, parse_mode="HTML", reply_markup=back_kb("admin_panel"))
    await callback.answer()


@dp.callback_query(F.data == "admin_banlist")
async def cb_admin_banlist(callback: CallbackQuery):
    if not is_admin(callback.from_user.id):
        await callback.answer("❌ Ruxsat yo'q!", show_alert=True)
        return
    bans = db.get_banned_list()
    if not bans:
        await callback.answer("✅ Blocklangan foydalanuvchilar yo'q!", show_alert=True)
        return
    text = "🚫 <b>Blocklangan:</b>\n\n"
    for uid, name, reason, ban_time in bans:
        text += f"• <b>{name}</b> (ID:{uid})\n  Sabab: {reason}\n  Vaqt: {ban_time}\n\n"
    await callback.message.edit_text(text, parse_mode="HTML", reply_markup=back_kb("admin_panel"))
    await callback.answer()


@dp.callback_query(F.data == "admin_stop")
async def cb_admin_stop(callback: CallbackQuery):
    if not is_admin(callback.from_user.id):
        await callback.answer("❌ Ruxsat yo'q!", show_alert=True)
        return
    chat_id = callback.message.chat.id
    if chat_id not in games:
        await callback.answer("❌ Aktiv o'yin yo'q!", show_alert=True)
        return
    game = games.pop(chat_id)
    await unmute_all(chat_id, game)
    await callback.answer("🛑 O'yin to'xtatildi!", show_alert=True)
    await bot.send_message(chat_id, "🛑 Admin o'yinni to'xtatdi!")


@dp.callback_query(F.data == "admin_addcoins")
async def cb_admin_addcoins(callback: CallbackQuery, state: FSMContext):
    if not is_admin(callback.from_user.id):
        await callback.answer("❌ Ruxsat yo'q!", show_alert=True)
        return
    await state.set_state(BotStates.waiting_addcoins_id)
    await callback.message.answer("💰 Coin berish uchun foydalanuvchi ID sini yuboring:")
    await callback.answer()


# ==================== BAN/UNBAN COMMANDS ====================

@dp.message(Command("ban"))
async def cmd_ban(message: Message):
    if not is_admin(message.from_user.id):
        return
    if message.reply_to_message:
        target = message.reply_to_message.from_user
        args = message.text.split(maxsplit=1)
        reason = args[1] if len(args) > 1 else "Sabab ko'rsatilmadi"
        db.ban_user(target.id, target.full_name, reason, message.from_user.id)
        try:
            await bot.ban_chat_member(message.chat.id, target.id)
        except Exception:
            pass
        await message.answer(f"🚫 <b>{target.full_name}</b> bloklandi!\nSabab: {reason}", parse_mode="HTML")
    else:
        args = message.text.split(maxsplit=2)
        if len(args) < 2:
            await message.answer("📌 /ban [user_id] [sabab]")
            return
        try:
            uid = int(args[1])
            reason = args[2] if len(args) > 2 else "Sabab ko'rsatilmadi"
            db.ban_user(uid, f"ID:{uid}", reason, message.from_user.id)
            await message.answer(f"🚫 ID:{uid} bloklandi! Sabab: {reason}")
        except ValueError:
            await message.answer("❌ Noto'g'ri ID!")


@dp.message(Command("unban"))
async def cmd_unban(message: Message):
    if not is_admin(message.from_user.id):
        return
    args = message.text.split()
    if len(args) < 2:
        await message.answer("📌 /unban [user_id]")
        return
    try:
        uid = int(args[1])
        db.unban_user(uid)
        try:
            await bot.unban_chat_member(message.chat.id, uid)
        except Exception:
            pass
        await message.answer(f"✅ ID:{uid} blokdan chiqarildi!")
    except ValueError:
        await message.answer("❌ Noto'g'ri ID!")


@dp.message(Command("anon"))
async def cmd_anon(message: Message, state: FSMContext):
    chat_id = message.chat.id
    user_id = message.from_user.id
    if chat_id not in games:
        await message.answer("❌ Bu guruhda aktiv o'yin yo'q!")
        return
    if not db.has_item(user_id, 13):
        await message.answer("❌ Sizda '📢 Anonim xabar' predmeti yo'q!\nDo'kondan 50💰 ga sotib oling.")
        return
    await state.set_state(BotStates.waiting_anon_msg)
    await state.update_data(chat_id=chat_id)
    await message.answer("📢 Yubormoqchi bo'lgan anonim xabaringizni yozing:")


# ==================== GURUH ADMIN PANEL ====================

@dp.callback_query(F.data == "group_admin_panel")
async def cb_group_admin_panel(callback: CallbackQuery):
    if not is_admin(callback.from_user.id):
        await callback.answer("❌ Siz admin emassiz!", show_alert=True)
        return
    chat_id = callback.message.chat.id
    has_game = chat_id in games and games[chat_id].state not in (GameState.ENDED,)
    game_waiting = has_game and games[chat_id].state == GameState.WAITING
    game_status = "🟢 Aktiv" if has_game else "🔴 O'yin yo'q"
    if game_waiting:
        game_status = "⏳ Kutmoqda (ro'yxat ochiq)"
    await callback.message.edit_text(
        f"👮 <b>GURUH ADMIN PANEL</b>\n\n🎮 O'yin holati: <b>{game_status}</b>\n\nNima qilmoqchisiz?",
        parse_mode="HTML",
        reply_markup=group_admin_panel_kb(has_game, game_waiting)
    )
    await callback.answer()


@dp.callback_query(F.data == "gadmin_addbots")
async def cb_gadmin_addbots(callback: CallbackQuery):
    if not is_admin(callback.from_user.id):
        await callback.answer("❌ Ruxsat yo'q!", show_alert=True)
        return
    chat_id = callback.message.chat.id
    if chat_id not in games or games[chat_id].state != GameState.WAITING:
        await callback.answer("❌ O'yin ro'yxat ochiq holatida emas!", show_alert=True)
        return
    game = games[chat_id]
    available = MAX_PLAYERS - len(game.players)
    if available <= 0:
        await callback.answer("❌ O'yin to'ldi! Bot qo'shib bo'lmaydi.", show_alert=True)
        return
    await callback.message.edit_text(
        f"🤖 <b>BOT QO'SHISH</b>\n\n"
        f"👥 Hozir: <b>{len(game.players)}</b> o'yinchi\n"
        f"📌 Bo'sh joy: <b>{available}</b> ta\n\n"
        f"Nechta bot qo'shmoqchisiz?\n"
        f"<i>Botlar 60 soniya ichida kiradi</i>",
        parse_mode="HTML",
        reply_markup=add_bots_count_kb()
    )
    await callback.answer()


@dp.callback_query(F.data.startswith("addbots_"))
async def cb_addbots_count(callback: CallbackQuery):
    if not is_admin(callback.from_user.id):
        await callback.answer("❌ Ruxsat yo'q!", show_alert=True)
        return
    chat_id = callback.message.chat.id
    if chat_id not in games or games[chat_id].state != GameState.WAITING:
        await callback.answer("❌ O'yin ro'yxat ochiq holatida emas!", show_alert=True)
        return
    game = games[chat_id]
    requested = int(callback.data.split("_")[1])
    available = MAX_PLAYERS - len(game.players)
    count = min(requested, available)
    if count <= 0:
        await callback.answer("❌ O'yin to'ldi!", show_alert=True)
        return
    await callback.answer(f"✅ {count} ta bot qo'shilmoqda...")
    try:
        await callback.message.edit_text(
            f"🤖 <b>{count} ta bot qo'shilmoqda...</b>\n\n"
            f"⏱ Botlar 60 soniya ichida birin-ketin kiradi!",
            parse_mode="HTML"
        )
    except Exception:
        pass
    asyncio.create_task(add_bots_gradually(chat_id, game, count))


async def add_bots_gradually(chat_id: int, game: MafiaGame, count: int):
    """Botlarni asta-sekin (60 soniya ichida) qo'shish"""
    used_names = {p['name'] for p in game.players}
    available_names = [n for n in BOT_NAMES if n not in used_names]
    random.shuffle(available_names)

    total_time = 55.0
    if count == 1:
        delays = [random.uniform(3, total_time)]
    else:
        delays = sorted([random.uniform(3, total_time) for _ in range(count)])

    prev = 0.0
    for i in range(count):
        wait = delays[i] - prev
        await asyncio.sleep(max(1.0, wait))
        prev = delays[i]

        if chat_id not in games or games[chat_id] is not game or game.state != GameState.WAITING:
            break
        if len(game.players) >= MAX_PLAYERS:
            break

        bot_id = _next_bot_id()
        bot_name = available_names[i] if i < len(available_names) else f"Bot{abs(bot_id)}"
        game.add_player(bot_id, f"🤖 {bot_name}")

        count_now = len(game.players)
        names = format_player_list(game.players)
        try:
            await bot.send_message(
                chat_id,
                f"🤖 <b>{bot_name}</b> o'yinga qo'shildi!\n\n"
                f"🎭 <b>MAFIA — Ro'yxat</b>\n\n"
                f"👥 O'yinchilar: <b>{count_now}</b>/{MAX_PLAYERS}\n\n{names}",
                parse_mode="HTML",
                reply_markup=join_game_kb(count_now)
            )
        except Exception as e:
            logger.warning(f"Bot join xabar xatosi: {e}")


async def bot_auto_night_actions(chat_id: int, game: MafiaGame):
    """Bot o'yinchilar uchun tun harakatlarini avtomatik bajarish"""
    await asyncio.sleep(5)
    if chat_id not in games or games[chat_id] is not game:
        return
    if game.state != GameState.NIGHT:
        return

    alive = game.get_alive_players()
    alive_real = [p for p in alive if not is_bot_player(p['id'])]
    alive_bots = [p for p in alive if is_bot_player(p['id'])]

    for p in alive_bots:
        if p['role'] in MAFIA_ROLES:
            if 'mafia' not in game.night_actions:
                targets = [x for x in alive if not is_bot_player(x['id']) and x['role'] not in MAFIA_ROLES]
                if not targets:
                    targets = [x for x in alive if x['id'] != p['id'] and x['role'] not in MAFIA_ROLES]
                if targets:
                    game.night_actions['mafia'] = random.choice(targets)['id']
        elif p['role'] == Role.SHERIFF:
            if 'sheriff' not in game.night_actions:
                targets = [x for x in alive if x['id'] != p['id']]
                if targets:
                    game.night_actions['sheriff'] = random.choice(targets)['id']
        elif p['role'] == Role.DOCTOR:
            if 'doctor' not in game.night_actions:
                targets = alive if not game.doctor_self_heal_used else [x for x in alive if x['id'] != p['id']]
                if targets:
                    target = random.choice(targets)
                    if target['id'] == p['id']:
                        game.doctor_self_heal_used = True
                    game.night_actions['doctor'] = target['id']
        elif p['role'] == Role.SPY:
            if 'spy' not in game.night_actions:
                targets = alive if not game.spy_self_block_used else [x for x in alive if x['id'] != p['id']]
                if targets:
                    target = random.choice(targets)
                    game.night_actions['spy'] = target['id']
                    game.spy_blocked_id = target['id']


async def bot_auto_votes(chat_id: int, game: MafiaGame):
    """Bot o'yinchilar uchun ovoz berishni avtomatik bajarish"""
    await asyncio.sleep(4)
    if chat_id not in games or games[chat_id] is not game:
        return
    if game.state != GameState.VOTING:
        return

    alive = game.get_alive_players()
    for p in alive:
        if is_bot_player(p['id']) and p['id'] not in game.votes:
            targets = [x for x in alive if x['id'] != p['id']]
            if targets:
                target = random.choice(targets)
                game.votes[p['id']] = [target['id']]


@dp.callback_query(F.data == "gadmin_close")
async def cb_gadmin_close(callback: CallbackQuery):
    if not is_admin(callback.from_user.id):
        await callback.answer("❌ Ruxsat yo'q!", show_alert=True)
        return
    try:
        await callback.message.delete()
    except Exception:
        pass
    await callback.answer("✅ Yopildi")


@dp.callback_query(F.data == "gadmin_stop")
async def cb_gadmin_stop(callback: CallbackQuery):
    if not is_admin(callback.from_user.id):
        await callback.answer("❌ Ruxsat yo'q!", show_alert=True)
        return
    chat_id = callback.message.chat.id
    if chat_id not in games:
        await callback.answer("❌ Aktiv o'yin yo'q!", show_alert=True)
        return
    await callback.message.edit_text(
        "🛑 <b>O'yinni to'xtatish</b>\n\nHaqiqatan ham bekor qilmoqchimisiz?\n⚠️ Coin berilmaydi.",
        parse_mode="HTML",
        reply_markup=confirm_stop_kb()
    )
    await callback.answer()


@dp.callback_query(F.data == "gadmin_confirmstop")
async def cb_gadmin_confirmstop(callback: CallbackQuery):
    if not is_admin(callback.from_user.id):
        await callback.answer("❌ Ruxsat yo'q!", show_alert=True)
        return
    chat_id = callback.message.chat.id
    if chat_id not in games:
        await callback.answer("❌ O'yin topilmadi!", show_alert=True)
        return
    game = games.pop(chat_id)
    await unmute_all(chat_id, game)
    for p in game.players:
        user_game_map.pop(p['id'], None)
    try:
        await callback.message.delete()
    except Exception:
        pass
    await bot.send_message(
        chat_id,
        f"🛑 <b>O'yin to'xtatildi!</b>\n\n👮 Admin <b>{callback.from_user.full_name}</b> tomonidan.",
        parse_mode="HTML"
    )
    await callback.answer("✅ O'yin to'xtatildi!")


@dp.callback_query(F.data == "gadmin_ban_menu")
async def cb_gadmin_ban_menu(callback: CallbackQuery):
    if not is_admin(callback.from_user.id):
        await callback.answer("❌ Ruxsat yo'q!", show_alert=True)
        return
    chat_id = callback.message.chat.id
    has_game = chat_id in games and games[chat_id].state not in (GameState.ENDED,)
    if has_game and games[chat_id].players:
        await callback.message.edit_text(
            "🚫 <b>BAN QILISH</b>\n\nO'yindagi o'yinchilardan birini tanlang:",
            parse_mode="HTML",
            reply_markup=ban_players_kb(games[chat_id].players)
        )
        await callback.answer()
        return
    await callback.answer("⚠️ O'yindagi o'yinchilar yo'q. /ban [ID] [sabab] ishlating.", show_alert=True)


@dp.callback_query(F.data.startswith("gadmin_ban_"))
async def cb_gadmin_ban_select(callback: CallbackQuery):
    if not is_admin(callback.from_user.id):
        await callback.answer("❌ Ruxsat yo'q!", show_alert=True)
        return
    parts = callback.data.split("_")
    if len(parts) < 4:
        await callback.answer("❌ Xato!", show_alert=True)
        return
    target_id = int(parts[2])
    target_name = "_".join(parts[3:])
    await callback.message.edit_text(
        f"🚫 <b>{target_name}</b>ni ban qilish\n\nBan sababini tanlang:",
        parse_mode="HTML",
        reply_markup=ban_reason_kb(target_id)
    )
    await callback.answer()


@dp.callback_query(F.data.startswith("gadmin_banreason_"))
async def cb_gadmin_banreason(callback: CallbackQuery):
    if not is_admin(callback.from_user.id):
        await callback.answer("❌ Ruxsat yo'q!", show_alert=True)
        return
    parts = callback.data.split("_")
    target_id = int(parts[2])
    reason = parts[3] if len(parts) > 3 else "boshqa"
    reason_labels = {
        "haqorat": "Haqorat", "spam": "Aldash/Spam",
        "nomaqul": "Noma'qul xatti-harakat", "qoidabuzarlik": "Qoidabuzarlik", "boshqa": "Boshqa sabab",
    }
    reason_text = reason_labels.get(reason, reason)
    target_name = f"ID:{target_id}"
    for _, g in games.items():
        p = g.get_player(target_id)
        if p:
            target_name = p['name']
            break
    if target_name == f"ID:{target_id}":
        ud = db.get_user(target_id)
        if ud:
            target_name = ud.get('name', target_name)
    await callback.message.edit_text(
        f"🚫 <b>Ban tasdiqlash</b>\n\n👤 Foydalanuvchi: <b>{target_name}</b>\n📝 Sabab: <b>{reason_text}</b>\n\nTasdiqlaysizmi?",
        parse_mode="HTML",
        reply_markup=confirm_ban_kb(target_id, reason)
    )
    await callback.answer()


@dp.callback_query(F.data.startswith("gadmin_confirmban_"))
async def cb_gadmin_confirmban(callback: CallbackQuery):
    if not is_admin(callback.from_user.id):
        await callback.answer("❌ Ruxsat yo'q!", show_alert=True)
        return
    parts = callback.data.split("_")
    target_id = int(parts[2])
    reason_key = parts[3] if len(parts) > 3 else "boshqa"
    reason_labels = {
        "haqorat": "Haqorat", "spam": "Aldash/Spam",
        "nomaqul": "Noma'qul xatti-harakat", "qoidabuzarlik": "Qoidabuzarlik", "boshqa": "Boshqa sabab",
    }
    reason_text = reason_labels.get(reason_key, reason_key)
    chat_id = callback.message.chat.id
    target_name = f"ID:{target_id}"
    for _, g in games.items():
        p = g.get_player(target_id)
        if p:
            target_name = p['name']
            p['alive'] = False
            break
    if target_name == f"ID:{target_id}":
        ud = db.get_user(target_id)
        if ud:
            target_name = ud.get('name', target_name)
    db.ban_user(target_id, target_name, reason_text, callback.from_user.id)
    try:
        await bot.ban_chat_member(chat_id, target_id)
    except Exception as e:
        logger.warning(f"Ban xatosi: {e}")
    await mute_user(chat_id, target_id)
    try:
        await callback.message.delete()
    except Exception:
        pass
    await bot.send_message(
        chat_id,
        f"🚫 <b>{target_name}</b> bloklandi!\n📝 Sabab: {reason_text}\n👮 Admin: {callback.from_user.full_name}",
        parse_mode="HTML"
    )
    await callback.answer(f"✅ {target_name} bloklandi!")


@dp.callback_query(F.data == "gadmin_unban_menu")
async def cb_gadmin_unban_menu(callback: CallbackQuery):
    if not is_admin(callback.from_user.id):
        await callback.answer("❌ Ruxsat yo'q!", show_alert=True)
        return
    bans = db.get_banned_list()
    if not bans:
        await callback.answer("✅ Blocklangan foydalanuvchilar yo'q!", show_alert=True)
        return
    await callback.message.edit_text(
        f"✅ <b>BLOKDAN CHIQARISH</b>\n\nBlocklangan: <b>{len(bans)}</b> ta\nTanlang:",
        parse_mode="HTML",
        reply_markup=unban_list_kb(bans)
    )
    await callback.answer()


@dp.callback_query(F.data.startswith("gadmin_unban_"))
async def cb_gadmin_unban(callback: CallbackQuery):
    if not is_admin(callback.from_user.id):
        await callback.answer("❌ Ruxsat yo'q!", show_alert=True)
        return
    target_id = int(callback.data.split("_")[2])
    chat_id = callback.message.chat.id
    ud = db.get_user(target_id)
    target_name = ud.get('name', f"ID:{target_id}") if ud else f"ID:{target_id}"
    db.unban_user(target_id)
    try:
        await bot.unban_chat_member(chat_id, target_id)
    except Exception as e:
        logger.warning(f"Unban xatosi: {e}")
    try:
        await callback.message.delete()
    except Exception:
        pass
    await bot.send_message(
        chat_id,
        f"✅ <b>{target_name}</b> blokdan chiqarildi!\n👮 Admin: {callback.from_user.full_name}",
        parse_mode="HTML"
    )
    await callback.answer(f"✅ {target_name} blokdan chiqarildi!")


@dp.callback_query(F.data == "gadmin_top")
async def cb_gadmin_top(callback: CallbackQuery):
    if not is_admin(callback.from_user.id):
        await callback.answer("❌ Ruxsat yo'q!", show_alert=True)
        return
    rows = db.get_top(10)
    if not rows:
        await callback.answer("📊 Hali statistika yo'q!", show_alert=True)
        return
    medals = ["🥇", "🥈", "🥉"] + ["🏅"] * 7
    text = "🏆 <b>TOP 10 O'YINCHILAR</b>\n\n"
    for i, (name, played, won, coins, winrate) in enumerate(rows):
        text += f"{medals[i]} <b>{name}</b> — {won}/{played} • {winrate}% • {coins}💰\n"
    await callback.message.edit_text(text, parse_mode="HTML", reply_markup=back_kb("group_admin_panel"))
    await callback.answer()


# ==================== MINI-GAMES MENU ====================

@dp.callback_query(F.data == "mini_games")
async def cb_mini_games(callback: CallbackQuery):
    user = callback.from_user
    db.ensure_user(user.id, user.full_name)
    user_data = db.get_user(user.id)
    streak = db.get_win_streak(user.id)
    streak_line = f"\n🌟 G'alaba seriyangiz: <b>{streak}</b>" if streak > 0 else ""
    await callback.message.edit_text(
        f"🎲 <b>MINI-O'YINLAR</b>\n\n"
        f"💰 Coinlaringiz: <b>{user_data['coins']}</b>{streak_line}\n\n"
        f"Quyidagilardan birini tanlang:",
        parse_mode="HTML",
        reply_markup=mini_games_kb()
    )
    await callback.answer()


# ==================== 1. RULET ====================

@dp.callback_query(F.data == "mini_rulet")
async def cb_mini_rulet(callback: CallbackQuery):
    user = callback.from_user
    db.ensure_user(user.id, user.full_name)
    user_data = db.get_user(user.id)
    await callback.message.edit_text(
        f"🎰 <b>RULET</b>\n\n"
        f"💰 Coinlaringiz: <b>{user_data['coins']}</b>\n\n"
        f"Qancha coin tikmoqchisiz?\n"
        f"<i>✅ 50% ehtimollik — g'alaba = 2x coin!\n"
        f"❌ Yutqazsangiz — tikkan coinlaringiz ketadi.</i>",
        parse_mode="HTML",
        reply_markup=rulet_bet_kb()
    )
    await callback.answer()


@dp.callback_query(F.data.startswith("rulet_"))
async def cb_rulet_bet(callback: CallbackQuery):
    user = callback.from_user
    bet = int(callback.data.split("_")[1])
    db.ensure_user(user.id, user.full_name)
    user_data = db.get_user(user.id)

    if user_data['coins'] < bet:
        await callback.answer(f"❌ Yetarli coin yo'q! Sizda: {user_data['coins']}💰", show_alert=True)
        return

    RULET_EMOJIS = ["🍋", "🍒", "💎", "🔔", "⭐", "🃏", "🎯", "🌟"]
    spin = [random.choice(RULET_EMOJIS) for _ in range(3)]
    won = random.random() < 0.5

    if won:
        winnings = bet
        db.update_stat(user.id, coins=winnings)
        result_text = f"✅ <b>G'ALABA!</b> +{winnings}💰"
        result_emoji = "🎉"
    else:
        db.update_stat(user.id, coins=-bet)
        result_text = f"❌ <b>Yutqazdingiz!</b> -{bet}💰"
        result_emoji = "😢"

    # Kunlik vazifa: rulet_done
    db.update_daily_mission(user.id, 'rulet_done')
    user_data = db.get_user(user.id)
    await callback.message.edit_text(
        f"🎰 <b>RULET NATIJASI</b>\n\n"
        f"🎡 {' | '.join(spin)}\n\n"
        f"{result_emoji} {result_text}\n\n"
        f"💰 Hozirgi coinlaringiz: <b>{user_data['coins']}</b>",
        parse_mode="HTML",
        reply_markup=rulet_bet_kb()
    )
    await callback.answer()


# ==================== 2. TOSH-QAYCHI-QO'GOZ ====================

@dp.callback_query(F.data == "mini_tqq")
async def cb_mini_tqq(callback: CallbackQuery):
    user = callback.from_user
    db.ensure_user(user.id, user.full_name)
    user_data = db.get_user(user.id)
    await callback.message.edit_text(
        f"✊ <b>TOSH-QAYCHI-QO'GOZ</b>\n\n"
        f"💰 Coinlaringiz: <b>{user_data['coins']}</b>\n\n"
        f"Birinchi, necha coin tikmoqchisiz?\n"
        f"<i>(0 tanlasangiz — pulisiz o'ynaysiz)</i>",
        parse_mode="HTML",
        reply_markup=tqq_bet_kb()
    )
    await callback.answer()


@dp.callback_query(F.data.startswith("tqqbet_"))
async def cb_tqq_bet(callback: CallbackQuery, state: FSMContext):
    bet = int(callback.data.split("_")[1])
    user = callback.from_user
    db.ensure_user(user.id, user.full_name)
    user_data = db.get_user(user.id)
    if bet > 0 and user_data['coins'] < bet:
        await callback.answer(f"❌ Yetarli coin yo'q! Sizda: {user_data['coins']}💰", show_alert=True)
        return
    await state.update_data(tqq_bet=bet)
    await callback.message.edit_text(
        f"✊ <b>TOSH-QAYCHI-QO'GOZ</b>\n\n"
        f"💰 Tikish: <b>{bet if bet > 0 else 'Pulis'}</b>{'💰' if bet > 0 else ''}\n\n"
        f"Tanlovingizni qiling:",
        parse_mode="HTML",
        reply_markup=tqq_kb()
    )
    await callback.answer()


@dp.callback_query(F.data.startswith("tqq_"))
async def cb_tqq_play(callback: CallbackQuery, state: FSMContext):
    choice_map = {"tosh": "✊ Tosh", "qaychi": "✌️ Qaychi", "qogoz": "🖐 Qog'oz"}
    win_map = {"tosh": "qaychi", "qaychi": "qogoz", "qogoz": "tosh"}
    key = callback.data.split("_")[1]
    if key not in choice_map:
        return
    user = callback.from_user
    db.ensure_user(user.id, user.full_name)
    data = await state.get_data()
    bet = data.get("tqq_bet", 0)
    user_data = db.get_user(user.id)

    bot_keys = list(choice_map.keys())
    bot_choice = random.choice(bot_keys)

    if key == bot_choice:
        result = "🤝 <b>DURRANG!</b>"
        coins_change = 0
    elif win_map[key] == bot_choice:
        result = f"🏆 <b>G'ALABA!</b> +{bet}💰" if bet > 0 else "🏆 <b>G'ALABA!</b>"
        if bet > 0:
            db.update_stat(user.id, coins=bet)
        coins_change = bet
    else:
        result = f"❌ <b>Yutqazdingiz!</b> -{bet}💰" if bet > 0 else "❌ <b>Yutqazdingiz!</b>"
        if bet > 0:
            db.update_stat(user.id, coins=-bet)
        coins_change = -bet

    await state.clear()
    user_data = db.get_user(user.id)
    await callback.message.edit_text(
        f"✊ <b>TOSH-QAYCHI-QO'GOZ NATIJASI</b>\n\n"
        f"Siz: <b>{choice_map[key]}</b>\n"
        f"Bot: <b>{choice_map[bot_choice]}</b>\n\n"
        f"{result}\n\n"
        f"💰 Coinlaringiz: <b>{user_data['coins']}</b>",
        parse_mode="HTML",
        reply_markup=back_kb("mini_games")
    )
    await callback.answer()


# ==================== 3. COIN SOVG'A ====================

@dp.callback_query(F.data == "mini_sovga")
async def cb_mini_sovga(callback: CallbackQuery, state: FSMContext):
    user = callback.from_user
    db.ensure_user(user.id, user.full_name)
    user_data = db.get_user(user.id)
    await state.set_state(BotStates.waiting_sovga_id)
    await callback.message.edit_text(
        f"🎁 <b>COIN SOVG'A BERISH</b>\n\n"
        f"💰 Sizda: <b>{user_data['coins']}</b> coin\n\n"
        f"Kimga coin yubormoqchisiz?\n"
        f"<b>Foydalanuvchining Telegram ID sini yozing</b>\n"
        f"<i>(ID ni bilish uchun @userinfobot ga /start bosing)</i>",
        parse_mode="HTML",
        reply_markup=back_kb("mini_games")
    )
    await callback.answer()


@dp.callback_query(F.data == "mini_luck")
async def cb_mini_luck(callback: CallbackQuery):
    user = callback.from_user
    db.ensure_user(user.id, user.full_name)
    import hashlib
    from datetime import date
    seed = f"{user.id}{date.today()}"
    h = int(hashlib.md5(seed.encode()).hexdigest(), 16)
    luck = (h % 101)
    if luck >= 80:
        icon = "🌟🌟🌟"
        msg = "Bugun sizning kuningiz! Hamma narsa yaxshi bo'ladi!"
    elif luck >= 60:
        icon = "😊"
        msg = "Yaxshi kun. Qo'lingizdan keladi!"
    elif luck >= 40:
        icon = "😐"
        msg = "O'rtacha kun. Ehtiyot bo'ling."
    elif luck >= 20:
        icon = "😬"
        msg = "Bugun ehtiyotkor bo'ling. Xavf bor."
    else:
        icon = "💀"
        msg = "Bugun uyda o'tiring... Mafiadan uzoq yuring! 😅"

    streak = db.get_win_streak(user.id)
    streak_line = f"\n\n🌟 G'alaba seriyangiz: <b>{streak}</b>" if streak > 0 else ""
    await callback.message.edit_text(
        f"🔮 <b>BUGUNGI OMAD BASHORATI</b>\n\n"
        f"{icon} <b>Omad darajasi: {luck}%</b>\n\n"
        f"<i>{msg}</i>{streak_line}\n\n"
        f"<i>📅 Bugun uchun bashorat (har kuni yangilanadi)</i>",
        parse_mode="HTML",
        reply_markup=back_kb("mini_games")
    )
    await callback.answer()


# ==================== 4. TAQDIR BASHORATI ====================

@dp.callback_query(F.data == "menu_fate")
async def cb_fate(callback: CallbackQuery):
    user = callback.from_user
    db.ensure_user(user.id, user.full_name)

    FATE_ROLES = [
        ("🔫 Mafia", "Siz shubhali ko'rinasiz... Tunda pichirlab gaplashingiz sezilyapti!"),
        ("👑 Donn", "Siz tabiiy lider! Hamma sizi eshitadi, hatto Sherif ham!"),
        ("🔍 Sherif", "Siz haqiqatni his qilasiz. Yolg'onchi ko'zlaringizdan qochib keta olmaydi!"),
        ("💉 Doktor", "Siz boshqalarni himoya qiluvchisiz. Ulug' qalb!"),
        ("💋 Ayg'oqchi", "Siz sirlarni yaxshi ko'rasiz. Hech kim sizning rejangizni bilmaydi!"),
        ("👥 Fuqaro", "Siz oddiy, lekin aqlli fuqarosiz. Ba'zan oddiylik kuch!"),
    ]
    role_name, role_desc = random.choice(FATE_ROLES)

    lucky_words = [
        "Omad bilan!", "Bu o'yinda g'alaba sizniki!", "Ehtiyot bo'ling!",
        "Hamma sizga ishonadi!", "Sirlaring yaxshi saqlang!", "Botga yozib turing!",
    ]
    lucky = random.choice(lucky_words)

    await callback.message.edit_text(
        f"🔮 <b>TAQDIR BASHORATI</b>\n\n"
        f"✨ Keyingi o'yiningizda siz...\n\n"
        f"<b>{role_name}</b> bo'lasiz!\n\n"
        f"<i>{role_desc}</i>\n\n"
        f"💫 <b>{lucky}</b>",
        parse_mode="HTML",
        reply_markup=fate_result_kb()
    )
    await callback.answer()


# ==================== 5. ASSASSIN TOP ====================

@dp.callback_query(F.data == "mini_killtop")
async def cb_killtop(callback: CallbackQuery):
    rows = db.get_top_kills(10)
    if not rows:
        await callback.answer("🗡️ Hali hech kim o'ldirmagan!", show_alert=True)
        return
    medals = ["🥇", "🥈", "🥉"] + ["🏅"] * 7
    text = "🗡️ <b>ASSASSIN TOP — Ko'p o'ldirganlar</b>\n\n"
    for i, (name, kills, played) in enumerate(rows):
        kpg = round(kills / played, 1) if played else 0
        text += f"{medals[i]} <b>{name}</b> — {kills} 💀 ({kpg}/o'yin)\n"
    await callback.message.edit_text(text, parse_mode="HTML", reply_markup=back_kb("mini_games"))
    await callback.answer()


# ==================== 6. GURUH SOZLAMALARI (Admin) ====================

@dp.callback_query(F.data == "gadmin_settings")
async def cb_gadmin_settings(callback: CallbackQuery):
    if not is_admin(callback.from_user.id):
        await callback.answer("❌ Ruxsat yo'q!", show_alert=True)
        return
    chat_id = callback.message.chat.id
    settings = db.get_chat_settings(chat_id)
    await callback.message.edit_text(
        f"⚙️ <b>GURUH O'YIN SOZLAMALARI</b>\n\n"
        f"⏱ Qo'shilish vaqti: <b>{settings['join_time']} soniya</b>\n"
        f"🌙 Tun vaqti: <b>{settings['night_time']} soniya</b>\n"
        f"☀️ Kun (muhokama): <b>{settings['discuss_time']} soniya</b>\n"
        f"🗳️ Ovoz berish: <b>{settings['vote_time']} soniya</b>\n\n"
        f"<i>O'zgartirish uchun quyidagi tugmani bosing:</i>",
        parse_mode="HTML",
        reply_markup=game_settings_kb(settings)
    )
    await callback.answer()


@dp.callback_query(F.data.regexp(r"^gset_(join|night|discuss|vote|reset)$"))
async def cb_gset_category(callback: CallbackQuery):
    if not is_admin(callback.from_user.id):
        await callback.answer("❌ Ruxsat yo'q!", show_alert=True)
        return
    key_map = {"gset_join": "join", "gset_night": "night", "gset_discuss": "discuss", "gset_vote": "vote", "gset_reset": "reset"}
    key = key_map.get(callback.data)
    if not key:
        return
    chat_id = callback.message.chat.id
    if key == "reset":
        db.update_chat_settings(chat_id, join_time=60, night_time=40, discuss_time=90, vote_time=45)
        settings = db.get_chat_settings(chat_id)
        await callback.message.edit_text(
            f"✅ <b>Sozlamalar standartga qaytarildi!</b>\n\n"
            f"⏱ Qo'shilish: <b>{settings['join_time']}s</b>\n"
            f"🌙 Tun: <b>{settings['night_time']}s</b>\n"
            f"☀️ Kun: <b>{settings['discuss_time']}s</b>\n"
            f"🗳️ Ovoz: <b>{settings['vote_time']}s</b>",
            parse_mode="HTML",
            reply_markup=game_settings_kb(settings)
        )
        await callback.answer("✅ Standartga qaytarildi!")
        return
    labels = {"join": "Qo'shilish", "night": "Tun", "discuss": "Kun muhokama", "vote": "Ovoz berish"}
    await callback.message.edit_text(
        f"⚙️ <b>{labels[key]} vaqtini tanlang:</b>",
        parse_mode="HTML",
        reply_markup=gset_time_kb(key)
    )
    await callback.answer()


@dp.callback_query(F.data.regexp(r"^gset_(join|night|discuss|vote)_\d+$"))
async def cb_gset_value(callback: CallbackQuery):
    if not is_admin(callback.from_user.id):
        await callback.answer("❌ Ruxsat yo'q!", show_alert=True)
        return
    parts = callback.data.split("_")
    key = parts[1]
    val = int(parts[2])
    chat_id = callback.message.chat.id
    db_key = f"{key}_time"
    db.update_chat_settings(chat_id, **{db_key: val})
    settings = db.get_chat_settings(chat_id)
    await callback.message.edit_text(
        f"✅ <b>Saqlandi!</b>\n\n"
        f"⏱ Qo'shilish: <b>{settings['join_time']}s</b>\n"
        f"🌙 Tun: <b>{settings['night_time']}s</b>\n"
        f"☀️ Kun: <b>{settings['discuss_time']}s</b>\n"
        f"🗳️ Ovoz: <b>{settings['vote_time']}s</b>",
        parse_mode="HTML",
        reply_markup=game_settings_kb(settings)
    )
    await callback.answer(f"✅ {key} = {val}s")


# ==================== 7. STREAK MA'LUMOTLARI ====================

@dp.callback_query(F.data == "menu_streak")
async def cb_streak(callback: CallbackQuery):
    user = callback.from_user
    db.ensure_user(user.id, user.full_name)
    streak = db.get_win_streak(user.id)
    if streak == 0:
        streak_text = "Hali seriya yo'q. G'alaba qozonishni boshlang!"
        emoji = "😴"
    elif streak == 1:
        streak_text = "Yaxshi boshlanish! Davom eting!"
        emoji = "😊"
    elif streak == 2:
        streak_text = "2 ketma-ket g'alaba! Zo'r!"
        emoji = "🔥"
    elif streak < 5:
        streak_text = f"{streak} g'alaba! Siz kuchli o'yinchisiz!"
        emoji = "⚡"
    else:
        streak_text = f"{streak} ketma-ket! Siz afsonaviy o'yinchisiz!"
        emoji = "👑"

    bonus_next = (streak + 1) * 15 if streak > 0 else 15
    await callback.message.edit_text(
        f"🌟 <b>G'ALABA SERIYASI</b>\n\n"
        f"{emoji} Hozirgi seriyangiz: <b>{streak}</b>\n\n"
        f"<i>{streak_text}</i>\n\n"
        f"💡 Keyingi g'alabada: <b>+{bonus_next}💰</b> bonus!\n\n"
        f"<b>Seriya bonuslari:</b>\n"
        f"  2 ketma-ket → +30💰\n"
        f"  3 ketma-ket → +45💰\n"
        f"  5 ketma-ket → +75💰\n"
        f"  10 ketma-ket → +150💰",
        parse_mode="HTML",
        reply_markup=streak_kb()
    )
    await callback.answer()


# ==================== 8. FSM — COIN SOVGA ====================

# private_message_handler da ham ushlash kerak — quyida ko'ramiz
# Buni private_message_handler ga qo'shamiz (yangi holat tekshiruvlari)


# ==================== 9. GURUH ADMIN PANELGA SOZLAMALAR QO'SHISH ====================

# group_admin_panel_kb ga "Sozlamalar" tugmasi qo'shish
# Buni keyboards.py da yangilaymiz

# ==================== 10. TOP MENYUSI KENGAYTIRISH ====================

@dp.callback_query(F.data == "top_menu")
async def cb_top_menu(callback: CallbackQuery):
    await callback.message.edit_text(
        "🏆 <b>REYTING TANLANG</b>\n\nQaysi reytingni ko'rmoqchisiz?",
        parse_mode="HTML",
        reply_markup=back_kb("menu_back")
    )
    await callback.answer()


# ==================== V4 — 20 YANGI FUNKSIYA ====================

# — — — — — — — — — — — — — — — — — — — — — — — — —
# BLACKJACK YORDAMCHI
# — — — — — — — — — — — — — — — — — — — — — — — — —

_BJ_CARDS = ['A', '2', '3', '4', '5', '6', '7', '8', '9', '10', 'J', 'Q', 'K']
_BJ_SUITS = ['♠', '♥', '♦', '♣']


def _bj_value(card: str) -> int:
    if card in ('J', 'Q', 'K'):
        return 10
    if card == 'A':
        return 11
    return int(card)


def _bj_total(cards: list) -> int:
    total = sum(_bj_value(c[0]) for c in cards)
    aces = sum(1 for c in cards if c[0] == 'A')
    while total > 21 and aces:
        total -= 10
        aces -= 1
    return total


def _bj_draw() -> str:
    return f"{random.choice(_BJ_CARDS)}{random.choice(_BJ_SUITS)}"


def _bj_hand_str(cards: list) -> str:
    return ' '.join(cards)


# 1. BLACKJACK MENU
@dp.callback_query(F.data == "mini_blackjack")
async def cb_mini_blackjack(callback: CallbackQuery):
    user = callback.from_user
    db.ensure_user(user.id, user.full_name)
    info = db.get_user(user.id)
    await callback.message.edit_text(
        f"🃏 <b>BLACKJACK (21)</b>\n\n"
        f"Qoidalar:\n"
        f"• 21 ga eng yaqin bo'lgan g'alaba qozonadi\n"
        f"• 21 dan oshsangiz — <b>bust</b> (yutqazasiz)\n"
        f"• Blackjack (A + 10) = 1.5x g'alaba\n"
        f"• A = 1 yoki 11\n\n"
        f"💰 Sizda: <b>{info['coins']}💰</b>\n\n"
        f"<b>Tikish miqdorini tanlang:</b>",
        parse_mode="HTML",
        reply_markup=blackjack_bet_kb()
    )
    await callback.answer()


@dp.callback_query(F.data.startswith("bj_bet_"))
async def cb_bj_bet(callback: CallbackQuery, state: FSMContext):
    user = callback.from_user
    bet = int(callback.data.split("_")[2])
    info = db.get_user(user.id)
    if info['coins'] < bet:
        await callback.answer("❌ Coin yetarli emas!", show_alert=True)
        return
    p1 = _bj_draw(); p2 = _bj_draw()
    d1 = _bj_draw()
    session = {'bet': bet, 'player_cards': [p1, p2], 'dealer_cards': [d1]}
    _bj_sessions[user.id] = session
    await state.set_state(BotStates.bj_playing)
    ptotal = _bj_total([p1, p2])
    db.add_coins(user.id, -bet)
    text = (
        f"🃏 <b>BLACKJACK</b> | Tikish: {bet}💰\n\n"
        f"🧑 Sizning kartalaringiz: {_bj_hand_str([p1,p2])} → <b>{ptotal}</b>\n"
        f"🤖 Dilerning karta: {d1} + ❓\n\n"
    )
    if ptotal == 21:
        winnings = int(bet * 1.5)
        db.add_coins(user.id, bet + winnings)
        await state.clear()
        _bj_sessions.pop(user.id, None)
        await callback.message.edit_text(
            text + f"🎉 <b>BLACKJACK!</b> Siz {winnings}💰 yutdingiz!", parse_mode="HTML",
            reply_markup=back_kb("mini_blackjack")
        )
    else:
        can_double = info['coins'] >= bet * 2
        await callback.message.edit_text(
            text + "Nima qilasiz?", parse_mode="HTML",
            reply_markup=blackjack_play_kb(ptotal, can_double=can_double)
        )
    await callback.answer()


@dp.callback_query(F.data == "bj_hit")
async def cb_bj_hit(callback: CallbackQuery, state: FSMContext):
    user = callback.from_user
    s = _bj_sessions.get(user.id)
    if not s:
        await callback.answer("O'yin topilmadi!", show_alert=True); return
    new_card = _bj_draw()
    s['player_cards'].append(new_card)
    ptotal = _bj_total(s['player_cards'])
    text = (
        f"🃏 <b>BLACKJACK</b> | Tikish: {s['bet']}💰\n\n"
        f"🧑 Sizning kartalaringiz: {_bj_hand_str(s['player_cards'])} → <b>{ptotal}</b>\n"
        f"🤖 Dilerning karta: {s['dealer_cards'][0]} + ❓\n\n"
    )
    if ptotal > 21:
        await state.clear(); _bj_sessions.pop(user.id, None)
        await callback.message.edit_text(
            text + f"💥 <b>Bust!</b> Siz yutqazdingiz. -{s['bet']}💰", parse_mode="HTML",
            reply_markup=back_kb("mini_blackjack")
        )
    elif ptotal == 21:
        winnings = int(s['bet'] * 1.5)
        db.add_coins(user.id, s['bet'] + winnings)
        await state.clear(); _bj_sessions.pop(user.id, None)
        await callback.message.edit_text(
            text + f"🎉 <b>21! Siz {winnings}💰 yutdingiz!</b>", parse_mode="HTML",
            reply_markup=back_kb("mini_blackjack")
        )
    else:
        await callback.message.edit_text(
            text + "Nima qilasiz?", parse_mode="HTML",
            reply_markup=blackjack_play_kb(ptotal)
        )
    await callback.answer()


@dp.callback_query(F.data == "bj_stand")
async def cb_bj_stand(callback: CallbackQuery, state: FSMContext):
    user = callback.from_user
    s = _bj_sessions.get(user.id)
    if not s:
        await callback.answer("O'yin topilmadi!", show_alert=True); return
    while _bj_total(s['dealer_cards']) < 17:
        s['dealer_cards'].append(_bj_draw())
    ptotal = _bj_total(s['player_cards'])
    dtotal = _bj_total(s['dealer_cards'])
    dealer_str = _bj_hand_str(s['dealer_cards'])
    player_str = _bj_hand_str(s['player_cards'])
    text = (
        f"🃏 <b>BLACKJACK — NATIJA</b>\n\n"
        f"🧑 Siz: {player_str} → <b>{ptotal}</b>\n"
        f"🤖 Diler: {dealer_str} → <b>{dtotal}</b>\n\n"
    )
    if dtotal > 21 or ptotal > dtotal:
        db.add_coins(user.id, s['bet'] * 2)
        text += f"🎉 <b>Siz g'alaba qozonding! +{s['bet']}💰</b>"
    elif ptotal == dtotal:
        db.add_coins(user.id, s['bet'])
        text += "🤝 <b>Draw (Tenglik). Tikish qaytarildi.</b>"
    else:
        text += f"😔 <b>Diler g'alaba qozondi. -{s['bet']}💰</b>"
    await state.clear(); _bj_sessions.pop(user.id, None)
    await callback.message.edit_text(text, parse_mode="HTML", reply_markup=back_kb("mini_blackjack"))
    await callback.answer()


@dp.callback_query(F.data == "bj_double")
async def cb_bj_double(callback: CallbackQuery, state: FSMContext):
    user = callback.from_user
    s = _bj_sessions.get(user.id)
    if not s:
        await callback.answer("O'yin topilmadi!", show_alert=True); return
    info = db.get_user(user.id)
    if info['coins'] < s['bet']:
        await callback.answer("❌ Double uchun coin yetarli emas!", show_alert=True); return
    db.add_coins(user.id, -s['bet'])
    s['bet'] *= 2
    s['player_cards'].append(_bj_draw())
    ptotal = _bj_total(s['player_cards'])
    while _bj_total(s['dealer_cards']) < 17:
        s['dealer_cards'].append(_bj_draw())
    dtotal = _bj_total(s['dealer_cards'])
    text = (
        f"🃏 <b>BLACKJACK — DOUBLE DOWN!</b>\n\n"
        f"🧑 Siz: {_bj_hand_str(s['player_cards'])} → <b>{ptotal}</b>\n"
        f"🤖 Diler: {_bj_hand_str(s['dealer_cards'])} → <b>{dtotal}</b>\n\n"
    )
    if ptotal > 21:
        text += f"💥 <b>Bust! -{s['bet']}💰</b>"
    elif dtotal > 21 or ptotal > dtotal:
        db.add_coins(user.id, s['bet'] * 2)
        text += f"🎉 <b>G'alaba! +{s['bet']}💰</b>"
    elif ptotal == dtotal:
        db.add_coins(user.id, s['bet'])
        text += "🤝 <b>Tenglik.</b>"
    else:
        text += f"😔 <b>Yutqazdingiz. -{s['bet']}💰</b>"
    await state.clear(); _bj_sessions.pop(user.id, None)
    await callback.message.edit_text(text, parse_mode="HTML", reply_markup=back_kb("mini_blackjack"))
    await callback.answer()


# 2. SIRLI QUTICHA
@dp.callback_query(F.data == "mini_secretbox")
async def cb_mini_secretbox(callback: CallbackQuery):
    user = callback.from_user
    db.ensure_user(user.id, user.full_name)
    info = db.get_user(user.id)
    await callback.message.edit_text(
        f"🎁 <b>SIRLI QUTICHA</b>\n\n"
        f"Ichida nima bor? Bilmaysan! 🤔\n"
        f"Yutishingiz mumkin: 2x, 3x, 5x yoki... 0!\n\n"
        f"💰 Sizda: <b>{info['coins']}💰</b>\n\n"
        f"<b>Qaysi qutichani tanlamoqchisiz?</b>",
        parse_mode="HTML",
        reply_markup=sirli_quticha_kb()
    )
    await callback.answer()


@dp.callback_query(F.data.startswith("box_"))
async def cb_box_open(callback: CallbackQuery):
    user = callback.from_user
    cost = int(callback.data.split("_")[1])
    info = db.get_user(user.id)
    if info['coins'] < cost:
        await callback.answer(f"❌ Kerakli: {cost}💰. Sizda: {info['coins']}💰", show_alert=True)
        return
    db.add_coins(user.id, -cost)
    outcomes = [
        (0.25, 0, "💀 Bo'sh quticha! Baxt kulib baqmadi."),
        (0.30, 2, "😊 2x yutdingiz!"),
        (0.25, 3, "🎉 3x! Zo'r!"),
        (0.15, 5, "🔥 5x! Juda baxtlisiz!"),
        (0.05, 10, "👑 10x!!! AFSONAVIY!!!"),
    ]
    roll = random.random()
    cumulative = 0.0
    won_mult, result_text = 0, ""
    for prob, mult, txt in outcomes:
        cumulative += prob
        if roll <= cumulative:
            won_mult, result_text = mult, txt
            break
    winnings = cost * won_mult
    if winnings > 0:
        db.add_coins(user.id, winnings)
    emoji = "🎁"
    await callback.message.edit_text(
        f"{emoji} <b>QUTICHA OCHILDI!</b>\n\n"
        f"Tikish: {cost}💰\n\n"
        f"{result_text}\n"
        f"{'➕' if winnings > 0 else '➖'} {winnings if winnings > 0 else cost}💰",
        parse_mode="HTML",
        reply_markup=back_kb("mini_secretbox")
    )
    await callback.answer()


# 3. SPINNING WHEEL
@dp.callback_query(F.data == "mini_wheel")
async def cb_mini_wheel(callback: CallbackQuery):
    user = callback.from_user
    db.ensure_user(user.id, user.full_name)
    jackpot = db.get_jackpot()
    await callback.message.edit_text(
        f"🎪 <b>SPINNING WHEEL</b>\n\n"
        f"Sektorlar:\n"
        f"🟢 5💰  🟡 10💰  🔵 25💰\n"
        f"🟠 50💰  🔴 100💰  ⭐ JACKPOT\n"
        f"💀 Hamma yo'qoladi\n\n"
        f"Har o'yinda 5% jackpotga o'tadi!\n"
        f"💰 <b>Hozirgi jackpot: {jackpot}💰</b>",
        parse_mode="HTML",
        reply_markup=spinning_wheel_kb(jackpot)
    )
    await callback.answer()


@dp.callback_query(F.data == "wheel_spin")
async def cb_wheel_spin(callback: CallbackQuery):
    user = callback.from_user
    cost = 20
    info = db.get_user(user.id)
    if info['coins'] < cost:
        await callback.answer("❌ 20💰 kerak!", show_alert=True); return
    db.add_coins(user.id, -cost)
    jackpot_contrib = max(1, cost // 5)
    db.add_to_jackpot(jackpot_contrib)
    sectors = [
        (0.20, 5, "🟢 5💰"),
        (0.20, 10, "🟡 10💰"),
        (0.20, 25, "🔵 25💰"),
        (0.15, 50, "🟠 50💰"),
        (0.10, 100, "🔴 100💰"),
        (0.10, 0, "💀 Hamma yo'qoladi!"),
        (0.05, -1, "⭐ JACKPOT!!!"),
    ]
    roll = random.random()
    cum = 0.0
    prize, label = 0, ""
    for prob, p, lbl in sectors:
        cum += prob
        if roll <= cum:
            prize, label = p, lbl
            break
    if prize == -1:
        prize = db.claim_jackpot(user.id)
        result = f"⭐ <b>JACKPOT! Siz {prize}💰 yutdingiz!!!</b>"
    elif prize > 0:
        db.add_coins(user.id, prize)
        result = f"🎉 <b>{label} — +{prize}💰!</b>"
    else:
        result = f"💀 <b>Yutqazdingiz! -{cost}💰</b>"
    jackpot_new = db.get_jackpot()
    await callback.message.edit_text(
        f"🎪 <b>SPINNING WHEEL</b>\n\n"
        f"🌀 Aylanmoqda...\n\n"
        f"{result}\n\n"
        f"💰 Jackpot hozir: {jackpot_new}💰",
        parse_mode="HTML",
        reply_markup=spinning_wheel_kb(jackpot_new)
    )
    await callback.answer("🎪 Aylandi!")


# 4. DUELLO
@dp.callback_query(F.data == "mini_duello")
async def cb_mini_duello(callback: CallbackQuery, state: FSMContext):
    user = callback.from_user
    db.ensure_user(user.id, user.full_name)
    await state.set_state(BotStates.waiting_duello_id)
    await callback.message.edit_text(
        "🎯 <b>DUELLO</b>\n\n"
        "Raqibingizning Telegram <b>user ID</b> sini yuboring.\n"
        "(Bot ular nomidan o'ynaydi)\n\n"
        "❌ Bekor qilish uchun /bekor",
        parse_mode="HTML"
    )
    await callback.answer()


@dp.message(BotStates.waiting_duello_id)
async def msg_duello_id(message: Message, state: FSMContext):
    try:
        target_id = int(message.text.strip())
    except ValueError:
        await message.answer("❌ Faqat raqam kiriting!"); return
    if target_id == message.from_user.id:
        await message.answer("❌ O'zingiz bilan duel bo'lmaydi!"); return
    target = db.get_user(target_id)
    if not target:
        await message.answer("❌ Bu ID da foydalanuvchi topilmadi!"); return
    await state.update_data(duello_target=target_id, duello_name=target['name'])
    await state.set_state(BotStates.waiting_duello_amount)
    await message.answer(
        f"🎯 Raqib: <b>{target['name']}</b>\n\nQancha tikasiz?",
        parse_mode="HTML",
        reply_markup=duello_bet_kb()
    )


@dp.callback_query(F.data.startswith("duel_bet_"))
async def cb_duel_bet(callback: CallbackQuery, state: FSMContext):
    user = callback.from_user
    bet = int(callback.data.split("_")[2])
    data = await state.get_data()
    target_id = data.get('duello_target')
    target_name = data.get('duello_name', 'Raqib')
    if not target_id:
        await callback.answer("Duel ma'lumoti topilmadi!", show_alert=True); return
    info = db.get_user(user.id)
    if not info or info['coins'] < bet:
        await callback.answer(f"❌ {bet}💰 kerak!", show_alert=True); return
    target_info = db.get_user(target_id)
    if not target_info or target_info['coins'] < bet:
        await callback.answer(f"❌ Raqibda {bet}💰 yo'q!", show_alert=True); return
    await state.clear()
    winner = random.choice([user.id, target_id])
    loser_id = target_id if winner == user.id else user.id
    winner_name = user.full_name if winner == user.id else target_name
    loser_name = target_name if winner == user.id else user.full_name
    db.add_coins(loser_id, -bet)
    db.add_coins(winner, bet)
    weapons = ["🗡️", "🔫", "🏹", "💣", "⚔️", "🪃"]
    w = random.choice(weapons)
    await callback.message.edit_text(
        f"🎯 <b>DUELLO NATIJASI</b>\n\n"
        f"{w} <b>{winner_name}</b> g'alaba qozondi!\n"
        f"💸 <b>{loser_name}</b> {bet}💰 yo'qotdi!\n\n"
        f"🏆 G'olib: <b>+{bet}💰</b>",
        parse_mode="HTML",
        reply_markup=back_kb("mini_games")
    )
    await callback.answer()


# 5. BIO O'RNATISH
@dp.callback_query(F.data == "profile_setbio")
async def cb_profile_setbio(callback: CallbackQuery, state: FSMContext):
    user = callback.from_user
    current = db.get_bio(user.id) or "Yo'q"
    await state.set_state(BotStates.waiting_bio)
    await callback.message.edit_text(
        f"📝 <b>BIO O'RNATISH</b>\n\n"
        f"Hozirgi bio: <i>{current}</i>\n\n"
        f"Yangi bio yuboring (max 100 belgi):\n"
        f"❌ Bekor qilish: /bekor",
        parse_mode="HTML"
    )
    await callback.answer()


@dp.message(BotStates.waiting_bio)
async def msg_set_bio(message: Message, state: FSMContext):
    bio = message.text.strip()[:100]
    db.set_bio(message.from_user.id, bio)
    await state.clear()
    await message.answer(
        f"✅ <b>Bio saqlandi!</b>\n\n📝 {bio}",
        parse_mode="HTML",
        reply_markup=back_kb("menu_profile")
    )


# 6. O'YINCHI QIDIRISH
@dp.callback_query(F.data == "menu_findplayer")
async def cb_find_player(callback: CallbackQuery, state: FSMContext):
    await state.set_state(BotStates.waiting_find_player)
    await callback.message.edit_text(
        "🔍 <b>O'YINCHI QIDIRISH</b>\n\nTelegram <b>user ID</b> ni yuboring:\n❌ /bekor",
        parse_mode="HTML"
    )
    await callback.answer()


@dp.message(BotStates.waiting_find_player)
async def msg_find_player(message: Message, state: FSMContext):
    try:
        target_id = int(message.text.strip())
    except ValueError:
        await message.answer("❌ Raqam kiriting!"); return
    info = db.get_user(target_id)
    if not info:
        await message.answer("❌ Bu ID da foydalanuvchi topilmadi!"); return
    await state.clear()
    bio = db.get_bio(target_id) or "Yo'q"
    emoji = db.get_profile_emoji(target_id)
    wr = round(info['games_won'] / info['games_played'] * 100) if info['games_played'] > 0 else 0
    streak = db.get_win_streak(target_id)
    await message.answer(
        f"{emoji} <b>{info['name']}</b>\n\n"
        f"📝 Bio: <i>{bio}</i>\n\n"
        f"💰 Coinlar: {info['coins']}\n"
        f"🎮 O'yinlar: {info['games_played']} | 🏆 G'alabalar: {info['games_won']}\n"
        f"📊 Win rate: {wr}%\n"
        f"⚡ Hozirgi seriya: {streak}\n"
        f"🗡️ O'ldirishlar: {info['kills']}",
        parse_mode="HTML",
        reply_markup=back_kb("menu_back")
    )


# 7. KUNLIK MASLAHAT
_DAILY_TIPS = [
    "🔴 Mafia sifatida kunduzi kamroq gapiring — shubha tortmaslik uchun.",
    "👮 Sherif sifatida avval eng faol o'yinchilarni tekshiring.",
    "💚 Shifokor sifatida o'zingizni himoya qiling, siz juda muhmsiz!",
    "👤 Fuqaro sifatida ovoz berishda mantiqqa suyaning, his-tuyg'uga emas.",
    "🕵️ Josus bo'lsangiz, to'g'ri vaqtda sherif bilan hamkorlik qiling.",
    "🎭 Mafiyachi sherif roliga o'xshab harakat qilsa, uzoqroq yashaydi.",
    "💡 Ko'p gapirgan o'yinchi mafia bo'lishi ehtimoli yuqori — kuzating!",
    "🤫 Ovoz bermay yoki oxirda ovoz berish mafiyachilarga foydali.",
    "⏱ Tun buyrug'ini tez berish siz mafiya emasligingizni ko'rsatadi.",
    "🏆 Har doim bir sabab bilan ovoz bering — bu sizni ishonchli ko'rsatadi.",
    "🔍 Kimni qutqarishni bilmasangiz, g'alaba ssenariyida eng muhim kishini!",
    "📢 Munozarada jim o'tirish shubha tug'diradi — doim fikr bildiring.",
]


@dp.callback_query(F.data == "menu_dailytip")
async def cb_daily_tip(callback: CallbackQuery):
    import hashlib
    today = datetime.now().strftime("%Y-%m-%d")
    idx = int(hashlib.md5(today.encode()).hexdigest(), 16) % len(_DAILY_TIPS)
    tip = _DAILY_TIPS[idx]
    await callback.message.edit_text(
        f"💡 <b>BUGUNGI MASLAHAT</b>\n\n{tip}\n\n"
        f"📅 Har kuni yangi maslahat!",
        parse_mode="HTML",
        reply_markup=back_kb("menu_back")
    )
    await callback.answer()


# 8. KUNLIK VAZIFALAR
@dp.callback_query(F.data == "menu_missions")
async def cb_daily_missions(callback: CallbackQuery):
    user = callback.from_user
    db.ensure_user(user.id, user.full_name)
    m = db.get_daily_missions(user.id)
    await callback.message.edit_text(
        f"📅 <b>BUGUNGI VAZIFALAR</b>\n\n"
        f"Har kuni yangilanadi! Bajarish uchun oddiy amallar:\n\n"
        f"{'✅' if m['games_done'] >= 1 else '🎯'} Vazifa 1: 1 ta o'yin o'yna → <b>+30💰</b>\n"
        f"{'✅' if m['rulet_done'] >= 2 else '🎯'} Vazifa 2: Ruletda 2 marta o'yna → <b>+20💰</b>\n"
        f"{'✅' if m['bonus_done'] >= 1 else '🎯'} Vazifa 3: Kunlik bonusni ol → <b>+10💰</b>\n\n"
        f"Bajarilgan vazifalarni quyida yig'ing:",
        parse_mode="HTML",
        reply_markup=daily_missions_kb(m['games_done'], m['rulet_done'], m['bonus_done'])
    )
    await callback.answer()


@dp.callback_query(F.data.startswith("dm_claim_"))
async def cb_dm_claim(callback: CallbackQuery):
    user = callback.from_user
    task_num = int(callback.data.split("_")[2])
    m = db.get_daily_missions(user.id)
    if task_num == 1:
        if m['games_done'] < 1:
            await callback.answer("❌ Avval 1 ta o'yin o'ynang!", show_alert=True); return
        db.add_coins(user.id, 30)
        await callback.answer("✅ +30💰 olindi!")
    elif task_num == 2:
        if m['rulet_done'] < 2:
            await callback.answer("❌ Avval 2 marta rulet o'ynang!", show_alert=True); return
        db.add_coins(user.id, 20)
        await callback.answer("✅ +20💰 olindi!")
    elif task_num == 3:
        if m['bonus_done'] < 1:
            await callback.answer("❌ Avval kunlik bonusni oling!", show_alert=True); return
        db.add_coins(user.id, 10)
        await callback.answer("✅ +10💰 olindi!")
    m2 = db.get_daily_missions(user.id)
    await callback.message.edit_reply_markup(
        reply_markup=daily_missions_kb(m2['games_done'], m2['rulet_done'], m2['bonus_done'])
    )


# 9. LOGIN SERIYASI
@dp.callback_query(F.data == "menu_loginstreak")
async def cb_login_streak(callback: CallbackQuery):
    user = callback.from_user
    db.ensure_user(user.id, user.full_name)
    streak, is_new = db.update_login_streak(user.id)
    bonus = 0
    note = ""
    if is_new:
        if streak % 7 == 0:
            bonus = 50
            db.add_coins(user.id, bonus)
            note = f"\n🎊 7 kunlik seriya! +{bonus}💰 bonus!"
        elif streak % 3 == 0:
            bonus = 20
            db.add_coins(user.id, bonus)
            note = f"\n🎉 3 kunlik seriya! +{bonus}💰 bonus!"
        else:
            note = "\n✅ Bugungi kirish qayd etildi!"
    else:
        note = "\n📍 Bugun allaqachon kirdingiz."
    milestones = "3 kun→+20💰 | 7 kun→+50💰 | 30 kun→+200💰"
    await callback.message.edit_text(
        f"🔥 <b>LOGIN SERIYASI</b>\n\n"
        f"🗓 Ketma-ket kunlar: <b>{streak}</b>\n"
        f"{note}\n\n"
        f"📊 Bonus milestones:\n{milestones}",
        parse_mode="HTML",
        reply_markup=back_kb("menu_back")
    )
    await callback.answer()


# 10. HAFTALIK BONUS
@dp.callback_query(F.data == "menu_weeklybonus")
async def cb_weekly_bonus(callback: CallbackQuery):
    user = callback.from_user
    db.ensure_user(user.id, user.full_name)
    can = db.can_claim_weekly_bonus(user.id)
    if can:
        db.claim_weekly_bonus(user.id, 75)
        await callback.message.edit_text(
            "💎 <b>HAFTALIK BONUS</b>\n\n"
            "🎉 <b>+75💰 olindi!</b>\n\n"
            "Keyingi bonus 7 kundan so'ng.",
            parse_mode="HTML", reply_markup=back_kb("menu_back")
        )
        await callback.answer("💎 +75💰!")
    else:
        await callback.message.edit_text(
            "💎 <b>HAFTALIK BONUS</b>\n\n"
            "❌ Siz allaqachon haftalik bonusni oldingiz.\n\n"
            "7 kun kutish kerak.",
            parse_mode="HTML", reply_markup=back_kb("menu_back")
        )
        await callback.answer("⏳ Keyingi hafta!", show_alert=True)


# 11. DO'STLAR
@dp.callback_query(F.data == "menu_friends")
async def cb_friends_menu(callback: CallbackQuery):
    user = callback.from_user
    db.ensure_user(user.id, user.full_name)
    friends = db.get_friends(user.id)
    count = len(friends)
    await callback.message.edit_text(
        f"🤝 <b>DO'STLAR</b>\n\n"
        f"Do'stlar soni: <b>{count}</b>\n\n"
        f"Do'st qo'shsangiz, profilda ko'rinadi!",
        parse_mode="HTML",
        reply_markup=friends_menu_kb()
    )
    await callback.answer()


@dp.callback_query(F.data == "friend_add")
async def cb_friend_add(callback: CallbackQuery, state: FSMContext):
    await state.set_state(BotStates.waiting_friend_id)
    await callback.message.edit_text(
        "🤝 Do'st qo'shish\n\nDo'stingizning Telegram <b>user ID</b> sini yuboring:\n❌ /bekor",
        parse_mode="HTML"
    )
    await callback.answer()


@dp.message(BotStates.waiting_friend_id)
async def msg_friend_add(message: Message, state: FSMContext):
    try:
        fid = int(message.text.strip())
    except ValueError:
        await message.answer("❌ Raqam kiriting!"); return
    if fid == message.from_user.id:
        await message.answer("❌ O'zingizni do'st qila olmaysiz!"); return
    target = db.get_user(fid)
    if not target:
        await message.answer("❌ Bu foydalanuvchi topilmadi!"); return
    db.add_friend(message.from_user.id, fid)
    await state.clear()
    await message.answer(
        f"✅ <b>{target['name']}</b> do'stlar ro'yxatiga qo'shildi!",
        parse_mode="HTML", reply_markup=back_kb("menu_friends")
    )


@dp.callback_query(F.data == "friend_list")
async def cb_friend_list(callback: CallbackQuery):
    user = callback.from_user
    friends = db.get_friends(user.id)
    if not friends:
        text = "👥 Do'stlar ro'yxati bo'sh.\n\n➕ Do'st qo'shing!"
    else:
        lines = [f"👤 <b>{f['name']}</b> (ID: <code>{f['user_id']}</code>)" for f in friends]
        text = "👥 <b>DO'STLARIM</b>\n\n" + "\n".join(lines)
    await callback.message.edit_text(text, parse_mode="HTML", reply_markup=back_kb("menu_friends"))
    await callback.answer()


# 12. JACKPOT
@dp.callback_query(F.data == "mini_jackpot")
async def cb_mini_jackpot(callback: CallbackQuery):
    amount = db.get_jackpot()
    await callback.message.edit_text(
        f"💰 <b>JACKPOT</b>\n\n"
        f"Umumiy fond: <b>{amount}💰</b>\n\n"
        f"Qoidalar:\n"
        f"• Har Spinning Wheel o'yinida 5% jackpotga ketadi\n"
        f"• Jackpotga ishtirok narxi: <b>50💰</b>\n"
        f"• G'olib hamma fondni oladi!\n"
        f"• Ehtimol: <b>10%</b>",
        parse_mode="HTML",
        reply_markup=jackpot_kb(amount)
    )
    await callback.answer()


@dp.callback_query(F.data == "jackpot_play")
async def cb_jackpot_play(callback: CallbackQuery):
    user = callback.from_user
    cost = 50
    info = db.get_user(user.id)
    if not info or info['coins'] < cost:
        await callback.answer("❌ 50💰 kerak!", show_alert=True); return
    db.add_coins(user.id, -cost)
    db.add_to_jackpot(cost)
    if random.random() < 0.10:
        prize = db.claim_jackpot(user.id)
        text = f"🎉🎉🎉 <b>JACKPOT YUTDINGIZ!</b> 🎉🎉🎉\n\n+<b>{prize}💰</b> hisobingizga o'tdi!"
    else:
        new_jp = db.get_jackpot()
        text = (
            f"😔 <b>Omad kulib baqmadi...</b>\n\n"
            f"Tikish: -{cost}💰\n"
            f"Jackpot hozir: {new_jp}💰\n\n"
            f"Yana urinib ko'ring!"
        )
    await callback.message.edit_text(text, parse_mode="HTML", reply_markup=jackpot_kb(db.get_jackpot()))
    await callback.answer()


# 13. SEVIMLI ROL
@dp.callback_query(F.data == "profile_favrol")
async def cb_profile_favrol(callback: CallbackQuery):
    user = callback.from_user
    current = db.get_favorite_role(user.id) or "Tanlanmagan"
    await callback.message.edit_text(
        f"🌟 <b>SEVIMLI ROL</b>\n\n"
        f"Hozir: <b>{current}</b>\n\n"
        f"Qaysi rol sizga mos keladi? (Faqat hazil 😄)\n"
        f"Bot buni yodda tutadi!",
        parse_mode="HTML",
        reply_markup=fav_role_kb()
    )
    await callback.answer()


@dp.callback_query(F.data.startswith("favrol_"))
async def cb_set_favrol(callback: CallbackQuery):
    user = callback.from_user
    role_key = callback.data.split("_")[1]
    role_names = {
        'mafia': '🔴 Mafia',
        'sheriff': '👮 Sherif',
        'doctor': '💚 Shifokor',
        'spy': '🕵️ Josus',
        'civilian': '👤 Fuqaro',
        'joker': '🃏 Jokker',
    }
    role_name = role_names.get(role_key, role_key)
    db.set_favorite_role(user.id, role_name)
    jokes = [
        "Bot bu ma'lumotni e'tiborga olmaydi lekin ko'nglingiz to'q 😄",
        "Istaklaringiz ro'yxatga olindi! (Natija kafolatsiz 🤭)",
        "Xudo xohlasa, keyingi o'yinda shunday bo'ladi... balki 🙏",
        "Statistika bu rolda win rate ni oshirishga harakat qiladi 📊",
    ]
    await callback.message.edit_text(
        f"🌟 Sevimli rol: <b>{role_name}</b>\n\n"
        f"<i>{random.choice(jokes)}</i>",
        parse_mode="HTML",
        reply_markup=back_kb("profile_favrol")
    )
    await callback.answer("✅ Saqlandi!")


# 14. ADMIN E'LON
@dp.callback_query(F.data == "admin_announce")
async def cb_admin_announce(callback: CallbackQuery, state: FSMContext):
    if not is_admin(callback.from_user.id):
        await callback.answer("❌ Ruxsat yo'q!", show_alert=True); return
    await state.set_state(BotStates.waiting_announce_text)
    await callback.message.edit_text(
        "📢 <b>ADMIN E'LON</b>\n\nE'lon matnini yuboring:\n(Guruh ID sini ham yozing, undan keyin matn)\n\nFormat:\n<code>-100123456789\nE'lon matni bu yerda</code>\n\n❌ /bekor",
        parse_mode="HTML"
    )
    await callback.answer()


@dp.message(BotStates.waiting_announce_text)
async def msg_announce_text(message: Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        await state.clear(); return
    lines = message.text.strip().split("\n", 1)
    if len(lines) < 2:
        await message.answer("❌ Format:\n<chat_id>\n<matn>"); return
    try:
        chat_id = int(lines[0].strip())
    except ValueError:
        await message.answer("❌ Birinchi qatorda guruh ID bo'lishi kerak!"); return
    text = lines[1].strip()
    await state.clear()
    try:
        await bot.send_message(chat_id, f"📢 <b>ADMIN E'LONI</b>\n\n{text}", parse_mode="HTML")
        await message.answer("✅ E'lon yuborildi!")
    except Exception as e:
        await message.answer(f"❌ Xato: {e}")


# 15. 2x COIN KUNI (ADMIN)
@dp.callback_query(F.data == "admin_double")
async def cb_admin_double(callback: CallbackQuery):
    if not is_admin(callback.from_user.id):
        await callback.answer("❌ Ruxsat yo'q!", show_alert=True); return
    chat_id = callback.message.chat.id
    if chat_id in _double_event_chats:
        _double_event_chats.discard(chat_id)
        await callback.answer("✅ 2x Coin kuni O'CHIRILDI!", show_alert=True)
    else:
        _double_event_chats.add(chat_id)
        await callback.answer("🎊 2x Coin kuni YOQILDI! O'yin comlari 2 barobarga oshdi!", show_alert=True)
    await callback.message.edit_text(
        f"🎊 <b>2x COIN KUNI</b>\n\n"
        f"Status: <b>{'✅ FAOL' if chat_id in _double_event_chats else '❌ Faol emas'}</b>\n\n"
        f"Faol bo'lsa, o'yin comlari 2 barobar beriladi!",
        parse_mode="HTML",
        reply_markup=admin_extra_kb()
    )


# 16. TEZ O'YIN REJIMI (ADMIN)
@dp.callback_query(F.data == "admin_speedmode")
async def cb_admin_speedmode(callback: CallbackQuery):
    if not is_admin(callback.from_user.id):
        await callback.answer("❌ Ruxsat yo'q!", show_alert=True); return
    chat_id = callback.message.chat.id
    if chat_id in _speed_mode_chats:
        _speed_mode_chats.discard(chat_id)
        await callback.answer("✅ Tez o'yin O'CHIRILDI!", show_alert=True)
    else:
        _speed_mode_chats.add(chat_id)
        await callback.answer("⚡ Tez o'yin YOQILDI! Vaqtlar 50% qisqaradi!", show_alert=True)
    await callback.message.edit_text(
        f"⚡ <b>TEZ O'YIN REJIMI</b>\n\n"
        f"Status: <b>{'✅ FAOL' if chat_id in _speed_mode_chats else '❌ Faol emas'}</b>\n\n"
        f"Faol bo'lsa, barcha o'yin vaqtlari 50% qisqaradi.",
        parse_mode="HTML",
        reply_markup=admin_extra_kb()
    )


# 17. GURUH STATISTIKASI
@dp.callback_query(F.data == "admin_groupstats")
async def cb_admin_groupstats(callback: CallbackQuery):
    chat_id = callback.message.chat.id
    stats = db.get_group_stats(chat_id)
    top = db.get_top(10)
    top_text = ""
    for i, u in enumerate(top[:5], 1):
        top_text += f"{i}. {u['name']} — {u['games_won']} galaba\n"
    last_game = stats['last_game_date'] or "Hali yoq"
    top_display = top_text if top_text else "Hali yoq"
    await callback.message.edit_text(
        f"📊 <b>GURUH STATISTIKASI</b>\n\n"
        f"🎮 Jami o'yinlar: <b>{stats['total_games']}</b>\n"
        f"📅 Oxirgi o'yin: {last_game}\n\n"
        f"🏆 <b>TOP 5 O'YINCHILAR:</b>\n{top_display}",
        parse_mode="HTML",
        reply_markup=back_kb("admin_extra_panel")
    )
    await callback.answer()


# 18. EMOJI RAMKA
@dp.callback_query(F.data == "profile_emoji")
async def cb_profile_emoji(callback: CallbackQuery):
    user = callback.from_user
    current = db.get_profile_emoji(user.id)
    await callback.message.edit_text(
        f"🌈 <b>PROFIL RAMKASI</b>\n\n"
        f"Hozirgi ramkangiz: <b>{current}</b>\n\n"
        f"Yangi ramka tanlang:",
        parse_mode="HTML",
        reply_markup=emoji_frame_kb()
    )
    await callback.answer()


@dp.callback_query(F.data.startswith("emoji_"))
async def cb_set_emoji(callback: CallbackQuery):
    user = callback.from_user
    emoji = callback.data[len("emoji_"):]
    if emoji not in PROFILE_EMOJIS:
        await callback.answer("❌ Noto'g'ri tanlov!", show_alert=True); return
    db.set_profile_emoji(user.id, emoji)
    await callback.message.edit_text(
        f"✅ <b>Ramka o'rnatildi: {emoji}</b>\n\nProfilingizda ko'rinadi!",
        parse_mode="HTML",
        reply_markup=back_kb("profile_emoji")
    )
    await callback.answer(f"✅ {emoji} tanlandi!")


# 19. ROL STATISTIKASI + REKORDLAR
@dp.callback_query(F.data == "profile_stats")
async def cb_profile_stats(callback: CallbackQuery):
    user = callback.from_user
    info = db.get_user(user.id)
    if not info:
        await callback.answer("Profil topilmadi!"); return
    games = info['games_played']
    won = info['games_won']
    wr = round(won / games * 100) if games > 0 else 0
    mafia_wr = round(info['mafia_games'] / max(1, games) * 100)
    sheriff_wr = round(info['sheriff_games'] / max(1, games) * 100)
    doctor_wr = round(info['doctor_games'] / max(1, games) * 100)
    bio = db.get_bio(user.id) or "—"
    emoji = db.get_profile_emoji(user.id)
    fav_role = db.get_favorite_role(user.id) or "—"
    await callback.message.edit_text(
        f"{emoji} <b>BATAFSIL STATISTIKA</b>\n\n"
        f"📝 Bio: <i>{bio}</i>\n"
        f"🌟 Sevimli rol: {fav_role}\n\n"
        f"🎮 Jami o'yinlar: {games}\n"
        f"🏆 G'alabalar: {won} ({wr}%)\n"
        f"💀 O'limlar: {info['deaths']}\n"
        f"🗡️ O'ldirishlar: {info['kills']}\n\n"
        f"<b>Rol taqsimoti:</b>\n"
        f"🔴 Mafia o'yinlari: {info['mafia_games']} ({mafia_wr}%)\n"
        f"👮 Sherif o'yinlari: {info['sheriff_games']} ({sheriff_wr}%)\n"
        f"💚 Shifokor o'yinlari: {info['doctor_games']} ({doctor_wr}%)",
        parse_mode="HTML",
        reply_markup=back_kb("menu_profile")
    )
    await callback.answer()


@dp.callback_query(F.data == "profile_records")
async def cb_profile_records(callback: CallbackQuery):
    user = callback.from_user
    info = db.get_user(user.id)
    if not info:
        await callback.answer("Profil topilmadi!"); return
    streak = db.get_win_streak(user.id)
    login_s = db.get_login_streak(user.id)
    emoji = db.get_profile_emoji(user.id)
    medals = []
    if info['kills'] >= 50:
        medals.append("🗡️ Assassin Ustasi (50+ o'ldirish)")
    if info['games_won'] >= 20:
        medals.append("🏆 Veteran (20+ g'alaba)")
    if streak >= 5:
        medals.append("🔥 Hot Streak (5+ ketma-ket)")
    if info['games_played'] >= 100:
        medals.append("🎮 100 O'yin Klubiga a'zo")
    medals_text = "\n".join(medals) if medals else "Hali yo'q"
    await callback.message.edit_text(
        f"{emoji} <b>REKORDLARIM</b>\n\n"
        f"⚡ Eng uzun win seriya: <b>{streak}</b>\n"
        f"🔥 Login seriyasi: <b>{login_s}</b> kun\n"
        f"🗡️ Jami o'ldirishlar: <b>{info['kills']}</b>\n"
        f"🎮 Jami o'yinlar: <b>{info['games_played']}</b>\n"
        f"🏆 Jami g'alabalar: <b>{info['games_won']}</b>\n\n"
        f"🏅 <b>MEDALLAR:</b>\n{medals_text}",
        parse_mode="HTML",
        reply_markup=back_kb("menu_profile")
    )
    await callback.answer()


# 20. ADMIN EXTRA PANEL + PROFIL EXTRA PANEL
@dp.callback_query(F.data == "admin_extra_panel")
async def cb_admin_extra_panel(callback: CallbackQuery):
    if not is_admin(callback.from_user.id):
        await callback.answer("❌ Ruxsat yo'q!", show_alert=True); return
    await callback.message.edit_text(
        "⚙️ <b>ADMIN KENGAYTIRILGAN PANEL</b>\n\nQo'shimcha admin amallar:",
        parse_mode="HTML",
        reply_markup=admin_extra_kb()
    )
    await callback.answer()


@dp.callback_query(F.data == "menu_extra")
async def cb_menu_extra(callback: CallbackQuery):
    user = callback.from_user
    db.ensure_user(user.id, user.full_name)
    await callback.message.edit_text(
        "⚙️ <b>QOSHIMCHA IMKONIYATLAR</b>\n\nProfilingizni sozlang va yangi funksiyalardan foydalaning:",
        parse_mode="HTML",
        reply_markup=profile_extra_kb()
    )
    await callback.answer()


# ==================== MAIN ====================

async def main():
    logger.info("🎭 Mafia Bot ishga tushmoqda...")
    await dp.start_polling(bot, skip_updates=True)


if __name__ == "__main__":
    asyncio.run(main())
