"""
Modelagem em grafos da relação imóvel <-> facility urbana
=========================================================

Ponto central do trabalho (conforme a orientação). Os imóveis e as facilities
urbanas (escolas, hospitais, parques, farmácias, etc.) são modelados como nós
de um grafo bipartido. Uma aresta liga um imóvel a uma facility quando a
distância entre eles é inferior a um limiar; o peso da aresta é dado por uma
função inversa da distância (eq. 1 da orientação):

        w(i, f) = 1 / (1 + d(i, f))

A partir do grafo derivam-se:

  * a acessibilidade por categoria de serviço (E, S, H, L da eq. 2);
  * um ranking multicritério dependente do perfil do morador;
  * métricas de centralidade (PageRank, grau ponderado, proximidade) que
    captam a "importância" estrutural de cada imóvel na rede urbana.

O módulo é autocontido: o bloco __main__ gera dados sintéticos e roda toda a
modelagem, de modo que pode ser testado sem depender de coleta externa
(OSMnx/scraping).
"""

import math

import numpy as np
import pandas as pd
import networkx as nx


# ---------------------------------------------------------------------------
# Perfis de público-alvo
# ---------------------------------------------------------------------------
# A orientação enfatiza que a qualidade de vida muda conforme o público; sem
# perfis o ranking fica genérico demais. Cada perfil pondera as categorias de
# facility de forma diferente. Os pesos somam ~1 para comparabilidade.

PERFIS = {
    "familia": {
        "school": 0.35,
        "hospital": 0.25,
        "park": 0.20,
        "pharmacy": 0.10,
        "university": 0.10,
    },
    "idoso": {
        "hospital": 0.40,
        "pharmacy": 0.30,
        "park": 0.15,
        "school": 0.05,
        "university": 0.10,
    },
    "estudante": {
        "university": 0.45,
        "park": 0.15,
        "pharmacy": 0.15,
        "school": 0.05,
        "hospital": 0.20,
    },
    "jovem_profissional": {
        "park": 0.30,
        "hospital": 0.25,
        "pharmacy": 0.20,
        "university": 0.10,
        "school": 0.15,
    },
}

CATEGORIAS = ["hospital", "school", "park", "pharmacy", "university"]

# Limiar de conexão padrão, em metros: imóvel e facility só se ligam abaixo
# desta distância (caminhabilidade urbana ~ 1,5 km).
LIMIAR_PADRAO_M = 1500.0


# ---------------------------------------------------------------------------
# Distância geográfica
# ---------------------------------------------------------------------------

def haversine_m(lat1, lon1, lat2, lon2):
    """Distância em metros entre dois pontos (lat, lon) pela fórmula de Haversine."""

    R = 6371000.0  # raio médio da Terra em metros

    p1 = math.radians(lat1)
    p2 = math.radians(lat2)

    dphi = math.radians(lat2 - lat1)
    dlmb = math.radians(lon2 - lon1)

    a = math.sin(dphi / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dlmb / 2) ** 2

    return 2 * R * math.asin(math.sqrt(a))


# ---------------------------------------------------------------------------
# Normalização de entradas (compatível com o pipeline atual)
# ---------------------------------------------------------------------------

def normalizar_facilities(gdf_servicos):
    """Converte o GeoDataFrame do OSM no esquema relacional 'facility'.

    Colunas de saída: id_facility, nome, categoria, latitude, longitude.
    Aceita o formato produzido por extracao_infra.py (colunas amenity/leisure/
    name/geometry com centroides).
    """

    registros = []

    for idx, row in gdf_servicos.reset_index(drop=True).iterrows():

        categoria = row.get("amenity")

        if categoria is None or (isinstance(categoria, float) and pd.isna(categoria)):
            categoria = row.get("leisure")

        # parques do OSM podem vir como 'park' ou 'recreation_ground'
        if categoria in ("recreation_ground",):
            categoria = "park"

        geom = row["geometry"]

        registros.append({
            "id_facility": f"fac_{idx}",
            "nome": row.get("name") if pd.notna(row.get("name")) else "Serviço",
            "categoria": categoria,
            "latitude": geom.y,
            "longitude": geom.x,
        })

    return pd.DataFrame(registros)


def normalizar_imoveis(df_imoveis):
    """Garante o esquema relacional 'imovel' com id e latitude/longitude.

    Aceita o formato de scraper_imoveis.py (coluna 'coords' = (lat, lon)).
    """

    df = df_imoveis.reset_index(drop=True).copy()

    if "id_imovel" not in df.columns:
        df["id_imovel"] = [f"imovel_{i}" for i in range(len(df))]

    if "latitude" not in df.columns or "longitude" not in df.columns:

        if "coords" in df.columns:
            df["latitude"] = df["coords"].apply(lambda c: c[0])
            df["longitude"] = df["coords"].apply(lambda c: c[1])
        else:
            raise ValueError("imóveis sem 'coords' nem latitude/longitude")

    return df


