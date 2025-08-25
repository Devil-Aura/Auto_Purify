import logging
from pyrogram import Client
from config import Config

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)
LOGGER = logging.getLogger(__name__)

class AutoRenameBot(Client):
    def __init__(self):
        super().__init__(
            "Auto-Rename-Bot",
            api_id=Config.API_ID,
            api_hash=Config.API_HASH,
            bot_token=Config.BOT_TOKEN,
            plugins=dict(root="Plugins")
        )

    async def start(self):
        await super().start()
        me = await self.get_me()
        LOGGER.info("Bot started as @%s ✅", me.username)

    async def stop(self, *args):
        await super().stop()
        LOGGER.info("Bot stopped ❌")

if __name__ == "__main__":
    AutoRenameBot().run()
