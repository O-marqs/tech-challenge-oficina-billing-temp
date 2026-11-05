"""Deterministic Billing demonstration, not OS/Execution or Mercado Pago integration."""

import base64
import json
import os
import tempfile
from datetime import UTC, datetime, timedelta
from uuid import uuid4

import jwt
from alembic import command
from alembic.config import Config
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from fastapi.testclient import TestClient
from sqlalchemy import select

from billing_service import contract
from billing_service.api import create_app
from billing_service.config import Settings
from billing_service.database import Database, OutboxRow
from billing_service.domain import Observation
from billing_service.providers import FakeProvider
from billing_service.workers import operation_once


def main():
    with tempfile.TemporaryDirectory(prefix="billing-demo-") as folder:
        url = f"sqlite:///{folder}/billing.db"
        os.environ["DATABASE_URL"] = url
        command.upgrade(Config("alembic.ini"), "head")
        private = rsa.generate_private_key(public_exponent=65537, key_size=2048)
        public = private.public_key().public_bytes(
            serialization.Encoding.PEM, serialization.PublicFormat.SubjectPublicKeyInfo
        )
        cfg = Settings(
            database_url=url,
            payment_provider="fake",
            app_env="development",
            auth_jwt_public_key_b64=base64.b64encode(public).decode(),
        )
        db = Database(url)
        app = create_app(cfg, database=db)
        billing = app.state.billing
        now = datetime.now(UTC)
        token = jwt.encode(
            {
                "iss": "oficina-auth",
                "aud": "oficina-api",
                "sub": "cliente:7",
                "cliente_id": 7,
                "principal_type": "cliente",
                "token_type": "access",
                "iat": int(now.timestamp()),
                "exp": int((now + timedelta(minutes=15)).timestamp()),
                "jti": str(uuid4()),
            },
            private,
            algorithm="RS256",
        )
        source = {
            "messageId": str(uuid4()),
            "type": "GerarOrcamento",
            "version": 1,
            "sagaId": str(uuid4()),
            "osId": 101,
            "causationId": None,
            "requestId": "req-demo-local",
            "occurredAt": now.isoformat(),
            "payload": {
                "clienteId": 7,
                "veiculoId": 15,
                "servicos": [{"servicoId": 12, "quantidade": 1}],
                "pecas": [{"pecaId": 40, "quantidade": 2}],
            },
        }
        billing.handle(source)
        qid = contract.stable_id(f"quote:{source['sagaId']}")
        with TestClient(app) as client:
            result = client.post(
                f"/api/v1/orcamentos/{qid}/aprovar", headers={"Authorization": f"Bearer {token}"}
            )
            assert result.status_code == 202, result.json()

        def send(kind, payload):
            billing.handle(
                {
                    **source,
                    "messageId": str(uuid4()),
                    "causationId": source["messageId"],
                    "type": kind,
                    "payload": payload,
                }
            )

        send("SolicitarPagamento", {"orcamentoId": qid, "valorTotalCentavos": 20000})
        operation_once(db, FakeProvider())
        pid = billing.payment(qid, 7)["pagamentoId"]
        assert billing.payment(qid, 7)["status"] == "AGUARDANDO_PAGAMENTO"
        billing.observe(pid, Observation("FAKE-DEMO-PAYMENT", pid, 20000, "BRL", "approved"))
        send("EstornarPagamento", {"pagamentoId": pid, "motivo": "EXECUCAO_FALHOU"})
        operation_once(db, FakeProvider())
        send("CancelarOrcamento", {"orcamentoId": qid, "motivo": "EXECUCAO_FALHOU"})
        with db.transaction() as u:
            types = [
                row.message["type"]
                for row in u.s.scalars(select(OutboxRow).order_by(OutboxRow.sequence))
            ]
        assert billing.quote(qid, 7)["status"] == "CANCELADO"
        print(
            json.dumps(
                {
                    "demonstracao": "Billing isolado",
                    "provedor": "FAKE EXPLICITO",
                    "totalCentavos": 20000,
                    "eventos": types,
                    "status": "PASS",
                    "integracaoMercadoPagoReal": False,
                    "stackCompletaDoGrupo": False,
                },
                ensure_ascii=False,
            )
        )


if __name__ == "__main__":
    main()
