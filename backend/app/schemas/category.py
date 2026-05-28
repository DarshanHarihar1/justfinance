from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class CategoryOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    color: str
    icon: str
    is_system: bool
    excluded_from_spending: bool
    sort_order: int
    mapping_count: int = 0


class CategoryCreate(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    color: str = "#9E9E9E"
    icon: str = "📦"
    excluded_from_spending: bool = False
    sort_order: int = 100


class CategoryPatch(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=100)
    color: str | None = None
    icon: str | None = None
    excluded_from_spending: bool | None = None
    sort_order: int | None = None
