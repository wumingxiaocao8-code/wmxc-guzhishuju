"""纯色块规则。新结果使用 Facts；旧 CSV/JSON 的文案只在 from_tags 中兼容。

优先级：不判断/假 → 界内降级 → 薄大 → 换月 → 品种腿2禁用 → 其余分档。
这里不导入浮层、行情 SDK 或报表入口。变更优先级必须通过回归样本。
"""
from dataclasses import asdict, dataclass, replace
import re

RULE_VERSION = "sizing-2026-11-15-v1"


@dataclass(frozen=True)
class Policy:
    small_when_light: tuple = ("al", "zn", "ag", "ni")
    off_when_light: tuple = ("cu", "sn", "pb")
    cap_normal: tuple = ("pb",)
    off_when_leg2: tuple = ("ru", "ag", "br", "cu")
    small_when_cross: tuple = ("sc",)
    keep_heavy: float | None = 5
    keep_leg2: float = 2
    roll_off_any: tuple = ("br",)


AUTHOR = Policy()
COLLEAGUE = replace(AUTHOR, off_when_leg2=())


@dataclass(frozen=True)
class Facts:
    product: str
    kind: str
    heavy: float | None = None  # 已向下截一位的机会倍数，2.96 仍按 2.9
    leg2: bool = False
    leg2_multiple: float | None = None
    thin: bool = False
    light: bool = False
    few: bool = False
    small_needle: bool = False  # 只为旧记录/回放保留，当前生产不生成
    roll: str | None = None
    inside: bool = False

    def to_dict(self):
        return asdict(self)


def from_tags(key, kind, tags, leg2_x=None):
    """旧文本协议的唯一解析边界；不要在业务函数里解析显示文案。"""
    names = [t.rstrip("！") for t, _ in tags]
    heavy = next((float(t[1:]) for t in names if re.fullmatch(r"重\d+(\.\d+)?", t)), None)
    return Facts(re.match(r"[a-z]+", key.lower()).group(0), kind, heavy,  # 股指版：组合是大写 IC2703-IC2612
                 "腿2秒进" in names, leg2_x, "薄大" in names, "不重" in names,
                 "量少" in names, "小针" in names,
                 next((t for t, _ in tags if t.startswith("换月")), None), "界内" in names)


def decide(f: Facts, policy: Policy = AUTHOR):
    if f.kind in ("没针", "不判断"):
        return None
    p = f.product
    if f.kind == "假":
        return ("小", "判❌·sc小") if p in policy.small_when_cross else ("关", "判❌")
    if f.inside:
        v = decide(replace(f, inside=False), policy)
        return v if v is None or v[0] == "关" else ({"重": "打", "打": "小", "小": "关"}[v[0]], v[1] + "·界内")
    if f.thin:
        return "关", "薄大"
    if f.roll:
        if f.roll != "换月" or p in policy.roll_off_any:
            return "关", f.roll
        v = decide(replace(f, roll=None), policy)
        return v if v is None or v[0] == "关" else ({"重": "打", "打": "小", "小": "小"}[v[0]], v[1] + "·换月")
    if f.leg2 and p in policy.off_when_leg2:
        return "关", "腿2秒进"
    if f.small_needle:
        return "小", "小针"
    if f.heavy is None:
        if f.light or p in policy.off_when_light:
            return "关", "不重"
        if f.leg2:
            return "小", "不重·腿2秒进"
        return ("小" if p in policy.small_when_light else "打"), "不重"
    why = [f"重{f.heavy:g}"]
    level = "重" if f.heavy >= 3 else "打"
    if f.few:
        why.append("量少")
        level = "打" if level == "重" else level
    if p in policy.cap_normal and level == "重":
        level = "打"
    if f.leg2:
        if policy.keep_heavy is not None and f.leg2_multiple is not None and f.heavy >= policy.keep_heavy and f.leg2_multiple < policy.keep_leg2:
            why.append(f"腿2 {f.leg2_multiple:g}倍不降")
        else:
            why.append("腿2秒进")
            level = "小"
    return level, "·".join(why)


def verdict(key, kind, tags, leg2_x=None, policy=AUTHOR):
    """旧调用接口；新业务直接传 Facts 给 decide。"""
    return decide(from_tags(key, kind, tags, leg2_x), policy)
