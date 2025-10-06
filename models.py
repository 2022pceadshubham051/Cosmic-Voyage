from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Set, Tuple
import random

from config import (
    Role, GamePhase, INITIAL_PLAYER_HP, INITIAL_SHIP_HP,
    RELIC_EFFECTS, MIN_PLAYERS, MAX_PLAYERS, TOTAL_DAYS, SECRET_OBJECTIVES,
    SHIP_UPGRADES
)

# models.py - Player class

@dataclass
class Player:
    user_id: int
    username: str
    role: Optional[Role] = None
    hp: int = INITIAL_PLAYER_HP
    collateral_damage: int = 0
    collateral_day: int = 0
    has_dodge: bool = False
    relics: List[str] = field(default_factory=list)
    is_alive: bool = True
    has_potion: bool = False
    action_blocked: bool = False
    coins: int = 0
    shields: int = 0
    rally_uses: int = 0
    pending_target: Optional[int] = None
    is_first_time: bool = True
    secret_objective: Optional[Dict] = None
    objective_progress: int = 0
    objective_completed: bool = False
    frame_job_uses: int = 1
    false_intel_uses: int = 1
    healed_targets: Set[int] = field(default_factory=set)
    weapons: Dict[str, int] = field(default_factory=dict)
    basic_attack_used_today: bool = False  # NEW: Track daily basic attack

    def take_damage(self, amount: int, is_collateral: bool = False, current_day: int = 0):
        """Apply damage to player with reductions and dodge chances"""
        reduction = 0
        dodge_chance = 0.5 if self.has_dodge else 0
        
        # Apply relic effects
        for relic in self.relics:
            if relic in RELIC_EFFECTS and RELIC_EFFECTS[relic]["type"] == "passive":
                if RELIC_EFFECTS[relic]["effect"] == "damage_reduction":
                    reduction += RELIC_EFFECTS[relic]["value"]
                elif RELIC_EFFECTS[relic]["effect"] == "dodge_bonus":
                    dodge_chance += RELIC_EFFECTS[relic]["value"]
        
        # Apply shield
        if self.shields > 0:
            amount = int(amount * 0.6)
            self.shields -= 1
        
        # Apply damage reduction
        amount -= reduction
        
        # Apply dodge chance
        if random.random() < dodge_chance:
            amount = amount // 2  # FIXED: Added the divisor
        
        self.hp -= max(0, amount)
        
        if is_collateral:
            self.collateral_damage += amount
            self.collateral_day = current_day
        
        if self.hp <= 0:
            self.is_alive = False

    def heal(self, amount: int):
        """Heal player and reduce collateral damage"""
        self.hp = min(INITIAL_PLAYER_HP, self.hp + amount)
        if self.collateral_damage > 0:
            heal_collateral = min(amount, self.collateral_damage)
            self.collateral_damage -= heal_collateral


@dataclass
class Ship:
    hp: int = INITIAL_SHIP_HP
    max_hp: int = INITIAL_SHIP_HP
    upgrades: Set[str] = field(default_factory=set)
    damage_reduction: float = 0.0

    def take_damage(self, amount: int):
        """Apply damage to ship, considering upgrades"""
        final_amount = int(amount * (1 - self.damage_reduction))
        self.hp -= final_amount
        if self.hp < 0:
            self.hp = 0

    def repair(self, amount: int):
        """Repair ship up to max HP"""
        self.hp = min(self.max_hp, self.hp + amount)

    def add_upgrade(self, upgrade_key: str):
        """Add a purchased upgrade and apply its effect."""
        self.upgrades.add(upgrade_key)
        if upgrade_key == "reinforced_hull":
            self.damage_reduction = 0.05  # FIXED: Changed from 0.5 to 0.05

