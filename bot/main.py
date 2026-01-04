# bot/main.py
"""Main entry point for the Mudlet Bug Bot."""
import asyncio
import logging
import signal
import sys

import discord
from aiohttp import web
from discord.ext import commands
from dotenv import load_dotenv

from bot.config import Config

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger(__name__)


class MudletBugBot(commands.Bot):
    """Discord bot for extracting and filing Mudlet bug reports."""

    def __init__(self, config: Config) -> None:
        intents = discord.Intents.default()
        intents.message_content = True
        super().__init__(command_prefix="!", intents=intents)
        self.config = config
        self._health_app: web.Application | None = None
        self._health_runner: web.AppRunner | None = None

    async def setup_hook(self) -> None:
        """Called when bot is starting up."""
        await self.load_extension("bot.cogs.bug_reporter")
        if self.config.test_guild_id:
            guild = discord.Object(id=int(self.config.test_guild_id))
            # Clear existing commands first to remove any stale registrations
            self.tree.clear_commands(guild=guild)
            self.tree.copy_global_to(guild=guild)
            await self.tree.sync(guild=guild)
            logger.info(f"Cleared and synced commands to test guild {self.config.test_guild_id}")
        else:
            await self.tree.sync()
            logger.info("Synced commands globally")
        await self._start_health_server()

    async def on_ready(self) -> None:
        """Called when bot is fully connected."""
        if self.user:
            logger.info(f"Logged in as {self.user} (ID: {self.user.id})")
        logger.info(f"Connected to {len(self.guilds)} guilds")
        # Log registered commands
        for cmd in self.tree.get_commands():
            logger.info(f"Registered command: /{cmd.name}")

    async def on_app_command_error(
        self, interaction: discord.Interaction, error: discord.app_commands.AppCommandError
    ) -> None:
        """Handle slash command errors."""
        logger.error(f"Command error: {error}", exc_info=True)
        if interaction.response.is_done():
            await interaction.followup.send(f"Error: {error}", ephemeral=True)
        else:
            await interaction.response.send_message(f"Error: {error}", ephemeral=True)

    async def _start_health_server(self) -> None:
        """Start the health check HTTP server."""
        self._health_app = web.Application()
        self._health_app.router.add_get("/health", self._health_handler)
        self._health_runner = web.AppRunner(self._health_app)
        await self._health_runner.setup()
        site = web.TCPSite(self._health_runner, "0.0.0.0", self.config.health_port)
        await site.start()
        logger.info(f"Health check server started on port {self.config.health_port}")

    async def _health_handler(self, request: web.Request) -> web.Response:
        """Handle health check requests."""
        return web.json_response({
            "status": "healthy",
            "latency_ms": round(self.latency * 1000, 2)
        })

    async def close(self) -> None:
        """Clean up on shutdown."""
        if self._health_runner:
            await self._health_runner.cleanup()
        await super().close()


async def main() -> None:
    """Main entry point."""
    load_dotenv()
    config = Config()
    errors = config.validate()
    if errors:
        for error in errors:
            logger.error(f"Config error: {error}")
        sys.exit(1)

    logging.getLogger().setLevel(config.log_level)
    bot = MudletBugBot(config)

    def handle_signal(sig: signal.Signals) -> None:
        logger.info(f"Received {sig.name}, shutting down...")
        asyncio.create_task(bot.close())

    loop = asyncio.get_event_loop()
    for sig in (signal.SIGINT, signal.SIGTERM):
        loop.add_signal_handler(sig, lambda s: handle_signal(s), sig)

    try:
        await bot.start(config.discord_token)
    except Exception as e:
        logger.error(f"Bot error: {e}")
        await bot.close()
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
