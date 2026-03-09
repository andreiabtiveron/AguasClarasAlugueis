import pandas as pd
import numpy as np


def scrape_aguas_claras(num_imoveis=50):

    print("Gerando dataset de imóveis simulados...")

    # centro aproximado de Águas Claras
    lat_centro = -15.839
    lon_centro = -48.025

    dados = []

    for i in range(num_imoveis):

        lat = lat_centro + np.random.uniform(-0.01, 0.01)
        lon = lon_centro + np.random.uniform(-0.01, 0.01)

        preco = np.random.randint(250000, 900000)

        area = np.random.randint(40, 120)

        endereco = f"Imovel_{i}_AguasClaras"

        dados.append({
            "preco": preco,
            "area": area,
            "endereco": endereco,
            "coords": (lat, lon)
        })

    df = pd.DataFrame(dados)

    print(f"{len(df)} imóveis gerados")

    return df