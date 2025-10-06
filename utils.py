import logging
import io
from datetime import datetime
from typing import Optional
from PIL import Image, ImageDraw, ImageFont
from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes

from config import (
    Role, GIFS, BLOCK, INITIAL_PLAYER_HP, RELIC_EFFECTS, 
    SHOP_ITEMS, BOT_OWNER_ID, CO_OWNER_ID, HELP_TEXTS, MAX_PLAYERS, MIN_PLAYERS,SHIP_UPGRADES
)
from models import CosmicVoyage, Player

logger = logging.getLogger(__name__)


def format_game_message(title, content, emoji="🌌", style="info"):
    """Create visually appealing formatted messages"""
    styles = {
        "info": {"border": "═", "color": "🔵"},
        "success": {"border": "═", "color": "🟢"},
        "warning": {"border": "═", "color": "🟡"},
        "danger": {"border": "═", "color": "🔴"},
        "special": {"border": "✦", "color": "⭐"}
    }
    
    style_data = styles.get(style, styles["info"])
    border = style_data["border"]
    color = style_data["color"]
    
    message = f"""╔{border * 40}╗
  {emoji} **{title}** {color}
╠{border * 40}╣

{content}

╚{border * 40}╝"""
    return message


def create_progress_bar(current, total, length=15, filled="█", empty="░"):
    """Create animated progress bar"""
    percentage = min(100, int((current / total) * 100)) if total > 0 else 0
    filled_length = int((current / total) * length) if total > 0 else 0
    bar = filled * filled_length + empty * (length - filled_length)
    return f"{bar} {percentage}%"


def create_countdown_display(seconds_remaining):
    """Visual countdown with emojis"""
    if seconds_remaining > 30:
        emoji = "🟢"
        status = "Plenty of time"
    elif seconds_remaining > 15:
        emoji = "🟡"
        status = "Time running out"
    elif seconds_remaining > 5:
        emoji = "🟠"
        status = "Hurry up!"
    else:
        emoji = "🔴"
        status = "LAST SECONDS!"
    return f"{emoji} **{seconds_remaining}s** - _{status}_"


def create_player_status_card(player, game):
    """Create detailed player status display"""
    alive_status = "✅ ALIVE" if player.is_alive else "💀 DECEASED"
    hp_bar = create_progress_bar(player.hp, 100, 12, "❤️", "🖤")
    
    special_status = []
    if player.has_potion:
        special_status.append("⚡ **POTION CARRIER**")
    if player.shields > 0:
        special_status.append(f"🛡️ {player.shields} Shield(s)")
    if player.collateral_damage > 0:
        days_left = 4 - (game.current_day - player.collateral_day)
        special_status.append(f"⚠️ Collateral: {player.collateral_damage} ({days_left}d)")
    if len(player.relics) > 0:
        special_status.append(f"💎 {len(player.relics)} Relic(s)")
    
    status_text = "\n".join([f"  └─ {s}" for s in special_status]) if special_status else ""
    
    card = f"""┌─────────────────────────
│ 👤 **{player.username}**
│ {alive_status}
├─────────────────────────
│ HP: {hp_bar}
│ 🪙 Coins: {player.coins}
{status_text}
└─────────────────────────"""
    return card

def get_role_description(role: Role) -> str:
    """Get description for a role"""
    descriptions = {
        Role.CAPTAIN: "🎖 **Captain:** Leads with valor, reducing ship damage by 20%. Can stabilize ship (+15 HP). Has 3 rally uses to heal entire team.",
        Role.HEALER: "🩹 **Healer/Shipwright:** Mends wounds (+20 HP) and repairs ship (+15 HP) with cosmic expertise. Can target specific players.",
        Role.ORACLE: "🔮 **Oracle/Navigator:** Foresees cosmic hazards and Monster attacks, guiding the crew safely through dangers.",
        Role.DRAGON_RIDER: "🐉 **Dragon Rider:** Commands a celestial dragon, reducing Monster damage by 50% for the entire team.",
        Role.ANGEL_GUARDIAN: "👼 **Angel Guardian:** Shields the Potion Bearer from sabotage and attacks with divine protection.",
        Role.EXPLORER: "🪐 **Explorer/Treasure Hunter:** Seeks ancient relics that provide permanent boosts and uncover cosmic secrets.",
        Role.POTION_BEARER: "⚡ **Potion Bearer:** Carries the cosmic potion, tasked with delivering it to Eldoria to achieve victory.",
        Role.BETRAYER: "🗡 **Betrayer:** A hidden traitor sabotaging the ship (Days 1-9), transforms into Epic Monster on Day 10 or when caught.and A hidden traitor sabotaging the ship. Can use Mind Games to create confusion.",
        Role.EPIC_MONSTER: "👹 **Epic Monster:** Unleashes devastating multi-attacks on ship, players, and potion after transformation. Can boost allies.",
        Role.SHADOW_SABOTEUR: "👤 **Shadow Saboteur:** Blocks one player's action per day, sowing chaos and disrupting strategies.",
        Role.DEVIL_HUNTER: "😈 **Devil Hunter:** Enhances Monster's attack once per game for massive damage boost.",
        Role.CREW_MEMBER: "👥 **Crew Member:** Basic crew member, supports the team with standard actions."
    }
    return descriptions.get(role, "Unknown role - please report this issue.")


