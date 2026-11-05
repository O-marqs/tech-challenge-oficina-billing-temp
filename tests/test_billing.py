from copy import deepcopy
from datetime import timedelta
from uuid import uuid4

import pytest
from sqlalchemy import select

from billing_service import contract
from billing_service.database import Database, InboxRow, OperationRow, OutboxRow, QuoteRow
from billing_service.domain import BillingError, Observation, instant
from billing_service.providers import FakeProvider
from billing_service.workers import operation_once, relay_once
from tests.conftest import message


def generated(billing, generate, attrs=None):
    billing.handle(generate, attrs)
    return contract.stable_id(f"quote:{generate['sagaId']}")


def requested(billing, generate):
    qid = generated(billing, generate)
    billing.decide(qid, 7, True)
    command = message(
        "SolicitarPagamento", {"orcamentoId": qid, "valorTotalCentavos": 20000}, generate
    )
    billing.handle(command)
    return qid, billing.payment(qid, 7)["pagamentoId"], command


def events(db):
    with db.transaction() as u:
        return [r.message for r in u.s.scalars(select(OutboxRow).order_by(OutboxRow.sequence))]


def test_full_participant_flow_and_compensation(billing, db, generate):
    qid, pid, cause = requested(billing, generate)
    assert operation_once(db, FakeProvider())
    assert billing.payment(qid, 7)["status"] == "AGUARDANDO_PAGAMENTO"
    assert not any(e["type"] == "PagamentoConfirmado" for e in events(db))
    billing.observe(pid, Observation("FAKE-PAYMENT-1", pid, 20000, "BRL", "approved"))
    refund = message(
        "EstornarPagamento", {"pagamentoId": pid, "motivo": "EXECUCAO_FALHOU"}, generate
    )
    billing.handle(refund)
    assert billing.payment(qid, 7)["status"] == "ESTORNO_PENDENTE"
    operation_once(db, FakeProvider())
    assert billing.payment(qid, 7)["status"] == "ESTORNADO"
    billing.handle(
        message("CancelarOrcamento", {"orcamentoId": qid, "motivo": "EXECUCAO_FALHOU"}, generate)
    )
    assert billing.quote(qid, 7)["status"] == "CANCELADO"
    assert [e["type"] for e in events(db)] == [
        "OrcamentoGerado",
        "OrcamentoAprovado",
        "PagamentoConfirmado",
        "PagamentoEstornado",
        "OrcamentoCancelado",
    ]
    for event in events(db):
        contract.validate(event)
        assert event["sagaId"] == generate["sagaId"]
        assert event["requestId"] == generate["requestId"]
    assert events(db)[2]["causationId"] == cause["messageId"]


def test_duplicate_survives_restart_and_detects_changed_body(billing, db, generate):
    qid = generated(billing, generate)
    restarted = type(billing)(
        Database(db.engine.url.render_as_string(hide_password=False)), billing.prices
    )
    assert restarted.handle(generate) == "DUPLICADA"
    assert restarted.quote(qid, 7)["valorTotalCentavos"] == 20000
    changed = deepcopy(generate)
    changed["payload"]["clienteId"] = 8
    with pytest.raises(BillingError, match="reutilizado"):
        restarted.handle(changed)
    assert len(events(db)) == 1


@pytest.mark.parametrize(
    "mutation",
    [
        lambda m: m.update(messageId="not-a-uuid"),
        lambda m: m.update(version=2),
        lambda m: m.update(traceparent="forbidden-in-body"),
        lambda m: m["payload"].update(unknown=1),
        lambda m: m["payload"]["pecas"][0].update(quantidade=0),
        lambda m: m.update(type="IniciarExecucao"),
    ],
)
def test_invalid_contract_has_no_effect(billing, db, generate, mutation):
    mutation(generate)
    with pytest.raises(BillingError):
        billing.handle(generate)
    assert not events(db)
    with db.transaction() as u:
        assert u.s.scalar(select(InboxRow)) is None


def test_unknown_price_and_zero_quote_publish_failure(billing, db, generate):
    billing.prices = {}
    billing.handle(generate)
    event = events(db)[0]
    assert event["type"] == "OrcamentoFalhou"
    assert event["payload"]["erro"]["codigo"] == "PRECO_NAO_ENCONTRADO"
    contract.validate(event)
    second = message("GerarOrcamento", generate["payload"])
    billing.prices = {"servico:12": 0, "peca:40": 0}
    billing.handle(second)
    assert events(db)[1]["payload"]["erro"]["codigo"] == "VALOR_ORCAMENTO_INVALIDO"


def test_decline_timeout_owner_and_reapproval(billing, db, generate):
    qid = generated(billing, generate)
    with pytest.raises(BillingError) as exc:
        billing.decide(qid, 8, True)
    assert exc.value.status == 403
    billing.decide(qid, 7, False, "Não desejo continuar")
    assert events(db)[-1]["type"] == "OrcamentoRecusado"
    with pytest.raises(BillingError):
        billing.decide(qid, 7, True)
    with pytest.raises(BillingError) as exc:
        billing.quote(str(uuid4()), 7)
    assert exc.value.status == 404
    third = message("GerarOrcamento", generate["payload"])
    qid2 = generated(billing, third)
    expiry = billing.quote(qid2, 7)["validoAte"]
    billing.clock = lambda: (instant(expiry) + timedelta(seconds=1)).isoformat()
    with pytest.raises(BillingError):
        billing.decide(qid2, 7, True)


