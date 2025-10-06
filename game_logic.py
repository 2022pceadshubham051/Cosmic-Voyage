import asyncio
import random
import logging
from datetime import datetime, timedelta
from typing import List
from config import RANDOM_EVENTS, RANDOM_EVENT_CHANCE, SECRET_OBJECTIVES, SHIP_UPGRADES
from utils import format_game_message, create_progress_bar, create_player_status_card

from telegram.ext import ContextTypes

from config import (
    Role, GamePhase, GIFS, POTION_DAY, ACTION_TIMER, TOTAL_DAYS,
    DIVINE_INTERVENTION_PROB, DIVINE_HEAL_AMOUNT, HEAL_SELF_AMOUNT,
    REPAIR_SHIP_AMOUNT
)
from models import CosmicVoyage, GameManager
from utils import (
    send_message_wrapper, send_animation_wrapper, get_day_gif,
    generate_status_image, create_action_keyboard, get_role_description,
    create_vote_keyboard
)

logger = logging.getLogger(__name__)

from context import game_manager


def get_role_abilities_highlight(role):
    """Get formatted abilities for role"""
    abilities_map = {
        Role.CAPTAIN: "▸ Reduce ship damage by 20%\n▸ Rally team (+10 HP all)\n▸ Repair ship (+15 HP)",
        Role.HEALER: "▸ Heal players (+20 HP)\n▸ Repair ship (+15 HP)\n▸ Target healing",
        Role.ORACLE: "▸ Predict hazards\n▸ Detect monsters",
        Role.DRAGON_RIDER: "▸ Reduce monster dmg 50%\n▸ Protect team",
        Role.EXPLORER: "▸ Find relics\n▸ Boost abilities",
        Role.BETRAYER: "▸ Sabotage ship\n▸ Transform Day 10\n▸ Mind games",
        Role.EPIC_MONSTER: "▸ Multi-attacks\n▸ Boost villains\n▸ Devastating power",
        Role.SHADOW_SABOTEUR: "▸ Block actions\n▸ Create chaos",
        Role.DEVIL_HUNTER: "▸ Boost monster\n▸ Sabotage"
    }
    return abilities_map.get(role, "▸ Support team\n▸ Survive")


