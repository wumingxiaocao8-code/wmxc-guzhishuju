"""作者/同事差异显式选择，不靠发布时修改业务源码。"""
import json
from pathlib import Path
from 色块规则 import AUTHOR, COLLEAGUE

PROFILE_FILE = Path(__file__).with_name("运行配置.json")


def profile():
    if not PROFILE_FILE.is_file():
        raise FileNotFoundError(f"缺少运行配置：{PROFILE_FILE}；请恢复作者或同事配置，不能自动猜测")
    name = json.loads(PROFILE_FILE.read_text(encoding="utf-8-sig"))["版本"]
    if name not in ("作者", "同事"):
        raise ValueError(f"未知运行版本：{name}")
    return name


def policy():
    return AUTHOR if profile() == "作者" else COLLEAGUE


PROFILE = profile()
POLICY = AUTHOR if PROFILE == "作者" else COLLEAGUE
