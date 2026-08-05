"""Shared validation helpers for office services."""
from datetime import datetime


def parse_datetime(value, field_name, required=False):
    """Parse an ISO-like datetime sent by the Vue client."""
    if value in (None, ''):
        if required:
            raise ValueError(f'{field_name} is required')
        return None
    if isinstance(value, datetime):
        return value
    try:
        return datetime.fromisoformat(str(value).replace('Z', '+00:00')).replace(tzinfo=None)
    except ValueError as error:
        raise ValueError(f'{field_name} must be a valid datetime') from error


def page_args(params):
    """Return bounded pagination arguments."""
    page = max(int(params.get('page', 1)), 1)
    page_size = min(max(int(params.get('page_size', 20)), 1), 100)
    return page, page_size