async def start_game(context: ContextTypes.DEFAULT_TYPE, chat_id: int):
    """Start the game after lobby ends"""
    logger.info(f"=== START_GAME CALLED for chat {chat_id} ===")
    
    game = game_manager.get_game(chat_id)
    if not game:
        logger.error(f"No game found for chat {chat_id}")
        return
    
    logger.info(f"Game found with {len(game.players)} players")
    
    # Scale ship HP based on player count - STARTING AT HALF
    player_count = len(game.players)
    if player_count <= 4:
        game.ship.max_hp = 80
        game.ship.hp = 56  # Half of max
    elif player_count <= 6:
        game.ship.max_hp = 100
        game.ship.hp = 70  # Half of max
    elif player_count <= 10:
        game.ship.max_hp = 120
        game.ship.hp = 84  # Half of max
    else:
        game.ship.max_hp = 140
        game.ship.hp = 98  # Half of max
    
    logger.info(f"Ship HP set to {game.ship.hp}/{game.ship.max_hp} (starting at 70%)")
    
    # Assign roles
    game.assign_roles()
    game.phase = GamePhase.HEALING
    game.current_day = 1
    game.game_start_time = datetime.now()
    game.assign_secret_objectives()
    
    logger.info("Roles assigned, phase set to HEALING")
    
    # Send start message with updated HP display
    try:
        await send_animation_wrapper(
            context, chat_id, GIFS['voyage_start'],
            caption=(
                "🚀 **COSMIC VOYAGE BEGINS!** 🚀\n\n"
                "Your starship launches from Mystara towards the cosmic realm of Eldoria!\n\n"
                f"👥 **Crew Size:** {len(game.players)} brave souls\n"
                f"🚢 **Ship Integrity:** {game.ship.hp}/{game.ship.max_hp} HP (⚠️ DAMAGED!)\n"
                f"🌌 **Mission:** Deliver the Cosmic Potion\n\n"
                "⚠️ **Days 1-3: Healing Phase**\n"
                "The ship sustained damage during launch. Repair it quickly!\n\n"
                "*Secret roles have been assigned via DM!*"
            ),
            parse_mode='Markdown'
        )
        logger.info("Start animation sent successfully")
    except Exception as e:
        logger.error(f"Failed to send start animation: {e}")
    
    # Send roles via DM
    logger.info("Sending role DMs to players...")
    
    # Get all negative roles except Betrayer
    revealed_villains = []
    for player in game.players.values():
        if player.role in [Role.SHADOW_SABOTEUR, Role.DEVIL_HUNTER] and player.role != Role.BETRAYER:
            revealed_villains.append(player)
    
    # FIXED: Proper indentation for this loop
    for player in game.players.values():
        try:
            negative_roles = [Role.BETRAYER, Role.EPIC_MONSTER, Role.SHADOW_SABOTEUR, Role.DEVIL_HUNTER]
            is_villain = player.role in negative_roles
            
            alignment_display = "🔴 **DARK SIDE**" if is_villain else "🔵 **LIGHT SIDE**"
            
            # Build allies section
            allies_section = ""
            if is_villain and player.role != Role.BETRAYER and revealed_villains:
                ally_list = "\n".join([
                    f"  ▸ {v.username} - {v.role.value}" 
                    for v in revealed_villains if v.user_id != player.user_id
                ])
                allies_section = f"""
**Your Demon Allies:**
{ally_list}

⚠️ Betrayer identity is hidden
"""
            
            abilities = get_role_abilities_highlight(player.role)
            
            role_message = format_game_message(
                "YOUR SECRET ROLE",
                f"""**{player.role.value}**
{alignment_display}

{get_role_description(player.role)}

**Your Abilities:**
{abilities}

{allies_section}

**Current Status:**
└─ ❤️ HP: {player.hp}/100
└─ 🚢 Ship: {game.ship.hp}/{game.ship.max_hp}
└─ 🪙 Coins: {player.coins}

Use /myrole to review anytime""",
                emoji="🎭",
                style="special"
            )
            
            await context.bot.send_message(player.user_id, role_message, parse_mode='Markdown')
            logger.info(f"Role DM sent to {player.username}")
        except Exception as e:
            logger.error(f"Failed to send role to {player.username}: {e}")
    
    # Schedule the first day to start
    logger.info("Scheduling first day...")
    await asyncio.sleep(5)  # Give players a moment to read their roles
    context.job_queue.run_once(
        next_day_callback, 1,
        data={'chat_id': chat_id},
        name=f'day_{chat_id}'
    )


