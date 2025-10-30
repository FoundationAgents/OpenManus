from __future__ import annotations

import re


def strip_markdown_fences(s: str) -> str:
    """If content is within ```json ... ```, extract the inner block."""
    m = re.search(r"```(?:json|JSON)?\s*(.*?)```", s, flags=re.DOTALL)
    return m.group(1) if m else s


def trim_to_outermost_json(s: str) -> str:
    """Slice from first '{' to last '}', tolerating prose outside."""
    start = s.find("{")
    end = s.rfind("}")
    return s[start : end + 1] if (start != -1 and end != -1 and end > start) else s


def normalize_unicode_quotes(s: str) -> str:
    """Normalize smart/Unicode quotes to ASCII."""
    return (
        s.replace("“", '"')
        .replace("”", '"')
        .replace("„", '"')
        .replace("«", '"')
        .replace("»", '"')
        .replace("’", "'")
        .replace("‘", "'")
    )


def remove_json_comments(s: str) -> str:
    """Remove // and /* */ outside strings safely."""
    out, i, n, in_str, esc = [], 0, len(s), False, False
    while i < n:
        ch = s[i]
        if in_str:
            if esc:
                esc = False
            elif ch == "\\":
                esc = True
            elif ch == '"':
                in_str = False
            out.append(ch)
            i += 1
            continue
        if ch == '"':
            in_str = True
            out.append(ch)
            i += 1
            continue
        if i + 1 < n and s[i : i + 2] == "//":
            i += 2
            while i < n and s[i] not in "\r\n":
                i += 1
            continue
        if i + 1 < n and s[i : i + 2] == "/*":
            i += 2
            while i + 1 < n and s[i : i + 2] != "*/":
                i += 1
            i += 2 if i + 1 < n else 0
            continue
        out.append(ch)
        i += 1
    return "".join(out)


def remove_trailing_commas(s: str) -> str:
    """Remove trailing commas before } or ] while respecting strings and **skipping whitespace**."""
    out = []
    i, n = 0, len(s)
    in_str = False
    esc = False
    while i < n:
        ch = s[i]
        if in_str:
            if esc:
                esc = False
            elif ch == "\\":
                esc = True
            elif ch == '"':
                in_str = False
            out.append(ch)
            i += 1
            continue
        if ch == '"':
            in_str = True
            out.append(ch)
            i += 1
            continue
        if ch == ",":
            # lookahead skipping whitespace
            j = i + 1
            while j < n and s[j] in " \t\r\n":
                j += 1
            if j < n and s[j] in "}]":
                # drop the comma (do not advance j; let normal loop output the closer)
                i += 1
                continue
        out.append(ch)
        i += 1
    return "".join(out)


def escape_illegal_string_chars(s: str) -> str:
    """Escape newlines/tabs only inside strings."""
    out = []
    i, n = 0, len(s)
    in_str = False
    esc = False
    while i < n:
        ch = s[i]
        if in_str:
            if ch in ("\n", "\r"):
                out.append("\\n")
                i += 1
                continue
            if ch == "\t":
                out.append("\\t")
                i += 1
                continue
            if esc:
                esc = False
            elif ch == "\\":
                esc = True
            elif ch == '"':
                in_str = False
            out.append(ch)
            i += 1
            continue
        else:
            if ch == '"':
                in_str = True
            out.append(ch)
            i += 1
            continue
    return "".join(out)


def balance_braces_brackets(s: str) -> str:
    """If exactly one closing brace/bracket is missing, append it conservatively."""
    open_curly = s.count("{")
    close_curly = s.count("}")
    if open_curly == close_curly + 1 and not s.rstrip().endswith("}"):
        return s.rstrip() + "}"
    open_sq = s.count("[")
    close_sq = s.count("]")
    if open_sq == close_sq + 1 and not s.rstrip().endswith("]"):
        return s.rstrip() + "]"
    return s


def sanity_checks(baseline: str, repaired: str) -> bool:
    """Reject repairs that remove more than 30% after safe structural passes."""
    return len(repaired) >= 0.70 * len(baseline)


def repair_json(text: str) -> tuple[str, list[str]]:
    """Apply passes in order; return (repaired_text, notes_of_passes).
    Baseline for sanity is after removing fences and outermost slice.
    """
    notes = []
    text1 = strip_markdown_fences(text)
    if text1 != text:
        notes.append("strip_markdown_fences")
        text = text1
    text1 = trim_to_outermost_json(text)
    if text1 != text:
        notes.append("trim_to_outermost_json")
        text = text1
    baseline = text

    for fn in (
        normalize_unicode_quotes,
        remove_json_comments,
        remove_trailing_commas,
        escape_illegal_string_chars,
        balance_braces_brackets,
    ):
        s1 = fn(text)
        if s1 != text:
            notes.append(fn.__name__)
        text = s1

    if not sanity_checks(baseline, text):
        raise ValueError("Unsafe repair delta")
    return text, notes
