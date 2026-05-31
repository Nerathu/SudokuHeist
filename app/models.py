"""Pydantic API schemas."""

from __future__ import annotations

from pydantic import BaseModel, Field


class CellPlaceRequest(BaseModel):
    row: int = Field(ge=0, le=8)
    col: int = Field(ge=0, le=8)
    value: int = Field(ge=1, le=9)


class CellClearRequest(BaseModel):
    row: int = Field(ge=0, le=8)
    col: int = Field(ge=0, le=8)


class ShopBuyRequest(BaseModel):
    item_id: str
    kind: str = Field(pattern="^(trick|kniff)$")


class MetaBuyRequest(BaseModel):
    upgrade_id: str


class BoostRequest(BaseModel):
    boost_id: str
    row: int | None = Field(default=None, ge=0, le=8)
    col: int | None = Field(default=None, ge=0, le=8)


class NewRunRequest(BaseModel):
    seed: int | None = None
