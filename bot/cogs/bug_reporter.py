# bot/cogs/bug_reporter.py
"""Bug reporter cog providing the /bug slash command."""

import logging
import re
from typing import TYPE_CHECKING

import discord
from discord import app_commands
from discord.ext import commands

from bot.models.bug_report import BugReport
from bot.services.duplicates import DuplicateDetector, DuplicateResult
from bot.services.github_client import GitHubClient
from bot.services.labels import detect_labels, validate_labels
from bot.services.llm import LLMService

if TYPE_CHECKING:
    from bot.main import MudletBugBot

logger = logging.getLogger(__name__)

# Preview timeout: 13 minutes (allowing users time to review before Discord's 15-min limit)
PREVIEW_TIMEOUT = 13 * 60


class PreviewView(discord.ui.View):
    """Interactive view for previewing and confirming bug reports."""

    def __init__(
        self,
        report: BugReport,
        github_client: GitHubClient,
        original_user_id: int,
        has_high_confidence_duplicate: bool,
    ) -> None:
        super().__init__(timeout=PREVIEW_TIMEOUT)
        self.report = report
        self.github_client = github_client
        self.original_user_id = original_user_id
        self.has_high_confidence_duplicate = has_high_confidence_duplicate
        self._confirmed_duplicate = False
        self._message: discord.Message | None = None

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        """Only allow the original user to interact with this view."""
        if interaction.user.id != self.original_user_id:
            await interaction.response.send_message(
                "Only the user who ran the command can interact with this.",
                ephemeral=True,
            )
            return False
        return True

    async def on_timeout(self) -> None:
        """Disable buttons and add expiry message when view times out."""
        for item in self.children:
            if isinstance(item, discord.ui.Button):
                item.disabled = True

        if self._message:
            try:
                embed = self._message.embeds[0] if self._message.embeds else None
                if embed:
                    embed.set_footer(
                        text="This preview has expired. Run /bug again to file a report."
                    )
                    await self._message.edit(embed=embed, view=self)
            except discord.NotFound:
                pass  # Message was deleted

    @discord.ui.button(label="File Issue", style=discord.ButtonStyle.primary, emoji=None)
    async def file_button(
        self, interaction: discord.Interaction, button: discord.ui.Button[discord.ui.View]
    ) -> None:
        """Handle file button click."""
        # If high-confidence duplicate and not yet confirmed, require second click
        if self.has_high_confidence_duplicate and not self._confirmed_duplicate:
            self._confirmed_duplicate = True
            button.label = "Confirm File"
            button.style = discord.ButtonStyle.danger
            await interaction.response.edit_message(view=self)
            return

        # Disable all buttons
        for item in self.children:
            if isinstance(item, discord.ui.Button):
                item.disabled = True

        await interaction.response.edit_message(view=self)

        try:
            # Create the GitHub issue
            url, number = self.github_client.create_issue(self.report)

            # Create success embed
            success_embed = discord.Embed(
                title="Issue Filed Successfully",
                description=f"**Issue #{number}** has been created.",
                color=discord.Color.green(),
                url=url,
            )
            success_embed.add_field(name="Title", value=self.report.title, inline=False)
            success_embed.add_field(name="Link", value=url, inline=False)

            await interaction.followup.send(embed=success_embed)
            logger.info(f"Issue #{number} created by user {self.original_user_id}")

        except Exception as e:
            logger.error(f"Failed to create issue: {e}")
            error_embed = discord.Embed(
                title="Error Creating Issue",
                description=f"Failed to create GitHub issue: {e}",
                color=discord.Color.red(),
            )
            await interaction.followup.send(embed=error_embed)

        self.stop()

    @discord.ui.button(label="Cancel", style=discord.ButtonStyle.secondary)
    async def cancel_button(
        self, interaction: discord.Interaction, button: discord.ui.Button[discord.ui.View]
    ) -> None:
        """Handle cancel button click."""
        # Disable all buttons
        for item in self.children:
            if isinstance(item, discord.ui.Button):
                item.disabled = True

        cancel_embed = discord.Embed(
            title="Bug Report Cancelled",
            description="The bug report has been cancelled and will not be filed.",
            color=discord.Color.greyple(),
        )

        await interaction.response.edit_message(embed=cancel_embed, view=self)
        self.stop()


