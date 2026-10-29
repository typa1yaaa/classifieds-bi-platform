from __future__ import annotations

import re


def strip_comments(sql: str) -> str:
    out, i, n = [], 0, len(sql)
    in_str = False
    while i < n:
        ch = sql[i]
        if ch == "'" and not in_str:
            in_str = True
        elif ch == "'" and in_str:
            in_str = False
        if not in_str and sql.startswith("--", i):
            j = sql.find("\n", i)
            i = n if j == -1 else j
            continue
        out.append(ch)
        i += 1
    return "".join(out)


def split_statements(sql: str) -> list[str]:
    sql = strip_comments(sql)
    parts, buf, in_str = [], [], False
    for ch in sql:
        if ch == "'":
            in_str = not in_str
        if ch == ";" and not in_str:
            parts.append("".join(buf))
            buf = []
        else:
            buf.append(ch)
    parts.append("".join(buf))
    return [p.strip() for p in parts if p.strip()]


def render(sql: str, **params) -> str:
    def repl(m: re.Match) -> str:
        key = m.group(1)
        return str(params[key]) if key in params else m.group(0)
    return re.sub(r"\{(\w+)\}", repl, sql)
