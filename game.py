import random
from enum import Enum


class Role(Enum):
    MAFIA = "Mafia"
    DONN = "Donn"
    SHERIFF = "Sherif"
    DOCTOR = "Doktor"
    SPY = "Ayg'oqchi"
    CIVILIAN = "Fuqaro"


class GameState(Enum):
    WAITING = "waiting"
    NIGHT = "night"
    DAY = "day"
    VOTING = "voting"
    ENDED = "ended"


ROLE_EMOJI = {
    Role.MAFIA: "🔫",
    Role.DONN: "👑",
    Role.SHERIFF: "🔍",
    Role.DOCTOR: "💉",
    Role.SPY: "💋",
    Role.CIVILIAN: "👥",
}

MAFIA_ROLES = {Role.MAFIA, Role.DONN}
CIVILIAN_ROLES = {Role.SHERIFF, Role.DOCTOR, Role.SPY, Role.CIVILIAN}


class MafiaGame:
    def __init__(self, chat_id: int):
        self.chat_id = chat_id
        self.players: list[dict] = []
        self.state = GameState.WAITING
        self.round = 1

        self.night_actions: dict = {}
        self.votes: dict = {}

        self.doctor_self_heal_used = False
        self.spy_self_block_used = False
        self.donn_reveal_used = False

        self.spy_blocked_id: int | None = None

        self.shield_users: set = set()
        self.lucky_users: set = set()
        self.extra_vote_users: set = set()
        self.alarm_users: set = set()
        self.poison_targets: dict = {}
        self.precise_users: set = set()
        self.spy_kit_users: set = set()
        self.anon_msg_pending: dict = {}

    def add_player(self, user_id: int, name: str, username: str = None):
        self.players.append({
            'id': user_id,
            'name': name,
            'username': username,
            'role': None,
            'alive': True,
            'kills': 0,
        })

    def remove_player(self, user_id: int):
        self.players = [p for p in self.players if p['id'] != user_id]

    def is_player(self, user_id: int) -> bool:
        return any(p['id'] == user_id for p in self.players)

    def get_player(self, user_id: int) -> dict | None:
        return next((p for p in self.players if p['id'] == user_id), None)

    def get_alive_players(self) -> list[dict]:
        return [p for p in self.players if p['alive']]

    def get_alive_mafia(self) -> list[dict]:
        return [p for p in self.players if p['alive'] and p['role'] in MAFIA_ROLES]

    def get_alive_civilians(self) -> list[dict]:
        return [p for p in self.players if p['alive'] and p['role'] in CIVILIAN_ROLES]

    def assign_roles(self):
        count = len(self.players)
        roles = []

        roles.append(Role.DONN)

        if count >= 8:
            roles.extend([Role.MAFIA, Role.MAFIA])
        else:
            roles.append(Role.MAFIA)

        roles.append(Role.SHERIFF)

        if count >= 6:
            roles.append(Role.DOCTOR)

        if count >= 7:
            roles.append(Role.SPY)

        remaining = count - len(roles)
        roles.extend([Role.CIVILIAN] * max(0, remaining))

        random.shuffle(roles)
        for i, player in enumerate(self.players):
            player['role'] = roles[i]

    def check_winner(self) -> str | None:
        alive = self.get_alive_players()
        mafia = [p for p in alive if p['role'] in MAFIA_ROLES]
        civilians = [p for p in alive if p['role'] in CIVILIAN_ROLES]

        if not mafia:
            return "civilian"
        if len(mafia) >= len(civilians):
            return "mafia"
        return None

    def get_role_group(self, role: Role) -> str:
        if role in MAFIA_ROLES:
            return "mafia"
        return "civilian"

    def get_mafia_mates_text(self) -> str:
        mates = [p['name'] for p in self.players if p['role'] in MAFIA_ROLES]
        return ", ".join(mates)
