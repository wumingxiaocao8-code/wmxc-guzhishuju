"""出界（11-15 上线，研究在 测试/2026-11-11_出界深入/小结.md）。

判 ✅▲ 的同品种跨月格子：竞价价差（csv 的「针」）有没有顺着针冲出这格前 40 次开盘（约 20 个交易日）昨收价差的最高 / 最低。
  针往上：竞价价差 > 最高 = 出界；针往下：竞价价差 < 最低 = 出界；没冲出去 = 界内 → 浮层贴灰框「界内」，色块降一级（重→打、打→小、小→关）。
  sc 不判（两年只有 90 根、方向说不清）；跨品种（nr-ru）不判（研究里没有）；旧值不到 10 个不判（「不够」，色块照旧）。
两年回放：正滑全拿时钱基本不变，正滑只拿一半时少亏 30–49 万；窗口 5–30 天结果几乎一样。

历史昨收价差从哪来（两种都行，研究里验过出界 / 界内判得 94% 一样；数据/ 里攒满 40 个先用第 2 种，不满用第 1 种，见 judge）：
  1. 天勤 5 分钟 K 线（实盘优先用）：每节（日盘、夜盘）最后一根线的收盘价 = 那节最后一笔，两腿相减。
     竞价判断 20:57 / 8:57 一启动、连天勤之前，先另开一个进程跑 `出界.py --prep 开盘文件夹名`（平时 7 秒左右，最多等 PREP_WAIT 秒），
     结果写进 数据/开盘文件夹/出界区间.json；卡住、出错都不影响竞价判断本身（没写成就退回第 2 种）。
  2. 数据/ 里每次开盘的 竞价判断.csv 记下的昨收价差（回放、开盘复盘补算、天勤没取到时用）。
只是线索，不是买卖建议。
"""
import argparse
import json
import os
import sys
import threading
import time
from datetime import datetime, timedelta
from pathlib import Path

HERE = Path(__file__).resolve().parent
ON = True  # False = 关掉出界（不贴「界内」、色块照旧）
WINDOW, MIN_N = 40, 10  # 前 40 次开盘的昨收价差，至少 10 个旧值
SKIP = ("sc",)
KLINE_N = 4000  # 每腿取多少根 5 分钟线（sc、ag 夜盘长，一天约 114 根，4000 根够 60 多次开盘）
PREP_LIMIT = 100  # --prep 最多跑几秒，到时自己退出（单独跑时的保险）
PREP_WAIT = 30  # 竞价判断最多等它几秒（run_prep），到时结束它再连天勤
CACHE_NAME = "出界区间.json"


def applies(p1: str, p2: str) -> bool:
    return ON and p1 == p2 and p1 not in SKIP


# ---------- 历史：天勤 5 分钟线 ----------
def session_closes(k) -> dict:
    """5 分钟线 → {节: 收盘价}。节 = ("日期", "日") 或 ("夜盘开始那天", "夜")。
    一节的最后一根 = 下一根隔了 30 分钟以上（或最后一根）；K 线时间是这根线的开始，+5 分钟是收盘时刻；
    收盘时刻在 13:31–15:00 算日盘，21 点以后或 3 点以前算夜盘，别的（11:30 午休、10:15 小休）不算。"""
    import pandas as pd
    t = pd.to_datetime(k["datetime"], unit="ns", utc=True).dt.tz_convert("Asia/Shanghai").dt.tz_localize(None)
    d = pd.DataFrame({"t": t, "c": k["close"]}).dropna()
    d = d[d["c"] > 0].reset_index(drop=True)
    if d.empty:
        return {}
    gap = d["t"].shift(-1) - d["t"]
    end = (gap > pd.Timedelta(minutes=30)) | gap.isna()
    out = {}
    for t0, c in zip(d.loc[end, "t"], d.loc[end, "c"]):
        e = t0 + pd.Timedelta(minutes=5)
        hm = e.hour * 60 + e.minute
        if 13 * 60 + 31 <= hm <= 15 * 60:
            out[(e.strftime("%Y-%m-%d"), "日")] = float(c)
        elif e.hour >= 21:
            out[(e.strftime("%Y-%m-%d"), "夜")] = float(c)
        elif e.hour <= 3:
            out[((e - pd.Timedelta(days=1)).strftime("%Y-%m-%d"), "夜")] = float(c)
    return out


