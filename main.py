import logging
import asyncio
from telegram import Update
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, filters

from config import BOT_TOKEN
from handlers import (
    start_command, help_command, newgame_command, join_command,
    leave_command, status_command, players_command, startvoyage_command,
    endgame_command, myrole_command, inventory_command, tutorial_command,
    shop_command, spectate_command, button_callback, added_to_group,
    upgrades_command, commands_command # ADD THIS LINE
)

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)


async def main():
    """Start the bot"""
    if not BOT_TOKEN or BOT_TOKEN == "YOUR_BOT_TOKEN_HERE":
        logger.error("Bot token not configured!")
        return

    application = Application.builder().token(BOT_TOKEN).connect_timeout(30).read_timeout(30).build()

    # Add handlers
    application.add_handler(CommandHandler("start", start_command))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("commands", commands_command)) 
    application.add_handler(CommandHandler("newgame", newgame_command))
    application.add_handler(CommandHandler("join", join_command))
    application.add_handler(CommandHandler("leave", leave_command))
    application.add_handler(CommandHandler("status", status_command))
    application.add_handler(CommandHandler("players", players_command))
    application.add_handler(CommandHandler("myrole", myrole_command))
    application.add_handler(CommandHandler("inventory", inventory_command))
    application.add_handler(CommandHandler("tutorial", tutorial_command))
    application.add_handler(CommandHandler("shop", shop_command))
    application.add_handler(CommandHandler("upgrades", upgrades_command))
    application.add_handler(CommandHandler("spectate", spectate_command))
    application.add_handler(CommandHandler("startvoyage", startvoyage_command))
    application.add_handler(CommandHandler("endgame", endgame_command))
    application.add_handler(CallbackQueryHandler(button_callback))
    application.add_handler(MessageHandler(filters.StatusUpdate.NEW_CHAT_MEMBERS, added_to_group))

    logger.info("Cosmic Voyage Bot is running...")

    # Initialize and run
    try:
        await application.initialize()
        await application.updater.start_polling(allowed_updates=Update.ALL_TYPES)
        await application.start()
        logger.info("Bot started successfully!")
        await asyncio.Event().wait()
    except (KeyboardInterrupt, SystemExit):
        logger.info("Bot stopping...")
    finally:
        if application.updater.running:
            await application.updater.stop()
        if application.running:
            await application.stop()
        await application.shutdown()
        logger.info("Bot stopped.")


if __name__ == "__main__":
    asyncio.run(main())