class CosmicVoyage:
    """Main game state class"""
    
    def __init__(self, chat_id: int):
        self.chat_id = chat_id
        self.players: Dict[int, Player] = {}
        self.ship = Ship()
        self.phase = GamePhase.LOBBY
        self.current_day = 0
        self.lobby_message_id: Optional[int] = None
        self.lobby_extensions = 0
        self.monster_revealed = False
        self.betrayer_caught = False
        self.potion_delivered = False
        self.betrayer_id: Optional[int] = None
        self.monster_id: Optional[int] = None
        self.pending_actions: Dict[int, str] = {}
        self.game_start_time: Optional[datetime] = None
        self.recent_messages: List[Tuple[datetime, int]] = []
        self.spectators: Set[int] = set()
        self.votes: Dict[int, int] = {}
        self.voted: Set[int] = set()
        self.captain_id: Optional[int] = None
        self.lobby_reminder_sent = False
        self.devil_hunter_boost_used = False
        self.villain_boost_active = False
        self.shadow_saboteur_uses = 0
        self.active_random_event: Optional[Dict] = None
        self.upgrade_contribution: Dict[str, int] = {key: 0 for key in SHIP_UPGRADES}

    def add_player(self, user_id: int, username: str) -> bool:
        """Add a player to the game"""
        if len(self.players) >= MAX_PLAYERS:
            return False
        if user_id not in self.players:
            self.players[user_id] = Player(user_id, username)
            return True
        return False

    def remove_player(self, user_id: int) -> bool:
        """Remove a player from the game"""
        if user_id in self.players:
            del self.players[user_id]
            return True
        return False
    
    def assign_secret_objectives(self):
        """Assign a secret objective to each player."""
        for player in self.players.values():
            if player.role in SECRET_OBJECTIVES:
                player.secret_objective = SECRET_OBJECTIVES[player.role]
            else:
                player.secret_objective = SECRET_OBJECTIVES["default"]

    def assign_roles(self):
        """Assign roles with better balance"""
        player_count = len(self.players)
        if player_count < MIN_PLAYERS:
            return

        player_list = list(self.players.values())
        random.shuffle(player_list)
    
        # Better role distribution
        if player_count == 4:
            roles_to_assign = [
                Role.CAPTAIN, 
                Role.HEALER, 
                Role.BETRAYER,
                Role.CREW_MEMBER
            ]
        elif player_count == 5:
            roles_to_assign = [
                Role.CAPTAIN, 
                Role.HEALER,
                Role.BETRAYER,
                Role.SHADOW_SABOTEUR,
                Role.CREW_MEMBER
            ]
        elif player_count == 6:
            roles_to_assign = [
                Role.CAPTAIN, 
                Role.HEALER,
                Role.EXPLORER,
                Role.BETRAYER,
                Role.SHADOW_SABOTEUR,
                Role.CREW_MEMBER
            ]
        elif player_count == 7:
            roles_to_assign = [
                Role.CAPTAIN, 
                Role.HEALER,
                Role.EXPLORER,
                Role.DRAGON_RIDER,
                Role.BETRAYER,
                Role.SHADOW_SABOTEUR,
                Role.CREW_MEMBER
            ]
        elif player_count == 8:
            roles_to_assign = [
                Role.CAPTAIN, 
                Role.HEALER,
                Role.ORACLE,
                Role.EXPLORER,
                Role.DRAGON_RIDER,
                Role.BETRAYER,
                Role.SHADOW_SABOTEUR,
                Role.CREW_MEMBER
            ]
        elif player_count <= 10:
            roles_to_assign = [
                Role.CAPTAIN, 
                Role.HEALER,
                Role.ORACLE,
                Role.EXPLORER,
                Role.DRAGON_RIDER,
                Role.ANGEL_GUARDIAN,
                Role.BETRAYER,
                Role.SHADOW_SABOTEUR,
                Role.DEVIL_HUNTER,
                Role.CREW_MEMBER
            ]
        else:  # 11+ players
            roles_to_assign = [
                Role.CAPTAIN, 
                Role.HEALER,
                Role.ORACLE,
                Role.EXPLORER,
                Role.DRAGON_RIDER,
                Role.ANGEL_GUARDIAN,
                Role.BETRAYER,
                Role.BETRAYER,  # 2nd betrayer for big games
                Role.SHADOW_SABOTEUR,
                Role.DEVIL_HUNTER,
                Role.CREW_MEMBER
            ]
        
            # Add more crew members for remaining slots
            while len(roles_to_assign) < player_count:
                roles_to_assign.append(Role.CREW_MEMBER)

        random.shuffle(roles_to_assign)
    
        # Track betrayers
        betrayer_count = 0

        # Assign to players
        for i, player in enumerate(player_list):
            player.role = roles_to_assign[i]
            if player.role == Role.BETRAYER:
                if betrayer_count == 0:
                    self.betrayer_id = player.user_id
                    self.monster_id = player.user_id
                betrayer_count += 1
            if player.role == Role.CAPTAIN:
                player.rally_uses = 1
                self.captain_id = player.user_id

    def get_living_players(self) -> List[Player]:
        """Get all living players"""
        return [p for p in self.players.values() if p.is_alive]

    def check_win_condition(self) -> Optional[str]:
        """Check win conditions"""
        living = self.get_living_players()
        
        negative_roles = [Role.BETRAYER, Role.EPIC_MONSTER, Role.SHADOW_SABOTEUR, Role.DEVIL_HUNTER]
        
        angels_alive = [p for p in living if p.role not in negative_roles]
        demons_alive = [p for p in living if p.role in negative_roles]
        
        # Don't check win conditions before game starts
        if self.current_day < 1:
            return None
        
        # Ship destroyed or all angels dead -> Demons win
        if self.ship.hp <= 0 or not angels_alive:
            return 'monster'
        
        # All demons dead -> Angels win (only after Day 5)
        if not demons_alive and self.current_day >= 5:
            return 'team'
        
        # Potion delivered -> Angels win
        if self.potion_delivered:
            return 'team'
        
        # Time expired without delivery -> Demons win
        if self.current_day > TOTAL_DAYS and not self.potion_delivered:
            return 'monster'
        
        return None

    def add_message(self, message_id: int):
        """Track recent messages for cleanup"""
        now = datetime.now()
        self.recent_messages.append((now, message_id))
        self.recent_messages = [(ts, mid) for ts, mid in self.recent_messages 
                                if now - ts < timedelta(minutes=15)]

    def apply_captain_damage_reduction(self, amount: int) -> int:
        """Apply captain's 10% damage reduction if alive"""
        captain = next((p for p in self.players.values() 
                        if p.role == Role.CAPTAIN and p.is_alive), None)
        return int(amount * 0.9) if captain else amount  # FIXED: Changed from 0.8

    def earn_coins(self):
        """Give coins to all living players"""
        for player in self.get_living_players():
            player.coins += 10

    def start_voting(self):
        """Initialize voting phase"""
        self.phase = GamePhase.VOTING
        self.votes = {uid: 0 for uid in self.players if self.players[uid].is_alive}
        self.voted = set()

    def process_vote(self, voter_id: int, target_id: int) -> bool:
        """Process a vote from a player"""
        if (voter_id in self.voted or 
            not self.players.get(voter_id) or 
            not self.players[voter_id].is_alive):
            return False
        self.votes[target_id] = self.votes.get(target_id, 0) + 1
        self.voted.add(voter_id)
        return True

    def end_voting(self) -> Optional[int]:
        """End voting and return eliminated player ID"""
        if not self.votes:
            return None
        
        max_votes = max(self.votes.values()) if self.votes else 0
        if max_votes == 0:
            return None
        
        eliminated = [uid for uid, count in self.votes.items() if count == max_votes]
        if eliminated:
            target_id = random.choice(eliminated)
            if target_id in self.players:
                target = self.players[target_id]
                if target_id == self.betrayer_id and not self.monster_revealed:
                    target.role = Role.EPIC_MONSTER
                    self.monster_revealed = True
                    self.betrayer_caught = True
                    return target_id
                else:
                    target.is_alive = False
                    return target_id
        return None


class GameManager:
    """Manages multiple game instances"""
    
    def __init__(self):
        self.games: Dict[int, CosmicVoyage] = {}

    def create_game(self, chat_id: int) -> Optional[CosmicVoyage]:
        """Create a new game for a chat"""
        if chat_id in self.games and self.games[chat_id].phase != GamePhase.ENDED:
            return None
        game = CosmicVoyage(chat_id)
        self.games[chat_id] = game
        return game

    def get_game(self, chat_id: int) -> Optional[CosmicVoyage]:
        """Get game for a chat"""
        return self.games.get(chat_id)

    def end_game(self, chat_id: int):
        """End and remove a game"""
        if chat_id in self.games:
            del self.games[chat_id]