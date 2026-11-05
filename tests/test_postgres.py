"""Run against real PostgreSQL in CI; never claim SQLite proves row-lock semantics."""

import os
from concurrent.futures import ThreadPoolExecutor

import pytest
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from billing_service.database import InboxRow, QuoteRow
from billing_service.domain import BillingError
from billing_service.providers import FakeProvider
from billing_service.workers import operation_once, relay_once
from tests.conftest import message
from tests.test_billing import events, generated, requested

pytestmark = [
    pytest.mark.postgres,
    pytest.mark.skipif(
        not os.environ.get("TEST_DATABASE_URL"),
        reason="Requires a dedicated real PostgreSQL database (CI provides one)",
    ),
]


def test_concurrent_duplicate_delivery_has_one_durable_result(billing, db, generate):
    def deliver(_):
        try:
            billing.handle(generate)
        except IntegrityError:
            # The delivery that lost the insert race must be retried, not acknowledged.
            return billing.handle(generate)

    with ThreadPoolExecutor(max_workers=6) as executor:
        list(executor.map(deliver, range(12)))
    with db.transaction() as u:
        assert len(list(u.s.scalars(select(QuoteRow)))) == 1
        assert len(list(u.s.scalars(select(InboxRow)))) == 1
    assert len(events(db)) == 1


def test_concurrent_approval_and_cancellation_do_not_publish_contradictions(billing, db, generate):
    qid = generated(billing, generate)

    def approve():
        try:
            return billing.decide(qid, 7, True)
        except BillingError:
            return None

    cancel = message("CancelarOrcamento", {"orcamentoId": qid, "motivo": "TIMEOUT"}, generate)
    with ThreadPoolExecutor(max_workers=2) as executor:
        a = executor.submit(approve)
        b = executor.submit(billing.handle, cancel)
        a.result()
        b.result()
    assert billing.quote(qid, 7)["status"] == "CANCELADO"
    # If approval won first, cancellation is a later transition, never a reopened quote.
    with pytest.raises(BillingError):
        billing.decide(qid, 7, True)


def test_two_provider_workers_and_relays_do_not_duplicate_effects(billing, db, generate):
    requested(billing, generate)

    class Counting(FakeProvider):
        calls = []

        def checkout(self, p, key):
            self.calls.append(key)
            return super().checkout(p, key)

    provider = Counting()
    with ThreadPoolExecutor(max_workers=2) as executor:
        list(executor.map(lambda _: operation_once(db, provider), range(2)))
    assert len(provider.calls) == 1
    sent = []

    class Publisher:
        def publish(self, m, attrs):
            sent.append(m["type"])

    with ThreadPoolExecutor(max_workers=2) as executor:
        list(executor.map(lambda _: relay_once(db, Publisher()), range(2)))
    while relay_once(db, Publisher()):
        pass
    assert sent == ["OrcamentoGerado", "OrcamentoAprovado"]
