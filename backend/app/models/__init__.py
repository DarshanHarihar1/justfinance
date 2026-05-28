"""Model registry — import side-effects register each table on ``Base.metadata``.

Importing this package once at startup is enough; downstream code can then do
``from app.models import Transaction`` etc.
"""
from .base import Base, CreatedAtMixin, TimestampMixin
from .category import Category
from .merchant_mapping import MerchantMapping
from .statement import Statement
from .transaction import Transaction

__all__ = [
    "Base",
    "Category",
    "CreatedAtMixin",
    "MerchantMapping",
    "Statement",
    "TimestampMixin",
    "Transaction",
]
