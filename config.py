import os
from enum import Enum

# Bot Configuration - USE ENVIRONMENT VARIABLES IN PRODUCTION
BOT_TOKEN = os.getenv("BOT_TOKEN", "7470395975:AAHRocEJXwTwzkREunhOj1hYeh1QGixwLQk")
BOT_OWNER_ID = int(os.getenv("BOT_OWNER_ID", "7460266461"))
CO_OWNER_ID = int(os.getenv("CO_OWNER_ID", "7379484662"))
SUPPORT_GROUP_ID = int(os.getenv("SUPPORT_GROUP_ID", "-1002707382739"))

# Game Constants
MIN_PLAYERS = 4
MAX_PLAYERS = 21
BASE_LOBBY_TIMER = 120
ACTION_TIMER = 90 
TOTAL_DAYS = 13
POTION_DAY = 9
COMMAND_COOLDOWN = 2
DIVINE_INTERVENTION_PROB = 0.5
RANDOM_EVENT_CHANCE = 0.25 
VOTING_START_DAY = 2
VOTING_TIMER = 45

# HP Values
INITIAL_SHIP_HP = 100
INITIAL_PLAYER_HP = 100
HEAL_SELF_AMOUNT = 15
REPAIR_SHIP_AMOUNT = 11
DIVINE_HEAL_AMOUNT = 15

ACHIEVEMENTS = {
    'master_healer': {'desc': 'Heal 500 HP across all games', 'threshold': 500, 'stat': 'total_heals'},
    'betrayer_king': {'desc': 'Win 3 games as Betrayer or Epic Monster', 'threshold': 3, 'condition': lambda player, stats: player.role in [Role.BETRAYER, Role.EPIC_MONSTER] and stats['wins'] >= 3},
    'survivor': {'desc': 'Survive to the end in 10 games', 'threshold': 10, 'stat': 'games_survived'},
    'coin_hoarder': {'desc': 'Earn 1000 coins lifetime', 'threshold': 1000, 'stat': 'total_coins'},
    'ship_savior': {'desc': 'Repair 300 ship HP across all games', 'threshold': 300, 'stat': 'total_heals'},  # Assuming ship repairs count as heals
    'monster_slayer': {'desc': 'Eliminate the Epic Monster 3 times', 'threshold': 3, 'condition': lambda player, stats: stats['total_kills'] >= 3 and any(p.role == Role.EPIC_MONSTER for p in game.players.values() if p.hp <= 0)},
    'potion_protector': {'desc': 'Deliver the potion as Potion Bearer 2 times', 'threshold': 2, 'stat': 'potions_delivered'},
    'shadow_master': {'desc': 'Perform 50 sabotages', 'threshold': 50, 'stat': 'sabotages_performed'},
    'relic_hunter': {'desc': 'Find 10 relics as Explorer', 'threshold': 10, 'stat': 'relics_found'},
    'captains_glory': {'desc': 'Use rally 10 times as Captain', 'threshold': 10, 'stat': 'rallies_used'},
    'oracles_vision': {'desc': 'Reveal the Betrayer/Epic Monster 5 times', 'threshold': 5, 'stat': 'monsters_revealed'},
    'dragon_tamer': {'desc': 'Protect allies with Dragon Rider 10 times', 'threshold': 10, 'condition': lambda player, stats: player.role == Role.DRAGON_RIDER and stats['games_played'] >= 10},  # Track via actions
    'guardian_angel': {'desc': 'Protect Potion Bearer from 5 attacks', 'threshold': 5, 'condition': lambda player, stats: player.role == Role.ANGEL_GUARDIAN and stats['games_played'] >= 5},  # Track via protect actions
    'cosmic_veteran': {'desc': 'Play 50 games', 'threshold': 50, 'stat': 'games_played'},
    'chaos_bringer': {'desc': 'Deal 1000 damage as a Shadow role', 'threshold': 1000, 'stat': 'total_damage', 'condition': lambda player, stats: player.role in [Role.BETRAYER, Role.EPIC_MONSTER, Role.SHADOW_SABOTEUR, Role.DEVIL_HUNTER]},
    'vote_master': {'desc': 'Cast 100 votes', 'threshold': 100, 'stat': 'votes_cast'},
    'divine_interventionist': {'desc': 'Trigger divine intervention 5 times while alive', 'threshold': 5, 'condition': lambda player, stats: player.is_alive and random.random() < DIVINE_INTERVENTION_PROB},
    'black_market_mogul': {'desc': 'Purchase 10 Black Market items', 'threshold': 10, 'condition': lambda player, stats: sum(1 for item in SHOP_ITEMS.values() if item.get('market', False))},
    'ship_upgrader': {'desc': 'Contribute to 5 ship upgrades', 'threshold': 5, 'condition': lambda player, stats: sum(game.upgrade_contribution.values()) >= 5},
    'team_player': {'desc': 'Win 10 games as a Light-side role', 'threshold': 10, 'condition': lambda player, stats: player.role not in [Role.BETRAYER, Role.EPIC_MONSTER, Role.SHADOW_SABOTEUR, Role.DEVIL_HUNTER] and stats['wins'] >= 10},
    'lone_wolf': {'desc': 'Survive as the last player 3 times', 'threshold': 3, 'condition': lambda player, stats: player.is_alive and len([p for p in game.players.values() if p.is_alive]) == 1},
    'quick_thinker': {'desc': 'Complete actions in 10s in 20 phases', 'threshold': 20, 'stat': 'game_action_time'},
    'underdog': {'desc': 'Win with fewer than 3 team members left', 'threshold': 1, 'condition': lambda player, stats: player.game_underdog_win},
    'flawless_victory': {'desc': 'Win without taking damage', 'threshold': 1, 'condition': lambda player, stats: player.game_flawless and stats['wins'] > 0},
    'cosmic_legend': {'desc': 'Achieve 15 different achievements', 'threshold': 15, 'condition': lambda player, stats: len(get_achievements(player.user_id)) >= 15}
}

