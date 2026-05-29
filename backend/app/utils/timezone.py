from datetime import datetime, timedelta, timezone


BEIJING_TZ = timezone(timedelta(hours=8))


def beijing_now():
    """Return a timezone-naive Beijing datetime for database storage."""
    return datetime.now(BEIJING_TZ).replace(tzinfo=None)


def format_beijing(dt):
    """Serialize a stored datetime as an explicit Beijing time string."""
    if not isinstance(dt, datetime):
        return dt
    if dt.tzinfo is not None:
        dt = dt.astimezone(BEIJING_TZ).replace(tzinfo=None)
    return dt.isoformat()