async def run_day_phase(context: ContextTypes.DEFAULT_TYPE, chat_id: int):
    """Run a single day phase"""
    logger.info(f"=== RUN_DAY_PHASE STARTED for chat {chat_id} ===")
    
    game = game_manager.get_game(chat_id)
    if not game:
        logger.error(f"No game found in run_day_phase for chat {chat_id}")
        return
    
    if game.phase == GamePhase.ENDED:
        logger.warning(f"Game already ended for chat {chat_id}")
        return
    
    logger.info(f"Current day: {game.current_day}, Phase: {game.phase}")
    
    # Check collateral damage deaths - FASTER NOW
    logger.info("Checking collateral damage deaths...")
    for player in list(game.players.values()):
        if player.collateral_damage > 0 and game.current_day - player.collateral_day >= 4:
            player.is_alive = False
            await send_message_wrapper(
                context, chat_id,
                f"💀 **{player.username}** succumbed to untreated collateral damage!",
                is_major=True
            )
            game.spectators.add(player.user_id)
            logger.info(f"{player.username} died from collateral damage")
    
    # Check win conditions
    logger.info("Checking win conditions...")
    winner = game.check_win_condition()
    if winner:
        logger.info(f"Win condition met: {winner}")
        await end_game_victory(context, chat_id, winner)
        return
    
    # Determine phase
    if game.current_day <= 3:
        game.phase = GamePhase.HEALING
        phase_name = "Healing Phase"
    elif game.current_day <= 9:
        game.phase = GamePhase.VOYAGE
        phase_name = "Cosmic Voyage"
    elif game.current_day == 10:
        game.phase = GamePhase.POTION_QUEST
        phase_name = "Potion Quest"
    elif game.current_day <= 12:
        game.phase = GamePhase.SHOWDOWN
        phase_name = "Monster Showdown"
    else:
        game.phase = GamePhase.DELIVERY
        phase_name = "Final Delivery"
    
    logger.info(f"Phase determined: {phase_name}")
    
    # Day start message
    logger.info("Sending day start message...")
    try:
        await send_animation_wrapper(
            context, chat_id, get_day_gif(game.current_day),
            caption=(
                f"🌅 **DAY {game.current_day} - {phase_name.upper()}** 🌅\n\n"
                f"🚢 **Ship HP:** {game.ship.hp}/{game.ship.max_hp}\n"
                f"👥 **Crew Alive:** {len(game.get_living_players())}/{len(game.players)}\n"
                f"🌌 **Mission Progress:** {game.current_day}/{TOTAL_DAYS} days\n\n"
                "⚡ **Actions will be requested via DM shortly...**"
            ),
            parse_mode='Markdown'
        )
        logger.info("Day start message sent")
    except Exception as e:
        logger.error(f"Failed to send day start message: {e}")
    
    # Send status image
    logger.info("Generating status image...")
    try:
        buf = generate_status_image(game)
        if buf:
            await context.bot.send_photo(chat_id, photo=buf)
            logger.info("Status image sent")
    except Exception as e:
        logger.error(f"Failed to send status image: {e}")
    
    await asyncio.sleep(2)
    
    # Divine intervention
    if random.random() < DIVINE_INTERVENTION_PROB and game.current_day > 3:
        logger.info("Divine intervention triggered!")
        negative_roles = [Role.BETRAYER, Role.EPIC_MONSTER, Role.SHADOW_SABOTEUR, Role.DEVIL_HUNTER]
        positive_players = [p for p in game.get_living_players() if p.role not in negative_roles]
        for p in positive_players:
            p.heal(DIVINE_HEAL_AMOUNT)
        await send_message_wrapper(
            context, chat_id,
            "✨ **Divine Intervention!** All heroes healed +20 HP!",
            is_major=True
        )
    
    # Special events
    if game.current_day == POTION_DAY:
        logger.info("Potion day event triggered")
        await handle_potion_day(context, chat_id)
    
    # Request actions
    logger.info("Requesting player actions...")
    await request_player_actions(context, chat_id)
    
    # Wait for actions
    logger.info(f"Waiting {ACTION_TIMER} seconds for player actions...")
    start_time = datetime.now()
    while datetime.now() - start_time < timedelta(seconds=ACTION_TIMER):
        if len(game.pending_actions) >= len(game.get_living_players()):
            logger.info("All players have submitted actions early")
            break
        await asyncio.sleep(1)
    
    logger.info(f"Actions received: {len(game.pending_actions)}/{len(game.get_living_players())}")
    
    # Process events
    logger.info("Processing day events...")
    await process_day_events(context, chat_id)
    
    # Voting phase
    if game.current_day >= 4 and not game.betrayer_caught:
        logger.info("Starting voting phase...")
        await send_message_wrapper(
            context, chat_id,
            "🗳️ **VOTING PHASE** 🗳️\n\nVote for who you suspect is the betrayer!\nCheck your DMs to cast your vote.",
            is_major=True
        )
        
        game.start_voting()
        for player in game.get_living_players():
            try:
                await context.bot.send_message(
                    player.user_id,
                    "🗳️ **TIME TO VOTE!**\n\nWho do you suspect?\nChoose wisely:",
                    reply_markup=create_vote_keyboard(game)
                )
            except Exception as e:
                logger.error(f"Could not send vote request to {player.username}: {e}")
        
        # Wait for votes
        logger.info("Waiting for votes...")
        start_time = datetime.now()
        while datetime.now() - start_time < timedelta(seconds=ACTION_TIMER):
            if len(game.voted) >= len(game.get_living_players()):
                break
            await asyncio.sleep(1)
        
        # Process votes
        logger.info("Processing votes...")
        eliminated_id = game.end_voting()
        if eliminated_id:
            eliminated_player = game.players[eliminated_id]
            if eliminated_id == game.betrayer_id and not game.monster_revealed:
                await send_message_wrapper(
                    context, chat_id,
                    f"❌ **THE CREW HAS SPOKEN!**\n\n**{eliminated_player.username}** is the Betrayer!\nThey transform into **Epic Monster**!",
                    is_major=True
                )
            else:
                await send_message_wrapper(
                    context, chat_id,
                    f"❌ **THE CREW HAS SPOKEN!**\n\n**{eliminated_player.username}** has been voted out!\nTheir role was: **{eliminated_player.role.value}**",
                    is_major=True
                )
                game.spectators.add(eliminated_id)
    
    # Check win conditions again
    winner = game.check_win_condition()
    if winner:
        logger.info(f"Win condition met after voting: {winner}")
        await end_game_victory(context, chat_id, winner)
        return
    
    # Next day
    game.current_day += 1
    logger.info(f"Day phase complete. Next day: {game.current_day}")
    
    if game.current_day <= TOTAL_DAYS:
        logger.info("Scheduling next day...")
        await asyncio.sleep(5)
        context.job_queue.run_once(
            next_day_callback, 1,
            data={'chat_id': chat_id},
            name=f'day_{chat_id}'
        )
    else:
        logger.info("Game duration complete, checking final result...")
        final_winner = game.check_win_condition() or 'monster'
        await end_game_victory(context, chat_id, final_winner)

    if random.random() < RANDOM_EVENT_CHANCE:
        event_key = random.choice(list(RANDOM_EVENTS.keys()))
        game.active_random_event = RANDOM_EVENTS[event_key]
        await send_message_wrapper(
            context, chat_id,
            f"🌪️ **RANDOM EVENT: {game.active_random_event['name']}** 🌪️\n\n_{game.active_random_event['desc']}_",
            is_major=True, parse_mode='Markdown'
        )

    # AUTO-REPAIR FROM UPGRADE
    if "auto_repair_system" in game.ship.upgrades:
        game.ship.repair(5)