# GIF URLs
GIFS = {
    'lobby': 'https://media3.giphy.com/media/v1.Y2lkPTZjMDliOTUyaG5wN3FpYW55d2FjOHUycWlkMzI0NWRudHJ5MmI4azVjaGtxMDVpZiZlcD12MV9pbnRlcm5hbF9naWZfYnlfaWQmY3Q9Zw/skl7A8hBxLt6AB2mcA/giphy.gif',
    'celestial_gates': 'https://media3.giphy.com/media/v1.Y2lkPTZjMDliOTUyaG5wN3FpYW55d2FjOHUycWlkMzI0NWRudHJ5MmI4azVjaGtxMDVpZiZlcD12MV9pbnRlcm5hbF9naWZfYnlfaWQmY3Q9Zw/skl7A8hBxLt6AB2mcA/giphy.gif',
    'voyage_start': 'https://media2.giphy.com/media/v1.Y2lkPTZjMDliOTUydHNmem5qZm1uaXhrN3ptN3lpOGZjaXh2dzlyNXZ3ZWxqYmd5Z3BzeSZlcD12MV9pbnRlcm5hbF9naWZfYnlfaWQmY3Q9Zw/fbweTsoLncIri6UZQ7/giphy.gif',
    'monster_attack': 'https://media4.giphy.com/media/v1.Y2lkPTZjMDliOTUyemlqYjB0bjRzaWx5amtqeGM4c3p5anV5a2doeTVhNDN6cWw1YnI1eiZlcD12MV9pbnRlcm5hbF9naWZfYnlfaWQmY3Q9Zw/BpRhdSuQeeYXMviWie/giphy.gif',
    'potion_found': 'https://media1.giphy.com/media/v1.Y2lkPTZjMDliOTUyZWNjanlqYjR3bnFyMjc5bzJ6cms5NDFtaDl1b2dsYXdvMGc2Znl6aiZlcD12MV9pbnRlcm5hbF9naWZfYnlfaWQmY3Q9Zw/26his0JJrH1eyF9Ju/giphy.gif',
    'victory': 'https://media0.giphy.com/media/v1.Y2lkPTZjMDliOTUyOXM4cWF2Z2ZsZTd4Y3JpdGZlZHRtcTVhM2I1a2R0cXo0Z3dyZWF4dSZlcD12MV9pbnRlcm5hbF9naWZfYnlfaWQmY3Q9Zw/V6qtMo0Ra64RO7qwGi/giphy.gif',
    'defeat': 'https://media.giphy.com/media/d2lcHJTG5Tscg/giphy.gif',
    'relic': 'https://media.giphy.com/media/l0HlMPcbD4jdARjRC/giphy.gif',
    'day_gifs': [
        'https://media3.giphy.com/media/v1.Y2lkPTZjMDliOTUyeG93MmZjc3EycDh1eWZ3aHJwcGVuZnJwYmJ3ZHoxYW4zcHAzZWZtYyZlcD12MV9pbnRlcm5hbF9naWZfYnlfaWQmY3Q9Zw/39qAdVJ4QCgvXwwCgC/giphy.gif',
        'https://media4.giphy.com/media/v1.Y2lkPTZjMDliOTUyZXJ6b3h0Y2xpbmxycWFodjB2eGN1cHk1ODRpZDJqdXFwc3RpZDdsayZlcD12MV9pbnRlcm5hbF9naWZfYnlfaWQmY3Q9Zw/LR6oIqNZyWsnsJFHs0/giphy.gif',
        'https://media3.giphy.com/media/v1.Y2lkPTZjMDliOTUya2xxNzlpb3VnMDdiNmI4MnJuYWg0bnp0cHY0MTgzMGxmbngzeHpwZSZlcD12MV9pbnRlcm5hbF9naWZfYnlfaWQmY3Q9Zw/26gs9KRJC8sRUzAM8/giphy.gif',
        'https://media0.giphy.com/media/v1.Y2lkPTZjMDliOTUyd3U4OGVicnV2anp1c2Q0YTJiNHBxOWhqNWpvdmNmcGloZGJkZ2M3MSZlcD12MV9pbnRlcm5hbF9naWZfYnlfaWQmY3Q9Zw/l0ExkIaOPEOBOB9Be/giphy.gif',
        'https://media3.giphy.com/media/v1.Y2lkPTZjMDliOTUyYmFheml2ZXk0dWVpY2xybmY4Mmlyd21uYXJqdHhza2pxc29sODducSZlcD12MV9pbnRlcm5hbF9naWZfYnlfaWQmY3Q9Zw/cAmiLut5okad35wc8d/giphy.gif',
        'https://media1.giphy.com/media/v1.Y2lkPTZjMDliOTUyeWFkdGRhdzdiNTl6dm1wbGs2NDU0azNzaHNnMXpub2xrM2hkemVlcyZlcD12MV9pbnRlcm5hbF9naWZfYnlfaWQmY3Q9Zw/j0qYU35hA5t9vfhckv/giphy.gif',
    ]
}
HELP_PHOTO = 'https://t.me/ttwusvsjssnsbsjsnsbsns/1487'

