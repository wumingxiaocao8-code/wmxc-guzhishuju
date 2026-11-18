"""开盘行情的字段、读取与针真假计算；不依赖复盘/预估入口或浮层。"""
import math
import re
import site
from pathlib import Path
from datetime import datetime, timedelta

VENV_SITE = Path.home()/".venvs/vault/Lib/site-packages"
if VENV_SITE.exists():
    site.addsitedir(str(VENV_SITE))
import pandas as pd
from 报表格式 import num, fmt, esc, table, Raw, page

HERE = Path(__file__).resolve().parent

DATA = HERE / "数据"

REVIEW = HERE / "复盘数据"

REC_FILE = REVIEW / "开盘复盘.csv"

NEEDLE_GATE = {"if": 15, "ic": 20, "im": 20}  # 股指门槛（档，一档 0.2 点）：IF 15 档 = 3 点，IC、IM 20 档 = 4 点（2026-11-18 他定的）

TICK = {"if": 0.2, "ic": 0.2, "im": 0.2}

RATIO_BINS = [(0.7, "0.7‰ 以下"), (1.5, "0.7–1.5‰"), (math.inf, "1.5‰ 以上")]

def product_of(symbol: str) -> str:
    """SHFE.ag2612 → ag"""
    return re.match(r"[A-Za-z]+", symbol.split(".")[-1]).group().lower()

def session_of(open_ts) -> str:
    return "夜盘" if open_ts.hour >= 20 else "日盘"

def needle_truth(dev, first, gate) -> str:
    """dev = 针比昨收价差偏几档，first = 首笔真实成交比昨收价差偏几档，gate = 这个品种的门槛（档）。
    真 = 首笔开在针的位置（离针 1 档以内，或比针走得还远）；半真 = 首笔偏出门槛、但比针小；
    假 = 首笔在门槛以内（几乎没动）；反向 = 首笔往针的反方向偏出门槛；没针 = 针本身没偏出门槛，不评。"""
    if gate is None or dev is None or first is None:
        return ""
    d, m = (int(math.copysign(math.floor(abs(x) + 0.5), x)) for x in (dev, first))  # 首笔是半秒成交均价，四舍五入到整档
    if abs(d) < gate:
        return "没针"
    m = m if d > 0 else -m
    if m >= abs(d) - 1:
        return "真"
    if m >= gate:
        return "半真"
    return "反向" if m <= -gate else "假"

def read_csv(f: Path):
    if not f.exists():
        return None
    return pd.read_csv(f, encoding="utf-8-sig")

def read_ticks(f: Path):
    df = read_csv(f)
    if df is None or not len(df):
        return None
    df["时间"] = pd.to_datetime(df["时间"])
    return df.set_index("时间").sort_index()

def auction_snapshot(leg, open_ts):
    """竞价窗口的成交合计与最新盘口；仅更新盘口的末张不会抹掉此前成交。"""
    if leg is None:
        return None
    o = pd.Timestamp(open_ts)
    w = leg[(leg.index >= o - pd.Timedelta(seconds=60)) & (leg.index < o)].sort_index()
    if w.empty:
        return None
    r = w.iloc[-1].copy()
    traded = w[w["成交手数"] > 0]
    r["最新价"] = traded["最新价"].iloc[-1] if len(traded) else float("nan")
    r["成交手数"] = w["成交手数"].clip(lower=0).sum(min_count=1)
    # 缺了任何一张持仓增量时，不能把已知部分当成完整竞价持仓变化。
    r["持仓变化"] = w["持仓变化"].sum(min_count=len(w)) if "持仓变化" in w else float("nan")
    return r

def small(n: int) -> str:
    return "没有样本" if not n else "样本太少，只是线索" if n < 10 else ("样本不多，证据弱" if n < 20 else "")

def load_closes(folder: Path, fc) -> dict:
    """{合约: {收盘价, 收盘时间, 到期日}}：收盘价.csv（开盘tick.py 存的），没有就用预估.csv 里记的。"""
    out = {}
    df = read_csv(folder / "收盘价.csv")
    if df is not None:
        for _, r in df.iterrows():
            out[r["合约"]] = {"收盘价": num(r["收盘价"]), "收盘时间": r.get("收盘时间"), "到期日": r.get("到期日"),
                              "最小变动价位": num(r.get("最小变动价位"))}
    if fc is not None:
        for _, r in fc.iterrows():
            for leg in ("腿1", "腿2"):
                out.setdefault(r[leg], {"收盘价": num(r[f"{leg}昨收"]), "收盘时间": r.get("收盘时间"),
                                        "到期日": r.get(f"{leg}到期日")})
    return out
