from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    bot_token: str
    admin_ids: str = ""
    deepseek_api_key: str
    database_url: str = "sqlite+aiosqlite:///data/bot.db"
    chat_history_window: int = 20


settings = Settings()  # type: ignore[call-arg]

ADMIN_IDS: set[int] = (
    {int(x.strip()) for x in settings.admin_ids.split(",") if x.strip()}
    if settings.admin_ids
    else set()
)