# ---------------------------------------------------------------------------
# Construção do grafo
# ---------------------------------------------------------------------------

def construir_grafo(df_imoveis, df_facilities, limiar_m=LIMIAR_PADRAO_M):
    """Constrói o grafo bipartido imóvel-facility.

    Nós de imóvel: tipo='imovel', com atributos preco, area, lat, lon.
    Nós de facility: tipo='facility', com atributo categoria, lat, lon.
    Arestas: criadas quando d(i,f) < limiar_m; atributos distancia_metros e peso.

    O peso usa a função inversa da distância (eq. 1), com a distância em km
    para manter os pesos numericamente estáveis:  w = 1 / (1 + d_km).
    """

    G = nx.Graph()

    for _, im in df_imoveis.iterrows():
        G.add_node(
            im["id_imovel"],
            tipo="imovel",
            preco=im.get("preco"),
            area=im.get("area"),
            latitude=im["latitude"],
            longitude=im["longitude"],
        )

    for _, fa in df_facilities.iterrows():
        G.add_node(
            fa["id_facility"],
            tipo="facility",
            categoria=fa["categoria"],
            nome=fa["nome"],
            latitude=fa["latitude"],
            longitude=fa["longitude"],
        )

    for _, im in df_imoveis.iterrows():
        for _, fa in df_facilities.iterrows():

            d = haversine_m(
                im["latitude"], im["longitude"],
                fa["latitude"], fa["longitude"],
            )

            if d < limiar_m:

                peso = 1.0 / (1.0 + d / 1000.0)

                G.add_edge(
                    im["id_imovel"],
                    fa["id_facility"],
                    distancia_metros=round(d, 1),
                    peso=round(peso, 6),
                )

    return G


def tabela_proximidade(G):
    """Extrai a tabela relacional 'proximidade' (arestas do grafo) como DataFrame.

    Colunas: id_imovel, id_facility, distancia_metros, peso_relacional.
    """

    linhas = []

    for u, v, dados in G.edges(data=True):

        # garante a orientação imóvel -> facility
        if G.nodes[u]["tipo"] == "imovel":
            id_imovel, id_facility = u, v
        else:
            id_imovel, id_facility = v, u

        linhas.append({
            "id_imovel": id_imovel,
            "id_facility": id_facility,
            "distancia_metros": dados["distancia_metros"],
            "peso_relacional": dados["peso"],
        })

    return pd.DataFrame(linhas)


# ---------------------------------------------------------------------------
# Acessibilidade por categoria (E, S, H, L da eq. 2)
# ---------------------------------------------------------------------------

def acessibilidade_por_categoria(G):
    """Para cada imóvel, soma os pesos das arestas por categoria de facility.

    Retorna DataFrame indexado por id_imovel com uma coluna por categoria
    (acess_<categoria>). É a acessibilidade gravitacional agregada que alimenta
    o ranking multicritério.
    """

    registros = {}

    imoveis = [n for n, d in G.nodes(data=True) if d["tipo"] == "imovel"]

    for n in imoveis:

        acumulado = {cat: 0.0 for cat in CATEGORIAS}

        for viz in G.neighbors(n):

            cat = G.nodes[viz].get("categoria")

            if cat in acumulado:
                acumulado[cat] += G[n][viz]["peso"]

        registros[n] = acumulado

    df = pd.DataFrame.from_dict(registros, orient="index")

    df = df.rename(columns={c: f"acess_{c}" for c in CATEGORIAS})

    df.index.name = "id_imovel"

    return df


def _normalizar_minmax(serie):
    """Normaliza uma série para [0, 1]; retorna 0.5 se constante."""

    mn, mx = serie.min(), serie.max()

    if mx == mn:
        return pd.Series(0.5, index=serie.index)

    return (serie - mn) / (mx - mn)


# ---------------------------------------------------------------------------
# Ranking multicritério por perfil
# ---------------------------------------------------------------------------

def rankear_por_perfil(G, df_imoveis, perfil="familia", lambda_custo=0.3):
    """Gera o ranking de imóveis para um perfil de público.

    score = soma_cat( peso_perfil[cat] * acess_norm[cat] ) - lambda_custo * custo_norm

    onde acess_norm e custo_norm são normalizados em [0,1]. O termo de custo
    implementa o -lambda*C(i) da eq. 2 (penaliza imóveis mais caros).
    """

    if perfil not in PERFIS:
        raise ValueError(f"Perfil '{perfil}' inválido. Opções: {list(PERFIS)}")

    pesos = PERFIS[perfil]

    acess = acessibilidade_por_categoria(G)

    df = df_imoveis.set_index("id_imovel").join(acess)

    # normaliza acessibilidade por categoria
    score = pd.Series(0.0, index=df.index)

    for cat in CATEGORIAS:
        col = f"acess_{cat}"
        norm = _normalizar_minmax(df[col].fillna(0.0))
        score = score + pesos.get(cat, 0.0) * norm

    # termo de custo (penalização). Usa preço por m2 se houver área.
    if "preco" in df.columns:

        if "area" in df.columns and df["area"].notna().all() and (df["area"] > 0).all():
            custo = df["preco"] / df["area"]
        else:
            custo = df["preco"]

        score = score - lambda_custo * _normalizar_minmax(custo.astype(float))

    df["score_perfil"] = score

    df = df.sort_values("score_perfil", ascending=False)

    df["ranking"] = range(1, len(df) + 1)

    return df


