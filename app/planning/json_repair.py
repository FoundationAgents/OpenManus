from __future__ import annotations

import re


def strip_markdown_fences(s: str) -> str:
    """Se vier entre ```json ... ```, extrai o conteúdo interno."""
    m = re.search(r"```(?:json|JSON)?\s*(.*?)```", s, flags=re.DOTALL)
    return m.group(1) if m else s


def trim_to_outermost_json(s: str) -> str:
    """Recorta do primeiro '{' ao último '}', tolerando prosa fora."""
    start = s.find("{")
    end = s.rfind("}")
    return s[start : end + 1] if (start != -1 and end != -1 and end > start) else s


def normalize_unicode_quotes(s: str) -> str:
    """Converte aspas unicode “smart” e semelhantes em ASCII."""
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
    """Remove // e /* */ fora de strings, de forma segura."""
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
    """Remove vírgulas finais antes de } ou ] respeitando strings."""
    out = []
    stack = []
    i, n, in_str, esc = 0, len(s), False, False
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
        if ch in "{[":
            stack.append(ch)
        if ch == "," and i + 1 < n and s[i + 1] in "}]":
            i += 1  # pula a vírgula antes de } ]
            continue
        if ch in "}]":
            if stack:
                stack.pop()
        out.append(ch)
        i += 1
    return "".join(out)


def escape_illegal_string_chars(s: str) -> str:
    """Escapa quebras e tabs **apenas dentro de strings**."""
    out = []
    i, n = 0, len(s)
    in_str = False
    esc = False
    while i < n:
        ch = s[i]
        if in_str:
            # escape de quebras/tab dentro de strings
            if ch == "\n" or ch == "\r":
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
    """Se faltar exatamente um '}' ou ']', completa conservadoramente."""
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
    """Recusa reparos que removam >5% **após** passos estruturais seguros."""
    return len(repaired) >= 0.70 * len(baseline)


def repair_json(text: str) -> tuple[str, list[str]]:
    """Aplica passes na ordem; retorna (texto_reparado, notas_de_passes).
    - Baseline de sanidade é após remoção de fences e recorte externo.
    """
    notes = []
    # 1) Passos estruturais seguros e baseline
    text1 = strip_markdown_fences(text)
    if text1 != text:
        notes.append("strip_markdown_fences")
        text = text1
    text1 = trim_to_outermost_json(text)
    if text1 != text:
        notes.append("trim_to_outermost_json")
        text = text1
    baseline = text

    # 2) Passos de normalização/limpeza
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
