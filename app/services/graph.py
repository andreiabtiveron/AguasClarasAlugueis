import asyncio
from contextlib import contextmanager
from typing import Any

from neo4j import GraphDatabase
from neo4j.exceptions import Neo4jError, ServiceUnavailable

from app.models import GraphStatus, GraphSummary, InfrastructurePoint, QualityProperty
from app.services.geo import haversine_m
from app.services.settings import settings


class GraphRepository:
    def __init__(self) -> None:
        self.enabled = settings.neo4j_enabled
        self.uri = settings.neo4j_uri
        self.database = settings.neo4j_database
        self.project = settings.neo4j_project
        self._driver = None

        if self.enabled:
            self._driver = GraphDatabase.driver(
                self.uri,
                auth=(settings.neo4j_user, settings.neo4j_password),
                connection_timeout=3,
            )

    @contextmanager
    def session(self):
        if not self.enabled or self._driver is None:
            raise RuntimeError("Neo4j esta desabilitado.")

        with self._driver.session(database=self.database) as session:
            yield session

    async def status(self) -> GraphStatus:
        if not self.enabled:
            return GraphStatus(
                enabled=False,
                connected=False,
                uri=self.uri,
                database=self.database,
                message="Neo4j desabilitado. Use NEO4J_ENABLED=true para ativar.",
            )

        return await asyncio.to_thread(self._status_sync)

    async def persist_quality(
        self,
        properties: list[QualityProperty],
        infrastructure: list[InfrastructurePoint],
    ) -> str:
        if not self.enabled:
            return "Neo4j desabilitado; grafo nao foi atualizado."

        return await asyncio.to_thread(self._persist_quality_sync, properties, infrastructure)

    async def summary(self) -> GraphSummary:
        if not self.enabled:
            return GraphSummary(
                enabled=False,
                connected=False,
                message="Neo4j desabilitado. Suba com docker compose ou defina NEO4J_ENABLED=true.",
            )

        return await asyncio.to_thread(self._summary_sync)

    async def top_value_properties(self) -> tuple[list[dict[str, Any]], str]:
        if not self.enabled:
            return [], "memoria"

        return await asyncio.to_thread(self._top_value_properties_sync)

    def close(self) -> None:
        if self._driver is not None:
            self._driver.close()

    def _status_sync(self) -> GraphStatus:
        try:
            with self.session() as session:
                value = session.run("RETURN 1 AS ok").single(strict=True)["ok"]

            return GraphStatus(
                enabled=True,
                connected=value == 1,
                uri=self.uri,
                database=self.database,
                message="Neo4j conectado.",
            )
        except (Neo4jError, ServiceUnavailable, OSError, RuntimeError) as exc:
            return GraphStatus(
                enabled=True,
                connected=False,
                uri=self.uri,
                database=self.database,
                message=f"Neo4j indisponivel: {exc}",
            )

    def _persist_quality_sync(
        self,
        properties: list[QualityProperty],
        infrastructure: list[InfrastructurePoint],
    ) -> str:
        property_rows = [_property_row(item, self.project) for item in properties]
        amenity_rows = [_amenity_row(item, self.project) for item in infrastructure]
        relationship_rows = [
            {
                "property_id": property_item.id,
                "amenity_id": amenity.id,
                "category": amenity.category,
                "distance_m": round(haversine_m(property_item.coords, amenity.coords), 1),
                "project": self.project,
            }
            for property_item in properties
            for amenity in infrastructure
            if haversine_m(property_item.coords, amenity.coords) <= 1_200
        ]

        try:
            with self.session() as session:
                session.execute_write(self._create_constraints)
                session.execute_write(self._replace_project_graph, property_rows, amenity_rows, relationship_rows)
        except (Neo4jError, ServiceUnavailable, OSError, RuntimeError) as exc:
            return f"Neo4j indisponivel; grafo nao foi atualizado. Detalhe: {exc}"

        return (
            "Grafo Neo4j atualizado: "
            f"{len(property_rows)} imoveis, {len(amenity_rows)} servicos, "
            f"{len(relationship_rows)} relacoes NEAR."
        )

    def _summary_sync(self) -> GraphSummary:
        try:
            with self.session() as session:
                counts = session.run(
                    """
                    MATCH (p:Property {project: $project})
                    WITH count(p) AS properties, avg(p.qv) AS avg_qv
                    MATCH (a:Amenity {project: $project})
                    WITH properties, avg_qv, count(a) AS amenities
                    MATCH (:Property {project: $project})-[r:NEAR]->(:Amenity {project: $project})
                    RETURN properties, amenities, count(r) AS relationships, avg_qv
                    """,
                    project=self.project,
                ).single()
                top_properties = session.run(
                    """
                    MATCH (p:Property {project: $project})
                    RETURN p.id AS id, p.title AS title, p.qv AS qv, p.price AS price
                    ORDER BY p.qv DESC
                    LIMIT 5
                    """,
                    project=self.project,
                )

                return GraphSummary(
                    enabled=True,
                    connected=True,
                    properties=counts["properties"] if counts else 0,
                    amenities=counts["amenities"] if counts else 0,
                    relationships=counts["relationships"] if counts else 0,
                    avg_qv=round(counts["avg_qv"], 4) if counts and counts["avg_qv"] is not None else None,
                    top_properties=[dict(record) for record in top_properties],
                    message="Resumo carregado do Neo4j.",
                )
        except (Neo4jError, ServiceUnavailable, OSError, RuntimeError) as exc:
            return GraphSummary(
                enabled=True,
                connected=False,
                message=f"Neo4j indisponivel: {exc}",
            )

    def _top_value_properties_sync(self) -> tuple[list[dict[str, Any]], str]:
        try:
            with self.session() as session:
                result = session.run(
                    """
                    MATCH (p:Property {project: $project})
                    WITH collect(p) AS properties, min(p.price) AS min_price, max(p.price) AS max_price
                    UNWIND properties AS p
                    WITH p,
                        CASE
                            WHEN max_price = min_price THEN 0.5
                            ELSE 1.0 - ((toFloat(p.price) - min_price) / (max_price - min_price))
                        END AS price_score
                    WITH p,
                        price_score,
                        (p.qv * 0.45 + p.iar * 0.35 + price_score * 0.20) AS composite_score
                    RETURN
                        p.id AS id,
                        p.title AS title,
                        p.price AS price,
                        p.qv AS qv,
                        p.iar AS iar,
                        p.area_m2 AS area_m2,
                        p.bedrooms AS bedrooms,
                        p.source AS source,
                        price_score AS price_score,
                        composite_score AS composite_score
                    ORDER BY composite_score DESC, p.qv DESC, p.price ASC
                    LIMIT 5
                    """,
                    project=self.project,
                )
                rows = [_round_ranking_row(dict(record)) for record in result]
                return rows, "neo4j"
        except (Neo4jError, ServiceUnavailable, OSError, RuntimeError):
            return [], "memoria"

    @staticmethod
    def _create_constraints(tx) -> None:
        tx.run("CREATE CONSTRAINT property_id IF NOT EXISTS FOR (p:Property) REQUIRE p.id IS UNIQUE")
        tx.run("CREATE CONSTRAINT amenity_id IF NOT EXISTS FOR (a:Amenity) REQUIRE a.id IS UNIQUE")

    @staticmethod
    def _replace_project_graph(tx, properties: list[dict[str, Any]], amenities: list[dict[str, Any]], relationships: list[dict[str, Any]]) -> None:
        tx.run("MATCH (n {project: $project}) DETACH DELETE n", project=settings.neo4j_project)
        tx.run(
            """
            UNWIND $rows AS row
            MERGE (p:Property {id: row.id})
            SET p = row
            """,
            rows=properties,
        )
        tx.run(
            """
            UNWIND $rows AS row
            MERGE (a:Amenity {id: row.id})
            SET a = row
            """,
            rows=amenities,
        )
        tx.run(
            """
            UNWIND $rows AS row
            MATCH (p:Property {id: row.property_id, project: row.project})
            MATCH (a:Amenity {id: row.amenity_id, project: row.project})
            CREATE (p)-[:NEAR {
                category: row.category,
                distance_m: row.distance_m,
                project: row.project
            }]->(a)
            """,
            rows=relationships,
        )


