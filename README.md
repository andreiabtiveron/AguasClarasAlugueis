# Aguas Claras NEW

Monolito com FastAPI, VueJS e Leaflet para visualizar imoveis em Aguas Claras e calcular qualidade de vida urbana pela proximidade de infraestrutura.

O frontend fica em Vue com Vite e usa componente `.vue`:

```text
frontend/src/App.vue
```

O build do Vue gera arquivos estaticos em `frontend/dist`, e o FastAPI serve esse build no mesmo servidor.

## API 0800 escolhida

Para anuncios de imoveis, o projeto usa um provedor plugavel:

- `auto`: tenta buscar listagens na API publica da Nestoria, sem chave.
- `nestoria`: forca a tentativa pela Nestoria.
- `simulated`: usa dados locais reproduziveis, bom para apresentacao em sala.

A infraestrutura urbana vem da Overpass API/OpenStreetMap, tambem gratuita e sem chave, buscando hospital/clinica, escola/universidade, farmacia, mercado e parque.

Na pratica, APIs brasileiras gratuitas de anuncios sao instaveis ou cobram por scraping. Por isso o app nunca quebra a demo: quando o provedor externo falha, o backend informa a queda e usa o dataset simulado.

## Rodando localmente

Sem `requirements.txt`. As dependencias ficam no `pyproject.toml`.

```bash
cd AguasClaras-NEW
python -m venv .venv
source .venv/bin/activate
pip install .

cd frontend
npm install
npm run build
cd ..

python -m uvicorn app.main:app --reload
```

Abra:

```text
http://localhost:8000
```

## Rodando com Docker

```bash
cd AguasClaras-NEW
docker compose up --build
```

Isso sobe:

- FastAPI + Vue em `http://localhost:8000`
- Neo4j Browser em `http://localhost:7474`

Credenciais locais do Neo4j:

```text
usuario: neo4j
senha: aguasclaras2026
```

## Endpoints

- `GET /api/health`
- `GET /api/properties?provider=auto&limit=48`
- `GET /api/infrastructure`
- `GET /api/quality?provider=auto&limit=48`
- `GET /api/graph/status`
- `GET /api/graph/summary`

## Neo4j

Quando `NEO4J_ENABLED=true`, o endpoint `/api/quality` tambem grava o grafo no Neo4j.

Modelo do grafo:

```cypher
(:Property)-[:NEAR {category, distance_m}]->(:Amenity)
```

Cada `Property` recebe `qv`, `iar`, preco, area e coordenadas. Cada `Amenity` recebe categoria, nome, fonte e coordenadas.

Consulta util no Neo4j Browser:

```cypher
MATCH (p:Property)-[r:NEAR]->(a:Amenity)
RETURN p, r, a
LIMIT 100
```

## Modelo

O backend calcula distancia geodesica entre cada imovel e cada servico urbano. Depois soma acessibilidade por categoria com decaimento espacial:

```text
acessibilidade = soma(1 / ((distancia_km + 0.08) ^ 1.5))
```

As categorias sao normalizadas e combinadas em:

- `IAR`: media ponderada.
- `QV`: Cobb-Douglas ponderado.

Pesos usados:

```text
hospital 0.32
school   0.24
pharmacy 0.16
market   0.16
park     0.12
```
