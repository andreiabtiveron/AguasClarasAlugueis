import pandas as pd
import numpy as np


def scrape_aguas_claras(num_imoveis=50, seed=None):
    """Gera um dataset simulado de imóveis em Águas Claras.

    LIMITAÇÃO METODOLÓGICA: estes dados são SIMULADOS (dado bruto sintético),
    não coletados de portais reais. Servem para demonstrar o pipeline de
    estruturação relacional e modelagem em grafo sem depender de scraping
    externo. A substituição por coleta real (web scraping / base pública)
    é um passo futuro previsto na orientação.

    As colunas seguem o esquema da tabela 'imovel' do trabalho:
    id_imovel, tipo, finalidade, preco, area_m2, quartos, banheiros, vagas,
    condominio, endereco, latitude, longitude, fonte. Também são mantidos os
    aliases 'coords' e 'area' por compatibilidade com o restante do pipeline.
    """

    print("Gerando dataset de imóveis simulados...")

    rng = np.random.default_rng(seed)

    # centro aproximado de Águas Claras
    lat_centro = -15.839
    lon_centro = -48.025

    dados = []

    for i in range(num_imoveis):

        lat = lat_centro + rng.uniform(-0.01, 0.01)
        lon = lon_centro + rng.uniform(-0.01, 0.01)

        tipo = rng.choice(["apartamento", "casa"], p=[0.8, 0.2])
        finalidade = rng.choice(["venda", "aluguel"], p=[0.6, 0.4])

        area = int(rng.integers(40, 120))
        quartos = int(rng.integers(1, 5))
        banheiros = int(rng.integers(1, quartos + 2))
        vagas = int(rng.integers(0, 3))

        if finalidade == "venda":
            preco = int(rng.integers(250000, 900000))
        else:
            preco = int(rng.integers(1500, 6000))

        condominio = int(rng.integers(300, 1200)) if tipo == "apartamento" else 0

        dados.append({
            "id_imovel": f"imovel_{i}",
            "tipo": tipo,
            "finalidade": finalidade,
            "preco": preco,
            "area_m2": area,
            "quartos": quartos,
            "banheiros": banheiros,
            "vagas": vagas,
            "condominio": condominio,
            "endereco": f"Imovel_{i}_AguasClaras",
            "latitude": lat,
            "longitude": lon,
            "fonte": "simulado",
            # aliases por compatibilidade com geocodificacao/modelagem/mapa
            "area": area,
            "coords": (lat, lon),
        })

    df = pd.DataFrame(dados)

    print(f"{len(df)} imóveis gerados")

    return df
