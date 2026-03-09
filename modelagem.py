import numpy as np
from scipy.spatial.distance import cdist


class MotorUrbano:

    def __init__(self, beta=1.5):

        self.beta = beta

    def calcular_acessibilidade(self, df_imoveis, gdf_servicos):

        coords_imoveis = np.array(df_imoveis["coords"].tolist())

        coords_servicos = np.array([
            (p.y, p.x) for p in gdf_servicos.geometry
        ])

        dist_matriz = cdist(coords_imoveis, coords_servicos, metric="euclidean")

        acess_matriz = 1 / (dist_matriz + 0.0005) ** self.beta

        categorias = ["hospital", "school", "park", "pharmacy"]

        for cat in categorias:

            indices_cat = gdf_servicos.index[
                (gdf_servicos["amenity"] == cat)
                | (gdf_servicos["leisure"] == cat)
            ].tolist()

            if len(indices_cat) > 0:

                df_imoveis[f"acess_{cat}"] = acess_matriz[:, indices_cat].sum(axis=1)

            else:

                df_imoveis[f"acess_{cat}"] = 0

        return df_imoveis

    def normalizar(self, df, colunas):

        for col in colunas:

            min_val = df[col].min()
            max_val = df[col].max()

            if max_val != min_val:

                df[col] = 0.01 + (df[col] - min_val) / (max_val - min_val)

            else:

                df[col] = 0.5

        return df

    def gerar_scores_finais(self, df):

        pesos = {
            "hospital": 0.4,
            "school": 0.3,
            "park": 0.2,
            "pharmacy": 0.1
        }

        cols = [f"acess_{c}" for c in pesos.keys()]

        df = self.normalizar(df, cols)

        df["IAR"] = (
            df["acess_hospital"] * pesos["hospital"]
            + df["acess_school"] * pesos["school"]
            + df["acess_park"] * pesos["park"]
            + df["acess_pharmacy"] * pesos["pharmacy"]
        )

        df["QV"] = (
            df["acess_hospital"] ** pesos["hospital"]
            * df["acess_school"] ** pesos["school"]
            * df["acess_park"] ** pesos["park"]
            * df["acess_pharmacy"] ** pesos["pharmacy"]
        )

        return df