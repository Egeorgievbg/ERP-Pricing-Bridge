from __future__ import annotations

from typing import Any, Dict, Mapping, Optional

from flask import jsonify


def json_error(message: str, status_code: int = 400, details: Optional[Mapping[str, Any]] = None):
    """Return a structured error response for the API."""
    payload: Dict[str, Any] = {
        "status": "error",
        "message": message,
    }
    if details:
        payload["details"] = details
    response = jsonify(payload)
    response.status_code = status_code
    return response