class BugReporter(commands.Cog):
    """Cog for extracting and filing bug reports from Discord conversations."""

    def __init__(self, bot: "MudletBugBot") -> None:
        self.bot = bot
        self.config = bot.config

        # Initialize services
        self.llm_service = LLMService(
            provider=self.config.llm_provider,
            openai_api_key=self.config.openai_api_key or None,
            anthropic_api_key=self.config.anthropic_api_key or None,
        )

        self.github_client = GitHubClient(
            token=self.config.github_token or None,
            repo=self.config.github_repo,
            app_id=self.config.github_app_id or None,
            private_key_path=self.config.github_private_key_path or None,
            installation_id=self.config.github_installation_id or None,
        )

        self.duplicate_detector = DuplicateDetector(self.github_client)

    def _check_roles(self, member: discord.Member) -> bool:
        """
        Check if a member has permission to use the /bug command.

        Args:
            member: The Discord member to check

        Returns:
            True if allowed (has any allowed role, or if allowed_roles is empty)
        """
        # If no roles configured, allow everyone
        if not self.config.allowed_roles:
            return True

        # Check if user has any of the allowed roles
        user_role_names = {role.name for role in member.roles}
        return bool(user_role_names & set(self.config.allowed_roles))

    def _create_discord_link(
        self, guild_id: int, channel_id: int, message_id: int
    ) -> str:
        """Create a Discord message link."""
        return f"https://discord.com/channels/{guild_id}/{channel_id}/{message_id}"

    def _format_messages_for_llm(
        self, messages: list[discord.Message]
    ) -> list[dict[str, str]]:
        """Format Discord messages for LLM extraction."""
        return [
            {"author": msg.author.display_name, "content": msg.content}
            for msg in messages
            if msg.content  # Skip empty messages
        ]

    def _create_preview_embed(
        self,
        report: BugReport,
        duplicates: list[DuplicateResult],
    ) -> discord.Embed:
        """Create the preview embed showing the extracted bug report."""
        embed = discord.Embed(
            title="Bug Report Preview",
            description="Review the extracted bug report before filing.",
            color=discord.Color.blue(),
        )

        embed.add_field(name="Summary", value=report.summary or "N/A", inline=False)

        steps_text = (
            "\n".join(f"{i}. {step}" for i, step in enumerate(report.steps, 1))
            if report.steps
            else "N/A"
        )
        # Truncate if too long for Discord embed field
        if len(steps_text) > 1024:
            steps_text = steps_text[:1021] + "..."
        embed.add_field(name="Steps to Reproduce", value=steps_text, inline=False)

        error_text = report.error_output.strip() if report.error_output.strip() else "N/A"
        if len(error_text) > 1024:
            error_text = error_text[:1021] + "..."
        embed.add_field(name="Error Output", value=error_text, inline=False)

        extra_text = report.extra_info.strip() if report.extra_info.strip() else "N/A"
        if len(extra_text) > 1024:
            extra_text = extra_text[:1021] + "..."
        embed.add_field(name="Extra Info", value=extra_text, inline=False)

        if report.labels:
            embed.add_field(
                name="Labels",
                value=", ".join(f"`{label}`" for label in report.labels),
                inline=False,
            )

        # Show duplicates if any
        if duplicates:
            dup_lines = []
            for dup in duplicates[:3]:  # Show max 3
                confidence_emoji = {
                    "high": "[HIGH]",
                    "medium": "[MEDIUM]",
                    "low": "[LOW]",
                }
                emoji = confidence_emoji.get(dup["confidence"], "")
                dup_lines.append(
                    f"{emoji} [#{dup['number']}]({dup['url']}) - {dup['title'][:50]}"
                )

            embed.add_field(
                name="Potential Duplicates",
                value="\n".join(dup_lines),
                inline=False,
            )

            # Add warning for high-confidence duplicates
            if any(d["confidence"] == "high" for d in duplicates):
                embed.set_footer(
                    text="A high-confidence duplicate was found. You'll need to confirm to file."
                )

        return embed

    async def _parse_message_link(self, message_link: str) -> tuple[int, int, int] | None:
        """
        Parse a Discord message link to extract guild_id, channel_id, message_id.

        Returns:
            Tuple of (guild_id, channel_id, message_id) or None if invalid
        """
        # Discord message link format: https://discord.com/channels/{guild}/{channel}/{message}
        pattern = r"https://(?:ptb\.|canary\.)?discord(?:app)?\.com/channels/(\d+)/(\d+)/(\d+)"
        match = re.match(pattern, message_link)
        if match:
            return int(match.group(1)), int(match.group(2)), int(match.group(3))
        return None

    @app_commands.command(name="ping", description="Test if the bot is responding")
    async def ping_command(self, interaction: discord.Interaction) -> None:
        """Simple test command to verify slash commands work."""
        logger.info(f"Ping command received from {interaction.user.id}")
        await interaction.response.send_message("Pong! Bot is working.", ephemeral=True)

    @app_commands.command(name="bug", description="Extract a bug report from recent messages")
    @app_commands.describe(
        message_count="Number of messages to analyze (default: 20, max: 100)",
        message_link="Link to a specific message to start from",
    )
    async def bug_command(
        self,
        interaction: discord.Interaction,
        message_count: int = 20,
        message_link: str | None = None,
    ) -> None:
        """Extract a bug report from recent channel messages."""
        logger.info(f"Bug command received from {interaction.user.id}")

        # Validate message_count
        message_count = max(1, min(100, message_count))

        # Check permissions
        if isinstance(interaction.user, discord.Member):
            if not self._check_roles(interaction.user):
                await interaction.response.send_message(
                    "You don't have permission to use this command.",
                    ephemeral=True,
                )
                return

        # Defer with thinking indicator for long operation
        await interaction.response.defer(thinking=True)

        try:
            channel = interaction.channel
            if not isinstance(channel, discord.TextChannel):
                await interaction.followup.send(
                    "This command can only be used in text channels.",
                    ephemeral=True,
                )
                return

            # Fetch messages
            messages: list[discord.Message] = []

            if message_link:
                parsed = await self._parse_message_link(message_link)
                if not parsed:
                    await interaction.followup.send(
                        "Invalid message link format.",
                        ephemeral=True,
                    )
                    return

                guild_id, channel_id, message_id = parsed

                # Verify the link is for this guild
                if interaction.guild and guild_id != interaction.guild.id:
                    await interaction.followup.send(
                        "The message link must be from this server.",
                        ephemeral=True,
                    )
                    return

                # Fetch messages starting from the linked message
                try:
                    start_message = await channel.fetch_message(message_id)
                    messages = [start_message]
                    async for msg in channel.history(
                        limit=message_count - 1, after=start_message
                    ):
                        messages.append(msg)
                    # Sort by timestamp (oldest first)
                    messages.sort(key=lambda m: m.created_at)
                except discord.NotFound:
                    await interaction.followup.send(
                        "Could not find the linked message.",
                        ephemeral=True,
                    )
                    return
            else:
                # Fetch recent messages
                async for msg in channel.history(limit=message_count):
                    messages.append(msg)
                # Sort by timestamp (oldest first)
                messages.sort(key=lambda m: m.created_at)

            if not messages:
                await interaction.followup.send(
                    "No messages found to analyze.",
                    ephemeral=True,
                )
                return

            # Format messages for LLM
            formatted_messages = self._format_messages_for_llm(messages)

            if not formatted_messages:
                await interaction.followup.send(
                    "No text content found in messages to analyze.",
                    ephemeral=True,
                )
                return

            # Extract bug report using LLM
            logger.info(
                f"Extracting bug report from {len(formatted_messages)} messages "
                f"in channel {channel.id}"
            )
            llm_output = await self.llm_service.extract(formatted_messages)

            # Detect labels from combined text
            combined_text = " ".join(msg["content"] for msg in formatted_messages)
            detected_labels = detect_labels(combined_text)

            # Validate labels against repository
            valid_repo_labels = self.github_client.get_valid_labels()
            validated_labels = validate_labels(detected_labels, valid_repo_labels)

            # Create discord link to first message
            first_message = messages[0]
            discord_link = self._create_discord_link(
                guild_id=interaction.guild.id if interaction.guild else 0,
                channel_id=channel.id,
                message_id=first_message.id,
            )

            # Create BugReport
            report = BugReport.from_llm_output(
                llm_output=llm_output,
                source_channel_id=str(channel.id),
                source_user_id=str(interaction.user.id),
                discord_link=discord_link,
                labels=validated_labels,
            )

            # Check for duplicates if enabled
            duplicates: list[DuplicateResult] = []
            has_high_confidence = False

            if self.config.enable_duplicate_detection:
                duplicates = self.duplicate_detector.find_duplicates(
                    title=report.summary,
                    steps=report.steps,
                )
                has_high_confidence = any(d["confidence"] == "high" for d in duplicates)

            # Create preview embed
            preview_embed = self._create_preview_embed(report, duplicates)

            # Create view
            view = PreviewView(
                report=report,
                github_client=self.github_client,
                original_user_id=interaction.user.id,
                has_high_confidence_duplicate=has_high_confidence,
            )

            # Send preview
            view._message = await interaction.followup.send(
                embed=preview_embed, view=view, wait=True
            )

            logger.info(
                f"Bug report preview sent to user {interaction.user.id} "
                f"in channel {channel.id}"
            )

        except Exception as e:
            logger.error(f"Error in /bug command: {e}", exc_info=True)
            await interaction.followup.send(
                f"An error occurred while extracting the bug report: {e}",
                ephemeral=True,
            )


async def setup(bot: "MudletBugBot") -> None:
    """Set up the bug reporter cog."""
    await bot.add_cog(BugReporter(bot))