def _property_row(item: QualityProperty, project: str) -> dict[str, Any]:
    return {
        "id": item.id,
        "project": project,
        "title": item.title,
        "price": item.price,
        "area_m2": item.area_m2,
        "bedrooms": item.bedrooms,
        "address": item.address,
        "source": item.source,
        "lat": item.coords.lat,
        "lon": item.coords.lon,
        "iar": item.iar,
        "qv": item.qv,
        "access_hospital": item.accessibility.hospital,
        "access_school": item.accessibility.school,
        "access_pharmacy": item.accessibility.pharmacy,
        "access_market": item.accessibility.market,
        "access_park": item.accessibility.park,
    }


def _amenity_row(item: InfrastructurePoint, project: str) -> dict[str, Any]:
    return {
        "id": item.id,
        "project": project,
        "name": item.name,
        "category": item.category,
        "source": item.source,
        "lat": item.coords.lat,
        "lon": item.coords.lon,
    }


def _round_ranking_row(row: dict[str, Any]) -> dict[str, Any]:
    row["qv"] = round(float(row["qv"]), 4)
    row["iar"] = round(float(row["iar"]), 4)
    row["price_score"] = round(float(row["price_score"]), 4)
    row["composite_score"] = round(float(row["composite_score"]), 4)
    return row


graph_repository = GraphRepository()
