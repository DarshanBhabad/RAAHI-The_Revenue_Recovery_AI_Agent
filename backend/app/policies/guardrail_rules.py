from datetime import datetime, time, timedelta
import os

DND_OVERRIDE_FOR_DEMO = os.getenv("RAAHI_IGNORE_DND", "false").lower() == "true"  #For demo purposes, allow bypassing DND window via env var. In production, this should be false.
# No outbound comms between 9 PM and 9 AM (DND window)
DND_START = time(21, 0)
DND_END = time(9, 0)

COOLDOWN_HOURS_BETWEEN_ATTEMPTS = 24
MAX_TOTAL_ATTEMPTS = 3  # matches Transaction.max_attempts default, kept explicit here for clarity


def is_within_dnd_window(check_time: datetime) -> bool:
    if DND_OVERRIDE_FOR_DEMO:
        return False  # demo mode: pretend we're always outside DND
    t = check_time.time()
    if DND_START < DND_END:
        return DND_START <= t <= DND_END
    # window wraps midnight (e.g. 21:00 -> 09:00)
    return t >= DND_START or t <= DND_END


def cooldown_satisfied(last_attempt_time: datetime | None, now: datetime) -> bool:
    if last_attempt_time is None:
        return True
    hours_elapsed = (now - last_attempt_time).total_seconds() / 3600
    return hours_elapsed >= COOLDOWN_HOURS_BETWEEN_ATTEMPTS


def attempts_within_limit(attempts_made: int, max_attempts: int) -> bool:
    return attempts_made < max_attempts

def next_allowed_time(now: datetime) -> datetime:
    """Returns the next timestamp when DND window ends (09:00)."""
    candidate = now.replace(hour=9, minute=0, second=0, microsecond=0)
    if now.time() >= DND_START or now.time() < DND_END:
        # if we're past 9am already today but still "in" a wrapped window edge case,
        # or if it's currently before 9am, push to today 9am; otherwise tomorrow 9am
        if now.time() < DND_END:
            return candidate  # later today, before 9am currently -> today 9am
        else:
            return candidate + timedelta(days=1)  # after 9pm -> tomorrow 9am
    return candidate