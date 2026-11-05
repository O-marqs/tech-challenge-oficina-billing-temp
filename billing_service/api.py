"""HTTP boundary. No anonymous business routes or fake-payment confirmation endpoint."""

import logging
from typing import Annotated, Literal
from uuid import UUID

from fastapi import Depends, FastAPI, Header, Query, Request
from fastapi import Path as APIPath
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel, ConfigDict, Field

from billing_service.config import Settings
from billing_service.database import Database
from billing_service.domain import BillingError
from billing_service.providers import FakeProvider, MercadoPagoOrders
from billing_service.security import client_identity, verify_webhook
from billing_service.service import Billing
from billing_service.transport import trace_attributes

LOG = logging.getLogger("billing")


class ApprovalResult(BaseModel):
    orcamentoId: UUID
    osId: int
    sagaId: UUID
    aprovadoEm: str


class Decline(BaseModel):
    model_config = ConfigDict(extra="forbid")
    motivo: str | None = Field(default=None, max_length=500)


class Webhook(BaseModel):
    type: Literal["order"]
    data: dict[str, str]
    live_mode: bool = Field(default=False, strict=True)


def create_app(settings: Settings | None = None, *, database=None, provider=None) -> FastAPI:
    cfg = settings or Settings()
    db = database or Database(cfg.database_url)
    billing = Billing(db, cfg.prices(), cfg.quote_valid_minutes)
    gateway = provider or (
        FakeProvider()
        if cfg.payment_provider == "fake"
        else MercadoPagoOrders(cfg.mercado_pago_access_token.get_secret_value())
    )
    app = FastAPI(
        title="Oficina Billing",
        version="0.1.0",
        description=(
            "Participante da Saga da OS. Aprovação e consultas exigem JWT RS256 do Auth. "
            "Provider fake é demonstração explícita; não comprova integração financeira real."
        ),
    )
    app.state.billing, app.state.database, app.state.provider, app.state.settings = (
        billing,
        db,
        gateway,
        cfg,
    )

    @app.exception_handler(BillingError)
    async def billing_error(_, exc: BillingError):
        return JSONResponse(
            status_code=exc.status,
            content={"codigo": exc.code, "mensagem": exc.message},
            headers={"WWW-Authenticate": "Bearer"} if exc.status == 401 else None,
        )

    @app.exception_handler(RequestValidationError)
    async def validation_error(_, __):
        return JSONResponse(
            status_code=422,
            content={"codigo": "REQUISICAO_INVALIDA", "mensagem": "Parâmetros inválidos."},
        )

    @app.middleware("http")
    async def safe_logs(request: Request, call_next):
        result = await call_next(request)
        LOG.info("http_request", extra={"method": request.method, "status": result.status_code})
        return result

    bearer = HTTPBearer(auto_error=False)

    def actor(
        credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer)] = None,
    ) -> int:
        authorization = f"Bearer {credentials.credentials}" if credentials else None
        return client_identity(authorization, cfg.auth_jwt_public_key_b64)

    @app.get("/health/live/", tags=["health"])
    def live():
        return {"status": "ok", "provider": cfg.payment_provider}

    @app.get("/health/ready/", tags=["health"])
    def ready():
        try:
            if db.ready():
                return {"status": "ready"}
        except Exception:
            LOG.warning("database_not_ready")
        return JSONResponse(status_code=503, content={"status": "not_ready"})

    @app.get("/api/v1/orcamentos/{id}", tags=["orcamento"])
    def quote(qid: Annotated[UUID, APIPath(alias="id")], client_id: Annotated[int, Depends(actor)]):
        return billing.quote(str(qid), client_id)

    @app.post(
        "/api/v1/orcamentos/{id}/aprovar",
        status_code=202,
        response_model=ApprovalResult,
        responses={
            401: {"description": "JWT inválido"},
            403: {"description": "Outro cliente"},
            404: {"description": "Orçamento não encontrado"},
            409: {"description": "Orçamento indisponível"},
        },
        tags=["orcamento"],
    )
    def approve(
        qid: Annotated[UUID, APIPath(alias="id")],
        request: Request,
        client_id: Annotated[int, Depends(actor)],
    ):
        return billing.decide(
            str(qid), client_id, True, attributes=trace_attributes(request.headers)
        )

    @app.post("/api/v1/orcamentos/{id}/recusar", status_code=202, tags=["orcamento"])
    def decline(
        qid: Annotated[UUID, APIPath(alias="id")],
        body: Decline,
        client_id: Annotated[int, Depends(actor)],
    ):
        return billing.decide(str(qid), client_id, False, body.motivo)

    @app.get("/api/v1/orcamentos/{id}/pagamento", tags=["pagamento"])
    def payment(
        qid: Annotated[UUID, APIPath(alias="id")], client_id: Annotated[int, Depends(actor)]
    ):
        return {**billing.payment(str(qid), client_id), "provedor": cfg.payment_provider}

    @app.post("/api/v1/webhooks/mercado-pago", tags=["webhook"])
    def webhook(
        body: Webhook,
        resource_id: Annotated[str, Query(alias="data.id")],
        x_signature: Annotated[str, Header()] = "",
        x_request_id: Annotated[str, Header()] = "",
    ):
        if cfg.payment_provider != "mercadopago_test":
            raise BillingError("WEBHOOK_DESABILITADO", "Webhook não habilitado neste modo.", 404)
        verify_webhook(
            x_signature,
            x_request_id,
            resource_id,
            cfg.mercado_pago_webhook_secret.get_secret_value(),
        )
        if body.live_mode or body.data.get("id") != resource_id:
            raise BillingError(
                "NOTIFICACAO_DIVERGENTE", "Notificação não pertence ao ambiente de testes.", 422
            )
        try:
            observation = gateway.observe(resource_id)
            billing.observe(observation.external_reference, observation)
        except BillingError:
            raise
        except Exception:
            raise BillingError(
                "PROVEDOR_INDISPONIVEL", "Não foi possível verificar o pagamento.", 503
            ) from None
        return {"status": "ok"}

    return app


app = create_app()