# Unicode characters
BLOCK = chr(9608)

# Default weapon for all positive roles (unlimited daily use)
DEFAULT_WEAPON = {
    "name": "Basic Strike",
    "damage": 8,
    "desc": "Basic attack available daily (unlimited uses per day)"
}

# Premium weapons (limited total uses)
PREMIUM_WEAPONS = {
    "Holy Sword": {"cost": 35, "damage": 30, "uses": 2, "desc": "Powerful holy blade (2 total uses)"},
    "Light Spear": {"cost": 28, "damage": 22, "uses": 3, "desc": "Divine spear (3 total uses)"},
    "Divine Bow": {"cost": 20, "damage": 18, "uses": 4, "desc": "Blessed bow (4 total uses)"},
    "Blessed Dagger": {"cost": 15, "damage": 12, "uses": 5, "desc": "Quick dagger (5 total uses)"}
}

# Update SHOP_ITEMS
SHOP_ITEMS = {
    "Healing Potion": {"cost": 15, "effect": "heal", "value": 30},
    "Shield": {"cost": 20, "effect": "shield"},
    "Vision Crystal": {"cost": 25, "effect": "reveal"},
    # Premium Weapons
    "Holy Sword": {"cost": 35, "effect": "weapon", "weapon_data": PREMIUM_WEAPONS["Holy Sword"]},
    "Light Spear": {"cost": 28, "effect": "weapon", "weapon_data": PREMIUM_WEAPONS["Light Spear"]},
    "Divine Bow": {"cost": 20, "effect": "weapon", "weapon_data": PREMIUM_WEAPONS["Divine Bow"]},
    "Blessed Dagger": {"cost": 15, "effect": "weapon", "weapon_data": PREMIUM_WEAPONS["Blessed Dagger"]},
    # Black Market Items
    "Sabotage Kit": {"cost": 40, "effect": "sabotage", "value": 20, "market": True},
    "Emergency Shield": {"cost": 50, "effect": "ship_shield", "value": 50, "market": True},
}

