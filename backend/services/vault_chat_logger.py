# /opt/locus/backend/services/vault_chat_logger.py
# Logs every Telegram bot conversation exchange as .md files in the vault.
#
# Structure:
#   /vault/03-AI-Chats/2026-05-12.md
#
# Each file is a daily chat log with exact timestamps (IST) per message.
# Format:
#   ---
#   tags: [locus-chat, ai-conversation]
#   date: 2026-05-12
#   locus_managed: true
#   ---
#   # Chat Log — 2026-05-12
#
#   ## 09:34:12
#   **Shivam:** How am I doing this week?
#
#   **Locus:** Based on your check-ins...
#
#   ---
#
#   ## 14:22:05
#   **Shivam:** Create a task for gym
#   ...

import os
import logging
from pathlib import Path
from datetime import datetime, timezone, timedelta

log = logging.getLogger("vault-chat-logger")

VAULT_PATH = os.getenv("VAULT_PATH", "/vault")
CHAT_DIR = "03-AI-Chats"
IST = timezone(timedelta(hours=5, minutes=30))


def _ensure_chat_dir() -> Path:
    """Ensure the chat log directory exists."""
    chat_path = Path(VAULT_PATH) / CHAT_DIR
    chat_path.mkdir(parents=True, exist_ok=True)
    return chat_path


def _get_daily_file(dt: datetime) -> Path:
    """Get the path for today's chat log file."""
    date_str = dt.strftime("%Y-%m-%d")
    return _ensure_chat_dir() / f"{date_str}.md"


def _init_daily_file(file_path: Path, dt: datetime) -> None:
    """Create a new daily chat log file with frontmatter."""
    date_str = dt.strftime("%Y-%m-%d")
    day_name = dt.strftime("%A")
    frontmatter = (
        f"---\n"
        f"tags: [locus-chat, ai-conversation]\n"
        f"date: {date_str}\n"
        f"day: {day_name}\n"
        f"locus_managed: true\n"
        f"---\n\n"
        f"# 🧠 Chat Log — {date_str} ({day_name})\n\n"
    )
    file_path.write_text(frontmatter, encoding="utf-8")
    log.info(f"Created new chat log: {file_path}")


def log_chat_exchange(
    user_message: str,
    bot_reply: str,
    model_used: str = "",
    intent: str = "",
) -> bool:
    """
    Append a user↔bot exchange to today's vault chat log.

    Each exchange gets an exact IST timestamp and is formatted as
    readable markdown that Obsidian renders nicely.

    Returns True if successfully written, False otherwise.
    """
    try:
        now = datetime.now(IST)
        file_path = _get_daily_file(now)

        # Create file with frontmatter if it doesn't exist
        if not file_path.exists():
            _init_daily_file(file_path, now)

        time_str = now.strftime("%H:%M:%S")
        timestamp_full = now.strftime("%Y-%m-%d %H:%M:%S IST")

        # Build the exchange block
        entry = f"\n---\n\n"
        entry += f"## {time_str}\n"
        entry += f"*{timestamp_full}*"
        if intent:
            entry += f" · `{intent}`"
        if model_used:
            entry += f" · `{model_used}`"
        entry += "\n\n"

        # User message
        entry += f"**Shivam:**\n{user_message}\n\n"

        # Bot reply (truncate extremely long replies for vault readability)
        reply_text = bot_reply[:8000] if len(bot_reply) > 8000 else bot_reply
        entry += f"**Locus:**\n{reply_text}\n\n"

        # Append to file
        with open(file_path, "a", encoding="utf-8") as f:
            f.write(entry)

        return True

    except Exception as e:
        log.error(f"Chat log write failed: {e}")
        return False


def get_todays_chat_count() -> int:
    """Return how many exchanges are logged today."""
    try:
        now = datetime.now(IST)
        file_path = _get_daily_file(now)
        if not file_path.exists():
            return 0
        content = file_path.read_text(encoding="utf-8")
        return content.count("**Shivam:**")
    except Exception:
        return 0