# ---------------------------------------------------------------------------
# Centralidades (Teoria dos Grafos / PageRank)
# ---------------------------------------------------------------------------

def calcular_centralidades(G, perfil=None):
    """Calcula métricas de centralidade dos imóveis no grafo.

    - pagerank: PageRank ponderado pelo peso das arestas. Se um perfil for
      informado, usa personalização: facilities recebem importância proporcional
      ao peso do perfil para sua categoria, propagando relevância aos imóveis
      mais bem conectados às facilities que importam para aquele público.
    - grau_ponderado: soma dos pesos das arestas incidentes (força do nó).
    - proximidade: closeness centrality ponderada pela distância.

    Retorna DataFrame indexado por id_imovel.
    """

    personalizacao = None

    if perfil is not None:

        pesos = PERFIS[perfil]
        personalizacao = {}

        for n, d in G.nodes(data=True):

            if d["tipo"] == "facility":
                personalizacao[n] = pesos.get(d.get("categoria"), 0.0) + 1e-9
            else:
                personalizacao[n] = 1e-9

        soma = sum(personalizacao.values())
        personalizacao = {k: v / soma for k, v in personalizacao.items()}

    pr = nx.pagerank(G, weight="peso", personalization=personalizacao)

    grau_pond = dict(G.degree(weight="peso"))

    # distância como custo para closeness (inverso do peso)
    for u, v, dd in G.edges(data=True):
        dd["dist_custo"] = 1.0 / (dd["peso"] + 1e-9)

    closeness = nx.closeness_centrality(G, distance="dist_custo")

    imoveis = [n for n, d in G.nodes(data=True) if d["tipo"] == "imovel"]

    df = pd.DataFrame({
        "pagerank": {n: pr[n] for n in imoveis},
        "grau_ponderado": {n: grau_pond[n] for n in imoveis},
        "proximidade": {n: closeness[n] for n in imoveis},
    })

    df.index.name = "id_imovel"

    return df.sort_values("pagerank", ascending=False)


# ---------------------------------------------------------------------------
# Dados sintéticos para teste autocontido
# ---------------------------------------------------------------------------

def _dados_sinteticos(n_imoveis=20, n_por_categoria=4, seed=42):

    rng = np.random.default_rng(seed)

    lat_c, lon_c = -15.839, -48.025

    imoveis = []

    for i in range(n_imoveis):
        imoveis.append({
            "id_imovel": f"imovel_{i}",
            "preco": int(rng.integers(250000, 900000)),
            "area": int(rng.integers(40, 120)),
            "latitude": lat_c + rng.uniform(-0.012, 0.012),
            "longitude": lon_c + rng.uniform(-0.012, 0.012),
        })

    facilities = []
    k = 0

    for cat in CATEGORIAS:
        for _ in range(n_por_categoria):
            facilities.append({
                "id_facility": f"fac_{k}",
                "nome": f"{cat}_{k}",
                "categoria": cat,
                "latitude": lat_c + rng.uniform(-0.012, 0.012),
                "longitude": lon_c + rng.uniform(-0.012, 0.012),
            })
            k += 1

    return pd.DataFrame(imoveis), pd.DataFrame(facilities)


if __name__ == "__main__":

    print("=== Modelagem em grafos (dados sintéticos) ===\n")

    df_imoveis, df_facilities = _dados_sinteticos()

    G = construir_grafo(df_imoveis, df_facilities, limiar_m=LIMIAR_PADRAO_M)

    n_imo = sum(1 for _, d in G.nodes(data=True) if d["tipo"] == "imovel")
    n_fac = sum(1 for _, d in G.nodes(data=True) if d["tipo"] == "facility")

    print(f"Grafo: {G.number_of_nodes()} nós ({n_imo} imóveis, {n_fac} facilities), "
          f"{G.number_of_edges()} arestas\n")

    print("Tabela proximidade (5 primeiras arestas):")
    print(tabela_proximidade(G).head().to_string(index=False))

    print("\n--- Ranking por perfil (top 5) ---")

    for perfil in PERFIS:

        rk = rankear_por_perfil(G, df_imoveis, perfil=perfil)

        print(f"\nPerfil: {perfil}")
        print(rk[["preco", "area", "score_perfil", "ranking"]].head().to_string())

    print("\n--- Centralidades (top 5, perfil família) ---")
    cen = calcular_centralidades(G, perfil="familia")
    print(cen.head().to_string())
