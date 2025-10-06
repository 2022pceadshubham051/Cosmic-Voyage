import asyncio
import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from utils import format_game_message, create_progress_bar, create_player_status_card
from telegram.ext import ContextTypes

from config import (
    BOT_OWNER_ID, CO_OWNER_ID, SUPPORT_GROUP_ID, MIN_PLAYERS, MAX_PLAYERS,
    BASE_LOBBY_TIMER, HELP_PHOTO, HELP_TEXTS, SHOP_ITEMS, RELIC_EFFECTS,
    Role,SHIP_UPGRADES   # ADD THIS LINE
)
from models import GameManager, GamePhase
from utils import (
    check_cooldown, create_lobby_keyboard, send_message_wrapper, 
    send_animation_wrapper, create_help_keyboard, create_shop_keyboard,
    get_role_description, generate_status_image, create_target_keyboard,
    create_relic_keyboard, is_owner_or_co_owner
)
from game_logic import start_game
from config import GIFS
import random

logger = logging.getLogger(__name__)
from context import game_manager


# ============================================================================
# COMMAND HANDLERS
# ============================================================================

async def added_to_group(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle bot being added to a group"""
    try:
        if update.message and update.message.new_chat_members:
            for member in update.message.new_chat_members:
                if member.id == context.bot.id:
                    adder = update.message.from_user
                    chat = update.message.chat
                    group_link = f"t.me/{chat.username}" if chat.username else "Private group"
                    await context.bot.send_message(
                        SUPPORT_GROUP_ID,
                        f"🤖 Bot added to group\n"
                        f"By: @{adder.username} (ID: {adder.id})\n"
                        f"Group: {chat.title} (ID: {chat.id})\n"
                        f"Group Link: {group_link}"
                    )
    except Exception as e:
        logger.error(f"Error in added_to_group: {e}")


async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /start command"""
    if not await check_cooldown(context, update.effective_user.id):
        return
    
    welcome_text = (
        "🚀 **COSMIC VOYAGE** 🚀\n\n"
        "*Embark on an epic space adventure!*\n\n"
        "🌌 **About the Game:**\n"
        "A thrilling multiplayer space adventure where heroes and monsters battle across the cosmos!\n\n"
        "🎮 **Quick Commands:**\n"
        "`/newgame` - Start a new game (groups only)\n"
        "`/commands` - See all available commands\n" 
        "`/join` - Join the current game\n"
        "`/help` - Learn how to play\n"
        "`/status` - Check game status\n"
        "`/tutorial` - Interactive tutorial\n\n"
        "⚡ **Game Features:**\n"
        "• 11 Unique Roles\n"
        "• Daily Actions & Voting\n"
        "• Cosmic Hazards & Relics\n"
        "• Strategic Teamplay\n"
        "• Epic Monster Battles\n\n"
        "Gather 3-15 space voyagers and begin your cosmic journey!"
    )
    
    await update.message.reply_text(welcome_text, parse_mode='Markdown')


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /help command"""
    if not await check_cooldown(context, update.effective_user.id):
        return
    
    help_text = (
        "📚 **COSMIC VOYAGE - COMPLETE GUIDE** 📚\n\n"
        "🎯 **OBJECTIVES:**\n"
        "⭐ **TEAM:** Deliver Cosmic Potion by Day 13\n"
        "👹 **MONSTER:** Destroy ship or eliminate all heroes\n\n"
        "📅 **GAME FLOW:**\n"
        "🌅 Days 1-3: Healing Phase\n"
        "🚢 Days 4-9: Cosmic Voyage\n"
        "⚡ Day 10: Potion Appears, Monster Reveals\n"
        "⚔️ Days 11-12: Monster Showdown\n"
        "🏆 Day 13: Final Delivery\n\n"
        "Use the buttons below to learn more!"
    )
    
    try:
        await update.message.reply_photo(
            photo=HELP_PHOTO,
            caption=help_text,
            parse_mode='Markdown',
            reply_markup=create_help_keyboard()
        )
    except Exception:
        await update.message.reply_text(help_text, parse_mode='Markdown', reply_markup=create_help_keyboard())


async def newgame_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /newgame command"""
    if not await check_cooldown(context, update.effective_user.id):
        return
        
    if update.effective_chat.type == 'private':
        await update.message.reply_text("❌ This command works only in groups!")
        return
        
    chat_id = update.effective_chat.id
    
    existing_game = game_manager.get_game(chat_id)
    if existing_game and existing_game.phase != GamePhase.ENDED:
        await update.message.reply_text(
            "🚫 Game already in progress!\n"
            "Use `/status` to check progress or `/endgame` to stop it.",
            parse_mode='Markdown'
        )
        return
    
    game = game_manager.create_game(chat_id)
    if not game:
        await update.message.reply_text("❌ Failed to create game. Please try again.")
        return
    
    lobby_msg = await send_animation_wrapper(
        context, chat_id, GIFS['celestial_gates'],
        caption=(
            "⚔️ **ANGELS VS DEMONS** ⚔️\n"
            "╔═══════════════════════╗\n\n"
            "🏰 **THE CELESTIAL FORTRESS**\n"
            "*A 13-day battle between Light and Darkness*\n\n"
            f"👥 **Warriors:** 0/{MAX_PLAYERS}\n"
            f"⏰ **Gates Close In:** {BASE_LOBBY_TIMER}s\n"
            f"⚔️ **Battle Begins At:** {MIN_PLAYERS} warriors\n\n"
            "🛳 **Join the fight for your side!**\n"
            "📜 **Learn the rules before joining!**"
        ),
        reply_markup=InlineKeyboardMarkup([
            [
                InlineKeyboardButton("🛳 Join Battle", callback_data="join_game"),
                InlineKeyboardButton("🚪 Leave Lobby", callback_data="leave_game")
            ],
            [
                InlineKeyboardButton("⏳ Extend Time (+30s)", callback_data="extend_lobby"),
                InlineKeyboardButton("📜 Rules & Roles", callback_data="show_rules")
            ]
        ]),
        parse_mode='Markdown'
    )
    
    if lobby_msg:
        game.lobby_message_id = lobby_msg.message_id
    
    # Start lobby timer
    context.job_queue.run_once(
        lobby_timer_callback, 
        BASE_LOBBY_TIMER,
        data={'chat_id': chat_id}, 
        name=f'lobby_{chat_id}'
    )
    
    # Schedule reminder at 30 seconds before end
    reminder_time = max(BASE_LOBBY_TIMER - 30, 10)
    context.job_queue.run_once(
        lobby_reminder_callback,
        reminder_time,
        data={'chat_id': chat_id},
        name=f'reminder_{chat_id}'
    )
    
    logger.info(f"Lobby timer started: {BASE_LOBBY_TIMER}s for chat {chat_id}")

async def lobby_reminder_callback(context: ContextTypes.DEFAULT_TYPE):
    """Remind players about lobby ending soon"""
    job = context.job
    chat_id = job.data['chat_id']
    game = game_manager.get_game(chat_id)
    
    if not game or game.phase != GamePhase.LOBBY or game.lobby_reminder_sent:
        return
        
    game.lobby_reminder_sent = True
    current_players = len(game.players)
    
    reminder_text = (
        "⏰ **LOBBY REMINDER** ⏰\n\n"
        f"Only **30 seconds** left to join!\n"
        f"👥 Current players: **{current_players}/{MAX_PLAYERS}**\n\n"
    )
    
    if current_players < MIN_PLAYERS:
        reminder_text += f"❌ Need **{MIN_PLAYERS - current_players}** more players to start!\n"
    else:
        reminder_text += "✅ Ready to start! Join now!\n"
    
    await send_message_wrapper(context, chat_id, reminder_text, 
                             reply_markup=create_lobby_keyboard(), parse_mode='Markdown')


async def lobby_timer_callback(context: ContextTypes.DEFAULT_TYPE):
    """Handle lobby timer expiration"""
    job = context.job
    chat_id = job.data['chat_id']
    game = game_manager.get_game(chat_id)
    
    if not game or game.phase != GamePhase.LOBBY:
        return
    
    if len(game.players) < MIN_PLAYERS:
        await send_message_wrapper(
            context, chat_id,
            f"❌ **Lobby closed!**\n\n"
            f"Not enough players joined.\n"
            f"Required: {MIN_PLAYERS} | Joined: {len(game.players)}\n\n"
            "Use `/newgame` to try again!",
            parse_mode='Markdown'
        )
        game_manager.end_game(chat_id)
        return
    
    await send_message_wrapper(context, chat_id, "🚀 **Lobby timer ended! Starting game...**")
    await start_game(context, chat_id)


async def join_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /join command"""
    if not await check_cooldown(context, update.effective_user.id):
        return
        
    if update.effective_chat.type == 'private':
        await update.message.reply_text("❌ Please join through the group where the game is hosted!")
        return
        
    chat_id = update.effective_chat.id
    game = game_manager.get_game(chat_id)
    
    if not game or game.phase != GamePhase.LOBBY:
        await update.message.reply_text(
            "❌ No active lobby found!\nUse `/newgame` to start a game first.",
            parse_mode='Markdown'
        )
        return
    
    user = update.effective_user
    if game.add_player(user.id, user.username or user.first_name):
        await update.message.reply_text(f"✅ **{user.first_name}** joined the cosmic voyage!")
        await update_lobby_message(context, game)
    else:
        await update.message.reply_text("❌ Lobby is full or you've already joined!")


# handlers.py - FIND AND REPLACE update_lobby_message

async def update_lobby_message(context: ContextTypes.DEFAULT_TYPE, game):
    """Enhanced lobby display"""
    try:
        player_count = len(game.players)
        progress = create_progress_bar(player_count, MAX_PLAYERS, 20, "👥", "⬜")
        
        player_grid = []
        for i, player in enumerate(game.players.values(), 1):
            player_grid.append(f"{i}. 🎮 {player.username}")
        
        player_display = "\n".join(player_grid) if player_grid else "⏳ _Waiting for players..._"
        
        if player_count < MIN_PLAYERS:
            status_emoji = "🔴"
            status_text = f"Need {MIN_PLAYERS - player_count} more"
            can_start = "❌ Cannot start yet"
        else:
            status_emoji = "🟢"
            status_text = "Ready to launch!"
            can_start = "✅ Can start anytime"
        
        caption = format_game_message(
            "COSMIC VOYAGE LOBBY",
            f"""{status_emoji} **Status:** {status_text}
{can_start}

**Player Count**
{progress}
{player_count}/{MAX_PLAYERS} Warriors

**Current Crew:**
{player_display}

🕐 Extensions: {game.lobby_extensions}/2
⚔️ Required: {MIN_PLAYERS} players""",
            emoji="🎮",
            style="info"
        )
        
        await context.bot.edit_message_caption(
            chat_id=game.chat_id,
            message_id=game.lobby_message_id,
            caption=caption,
            reply_markup=create_lobby_keyboard(),
            parse_mode='Markdown'
        )
    except Exception as e:
        logger.warning(f"Could not update lobby: {e}")


async def leave_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /leave command"""
    chat_id = update.effective_chat.id
    game = game_manager.get_game(chat_id)
    
    if not game or game.phase != GamePhase.LOBBY:
        await update.message.reply_text("❌ No active lobby to leave!")
        return
    
    user = update.effective_user
    if game.remove_player(user.id):
        await update.message.reply_text(f"👋 **{user.first_name}** left the lobby.")
        await update_lobby_message(context, game)
    else:
        await update.message.reply_text("❌ You're not in the lobby!")


async def status_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /status command"""
    if not await check_cooldown(context, update.effective_user.id):
        return
        
    chat_id = update.effective_chat.id
    game = game_manager.get_game(chat_id)
    
    if not game:
        await update.message.reply_text("❌ No active game found!")
        return
    
    if game.phase == GamePhase.LOBBY:
        status_text = (
            "🎮 **LOBBY STATUS** 🎮\n\n"
            f"👥 **Players:** {len(game.players)}/{MAX_PLAYERS}\n"
            f"🎯 **Required:** {MIN_PLAYERS} players\n"
            f"🕒 **Phase:** Waiting in Lobby\n\n"
        )
        
        if game.players:
            player_list = "\n".join([f"• {p.username}" for p in game.players.values()])
            status_text += f"**Current Players:**\n{player_list}"
        
        await update.message.reply_text(status_text, parse_mode='Markdown')
    else:
        buf = generate_status_image(game)
        if buf:
            caption = (
                f"📊 **DAY {game.current_day} STATUS** 📊\n\n"
                f"🚢 **Ship HP:** {game.ship.hp}/{game.ship.max_hp}\n"
                f"👥 **Alive:** {len(game.get_living_players())}/{len(game.players)}\n"
                f"🌌 **Phase:** {game.phase.value.title()}"
            )
            await update.message.reply_photo(photo=buf, caption=caption, parse_mode='Markdown')
        else:
            await update.message.reply_text("❌ Could not generate status image.")


async def players_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /players command"""
    if not await check_cooldown(context, update.effective_user.id):
        return
        
    chat_id = update.effective_chat.id
    game = game_manager.get_game(chat_id)
    
    if not game:
        await update.message.reply_text("❌ No active game found!")
        return
    
    if not game.players:
        await update.message.reply_text("👥 No players have joined yet!")
        return
    
    player_list = "👥 **GAME PLAYERS** 👥\n\n"
    for player in game.players.values():
        status = "✅ ALIVE" if player.is_alive else "💀 DECEASED"
        player_list += f"• {player.username} - {status}\n"
    
    await update.message.reply_text(player_list, parse_mode='Markdown')


async def startvoyage_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /startvoyage command (admin only)"""
    chat_id = update.effective_chat.id
    game = game_manager.get_game(chat_id)
    
    if not game or game.phase != GamePhase.LOBBY:
        await update.message.reply_text("❌ No active lobby to start!")
        return
    
    try:
        member = await context.bot.get_chat_member(chat_id, update.effective_user.id)
        if member.status not in ['creator', 'administrator']:
            await update.message.reply_text("❌ Only admins can force start the game!")
            return
    except Exception as e:
        logger.error(f"Error checking admin status: {e}")
        await update.message.reply_text("❌ Could not verify admin privileges!")
        return
    
    if len(game.players) < MIN_PLAYERS:
        await update.message.reply_text(
            f"❌ Need at least {MIN_PLAYERS} players to start!\n"
            f"Current: {len(game.players)}/{MIN_PLAYERS}"
        )
        return
    
    # Cancel timers
    for job in context.job_queue.get_jobs_by_name(f'lobby_{chat_id}'):
        job.schedule_removal()
    for job in context.job_queue.get_jobs_by_name(f'reminder_{chat_id}'):
        job.schedule_removal()
    
    await update.message.reply_text("🚀 **Game starting now!** Admin has forced start.")
    await start_game(context, chat_id)


async def endgame_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /endgame command (admin only)"""
    chat_id = update.effective_chat.id
    game = game_manager.get_game(chat_id)
    
    if not game:
        await update.message.reply_text("❌ No active game to end!")
        return
    
    try:
        member = await context.bot.get_chat_member(chat_id, update.effective_user.id)
        is_admin = member.status in ['creator', 'administrator']
        is_owner = is_owner_or_co_owner(update.effective_user.id)
        
        if not (is_admin or is_owner):
            await update.message.reply_text("❌ Only admins or bot owners can end the game!")
            return
    except Exception:
        await update.message.reply_text("❌ Could not verify permissions!")
        return
    
    game_manager.end_game(chat_id)
    await update.message.reply_text("🛑 **Game ended** by admin. Thanks for playing!")


async def myrole_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /myrole command"""
    if update.effective_chat.type != 'private':
        await update.message.reply_text("❌ This command works only in private messages!")
        return
        
    user_id = update.effective_user.id
    
    user_game = None
    for game in game_manager.games.values():
        if user_id in game.players:
            user_game = game
            break
    
    if not user_game or not user_game.players[user_id].role:
        await update.message.reply_text("❌ You're not in any active game or roles haven't been assigned yet!")
        return
    
    player = user_game.players[user_id]
    
    role_info = (
        f"🎭 **YOUR SECRET ROLE** 🎭\n\n"
        f"**{player.role.value}**\n\n"
        f"{get_role_description(player.role)}\n\n"
        f"📊 **YOUR STATUS:**\n"
        f"❤️ HP: {player.hp}/100\n"
        f"🪙 Coins: {player.coins}\n"
        f"🛡 Shields: {player.shields}\n"
        f"💎 Relics: {len(player.relics)}\n"
    )
    
    if player.secret_objective and not player.objective_completed:
        role_info += f"\n🎯 **Secret Mission:** {player.secret_objective['desc']}\n"

    if player.collateral_damage > 0:
        days_left = 6 - (user_game.current_day - player.collateral_day)
        role_info += f"\n⚠️ **Collateral Damage:** {player.collateral_damage}\n"
        role_info += f"⏰ Heal within **{days_left}** days or perish!\n"
    
    if player.has_potion:
        role_info += f"\n⚡ **YOU HAVE THE COSMIC POTION!**\nDeliver it to win the game!\n"
    
    negative_roles = [Role.BETRAYER, Role.EPIC_MONSTER, Role.SHADOW_SABOTEUR, Role.DEVIL_HUNTER]
    if player.role in negative_roles:
        role_info += f"\n🔴 **ALIGNMENT: DARK SIDE**\n"
    else:
        role_info += f"\n🔵 **ALIGNMENT: LIGHT SIDE**\n"
    
    await update.message.reply_text(role_info, parse_mode='Markdown')


async def inventory_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /inventory command"""
    if not await check_cooldown(context, update.effective_user.id):
        return
        
    if update.effective_chat.type != 'private':
        await update.message.reply_text("❌ This command works only in private messages!")
        return
        
    user_id = update.effective_user.id
    
    user_game = None
    for game in game_manager.games.values():
        if user_id in game.players:
            user_game = game
            break
    
    if not user_game:
        await update.message.reply_text("❌ You're not in any active game!")
        return
    
    player = user_game.players[user_id]
    
    inventory_text = "🎒 **YOUR INVENTORY** 🎒\n\n"
    
    if player.has_potion:
        inventory_text += "⚡ **Cosmic Potion** - Deliver to achieve victory!\n\n"
    
    inventory_text += (
        f"💰 **Resources:**\n"
        f"🪙 Coins: {player.coins}\n"
        f"🛡 Shields: {player.shields}\n\n"
    )
    
    if player.relics:
        inventory_text += "💎 **Relics:**\n"
        for relic in player.relics:
            desc = RELIC_EFFECTS.get(relic, {}).get("desc", "Mysterious artifact")
            relic_type = RELIC_EFFECTS.get(relic, {}).get("type", "unknown")
            type_marker = "🔄" if relic_type == "passive" else "💫"
            inventory_text += f"• {relic} {type_marker}\n  └─ {desc}\n"
    else:
        inventory_text += "💎 No relics collected yet.\n"
    
    inventory_text += f"\n❤️ Current HP: {player.hp}/100"
    
    await update.message.reply_text(inventory_text, parse_mode='Markdown')


async def tutorial_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /tutorial command"""
    if not await check_cooldown(context, update.effective_user.id):
        return
        
    tutorial_text = (
        "📖 **INTERACTIVE TUTORIAL** 📖\n\n"
        "Learn everything about Cosmic Voyage!\n\n"
        "Choose a topic below to get started:"
    )
    
    await update.message.reply_text(tutorial_text, reply_markup=create_help_keyboard())


async def shop_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /shop command"""
    if not await check_cooldown(context, update.effective_user.id):
        return
        
    user_id = update.effective_user.id
    
    user_game = None
    for game in game_manager.games.values():
        if user_id in game.players:
            user_game = game
            break
    
    if not user_game or user_game.phase == GamePhase.LOBBY:
        await update.message.reply_text("❌ Game hasn't started yet!")
        return
    
    shop_text = (
        "🛒 **COSMIC SHOP** 🛒\n\n"
        "Spend your hard-earned coins on useful items!\n\n"
        "**Available Items:**\n"
    )
    
    for item_name, item_data in SHOP_ITEMS.items():
        effect_desc = ""
        if item_data["effect"] == "heal":
            effect_desc = f"Restores {item_data['value']} HP"
        elif item_data["effect"] == "shield":
            effect_desc = "50% damage reduction for 1 attack"
        elif item_data["effect"] == "reveal":
            effect_desc = "Reveals a random player's role"
        
        shop_text += f"• **{item_name}** - {item_data['cost']} coins\n  └─ {effect_desc}\n"
    
    shop_text += f"\n💰 Your coins: {user_game.players[user_id].coins}"
    
    await update.message.reply_text(shop_text, parse_mode='Markdown', reply_markup=create_shop_keyboard())


async def spectate_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /spectate command"""
    if not await check_cooldown(context, update.effective_user.id):
        return
        
    chat_id = update.effective_chat.id
    game = game_manager.get_game(chat_id)
    
    if not game:
        await update.message.reply_text("❌ No active game to spectate!")
        return
    
    user_id = update.effective_user.id
    if user_id not in game.players and user_id not in game.spectators:
        game.spectators.add(user_id)
        await update.message.reply_text("👀 You are now spectating the game! You'll receive major updates.")
    else:
        await update.message.reply_text("❌ You're already in the game or spectating!")

async def commands_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /commands - Show all available commands"""
    if not await check_cooldown(context, update.effective_user.id):
        return
    
    commands_text = (
        "🎮 **COSMIC VOYAGE - ALL COMMANDS** 🎮\n\n"
        
        "📋 **BASIC COMMANDS:**\n"
        "/start - Start the bot and see welcome message\n"
        "/help - Complete game guide with roles and mechanics\n"
        "/commands - Show this commands list\n\n"
        
        "🎯 **GAME MANAGEMENT:**\n"
        "/newgame - Create new game lobby (groups only)\n"
        "/join - Join the current lobby\n"
        "/leave - Leave the lobby before game starts\n"
        "/startvoyage - Force start game (admins only)\n"
        "/endgame - End current game (admins/owners only)\n\n"
        
        "📊 **GAME INFO:**\n"
        "/status - View current game status with HP bars\n"
        "/players - See all players and their status\n"
        "/myrole - Check your secret role (DM only)\n"
        "/inventory - View your items and relics (DM only)\n\n"
        
        "🛒 **IN-GAME ACTIONS:**\n"
        "/shop - Browse and buy items with coins\n"
        "/upgrades - Contribute to ship upgrades\n"
        "/spectate - Watch the game as spectator\n\n"
        
        "📖 **LEARNING:**\n"
        "/tutorial - Interactive tutorial for new players\n\n"
    )
    
    await update.message.reply_text(commands_text, parse_mode='Markdown')

async def handle_upgrade_contribution(update: Update, context: ContextTypes.DEFAULT_TYPE, data: str):
    """Handle a player contributing to a ship upgrade."""
    query = update.callback_query
    upgrade_key = data.replace("upgrade_", "")
    user_id = query.from_user.id

    # Logic to find the user's game
    user_game = None
    for game in game_manager.games.values():
        if user_id in game.players:
            user_game = game
            break
            
    if not user_game:
        await query.answer("You are not in an active game!", show_alert=True)
        return

    player = user_game.players[user_id]
    upgrade = SHIP_UPGRADES[upgrade_key]
    
    if player.coins > 0:
        contribution = player.coins
        user_game.upgrade_contribution[upgrade_key] += contribution
        player.coins = 0
        
        await query.answer(f"You contributed {contribution} coins to {upgrade['name']}!", show_alert=True)

        total_contribution = user_game.upgrade_contribution[upgrade_key]
        if total_contribution >= upgrade['cost']:
            user_game.ship.add_upgrade(upgrade_key)
            await send_message_wrapper(
                context, user_game.chat_id, 
                f"✅ **UPGRADE INSTALLED:** {upgrade['name']}!",
                is_major=True, parse_mode='Markdown'
            )
        
        # Update the original upgrade message to reflect the new contribution status
        try:
            new_keyboard = create_upgrades_keyboard(user_game)
            upgrade_text = "🛠️ **SHIP UPGRADES** 🛠️\n\nContribute to purchase permanent upgrades.\n\n"
            for key, upg in SHIP_UPGRADES.items():
                status = "✅ INSTALLED" if key in user_game.ship.upgrades else "AVAILABLE"
                upgrade_text += f"• **{upg['name']}** - {status}\n  └─ {upg['desc']}\n"
                
            await query.edit_message_text(
                upgrade_text, 
                reply_markup=new_keyboard,
                parse_mode='Markdown'
            )
        except Exception as e:
            logger.error(f"Error while updating upgrade message: {e}")
            
    else:
        await query.answer("You have no coins to contribute!", show_alert=True)

async def handle_basic_attack_target(update: Update, context: ContextTypes.DEFAULT_TYPE, data: str):
    """Handle basic attack target"""
    query = update.callback_query
    target_id = int(data.replace("basic_attack_", ""))
    user_id = query.from_user.id
    
    user_game = None
    for game in game_manager.games.values():
        if user_id in game.players:
            user_game = game
            break
    
    if not user_game:
        await query.answer("Game not found!", show_alert=True)
        return
    
    player = user_game.players[user_id]
    target = user_game.players[target_id]
    
    player.pending_target = target_id
    user_game.pending_actions[user_id] = "basic_attack"
    player.basic_attack_used_today = True
    
    formatted = format_game_message(
        "Attack Queued",
        f"Target: {target.username}\nDamage: 8\n\n_Attack will execute at end of day_",
        "⚔️",
        "warning"
    )
    await query.edit_message_text(formatted, parse_mode='Markdown')


# ============================================================================
# CALLBACK HANDLERS
# ============================================================================

async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle all button callbacks"""
    query = update.callback_query
    await query.answer()
    data = query.data

    try:
        if data == "join_game":
            await handle_join_game(update, context)
        elif data.startswith("basic_attack_"):  # NEW
            await handle_basic_attack_target(update, context, data)
        elif data.startswith("upgrade_"):
            await handle_upgrade_contribution(update, context, data)
        elif data == "leave_game":
            await handle_leave_game(update, context)
        elif data == "extend_lobby":
            await handle_extend_lobby(update, context)
        elif data == "show_rules":
            await query.edit_message_text(
                HELP_TEXTS["roles"] + "\n\n" + HELP_TEXTS["flow"],
                parse_mode='Markdown',
                reply_markup=create_help_keyboard()
            )
        elif data.startswith("action_"):
            await handle_player_action(update, context, data)
        elif data.startswith("help_"):
            await handle_help_section(update, context, data)
        elif data.startswith("buy_"):
            await handle_shop_purchase(update, context, data)
        elif data.startswith("vote_"):
            await handle_voting(update, context, data)
        elif data.startswith("target_"):
            await handle_target_selection(update, context, data)
        elif data.startswith("use_relic_"):
            await handle_relic_usage(update, context, data)
    except Exception as e:
        logger.error(f"Error in button callback: {e}")
        await query.answer("An error occurred.", show_alert=True)
 


async def handle_join_game(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle join game button"""
    query = update.callback_query
    chat_id = query.message.chat_id
    game = game_manager.get_game(chat_id)
    
    if not game or game.phase != GamePhase.LOBBY:
        await query.answer("No active lobby found!", show_alert=True)
        return
    
    user = query.from_user
    if game.add_player(user.id, user.username or user.first_name):
        await context.bot.send_message(chat_id, f"✅ **{user.first_name}** joined the cosmic voyage!")
        await update_lobby_message(context, game)
        
        player = game.players[user.id]
        if player.is_first_time:
            try:
                welcome_dm = (
                    "🌌 Welcome to Cosmic Voyage!\n\n"
                    "You've joined an epic space adventure!\n"
                    "Your secret role will be assigned when the game starts.\n\n"
                    "Use `/help` to learn more!"
                )
                await context.bot.send_message(user.id, welcome_dm)
                player.is_first_time = False
            except Exception:
                pass
    else:
        await query.answer("Lobby is full or you've already joined!", show_alert=True)


async def handle_leave_game(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle leave game button"""
    query = update.callback_query
    chat_id = query.message.chat_id
    game = game_manager.get_game(chat_id)
    
    if not game or game.phase != GamePhase.LOBBY:
        await query.answer("No active lobby found!", show_alert=True)
        return
    
    user = query.from_user
    if game.remove_player(user.id):
        await context.bot.send_message(chat_id, f"👋 **{user.first_name}** left the lobby.")
        await update_lobby_message(context, game)
    else:
        await query.answer("You're not in the lobby!", show_alert=True)


async def handle_extend_lobby(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle lobby extension button"""
    query = update.callback_query
    chat_id = query.message.chat_id
    game = game_manager.get_game(chat_id)
    
    if not game or game.phase != GamePhase.LOBBY:
        await query.answer("No active lobby found!", show_alert=True)
        return
    
    try:
        member = await context.bot.get_chat_member(chat_id, query.from_user.id)
        if member.status not in ['creator', 'administrator']:
            await query.answer("Only admins can extend the lobby timer!", show_alert=True)
            return
    except Exception:
        await query.answer("Could not verify admin status!", show_alert=True)
        return
    
    if game.lobby_extensions >= 2:
        await query.answer("Maximum extensions reached! (2 extensions allowed)", show_alert=True)
        return
    
    game.lobby_extensions += 1
    await query.answer("⏰ Lobby timer extended by 60 seconds!")
    
    for job in context.job_queue.get_jobs_by_name(f'lobby_{chat_id}'):
        job.schedule_removal()
    
    context.job_queue.run_once(lobby_timer_callback, 60, 
                              data={'chat_id': chat_id}, name=f'lobby_{chat_id}')


# handlers.py - FIND handle_player_action AND ADD THIS FEEDBACK

async def handle_player_action(update: Update, context: ContextTypes.DEFAULT_TYPE, action: str):
    """Handle player action selection"""
    query = update.callback_query
    user_id = query.from_user.id
    
    user_game = None
    for game in game_manager.games.values():
        if user_id in game.players:
            user_game = game
            break
    
    if not user_game:
        await query.answer("You're not in any active game!", show_alert=True)
        return
    
    player = user_game.players[user_id]
    action_type = action.replace("action_", "")
    user_game.pending_actions[user_id] = action_type
    
# BASIC ATTACK - Show villain targets
    if action_type == "basic_attack":
        negative_roles = [Role.BETRAYER, Role.EPIC_MONSTER, Role.SHADOW_SABOTEUR, Role.DEVIL_HUNTER]
        villain_targets = [p for p in user_game.get_living_players() if p.role in negative_roles]
        
        if not villain_targets:
            await query.edit_message_text("❌ No villains available to attack!")
            return
        
        keyboard = []
        for villain in villain_targets:
            keyboard.append([
                InlineKeyboardButton(f"{villain.username}", callback_data=f"basic_attack_{villain.user_id}")
            ])
        
        await query.edit_message_text(
            "⚔️ **Basic Attack (8 damage)**\n\nChoose your target:",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        return
    
    # PREMIUM WEAPON
    if action_type == "premium_weapon":
        await query.edit_message_text(
            "🗡️ **Choose your premium weapon:**",
            reply_markup=create_weapon_keyboard(player)
        )
        return

    if action_type == "use_relic":
        await query.edit_message_text(
            "💎 **Choose a relic to use:**",
            reply_markup=create_relic_keyboard(player)
        )
        return
    
    if action_type == "heal" and player.role == Role.HEALER:
        await query.edit_message_text(
            "🎯 **Choose your target:**",
            reply_markup=create_target_keyboard(user_game, user_id)
        )
        return
    
    if action_type == "block" and player.role == Role.SHADOW_SABOTEUR:
        await query.edit_message_text(
            "🎯 **Choose who to block:**",
            reply_markup=create_target_keyboard(user_game, user_id)
        )
        return
    
    if action_type in ["frame_job", "false_intel"] and player.role == Role.BETRAYER:
        await query.edit_message_text(
            "🎯 **Choose your target:**",
            reply_markup=create_target_keyboard(user_game, user_id)
        )
        return
    
    # ENHANCED FEEDBACK MESSAGES
    feedback_map = {
        "heal": ("🩹", "Healing Applied", "You channeled healing energy!", "success"),
        "dodge": ("💨", "Dodge Ready", "50% damage reduction prepared!", "warning"),
        "repair": ("🔧", "Ship Repair", "Hull reinforced!", "success"),
        "relic": ("🪶", "Relic Search", "Searching for artifacts...", "special"),
        "deliver": ("⚡", "Delivery Attempt", "Preparing to deliver potion!", "special"),
        "sabotage": ("🔪", "Sabotage Set", "Damage queued!", "danger"),
        "monster_attack": ("💹", "Attack Ready", "Preparing devastating blow!", "danger"),
        "boost_allies": ("📈", "Boost Active", "Villains empowered!", "danger"),
        "block": ("🚫", "Block Ready", "Target will be blocked!", "warning"),
        "boost": ("😈", "Monster Boosted", "Attack enhanced!", "danger"),
        "protect": ("🛡️", "Protection Active", "Shield ready!", "info"),
        "protect_potion": ("👼", "Guard Active", "Potion protected!", "info"),
        "rally": ("🎖️", "Rally Called", "Team will be healed!", "success"),
        "skip": ("⏭️", "Turn Skipped", "You chose to wait.", "info")
    }
    
    emoji, title, message, style = feedback_map.get(
        action_type,
        ("✅", "Action Recorded", "Your action is queued!", "info")
    )
    
    # Apply immediate effects
    if action_type == "dodge":
        player.has_dodge = True
    elif action_type == "boost_allies" and player.role == Role.EPIC_MONSTER:
        user_game.villain_boost_active = True
    elif action_type == "boost" and player.role == Role.DEVIL_HUNTER:
        user_game.devil_hunter_boost_used = True
    
    formatted = format_game_message(title, message, emoji, style)
    await query.edit_message_text(formatted, parse_mode='Markdown')


async def handle_help_section(update: Update, context: ContextTypes.DEFAULT_TYPE, data: str):
    """Handle help section selection"""
    query = update.callback_query
    section = data.replace("help_", "")
    text = HELP_TEXTS.get(section, "Information not available.")
    await query.edit_message_text(text, parse_mode='Markdown', reply_markup=create_help_keyboard())


async def handle_shop_purchase(update: Update, context: ContextTypes.DEFAULT_TYPE, data: str):
    """Handle shop item purchase"""
    query = update.callback_query
    item_key = data.replace("buy_", "").replace("_", " ")
    user_id = query.from_user.id
    
    user_game = None
    for game in game_manager.games.values():
        if user_id in game.players:
            user_game = game
            break
    
    if not user_game:
        await query.answer("You're not in any active game!", show_alert=True)
        return
    
    player = user_game.players[user_id]
    item = SHOP_ITEMS.get(item_key)
    
    if not item:
        await query.answer("Invalid item!", show_alert=True)
        return
    
    if player.coins >= item["cost"]:
        player.coins -= item["cost"]
        
        if item["effect"] == "heal":
            player.heal(item["value"])
            message = f"Restored {item['value']} HP!"
        elif item["effect"] == "shield":
            player.shields += 1
            message = "Shield activated!"
        elif item["effect"] == "reveal":
            other_players = [p for p in user_game.players.values() if p.user_id != user_id and p.role]
            if other_players:
                target = random.choice(other_players)
                message = f"Vision revealed: {target.username} is {target.role.value}"
            else:
                message = "No other players to reveal!"
        
        await query.answer(f"Purchased {item_key}! {message}")
    else:
        await query.answer("Not enough coins!", show_alert=True)


async def handle_voting(update: Update, context: ContextTypes.DEFAULT_TYPE, data: str):
    """Handle vote submission"""
    query = update.callback_query
    target_id = int(data.replace("vote_", ""))
    user_id = query.from_user.id
    
    user_game = None
    for game in game_manager.games.values():
        if user_id in game.players:
            user_game = game
            break
    
    if user_game and user_game.process_vote(user_id, target_id):
        target_name = user_game.players[target_id].username
        await query.answer(f"Voted for {target_name}!")
        await query.edit_message_text(f"✅ Your Vote has been cast for {target_name}/nThank You ")
    else:
        await query.answer("You cannot vote right now!", show_alert=True)


async def handle_target_selection(update: Update, context: ContextTypes.DEFAULT_TYPE, data: str):
    """Handle target selection for abilities"""
    query = update.callback_query
    target_id = int(data.replace("target_", ""))
    user_id = query.from_user.id
    
    user_game = None
    for game in game_manager.games.values():
        if user_id in game.players:
            user_game = game
            break
    
    if not user_game:
        await query.answer("Game not found!", show_alert=True)
        return
    
    player = user_game.players[user_id]
    player.pending_target = target_id
    
    target_player = user_game.players[target_id]
    action = user_game.pending_actions.get(user_id)
    
    if action == "heal":
        await query.edit_message_text(f"🩹  Heal for {target_player.username} recorded!")
    elif action == "block":
        await query.edit_message_text(f"🚫 Block for {target_player.username} recorded!")
    # ADD THESE LINES:
    elif action == "frame_job":
        await query.edit_message_text(f"⚔️ Frame Job targeting {target_player.username} recorded!")
    elif action == "false_intel":
        await query.edit_message_text(f"🎮 False Intel sent to {target_player.username}!")


async def upgrades_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /upgrades command."""
    if not await check_cooldown(context, update.effective_user.id):
        return
        
    chat_id = update.effective_chat.id
    game = game_manager.get_game(chat_id)

    if not game or game.phase == GamePhase.LOBBY:
        await update.message.reply_text("❌ You can only view upgrades after the game has started!")
        return
        
    upgrade_text = "🛠️ **SHIP UPGRADES** 🛠️\n\nContribute your coins to purchase permanent upgrades for the ship.\n\n"
    for key, upgrade in SHIP_UPGRADES.items():
        status = "✅ INSTALLED" if key in game.ship.upgrades else "AVAILABLE"
        upgrade_text += f"• **{upgrade['name']}** - {status}\n  └─ {upgrade['desc']}\n"
    
    await update.message.reply_text(upgrade_text, parse_mode='Markdown', reply_markup=create_upgrades_keyboard(game))

async def handle_relic_usage(update: Update, context: ContextTypes.DEFAULT_TYPE, data: str):
    """Handle relic usage"""
    query = update.callback_query
    relic_name = data.replace("use_relic_", "")
    user_id = query.from_user.id
    
    user_game = None
    for game in game_manager.games.values():
        if user_id in game.players:
            user_game = game
            break
    
    if not user_game:
        await query.answer("Game not found!", show_alert=True)
        return
    
    player = user_game.players[user_id]
    
    if relic_name in player.relics:
        effect = RELIC_EFFECTS[relic_name]
        if effect["type"] == "one_time":
            if effect["effect"] == "heal":
                player.heal(effect["value"])
                message = f"Restored {effect['value']} HP!"
            elif effect["effect"] == "coins":
                player.coins += effect["value"]
                message = f"Gained {effect['value']} coins!"
            
            player.relics.remove(relic_name)
            await query.edit_message_text(f"💎 Used {relic_name}!\n{message}")
        else:
            await query.answer("This relic is passive and doesn't need activation!", show_alert=True)
    else:
        await query.answer("You don't have this relic!", show_alert=True)