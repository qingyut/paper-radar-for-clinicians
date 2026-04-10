from __future__ import annotations

import re

from paper_radar.utils import normalize_whitespace


class QuerySyntaxError(ValueError):
    pass


_OPERATOR_RE_TEMPLATE = r"(?<!\w){op}(?!\w)"


def _split_top_level(expr: str, operator: str) -> list[str]:
    pieces: list[str] = []
    current: list[str] = []
    depth = 0
    in_quote = False
    i = 0
    op_re = re.compile(_OPERATOR_RE_TEMPLATE.format(op=re.escape(operator)), re.IGNORECASE)

    while i < len(expr):
        ch = expr[i]
        if ch == '"':
            in_quote = not in_quote
            current.append(ch)
            i += 1
            continue
        if not in_quote:
            if ch == '(':
                depth += 1
                current.append(ch)
                i += 1
                continue
            if ch == ')':
                depth -= 1
                if depth < 0:
                    raise QuerySyntaxError("Unbalanced parentheses in query expression.")
                current.append(ch)
                i += 1
                continue
            if depth == 0:
                match = op_re.match(expr, i)
                if match:
                    prev_ok = i == 0 or expr[i - 1].isspace() or expr[i - 1] == ')'
                    next_i = match.end()
                    next_ok = next_i == len(expr) or expr[next_i].isspace() or expr[next_i] == '('
                    if prev_ok and next_ok:
                        piece = normalize_whitespace("".join(current))
                        if piece:
                            pieces.append(piece)
                        current = []
                        i = next_i
                        continue
        current.append(ch)
        i += 1

    if in_quote:
        raise QuerySyntaxError("Unbalanced double quotes in query expression.")
    if depth != 0:
        raise QuerySyntaxError("Unbalanced parentheses in query expression.")

    tail = normalize_whitespace("".join(current))
    if tail:
        pieces.append(tail)
    return pieces


def _strip_outer_parentheses(text: str) -> str:
    text = normalize_whitespace(text)
    while text.startswith("(") and text.endswith(")"):
        depth = 0
        enclosed = True
        in_quote = False
        for idx, ch in enumerate(text):
            if ch == '"':
                in_quote = not in_quote
            elif not in_quote:
                if ch == '(':
                    depth += 1
                elif ch == ')':
                    depth -= 1
                    if depth == 0 and idx != len(text) - 1:
                        enclosed = False
                        break
        if enclosed and depth == 0:
            text = normalize_whitespace(text[1:-1])
        else:
            break
    return text


def _unquote(term: str) -> str:
    term = normalize_whitespace(term)
    if len(term) >= 2 and term[0] == '"' and term[-1] == '"':
        return normalize_whitespace(term[1:-1])
    return term


def parse_keyword_groups(keyword: str) -> list[list[str]]:
    """Parse a lightweight boolean query into AND-of-OR groups.

    Supported syntax:
    - Group-level AND
    - In-group OR
    - Parentheses
    - Optional double-quoted phrases

    Examples:
        (gallbladder cancer OR gallbladder neoplasms) AND (multimodal OR "multi-modal")
        gallbladder cancer
        pathology OR histopathology
    """
    keyword = normalize_whitespace(keyword)
    if not keyword:
        raise QuerySyntaxError("Keyword/query must not be empty.")

    has_boolean = bool(re.search(r"(?<!\w)(AND|OR)(?!\w)|[()]", keyword, re.IGNORECASE))
    if not has_boolean:
        return [[_unquote(keyword)]]

    and_groups = _split_top_level(keyword, "AND")
    if not and_groups:
        raise QuerySyntaxError("Could not parse any query groups from expression.")

    parsed: list[list[str]] = []
    for group in and_groups:
        group = _strip_outer_parentheses(group)
        if not group:
            raise QuerySyntaxError("Empty group found in query expression.")
        if "(" in group or ")" in group:
            raise QuerySyntaxError(
                "Nested parentheses are not supported yet. Use a flat pattern such as "
                '(A OR B) AND (C OR D).'
            )
        terms = [_unquote(part) for part in _split_top_level(group, "OR")]
        terms = [t for t in terms if t]
        if not terms:
            raise QuerySyntaxError("A query group resolved to zero terms.")
        parsed.append(terms)

    return parsed
