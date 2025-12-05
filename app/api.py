from __future__ import annotations

from typing import Any, Dict, Iterable, List, Mapping, Optional

import logging
from flask import Flask, Response, jsonify, request

from app.config import AppConfig, load_config
from app.core import PricingEngine
from app.errors import json_error
from app.mapper import Mapper, load_mapping_definition
from app.models import CartItem, CalculationResult, ProcessedItem

LOGGER = logging.getLogger(__name__)


def create_app(config: Optional[AppConfig] = None) -> Flask:
    """Create Flask application factory for the ERP Pricing Bridge."""
    cfg = config or load_config()
    logging.basicConfig(level=cfg.log_level, format="%(asctime)s %(levelname)s %(name)s %(message)s")
    mapping = load_mapping_definition(cfg.mapping_path)
    engine = PricingEngine(cfg, Mapper(mapping))

    app = Flask(__name__)
    app.config["ENGINE"] = engine

    @app.route("/", methods=["GET"])
    def health():
        return jsonify(
            {
                "status": "ok",
                "description": "ERP-Pricing-Bridge is ready to accept POST /calculate",
            }
        )

    @app.route("/calculate", methods=["POST"])
    def calculate():
        payload = _load_payload()
        if isinstance(payload, Response):
            return payload

        raw_items = payload.get("items")
        if not raw_items:
            return json_error("items array is required", 422)

        try:
            items = _build_cart_items(raw_items)
        except ValueError as exc:
            return json_error(str(exc), 422)

        customer_id = payload.get("customer_id") or cfg.default_customer_id
        result = engine.calculate(items, customer_id)
        return _format_response(result)

    return app


def _load_payload() -> Any:
    """Safely parse JSON payload and respond with an error message if parsing fails."""
    payload = request.get_json(silent=True)
    if payload is None:
        return json_error("Invalid JSON payload", 400)
    return payload


def _build_cart_items(raw_items: Iterable[Mapping[str, Any]]) -> List[CartItem]:
    """Convert incoming item dictionaries to CartItem objects."""
    mapped: List[CartItem] = []
    for index, raw in enumerate(raw_items):
        try:
            mapped.append(
                CartItem(
                    id=str(raw["id"]),
                    name=str(raw["name"]),
                    qty=float(raw.get("qty", 1)),
                    base_price=float(raw.get("base_price", 0)),
                    metadata=raw.get("metadata", {}),
                )
            )
        except KeyError as exc:
            raise ValueError(f"item at index {index} is missing {exc.args[0]}") from exc
        except (TypeError, ValueError):
            raise ValueError(f"invalid numeric value for item at index {index}")
    return mapped


def _serialize_item(item: ProcessedItem) -> Dict[str, Any]:
    """Prepare processed items for JSON serialization."""
    return {
        "id": item.id,
        "name": item.name,
        "qty": item.qty,
        "base_price": item.base_price,
        "final_price": item.final_price,
        "line_total": round(item.line_total, 2),
        "is_b2b": item.is_b2b,
        "client_name": item.client_name,
        "status_msg": item.status_msg,
        "logs": item.logs,
    }


def _format_response(result: CalculationResult) -> Any:
    """Create clean response structure for the client."""
    payload = {
        "status": "success",
        "duration": result.duration,
        "items": [_serialize_item(item) for item in result.items],
        "client_name": result.client_name,
        "grand_total": result.grand_total,
        "vat": result.vat,
        "total_with_vat": result.total_with_vat,
        "savings": result.savings,
        "item_count": len(result.items),
        "base_total": result.base_total,
    }
    return jsonify(payload)
