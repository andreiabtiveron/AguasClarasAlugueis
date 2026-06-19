from pathlib import Path

from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from app.models import Coordinates, DashboardResponse, DashboardTopProperty, GraphStatus, GraphSummary, QualityProperty, QualityResponse
from app.services.graph import graph_repository
from app.services.infrastructure import fetch_infrastructure
from app.services.properties import PropertyProvider, PropertyProviderError, fetch_properties
from app.services.scoring import build_quality
from app.services.settings import settings

app = FastAPI(title=settings.app_name)

FRONTEND_DIST = Path("frontend/dist")

app.mount("/static", StaticFiles(directory=FRONTEND_DIST), name="static")


@app.get("/")
async def index() -> FileResponse:
    return FileResponse(FRONTEND_DIST / "index.html")


@app.get("/api/health")
async def health() -> dict[str, str]:
    return {"status": "ok", "app": settings.app_name}


@app.on_event("shutdown")
def shutdown() -> None:
    graph_repository.close()


@app.get("/api/properties")
async def properties(
    provider: PropertyProvider = "auto",
    limit: int = Query(default=settings.default_limit, ge=1, le=80),
) -> dict:
    try:
        items, source, notes = await fetch_properties(provider=provider, limit=limit)
    except PropertyProviderError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc

    return {"source": source, "notes": notes, "properties": items}


@app.get("/api/infrastructure")
async def infrastructure() -> dict:
    points, source, notes = await fetch_infrastructure()
    return {"source": source, "notes": notes, "infrastructure": points}


@app.get("/api/quality", response_model=QualityResponse)
async def quality(
    provider: PropertyProvider = "auto",
    limit: int = Query(default=settings.default_limit, ge=1, le=80),
) -> QualityResponse:
    try:
        properties_data, property_source, property_notes = await fetch_properties(provider=provider, limit=limit)
    except PropertyProviderError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc

    infrastructure_data, infrastructure_source, infrastructure_notes = await fetch_infrastructure()
    scored = build_quality(properties_data, infrastructure_data)
    graph_note = await graph_repository.persist_quality(scored, infrastructure_data)
    dashboard = await _build_dashboard(scored)

    return QualityResponse(
        provider=provider,
        property_source=property_source,
        infrastructure_source=infrastructure_source,
        graph_source="Neo4j" if settings.neo4j_enabled else "Neo4j desabilitado",
        center=Coordinates(lat=settings.center_lat, lon=settings.center_lon),
        properties=scored,
        infrastructure=infrastructure_data,
        dashboard=dashboard,
        notes=property_notes + infrastructure_notes + [graph_note],
    )


@app.get("/api/graph/status", response_model=GraphStatus)
async def graph_status() -> GraphStatus:
    return await graph_repository.status()


@app.get("/api/graph/summary", response_model=GraphSummary)
async def graph_summary() -> GraphSummary:
    return await graph_repository.summary()


async def _build_dashboard(properties: list[QualityProperty]) -> DashboardResponse:
    graph_rows, query_source = await graph_repository.top_value_properties()
    if graph_rows:
        top_properties = [DashboardTopProperty(**row) for row in graph_rows]
        source_label = "Neo4j/Cypher"
    else:
        top_properties = _rank_properties_in_memory(properties)
        source_label = "Memoria Python"

    average_qv = sum(item.qv for item in properties) / len(properties) if properties else 0

    return DashboardResponse(
        property_count=len(properties),
        average_qv=round(average_qv, 4),
        top_value_properties=top_properties,
        query_source=source_label if query_source == "neo4j" else source_label,
        query_description="Ranking = 0.45*QV + 0.35*IAR + 0.20*preco_normalizado_invertido.",
    )


def _rank_properties_in_memory(properties: list[QualityProperty]) -> list[DashboardTopProperty]:
    if not properties:
        return []

    prices = [item.price for item in properties]
    min_price = min(prices)
    max_price = max(prices)

    rows: list[DashboardTopProperty] = []
    for item in properties:
        if max_price == min_price:
            price_score = 0.5
        else:
            price_score = 1 - ((item.price - min_price) / (max_price - min_price))

        composite_score = item.qv * 0.45 + item.iar * 0.35 + price_score * 0.20
        rows.append(
            DashboardTopProperty(
                id=item.id,
                title=item.title,
                price=item.price,
                qv=item.qv,
                iar=item.iar,
                price_score=round(price_score, 4),
                composite_score=round(composite_score, 4),
                area_m2=item.area_m2,
                bedrooms=item.bedrooms,
                source=item.source,
            )
        )

    return sorted(rows, key=lambda row: (row.composite_score, row.qv, -row.price), reverse=True)[:5]
