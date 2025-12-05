from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, Iterable, Mapping, MutableMapping, Optional


@dataclass
class MapperDefinition:
    """Defines how application fields map to the legacy ERP payload."""

    request_fields: Dict[str, str]
    response_fields: Dict[str, str]
    static_params: Dict[str, Any] = field(default_factory=dict)
    default_client_field: str = "klient"


class Mapper:
    """Converts internal cart objects to ERP requests and parses responses."""

    def __init__(self, definition: MapperDefinition) -> None:
        self.definition = definition

    def build_request_payload(self, item: Mapping[str, Any]) -> Dict[str, Any]:
        payload: MutableMapping[str, Any] = dict(self.definition.static_params)
        for remote_key, local_key in self.definition.request_fields.items():
            if (value := self._walk_value(item, local_key)) is not None:
                payload[remote_key] = value
        return dict(payload)

    def parse_response(self, raw_response: Mapping[str, Any]) -> Dict[str, Any]:
        parsed: Dict[str, Any] = {}
        for result_key, source_key in self.definition.response_fields.items():
            parsed[result_key] = self._walk_value(raw_response, source_key)
        parsed.setdefault("client_name", self._walk_value(raw_response, self.definition.default_client_field))
        return parsed

    @staticmethod
    def _walk_value(source: Mapping[str, Any], key: str) -> Optional[Any]:
        """Support simple nested keys in the format parent.child."""
        current: Any = source
        for part in key.split("."):
            if isinstance(current, Mapping) and part in current:
                current = current[part]
            else:
                return None
        return current


DEFAULT_MAPPING = MapperDefinition(
    request_fields={"id_art": "id"},
    response_fields={"price": "cena1", "status": "info"},
)


def load_mapping_definition(path: Optional[str]) -> MapperDefinition:
    """Load a mapping definition from a JSON file or fall back to defaults."""
    if not path:
        return DEFAULT_MAPPING

    mapping_path = Path(path)
    if not mapping_path.exists():
        raise FileNotFoundError(f"Mapping configuration not found: {mapping_path}")

    raw = json.loads(mapping_path.read_text(encoding="utf-8"))
    return MapperDefinition(
        request_fields=raw.get("request_fields", {}),
        response_fields=raw.get("response_fields", {}),
        static_params=raw.get("static_params", {}),
        default_client_field=raw.get("default_client_field", DEFAULT_MAPPING.default_client_field),
    )
