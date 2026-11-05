"""SQL adapter. Each transaction owns locks, inbox, state and outbox together."""

from contextlib import contextmanager
from dataclasses import asdict
from pathlib import Path

from sqlalchemy import (
    JSON,
    Boolean,
    DateTime,
    ForeignKey,
    Integer,
    String,
    create_engine,
    event,
    exists,
    select,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, Session, aliased, mapped_column

from billing_service.domain import Operation, Payment, Quote, instant


class Base(DeclarativeBase):
    pass


class QuoteRow(Base):
    __tablename__ = "quotes"
    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    saga_id: Mapped[str] = mapped_column(String(36), unique=True)
    data: Mapped[dict] = mapped_column(JSON)


class PaymentRow(Base):
    __tablename__ = "payments"
    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    quote_id: Mapped[str] = mapped_column(ForeignKey("quotes.id"), unique=True)
    data: Mapped[dict] = mapped_column(JSON)


class InboxRow(Base):
    __tablename__ = "inbox"
    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    digest: Mapped[str] = mapped_column(String(64))


class OutboxRow(Base):
    __tablename__ = "outbox"
    sequence: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    message_id: Mapped[str] = mapped_column(String(36), unique=True)
    saga_id: Mapped[str] = mapped_column(String(36), index=True)
    message: Mapped[dict] = mapped_column(JSON)
    attributes: Mapped[dict] = mapped_column(JSON)
    published: Mapped[bool] = mapped_column(Boolean, default=False, index=True)


class OperationRow(Base):
    __tablename__ = "provider_operations"
    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    status: Mapped[str] = mapped_column(String(32), index=True)
    available_at: Mapped[object] = mapped_column(DateTime(timezone=True), index=True)
    data: Mapped[dict] = mapped_column(JSON)


class SQLUnitOfWork:
    def __init__(self, session: Session):
        self.s = session

    def get_quote(self, quote_id: str) -> Quote | None:
        row = self.s.scalar(select(QuoteRow).where(QuoteRow.id == quote_id).with_for_update())
        return Quote(**row.data) if row else None

    def quote_for_saga(self, saga_id: str) -> Quote | None:
        row = self.s.scalar(select(QuoteRow).where(QuoteRow.saga_id == saga_id).with_for_update())
        return Quote(**row.data) if row else None

    def save_quote(self, quote: Quote) -> None:
        self.s.merge(QuoteRow(id=quote.id, saga_id=quote.saga_id, data=asdict(quote)))
        self.s.flush()

    def get_payment(self, payment_id: str, *, lock: bool = True) -> Payment | None:
        query = select(PaymentRow).where(PaymentRow.id == payment_id)
        row = self.s.scalar(query.with_for_update() if lock else query)
        return Payment(**row.data) if row else None

    def payment_for_quote(self, quote_id: str) -> Payment | None:
        row = self.s.scalar(
            select(PaymentRow).where(PaymentRow.quote_id == quote_id).with_for_update()
        )
        return Payment(**row.data) if row else None

    def save_payment(self, payment: Payment) -> None:
        self.s.merge(PaymentRow(id=payment.id, quote_id=payment.quote_id, data=asdict(payment)))
        self.s.flush()

    def inbox_hash(self, message_id: str) -> str | None:
        row = self.s.get(InboxRow, message_id)
        return row.digest if row else None

    def add_inbox(self, message_id: str, digest: str) -> None:
        self.s.add(InboxRow(id=message_id, digest=digest))
        self.s.flush()

    def enqueue(self, message: dict, attributes: dict) -> None:
        self.s.add(
            OutboxRow(
                message_id=message["messageId"],
                saga_id=message["sagaId"],
                message=message,
                attributes=attributes,
                published=False,
            )
        )
        self.s.flush()

    def save_operation(self, operation: Operation) -> None:
        self.s.merge(
            OperationRow(
                id=operation.id,
                status=operation.status,
                available_at=instant(operation.available_at),
                data=asdict(operation),
            )
        )
        self.s.flush()

    def pending_operation(self, now: str) -> Operation | None:
        row = self.s.scalar(
            select(OperationRow)
            .where(
                OperationRow.status.in_(["PENDENTE", "DESCONHECIDO"]),
                OperationRow.available_at <= instant(now),
            )
            .order_by(OperationRow.available_at, OperationRow.id)
            .with_for_update(skip_locked=True)
            .limit(1)
        )
        return Operation(**row.data) if row else None

    def pending_event(self) -> tuple[int, dict, dict] | None:
        previous = aliased(OutboxRow)
        row = self.s.scalar(
            select(OutboxRow)
            .where(
                OutboxRow.published.is_(False),
                ~exists().where(
                    previous.saga_id == OutboxRow.saga_id,
                    previous.sequence < OutboxRow.sequence,
                    previous.published.is_(False),
                ),
            )
            .order_by(OutboxRow.sequence)
            .with_for_update(skip_locked=True)
            .limit(1)
        )
        return (row.sequence, row.message, row.attributes) if row else None

    def mark_published(self, sequence: int) -> None:
        row = self.s.get(OutboxRow, sequence)
        row.published = True


class Database:
    def __init__(self, url: str):
        if url.startswith("postgresql://"):
            url = url.replace("postgresql://", "postgresql+psycopg://", 1)
        sqlite = url.startswith("sqlite")
        if sqlite and "///" in url and not url.endswith(":memory:"):
            Path(url.split("///", 1)[1]).parent.mkdir(parents=True, exist_ok=True)
        self.engine = create_engine(
            url,
            pool_pre_ping=True,
            connect_args={"check_same_thread": False, "timeout": 15} if sqlite else {},
        )
        self.sqlite = sqlite
        if sqlite:

            @event.listens_for(self.engine, "connect")
            def configure(connection, _):
                connection.execute("PRAGMA foreign_keys=ON")
                connection.execute("PRAGMA busy_timeout=15000")

    @contextmanager
    def transaction(self):
        with Session(self.engine) as session, session.begin():
            if self.sqlite:
                session.connection().exec_driver_sql("BEGIN IMMEDIATE")
            yield SQLUnitOfWork(session)

    def ready(self) -> bool:
        with Session(self.engine) as session:
            session.execute(select(QuoteRow.id).limit(1))
            session.execute(select(OperationRow.id).limit(1))
        return True