def test_payment_value_correlation_and_new_id_cannot_duplicate_charge(billing, db, generate):
    qid, pid, original = requested(billing, generate)
    wrong = message("SolicitarPagamento", {"orcamentoId": qid, "valorTotalCentavos": 1}, generate)
    with pytest.raises(BillingError):
        billing.handle(wrong)
    wrong["payload"]["valorTotalCentavos"] = 20000
    wrong["sagaId"] = str(uuid4())
    with pytest.raises(BillingError):
        billing.handle(wrong)
    duplicate = deepcopy(original)
    duplicate["messageId"] = str(uuid4())
    billing.handle(duplicate)
    with db.transaction() as u:
        assert len(list(u.s.scalars(select(OperationRow)))) == 1
    assert billing.payment(qid, 7)["pagamentoId"] == pid
    with pytest.raises(BillingError):
        billing.handle(
            message("CancelarOrcamento", {"orcamentoId": qid, "motivo": "TIMEOUT"}, generate)
        )


@pytest.mark.parametrize(
    "changes",
    [dict(amount=1), dict(currency="USD"), dict(live_mode=True), dict(external_reference="other")],
)
def test_provider_observation_must_match_owned_payment(billing, generate, changes):
    _, pid, _ = requested(billing, generate)
    data = dict(
        payment_id="provider-1",
        external_reference=pid,
        amount=20000,
        currency="BRL",
        status="approved",
    )
    with pytest.raises(BillingError):
        billing.observe(pid, Observation(**{**data, **changes}))


def test_pending_failure_duplicate_and_late_notifications(billing, db, generate):
    qid, pid, _ = requested(billing, generate)
    billing.observe(pid, Observation("p1", pid, 20000, "BRL", "pending"))
    assert not any(e["type"].startswith("Pagamento") for e in events(db))
    billing.observe(pid, Observation("p1", pid, 20000, "BRL", "rejected"))
    assert events(db)[-1]["type"] == "PagamentoFalhou"
    with pytest.raises(BillingError, match="tardia"):
        billing.observe(pid, Observation("p1", pid, 20000, "BRL", "approved"))
    billing.handle(
        message("CancelarOrcamento", {"orcamentoId": qid, "motivo": "PAGAMENTO_FALHOU"}, generate)
    )


def test_refund_needs_confirmed_payment_and_duplicate_approval_is_idempotent(billing, db, generate):
    qid, pid, _ = requested(billing, generate)
    with pytest.raises(BillingError):
        billing.handle(
            message("EstornarPagamento", {"pagamentoId": pid, "motivo": "TIMEOUT"}, generate)
        )
    observation = Observation("p1", pid, 20000, "BRL", "approved")
    billing.observe(pid, observation)
    billing.observe(pid, observation)
    assert len([e for e in events(db) if e["type"] == "PagamentoConfirmado"]) == 1
    with pytest.raises(BillingError, match="Outro pagamento"):
        billing.observe(pid, Observation("p2", pid, 20000, "BRL", "approved"))


def test_transaction_rolls_back_business_inbox_and_outbox_together(
    db, billing, generate, monkeypatch
):
    from billing_service.database import SQLUnitOfWork

    original = SQLUnitOfWork.add_inbox

    def crash(*args):
        original(*args)
        raise RuntimeError("crash before commit")

    with monkeypatch.context() as patch:
        patch.setattr(SQLUnitOfWork, "add_inbox", crash)
        with pytest.raises(RuntimeError):
            billing.handle(generate)
    with db.transaction() as u:
        assert u.s.scalar(select(QuoteRow)) is None
        assert u.s.scalar(select(InboxRow)) is None
    assert not events(db)
    billing.handle(generate)
    assert len(events(db)) == 1


def test_relay_replays_identical_event_after_send_then_crash(billing, db, generate):
    generated(billing, generate)
    sent = []

    class FailsAfterSend:
        def publish(self, m, attrs):
            sent.append((m, attrs))
            raise RuntimeError("lost acknowledgement")

    with pytest.raises(RuntimeError):
        relay_once(db, FailsAfterSend())

    class Works:
        def publish(self, m, attrs):
            sent.append((m, attrs))

    assert relay_once(db, Works())
    assert sent[0] == sent[1]
    assert not relay_once(db, Works())


def test_checkout_timeout_is_unknown_and_retry_uses_same_key(billing, db, generate):
    qid, _, _ = requested(billing, generate)
    keys = []

    class Timeout(FakeProvider):
        def checkout(self, p, key):
            keys.append(key)
            raise TimeoutError("must never be logged verbatim")

    operation_once(db, Timeout())
    assert billing.payment(qid, 7)["status"] == "RESULTADO_DESCONHECIDO"
    assert not any(e["type"] == "PagamentoFalhou" for e in events(db))

    def future():
        return "2099-01-01T00:00:00Z"

    operation_once(db, Timeout(), future)
    assert keys[0] == keys[1]
