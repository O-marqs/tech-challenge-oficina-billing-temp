"""Transactional participant logic; external effects run through durable operations."""

from collections.abc import Callable
from datetime import timedelta

from billing_service import contract
from billing_service.domain import (
    BillingError,
    Observation,
    Operation,
    Payment,
    Quote,
    instant,
    now_iso,
    price_items,
)
from billing_service.ports import Store, UnitOfWork


class Billing:
    def __init__(
        self,
        store: Store,
        prices: dict[str, int],
        validity: int = 30,
        clock: Callable[[], str] = now_iso,
    ):
        self.store, self.prices, self.validity, self.clock = store, prices, validity, clock

    def handle(self, message: dict, attributes: dict | None = None) -> str:
        contract.validate(message, command=True)
        hashed = contract.digest(message)
        with self.store.transaction() as u:
            previous = u.inbox_hash(message["messageId"])
            if previous:
                if previous != hashed:
                    raise BillingError(
                        "MESSAGE_ID_REUTILIZADO", "messageId reutilizado com outro conteúdo."
                    )
                return "DUPLICADA"
            # Lock before mutation; unique saga_id guards concurrent creation.
            if message["type"] == "GerarOrcamento":
                self._generate(u, message, attributes or {})
            elif message["type"] == "CancelarOrcamento":
                q = self._quote(u, message["payload"]["orcamentoId"], message)
                payment = u.payment_for_quote(q.id)
                if payment and payment.status not in ["FALHOU", "ESTORNADO"]:
                    raise BillingError(
                        "PAGAMENTO_NAO_COMPENSADO", "Pagamento ainda requer resolução."
                    )
                if q.status != "CANCELADO":
                    q.status = "CANCELADO"
                    u.save_quote(q)
                    u.enqueue(
                        contract.response(
                            message, "OrcamentoCancelado", {"orcamentoId": q.id}, self.clock()
                        ),
                        attributes or {},
                    )
            elif message["type"] == "SolicitarPagamento":
                self._request_payment(u, message, attributes or {})
            else:
                self._request_refund(u, message)
            u.add_inbox(message["messageId"], hashed)
        return "PROCESSADA"

    def _generate(self, u: UnitOfWork, m: dict, attrs: dict) -> None:
        q = u.quote_for_saga(m["sagaId"])
        if q:
            if (
                q.os_id != m["osId"]
                or q.client_id != m["payload"]["clienteId"]
                or q.command_id != m["messageId"]
            ):
                raise BillingError("SAGA_JA_EXISTE", "Saga já vinculada a outro comando.")
            return
        now = self.clock()
        try:
            total, items = price_items(m["payload"], self.prices)
        except BillingError as exc:
            u.enqueue(
                contract.response(
                    m,
                    "OrcamentoFalhou",
                    {"erro": {"codigo": exc.code, "mensagem": exc.message}},
                    now,
                ),
                attrs,
            )
            return
        qid = contract.stable_id(f"quote:{m['sagaId']}")
        expiry = (
            (instant(now) + timedelta(minutes=self.validity)).isoformat().replace("+00:00", "Z")
        )
        event = contract.response(
            m,
            "OrcamentoGerado",
            {"orcamentoId": qid, "valorTotalCentavos": total, "validoAte": expiry},
            now,
        )
        q = Quote(
            qid,
            m["sagaId"],
            m["osId"],
            m["payload"]["clienteId"],
            m["payload"]["veiculoId"],
            m["requestId"],
            m["messageId"],
            event["messageId"],
            total,
            expiry,
            items,
            trace_attributes=attrs,
        )
        u.save_quote(q)
        u.enqueue(event, attrs)

    def _quote(self, u: UnitOfWork, qid: str, m: dict | None = None) -> Quote:
        q = u.get_quote(qid)
        if not q:
            raise BillingError("ORCAMENTO_NAO_ENCONTRADO", "Orçamento não encontrado.", 404)
        if m and (
            q.saga_id != m["sagaId"] or q.os_id != m["osId"] or q.request_id != m["requestId"]
        ):
            raise BillingError("CORRELACAO_INVALIDA", "Comando não pertence ao orçamento.")
        return q

    def _request_payment(self, u: UnitOfWork, m: dict, attrs: dict | None = None) -> None:
        q = self._quote(u, m["payload"]["orcamentoId"], m)
        if q.status != "APROVADO" or q.total != m["payload"]["valorTotalCentavos"]:
            raise BillingError("PAGAMENTO_INVALIDO", "Orçamento não aprovado ou valor divergente.")
        if u.payment_for_quote(q.id):
            return  # Unique business key prevents a second charge even with another messageId.
        p = Payment(
            contract.stable_id(f"payment:{q.id}"),
            q.id,
            q.saga_id,
            q.os_id,
            q.client_id,
            q.request_id,
            m["messageId"],
            q.total,
            trace_attributes=attrs or q.trace_attributes,
        )
        u.save_payment(p)
        u.save_operation(
            Operation(contract.stable_id(f"checkout:{p.id}"), p.id, "CHECKOUT", m["messageId"])
        )

    def _request_refund(self, u: UnitOfWork, m: dict) -> None:
        # Lock order is always quote then payment, including notification and operation workers.
        p0 = u.get_payment(m["payload"]["pagamentoId"], lock=False)
        if not p0:
            raise BillingError("PAGAMENTO_NAO_ENCONTRADO", "Pagamento não encontrado.", 404)
        self._quote(u, p0.quote_id, m)
        p = u.get_payment(p0.id)
        if p.status == "ESTORNADO":
            return
        if p.status not in ["CONFIRMADO", "ESTORNO_PENDENTE"]:
            raise BillingError(
                "PAGAMENTO_NAO_CONFIRMADO", "Somente pagamento confirmado admite estorno."
            )
        if p.status == "CONFIRMADO":
            p.status = "ESTORNO_PENDENTE"
            u.save_payment(p)
            u.save_operation(
                Operation(contract.stable_id(f"refund:{p.id}"), p.id, "REFUND", m["messageId"])
            )

    def decide(
        self,
        qid: str,
        client_id: int,
        approved: bool,
        reason: str | None = None,
        attributes: dict | None = None,
    ) -> dict:
        with self.store.transaction() as u:
            q = self._quote(u, qid)
            self._owner(q.client_id, client_id)
            now = self.clock()
            q.decide(approved, now)
            payload = {"orcamentoId": q.id, "aprovadoEm" if approved else "recusadoEm": now}
            if not approved:
                payload["motivo"] = reason
            src = self._source(q, q.generated_event_id)
            u.enqueue(
                contract.response(
                    src, "OrcamentoAprovado" if approved else "OrcamentoRecusado", payload, now
                ),
                q.trace_attributes or attributes or {},
            )
            u.save_quote(q)
            return {
                "orcamentoId": q.id,
                "osId": q.os_id,
                "sagaId": q.saga_id,
                "aprovadoEm" if approved else "recusadoEm": now,
            }

    def quote(self, qid: str, client_id: int) -> dict:
        with self.store.transaction() as u:
            q = self._quote(u, qid)
            self._owner(q.client_id, client_id)
            return {
                "orcamentoId": q.id,
                "osId": q.os_id,
                "sagaId": q.saga_id,
                "status": q.status,
                "valorTotalCentavos": q.total,
                "validoAte": q.valid_until,
                "itens": q.items,
            }

    def payment(self, qid: str, client_id: int) -> dict:
        with self.store.transaction() as u:
            q = self._quote(u, qid)
            self._owner(q.client_id, client_id)
            p = u.payment_for_quote(qid)
            if not p:
                raise BillingError(
                    "PAGAMENTO_NAO_ENCONTRADO", "Pagamento ainda não solicitado.", 404
                )
            return {
                "pagamentoId": p.id,
                "orcamentoId": p.quote_id,
                "status": p.status,
                "valorTotalCentavos": p.amount,
                "checkoutUrl": p.checkout_url,
            }

    def observe(self, payment_id: str, observation: Observation, attrs: dict | None = None) -> None:
        with self.store.transaction() as u:
            p0 = u.get_payment(payment_id, lock=False)
            if not p0:
                raise BillingError("PAGAMENTO_NAO_ENCONTRADO", "Pagamento não encontrado.", 404)
            q = self._quote(u, p0.quote_id)
            p = u.get_payment(payment_id)
            if (
                observation.live_mode
                or observation.external_reference != p.id
                or (observation.amount != p.amount or observation.currency != "BRL")
            ):
                raise BillingError("PROVEDOR_DIVERGENTE", "Dados de pagamento não conferem.")
            if p.status in ["CONFIRMADO", "ESTORNO_PENDENTE", "ESTORNADO"]:
                if p.provider_payment_id and p.provider_payment_id != observation.payment_id:
                    raise BillingError(
                        "PAGAMENTO_DUPLO", "Outro pagamento exige reconciliação manual."
                    )
                return
            if p.status == "FALHOU" or q.status == "CANCELADO":
                raise BillingError(
                    "PAGAMENTO_TARDIO", "Notificação tardia exige reconciliação manual."
                )
            if observation.status == "approved":
                p.status, p.provider_payment_id = "CONFIRMADO", observation.payment_id
                payload = {
                    "pagamentoId": p.id,
                    "valorPagoCentavos": p.amount,
                    "mercadoPagoPaymentId": observation.payment_id,
                    "confirmadoEm": self.clock(),
                }
                kind = "PagamentoConfirmado"
            elif observation.status in ["rejected", "cancelled", "expired"]:
                p.status, p.failure_reason = (
                    "FALHOU",
                    "EXPIRADO" if observation.status == "expired" else "RECUSADO",
                )
                payload, kind = {"motivo": p.failure_reason}, "PagamentoFalhou"
            else:
                return  # Pending/unknown is not a terminal failure.
            u.save_payment(p)
            u.enqueue(
                contract.response(self._source(q, p.command_id), kind, payload, self.clock()),
                p.trace_attributes or attrs or {},
            )

    @staticmethod
    def _source(q: Quote, cause: str) -> dict:
        return {"messageId": cause, "sagaId": q.saga_id, "osId": q.os_id, "requestId": q.request_id}

    @staticmethod
    def _owner(owner: int, actor: int) -> None:
        if owner != actor:
            raise BillingError("ACESSO_NEGADO", "Orçamento pertence a outro cliente.", 403)
