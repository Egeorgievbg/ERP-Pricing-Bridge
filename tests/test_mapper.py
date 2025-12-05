from app.mapper import Mapper, MapperDefinition


def test_build_request_payload_maps_fields():
    definition = MapperDefinition(
        request_fields={"remote_id": "id", "remote_qty": "qty"}
    )
    mapper = Mapper(definition)

    payload = mapper.build_request_payload({"id": "foo", "qty": 2})

    assert payload["remote_id"] == "foo"
    assert payload["remote_qty"] == 2


def test_parse_response_handles_nested_keys():
    definition = MapperDefinition(
        request_fields={},
        response_fields={"price": "pricing.price", "status": "info.status"},
        default_client_field="client.name",
    )
    mapper = Mapper(definition)

    sample = {"pricing": {"price": 42}, "info": {"status": "OK"}, "client": {"name": "Acme"}}
    parsed = mapper.parse_response(sample)

    assert parsed["price"] == 42
    assert parsed["status"] == "OK"
    assert parsed["client_name"] == "Acme"
