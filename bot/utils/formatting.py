import re


# ── HTML escaping ─────────────────────────────────────────────────────────────

def escape_html(text: str) -> str:
    """Escape characters that have special meaning in HTML."""
    return (
        text
        .replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
    )


# ── Markdown → HTML converter ─────────────────────────────────────────────────

def format_llm_response(text: str) -> str:
    """Convert standard markdown from LLM output to Telegram HTML.

    Supported:
      ```lang\n...\n```  → <pre><code>...</code></pre>
      `inline code`      → <code>...</code>
      **bold**           → <b>...</b>
      __bold__           → <b>...</b>
      *italic*           → <i>...</i>
      _italic_           → <i>...</i>
      ### heading        → <b>heading</b>
      - item / * item    → • item  (plain bullet, Telegram has no list tag)
    """
    result: list[str] = []
    i = 0
    length = len(text)

    while i < length:
        # ── fenced code block ```...``` ───────────────────────────────────────
        if text[i:i+3] == "```":
            end = text.find("```", i + 3)
            if end == -1:
                result.append(escape_html(text[i:]))
                break
            block = text[i + 3 : end]
            # strip optional language tag on first line
            first_nl = block.find("\n")
            if first_nl != -1 and not block[:first_nl].strip().startswith(" "):
                block = block[first_nl + 1 :]
            result.append(f"<pre><code>{escape_html(block.strip())}</code></pre>")
            i = end + 3
            continue

        # ── inline code `...` ─────────────────────────────────────────────────
        if text[i] == "`":
            end = text.find("`", i + 1)
            if end == -1:
                result.append(escape_html(text[i:]))
                break
            result.append(f"<code>{escape_html(text[i + 1 : end])}</code>")
            i = end + 1
            continue

        # ── process line by line for headings, bullets, bold/italic ──────────
        nl = text.find("\n", i)
        if nl == -1:
            nl = length
        line = text[i : nl]
        i = nl + 1 if nl < length else length

        line = _format_line(line)
        result.append(line)
        if nl < length:
            result.append("\n")

    return "".join(result)


def _format_line(line: str) -> str:
    """Apply inline markdown formatting to a single line of plain text."""
    # Headings: ### text  →  <b>text</b>
    heading = re.match(r"^(#{1,6})\s+(.*)", line)
    if heading:
        content = _inline_formats(heading.group(2))
        return f"<b>{content}</b>"

    # Unordered list: - item  or  * item  →  • item
    bullet = re.match(r"^[\-\*]\s+(.*)", line)
    if bullet:
        content = _inline_formats(bullet.group(1))
        return f"• {content}"

    # Numbered list: 1. item  →  1. item  (keep number, format content)
    numbered = re.match(r"^(\d+\.\s+)(.*)", line)
    if numbered:
        content = _inline_formats(numbered.group(2))
        return f"{numbered.group(1)}{content}"

    return _inline_formats(line)


def _inline_formats(text: str) -> str:
    """Apply bold/italic inline markdown, escaping HTML entities."""
    # We process the string token by token to avoid double-escaping.
    # Order matters: check ** before *, __ before _.
    tokens = re.split(r"(\*\*|__|\*|_)", text)
    result: list[str] = []
    bold_open = False
    italic_open = False

    for token in tokens:
        if token == "**" or token == "__":
            if bold_open:
                result.append("</b>")
                bold_open = False
            else:
                result.append("<b>")
                bold_open = True
        elif token == "*" or token == "_":
            if italic_open:
                result.append("</i>")
                italic_open = False
            else:
                result.append("<i>")
                italic_open = True
        else:
            result.append(escape_html(token))

    # Close any unclosed tags (malformed markdown)
    if bold_open:
        result.append("</b>")
    if italic_open:
        result.append("</i>")

    return "".join(result)


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
