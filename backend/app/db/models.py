import uuid
from datetime import date, datetime
from decimal import Decimal
from sqlalchemy import (
    Boolean, CheckConstraint, Date, DateTime, ForeignKey, Index, Integer,
    Numeric, String, Text, func,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


class Account(Base):
    __tablename__ = "accounts"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String, nullable=False)
    bank: Mapped[str] = mapped_column(String, nullable=False)  # "partners" | "generic"
    iban: Mapped[str | None] = mapped_column(String, nullable=True)
    currency: Mapped[str] = mapped_column(String, nullable=False, default="CZK")
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    transactions: Mapped[list["Transaction"]] = relationship(back_populates="account")
    import_batches: Mapped[list["ImportBatch"]] = relationship(back_populates="account")


class ImportBatch(Base):
    __tablename__ = "import_batches"
    __table_args__ = (
        CheckConstraint("status IN ('processing', 'completed', 'failed')", name="ck_import_batch_status"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    account_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("accounts.id"), nullable=False)
    filename: Mapped[str] = mapped_column(String, nullable=False)
    parser_used: Mapped[str] = mapped_column(String, nullable=False)
    column_mapping: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    row_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    imported_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    duplicate_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    status: Mapped[str] = mapped_column(String, nullable=False, default="processing")  # processing | completed | failed
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    imported_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    account: Mapped["Account"] = relationship(back_populates="import_batches")
    transactions: Mapped[list["Transaction"]] = relationship(back_populates="import_batch")


class Transaction(Base):
    __tablename__ = "transactions"
    __table_args__ = (
        Index("ix_transactions_account_booking", "account_id", "booking_date"),
        Index("ix_transactions_category_booking", "category_id", "booking_date"),
        Index("ix_transactions_is_transfer", "is_transfer"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    account_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("accounts.id"), nullable=False)
    import_batch_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("import_batches.id"), nullable=False)
    booking_date: Mapped[date] = mapped_column(Date, nullable=False)
    value_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    amount: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False)
    currency: Mapped[str] = mapped_column(String, nullable=False, default="CZK")
    counterparty_name: Mapped[str | None] = mapped_column(Text, nullable=True)
    counterparty_account: Mapped[str | None] = mapped_column(Text, nullable=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    raw_reference: Mapped[str | None] = mapped_column(Text, nullable=True)
    # TODO(M2): Add ForeignKey("categories.id") here and generate an Alembic migration
    # to add the FK constraint once the categories table is created in M2.
    category_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    categorization_source: Mapped[str | None] = mapped_column(String, nullable=True)  # rule | llm | manual
    confidence: Mapped[Decimal | None] = mapped_column(Numeric(3, 2), nullable=True)
    is_transfer: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    transfer_pair_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    hash_key: Mapped[str] = mapped_column(String, nullable=False, unique=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    account: Mapped["Account"] = relationship(back_populates="transactions")
    import_batch: Mapped["ImportBatch"] = relationship(back_populates="transactions")
