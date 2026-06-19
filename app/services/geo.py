from math import asin, cos, radians, sin, sqrt

from app.models import Coordinates


def haversine_m(a: Coordinates, b: Coordinates) -> float:
    earth_radius_m = 6_371_000
    dlat = radians(b.lat - a.lat)
    dlon = radians(b.lon - a.lon)
    lat1 = radians(a.lat)
    lat2 = radians(b.lat)

    h = sin(dlat / 2) ** 2 + cos(lat1) * cos(lat2) * sin(dlon / 2) ** 2
    return 2 * earth_radius_m * asin(sqrt(h))
