from decimal import Decimal
from datetime import datetime

from sqlalchemy import BigInteger, CheckConstraint, DateTime, ForeignKey, Identity, Numeric, String, func
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


class Employee(Base):
    __tablename__ = "employees"

    id: Mapped[int] = mapped_column(BigInteger, Identity(), primary_key=True)
    telegram_id: Mapped[str] = mapped_column(String)
    name: Mapped[str] = mapped_column(String)


class Product(Base):
    __tablename__ = "products"
    __table_args__ = (CheckConstraint("kind IN ('component', 'product')"),)

    id: Mapped[int] = mapped_column(BigInteger, Identity(), primary_key=True)
    article: Mapped[str] = mapped_column(String)
    name: Mapped[str] = mapped_column(String)
    price: Mapped[Decimal] = mapped_column(Numeric)
    quantity: Mapped[int] = mapped_column(BigInteger, default=0, server_default="0")
    comment: Mapped[str] = mapped_column(String)
    kind: Mapped[str] = mapped_column(String, default="component", server_default="component")
    responsible: Mapped[str | None] = mapped_column(String)
    components: Mapped[list["ProductComponent"]] = relationship(
        foreign_keys="ProductComponent.product_id", cascade="all, delete-orphan",
    )


class ProductComponent(Base):
    __tablename__ = "product_components"
    __table_args__ = (
        CheckConstraint("quantity > 0"),
        CheckConstraint("product_id != component_id"),
    )

    product_id: Mapped[int] = mapped_column(
        ForeignKey("products.id", ondelete="CASCADE"), primary_key=True,
    )
    component_id: Mapped[int] = mapped_column(
        ForeignKey("products.id", ondelete="RESTRICT"), primary_key=True,
    )
    quantity: Mapped[int] = mapped_column(BigInteger)
    component: Mapped[Product] = relationship(foreign_keys=[component_id])


class Operation(Base):
    __tablename__ = "operations"

    id: Mapped[int] = mapped_column(BigInteger, Identity(), primary_key=True)
    product_id: Mapped[int] = mapped_column(ForeignKey("products.id", ondelete="RESTRICT"))
    product: Mapped[Product] = relationship()
    op_type: Mapped[str] = mapped_column(String)
    quantity: Mapped[int] = mapped_column(BigInteger)
    comment: Mapped[str] = mapped_column(String)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
