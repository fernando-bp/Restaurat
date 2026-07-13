from app.application.services.factus_service import FactusInvoiceService


def test_build_payload_uses_consumer_final_defaults_when_nit_missing():
    service = FactusInvoiceService()

    payload = service.build_payload(
        order_id=42,
        order_data={
            "id": 42,
            "mesa_id": 3,
            "cliente_nombre": None,
            "cliente_nit": None,
            "cliente_email": None,
            "total_bruto": 10000,
            "total_descuento": 0,
            "total_iva": 1900,
            "total_neto": 11900,
        },
        items=[
            {"receta_id": 1, "cantidad": 2, "precio_unitario": 4000, "subtotal": 8000},
            {"receta_id": 2, "cantidad": 1, "precio_unitario": 3900, "subtotal": 3900},
        ],
        recipe_map={
            1: {"nombre": "Hamburguesa", "precio_venta": 4000},
            2: {"nombre": "Coca Cola", "precio_venta": 3900},
        },
        cliente_nombre=None,
        cliente_nit=None,
        cliente_email=None,
    )

    assert payload["reference_code"] == "ORD-42"
    assert payload["customer"]["names"] == "Consumidor final"
    assert payload["customer"]["identification"] == "222222222222"
    assert payload["customer"]["tribute_code"] == "ZZ"
    assert payload["items"][0]["name"] == "Hamburguesa"
    assert payload["document"] == "01"
    assert payload["payment_details"][0]["amount"] == "11900.00"
    assert payload["payment_details"][0]["reference_code"] == "PAY-42"
