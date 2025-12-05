# ERP-Pricing-Bridge

ERP-Pricing-Bridge is a lightweight Python middleware that turns any shopping cart into a resilient, configurable connector for legacy ERP pricing APIs. It keeps the heavy lifting (threading, throttling, retries) in one place so your Django or other backend can stay focused on the cart experience.

## Why use this?
- **Performance**: The core engine executes concurrent lookups via `ThreadPoolExecutor`, keeping slow ERPs from blocking cart flows.
- **Resilience**: Built-in timeout handling, HTTP status checks, and structured error responses mean the service never crashes when the ERP misbehaves.
- **Open source friendly**: Configuration, mapping, and business logic are decoupled so that teams can reuse the engine across ERPs without touching the threading layer.

## Folder structure

```
/
|-- app/                # Flask factory, core engine, mapper, error helpers
|-- config/             # Sample mapping definitions
|-- tests/              # Unit tests for mappers and helpers
|-- requirements.txt    # Python dependencies
|-- Dockerfile          # Container definition
|-- docker-compose.yml  # Quick local stack
|-- .env.example        # Overrideable runtime configuration
|-- README.md
```

## Configuration

Copy `.env.example` to `.env` and override values for your environment. The following keys are supported:

| Variable | Description |
| --- | --- |
| `ERP_URL` | URL of the legacy ERP pricing endpoint. |
| `MAX_WORKERS` | Max threads the engine can spawn (default `8`). |
| `REQUEST_TIMEOUT` | Seconds before an ERP call is aborted (default `5`). |
| `STORE_CODE` | Optional static store identifier (example `2`). |
| `API_TOKEN` | (Optional) Bearer token sent in `Authorization` headers. |
| `LOG_LEVEL` | Standard Python log level (e.g., `INFO`, `DEBUG`). |
| `DEFAULT_CUSTOMER_ID` | Fallback customer identifier when none is supplied. |
| `MAPPING_CONFIG_PATH` | Path to a JSON file describing how to map fields. Defaults to `config/example_mapping.json`. |

## Mapping your ERP

The `MapperDefinition` controls how internal fields translate to ERP payloads and how ERP responses should be parsed. Example:

```json
{
  "request_fields": {
    "id_art": "id",
    "qty": "qty"
  },
  "response_fields": {
    "price": "cena1",
    "status": "info",
    "client_name": "klient"
  },
  "static_params": {},
  "default_client_field": "klient"
}
```

Drop your own JSON file and point `MAPPING_CONFIG_PATH` at it to adapt ERP-specific keys. The mapper also understands nested keys using `.` notation (e.g., `"nested.price": "pricing.value"`).

## API

### `POST /calculate`

Accepts JSON payloads with `items` (list of cart items) and an optional `customer_id`.

```json
{
  "customer_id": "CUSTOMER_ID_PLACEHOLDER",
  "items": [
    {"id": "12345", "name": "Widget", "qty": 2, "base_price": 9.99},
    {"id": "98765", "name": "Gadget", "qty": 1, "base_price": 15.49}
  ]
}
```

**Response shape**:

```json
{
  "status": "success",
  "duration": 1.24,
  "items": [...],
  "client_name": "Example B2B",
  "grand_total": 34.56,
  "vat": 6.91,
  "total_with_vat": 41.47,
  "savings": 2.13,
  "item_count": 2,
  "base_total": 36.69
}
```

Errors are returned in a consistent JSON envelope:

```json
{
  "status": "error",
  "message": "Invalid JSON payload"
}
```

## Example requests

- **cURL**

  ```bash
  curl -X POST http://localhost:5000/calculate \
    -H "Content-Type: application/json" \
    -d '{"customer_id": "CUSTOMER_ID_PLACEHOLDER", "items": [{"id": "500", "name": "Test", "qty": 1, "base_price": 9.99}]}'
  ```

- **Fetch (Browser / Node)**

  ```js
  await fetch("http://localhost:5000/calculate", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      customer_id: "CUSTOMER_ID_PLACEHOLDER",
      items: [{ id: "500", name: "Test", qty: 1, base_price: 9.99 }],
    }),
  });
  ```

## Running

- **Locally**: `pip install -r requirements.txt && python app.py`
- **Tests**: `pytest`
- **Docker**: `docker build -t erp-pricing-bridge .` then `docker run -p 5000:5000 --env-file=.env erp-pricing-bridge`
- **Docker Compose**: `docker compose up --build`

## Django 4.2 integration

- Derive the ERP customer identifier (`EIK`) from your Django user profile (e.g., `request.user.profile.erp_eik`) before forwarding cart items to `/calculate`. This keeps production data tied to authenticated identities.
- For end-to-end testing or manual QA you can still pass `customer_id` directly in the JSON payload; the bridge falls back to the payload value when present, so you retain the manual input you requested.
- Use the engine directly by importing `app.core.PricingEngine` or invoking the Flask endpoint from Django views if you prefer embedding it inside your existing service layer.

```python
from django.http import JsonResponse
from app.core import PricingEngine
from app.mapper import Mapper, load_mapping_definition
from app.config import load_config

engine = PricingEngine(load_config(), Mapper(load_mapping_definition(None)))

def pricing_view(request):
    customer_id = getattr(request.user.profile, "erp_eik", None)
    if not customer_id:
        return JsonResponse({"status": "error", "message": "missing ERP identifier"}, status=400)

    cart_items = [
        # Build this from request data or your Django cart models
    ]
    result = engine.calculate(cart_items, customer_id)
    return JsonResponse({"status": "success", "data": result})
```

## Next steps

1. Point `MAPPING_CONFIG_PATH` to a file that mirrors your ERP request/response schema.
2. Provide realistic cart payloads via `/calculate` from your frontend or integration layer.
3. Extend `tests/` with mocks of your ERP JSON payloads to keep the bridge resilient.
