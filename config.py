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
ACTION_TIMER = 45
TOTAL_DAYS = 13
POTION_DAY = 7
COMMAND_COOLDOWN = 3
DIVINE_INTERVENTION_PROB = 0.5
RANDOM_EVENT_CHANCE = 0.25 

# HP Values
INITIAL_SHIP_HP = 100
INITIAL_PLAYER_HP = 100
HEAL_SELF_AMOUNT = 15
REPAIR_SHIP_AMOUNT = 11
DIVINE_HEAL_AMOUNT = 15

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
    "roles": "🎭 **ROLES GUIDE** 🎭\n\n"
            "✨ **HEROES** ✨\n"
            "• 🎖 **Captain:** Leads team, reduces ship damage by 20%, can repair ship\n"
            "• 🩹 **Healer:** Heals players (+20 HP) and repairs ship (+15 HP)\n"
            "• 🔮 **Oracle:** Detects hazards and monster attacks\n"
            "• 🐉 **Dragon Rider:** Reduces monster damage by 50%\n"
            "• 👼 **Angel Guardian:** Protects Potion Bearer from attacks\n"
            "• 🪐 **Explorer:** Finds relics to boost abilities\n"
            "• ⚡ **Potion Bearer:** Carries and delivers the cosmic potion\n\n"
            "👹 **VILLAINS** 👹\n"
            "• 🗡 **Betrayer:** Sabotages ship, transforms into Epic Monster\n"
            "• 👹 **Epic Monster:** Attacks ship, players, and potion\n"
            "• 👤 **Shadow Saboteur:** Blocks one player's action daily\n"
            "• 😈 **Devil Hunter:** Boosts monster's attack once per game",
    
    "flow": "📅 **GAME FLOW** 📅\n\n"
           "🌅 **Days 1-3: Healing Phase**\n"
           "• Calm journey, prepare for challenges\n"
           "• Focus on healing and gathering resources\n\n"
           "🚢 **Days 4-9: Cosmic Voyage**\n"
           "• Hazards and adventures\n"
           "• Monster may sabotage secretly\n\n"
           "⚡ **Day 10: Potion Quest**\n"
           "• Cosmic Potion appears\n"
           "• Betrayer transforms into Epic Monster\n\n"
           "⚔️ **Days 11-12: Monster Showdown**\n"
           "• Epic Monster reveals itself\n"
           "• Intense battles and strategies\n\n"
           "🏆 **Day 13: Final Delivery**\n"
           "• Last chance to deliver potion\n"
           "• Victory or defeat decided!",
    
    "objective": "🎯 **OBJECTIVES** 🎯\n\n"
                "⭐ **TEAM GOAL:**\n"
                "Deliver the Cosmic Potion by Day 13\n"
                "• Protect the Potion Bearer\n"
                "• Keep ship HP above 0\n"
                "• Survive monster attacks\n\n"
                "👹 **MONSTER GOAL:**\n"
                "Destroy the ship or eliminate all heroes\n"
                "• Sabotage the ship\n"
                "• Attack players\n"
                "• Prevent potion delivery\n\n"
                "⚡ **Daily Actions:**\n"
                "Each day you choose actions via DM\n"
                "20 seconds to decide!",
    
    "tips": "💡 **PRO TIPS** 💡\n\n"
           "🎮 **For New Players:**\n"
           "• Keep your role secret from others\n"
           "• Vote wisely during elimination\n"
           "• Use resources strategically\n"
           "• Coordinate with your team\n\n"
           "⚡ **Advanced Strategies:**\n"
           "• Heal collateral damage within 4 days\n"
           "• Use relics and shop items wisely\n"
           "• Protect the Potion Bearer at all costs\n"
           "• Monitor ship HP carefully\n\n"
           "🏆 **Win Probability:**\n"
           "Team: ~45% | Monster: ~55%\n\n"
           "Good luck, space voyager! 🌟"
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