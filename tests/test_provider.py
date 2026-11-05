import json

import httpx
import pytest

from billing_service.domain import BillingError, Payment
from billing_service.providers import FakeProvider, MercadoPagoOrders, cents


def payment():
    return Payment(
        "internal-1",
        "quote-1",
        "saga-1",
        101,
        7,
        "request-1",
        "command-1",
        20000,
        order_id="ORDTSTABC",
        provider_payment_id="PAYABC",
    )


def client(handler):
    return httpx.Client(
        base_url="https://api.mercadopago.com", transport=httpx.MockTransport(handler)
    )


def order(**changes):
    return {
        "id": "ORDTSTABC",
        "external_reference": "internal-1",
        "total_amount": "200.00",
        "currency": "BRL",
        "status": "processed",
        "live_mode": False,
        "transactions": {
            "payments": [
                {
                    "id": "PAYABC",
                    "paid_amount": "200.00",
                    "status": "processed",
                    "status_detail": "accredited",
                }
            ]
        },
        **changes,
    }


def test_checkout_orders_adapter_uses_exact_decimal_and_stable_idempotency():
    calls = []

    def handler(request):
        calls.append(request)
        return httpx.Response(
            201,
            json={
                "id": "ORDTSTABC",
                "checkout_url": "https://www.mercadopago.com.br/checkout/v1/redirect?order_id=ORDTSTABC",
            },
        )

    adapter = MercadoPagoOrders("test-only-token", client=client(handler))
    assert adapter.checkout(payment(), "stable-operation-1")[0] == "ORDTSTABC"
    request = calls[0]
    assert request.url.path == "/v1/orders"
    assert request.headers["X-Idempotency-Key"] == "stable-operation-1"
    data = json.loads(request.content)
    assert data["total_amount"] == "200.00"
    assert data["external_reference"] == "internal-1"
    assert data["processing_mode"] == "manual"


def test_observe_gets_payment_transaction_id_and_not_order_id():
    adapter = MercadoPagoOrders(
        "test-token", client=client(lambda _: httpx.Response(200, json=order()))
    )
    observed = adapter.observe("ORDTSTABC")
    assert observed.payment_id == "PAYABC"
    assert observed.amount == 20000
    assert observed.status == "approved"


@pytest.mark.parametrize(
    "changes,status",
    [
        (dict(status="created", transactions={}), "pending"),
        (dict(status="expired", transactions={}), "expired"),
        (dict(status="rejected", transactions={}), "rejected"),
    ],
)
def test_provider_terminal_and_pending_states(changes, status):
    adapter = MercadoPagoOrders(
        "test-token", client=client(lambda _: httpx.Response(200, json=order(**changes)))
    )
    assert adapter.observe("ORDTSTABC").status == status


def test_refund_uses_orders_endpoint_and_reconciles_existing_refund():
    calls = []

    def handler(request):
        calls.append(request)
        return httpx.Response(
            200,
            json=order() if request.method == "GET" else {"id": "ORDTSTABC", "status": "refunded"},
        )

    adapter = MercadoPagoOrders("test-token", client=client(handler))
    assert adapter.refund(payment(), "refund-key")
    assert calls[1].url.path == "/v1/orders/ORDTSTABC/refund"
    assert calls[1].headers["x-idempotency-key"] == "refund-key"
    assert json.loads(calls[1].content)["transactions"] == [{"id": "PAYABC", "amount": "200.00"}]
    adapter = MercadoPagoOrders(
        "test-token", client=client(lambda _: httpx.Response(200, json=order(status="refunded")))
    )
    assert adapter.refund(payment(), "refund-key")


@pytest.mark.parametrize(
    "data",
    [
        dict(id="ORDLIVE"),
        dict(id="ORDTSTABC", live_mode=True),
        dict(id="ORDTSTABC", checkout_url="https://attacker.invalid"),
        dict(id="ORDTSTABC", checkout_url="https://www.mercadopago.com.br.attacker.invalid"),
    ],
)
def test_checkout_rejects_live_order_or_untrusted_redirect(data):
    adapter = MercadoPagoOrders(
        "test-token", client=client(lambda _: httpx.Response(200, json=data))
    )
    with pytest.raises(BillingError):
        adapter.checkout(payment(), "key")


def test_provider_rejects_untrusted_resource_and_multiple_payments():
    adapter = MercadoPagoOrders(
        "test-token",
        client=client(
            lambda _: httpx.Response(200, json=order(transactions={"payments": [{}, {}]}))
        ),
    )
    with pytest.raises(BillingError):
        adapter.observe("../../users/me")
    with pytest.raises(BillingError):
        adapter.observe("ORDTSTABC")


@pytest.mark.parametrize("value", ["0.001", "NaN", "-1", "Infinity"])
def test_provider_amount_is_exact(value):
    with pytest.raises((ValueError, ArithmeticError)):
        cents(value)


def test_fake_is_explicit_and_does_not_fabricate_confirmation():
    fake = FakeProvider()
    assert fake.checkout(payment(), "key")[1].startswith("https://checkout.example.invalid/")
    assert fake.refund(payment(), "key")
    with pytest.raises(BillingError):
        fake.observe("anything")
