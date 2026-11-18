"""Datas no fuso horário do negócio (America/Sao_Paulo por padrão)."""

import calendar
from datetime import UTC, date, datetime, time, timedelta
from zoneinfo import ZoneInfo

from app.core.config import settings

TZ = ZoneInfo(settings.TIMEZONE)


def now_utc() -> datetime:
    return datetime.now(UTC)


def today_local() -> date:
    return datetime.now(TZ).date()


def start_of_day(d: date) -> datetime:
    """00:00 do dia no fuso local, como datetime timezone-aware (para comparar com timestamptz)."""
    return datetime.combine(d, time.min, tzinfo=TZ)


def end_of_day_exclusive(d: date) -> datetime:
    """00:00 do dia seguinte — use com `<` para incluir o dia inteiro."""
    return start_of_day(d + timedelta(days=1))


def month_start(d: date) -> date:
    return d.replace(day=1)


def add_months(d: date, months: int) -> date:
    month_index = d.month - 1 + months
    year = d.year + month_index // 12
    month = month_index % 12 + 1
    day = min(d.day, calendar.monthrange(year, month)[1])
    return date(year, month, day)


def days_between(start: datetime, end: datetime) -> float:
    return (end - start).total_seconds() / 86400
