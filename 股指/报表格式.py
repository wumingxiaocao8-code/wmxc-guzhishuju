"""标准库报表格式；不导入 SDK、数据或业务入口。"""
import html
import math

def num(x):
    """CSV 里的数：空的、写不成数的都当没有。"""
    try:
        v = float(x)
        return None if math.isnan(v) else v
    except (TypeError, ValueError):
        return None

def fmt(x, nd=2, plus=False) -> str:
    v = num(x)
    if v is None:
        return ""
    s = f"{v:+.{nd}f}" if plus else f"{v:.{nd}f}"
    return s.rstrip("0").rstrip(".") if "." in s else s

def esc(x) -> str:
    return html.escape("" if x is None or (isinstance(x, float) and math.isnan(x)) else str(x))

def table(head: list, rows: list) -> str:
    h = "".join(f"<th>{esc(x)}</th>" for x in head)
    b = "".join("<tr>" + "".join(f"<td>{c if isinstance(c, Raw) else esc(c)}</td>" for c in r) + "</tr>" for r in rows)
    return f'<div class="wrap"><table><thead><tr>{h}</tr></thead><tbody>{b}</tbody></table></div>'

class Raw(str):
    """已经是 HTML 的格子，不再转义。"""

def page(title: str, body: str) -> str:
    return (f'<!doctype html><html lang="zh-CN"><head><meta charset="utf-8">'
            f'<meta name="viewport" content="width=device-width,initial-scale=1"><title>{esc(title)}</title>'
            f"<style>{CSS}</style></head><body><main>{body}</main></body></html>")

CSS = """
:root{--bg:#f7f6f2;--fg:#1d2433;--muted:#667085;--line:#e3e0d8;--card:#fff;--accent:#1f4e79;--warn:#b54708;--warnbg:#fff4e5;--up:#c0392b;--down:#1e7d4f}
@media (prefers-color-scheme:dark){:root:not([data-theme="light"]){--bg:#14171c;--fg:#e6e8eb;--muted:#9aa3ae;--line:#2c313a;--card:#1b1f26;--accent:#7fb3e6;--warn:#f5a623;--warnbg:#2b2214;--up:#ff6b5e;--down:#4cc38a}}
:root[data-theme="dark"]{--bg:#14171c;--fg:#e6e8eb;--muted:#9aa3ae;--line:#2c313a;--card:#1b1f26;--accent:#7fb3e6;--warn:#f5a623;--warnbg:#2b2214;--up:#ff6b5e;--down:#4cc38a}
body{margin:0;background:var(--bg);color:var(--fg);font:15px/1.65 "Segoe UI","Microsoft YaHei",sans-serif}
main{max-width:1180px;margin:0 auto;padding:20px 16px 60px}
h1{font-size:22px;margin:0 0 4px}h2{font-size:18px;margin:30px 0 8px;padding-left:8px;border-left:4px solid var(--accent)}
h3{font-size:16px;margin:4px 0 6px}h4{font-size:14px;margin:12px 0 2px;color:var(--muted)}
ul.list{margin:2px 0 6px;padding-left:20px;font-size:14px}ul.list li{margin:2px 0}
.meta,.note{color:var(--muted);font-size:13px}.note{margin:4px 0}
.card{background:var(--card);border:1px solid var(--line);border-radius:8px;padding:12px 14px;margin:12px 0}
.warn{background:var(--warnbg);border-left:4px solid var(--warn);padding:6px 12px;border-radius:4px;margin:8px 0}
.wrap{overflow-x:auto}table{border-collapse:collapse;width:100%;font-size:14px;margin:6px 0}
th,td{border-bottom:1px solid var(--line);padding:5px 8px;text-align:right;white-space:nowrap}
th{color:var(--muted);font-weight:600}td:first-child,th:first-child{text-align:left}
.big{font-size:19px;font-weight:700}.up{color:var(--up)}.down{color:var(--down)}
a{color:var(--accent)}
"""