def create_lobby_keyboard() -> InlineKeyboardMarkup:
    """Create keyboard for lobby"""
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("✅ Join Game", callback_data="join_game"),
            InlineKeyboardButton("❌ Leave Game", callback_data="leave_game")
        ],
        [InlineKeyboardButton("⏳ Extend Timer (+60s)", callback_data="extend_lobby")]
    ])


# utils.py - Better action keyboard

# utils.py - create_action_keyboard update

def create_action_keyboard(player: Player, game) -> InlineKeyboardMarkup:
    """Action keyboard with basic attack"""
    keyboard = []
    negative_roles = [Role.BETRAYER, Role.EPIC_MONSTER, Role.SHADOW_SABOTEUR, Role.DEVIL_HUNTER]
    
    # HERO ACTIONS
    if player.role not in negative_roles:
        
        # BASIC ATTACK (Daily, unlimited) - ALWAYS SHOW FIRST
        if not player.basic_attack_used_today:
            keyboard.append([
                InlineKeyboardButton("⚔️ Basic Attack (8 dmg)", callback_data="action_basic_attack")
            ])
        
        # Role-specific actions
        if player.role == Role.CAPTAIN:
            keyboard.append([
                InlineKeyboardButton("🔧 Repair Ship", callback_data="action_repair"),
                InlineKeyboardButton("🩹 Heal Self", callback_data="action_heal")
            ])
            if player.rally_uses > 0:
                keyboard.append([
                    InlineKeyboardButton(f"🎖️ Rally Team ({player.rally_uses})", callback_data="action_rally")
                ])
        
        elif player.role == Role.HEALER:
            keyboard.append([
                InlineKeyboardButton("🩹 Heal Player", callback_data="action_heal"),
                InlineKeyboardButton("🔧 Repair Ship", callback_data="action_repair")
            ])
        
        elif player.role == Role.ORACLE:
            keyboard.append([
                InlineKeyboardButton("🔮 Predict Danger", callback_data="action_predict"),
                InlineKeyboardButton("🩹 Heal Self", callback_data="action_heal")
            ])
        
        elif player.role == Role.DRAGON_RIDER:
            keyboard.append([
                InlineKeyboardButton("🐉 Protect Team", callback_data="action_protect"),
                InlineKeyboardButton("🩹 Heal Self", callback_data="action_heal")
            ])
        
        elif player.role == Role.ANGEL_GUARDIAN:
            keyboard.append([
                InlineKeyboardButton("👼 Protect Potion", callback_data="action_protect_potion"),
                InlineKeyboardButton("🩹 Heal Self", callback_data="action_heal")
            ])
        
        elif player.role == Role.EXPLORER:
            keyboard.append([
                InlineKeyboardButton("🪶 Search Relic", callback_data="action_relic"),
                InlineKeyboardButton("🩹 Heal Self", callback_data="action_heal")
            ])
        
        else:  # CREW MEMBER
            keyboard.append([
                InlineKeyboardButton("🩹 Heal Self", callback_data="action_heal"),
                InlineKeyboardButton("💨 Dodge", callback_data="action_dodge")
            ])
        
        # PREMIUM WEAPON ATTACK
        if player.weapons:
            available_weapons = [w for w, uses in player.weapons.items() if uses > 0]
            if available_weapons:
                keyboard.append([
                    InlineKeyboardButton(f"🗡️ Premium Weapon ({len(available_weapons)})", callback_data="action_premium_weapon")
                ])
        
        # POTION DELIVERY
        if player.has_potion and game.current_day >= 10:
            keyboard.insert(0, [
                InlineKeyboardButton("⚡ DELIVER POTION (WIN!) ⚡", callback_data="action_deliver")
            ])
    
    # VILLAIN ACTIONS (unchanged)
    else:
        if player.role == Role.BETRAYER and not game.monster_revealed:
            keyboard.append([
                InlineKeyboardButton("🔪 Sabotage Ship", callback_data="action_sabotage"),
                InlineKeyboardButton("🩹 Heal (Blend)", callback_data="action_heal")
            ])
            if player.frame_job_uses > 0:
                keyboard.append([InlineKeyboardButton("🎭 Frame Job", callback_data="action_frame_job")])
            if player.false_intel_uses > 0:
                keyboard.append([InlineKeyboardButton("🤫 False Intel", callback_data="action_false_intel")])
        
        elif player.role == Role.EPIC_MONSTER or (player.role == Role.BETRAYER and game.monster_revealed):
            if game.current_day >= 2:
                keyboard.append([
                    InlineKeyboardButton("👹 Attack Ship", callback_data="action_monster_attack"),
                    InlineKeyboardButton("📈 Boost Villains", callback_data="action_boost_allies")
                ])
            else:
                keyboard.append([
                    InlineKeyboardButton("🩹 Heal Self", callback_data="action_heal"),
                    InlineKeyboardButton("⏭️ Skip", callback_data="action_skip")
                ])
        
        elif player.role == Role.SHADOW_SABOTEUR:
            if game.current_day >= 2:
                keyboard.append([
                    InlineKeyboardButton("🚫 Block Player", callback_data="action_block"),
                    InlineKeyboardButton("🩹 Heal Self", callback_data="action_heal")
                ])
            else:
                keyboard.append([
                    InlineKeyboardButton("🩹 Heal Self", callback_data="action_heal"),
                    InlineKeyboardButton("⏭️ Skip", callback_data="action_skip")
                ])
        
        elif player.role == Role.DEVIL_HUNTER:
            if game.current_day >= 2:
                if not game.devil_hunter_boost_used:
                    keyboard.append([InlineKeyboardButton("😈 Boost Monster", callback_data="action_boost")])
                keyboard.append([
                    InlineKeyboardButton("🔪 Sabotage", callback_data="action_sabotage"),
                    InlineKeyboardButton("🩹 Heal", callback_data="action_heal")
                ])
            else:
                keyboard.append([
                    InlineKeyboardButton("🩹 Heal Self", callback_data="action_heal"),
                    InlineKeyboardButton("⏭️ Skip", callback_data="action_skip")
                ])
    
    # RELICS
    if player.relics:
        one_time = [r for r in player.relics if RELIC_EFFECTS.get(r, {}).get("type") == "one_time"]
        if one_time:
            keyboard.append([InlineKeyboardButton(f"💎 Use Relic ({len(one_time)})", callback_data="action_use_relic")])
    
    # SKIP
    if not any(btn.callback_data == "action_skip" for row in keyboard for btn in row):
        keyboard.append([InlineKeyboardButton("⏭️ Skip Turn", callback_data="action_skip")])
    
    return InlineKeyboardMarkup(keyboard)


