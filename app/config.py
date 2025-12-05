from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Optional

from dotenv import load_dotenv

load_dotenv()


@dataclass
class AppConfig:
    """Runtime configuration loaded from environment for the pricing bridge."""

    erp_url: str
    max_workers: int
    request_timeout: float
    store_code: str
    api_token: Optional[str]
    log_level: str
    default_customer_id: str
    mapping_path: Optional[str]


def load_config() -> AppConfig:
    """Create an AppConfig from the environment with sane defaults."""
    return AppConfig(
        erp_url=os.getenv("ERP_URL", "https://erp.example.com/api/pricing"),
        max_workers=int(os.getenv("MAX_WORKERS", "8")),
        request_timeout=float(os.getenv("REQUEST_TIMEOUT", "5.0")),
        store_code=os.getenv("STORE_CODE", "2"),
        api_token=os.getenv("API_TOKEN"),
        log_level=os.getenv("LOG_LEVEL", "INFO").upper(),
        default_customer_id=os.getenv("DEFAULT_CUSTOMER_ID", "CUSTOMER_ID_PLACEHOLDER"),
        mapping_path=os.getenv("MAPPING_CONFIG_PATH"),
    )
