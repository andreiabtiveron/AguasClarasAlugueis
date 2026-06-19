from dataclasses import dataclass
import os


@dataclass(frozen=True)
class Settings:
    app_name: str = "Aguas Claras NEW"
    center_lat: float = -15.8390
    center_lon: float = -48.0250
    overpass_url: str = "https://overpass-api.de/api/interpreter"
    nestoria_url: str = "https://api.nestoria.com.br/api"
    nestoria_place: str = "Aguas Claras DF"
    neo4j_enabled: bool = False
    neo4j_uri: str = "bolt://localhost:7687"
    neo4j_user: str = "neo4j"
    neo4j_password: str = "aguasclaras2026"
    neo4j_database: str = "neo4j"
    neo4j_project: str = "aguas-claras-new"
    default_limit: int = 48
    request_timeout: float = 12.0

    @classmethod
    def from_env(cls) -> "Settings":
        return cls(
            overpass_url=os.getenv("OVERPASS_URL", cls.overpass_url),
            nestoria_url=os.getenv("NESTORIA_URL", cls.nestoria_url),
            nestoria_place=os.getenv("NESTORIA_PLACE", cls.nestoria_place),
            neo4j_enabled=os.getenv("NEO4J_ENABLED", "false").lower() == "true",
            neo4j_uri=os.getenv("NEO4J_URI", cls.neo4j_uri),
            neo4j_user=os.getenv("NEO4J_USER", cls.neo4j_user),
            neo4j_password=os.getenv("NEO4J_PASSWORD", cls.neo4j_password),
            neo4j_database=os.getenv("NEO4J_DATABASE", cls.neo4j_database),
            neo4j_project=os.getenv("NEO4J_PROJECT", cls.neo4j_project),
            default_limit=int(os.getenv("DEFAULT_PROPERTY_LIMIT", cls.default_limit)),
            request_timeout=float(os.getenv("REQUEST_TIMEOUT", cls.request_timeout)),
        )


settings = Settings.from_env()