def get_timer_emoji(seconds_remaining: int) -> str:
    """Get animated timer emoji"""
    if seconds_remaining > 15:
        return "🕐"
    elif seconds_remaining > 10:
        return "⏳"
    elif seconds_remaining > 5:
        return "⏰"
    else:
        return "🔥"

def generate_hp_bar(current: int, maximum: int, length: int = 20) -> str:
    """Generate visual HP bar with emojis"""
    filled = int((current / maximum) * length) if maximum > 0 else 0
    bar = "🟦" * filled + "⬜" * (length - filled)
    percentage = int((current / maximum) * 100) if maximum > 0 else 0
    return f"{bar} {percentage}%"


def create_relic_keyboard(player: Player) -> InlineKeyboardMarkup:
    """Create keyboard for relic selection"""
    relics = [relic for relic in player.relics if RELIC_EFFECTS.get(relic, {}).get("type") == "one_time"]
    keyboard = [[InlineKeyboardButton(relic, callback_data=f"use_relic_{relic}")] for relic in relics]
    return InlineKeyboardMarkup(keyboard)


def create_help_keyboard() -> InlineKeyboardMarkup:
    """Create help section keyboard"""
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("🎭 Roles", callback_data="help_roles"),
            InlineKeyboardButton("📅 Flow", callback_data="help_flow")
        ],
        [
            InlineKeyboardButton("🎯 Objective", callback_data="help_objective"),
            InlineKeyboardButton("💡 Tips", callback_data="help_tips")
        ]
    ])

