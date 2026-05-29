"""
Persistência relacional dos dados (CSV + SQLite)
================================================

Após a coleta, os dados são normalizados e estruturados no modelo relacional
proposto na orientação. São quatro tabelas:

    imovel            (id_imovel PK)
    facility          (id_facility PK)
    categoria_facility(id_categoria PK)
    proximidade       (id_imovel, id_facility) PK composta

As funções deste módulo:
  1. constroem cada tabela a partir das saídas do pipeline;
  2. aplicam regras de limpeza explícitas (distinguindo dado bruto de tratado);
  3. exportam tudo para CSV e para um banco SQLite com integridade referencial
     (chaves estrangeiras);
  4. emitem um dicionário de dados (dicionario_dados.csv e .md).

Regras de limpeza aplicadas
---------------------------
  R1. Remoção de registros sem chave primária (id nulo).
  R2. Remoção de duplicatas por chave primária (mantém o primeiro).
  R3. Coerção de tipos numéricos; descarte de imóveis com preco<=0 ou area_m2<=0.
  R4. Validação de domínio: tipo in {apartamento, casa};
      finalidade in {aluguel, venda}; quartos/banheiros/vagas >= 0.
  R5. Validação de coordenadas dentro de um retângulo plausível de Águas Claras.
  R6. Normalização de texto (strip de espaços).
  R7. Integridade referencial: proximidade só mantém pares cujos id_imovel e
      id_facility existem nas respectivas tabelas.
"""

import sqlite3

import numpy as np
import pandas as pd

from modelagem_grafo import tabela_proximidade


# Retângulo plausível para Águas Claras/DF (validação de coordenadas, R5).
BBOX = {"lat_min": -15.86, "lat_max": -15.81, "lon_min": -48.05, "lon_max": -47.99}

TIPOS_VALIDOS = {"apartamento", "casa"}
FINALIDADES_VALIDAS = {"aluguel", "venda"}

# velocidade de caminhada para estimar tempo (m/min) -> ~4,8 km/h
VELOCIDADE_CAMINHADA_M_MIN = 80.0

COLUNAS_IMOVEL = [
    "id_imovel", "tipo", "finalidade", "preco", "area_m2", "quartos",
    "banheiros", "vagas", "condominio", "endereco", "latitude", "longitude",
    "fonte",
]

COLUNAS_FACILITY = [
    "id_facility", "nome", "categoria", "endereco", "latitude", "longitude",
]


# ---------------------------------------------------------------------------
# Construção e limpeza das tabelas
# ---------------------------------------------------------------------------

def construir_tabela_imovel(df_bruto):
    """Constrói e limpa a tabela 'imovel' a partir do dataframe bruto."""

    df = df_bruto.copy()

    # garante presença das colunas do esquema (preenche ausentes com NA)
    for col in COLUNAS_IMOVEL:
        if col not in df.columns:
            df[col] = pd.NA

    df = df[COLUNAS_IMOVEL].copy()

    n0 = len(df)

    # R6: normalização de texto
    for col in ["id_imovel", "tipo", "finalidade", "endereco", "fonte"]:
        df[col] = df[col].astype("string").str.strip()

    # R1: id nulo
    df = df[df["id_imovel"].notna() & (df["id_imovel"] != "")]

    # R2: duplicatas
    df = df.drop_duplicates(subset="id_imovel", keep="first")

    # R3: coerção numérica
    for col in ["preco", "area_m2", "quartos", "banheiros", "vagas",
                "condominio", "latitude", "longitude"]:
        df[col] = pd.to_numeric(df[col], errors="coerce")

    df = df[(df["preco"] > 0) & (df["area_m2"] > 0)]

    # R4: domínio
    df = df[df["tipo"].isin(TIPOS_VALIDOS)]
    df = df[df["finalidade"].isin(FINALIDADES_VALIDAS)]
    df = df[(df["quartos"] >= 0) & (df["banheiros"] >= 0) & (df["vagas"] >= 0)]

    # R5: coordenadas dentro do bbox
    df = df[
        df["latitude"].between(BBOX["lat_min"], BBOX["lat_max"])
        & df["longitude"].between(BBOX["lon_min"], BBOX["lon_max"])
    ]

    df = df.reset_index(drop=True)

    print(f"[limpeza imovel] bruto={n0} -> tratado={len(df)} "
          f"(removidos {n0 - len(df)})")

    return df


