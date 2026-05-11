# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

A lightweight Telegram bot using aiogram v3 that interfaces with LLM providers (starting with DeepSeek). Focus on modularity, asynchronous operations, and zero external dependencies (no Redis).

## Build & Run Commands

- **Run (Docker V2):** `docker compose up --build -d`
- **Stop:** `docker compose down`
- **Logs:** `docker compose logs -f`
- **Check Status:** `docker compose ps`
- **Install dependencies (local):** `pip install -r requirements.txt`
- **Run bot (local):** `python -m bot.main`
- **Database migrations (Alembic):** `alembic upgrade head`
- **Linting:** `ruff check .`
- **Type checking:** `mypy .`

## Code Style & Architecture Rules

- **Framework:** Always use aiogram v3 features (Routers, Middlewares, Magic Filters).
- **LLM pattern:** Use a Provider pattern (`BaseProvider` abstract class) to ensure scalability for future platforms.
- **Database:** Use SQLAlchemy 2.0 with aiosqlite for asynchronous SQLite operations.
- **State management:** Use `MemoryStorage` for FSM to keep the project lightweight.
- **Concurrency:** All I/O operations (API calls, DB queries) must be `await`-ed. Use `httpx` for LLM API requests.
- **Type hinting:** Use strict Python type hints for all function signatures and class attributes.
- **Error handling:** Wrap API calls in try-except blocks with user-friendly Telegram notifications.
- **Message formatting:** Use MarkdownV2. Always use a utility function to escape special characters to prevent Telegram API errors.
- **Long messages:** Implement a utility to split bot responses exceeding 4096 characters.

## Project Structure

```
bot/handlers/      - UI logic and commands
bot/middlewares/   - Access control (Admin/Allowed users check)
bot/providers/     - LLM API implementations
bot/database/      - Models, session management, and CRUD operations
bot/utils/         - Formatting, logging, and helper functions
```
