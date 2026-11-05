import base64
import hashlib
import hmac
import time
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from billing_service.api import create_app
from billing_service.config import Settings
from billing_service.domain import BillingError, Observation
from billing_service.security import client_identity, verify_webhook
from tests.test_billing import generated, requested


def test_api_approval_ownership_health_and_openapi(db, billing, generate, token, keypair):
    app = create_app(Settings(auth_jwt_public_key_b64=keypair[1]), database=db)
    qid = generated(billing, generate)
    with TestClient(app) as client:
        assert client.get("/health/live/").status_code == 200
        assert client.get("/health/ready/").status_code == 200
        url = f"/api/v1/orcamentos/{qid}"
        assert client.get(url).status_code == 401
        assert client.get(url, headers={"Authorization": f"Bearer {token(8)}"}).status_code == 403
        auth = {"Authorization": f"Bearer {token()}"}
        assert client.get(url, headers=auth).json()["valorTotalCentavos"] == 20000
        assert client.get(url + "/pagamento", headers=auth).status_code == 404
        result = client.post(url + "/aprovar", headers=auth)
        assert result.status_code == 202
        assert set(result.json()) == {"orcamentoId", "osId", "sagaId", "aprovadoEm"}
        assert client.post(url + "/aprovar", headers=auth).status_code == 409
        assert client.get("/api/v1/orcamentos/not-uuid", headers=auth).status_code == 422
        schema = client.get("/openapi.json").json()
        assert "HTTPBearer" in schema["components"]["securitySchemes"]
        assert "/api/v1/orcamentos/{id}/aprovar" in schema["paths"]
        assert client.get("/docs").status_code == 200


def test_api_decline_and_readiness_without_schema(tmp_path, billing, db, generate, token, keypair):
    from billing_service.database import Database

    empty = Database(f"sqlite:///{tmp_path}/empty.db")
    with TestClient(create_app(Settings(), database=empty)) as client:
        assert client.get("/health/ready/").status_code == 503
    qid = generated(billing, generate)
    with TestClient(
        create_app(Settings(auth_jwt_public_key_b64=keypair[1]), database=db)
    ) as client:
        result = client.post(
            f"/api/v1/orcamentos/{qid}/recusar",
            json={"motivo": "Recusa"},
            headers={"Authorization": f"Bearer {token()}"},
        )
        assert result.status_code == 202


@pytest.mark.parametrize(
    "claims",
    [
        dict(aud="other"),
        dict(iss="other"),
        dict(sub="cliente:8"),
        dict(principal_type="staff"),
        dict(token_type="refresh"),
        dict(cliente_id=True),
        dict(cliente_id=-1),
        dict(jti="bad"),
        dict(exp=1),
        dict(iat=9999999999),
        dict(cpf="synthetic"),
        dict(iat=True),
    ],
)
def test_jwt_rejects_invalid_claims(token, keypair, claims):
    with pytest.raises(BillingError) as exc:
        client_identity("Bearer " + token(**claims), keypair[1])
    assert exc.value.status == 401


def test_jwt_requires_valid_signature_and_config(token, keypair):
    assert client_identity("Bearer " + token(), keypair[1]) == 7
    for value in [None, "Basic abc", "Bearer bad", "Bearer " + token()[:-8] + "ABCDEFGH"]:
        with pytest.raises(BillingError):
            client_identity(value, keypair[1])
    with pytest.raises(BillingError) as exc:
        client_identity("Bearer " + token(), "")
    assert exc.value.status == 503
    with pytest.raises(BillingError):
        client_identity("Bearer " + token(), base64.b64encode(b"invalid-key").decode())


def signature(resource, request_id, secret, ts):
    manifest = f"id:{resource.lower()};request-id:{request_id};ts:{ts};"
    signed = hmac.new(secret.encode(), manifest.encode(), hashlib.sha256).hexdigest()
    return f"ts={ts},v1={signed}"


def test_signature_is_bound_to_id_request_and_timestamp():
    secret, rid, req, ts = "test-secret", "ORDTSTABC", str(uuid4()), str(int(time.time()))
    signed = signature(rid, req, secret, ts)
    verify_webhook(signed, req, rid, secret)
    for arguments in [
        (signed, req, rid + "OTHER", secret),
        (signed, "other", rid, secret),
        (signed, req, rid, "bad-secret"),
        ("bad", req, rid, secret),
    ]:
        with pytest.raises(BillingError):
            verify_webhook(*arguments)
    with pytest.raises(BillingError):
        verify_webhook(signed, req, rid, secret, now=time.time() + 1000)


def test_webhook_uses_verified_provider_observation(db, billing, generate):
    _, pid, _ = requested(billing, generate)

    class Provider:
        calls = 0

        def observe(self, resource):
            self.calls += 1
            return Observation("PAYTEST", pid, 20000, "BRL", "approved")

    gateway = Provider()
    cfg = Settings(
        payment_provider="mercadopago_test",
        mercado_pago_access_token="test-token",
        mercado_pago_webhook_secret="test-secret",
        mercado_pago_notification_url="https://example.invalid/hook",
        mercado_pago_return_url="https://example.invalid/return",
    )
    app = create_app(cfg, database=db, provider=gateway)
    rid, req, ts = "ORDTSTABC", str(uuid4()), str(int(time.time()))
    headers = {"x-signature": signature(rid, req, "test-secret", ts), "x-request-id": req}
    url = f"/api/v1/webhooks/mercado-pago?data.id={rid}"
    body = {"type": "order", "data": {"id": rid}, "live_mode": False}
    with TestClient(app) as client:
        assert client.post(url, json=body).status_code == 401
        assert gateway.calls == 0
        assert client.post(url, json=body, headers=headers).status_code == 200
        assert client.post(url, json=body, headers=headers).status_code == 200
        assert (
            client.post(url, json={**body, "live_mode": True}, headers=headers).status_code == 422
        )
    with db.transaction() as u:
        assert u.get_payment(pid).status == "CONFIRMADO"


def test_fake_webhook_is_disabled(db):
    with TestClient(create_app(Settings(), database=db)) as client:
        result = client.post(
            "/api/v1/webhooks/mercado-pago?data.id=ORDTSTABC",
            json={"type": "order", "data": {"id": "ORDTSTABC"}},
        )
        assert result.status_code == 404


@pytest.mark.parametrize(
    "settings",
    [
        dict(app_env="production"),
        dict(quote_valid_minutes=0),
        dict(payment_provider="mercadopago_test"),
    ],
)
def test_unsafe_configuration_is_rejected(settings):
    with pytest.raises(ValueError):
        Settings(**settings)