def construir_tabela_facility(df_facilities):
    """Constrói e limpa a tabela 'facility' (espera o esquema normalizado).

    Espera as colunas id_facility, nome, categoria, latitude, longitude
    (saída de modelagem_grafo.normalizar_facilities). 'endereco' é opcional.
    """

    df = df_facilities.copy()

    if "endereco" not in df.columns:
        df["endereco"] = pd.NA

    df = df[COLUNAS_FACILITY].copy()

    n0 = len(df)

    # R6
    for col in ["id_facility", "nome", "categoria", "endereco"]:
        df[col] = df[col].astype("string").str.strip()

    # R1 + R2
    df = df[df["id_facility"].notna() & (df["id_facility"] != "")]
    df = df.drop_duplicates(subset="id_facility", keep="first")

    # categoria obrigatória (sem categoria não há aresta válida no grafo)
    df = df[df["categoria"].notna() & (df["categoria"] != "")]

    # R3 coordenadas
    df["latitude"] = pd.to_numeric(df["latitude"], errors="coerce")
    df["longitude"] = pd.to_numeric(df["longitude"], errors="coerce")
    df = df[df["latitude"].notna() & df["longitude"].notna()]

    df = df.reset_index(drop=True)

    print(f"[limpeza facility] bruto={n0} -> tratado={len(df)} "
          f"(removidos {n0 - len(df)})")

    return df


def construir_tabela_categoria(df_facility):
    """Deriva a tabela 'categoria_facility' das categorias presentes."""

    categorias = sorted(df_facility["categoria"].dropna().unique())

    return pd.DataFrame({
        "id_categoria": range(1, len(categorias) + 1),
        "nome_categoria": categorias,
    })


def construir_tabela_proximidade(G, df_imovel, df_facility):
    """Extrai a tabela 'proximidade' do grafo e adiciona tempo_estimado.

    Aplica R7 (integridade referencial): mantém apenas pares cujos ids existem
    nas tabelas imovel e facility já tratadas.
    """

    prox = tabela_proximidade(G)

    # tempo estimado de caminhada (minutos) a partir da distância
    prox["tempo_estimado"] = (
        prox["distancia_metros"] / VELOCIDADE_CAMINHADA_M_MIN
    ).round(2)

    prox = prox[[
        "id_imovel", "id_facility", "distancia_metros",
        "tempo_estimado", "peso_relacional",
    ]]

    # R7: integridade referencial
    ids_imovel = set(df_imovel["id_imovel"])
    ids_facility = set(df_facility["id_facility"])

    n0 = len(prox)

    prox = prox[
        prox["id_imovel"].isin(ids_imovel)
        & prox["id_facility"].isin(ids_facility)
    ].reset_index(drop=True)

    print(f"[limpeza proximidade] bruto={n0} -> tratado={len(prox)} "
          f"(removidos {n0 - len(prox)})")

    return prox


# ---------------------------------------------------------------------------
# Exportação
# ---------------------------------------------------------------------------

def exportar_csv(tabelas, prefixo=""):
    """Exporta um dict {nome: DataFrame} para arquivos CSV."""

    for nome, df in tabelas.items():
        caminho = f"{prefixo}{nome}.csv"
        df.to_csv(caminho, index=False)
        print(f"  CSV salvo: {caminho} ({len(df)} linhas)")