def create_upgrades_keyboard(game: CosmicVoyage) -> InlineKeyboardMarkup:
    """Create keyboard for ship upgrades shop."""
    keyboard = []
    for key, upgrade in SHIP_UPGRADES.items():
        if key not in game.ship.upgrades:
            cost = upgrade['cost']
            contribution = game.upgrade_contribution.get(key, 0)
            remaining = cost - contribution
            keyboard.append([
                InlineKeyboardButton(f"{upgrade['name']} ({remaining}/{cost} coins)", callback_data=f"upgrade_{key}")
            ])
    return InlineKeyboardMarkup(keyboard)

def create_shop_keyboard() -> InlineKeyboardMarkup:
    """Create shop keyboard"""
    keyboard = []
    for key, item in SHOP_ITEMS.items():
        keyboard.append([
            InlineKeyboardButton(f"{key} - {item['cost']} coins", 
                               callback_data=f"buy_{key.replace(' ', '_')}")
        ])
    return InlineKeyboardMarkup(keyboard)


def create_vote_keyboard(game: CosmicVoyage) -> InlineKeyboardMarkup:
    """Create voting keyboard"""
    keyboard = []
    for player in game.get_living_players():
        keyboard.append([
            InlineKeyboardButton(f"{player.username} (HP: {player.hp})", 
                               callback_data=f"vote_{player.user_id}")
        ])
    return InlineKeyboardMarkup(keyboard)


def create_target_keyboard(game: CosmicVoyage, exclude_id: int) -> InlineKeyboardMarkup:
    """Create target selection keyboard"""
    keyboard = []
    for player in game.get_living_players():
        if player.user_id != exclude_id:
            keyboard.append([
                InlineKeyboardButton(player.username, callback_data=f"target_{player.user_id}")
            ])
    return InlineKeyboardMarkup(keyboard)


def get_unicode_bar(value: int, max_value: int, length: int = 10) -> str:
    """Generate a unicode bar for HP display"""
    filled = int((value / max_value) * length) if max_value > 0 else 0
    return BLOCK * filled + '─' * (length - filled)


def is_owner_or_co_owner(user_id: int) -> bool:
    """Check if user is bot owner or co-owner"""
    return user_id in [BOT_OWNER_ID, CO_OWNER_ID]


def get_day_gif(day: int) -> str:
    """Get appropriate GIF for the day"""
    return GIFS['day_gifs'][(day - 1) % len(GIFS['day_gifs'])]


