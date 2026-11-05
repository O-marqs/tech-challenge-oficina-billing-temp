import json
import signal
import sys
from uuid import uuid4

import pytest

from billing_service.cli import main
from billing_service.domain import Observation
from tests.test_billing import requested


def invoke(monkeypatch, args):
    monkeypatch.setattr(sys, "argv", ["billing", *args])
    # Calling main inside pytest must not replace the test runner's signal handlers.
    monkeypatch.setattr(signal, "signal", lambda *_: None)
    main()


@pytest.fixture
def cli_env(db, monkeypatch):
    monkeypatch.setenv("DATABASE_URL", db.engine.url.render_as_string(hide_password=False))
    monkeypatch.setenv("APP_ENV", "test")
    monkeypatch.setenv("PAYMENT_PROVIDER", "fake")
    return db


def test_cli_migrate_is_reentrant(tmp_path, monkeypatch):
    from billing_service.database import Database

    url = f"sqlite:///{tmp_path}/migration.db"
    monkeypatch.setenv("DATABASE_URL", url)
    invoke(monkeypatch, ["migrate"])
    invoke(monkeypatch, ["migrate"])
    assert Database(url).ready()


def test_cli_handle_file_and_query_via_api_logic(
    cli_env, billing, generate, tmp_path, monkeypatch, capsys
):
    from billing_service.contract import stable_id

    path = tmp_path / "command.json"
    path.write_text(json.dumps(generate))
    invoke(monkeypatch, ["handle-file", "--file", str(path)])
    assert "PROCESSADA" in capsys.readouterr().out
    qid = stable_id(f"quote:{generate['sagaId']}")
    assert billing.quote(qid, 7)["valorTotalCentavos"] == 20000


def test_cli_operation_and_explicit_simulation(cli_env, billing, generate, monkeypatch, capsys):
    qid, pid, _ = requested(billing, generate)
    invoke(monkeypatch, ["operations", "--once"])
    assert billing.payment(qid, 7)["status"] == "AGUARDANDO_PAGAMENTO"
    invoke(monkeypatch, ["simulate-payment", "--payment-id", pid])
    assert billing.payment(qid, 7)["status"] == "CONFIRMADO"
    output = capsys.readouterr().out
    assert "approved" in output and "fake" in output
    assert "Authorization" not in output


def test_cli_reconcile_uses_provider(cli_env, billing, generate, monkeypatch):
    import billing_service.cli as cli

    _, pid, _ = requested(billing, generate)

    class Provider:
        def observe(self, resource):
            return Observation("verified-test-payment", pid, 20000, "BRL", "approved")

    monkeypatch.setattr(cli, "FakeProvider", Provider)
    invoke(monkeypatch, ["reconcile", "--payment-id", pid])
    with cli_env.transaction() as u:
        assert u.get_payment(pid).status == "CONFIRMADO"


def test_cli_sqs_modes_and_once_error(cli_env, generate, monkeypatch):
    import billing_service.cli as cli

    class SQS:
        sends = []

        def receive_message(self, **kwargs):
            return {"Messages": [{"Body": json.dumps(generate), "ReceiptHandle": "receipt"}]}

        def delete_message(self, **kwargs):
            pass

        def send_message(self, **kwargs):
            self.sends.append(kwargs)

    sqs = SQS()
    monkeypatch.setattr(cli, "sqs_client", lambda _: sqs)
    monkeypatch.setenv("QUEUE_BILLING_COMANDOS_URL", "http://localhost:4566/commands.fifo")
    monkeypatch.setenv("QUEUE_OS_SAGA_RESPOSTAS_URL", "http://localhost:4566/responses.fifo")
    invoke(monkeypatch, ["consume", "--once"])
    invoke(monkeypatch, ["relay", "--once"])
    assert len(sqs.sends) == 1

    def fail(*args):
        raise RuntimeError("must not be logged")

    monkeypatch.setattr(cli, "relay_once", fail)
    with pytest.raises(SystemExit) as exc:
        invoke(monkeypatch, ["relay", "--once"])
    assert exc.value.code == 1


@pytest.mark.parametrize(
    "args",
    [["handle-file"], ["simulate-payment"], ["simulate-payment", "--payment-id", str(uuid4())]],
)
def test_cli_rejects_missing_operator_arguments(cli_env, monkeypatch, args):
    with pytest.raises(SystemExit) as exc:
        invoke(monkeypatch, args)
    assert exc.value.code == 2
