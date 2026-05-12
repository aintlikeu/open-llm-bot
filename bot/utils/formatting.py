import re


# ── HTML escaping ─────────────────────────────────────────────────────────────

def escape_html(text: str) -> str:
    """Escape characters that have special meaning in Telegram HTML."""
    return text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


# ── Markdown → HTML converter ─────────────────────────────────────────────────

# Inline patterns applied in order (bold before italic to handle ** vs *)
_INLINE_PATTERNS: list[tuple[re.Pattern[str], str]] = [
    (re.compile(r"\*\*(.+?)\*\*", re.DOTALL), r"<b>\1</b>"),
    (re.compile(r"__(.+?)__", re.DOTALL),     r"<b>\1</b>"),
    (re.compile(r"\*(.+?)\*",   re.DOTALL),   r"<i>\1</i>"),
    (re.compile(r"_([^_\n]+?)_"),              r"<i>\1</i>"),
]


def _apply_inline(text: str) -> str:
    """Escape HTML, then apply bold/italic substitutions."""
    text = escape_html(text)
    for pattern, replacement in _INLINE_PATTERNS:
        text = pattern.sub(replacement, text)
    return text


def format_llm_response(text: str) -> str:
    """Convert standard markdown from LLM output to Telegram HTML.

    Supported constructs:
      ```lang\n...\n```  → <pre><code>...</code></pre>
      `inline`           → <code>...</code>
      **bold**           → <b>...</b>
      __bold__           → <b>...</b>
      *italic*           → <i>...</i>
      _italic_           → <i>...</i>
      ### heading        → <b>heading</b>
      - item / * item    → • item
      1. item            → 1. item
    """
    result: list[str] = []

    # Split on fenced code blocks first so we never mangle code content
    segments = re.split(r"(```[\s\S]*?```)", text)

    for segment in segments:
        if segment.startswith("```") and segment.endswith("```"):
            block = segment[3:-3]
            # Strip optional language tag on the first line
            first_nl = block.find("\n")
            if first_nl != -1 and block[:first_nl].strip().isidentifier():
                block = block[first_nl + 1:]
            result.append(f"<pre><code>{escape_html(block.strip())}</code></pre>")
            continue

        # Process remaining text line by line
        lines = segment.split("\n")
        formatted_lines: list[str] = []
        for line in lines:
            # Split out inline code spans first, then format the rest
            parts = re.split(r"`([^`\n]+)`", line)
            rebuilt = ""
            for idx, part in enumerate(parts):
                if idx % 2 == 1:
                    # odd parts are the captured inline-code content
                    rebuilt += f"<code>{escape_html(part)}</code>"
                else:
                    rebuilt += _format_plain_line(part)
            formatted_lines.append(rebuilt)

        result.append("\n".join(formatted_lines))

    return "".join(result)


def _format_plain_line(line: str) -> str:
    """Apply heading / bullet / inline markdown to a plain-text line segment."""
    # Heading: ### text
    m = re.match(r"^(#{1,6})\s+(.*)", line)
    if m:
        return f"<b>{_apply_inline(m.group(2))}</b>"

    # Unordered bullet: - item  or  * item
    m = re.match(r"^[\-\*]\s+(.*)", line)
    if m:
        return f"• {_apply_inline(m.group(1))}"

    # Numbered list: 1. item
    m = re.match(r"^(\d+\.\s+)(.*)", line)
    if m:
        return f"{m.group(1)}{_apply_inline(m.group(2))}"

    return _apply_inline(line)


# ── Message splitting ─────────────────────────────────────────────────────────

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
