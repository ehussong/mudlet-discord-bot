# Mudlet Discord Bug Bot

A Discord bot that extracts bug reports from conversations and files them as GitHub issues on the Mudlet repository. Created to address [Mudlet issue #8159](https://github.com/Mudlet/Mudlet/issues/8159).

## Features

- **Slash Command Interface**: Use `/bug` to extract bug reports from channel messages
- **LLM-Powered Extraction**: Uses OpenAI or Anthropic to intelligently parse conversations into structured bug reports
- **Automatic Label Detection**: Detects OS, components, severity, and issue type from message content
- **Duplicate Detection**: Searches existing GitHub issues to prevent duplicate filings
- **Preview & Confirmation**: Shows users a preview before filing, with confirmation for potential duplicates
- **GitHub Integration**: Creates issues matching Mudlet's bug report template format
- **Role-Based Access**: Optionally restrict command usage to specific Discord roles
- **Health Endpoint**: Built-in HTTP endpoint for monitoring

## Architecture

```
┌─────────────────────────────────────────────────────────────────────────┐
│                           Discord Server                                │
│                                                                         │
│   User runs /bug command                                                │
│         │                                                               │
│         ▼                                                               │
│   ┌─────────────┐                                                       │
│   │ Bug Reporter│ ◄─── Fetches recent messages from channel             │
│   │    Cog      │                                                       │
│   └─────┬───────┘                                                       │
└─────────┼───────────────────────────────────────────────────────────────┘
          │
          ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                          Bot Services                                   │
│                                                                         │
│  ┌─────────────┐    ┌─────────────┐    ┌──────────────┐                 │
│  │ LLM Service │    │   Labels    │    │  Duplicates  │                 │
│  │             │    │  Detector   │    │   Detector   │                 │
│  │ OpenAI /    │    │             │    │              │                 │
│  │ Anthropic   │    │ Regex-based │    │ GitHub Search│                 │
│  └─────┬───────┘    └─────┬───────┘    └──────┬───────┘                 │
│        │                  │                   │                         │
│        └──────────────────┼───────────────────┘                         │
│                           │                                             │
│                           ▼                                             │
│                    ┌─────────────┐                                      │
│                    │  BugReport  │                                      │
│                    │   Model     │                                      │
│                    └─────┬───────┘                                      │
│                          │                                              │
│                          ▼                                              │
│                   ┌──────────────┐                                      │
│                   │GitHub Client │ ────► Creates Issue on Mudlet/Mudlet │
│                   │              │                                      │
│                   └──────────────┘                                      │
└─────────────────────────────────────────────────────────────────────────┘
```

### Project Structure

```
mudlet-discord-bot/
├── bot/
│   ├── main.py              # Entry point, bot lifecycle, health server
│   ├── config.py            # Environment configuration
│   ├── cogs/
│   │   └── bug_reporter.py  # /bug slash command implementation
│   ├── services/
│   │   ├── llm.py           # OpenAI/Anthropic extraction with failover
│   │   ├── github_client.py # GitHub API integration
│   │   ├── labels.py        # Regex-based label detection
│   │   └── duplicates.py    # Duplicate issue detection
│   └── models/
│       └── bug_report.py    # BugReport dataclass
├── config/
│   └── prompts.py           # LLM prompts for extraction
├── tests/                   # Test suite
├── Dockerfile               # Container build
├── docker-compose.yml       # Container orchestration
└── requirements.txt         # Python dependencies
```

## Setup

### Prerequisites

- Python 3.11+
- Discord Bot Token
- OpenAI or Anthropic API key
- GitHub Personal Access Token (with repo scope) or GitHub App credentials

### Discord Bot Setup

1. Go to [Discord Developer Portal](https://discord.com/developers/applications)
2. Create a new application
3. Go to **Bot** → Create bot and copy the token
4. Enable these **Privileged Gateway Intents**:
   - Message Content Intent
5. Go to **OAuth2** → **URL Generator**:
   - Scopes: `bot`, `applications.commands`
   - Bot Permissions: `Send Messages`, `Read Message History`
6. Use the generated URL to invite the bot to your server

### Installation

```bash
# Clone the repository
git clone https://github.com/Mudlet/mudlet-discord-bot.git
cd mudlet-discord-bot

# Create virtual environment
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

### Configuration

Copy `.env.example` to `.env` and configure:

```bash
cp .env.example .env
```

Edit `.env` with your credentials:

```bash
# Required
DISCORD_BOT_TOKEN=your_discord_bot_token
GITHUB_TOKEN=ghp_your_github_token
OPENAI_API_KEY=sk-your_openai_key

# Optional
GITHUB_REPO=Mudlet/Mudlet           # Target repository
LLM_PROVIDER=openai                  # or "anthropic"
ANTHROPIC_API_KEY=                   # Fallback LLM provider
BUG_COMMAND_ROLES=                   # Comma-separated role names (empty = all)
DISCORD_TEST_GUILD_ID=               # For faster command sync during dev
```

**Important:** Do not use inline comments in `.env` values. Place comments on separate lines.

### Running the Bot

```bash
# Development
python -m bot.main

# Production (Docker)
docker compose up -d
```

## Usage

### Commands

| Command | Description |
|---------|-------------|
| `/bug` | Extract a bug report from recent channel messages |
| `/bug message_count:50` | Analyze the last 50 messages (default: 20, max: 100) |
| `/bug message_link:<url>` | Start analysis from a specific message |
| `/ping` | Test if the bot is responding |

### Workflow

1. A user describes a bug in a Discord channel
2. A developer runs `/bug` in that channel
3. The bot fetches recent messages and uses an LLM to extract:
   - Summary/title
   - Steps to reproduce
   - Error output
   - Extra info (OS, Mudlet version, etc.)
4. Labels are auto-detected from the conversation
5. Potential duplicate issues are searched
6. A preview embed is shown with **File Issue** and **Cancel** buttons
7. If high-confidence duplicates exist, the user must confirm before filing
8. On confirmation, a GitHub issue is created matching Mudlet's template

### GitHub Issue Format

Created issues follow Mudlet's bug report template:

```markdown
#### Brief summary of issue:
[Extracted summary]

#### Steps to reproduce the issue:
1. [Step 1]
2. [Step 2]

#### Error output
[Any error messages or stack traces]

#### Extra information, such as the Mudlet version, operating system and ideas for how to solve:
[OS, version, and other context]

---
*Auto-generated from Discord by mudlet-bug-bot • [Original conversation](link)*
```

## Development

### Install Development Dependencies

```bash
pip install -r requirements-dev.txt
```

### Running Tests

```bash
# Run all tests
pytest tests/ -v

# Run with coverage
pytest tests/ --cov=bot --cov-report=term-missing

# Run specific test file
pytest tests/test_labels.py -v
```

### Code Quality

```bash
# Type checking
mypy bot/

# Linting
ruff check bot/ tests/

# Auto-fix lint issues
ruff check --fix bot/ tests/
```

### Label Detection

Labels are auto-detected using regex patterns in `bot/services/labels.py`:

| Pattern | Label |
|---------|-------|
| windows, win10, win11 | OS:Windows |
| macos, mac os, osx | OS:macOS |
| linux, ubuntu, debian | OS:GNU/Linux |
| map, mapper, room | mapper bug |
| lua, script, trigger | Lua only |
| crash, segfault, freeze | high |
| regression, used to work | regression |
| feature request, wish | wishlist |

Labels are validated against the target repository's actual labels before being applied.

## Deployment

### Docker

```bash
# Build and run
docker compose up -d

# View logs
docker compose logs -f

# Stop
docker compose down
```

### Health Check

The bot exposes a health endpoint at `http://localhost:8080/health`:

```json
{
  "status": "healthy",
  "latency_ms": 45.23
}
```

### Environment Variables Reference

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `DISCORD_BOT_TOKEN` | Yes | - | Discord bot token |
| `OPENAI_API_KEY` | Yes* | - | OpenAI API key |
| `ANTHROPIC_API_KEY` | Yes* | - | Anthropic API key |
| `GITHUB_TOKEN` | Yes** | - | GitHub PAT with repo scope |
| `GITHUB_APP_ID` | Yes** | - | GitHub App ID |
| `GITHUB_PRIVATE_KEY_PATH` | No | - | Path to GitHub App private key |
| `GITHUB_INSTALLATION_ID` | No | - | GitHub App installation ID |
| `GITHUB_REPO` | No | Mudlet/Mudlet | Target repository |
| `LLM_PROVIDER` | No | openai | Primary LLM provider |
| `BUG_COMMAND_ROLES` | No | (all) | Comma-separated role names |
| `ENABLE_DUPLICATE_DETECTION` | No | true | Enable duplicate checking |
| `ENABLE_IMAGE_ANALYSIS` | No | true | Enable image analysis |
| `DISCORD_TEST_GUILD_ID` | No | - | Guild ID for dev command sync |
| `HEALTH_PORT` | No | 8080 | Health check server port |
| `LOG_LEVEL` | No | INFO | Logging level |

\* At least one LLM provider is required
\** Either GitHub token or App credentials required

## License

GPL-2.0 - Same as [Mudlet](https://github.com/Mudlet/Mudlet)

## Contributing

1. Fork the repository
2. Create a feature branch
3. Run tests: `pytest tests/ -v`
4. Run linting: `ruff check bot/ tests/`
5. Submit a pull request

## Support

- [Mudlet Discord](https://discord.gg/mudlet) - General Mudlet community
- [GitHub Issues](https://github.com/Mudlet/mudlet-discord-bot/issues) - Bug reports for this bot