def exportar_sqlite(tabelas, caminho="aguas_claras.db"):
    """Cria um banco SQLite relacional com PKs e FKs.

    Demonstra a estruturação em banco relacional exigida pela orientação,
    com integridade referencial garantida no nível do schema.
    """

    conn = sqlite3.connect(caminho)
    conn.execute("PRAGMA foreign_keys = ON;")

    cur = conn.cursor()

    cur.executescript("""
        DROP TABLE IF EXISTS proximidade;
        DROP TABLE IF EXISTS facility;
        DROP TABLE IF EXISTS imovel;
        DROP TABLE IF EXISTS categoria_facility;

        CREATE TABLE categoria_facility (
            id_categoria   INTEGER PRIMARY KEY,
            nome_categoria TEXT NOT NULL UNIQUE
        );

        CREATE TABLE imovel (
            id_imovel   TEXT PRIMARY KEY,
            tipo        TEXT,
            finalidade  TEXT,
            preco       REAL,
            area_m2     REAL,
            quartos     INTEGER,
            banheiros   INTEGER,
            vagas       INTEGER,
            condominio  REAL,
            endereco    TEXT,
            latitude    REAL,
            longitude   REAL,
            fonte       TEXT
        );

        CREATE TABLE facility (
            id_facility TEXT PRIMARY KEY,
            nome        TEXT,
            categoria   TEXT,
            endereco    TEXT,
            latitude    REAL,
            longitude   REAL,
            FOREIGN KEY (categoria) REFERENCES categoria_facility(nome_categoria)
        );

        CREATE TABLE proximidade (
            id_imovel        TEXT,
            id_facility      TEXT,
            distancia_metros REAL,
            tempo_estimado   REAL,
            peso_relacional  REAL,
            PRIMARY KEY (id_imovel, id_facility),
            FOREIGN KEY (id_imovel)   REFERENCES imovel(id_imovel),
            FOREIGN KEY (id_facility) REFERENCES facility(id_facility)
        );
    """)

    # ordem de inserção respeita as dependências de FK
    tabelas["categoria_facility"].to_sql("categoria_facility", conn,
                                         if_exists="append", index=False)
    tabelas["imovel"].to_sql("imovel", conn, if_exists="append", index=False)
    tabelas["facility"].to_sql("facility", conn, if_exists="append", index=False)
    tabelas["proximidade"].to_sql("proximidade", conn,
                                  if_exists="append", index=False)

    conn.commit()
    conn.close()

    print(f"  Banco SQLite salvo: {caminho}")


# ---------------------------------------------------------------------------
# Dicionário de dados
# ---------------------------------------------------------------------------

DICIONARIO = [
    ("imovel", "id_imovel", "TEXT (PK)", "Identificador único do imóvel"),
    ("imovel", "tipo", "TEXT", "Tipo do imóvel: apartamento ou casa"),
    ("imovel", "finalidade", "TEXT", "Finalidade: aluguel ou venda"),
    ("imovel", "preco", "REAL", "Preço (R$) de venda ou aluguel mensal"),
    ("imovel", "area_m2", "REAL", "Área útil em metros quadrados"),
    ("imovel", "quartos", "INTEGER", "Número de quartos"),
    ("imovel", "banheiros", "INTEGER", "Número de banheiros"),
    ("imovel", "vagas", "INTEGER", "Número de vagas de garagem"),
    ("imovel", "condominio", "REAL", "Valor mensal do condomínio (R$)"),
    ("imovel", "endereco", "TEXT", "Endereço ou rótulo do imóvel"),
    ("imovel", "latitude", "REAL", "Latitude (graus decimais, WGS84)"),
    ("imovel", "longitude", "REAL", "Longitude (graus decimais, WGS84)"),
    ("imovel", "fonte", "TEXT", "Origem do dado (ex.: simulado, portal X)"),
    ("facility", "id_facility", "TEXT (PK)", "Identificador único da facility"),
    ("facility", "nome", "TEXT", "Nome do serviço urbano"),
    ("facility", "categoria", "TEXT (FK)", "Categoria; referencia categoria_facility.nome_categoria"),
    ("facility", "endereco", "TEXT", "Endereço da facility (quando disponível)"),
    ("facility", "latitude", "REAL", "Latitude do centroide (WGS84)"),
    ("facility", "longitude", "REAL", "Longitude do centroide (WGS84)"),
    ("categoria_facility", "id_categoria", "INTEGER (PK)", "Identificador da categoria"),
    ("categoria_facility", "nome_categoria", "TEXT", "Nome da categoria (hospital, school, ...)"),
    ("proximidade", "id_imovel", "TEXT (PK/FK)", "Imóvel; referencia imovel.id_imovel"),
    ("proximidade", "id_facility", "TEXT (PK/FK)", "Facility; referencia facility.id_facility"),
    ("proximidade", "distancia_metros", "REAL", "Distância imóvel-facility (Haversine, m)"),
    ("proximidade", "tempo_estimado", "REAL", "Tempo de caminhada estimado (min)"),
    ("proximidade", "peso_relacional", "REAL", "Peso da aresta w=1/(1+d_km)"),
]