async def next_day_callback(context: ContextTypes.DEFAULT_TYPE):
    """Callback for scheduling next day"""
    job = context.job
    chat_id = job.data['chat_id']
    logger.info(f"Next day callback triggered for chat {chat_id}")
    await run_day_phase(context, chat_id)


async def request_player_actions(context: ContextTypes.DEFAULT_TYPE, chat_id: int):
    """Request actions from all living players"""
    game = game_manager.get_game(chat_id)
    if not game:
        return
    
    game.pending_actions.clear()
    
    for player in game.get_living_players():
        if player.action_blocked:
            player.action_blocked = False
            try:
                await context.bot.send_message(
                    player.user_id,
                    "🚫 **ACTION BLOCKED!**\n\nThe Shadow Saboteur prevented you from taking action today."
                )
            except Exception as e:
                logger.error(f"Could not send block message to {player.username}: {e}")
            continue
        
        try:
            await context.bot.send_message(
                player.user_id,
                f"⚡ **DAY {game.current_day} - CHOOSE YOUR ACTION!** ⚡\n\n"
                f"📊 **Your Status:**\n"
                f"❤️ HP: {player.hp}/100\n"
                f"🪙 Coins: {player.coins}\n"
                f"🛡 Shields: {player.shields}\n\n"
                f"🚢 **Ship Status:** {game.ship.hp}/{game.ship.max_hp} HP\n\n"
                f"⏰ **Time Limit:** {ACTION_TIMER} seconds\n\nChoose your action below:",
                reply_markup=create_action_keyboard(player, game),
                parse_mode='Markdown'
            )
            logger.info(f"Action request sent to {player.username}")
        except Exception as e:
            logger.error(f"Could not send action request to {player.username}: {e}")


