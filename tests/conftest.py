import base64
import os
from datetime import UTC, datetime, timedelta
from uuid import uuid4

import jwt
import pytest
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa

from billing_service.database import Base, Database
from billing_service.service import Billing


@pytest.fixture
def db(tmp_path):
    url = os.environ.get("TEST_DATABASE_URL", f"sqlite:///{tmp_path}/billing.db")
    store = Database(url)
    Base.metadata.drop_all(store.engine)
    Base.metadata.create_all(store.engine)
    yield store
    store.engine.dispose()


@pytest.fixture
def billing(db):
    return Billing(db, {"servico:12": 15000, "peca:40": 2500})


@pytest.fixture
def generate():
    return message(
        "GerarOrcamento",
        {
            "clienteId": 7,
            "veiculoId": 15,
            "servicos": [{"servicoId": 12, "quantidade": 1}],
            "pecas": [{"pecaId": 40, "quantidade": 2}],
        },
    )


def message(kind, payload, source=None):
    return {
        "messageId": str(uuid4()),
        "type": kind,
        "version": 1,
        "sagaId": source["sagaId"] if source else str(uuid4()),
        "osId": 101,
        "causationId": str(uuid4()) if source else None,
        "requestId": source["requestId"] if source else "req-demo-101",
        "occurredAt": datetime.now(UTC).isoformat(),
        "payload": payload,
    }


@pytest.fixture(scope="session")
def keypair():
    private = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    public = private.public_key().public_bytes(
        serialization.Encoding.PEM, serialization.PublicFormat.SubjectPublicKeyInfo
    )
    return private, base64.b64encode(public).decode()


@pytest.fixture
def token(keypair):
    def issue(client_id=7, **changes):
        now = datetime.now(UTC)
        payload = {
            "iss": "oficina-auth",
            "aud": "oficina-api",
            "sub": f"cliente:{client_id}",
            "cliente_id": client_id,
            "principal_type": "cliente",
            "token_type": "access",
            "iat": int(now.timestamp()),
            "exp": int((now + timedelta(minutes=15)).timestamp()),
            "jti": str(uuid4()),
            **changes,
        }
        return jwt.encode(payload, keypair[0], algorithm="RS256")

    return issue
