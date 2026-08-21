from datetime import datetime, time

# No outbound comms between 9 PM and 9 AM (DND window)
DND_START = time(21, 0)
DND_END = time(9, 0)

COOLDOWN_HOURS_BETWEEN_ATTEMPTS = 24
MAX_TOTAL_ATTEMPTS = 3  # matches Transaction.max_attempts default, kept explicit here for clarity


def is_within_dnd_window(check_time: datetime) -> bool:
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