"""开盘时间计算（股指版）；不启动任务、不连接行情。股指只有日盘：9:25–9:29 报单、9:29 集合竞价撮合、9:30 开盘。"""
from datetime import datetime, timedelta

OPEN_H, OPEN_M = 9, 30


def next_opening(now: datetime) -> datetime:
    """now 之后最近的一次股指开盘：9:30。"""
    day = now.replace(hour=OPEN_H, minute=OPEN_M, second=0, microsecond=0)
    return day if day > now else day + timedelta(days=1)


def has_opening(o: datetime, days: set) -> bool:
    """这天是不是交易日（股指没有夜盘）。"""
    return o.date() in days
