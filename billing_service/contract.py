"""Offline JSON Schema validation against unmodified, pinned group contracts."""

import hashlib
import json
from pathlib import Path
from uuid import NAMESPACE_URL, uuid5

from jsonschema import Draft7Validator, FormatChecker
from referencing import Registry, Resource

from billing_service.domain import BillingError

ROOT = Path(__file__).parent / "contracts" / "schemas"
SCHEMAS = [json.loads(p.read_text()) for p in ROOT.rglob("*.json")]
REGISTRY = Registry().with_resources((s["$id"], Resource.from_contents(s)) for s in SCHEMAS)
VALIDATORS = {
    s["title"]: Draft7Validator(s, registry=REGISTRY, format_checker=FormatChecker())
    for s in SCHEMAS
    if s.get("title")
}
COMMANDS = {"GerarOrcamento", "CancelarOrcamento", "SolicitarPagamento", "EstornarPagamento"}


def validate(message: dict, *, command: bool = False) -> None:
    kind = message.get("type") if isinstance(message, dict) else None
    if kind not in VALIDATORS or (command and kind not in COMMANDS):
        raise BillingError("MENSAGEM_INVALIDA", "Tipo de mensagem não suportado.", 422)
    if next(VALIDATORS[kind].iter_errors(message), None) is not None:
        raise BillingError(
            "MENSAGEM_INVALIDA", "Mensagem não corresponde ao contrato da Saga.", 422
        )


def digest(message: dict) -> str:
    return hashlib.sha256(
        json.dumps(message, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()


def stable_id(value: str) -> str:
    return str(uuid5(NAMESPACE_URL, f"oficina-billing:{value}"))


def response(source: dict, kind: str, payload: dict, now: str) -> dict:
    result = {
        **{k: source[k] for k in ["sagaId", "osId", "requestId"]},
        "messageId": stable_id(f"{source['messageId']}:{kind}"),
        "type": kind,
        "version": 1,
        "causationId": source["messageId"],
        "occurredAt": now,
        "payload": payload,
    }
    validate(result)
    return result