def hist_from_closes(a: dict, b: dict, o: datetime) -> list:
    """两腿共有的节，按时间排；去掉 o 以后的和最近那一节（那是这次开盘自己的昨收），留最后 WINDOW 个价差。"""
    def stamp(k):  # 节的收盘时刻，排序、和 o 比用
        d = datetime.strptime(k[0], "%Y-%m-%d")
        return d.replace(hour=15) if k[1] == "日" else d.replace(hour=23, minute=59)
    keys = sorted((k for k in set(a) & set(b) if stamp(k) < o), key=stamp)
    return [a[k] - b[k] for k in keys[:-1][-WINDOW:]]


def prep(name: str) -> None:
    """另开的进程：连天勤取看板每腿的 5 分钟线，算每格的前 40 节高低，写 数据/name/出界区间.json。"""
    threading.Timer(PREP_LIMIT, lambda: os._exit(3)).start()  # 到时间还没完就整个进程退出，不留尾巴
    import 开盘tick as tick
    import 开盘基础 as rv
    from 看板配置 import board_and_list
    o = datetime.strptime(name, "%Y-%m-%d_%H%M")
    pairs = [(a, b) for a, b in board_and_list() if applies(rv.product_of(a), rv.product_of(b))]
    legs = sorted({s for pr in pairs for s in pr})
    out = {"开盘": f"{o:%Y-%m-%d %H:%M}", "依据": "天勤 5 分钟线（每节最后一笔）", "格子": {}, "没取到": []}
    t0 = time.time()
    api = tick.connect(tries=1)
    try:
        closes = {}
        for s in legs:
            try:
                k = api.get_kline_serial(s, 300, data_length=KLINE_N)
                closes[s] = session_closes(k.copy())
            except Exception as e:  # noqa: BLE001  一条腿没取到只少那几格
                out["没取到"].append(f"{s.split('.')[-1]} {type(e).__name__}")
    finally:
        try:
            api.close()
        except Exception:  # noqa: BLE001
            pass
    for s1, s2 in pairs:
        if s1 in closes and s2 in closes:
            h = hist_from_closes(closes[s1], closes[s2], o)
            if h:
                out["格子"][f"{s1.split('.')[-1]}-{s2.split('.')[-1]}"] = {"高": max(h), "低": min(h), "节数": len(h)}
    out["算好"] = f"{datetime.now():%Y-%m-%d %H:%M:%S}"
    out["用时秒"] = round(time.time() - t0, 1)
    folder = rv.DATA / name
    folder.mkdir(parents=True, exist_ok=True)
    tmp = folder / (CACHE_NAME + ".tmp")
    tmp.write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")
    os.replace(tmp, folder / CACHE_NAME)
    print(f"出界区间：{len(out['格子'])} 格，用时 {out['用时秒']} 秒" + (f"；没取到 {'、'.join(out['没取到'])}" if out["没取到"] else ""),
          flush=True)
    os._exit(0)


