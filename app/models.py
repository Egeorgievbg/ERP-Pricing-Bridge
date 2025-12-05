from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class CartItem:
    """Represents a line item coming from the shopping cart."""

    id: str
    name: str
    qty: float
    base_price: float
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ProcessedItem:
    """Stores the transformed price details returned for a cart item."""

    id: str
    name: str
    qty: float
    base_price: float
    final_price: float
    line_total: float
    is_b2b: bool
    client_name: Optional[str]
    status_msg: str
    logs: List[str]


@dataclass
class CalculationResult:
    """Aggregated pricing results returned by the engine."""

    items: List[ProcessedItem]
    duration: float
    grand_total: float
    base_total: float
    savings: float
    vat: float
    total_with_vat: float
    client_name: Optional[str]
