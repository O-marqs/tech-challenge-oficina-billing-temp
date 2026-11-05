"""Billing-only smoke against localhost containers, real Postgres and emulated SQS.

The explicit fake observation is performed via the development CLI, never an HTTP backdoor.
"""

import json
import subprocess
import time
from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4

import boto3
import httpx

from billing_service import contract

TRACE = "00-" + "1" * 32 + "-" + "2" * 16 + "-01"


def main():
    sqs = boto3.client(
        "sqs",
        endpoint_url="http://localhost:4566",
        region_name="us-east-1",
        aws_access_key_id="test",
        aws_secret_access_key="test",
    )
    commands = sqs.get_queue_url(QueueName="oficina-billing-comandos.fifo")["QueueUrl"]
    replies = sqs.get_queue_url(QueueName="oficina-os-saga-respostas.fifo")["QueueUrl"]
    token = Path(".local/client-token.txt").read_text().strip()
    source = {
        "messageId": str(uuid4()),
        "type": "GerarOrcamento",
        "version": 1,
        "sagaId": str(uuid4()),
        "osId": 101,
        "causationId": None,
        "requestId": "req-smoke-" + uuid4().hex,
        "occurredAt": datetime.now(UTC).isoformat(),
        "payload": {
            "clienteId": 7,
            "veiculoId": 15,
            "servicos": [{"servicoId": 12, "quantidade": 1}],
            "pecas": [{"pecaId": 40, "quantidade": 2}],
        },
    }
    observed = []

    def send(kind, payload):
        msg = {
            **source,
            "type": kind,
            "payload": payload,
            "messageId": str(uuid4()),
            "causationId": source["messageId"],
        }
        contract.validate(msg, command=True)
        sqs.send_message(
            QueueUrl=commands,
            MessageBody=json.dumps(msg),
            MessageGroupId=source["sagaId"],
            MessageDeduplicationId=msg["messageId"],
            MessageAttributes={"traceparent": {"DataType": "String", "StringValue": TRACE}},
        )

    def wait_event(kind):
        deadline = time.monotonic() + 60
        while time.monotonic() < deadline:
            for item in sqs.receive_message(
                QueueUrl=replies, WaitTimeSeconds=1, MessageAttributeNames=["All"]
            ).get("Messages", []):
                msg = json.loads(item["Body"])
                if msg["sagaId"] == source["sagaId"]:
                    contract.validate(msg)
                    assert msg["requestId"] == source["requestId"]
                    assert item["MessageAttributes"]["traceparent"]["StringValue"] == TRACE
                    observed.append(msg["type"])
                    sqs.delete_message(QueueUrl=replies, ReceiptHandle=item["ReceiptHandle"])
                    if msg["type"] == kind:
                        return msg
            time.sleep(0.1)
        raise AssertionError(f"Timed out waiting for {kind}; received {observed}")

    with httpx.Client(base_url="http://localhost:8001", timeout=10) as api:
        assert api.get("/health/ready/").status_code == 200
        assert api.get("/health/live/").json()["provider"] == "fake"
        send("GerarOrcamento", source["payload"])
        generated = wait_event("OrcamentoGerado")
        qid = generated["payload"]["orcamentoId"]
        assert api.get(f"/api/v1/orcamentos/{qid}").status_code == 401
        api.headers["Authorization"] = f"Bearer {token}"
        assert api.get(f"/api/v1/orcamentos/{qid}").json()["valorTotalCentavos"] == 20000
        assert api.post(f"/api/v1/orcamentos/{qid}/aprovar").status_code == 202
        wait_event("OrcamentoAprovado")
        send("SolicitarPagamento", {"orcamentoId": qid, "valorTotalCentavos": 20000})
        deadline = time.monotonic() + 60
        payment = None
        while time.monotonic() < deadline:
            result = api.get(f"/api/v1/orcamentos/{qid}/pagamento")
            if result.status_code == 200 and result.json()["status"] == "AGUARDANDO_PAGAMENTO":
                payment = result.json()
                break
            time.sleep(0.5)
        assert payment, "Checkout worker did not produce a pending fake checkout"
        subprocess.run(
            [
                "docker",
                "compose",
                "exec",
                "-T",
                "operations",
                "python",
                "-m",
                "billing_service.cli",
                "simulate-payment",
                "--payment-id",
                payment["pagamentoId"],
            ],
            check=True,
            capture_output=True,
            text=True,
        )
        wait_event("PagamentoConfirmado")
        send(
            "EstornarPagamento",
            {"pagamentoId": payment["pagamentoId"], "motivo": "EXECUCAO_FALHOU"},
        )
        wait_event("PagamentoEstornado")
        send("CancelarOrcamento", {"orcamentoId": qid, "motivo": "EXECUCAO_FALHOU"})
        wait_event("OrcamentoCancelado")
        assert api.get(f"/api/v1/orcamentos/{qid}").json()["status"] == "CANCELADO"
    print(
        json.dumps(
            {
                "status": "PASS",
                "scope": "Billing containers only",
                "provider": "fake",
                "postgres": True,
                "sqs": "LocalStack",
                "events": observed,
                "realMercadoPago": False,
                "teamStack": False,
            }
        )
    )


if __name__ == "__main__":
    main()
