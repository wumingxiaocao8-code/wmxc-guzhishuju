"""看板配置与组合命名；不依赖 Windows 浮层。"""
import json
import re
from pathlib import Path
from 色块规则 import verdict as _verdict
from 运行配置 import POLICY
LOTS_DEFAULT = (40, 100, 200)

HERE = Path(__file__).resolve().parent

BOARD_FILE = HERE / "看板.txt"

REF_DIR = HERE / "复盘数据" / "看板样子"  # --test 时存的每格标题样子

DEFAULTS = {"网格左": 19, "网格上": 47, "网格右": 0, "网格下": 20, "标签上": 20, "标签右": 8, "字号": 10,
            "公式宽": 410, "公式左": 66, "提示左": 560, "提示上": 2, "提示字号": 13}

LOTS = {"sc": (4, 6, 10), "ag": (6, 12, 20), "cu": (10, 20, 40), "sn": (4, 6, 10), "ni": (10, 20, 30),   # 11-17 他改 sn ni ao nr br ru hc rb
        "rb": (20, 40, 60), "hc": (60, 100, 200), "ao": (20, 40, 60), "sp": (40, 60, 80),
        "nr": (10, 20, 40), "br": (10, 20, 40), "ru": (10, 20, 30),
        **{p: (20, 40, 60) for p in ("ss", "al", "zn", "pb")}}

LIFE = 600  # 最多开 10 分钟（竞价判断.py 出意外没写结果时，浮层自己关掉）

def read_board(f: Path = BOARD_FILE) -> dict:
    """看板.txt：格子（一行一排，从左到右，「交易所.代码,交易所.代码」，空格子写 -）、位置参数（像素）
    和他的手数（「手数 sc = 4 6 10」= 正常 / 波动大 / 非常大，盘口框分少 / 正常 / 大用）。"""
    rows, opts, lots = [], dict(DEFAULTS), dict(LOTS)
    if f.exists():
        for line in f.read_text(encoding="utf-8").splitlines():
            line = line.split("#")[0].strip()
            if not line:
                continue
            if "=" in line:
                k, v = (x.strip() for x in line.split("=", 1))
                if k.startswith("手数"):
                    try:
                        n = tuple(float(x) for x in v.replace(",", " ").replace("，", " ").split())
                    except ValueError:
                        n = ()
                    if len(n) >= 2:
                        lots[k[2:].strip().lower()] = n
                    continue
                try:
                    opts[k] = float(v)
                except ValueError:  # 「只认路径 = 东证」这种文字设置，原样存着
                    opts[k] = v
            else:
                rows.append(line.split())
    board = {"格子": rows, "参数": opts, "手数": lots}
    try:  # --test 时量的每排格子实际在哪（博易云的格子不一定一样高）
        lines = json.loads((REF_DIR / "窗口.json").read_text(encoding="utf-8")).get("行线")
        if lines and len(lines) == len(rows) + 1:
            board["行线"] = lines
    except (OSError, ValueError):
        pass
    return board

def pair_key(item: str) -> str:
    """INE.sc2701,INE.sc2612 → sc2701-sc2612（和开盘复盘、竞价判断里的「组合」一样）；空格子 → 空。"""
    legs = item.split(",")
    return "-".join(x.split(".")[-1] for x in legs) if len(legs) == 2 else ""

def label_name(s1: str, s2: str) -> str:
    """标签上的组合名：同品种写 sc2701-2612，跨品种写全 nr2612-ru2701。"""
    c1, c2 = s1.split(".")[-1], s2.split(".")[-1]
    p1, p2 = (re.match(r"[A-Za-z]+", c).group().lower() for c in (c1, c2))
    return f"{c1}-{c2[len(p2):]}" if p1 == p2 else f"{c1}-{c2}"

def board_pairs(board: dict) -> list[tuple[str, str]]:
    """看板上所有的组合 (腿1, 腿2)，按格子顺序。"""
    return [tuple(x.split(",")) for row in board["格子"] for x in row if len(x.split(",")) == 2]


def board_and_list() -> list:
    """股指版：只判断看板.txt 上的格子（没有 合约.txt），按格子顺序去重。"""
    pairs = [tuple(p) for p in board_pairs(read_board())]
    return list(dict.fromkeys(pairs))


def verdict(key, kind, tags, leg2_x=None):
    """兼容原 jd.fl.verdict 调用，采用显式运行配置。"""
    return _verdict(key, kind, tags, leg2_x, POLICY)