# Relic effects
RELIC_EFFECTS = {
    "Crystal of Clarity": {"type": "passive", "effect": "reveal", "desc": "Reveals random info each day"},
    "Shield of Stars": {"type": "passive", "effect": "damage_reduction", "value": 10, "desc": "-10 damage reduction"},
    "Amulet of Protection": {"type": "passive", "effect": "dodge_bonus", "value": 0.25, "desc": "+25% dodge chance"},
    "Sword of Light": {"type": "passive", "effect": "damage_bonus", "value": 15, "desc": "+15 damage bonus"},
    "Healing Herb": {"type": "one_time", "effect": "heal", "value": 15, "desc": "+15 HP when used"},
    "Ancient Scroll": {"type": "one_time", "effect": "coins", "value": 20, "desc": "+20 coins when used"}
}

# Shop items
SHOP_ITEMS = {
    "Healing Potion": {"cost": 15, "effect": "heal", "value": 30},
    "Shield": {"cost": 20, "effect": "shield"},
    "Vision Crystal": {"cost": 25, "effect": "reveal"}
}

# Help texts
HELP_TEXTS = {
    "roles": "🎭 **Role Overview** 🎭\n\n"
            "✨ **Heroes of Light** ✨\n"
            "• 🎖️ **Captain:** Guides crew, cuts ship damage 20%, repairs hull.\n"
            "• 🩹 **Healer:** Mends allies (+20 HP), fixes ship (+15 HP).\n"
            "• 🔮 **Oracle:** Foresees dangers and foe strikes.\n"
            "• 🐉 **Dragon Rider:** Halves monster assaults.\n"
            "• 👼 **Angel Guardian:** Shields potion carrier.\n"
            "• 🪐 **Explorer:** Uncovers relics for boosts.\n"
            "• ⚡ **Potion Bearer:** Holds and delivers the key artifact.\n\n"
            "👹 **Shadows of Chaos** 👹\n"
            "• 🗡️ **Betrayer:** Undermines ship, evolves into Epic Monster.\n"
            "• 👹 **Epic Monster:** Ravages ship and crew.\n"
            "• 👤 **Shadow Saboteur:** Thwarts one action daily.\n"
            "• 😈 **Devil Hunter:** Amplifies monster power once.",
    
    "flow": "📅 **Journey Phases** 📅\n\n"
           "🌅 **Days 1-3: Recovery** \n"
           "Calm start – heal wounds, stock up.\n\n"
           "🚢 **Days 4-9: Deep Space** \n"
           "Face hazards; shadows lurk.\n\n"
           "⚡ **Day 10: Artifact Awakens** \n"
           "Potion emerges; betrayer transforms.\n\n"
           "⚔️ **Days 11-12: Clash Peak** \n"
           "Monster unleashes; strategize fiercely.\n\n"
           "🏆 **Day 13: Destiny** \n"
           "Final push – deliver or doom!",
    
    "objective": "🎯 **Core Missions** 🎯\n\n"
                "⭐ **Light's Quest:** \n"
                "Secure potion delivery by Day 13.\n"
                "- Guard the bearer\n"
                "- Maintain ship integrity\n"
                "- Endure assaults\n\n"
                "👹 **Shadow's Scheme:** \n"
                "Ruin ship or vanquish heroes.\n"
                "- Weaken hull\n"
                "- Strike foes\n"
                "- Block delivery\n\n"
                "⚡ **Daily Moves:** \n"
                "Select via DM – 20s to act wisely!",
    
    "tips": "💡 **Strategic Insights** 💡\n\n"
           "🎮 **New Voyagers:** \n"
           "- Guard your role\n"
           "- Vote thoughtfully\n"
           "- Manage resources\n"
           "- Ally wisely\n\n"
           "⚡ **Veteran Tactics:** \n"
           "- Cure damage in 4 days\n"
           "- Leverage relics/items\n"
           "- Shield the bearer\n"
           "- Track ship health\n\n"
           "🏆 **Odds:** \n"
           "Light: ~45% | Shadow: ~55%\n\n"
           "Forge ahead, voyager! 🌟"
}