def generate_status_image(game: CosmicVoyage) -> Optional[io.BytesIO]:
    """Generate status image showing game state"""
    try:
        width, height = 800, 600
        img = Image.new('RGB', (width, height), color=(10, 20, 40))
        draw = ImageDraw.Draw(img)
        
        # Try to load fonts with fallbacks
        try:
            title_font = ImageFont.truetype("DejaVuSans-Bold.ttf", 28)
            header_font = ImageFont.truetype("DejaVuSans-Bold.ttf", 22)
            normal_font = ImageFont.truetype("DejaVuSans.ttf", 18)
        except IOError:
            # Try common font paths
            font_paths = [
                "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
                "/System/Library/Fonts/Helvetica.ttc",
                "C:\\Windows\\Fonts\\arial.ttf"
            ]
            fonts_loaded = False
            for font_path in font_paths:
                try:
                    title_font = ImageFont.truetype(font_path, 28)
                    header_font = ImageFont.truetype(font_path, 22)
                    normal_font = ImageFont.truetype(font_path, 18)
                    fonts_loaded = True
                    break
                except IOError:
                    continue
            
            if not fonts_loaded:
                logger.warning("Could not load any fonts, using default")
                title_font = ImageFont.load_default()
                header_font = ImageFont.load_default()
                normal_font = ImageFont.load_default()

        # Title
        draw.text((width//2, 20), f"COSMIC VOYAGE - DAY {game.current_day}", 
                 fill=(255, 215, 0), font=title_font, anchor="mm")
        
        # Ship Status
        draw.text((20, 70), "🚢 SHIP STATUS", fill=(100, 200, 255), font=header_font)
        ship_hp_text = f"HP: {game.ship.hp}/{game.ship.max_hp}"
        draw.text((250, 70), ship_hp_text, fill=(255, 255, 255), font=normal_font)
        
        # Ship HP Bar
        bar_width = 400
        fill_width = (game.ship.hp / game.ship.max_hp) * bar_width if game.ship.max_hp > 0 else 0
        draw.rectangle([(20, 100), (20 + bar_width, 120)], outline=(70, 130, 200))
        draw.rectangle([(20, 100), (20 + fill_width, 120)], fill=(0, 200, 100))
        
        # Players Status
        y_offset = 150
        draw.text((20, y_offset), "👥 PLAYERS STATUS", fill=(100, 200, 255), font=header_font)
        y_offset += 40
        
        for player in game.players.values():
            if y_offset > height - 50:
                break
                
            status_emoji = "✅" if player.is_alive else "💀"
            username = player.username[:15] + "..." if len(player.username) > 15 else player.username
            
            draw.text((20, y_offset), f"{status_emoji} {username}", 
                     fill=(255, 255, 255) if player.is_alive else (150, 150, 150), font=normal_font)
            
            hp_text = f"HP: {player.hp}/{INITIAL_PLAYER_HP}"
            draw.text((250, y_offset), hp_text, 
                     fill=(255, 100, 100) if player.hp < 30 else (100, 255, 100), font=normal_font)
            
            # HP Bar
            hp_bar_width = 200
            hp_fill = (player.hp / INITIAL_PLAYER_HP) * hp_bar_width if INITIAL_PLAYER_HP > 0 else 0
            bar_x = 350
            
            draw.rectangle([(bar_x, y_offset + 5), (bar_x + hp_bar_width, y_offset + 20)], 
                         outline=(100, 100, 100), fill=(50, 50, 50))
            
            if player.hp > 0:
                hp_color = (255, 50, 50) if player.hp < 30 else (50, 200, 50)
                draw.rectangle([(bar_x, y_offset + 5), (bar_x + hp_fill, y_offset + 20)], fill=hp_color)
            
            y_offset += 35

        # Game Phase
        phase_text = f"Phase: {game.phase.value.upper()}"
        draw.text((20, height - 40), phase_text, fill=(200, 200, 100), font=normal_font)
        
        # Alive count
        alive_count = len(game.get_living_players())
        alive_text = f"Alive: {alive_count}/{len(game.players)}"
        draw.text((width - 150, height - 40), alive_text, fill=(200, 200, 100), font=normal_font)
        
        buf = io.BytesIO()
        img.save(buf, format='PNG', quality=95)
        buf.seek(0)
        return buf
        
    except Exception as e:
        logger.error(f"Error generating status image: {e}")
        return None


async def send_message_wrapper(context: ContextTypes.DEFAULT_TYPE, chat_id: int, 
                               text: str, is_major: bool = False, **kwargs):
    """Wrapper for sending messages with game tracking"""
    from context import game_manager
    game = game_manager.get_game(chat_id)
    
    try:
        # Remove is_major from kwargs before sending
        kwargs.pop('is_major', None)
        msg = await context.bot.send_message(chat_id, text, **kwargs)
        if game:
            game.add_message(msg.message_id)
            if is_major:
                for spec in list(game.spectators):
                    try:
                        await context.bot.send_message(spec, text)
                    except Exception:
                        game.spectators.remove(spec)
        return msg
    except Exception as e:
        logger.error(f"Error sending message to {chat_id}: {e}")
        return None



async def send_animation_wrapper(context: ContextTypes.DEFAULT_TYPE, chat_id: int, 
                                 animation: str, caption: str = "", is_major: bool = False, **kwargs):
    """Wrapper for sending animations with fallback"""
    from context import game_manager
    game = game_manager.get_game(chat_id)
    
    try:
        # Remove is_major from kwargs before sending
        kwargs.pop('is_major', None)
        msg = await context.bot.send_animation(chat_id, animation, caption=caption, **kwargs)
        if game:
            game.add_message(msg.message_id)
            if is_major:
                for spec in list(game.spectators):
                    try:
                        await context.bot.send_message(spec, caption)
                    except Exception:
                        game.spectators.remove(spec)
        return msg
    except Exception as e:
        logger.warning(f"Could not send GIF to {chat_id}. Error: {e}")
        # Fallback to text message
        return await send_message_wrapper(context, chat_id, caption, is_major=is_major, **kwargs)



async def check_cooldown(context: ContextTypes.DEFAULT_TYPE, user_id: int) -> bool:
    """Check if user is on cooldown for commands"""
    from config import COMMAND_COOLDOWN
    now = datetime.now().timestamp()
    last_cmd = context.user_data.get('last_cmd', 0)
    if now - last_cmd < COMMAND_COOLDOWN:
        return False
    context.user_data['last_cmd'] = now
    return True