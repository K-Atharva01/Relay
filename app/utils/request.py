"""Request parsing helpers."""

from flask import request


def get_json_object():
    """Return the request's JSON body if it is an object, otherwise {}."""
    data = request.get_json(silent=True)
    return data if isinstance(data, dict) else {}


def get_str(data, key):
    """Return data[key] if it is a string, otherwise None."""
    value = data.get(key)
    return value if isinstance(value, str) else None
