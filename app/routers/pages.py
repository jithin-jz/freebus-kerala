import logging

from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.database import get_db
from app.services.search import nearby_buses, search_routes

logger = logging.getLogger(__name__)
router = APIRouter(tags=["pages"])
templates = Jinja2Templates(directory="app/templates")


def base_context(request: Request) -> dict[str, object]:
    return {"settings": get_settings()}


def render(request: Request, template_name: str, context: dict[str, object] | None = None) -> HTMLResponse:
    return templates.TemplateResponse(
        request,
        template_name,
        base_context(request) | (context or {}),
    )


@router.get("/", response_class=HTMLResponse)
async def index(request: Request) -> HTMLResponse:
    return render(request, "index.html")


@router.get("/search", response_class=HTMLResponse)
async def search_page(
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> HTMLResponse:
    origin = request.query_params.get("from")
    destination = request.query_params.get("to")
    free_only = request.query_params.get("free_only", "true").lower() != "false"
    results = []
    error = None
    if origin or destination:
        try:
            results = await search_routes(db, origin=origin, destination=destination, free_only=free_only)
        except Exception as exc:
            logger.warning("Search page query failed: %s", exc)
            error = "Search is temporarily unavailable. Please try again later."
    context = {
        "query_from": origin or "",
        "query_to": destination or "",
        "free_only": free_only,
        "results": results,
        "error": error,
    }
    return render(request, "results.html", context)


@router.get("/nearby", response_class=HTMLResponse)
async def nearby_page(
    request: Request,
    lat: float | None = None,
    lng: float | None = None,
    radius_metres: int | None = None,
    db: AsyncSession = Depends(get_db),
) -> HTMLResponse:
    settings = get_settings()
    radius = radius_metres or settings.default_nearby_radius_metres
    results = []
    error = None
    if lat is not None and lng is not None:
        try:
            results = await nearby_buses(db, lat=lat, lng=lng, radius_metres=radius, free_only=True)
        except Exception as exc:
            logger.warning("Nearby page query failed: %s", exc)
            error = "Nearby buses are temporarily unavailable. Please try again later."
    context = {
        "lat": lat,
        "lng": lng,
        "radius_metres": radius,
        "results": results,
        "error": error,
    }
    return render(request, "nearby.html", context)


@router.get("/routes/{route_id}", response_class=HTMLResponse)
async def route_detail(request: Request, route_id: int) -> HTMLResponse:
    return render(request, "route_detail.html", {"route_id": route_id})


@router.get("/scheme", response_class=HTMLResponse)
async def scheme_info(request: Request) -> HTMLResponse:
    return render(request, "scheme_info.html")


@router.get("/offline.html", response_class=HTMLResponse)
async def offline(request: Request) -> HTMLResponse:
    return render(request, "offline.html")
