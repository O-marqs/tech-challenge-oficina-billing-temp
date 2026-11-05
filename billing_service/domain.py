"""Pure domain types and pricing rules. No framework, database or cloud imports."""

from dataclasses import dataclass, field
from datetime import UTC, datetime


class BillingError(Exception):
    def __init__(self, code: str, message: str, status: int = 409):
        super().__init__(message)
        self.code, self.message, self.status = code, message, status


def now_iso() -> str:
    return datetime.now(UTC).isoformat().replace("+00:00", "Z")


def instant(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


@dataclass
class Quote:
    id: str
    saga_id: str
    os_id: int
    client_id: int
    vehicle_id: int
    request_id: str
    command_id: str
    generated_event_id: str
    total: int
    valid_until: str
    items: list[dict]
    status: str = "AGUARDANDO_APROVACAO"
    trace_attributes: dict = field(default_factory=dict)

    def decide(self, approved: bool, now: str) -> None:
        if self.status != "AGUARDANDO_APROVACAO" or instant(now) >= instant(self.valid_until):
            raise BillingError(
                "ORCAMENTO_NAO_AGUARDA_APROVACAO", "Orçamento indisponível para decisão."
            )
        self.status = "APROVADO" if approved else "RECUSADO"


@dataclass
class Payment:
    id: str
    quote_id: str
    saga_id: str
    os_id: int
    client_id: int
    request_id: str
    command_id: str
    amount: int
    status: str = "CRIACAO_PENDENTE"
    checkout_url: str | None = None
    order_id: str | None = None
    provider_payment_id: str | None = None
    failure_reason: str | None = None
    trace_attributes: dict = field(default_factory=dict)


@dataclass
class Operation:
    id: str
    payment_id: str
    kind: str
    cause_id: str
    status: str = "PENDENTE"
    attempts: int = 0
    available_at: str = field(default_factory=now_iso)
    last_error: str | None = None


@dataclass(frozen=True)
class Observation:
    payment_id: str
    external_reference: str
    amount: int
    currency: str
    status: str
    live_mode: bool = False


def price_items(payload: dict, prices: dict[str, int]) -> tuple[int, list[dict]]:
    items = []
    for plural, kind, id_field in [
        ("servicos", "servico", "servicoId"),
        ("pecas", "peca", "pecaId"),
    ]:
        for item in payload[plural]:
            key = f"{kind}:{item[id_field]}"
            value = prices.get(key)
            if isinstance(value, bool) or not isinstance(value, int) or value < 0:
                raise BillingError("PRECO_NAO_ENCONTRADO", "Item sem preço cadastrado.", 422)
            subtotal = value * item["quantidade"]
            items.append(
                {
                    "tipo": kind,
                    "itemId": item[id_field],
                    "quantidade": item["quantidade"],
                    "valorUnitarioCentavos": value,
                    "subtotalCentavos": subtotal,
                }
            )
    total = sum(i["subtotalCentavos"] for i in items)
    if total <= 0 or total > 999_999_999:
        raise BillingError("VALOR_ORCAMENTO_INVALIDO", "O orçamento deve ter valor positivo.", 422)
    return total, items
