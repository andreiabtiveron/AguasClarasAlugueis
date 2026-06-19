import random
from typing import Literal
from uuid import uuid4

import httpx

from app.models import Coordinates, Property
from app.services.settings import settings

PropertyProvider = Literal["auto", "nestoria", "simulated"]


class PropertyProviderError(RuntimeError):
    pass


async def fetch_properties(provider: PropertyProvider = "auto", limit: int | None = None) -> tuple[list[Property], str, list[str]]:
    limit = limit or settings.default_limit
    notes: list[str] = []

    if provider in {"auto", "nestoria"}:
        try:
            properties = await fetch_nestoria(limit)
            if properties:
                notes.append("Listagens carregadas pela API publica da Nestoria.")
                return properties, "Nestoria API", notes
            raise PropertyProviderError("Nestoria nao retornou listagens com coordenadas.")
        except Exception as exc:
            detail = str(exc) or exc.__class__.__name__
            notes.append(f"Nestoria indisponivel ou incompleta; usando dataset simulado. Detalhe: {detail}")

    properties = simulate_properties(limit)
    notes.append("Dataset simulado usado para manter a demonstracao reproduzivel.")
    return properties, "Simulado local", notes


async def fetch_nestoria(limit: int) -> list[Property]:
    params = {
        "encoding": "json",
        "action": "search_listings",
        "country": "br",
        "place_name": settings.nestoria_place,
        "listing_type": "buy",
        "number_of_results": min(limit, 50),
    }

    async with httpx.AsyncClient(timeout=settings.request_timeout, verify=False) as client:
        response = await client.get(settings.nestoria_url, params=params)
        response.raise_for_status()
        payload = response.json()

    listings = payload.get("response", {}).get("listings", [])
    properties: list[Property] = []

    for item in listings:
        lat = _as_float(item.get("latitude"))
        lon = _as_float(item.get("longitude"))
        price = _as_float(item.get("price"))

        if lat is None or lon is None or price is None:
            continue

        properties.append(
            Property(
                id=str(item.get("lister_url") or item.get("guid") or uuid4()),
                title=str(item.get("title") or item.get("property_type") or "Imovel a venda"),
                price=price,
                area_m2=_as_float(item.get("floor_area")),
                bedrooms=_as_int(item.get("bedroom_number")),
                address=item.get("summary"),
                url=item.get("lister_url"),
                source="Nestoria API",
                coords=Coordinates(lat=lat, lon=lon),
            )
        )

    return properties


def simulate_properties(limit: int) -> list[Property]:
    rng = random.Random(20261)
    titles = [
        "Apartamento perto da Estacao Aguas Claras",
        "Apartamento familiar em condominio",
        "Cobertura compacta proxima ao comercio",
        "Studio para investimento",
        "Apartamento nascente com varanda",
        "Imovel perto do metro e mercado",
    ]
    properties: list[Property] = []

    for index in range(limit):
        area = rng.randint(42, 128)
        bedrooms = rng.choice([1, 2, 2, 3, 3, 4])
        price_per_m2 = rng.randint(7800, 12200)
        price = area * price_per_m2 + rng.randint(-25_000, 40_000)
        lat = settings.center_lat + rng.uniform(-0.012, 0.012)
        lon = settings.center_lon + rng.uniform(-0.014, 0.014)

        properties.append(
            Property(
                id=f"sim-{index + 1:03d}",
                title=titles[index % len(titles)],
                price=float(max(price, 240_000)),
                area_m2=float(area),
                bedrooms=bedrooms,
                address="Aguas Claras, Brasilia - DF",
                source="Simulado local",
                coords=Coordinates(lat=lat, lon=lon),
            )
        )

    return properties


def _as_float(value: object) -> float | None:
    try:
        if value in (None, ""):
            return None
        return float(value)
    except (TypeError, ValueError):
        return None


def _as_int(value: object) -> int | None:
    try:
        if value in (None, ""):
            return None
        return int(float(value))
    except (TypeError, ValueError):
        return None