async def process_day_events(context: ContextTypes.DEFAULT_TYPE, chat_id: int):
    """Process all actions and events for the day"""
    game = game_manager.get_game(chat_id)
    if not game:
        return
        
    events = []
    
    villain_multiplier = 1.0
    if game.active_random_event and game.active_random_event['name'] == "Traitor's Moon":
        villain_multiplier = 2.0
    
    is_anonymous = game.active_random_event and game.active_random_event['name'] == "Cosmic Flare"

    # Process player actions
    for player in game.get_living_players():
        action = game.pending_actions.get(player.user_id, "skip")
        player.basic_attack_used_today = False
        
        if not player.objective_completed and player.secret_objective:
            if player.secret_objective['desc'] == "Heal 3 different players." and action == "heal" and player.pending_target:
                player.objective_progress += 1
            elif player.secret_objective['desc'] == "Find 2 relics." and action == "relic":
                player.objective_progress += 1
            elif player.secret_objective['desc'] == "Successfully use Rally Team twice." and action == "rally":
                player.objective_progress += 1
         
        if action == "basic_attack" and player.pending_target:
            target = game.players.get(player.pending_target)
            if target and target.is_alive:
                from config import DEFAULT_WEAPON
                damage = DEFAULT_WEAPON["damage"]
                target.take_damage(damage)
                events.append(f"⚔️ {player.username} attacked {target.username} with Basic Strike! (-{damage} HP)")
                
                if not target.is_alive:
                    events.append(f"💀 {target.username} has been slain!")
                    game.spectators.add(target.user_id)
        
        # PREMIUM WEAPON ATTACK
        elif action == "weapon_attack" and player.pending_target and hasattr(player, 'selected_weapon'):
            target = game.players.get(player.pending_target)
            weapon_name = player.selected_weapon
            
            if target and weapon_name in player.weapons and player.weapons[weapon_name] > 0:
                from config import PREMIUM_WEAPONS
                weapon_data = PREMIUM_WEAPONS[weapon_name]
                damage = weapon_data["damage"]
                
                target.take_damage(damage)
                player.weapons[weapon_name] -= 1
                
                events.append(f"🗡️ {player.username} attacked {target.username} with {weapon_name}! (-{damage} HP)")
                
                if not target.is_alive:
                    events.append(f"💀 {target.username} has been eliminated!")
                    game.spectators.add(target.user_id)
        
        player.pending_target = None
        if hasattr(player, 'selected_weapon'):
            delattr(player, 'selected_weapon')
        
        elif action == "heal":
            if player.pending_target and player.role == Role.HEALER:
                target = game.players.get(player.pending_target)
                if target:
                    target.heal(HEAL_SELF_AMOUNT)
                    events.append(f"🩹  {player.username} healed {target.username} (+{HEAL_SELF_AMOUNT} HP)")
                    player.healed_targets.add(player.pending_target)
                    player.objective_progress = len(player.healed_targets)
            else:
                player.heal(HEAL_SELF_AMOUNT)
                events.append(f"🩹  {player.username} healed themselves (+{HEAL_SELF_AMOUNT} HP)")
        
        elif action == "repair" and player.role in [Role.HEALER, Role.CAPTAIN]:
            game.ship.repair(REPAIR_SHIP_AMOUNT)
            events.append(f"🔧 {player.username} repaired the ship (+{REPAIR_SHIP_AMOUNT} HP)")
        
        elif action == "protect" and player.role == Role.DRAGON_RIDER:
            events.append(f"🐉 {player.username} is protecting the team")
        
        elif action == "relic" and player.role == Role.EXPLORER:
            from config import RELIC_EFFECTS
            available_relics = [r for r in RELIC_EFFECTS.keys() if r not in player.relics]
            if available_relics:
                found_relic = random.choice(available_relics)
                player.relics.append(found_relic)
                events.append(f"🪶 {player.username} found the {found_relic}")
        
        elif action == "rally" and player.role == Role.CAPTAIN and player.rally_uses > 0:
            for p in game.get_living_players():
                p.heal(10)
            player.rally_uses -= 1
            events.append(f"🎖 {player.username} rallied the team! +10 HP to all")
        
        elif action == "sabotage" and player.role == Role.BETRAYER:
            damage = int(random.randint(12, 22) * villain_multiplier)
            damage = game.apply_captain_damage_reduction(damage)
            game.ship.take_damage(damage)
            events.append(f"🔪 Sabotage! Ship took {damage} damage (anonymous)")
            if not player.objective_completed and player.secret_objective['desc'] == "Successfully sabotage the ship for a total of 50 damage.":
                player.objective_progress += damage

        elif action == "deliver" and player.has_potion:
            game.potion_delivered = True
            events.append(f"⚡ **{player.username} delivered the Cosmic Potion!** The team wins!")
        
        elif action == "block" and player.pending_target and player.role == Role.SHADOW_SABOTEUR:
            target = game.players.get(player.pending_target)
            if target:
                target.action_blocked = True
                game.shadow_saboteur_uses += 1
                events.append(f"🚫 Someone's action was blocked (anonymous)")

        elif action == "frame_job" and player.role == Role.BETRAYER and player.frame_job_uses > 0 and player.pending_target:
            target = game.players.get(player.pending_target)
            if target and target.role != Role.BETRAYER:
                player.frame_job_uses -= 1
                events.append(f"🎭 Someone's action caused minor damage! (Suspicious)")
                game.ship.take_damage(5)
        
        elif action == "false_intel" and player.role == Role.BETRAYER and player.false_intel_uses > 0 and player.pending_target:
            target = game.players.get(player.pending_target)
            if target and target.role != Role.BETRAYER:
                player.false_intel_uses -= 1
                try:
                    await context.bot.send_message(target.user_id, f"🤫 Anonymous tip: {random.choice(['Someone saw a crew member near the engine room...', 'Strange noises were heard from the cargo bay...', 'A player was acting suspiciously...'])}")
                except Exception:
                    pass

        player.pending_target = None

    # SECRET OBJECTIVE COMPLETION CHECK
    for player in game.get_living_players():
        if not player.objective_completed and player.secret_objective:
            obj = player.secret_objective
            is_complete = False
            
            if obj['desc'] == "Survive until Day 8." and game.current_day >= obj['target_count']:
                is_complete = True
            elif obj['desc'] == "Successfully sabotage the ship for a total of 50 damage." and player.objective_progress >= obj['target_count']:
                is_complete = True
            elif player.objective_progress >= obj['target_count']:
                is_complete = True

            if is_complete:
                player.objective_completed = True
                reward_msg = f"🎯 **Secret Mission Complete!** You completed: '{obj['desc']}'.\n"
                if obj['reward_type'] == 'coins':
                    player.coins += obj['value']
                    reward_msg += f"💰 You have been awarded {obj['value']} coins!"
                elif obj['reward_type'] == 'item':
                    player.shields += 1
                    reward_msg += f"🛡️ You have received a free Shield!"
                elif obj['reward_type'] == 'hp_boost':
                     player.hp += obj['value']
                     reward_msg += f"❤️ Your HP has been boosted by {obj['value']}!"
                
                try:
                    await context.bot.send_message(player.user_id, reward_msg)
                except Exception:
                    pass
    
    # Random hazards
    if game.phase == GamePhase.VOYAGE and random.random() < 0.5:
        hazard = random.choice(["Cosmic Storm", "Meteor Shower", "Solar Flare", "Dimensional Rift"])
        damage = game.apply_captain_damage_reduction(random.randint(8, 18))
        game.ship.take_damage(damage)
        events.append(f"🌪️ {hazard} hit the ship! (-{damage} HP)")
    
    # Monster attack
    if game.monster_revealed and game.monster_id and game.players[game.monster_id].is_alive:
        await process_monster_attack(context, game, events)
    
    # Daily coins
    game.earn_coins()

    # Reset the active random event at the end of the day
    game.active_random_event = None
    game.villain_boost_active = False
    
    # Send events
    if events:
        event_summary = "\n".join([f"  ▸ {event}" for event in events[:8]])
        if len(events) > 8:
            event_summary += f"\n  ... +{len(events) - 8} more"
        
        alive_count = len(game.get_living_players())
        ship_percent = int((game.ship.hp / game.ship.max_hp) * 100)
        
        if ship_percent > 70:
            ship_status = "🟢 GOOD"
        elif ship_percent > 40:
            ship_status = "🟡 DAMAGED"
        else:
            ship_status = "🔴 CRITICAL"
        
        formatted_events = format_game_message(
            f"DAY {game.current_day} EVENTS",
            f"""**Mission Status**
└─ Phase: {game.phase.value.title()}

**Ship Status**
└─ HP: {game.ship.hp}/{game.ship.max_hp}
└─ Status: {ship_status}

**Crew**
└─ Alive: {alive_count}/{len(game.players)}

**Today's Events:**
{event_summary}""",
            emoji="📜",
            style="info"
        )
        
        await send_message_wrapper(context, chat_id, formatted_events, is_major=True, parse_mode='Markdown')


