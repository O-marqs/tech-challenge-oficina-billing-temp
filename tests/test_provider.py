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


def refunded(**changes):
    return order(
        status="refunded",
        status_detail="refunded",
        transactions={
            **order()["transactions"],
            "refunds": [
                {
                    "id": "REFABC",
                    "transaction_id": "PAYABC",
                    "amount": "200.00",
                    "status": "processed",
                }
            ],
        },
        **changes,
    )


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

    adapter = MercadoPagoOrders(
        "test-only-token", return_url="https://example.invalid/return", client=client(handler)
    )
    assert adapter.checkout(payment(), "stable-operation-1")[0] == "ORDTSTABC"
    request = calls[0]
    assert request.url.path == "/v1/orders"
    assert request.headers["X-Idempotency-Key"] == "stable-operation-1"
    data = json.loads(request.content)
    assert data["total_amount"] == "200.00"
    assert data["external_reference"] == "internal-1"
    assert data["processing_mode"] == "manual"
    assert data["config"]["online"] == {
        "success_url": "https://example.invalid/return",
        "failure_url": "https://example.invalid/return",
        "pending_url": "https://example.invalid/return",
    }
    assert "notification_url" not in data  # Configured in the Mercado Pago Webhooks panel.


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
            json=order() if request.method == "GET" else refunded(),
        )

    adapter = MercadoPagoOrders("test-token", client=client(handler))
    assert adapter.refund(payment(), "refund-key")
    assert calls[1].url.path == "/v1/orders/ORDTSTABC/refund"
    assert calls[1].headers["x-idempotency-key"] == "refund-key"
    assert json.loads(calls[1].content) == {}
    calls.clear()

    def reconciled(request):
        calls.append(request)
        return httpx.Response(200, json=refunded())

    adapter = MercadoPagoOrders("test-token", client=client(reconciled))
    assert adapter.refund(payment(), "refund-key")
    assert [r.method for r in calls] == ["GET"]


@pytest.mark.parametrize("transaction_id", [None, "", "ORDTSTABC"])
def test_approved_order_requires_real_payment_transaction_id(transaction_id):
    data = order()
    data["transactions"]["payments"][0]["id"] = transaction_id
    adapter = MercadoPagoOrders(
        "test-token", client=client(lambda _: httpx.Response(200, json=data))
    )
    with pytest.raises(BillingError, match="ID de transação"):
        adapter.observe("ORDTSTABC")


@pytest.mark.parametrize(
    "changes",
    [
        dict(currency="USD"),
        dict(external_reference="another-payment"),
        dict(total_amount="199.00"),
        dict(transactions={"payments": []}),
        dict(transactions={"payments": [{"id": "OTHER"}]}),
        dict(transactions={"payments": [{"id": "PAYABC"}, {"id": "OTHER"}]}),
        dict(transactions={"payments": [{"id": "PAYABC", "paid_amount": "1.00"}]}),
    ],
)
def test_refund_rejects_mismatch_before_any_financial_request(changes):
    calls = []

    def handler(request):
        calls.append(request.method)
        return httpx.Response(200, json=order(**changes))

    adapter = MercadoPagoOrders("test-token", client=client(handler))
    with pytest.raises(BillingError, match="corresponde"):
        adapter.refund(payment(), "refund-key")
    assert calls == ["GET"]


@pytest.mark.parametrize("change", ["amount", "pending", "missing", "partial"])
def test_refund_requires_complete_processed_evidence(change):
    data = refunded()
    if change == "amount":
        data["transactions"]["refunds"][0]["amount"] = "100.00"
    elif change == "pending":
        data["transactions"]["refunds"][0]["status"] = "processing"
    elif change == "missing":
        data["transactions"].pop("refunds")
    else:
        data["status_detail"] = "partially_refunded"
    calls = []

    def handler(request):
        calls.append(request.method)
        return httpx.Response(200, json=data)

    adapter = MercadoPagoOrders("test-token", client=client(handler))
    assert not adapter.refund(payment(), "refund-key")
    assert calls == ["GET"]  # Never repeat a refund whose reported result is incomplete.


@pytest.mark.parametrize("change", ["order", "transaction", "duplicate", "missing_id", "live"])
def test_refund_response_must_belong_to_expected_order_and_transaction(change):
    data = refunded()
    if change == "order":
        data["id"] = "ORDTSTOTHER"
    elif change == "transaction":
        data["transactions"]["refunds"][0]["transaction_id"] = "OTHER"
    elif change == "duplicate":
        data["transactions"]["refunds"] *= 2
    elif change == "missing_id":
        data["transactions"]["refunds"][0]["id"] = None
    else:
        data["live_mode"] = True
    adapter = MercadoPagoOrders(
        "test-token",
        client=client(lambda r: httpx.Response(200, json=order() if r.method == "GET" else data)),
    )
    with pytest.raises(BillingError):
        adapter.refund(payment(), "refund-key")


def test_incomplete_provider_refund_cannot_finish_saga_compensation(billing, db, generate):
    from billing_service.domain import Observation
    from billing_service.workers import operation_once
    from tests.conftest import message
    from tests.test_billing import events, requested

    qid, pid, _ = requested(billing, generate)
    operation_once(db, FakeProvider())
    with db.transaction() as u:
        p = u.payment_for_quote(qid)
        p.order_id = "ORDTSTABC"
        u.save_payment(p)
    billing.observe(pid, Observation("PAYABC", pid, 20000, "BRL", "approved"))
    billing.handle(
        message("EstornarPagamento", {"pagamentoId": pid, "motivo": "EXECUCAO_FALHOU"}, generate)
    )
    data = refunded()
    data["external_reference"] = pid
    data["transactions"]["refunds"][0]["amount"] = "100.00"
    adapter = MercadoPagoOrders(
        "test-token", client=client(lambda _: httpx.Response(200, json=data))
    )
    operation_once(db, adapter)
    assert billing.payment(qid, 7)["status"] == "ESTORNO_PENDENTE"
    assert not any(e["type"] == "PagamentoEstornado" for e in events(db))
    with pytest.raises(BillingError, match="resolução"):
        billing.handle(
            message(
                "CancelarOrcamento", {"orcamentoId": qid, "motivo": "EXECUCAO_FALHOU"}, generate
            )
        )


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