def exportar_dicionario(prefixo=""):
    """Gera o dicionário de dados em CSV e Markdown."""

    df = pd.DataFrame(DICIONARIO,
                      columns=["tabela", "campo", "tipo", "descricao"])

    df.to_csv(f"{prefixo}dicionario_dados.csv", index=False)

    linhas = ["# Dicionário de Dados\n"]

    for tabela in df["tabela"].unique():
        linhas.append(f"\n## Tabela `{tabela}`\n")
        linhas.append("| Campo | Tipo | Descrição |")
        linhas.append("| --- | --- | --- |")
        sub = df[df["tabela"] == tabela]
        for _, r in sub.iterrows():
            linhas.append(f"| {r['campo']} | {r['tipo']} | {r['descricao']} |")

    with open(f"{prefixo}dicionario_dados.md", "w", encoding="utf-8") as f:
        f.write("\n".join(linhas) + "\n")

    print(f"  Dicionário salvo: {prefixo}dicionario_dados.csv / .md")

    return df


# ---------------------------------------------------------------------------
# Orquestração
# ---------------------------------------------------------------------------

def persistir_tudo(df_bruto_imoveis, df_facilities, G, prefixo=""):
    """Constrói, limpa, exporta (CSV + SQLite) e documenta todas as tabelas."""

    print("Estruturando dados no modelo relacional...")

    t_imovel = construir_tabela_imovel(df_bruto_imoveis)
    t_facility = construir_tabela_facility(df_facilities)
    t_categoria = construir_tabela_categoria(t_facility)
    t_prox = construir_tabela_proximidade(G, t_imovel, t_facility)

    tabelas = {
        "categoria_facility": t_categoria,
        "imovel": t_imovel,
        "facility": t_facility,
        "proximidade": t_prox,
    }

    exportar_csv(tabelas, prefixo=prefixo)
    exportar_sqlite(tabelas, caminho=f"{prefixo}aguas_claras.db")
    exportar_dicionario(prefixo=prefixo)

    return tabelas


if __name__ == "__main__":

    from scraper_imoveis import scrape_aguas_claras
    from modelagem_grafo import (
        _dados_sinteticos,
        normalizar_imoveis,
        construir_grafo,
    )

    print("=== Teste de persistência relacional (dados sintéticos) ===\n")

    # imóveis ricos do scraper simulado
    df_bruto = scrape_aguas_claras(num_imoveis=30, seed=7)

    # facilities sintéticas (já no esquema normalizado)
    _, df_facilities = _dados_sinteticos()

    # grafo usando os mesmos ids
    df_imoveis_norm = normalizar_imoveis(df_bruto)
    G = construir_grafo(df_imoveis_norm, df_facilities)

    print()
    tabelas = persistir_tudo(df_bruto, df_facilities, G)

    print("\n--- Amostra: tabela imovel ---")
    print(tabelas["imovel"].head().to_string(index=False))

    print("\n--- Amostra: tabela proximidade ---")
    print(tabelas["proximidade"].head().to_string(index=False))

    print("\n--- categoria_facility ---")
    print(tabelas["categoria_facility"].to_string(index=False))

    # verificação de integridade no banco
    import sqlite3
    conn = sqlite3.connect("aguas_claras.db")
    conn.execute("PRAGMA foreign_keys = ON;")
    viol = conn.execute("PRAGMA foreign_key_check;").fetchall()
    cont = {
        t: conn.execute(f"SELECT COUNT(*) FROM {t}").fetchone()[0]
        for t in ["categoria_facility", "imovel", "facility", "proximidade"]
    }
    conn.close()

    print(f"\nContagem no SQLite: {cont}")
    print(f"Violações de FK: {len(viol)}")