async def process_monster_attack(context: ContextTypes.DEFAULT_TYPE, game: CosmicVoyage, events: List[str]):
    """Process monster attack logic"""
    monster = game.players.get(game.monster_id)
    if not monster or not monster.is_alive:
        return
    
    devil_boost = 1.5 if game.devil_hunter_boost_used else 1.0
    villain_boost = 1.5 if game.villain_boost_active else 1.0
    total_boost = devil_boost * villain_boost
    
    ship_damage = game.apply_captain_damage_reduction(int(random.randint(20, 35) * total_boost))
    game.ship.take_damage(ship_damage)
    events.append(f"👹 Monster attacked the ship! (-{ship_damage} HP)")
    
    targets = [p for p in game.get_living_players() if p.user_id != game.monster_id]
    num_targets = min(len(targets), 2)
    
    if num_targets > 0:
        for target in random.sample(targets, num_targets):
            is_dragon_protected = any(
                p.role == Role.DRAGON_RIDER and p.is_alive and 
                game.pending_actions.get(p.user_id) == "protect" 
                for p in game.players.values()
            )
            
            damage = int(random.randint(25, 40) * total_boost)
            if is_dragon_protected:
                damage = int(damage * 0.6)
            
            target.take_damage(damage, is_collateral=True, current_day=game.current_day)
            events.append(f"👹 {target.username} took {damage} collateral damage!")
    
    await send_animation_wrapper(context, game.chat_id, GIFS['monster_attack'], 
                               caption="👹 **EPIC MONSTER ATTACK!** 👹")


