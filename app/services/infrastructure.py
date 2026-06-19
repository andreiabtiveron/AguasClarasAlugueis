from collections.abc import Iterable
from uuid import uuid4

import httpx

from app.models import Coordinates, InfraCategory, InfrastructurePoint
from app.services.settings import settings


OVERPASS_QUERY = """
[out:json][timeout:25];
(
  node["amenity"~"hospital|clinic|school|university|pharmacy|marketplace"](-15.858,-48.047,-15.819,-48.000);
  way["amenity"~"hospital|clinic|school|university|pharmacy|marketplace"](-15.858,-48.047,-15.819,-48.000);
  relation["amenity"~"hospital|clinic|school|university|pharmacy|marketplace"](-15.858,-48.047,-15.819,-48.000);
  node["shop"~"supermarket|convenience|grocery"](-15.858,-48.047,-15.819,-48.000);
  way["shop"~"supermarket|convenience|grocery"](-15.858,-48.047,-15.819,-48.000);
  relation["shop"~"supermarket|convenience|grocery"](-15.858,-48.047,-15.819,-48.000);
  node["leisure"~"park|recreation_ground|playground"](-15.858,-48.047,-15.819,-48.000);
  way["leisure"~"park|recreation_ground|playground"](-15.858,-48.047,-15.819,-48.000);
  relation["leisure"~"park|recreation_ground|playground"](-15.858,-48.047,-15.819,-48.000);
);
out center tags;
"""


async def fetch_infrastructure() -> tuple[list[InfrastructurePoint], str, list[str]]:
    notes: list[str] = []
    try:
        points = await fetch_overpass()
        if points:
            return points, "OpenStreetMap/Overpass", notes
        notes.append("Overpass respondeu sem pontos; usando infraestrutura local de reserva.")
    except Exception as exc:
        notes.append(f"Overpass indisponivel; usando infraestrutura local de reserva. Detalhe: {exc}")

    return fallback_infrastructure(), "Reserva local", notes


async def fetch_overpass() -> list[InfrastructurePoint]:
    headers = {
        "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
        "User-Agent": "AguasClarasNEW/0.1 academic project",
    }

    async with httpx.AsyncClient(timeout=settings.request_timeout) as client:
        response = await client.post(settings.overpass_url, content=f"data={OVERPASS_QUERY}", headers=headers)
        response.raise_for_status()
        payload = response.json()

    points: list[InfrastructurePoint] = []
    seen: set[tuple[str, float, float]] = set()

    for element in payload.get("elements", []):
        tags = element.get("tags", {})
        category = _category_from_tags(tags)
        coords = _coords_from_element(element)

        if category is None or coords is None:
            continue

        key = (category, round(coords.lat, 6), round(coords.lon, 6))
        if key in seen:
            continue
        seen.add(key)

        points.append(
            InfrastructurePoint(
                id=f"osm-{element.get('type', 'x')}-{element.get('id', uuid4())}",
                name=tags.get("name") or _fallback_name(category),
                category=category,
                coords=coords,
            )
        )

    return points


def fallback_infrastructure() -> list[InfrastructurePoint]:
    raw: Iterable[tuple[str, InfraCategory, float, float]] = [
        ("Hospital Anchieta", "hospital", -15.8358, -48.0300),
        ("UBS Aguas Claras", "hospital", -15.8429, -48.0280),
        ("Colegio La Salle", "school", -15.8377, -48.0242),
        ("Centro Educacional Sigma", "school", -15.8450, -48.0204),
        ("Colegio Ideal", "school", -15.8331, -48.0194),
        ("Drogasil", "pharmacy", -15.8395, -48.0279),
        ("Pacheco", "pharmacy", -15.8366, -48.0216),
        ("Supermercado Dona de Casa", "market", -15.8408, -48.0263),
        ("Big Box", "market", -15.8344, -48.0236),
        ("Parque Ecologico de Aguas Claras", "park", -15.8436, -48.0350),
        ("Praca Rouxinol", "park", -15.8328, -48.0251),
    ]
    return [
        InfrastructurePoint(
            id=f"fallback-{index}",
            name=name,
            category=category,
            coords=Coordinates(lat=lat, lon=lon),
            source="Reserva local",
        )
        for index, (name, category, lat, lon) in enumerate(raw, start=1)
    ]


def _category_from_tags(tags: dict[str, str]) -> InfraCategory | None:
    amenity = tags.get("amenity")
    leisure = tags.get("leisure")
    shop = tags.get("shop")

    if amenity in {"hospital", "clinic"}:
        return "hospital"
    if amenity in {"school", "university"}:
        return "school"
    if amenity == "pharmacy":
        return "pharmacy"
    if amenity == "marketplace" or shop in {"supermarket", "convenience", "grocery"}:
        return "market"
    if leisure in {"park", "recreation_ground", "playground"}:
        return "park"
    return None


def _coords_from_element(element: dict) -> Coordinates | None:
    lat = element.get("lat") or element.get("center", {}).get("lat")
    lon = element.get("lon") or element.get("center", {}).get("lon")

    if lat is None or lon is None:
        return None
    return Coordinates(lat=float(lat), lon=float(lon))


def _fallback_name(category: InfraCategory) -> str:
    names = {
        "hospital": "Servico de saude",
        "school": "Instituicao de ensino",
        "pharmacy": "Farmacia",
        "market": "Mercado",
        "park": "Area verde",
    }
    return names[category]
