# Open LLM Bot

Telegram bot powered by DeepSeek LLM, built with aiogram v3 and SQLAlchemy 2.0.

## Quick Start

1. Copy `.env.example` to `.env` and fill in your values:

```bash
cp .env.example .env
```

Required variables:
- `BOT_TOKEN` — Telegram bot token from [@BotFather](https://t.me/BotFather)
- `ADMIN_IDS` — Comma-separated Telegram user IDs for admin access
- `DEEPSEEK_API_KEY` — API key from [DeepSeek](https://platform.deepseek.com/)

2. Start with Docker Compose:

```bash
docker compose up --build -d
```

3. Check status:

```bash
docker compose ps
docker compose logs -f
```

4. Stop:

```bash
docker compose down
```

## Features

- **Multi-model support** — Switch between DeepSeek Chat and Reasoner models
- **Sliding window memory** — Conversation history stored in SQLite (configurable window size)
- **Admin panel** — Inline menus to manage users, toggle models, and view usage statistics
- **Access control** — Middleware-based allowlist with admin override
- **Cost tracking** — Per-request token and cost logging
- **Safe formatting** — MarkdownV2 escaping with automatic plaintext fallback
- **Message splitting** — Handles responses over 4096 characters

## Commands

### User
- `/start` — Register and see welcome message
- `/cabinet` — Select model and manage settings
- `/new` — Clear chat history and start fresh
- `/help` — Show available commands

### Admin
- `/admin` — Open admin panel with inline menus

## Local Development

```bash
pip install -r requirements.txt
python -m bot.main
```

### Database Migrations

```bash
alembic upgrade head
alembic revision --autogenerate -m "description"
```

## Architecture

```
bot/
  handlers/      — Telegram UI logic (commands, callbacks)
  middlewares/    — Access control (admin + allowlist)
  providers/     — LLM API implementations (BaseProvider pattern)
  database/      — SQLAlchemy models, sessions, CRUD
  utils/         — Formatting, logging helpers
```
