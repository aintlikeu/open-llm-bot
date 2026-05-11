import re

_ESCAPE_CHARS = r"\_*[]()~`>#+=|{}.!-"
_ESCAPE_RE = re.compile(f"([{re.escape(_ESCAPE_CHARS)}])")


def escape_markdown_v2(text: str) -> str:
    return _ESCAPE_RE.sub(r"\\\1", text)


def format_llm_response(text: str) -> str:
    """Convert standard markdown from LLM output to Telegram MarkdownV2."""
    parts = re.split(r"(```[\s\S]*?```|`[^`\n]+`)", text)
    result: list[str] = []
    for part in parts:
        if part.startswith("```") and part.endswith("```"):
            inner = part[3:-3]
            inner = inner.replace("\\", "\\\\").replace("`", "\\`")
            result.append(f"```{inner}```")
        elif part.startswith("`") and part.endswith("`") and len(part) > 1:
            inner = part[1:-1].replace("\\", "\\\\").replace("`", "\\`")
            result.append(f"`{inner}`")
        else:
            result.append(escape_markdown_v2(part))
    return "".join(result)


def unescape_markdown_v2(text: str) -> str:
    return re.sub(r"\\(.)", r"\1", text)


def split_message(text: str, max_length: int = 4096) -> list[str]:
    if len(text) <= max_length:
        return [text]
    parts: list[str] = []
    while text:
        if len(text) <= max_length:
            parts.append(text)
            break
        split_at = text.rfind("\n", 0, max_length)
        if split_at <= 0:
            split_at = text.rfind(" ", 0, max_length)
        if split_at <= 0:
            split_at = max_length
        parts.append(text[:split_at])
        text = text[split_at:].lstrip("\n")
    return parts