async def handle_potion_day(context: ContextTypes.DEFAULT_TYPE, chat_id: int):
    """Handle day 10 potion appearance"""
    game = game_manager.get_game(chat_id)
    if not game:
        return
    
    negative_roles = [Role.BETRAYER, Role.EPIC_MONSTER, Role.SHADOW_SABOTEUR, Role.DEVIL_HUNTER]
    positive_players = [p for p in game.get_living_players() if p.role not in negative_roles]
    
    if not positive_players:
        return
    
    potion_bearer = random.choice(positive_players)
    potion_bearer.has_potion = True
    
    if game.betrayer_id in game.players and game.players[game.betrayer_id].is_alive and not game.monster_revealed:
        game.players[game.betrayer_id].role = Role.EPIC_MONSTER
        game.monster_revealed = True
    
    await send_animation_wrapper(
        context, chat_id, GIFS['potion_found'],
        caption=(
            "⚡**COSMIC POTION DISCOVERED!** ⚡\n\n"
            f"**{potion_bearer.username}** has been chosen as the Potion Carrier!\n\n"
            "🎯 **New Mission:** Protect the Potion Carrier and deliver the potion!\n"
            "⏰ **Deadline:** Day 13\n\n"
            "👹 **THE MONSTER REVEALS ITSELF!** 👹\n"
            "The cosmic entity shows its true form!\n\n"
            "*The final battle begins...*"
        ),
        parse_mode='Markdown', is_major=True
    )


