import os
from datetime import datetime, time, timedelta
from zoneinfo import ZoneInfo

IST = ZoneInfo("Asia/Kolkata")

# TRAI visiting hours: 9:00 AM – 9:00 PM IST
# DND window = outside visiting hours = 9 PM to 9 AM
DND_START = time(21, 0)   # 9 PM IST
DND_END   = time(9, 0)    # 9 AM IST

COOLDOWN_HOURS_BETWEEN_ATTEMPTS = 24
MAX_TOTAL_ATTEMPTS = 3

# Set RAAHI_IGNORE_DND=true in Render env to bypass DND during demos
DND_OVERRIDE_FOR_DEMO = os.getenv("RAAHI_IGNORE_DND", "false").lower() == "true"

# Set RAAHI_IGNORE_RETRY_TIMING=true in Render env to bypass ML timing windows during demos
RETRY_TIMING_OVERRIDE = os.getenv("RAAHI_IGNORE_RETRY_TIMING", "false").lower() == "true"


def is_within_dnd_window(check_time_utc: datetime) -> bool:
    if DND_OVERRIDE_FOR_DEMO:
        return False  # demo/testing override — pretend we're always outside DND

    ist_time = check_time_utc.replace(tzinfo=ZoneInfo("UTC")).astimezone(IST).time()
    if DND_START < DND_END:
        return DND_START <= ist_time <= DND_END
    return ist_time >= DND_START or ist_time <= DND_END


def next_allowed_time(now_utc: datetime) -> datetime:
    now_ist = now_utc.replace(tzinfo=ZoneInfo("UTC")).astimezone(IST)
    candidate_ist = now_ist.replace(hour=9, minute=0, second=0, microsecond=0)

    if now_ist.time() < DND_END:
        next_ist = candidate_ist
    else:
        next_ist = candidate_ist + timedelta(days=1)

    return next_ist.astimezone(ZoneInfo("UTC")).replace(tzinfo=None)


def cooldown_satisfied(last_attempt_time, now: datetime) -> bool:
    if last_attempt_time is None:
        return True
    hours_elapsed = (now - last_attempt_time).total_seconds() / 3600
    return hours_elapsed >= COOLDOWN_HOURS_BETWEEN_ATTEMPTS


def attempts_within_limit(attempts_made: int, max_attempts: int) -> bool:
    return attempts_made < max_attempts