"""Durable provider-operation worker and ordered transactional-outbox relay."""

import logging
from collections.abc import Callable
from datetime import timedelta

from billing_service import contract
from billing_service.domain import BillingError, instant, now_iso
from billing_service.ports import Provider, Publisher, Store

LOG = logging.getLogger("billing")


def operation_once(store: Store, provider: Provider, clock: Callable[[], str] = now_iso) -> bool:
    with store.transaction() as u:
        op = u.pending_operation(clock())
        if not op:
            return False
        p0 = u.get_payment(op.payment_id, lock=False)
        u.get_quote(p0.quote_id)
        p = u.get_payment(op.payment_id)
        op.attempts += 1
        if op.kind == "CHECKOUT" and p.status not in ["CRIACAO_PENDENTE", "RESULTADO_DESCONHECIDO"]:
            op.status = "CONCLUIDA"
            u.save_operation(op)
            return True
        try:
            if op.kind == "CHECKOUT":
                if p.status not in ["CRIACAO_PENDENTE", "RESULTADO_DESCONHECIDO"]:
                    raise BillingError(
                        "ESTADO_INVALIDO", "Pagamento não admite criação de checkout."
                    )
                p.order_id, p.checkout_url = provider.checkout(p, op.id)
                p.status = "AGUARDANDO_PAGAMENTO"
            else:
                if not provider.refund(p, op.id):
                    raise BillingError(
                        "ESTORNO_PENDENTE", "Estorno ainda não confirmado pelo provedor."
                    )
                p.status = "ESTORNADO"
                source = {
                    "messageId": op.cause_id,
                    "sagaId": p.saga_id,
                    "osId": p.os_id,
                    "requestId": p.request_id,
                }
                u.enqueue(
                    contract.response(
                        source,
                        "PagamentoEstornado",
                        {"pagamentoId": p.id, "estornadoEm": clock()},
                        clock(),
                    ),
                    p.trace_attributes,
                )
            op.status, op.last_error = "CONCLUIDA", None
        except Exception as exc:
            # Never log provider exception text/body/headers: they may contain secrets.
            op.last_error = exc.code if isinstance(exc, BillingError) else type(exc).__name__
            op.status = "DESCONHECIDO"
            op.available_at = (
                instant(clock()) + timedelta(seconds=min(300, 2 ** min(op.attempts, 8)))
            ).isoformat()
            if op.kind == "CHECKOUT":
                p.status = "RESULTADO_DESCONHECIDO"
            LOG.warning(
                "provider_operation_retry", extra={"operation_id": op.id, "code": op.last_error}
            )
        u.save_payment(p)
        u.save_operation(op)
    return True


def relay_once(store: Store, publisher: Publisher) -> bool:
    with store.transaction() as u:
        event = u.pending_event()
        if not event:
            return False
        sequence, message, attrs = event
        contract.validate(message)
        publisher.publish(message, attrs)
        u.mark_published(sequence)
    return True