class Role(Enum):
    # Angel Roles
    CAPTAIN = "Captain"
    HEALER = "Healer/Shipwright"
    ORACLE = "Oracle/Navigator"
    DRAGON_RIDER = "Dragon Rider"
    ANGEL_GUARDIAN = "Angel Guardian"
    EXPLORER = "Explorer/Treasure Hunter"
    POTION_BEARER = "Potion Bearer"
    CREW_MEMBER = "Crew Member"

    # Demon Roles
    BETRAYER = "Betrayer"
    EPIC_MONSTER = "Epic Monster"
    SHADOW_SABOTEUR = "Shadow Saboteur"
    DEVIL_HUNTER = "Devil Hunter"


class GamePhase(Enum):
    LOBBY = "lobby"
    HEALING = "healing"
    VOYAGE = "voyage"
    POTION_QUEST = "potion_quest"
    SHOWDOWN = "showdown"
    DELIVERY = "delivery"
    VOTING = "voting"
    ENDED = "ended"

# --- NEW FEATURES ---

# 1. SECRET OBJECTIVES
SECRET_OBJECTIVES = {
    Role.HEALER: {"desc": "Heal 3 different players.", "reward_type": "heal_boost", "value": 1.5, "target_count": 3},
    Role.EXPLORER: {"desc": "Find 2 relics.", "reward_type": "item", "value": "Shield", "target_count": 2},
    Role.CAPTAIN: {"desc": "Successfully use Rally Team twice.", "reward_type": "coins", "value": 50, "target_count": 2},
    Role.BETRAYER: {"desc": "Successfully sabotage the ship for a total of 50 damage.", "reward_type": "hp_boost", "value": 20, "target_count": 50},
    "default": {"desc": "Survive until Day 8.", "reward_type": "coins", "value": 30, "target_count": 8}
}

# 2. SHIP UPGRADES
SHIP_UPGRADES = {
    "reinforced_hull": {"name": "Reinforced Hull", "cost": 100, "desc": "Reduces all ship damage by 10% permanently."},
    "advanced_scanners": {"name": "Advanced Scanners", "cost": 80, "desc": "Gives the Oracle clearer information."},
    "auto_repair_system": {"name": "Auto-Repair System", "cost": 120, "desc": "Automatically repairs 5 ship HP each day."}
}

# 3. RANDOM EVENTS
RANDOM_EVENTS = {
    "cosmic_flare": {
        "name": "Cosmic Flare",
        "desc": "A solar flare jams all communications! All actions today will be anonymous."
    },
    "black_market": {
        "name": "Black Market",
        "desc": "A smuggler is nearby! Special powerful items are available in the shop for one day only."
    },
    "traitors_moon": {
        "name": "Traitor's Moon",
        "desc": "A dark moon empowers evil! All sabotage and Monster attacks are twice as powerful today."
    }
}

# Shop items (including Black Market)
SHOP_ITEMS = {
    "Healing Potion": {"cost": 15, "effect": "heal", "value": 30},
    "Shield": {"cost": 20, "effect": "shield"},
    "Vision Crystal": {"cost": 25, "effect": "reveal"},
    # Black Market Items
    "Sabotage Kit": {"cost": 40, "effect": "sabotage", "value": 20, "market": True},
    "Emergency Shield": {"cost": 50, "effect": "ship_shield", "value": 50, "market": True},
}