async def end_game_victory(context: ContextTypes.DEFAULT_TYPE, chat_id: int, winner: str):
    """End game and announce winner"""
    game = game_manager.get_game(chat_id)
    if not game or game.phase == GamePhase.ENDED:
        return
    
    game.phase = GamePhase.ENDED
    
    # Cancel jobs
    jobs = context.job_queue.get_jobs_by_name(f'day_{chat_id}')
    for job in jobs:
        job.schedule_removal()
    
    # Determine winners/losers
    villain_roles = [Role.BETRAYER, Role.EPIC_MONSTER, Role.SHADOW_SABOTEUR, Role.DEVIL_HUNTER]
    winners = []
    losers = []
    mvp_candidates = []
    
    winning_team = 'team' if winner == 'team' else 'monster'
    
    for player in game.players.values():
        is_villain = player.role in villain_roles
        mvp_candidates.append((player, player.coins))
        
        if (winning_team == 'team' and not is_villain) or \
           (winning_team == 'monster' and is_villain):
            winners.append(f"  ✅ {player.username} - {player.role.value}")
        else:
            losers.append(f"  ❌ {player.username} - {player.role.value}")
    
    mvp_candidates.sort(key=lambda x: x[1], reverse=True)
    mvp = mvp_candidates[0][0] if mvp_candidates else None
    
    duration = datetime.now() - game.game_start_time
    survival_rate = (len(game.get_living_players()) / len(game.players)) * 100 if game.players else 0
    
    if winner == 'team':
        title = "VICTORY - LIGHT TRIUMPHS!"
        emoji = "⭐"
        flavor = "_Potion delivered! Light prevails!_"
        gif = GIFS['victory']
    else:
        title = "DEFEAT - DARKNESS WINS!"
        emoji = "👹"
        flavor = "_Ship destroyed... Darkness reigns._"
        gif = GIFS['defeat']
    
    final_message = format_game_message(
        title,
        f"""{emoji} **GAME OVER** {emoji}

{flavor}

**🏆 WINNERS:**
{chr(10).join(winners)}

**💔 LOSERS:**
{chr(10).join(losers)}

**📊 STATISTICS:**
└─ ⏱️ Duration: {str(duration).split('.')[0]}
└─ ❤️ Survival: {survival_rate:.1f}%
└─ 🚢 Ship: {game.ship.hp}/{game.ship.max_hp}
└─ 👥 Players: {len(game.players)}
└─ 📅 Days: {game.current_day}/{TOTAL_DAYS}

{f"**⭐ MVP:** {mvp.username} ({mvp.coins} coins)" if mvp else ""}

_Thanks for playing! Use /newgame again!_""",
        emoji="🎮",
        style="special"
    )
    
    await send_animation_wrapper(
        context, chat_id, gif,
        caption=final_message,
        parse_mode='Markdown',
        is_major=True
    )
    
    game_manager.end_game(chat_id)