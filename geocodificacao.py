from scipy.spatial.distance import cdist
import numpy as np


def calcular_indices_reais(df_imoveis, gdf_servicos):

    if "coords" not in df_imoveis.columns:
        print("Nenhuma coordenada encontrada.")
        return df_imoveis

    coords_imoveis = np.array(df_imoveis["coords"].tolist())

    coords_servicos = np.array([
        (p.y, p.x) for p in gdf_servicos.geometry
    ])

    print("Calculando matriz de distâncias...")

    dist_matriz = cdist(coords_imoveis, coords_servicos, metric="euclidean")

    df_imoveis["score_acessibilidade"] = 1 / (dist_matriz.min(axis=1) + 0.001)

    return df_imoveis