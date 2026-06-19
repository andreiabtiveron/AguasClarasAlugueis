from collections import defaultdict

from app.models import AccessibilityScore, InfrastructurePoint, Property, QualityProperty
from app.services.geo import haversine_m


WEIGHTS = {
    "hospital": 0.32,
    "school": 0.24,
    "pharmacy": 0.16,
    "market": 0.16,
    "park": 0.12,
}


def build_quality(properties: list[Property], infrastructure: list[InfrastructurePoint]) -> list[QualityProperty]:
    by_category = defaultdict(list)
    for point in infrastructure:
        by_category[point.category].append(point)

    raw_scores: list[dict[str, float]] = []
    nearest_distances: list[dict[str, float]] = []

    for prop in properties:
        scores: dict[str, float] = {}
        nearest: dict[str, float] = {}

        for category in WEIGHTS:
            distances = [haversine_m(prop.coords, point.coords) for point in by_category[category]]
            if not distances:
                scores[category] = 0.0
                nearest[category] = 0.0
                continue

            nearest[category] = min(distances)
            scores[category] = sum(1 / ((distance / 1000) + 0.08) ** 1.5 for distance in distances)

        raw_scores.append(scores)
        nearest_distances.append(nearest)

    normalized = _normalize_scores(raw_scores)
    quality: list[QualityProperty] = []

    for prop, scores, nearest in zip(properties, normalized, nearest_distances, strict=True):
        iar = sum(scores[category] * weight for category, weight in WEIGHTS.items())
        qv = 1.0
        for category, weight in WEIGHTS.items():
            qv *= max(scores[category], 0.01) ** weight

        quality.append(
            QualityProperty(
                **prop.model_dump(),
                accessibility=AccessibilityScore(**scores),
                iar=round(iar, 4),
                qv=round(qv, 4),
                nearest={category: round(distance, 1) for category, distance in nearest.items()},
            )
        )

    return sorted(quality, key=lambda item: item.qv, reverse=True)


def _normalize_scores(rows: list[dict[str, float]]) -> list[dict[str, float]]:
    if not rows:
        return []

    normalized = [{category: 0.01 for category in WEIGHTS} for _ in rows]

    for category in WEIGHTS:
        values = [row[category] for row in rows]
        min_value = min(values)
        max_value = max(values)

        for index, value in enumerate(values):
            if max_value == min_value:
                normalized[index][category] = 0.5 if value > 0 else 0.01
            else:
                normalized[index][category] = round(0.01 + 0.99 * (value - min_value) / (max_value - min_value), 4)

    return normalized
