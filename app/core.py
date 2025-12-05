from __future__ import annotations

import logging
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Iterable, List, Optional

import requests

from app.config import AppConfig
from app.mapper import Mapper
from app.models import CalculationResult, CartItem, ProcessedItem

LOGGER = logging.getLogger(__name__)


class PricingEngine:
    """Handles threading, HTTP error handling, and aggregation logic."""

    def __init__(self, config: AppConfig, mapper: Mapper) -> None:
        self.config = config
        self.mapper = mapper
        self.session = requests.Session()
        headers = {"Accept": "application/json"}
        if self.config.api_token:
            headers["Authorization"] = f"Bearer {self.config.api_token}"
        self.session.headers.update(headers)

    def fetch_price(self, item: CartItem, customer_id: str) -> ProcessedItem:
        """Fetch a price from the legacy API for a single cart item."""
        logs: List[str] = []
        params = self.mapper.build_request_payload(item.__dict__)
        params.update({"sk_code": self.config.store_code, "kl_eik": customer_id})

        processed = ProcessedItem(
            id=item.id,
            name=item.name,
            qty=item.qty,
            base_price=item.base_price,
            final_price=item.base_price,
            line_total=item.base_price * item.qty,
            is_b2b=False,
            client_name=None,
            status_msg="standard",
            logs=logs,
        )

        try:
            response = self.session.get(self.config.erp_url, params=params, timeout=self.config.request_timeout)
            logs.append(f"erp_status={response.status_code}")

            if response.ok:
                payload = response.json()
                if isinstance(payload, list) and payload:
                    record = payload[0]
                elif isinstance(payload, dict):
                    record = payload
                else:
                    record = {}
                    logs.append("empty payload")

                parsed = self.mapper.parse_response(record)
                self._apply_parsed_response(processed, parsed, logs)
            else:
                logs.append(f"unexpected status={response.status_code}")
        except requests.RequestException as exc:
            LOGGER.exception("calls to ERP failed", exc_info=exc)
            logs.append(f"exception={exc}")

        return processed

    def calculate(self, items: Iterable[CartItem], customer_id: str) -> CalculationResult:
        """Orchestrate concurrent pricing lookups and summarize the response."""
        indexed_items = list(items)
        results: List[Optional[ProcessedItem]] = [None] * len(indexed_items)
        client_name: Optional[str] = None
        start = time.perf_counter()

        with ThreadPoolExecutor(max_workers=self.config.max_workers) as executor:
            futures = {
                executor.submit(self.fetch_price, item, customer_id): idx
                for idx, item in enumerate(indexed_items)
            }

            for future in as_completed(futures):
                idx = futures[future]
                processed = future.result()
                results[idx] = processed
                if processed.client_name and len(processed.client_name) > 2 and not client_name:
                    client_name = processed.client_name

        duration = round(time.perf_counter() - start, 2)
        processed_items = [item for item in results if item]
        grand_total = sum(item.line_total for item in processed_items)
        base_total = sum(item.base_price * item.qty for item in indexed_items)
        savings = round(max(base_total - grand_total, 0.0), 2)
        vat = round(grand_total * 0.20, 2)
        total_with_vat = round(grand_total + vat, 2)

        return CalculationResult(
            items=processed_items,
            duration=duration,
            grand_total=round(grand_total, 2),
            base_total=round(base_total, 2),
            savings=savings,
            vat=vat,
            total_with_vat=total_with_vat,
            client_name=client_name,
        )

    def _apply_parsed_response(
        self, processed: ProcessedItem, parsed: dict[str, Optional[str]], logs: List[str]
    ) -> None:
        """Apply parsed values from the ERP back into the processed record."""
        price_value = parsed.get("price")
        status_value = (parsed.get("status") or "").upper()
        client_name = parsed.get("client_name")

        try:
            final_price = float(price_value)
        except (TypeError, ValueError):
            logs.append("invalid price")
            return

        if final_price <= 0 or "DUBLICATE" in status_value:
            processed.status_msg = "Duplicate/Error"
            logs.append(f"status={status_value or 'unknown'}")
            return

        processed.final_price = final_price
        processed.line_total = final_price * processed.qty
        processed.is_b2b = True
        if client_name:
            processed.client_name = client_name
        processed.status_msg = "B2B Deal"
        logs.append(f"price={final_price:.2f}")
