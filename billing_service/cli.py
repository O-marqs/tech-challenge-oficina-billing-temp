"""Operator commands. The fake observation command is deliberately CLI-only."""

import argparse
import json
import logging
import signal
from pathlib import Path
from threading import Event

from alembic import command
from alembic.config import Config

from billing_service.config import Settings
from billing_service.database import Database
from billing_service.domain import Observation
from billing_service.providers import FakeProvider, MercadoPagoOrders
from billing_service.service import Billing
from billing_service.transport import SQSConsumer, SQSPublisher, sqs_client
from billing_service.workers import operation_once, relay_once


class JsonLogs(logging.Formatter):
    def format(self, record):
        return json.dumps(
            {
                "event": record.getMessage(),
                "level": record.levelname,
                **{
                    k: getattr(record, k)
                    for k in ["code", "operation_id", "status", "method"]
                    if hasattr(record, k)
                },
            }
        )


def main():
    parser = argparse.ArgumentParser(description="Billing participant operations")
    parser.add_argument(
        "action",
        choices=[
            "migrate",
            "consume",
            "relay",
            "operations",
            "handle-file",
            "simulate-payment",
            "reconcile",
        ],
    )
    parser.add_argument("--once", action="store_true")
    parser.add_argument("--file", type=Path)
    parser.add_argument("--payment-id")
    parser.add_argument(
        "--outcome", choices=["approved", "rejected", "expired"], default="approved"
    )
    args = parser.parse_args()
    cfg = Settings()
    db = Database(cfg.database_url)
    handler = logging.StreamHandler()
    handler.setFormatter(JsonLogs())
    logging.getLogger("billing").addHandler(handler)
    logging.getLogger("billing").setLevel(logging.INFO)
    billing = Billing(db, cfg.prices(), cfg.quote_valid_minutes)
    provider = (
        FakeProvider()
        if cfg.payment_provider == "fake"
        else MercadoPagoOrders(
            cfg.mercado_pago_access_token.get_secret_value(), return_url=cfg.mercado_pago_return_url
        )
    )
    if args.action == "migrate":
        command.upgrade(Config("alembic.ini"), "head")
        return
    if args.action == "handle-file":
        if not args.file:
            parser.error("--file is required")
        print(billing.handle(json.loads(args.file.read_text())))
        return
    if args.action in ["simulate-payment", "reconcile"]:
        if not args.payment_id:
            parser.error("--payment-id is required")
        with db.transaction() as u:
            p = u.get_payment(args.payment_id)
        if not p:
            parser.error("Payment not found")
        if args.action == "simulate-payment":
            if cfg.app_env not in ["development", "test"] or cfg.payment_provider != "fake":
                parser.error("Simulation requires explicit development/test and fake provider")
            observation = Observation(f"FAKE-PAY-{p.id}", p.id, p.amount, "BRL", args.outcome)
        else:
            observation = provider.observe(p.order_id)
        billing.observe(p.id, observation)
        print(
            json.dumps(
                {
                    "paymentId": p.id,
                    "observation": observation.status,
                    "provider": cfg.payment_provider,
                }
            )
        )
        return
    if args.action == "consume":
        step = SQSConsumer(sqs_client(cfg), cfg.queue_billing_comandos_url, billing).once
    elif args.action == "relay":
        publisher = SQSPublisher(sqs_client(cfg), cfg.queue_os_saga_respostas_url)

        def step():
            return relay_once(db, publisher)
    else:

        def step():
            return operation_once(db, provider)

    stopped = Event()
    for sig in [signal.SIGTERM, signal.SIGINT]:
        signal.signal(sig, lambda *_: stopped.set())
    while not stopped.is_set():
        try:
            result = step()
            if args.once:
                print(json.dumps({"processed": result}))
                break
            if not result:
                stopped.wait(1)
        except Exception as exc:
            logging.getLogger("billing").warning("worker_retry", extra={"code": type(exc).__name__})
            if args.once:
                raise SystemExit(1) from None
            stopped.wait(2)


if __name__ == "__main__":
    main()