def start_prep(name: str):
    """竞价判断一启动就调：后台进程算出界区间，不等它。"""
    import subprocess
    exe = Path(sys.executable).with_name("pythonw.exe")
    exe = exe if exe.exists() else Path(sys.executable)
    try:
        return subprocess.Popen([str(exe), str(HERE / "出界.py"), "--prep", name], cwd=HERE,
                                creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
    except Exception as e:  # noqa: BLE001
        print(f"出界区间没启动（这次退回用记下的昨收价差）：{type(e).__name__} {e}")
        return None


def run_prep(name: str, wait: float = None) -> None:
    """竞价判断连天勤之前调：算出界区间，最多等 wait 秒（平时 7 秒左右），到时没完就结束那个进程。
    先算完再让竞价判断连天勤，两个连接不同时开（同事的天勤账号不一定允许同时登两个）。竞价判断平时 HH:57:04 就取好昨收、空等到 59 分，等这几秒不耽误。"""
    import subprocess
    p = start_prep(name)
    if p is None:
        return
    try:
        p.wait(timeout=PREP_WAIT if wait is None else wait)
        if p.returncode != 0:
            print(f"出界区间没算成（退出码 {p.returncode}），这次用 数据/ 里记下的昨收价差")
    except subprocess.TimeoutExpired:
        p.kill()
        print(f"出界区间 {PREP_WAIT} 秒没算完，停掉，这次用 数据/ 里记下的昨收价差")


def read_cache(o: datetime) -> dict:
    import 开盘基础 as rv
    f = rv.DATA / f"{o:%Y-%m-%d_%H%M}" / CACHE_NAME
    try:
        d = json.loads(f.read_text(encoding="utf-8"))
        return {c: v | {"依据": "天勤5分钟线"} for c, v in d.get("格子", {}).items()} if d.get("开盘") == f"{o:%Y-%m-%d %H:%M}" else {}
    except Exception:  # noqa: BLE001  没有文件、没写完都当没有
        return {}


# ---------- 历史：数据/ 里记下的昨收价差 ----------
_REC = {}


def records():
    """数据/*/竞价判断.csv 的 (开盘, 组合, 昨收价差)，一个进程只读一次。"""
    if "df" not in _REC:
        import pandas as pd
        import 开盘基础 as rv
        parts = []
        for f in sorted(rv.DATA.glob("????-??-??_????/竞价判断.csv")):
            try:
                parts.append(pd.read_csv(f, encoding="utf-8-sig", usecols=["开盘", "组合", "昨收价差"]))
            except Exception:  # noqa: BLE001
                pass
        df = pd.concat(parts, ignore_index=True) if parts else pd.DataFrame(columns=["开盘", "组合", "昨收价差"])
        _REC["df"] = df.dropna(subset=["昨收价差"]).drop_duplicates(["开盘", "组合"]).sort_values("开盘")
    return _REC["df"]


def from_records(combo: str, o: datetime) -> dict | None:
    df = records()
    h = df[(df["组合"] == combo) & (df["开盘"] < f"{o:%Y-%m-%d %H:%M}")]["昨收价差"].tail(WINDOW).tolist()
    return {"高": max(h), "低": min(h), "节数": len(h), "依据": "记下的昨收价差"} if h else None


# ---------- 判 ----------
def judge(j: dict, combo: str, p1: str, p2: str, o: datetime, cache: dict | None = None) -> dict:
    """返回要并进这一行的字段：出界（出界 / 界内 / 不够）、近40节高、近40节低、出界节数、出界依据。不适用返回空。"""
    if not applies(p1, p2) or j.get("档") not in ("真", "半真"):
        return {}
    try:
        needle, dev = float(j["针"]), float(j["针偏几档"])
    except (KeyError, TypeError, ValueError):
        return {}
    # 记下的（30 秒均价，研究主口径）攒满 40 个先用它；不满时用天勤（最后一笔，收盘那几秒偶尔被打价，sc fu 见过差 30–45 档）补；都不够再看记下的够不够 10 个
    rec, kl = from_records(combo, o), (cache or {}).get(combo)
    b = rec if rec and rec["节数"] >= WINDOW else kl if kl and kl.get("节数", 0) >= MIN_N else rec
    if not b or b["节数"] < MIN_N:
        return {"出界": "不够", "出界节数": b["节数"] if b else 0, "出界依据": b["依据"] if b else ""}
    up = dev > 0
    lab = "出界" if (needle > b["高"] if up else needle < b["低"]) else "界内"
    return {"出界": lab, "近40节高": round(b["高"], 4), "近40节低": round(b["低"], 4), "出界节数": b["节数"], "出界依据": b["依据"]}


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--prep", help="开盘文件夹名，如 2026-11-16_0900：取天勤 5 分钟线算出界区间")
    a = p.parse_args()
    if a.prep:
        prep(a.prep)


if __name__ == "__main__":
    main()
