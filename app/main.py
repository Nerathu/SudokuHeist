"""FastAPI application entry point."""

from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter, FastAPI, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles

from app.config import BASE_PATH
from app.db import get_meta, init_db
from app.game import run as run_service
from app.models import BoostRequest, CellClearRequest, CellPlaceRequest, MetaBuyRequest, NewRunRequest, ShopBuyRequest

STATIC_DIR = Path(__file__).resolve().parent.parent / "static"
_INDEX_TEMPLATE = (STATIC_DIR / "index.html").read_text(encoding="utf-8")

app = FastAPI(title="SudokuHeist", version="1.0.0")
router = APIRouter(prefix=BASE_PATH or None)


@app.on_event("startup")
def startup() -> None:
    init_db()


def _index_html() -> str:
    return _INDEX_TEMPLATE.replace("__BASE_PATH__", BASE_PATH)


@router.get("/")
@router.get("")
def index() -> HTMLResponse:
    return HTMLResponse(_index_html())


@router.get("/health")
def health() -> dict:
    return {"ok": True, "base_path": BASE_PATH or "/"}


@router.get("/api/meta")
def api_meta() -> dict:
    meta = get_meta()
    from app.game.tricks import meta_upgrades

    return {**meta, "catalog": meta_upgrades(), "has_run": run_service.has_active_run()}


@router.get("/api/run/state")
def api_run_state() -> dict:
    state = run_service.get_state()
    if not state:
        raise HTTPException(404, "Kein aktiver Run")
    return state


@router.post("/api/run/new")
def api_run_new(body: NewRunRequest | None = None) -> dict:
    seed = body.seed if body else None
    return run_service.new_run(seed=seed)


@router.post("/api/run/start")
def api_run_start() -> dict:
    if not run_service.has_active_run():
        raise HTTPException(404, "Kein Run")
    return run_service.start_from_map()


@router.post("/api/cell/place")
def api_cell_place(body: CellPlaceRequest) -> dict:
    try:
        return run_service.place_cell(body.row, body.col, body.value)
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc


@router.post("/api/cell/clear")
def api_cell_clear(body: CellClearRequest) -> dict:
    try:
        return run_service.clear_cell(body.row, body.col)
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc


@router.post("/api/ante/advance")
def api_ante_advance() -> dict:
    try:
        return run_service.advance_from_victory()
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc


@router.post("/api/shop/buy")
def api_shop_buy(body: ShopBuyRequest) -> dict:
    try:
        return run_service.shop_buy(body.item_id, body.kind)
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc


@router.post("/api/shop/reroll")
def api_shop_reroll() -> dict:
    try:
        return run_service.shop_reroll()
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc


@router.post("/api/ante/continue")
def api_ante_continue() -> dict:
    try:
        return run_service.ante_continue()
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc


@router.post("/api/ante/boost")
def api_ante_boost(body: BoostRequest) -> dict:
    try:
        return run_service.buy_boost(body.boost_id, body.row, body.col)
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc


@router.post("/api/kniff/use")
def api_kniff_use(item_id: str) -> dict:
    try:
        return run_service.use_kniff(item_id)
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc


@router.post("/api/meta/buy")
def api_meta_buy(body: MetaBuyRequest) -> dict:
    try:
        return run_service.buy_meta_upgrade(body.upgrade_id)
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc


app.include_router(router)

_static_mount = f"{BASE_PATH}/static" if BASE_PATH else "/static"
app.mount(_static_mount, StaticFiles(directory=STATIC_DIR), name="static")


if BASE_PATH:

    @app.get("/")
    def redirect_root() -> RedirectResponse:
        return RedirectResponse(url=f"{BASE_PATH}/")
