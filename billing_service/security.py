"""Client JWT verification and provider signature validation; secrets never logged."""

import base64
import hashlib
import hmac
import re
import time
from uuid import UUID

import jwt

from billing_service.domain import BillingError

REQUIRED = ["iss", "aud", "sub", "cliente_id", "principal_type", "token_type", "iat", "exp", "jti"]


def client_identity(authorization: str | None, public_key_b64: str) -> int:
    if not authorization or not authorization.startswith("Bearer "):
        raise BillingError("TOKEN_INVALIDO", "JWT obrigatório.", 401)
    if not public_key_b64:
        raise BillingError(
            "AUTH_INDISPONIVEL", "Chave pública de autenticação não configurada.", 503
        )
    try:
        key = base64.b64decode(public_key_b64, validate=True)
        claims = jwt.decode(
            authorization[7:],
            key,
            algorithms=["RS256"],
            issuer="oficina-auth",
            audience="oficina-api",
            options={"require": REQUIRED},
        )
        cid = claims["cliente_id"]
        if type(cid) is not int or cid <= 0 or claims["sub"] != f"cliente:{cid}":
            raise ValueError("Invalid client")
        if claims["principal_type"] != "cliente" or claims["token_type"] != "access":
            raise ValueError("Invalid principal")
        if type(claims["iat"]) is not int or type(claims["exp"]) is not int:
            raise ValueError("Invalid date")
        if claims["exp"] <= claims["iat"] or UUID(claims["jti"]).version != 4:
            raise ValueError("Invalid claims")
        if {"cpf", "documento", "nome", "email", "created_by_id"}.intersection(claims):
            raise ValueError("Unexpected personal data")
        return cid
    except (jwt.PyJWTError, ValueError, TypeError, KeyError):
        raise BillingError("TOKEN_INVALIDO", "JWT inválido ou expirado.", 401) from None


def verify_webhook(
    signature: str, request_id: str, resource_id: str, secret: str, now: float | None = None
) -> None:
    try:
        if not secret or not request_id or not re.fullmatch(r"[A-Za-z0-9_-]{1,64}", resource_id):
            raise ValueError("Missing signature data")
        parts = dict(part.strip().split("=", 1) for part in signature.split(","))
        ts, actual = parts["ts"], parts["v1"]
        stamp = int(ts)
        stamp_seconds = stamp / 1000 if len(ts) > 10 else stamp
        if abs((time.time() if now is None else now) - stamp_seconds) > 300:
            raise ValueError("Stale timestamp")
        manifest = f"id:{resource_id.lower()};request-id:{request_id};ts:{ts};"
        expected = hmac.new(secret.encode(), manifest.encode(), hashlib.sha256).hexdigest()
        if not hmac.compare_digest(expected, actual):
            raise ValueError("Invalid signature")
    except (ValueError, KeyError, TypeError):
        raise BillingError(
            "ASSINATURA_INVALIDA", "Assinatura de notificação inválida.", 401
        ) from None
