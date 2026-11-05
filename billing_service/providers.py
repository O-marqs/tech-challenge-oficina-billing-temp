"""Explicit local fake and test-only Checkout Pro Orders adapter.

No request is made at import time. Live integration evidence requires account testing.
"""

import re
from decimal import Decimal
from urllib.parse import urlparse

import httpx

from billing_service.domain import BillingError, Observation, Payment


class FakeProvider:
    def checkout(self, payment: Payment, key: str) -> tuple[str, str]:
        return f"FAKE-{key}", f"https://checkout.example.invalid/{payment.id}"

    def refund(self, payment: Payment, key: str) -> bool:
        return True

    def observe(self, resource_id: str) -> Observation:
        raise BillingError("FAKE_SEM_WEBHOOK", "Provedor fake não recebe webhook externo.", 404)


def cents(value) -> int:
    amount = Decimal(str(value)) * 100
    if not amount.is_finite() or amount != amount.to_integral_value() or amount < 0:
        raise ValueError("Provider amount is not an exact nonnegative number of cents")
    return int(amount)


class MercadoPagoOrders:
    def __init__(
        self, access_token: str, *, return_url: str = "", client: httpx.Client | None = None
    ):
        self.client = client or httpx.Client(
            base_url="https://api.mercadopago.com", timeout=10, follow_redirects=False
        )
        self.headers = {"Authorization": f"Bearer {access_token}"}
        self.return_url = return_url

    def _request(self, method: str, path: str, *, key: str | None = None, body=None) -> dict:
        headers = {**self.headers, **({"X-Idempotency-Key": key} if key else {})}
        result = self.client.request(method, path, headers=headers, json=body)
        result.raise_for_status()
        return result.json()

    @staticmethod
    def _test_order(data: dict) -> None:
        if not str(data.get("id", "")).startswith("ORDTST") or data.get("live_mode") is True:
            raise BillingError(
                "MODO_PROVEDOR_INVALIDO", "Adapter aceita somente orders de teste.", 503
            )

    def checkout(self, payment: Payment, key: str) -> tuple[str, str]:
        amount = f"{Decimal(payment.amount) / 100:.2f}"
        data = self._request(
            "POST",
            "/v1/orders",
            key=key,
            body={
                "type": "online",
                "processing_mode": "manual",
                "total_amount": amount,
                "external_reference": payment.id,
                "items": [{"title": "Orçamento oficina", "quantity": 1, "unit_price": amount}],
                **(
                    {
                        "config": {
                            "online": {
                                "success_url": self.return_url,
                                "failure_url": self.return_url,
                                "pending_url": self.return_url,
                            }
                        }
                    }
                    if self.return_url
                    else {}
                ),
            },
        )
        self._test_order(data)
        url = data["checkout_url"]
        parsed = urlparse(url)
        if parsed.scheme != "https" or parsed.hostname != "www.mercadopago.com.br":
            raise BillingError("URL_PROVEDOR_INVALIDA", "URL de checkout inesperada.", 503)
        return str(data["id"]), url

    def _get(self, resource_id: str) -> dict:
        if not re.fullmatch(r"ORDTST[A-Za-z0-9]{1,58}", resource_id):
            raise BillingError("ORDER_INVALIDA", "ID da order de teste inválido.", 422)
        data = self._request("GET", f"/v1/orders/{resource_id}")
        self._test_order(data)
        if data["id"] != resource_id:
            raise BillingError("ORDER_DIVERGENTE", "Order não corresponde à consulta.")
        return data

    def observe(self, resource_id: str) -> Observation:
        data = self._get(resource_id)
        payments = data.get("transactions", {}).get("payments", [])
        if len(payments) > 1:
            raise BillingError(
                "MULTIPLOS_PAGAMENTOS", "Order exige reconciliação de múltiplos pagamentos."
            )
        p = payments[0] if payments else {}
        status = data.get("status", "created")
        if (
            status == "processed"
            and p.get("status") == "processed"
            and p.get("status_detail") == "accredited"
        ):
            if not isinstance(p.get("id"), str) or not p["id"] or p["id"] == resource_id:
                raise BillingError(
                    "PAGAMENTO_PROVEDOR_INVALIDO", "Pagamento aprovado sem ID de transação válido."
                )
            status = "approved"
            amount = cents(p["paid_amount"])
        else:
            amount = cents(data["total_amount"])
            if status not in ["rejected", "cancelled", "expired"]:
                status = "pending"
        return Observation(
            str(p.get("id", resource_id)),
            data["external_reference"],
            amount,
            data["currency"],
            status,
            data.get("live_mode", False),
        )

    def refund(self, payment: Payment, key: str) -> bool:
        data = self._get(payment.order_id or "")
        payments = data.get("transactions", {}).get("payments", [])
        if (
            data["external_reference"] != payment.id
            or cents(data["total_amount"]) != payment.amount
            or data.get("currency") != "BRL"
            or not payment.provider_payment_id
            or len(payments) != 1
            or payments[0].get("id") != payment.provider_payment_id
        ):
            raise BillingError("ORDER_DIVERGENTE", "Order não corresponde ao pagamento.")
        if data.get("status") == "refunded":
            return self._refund_complete(data, payment)
        if cents(payments[0]["paid_amount"]) != payment.amount:
            raise BillingError("ORDER_DIVERGENTE", "Valor pago não corresponde ao pagamento.")
        result = self._request(
            "POST",
            f"/v1/orders/{payment.order_id}/refund",
            key=key,
            body={},  # Orders API: empty body requests the full refund required by the Saga.
        )
        return self._refund_complete(result, payment)

    def _refund_complete(self, data: dict, payment: Payment) -> bool:
        self._test_order(data)
        if data["id"] != payment.order_id:
            raise BillingError("ORDER_DIVERGENTE", "Estorno não corresponde à order.")
        if data.get("status") != "refunded" or data.get("status_detail") != "refunded":
            return False
        refunds = data.get("transactions", {}).get("refunds", [])
        if not refunds:
            return False
        ids = [r.get("id") for r in refunds]
        if (
            any(not isinstance(rid, str) or not rid for rid in ids)
            or len(set(ids)) != len(ids)
            or any(r.get("transaction_id") != payment.provider_payment_id for r in refunds)
        ):
            raise BillingError("ESTORNO_DIVERGENTE", "Estorno não corresponde à transação.")
        if any(r.get("status") != "processed" for r in refunds):
            return False
        return sum(cents(r["amount"]) for r in refunds) == payment.amount
