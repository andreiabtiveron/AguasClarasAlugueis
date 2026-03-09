import folium
import pandas as pd
import branca.colormap as cm
import webbrowser

def gerar_mapa_aguas_claras(df_final, gdf_servicos):

    lat_centro = -15.8390
    lon_centro = -48.0250

    m = folium.Map(
        location=[lat_centro, lon_centro],
        zoom_start=15,
        tiles="cartodbpositron"
    )

    cores_servicos = {
        "hospital": "red",
        "school": "blue",
        "park": "green",
        "pharmacy": "orange"
    }

    for _, row in gdf_servicos.iterrows():

        tipo = row["amenity"] if pd.notna(row["amenity"]) else "park"

        cor = cores_servicos.get(tipo, "gray")

        nome = row["name"] if pd.notna(row["name"]) else "Serviço"

        folium.Marker(
            location=[row.geometry.y, row.geometry.x],
            popup=f"{nome}",
            icon=folium.Icon(color=cor)
        ).add_to(m)

    colormap = cm.LinearColormap(
        colors=["yellow", "orange", "red"],
        vmin=df_final["QV"].min(),
        vmax=df_final["QV"].max()
    )

    for _, row in df_final.iterrows():

        folium.CircleMarker(
            location=[row["coords"][0], row["coords"][1]],
            radius=7,
            color=colormap(row["QV"]),
            fill=True,
            fill_opacity=0.7,
            popup=(
                f"Preço: {row['preco']}<br>"
                f"Área: {row['area']}<br>"
                f"QV: {row['QV']:.3f}"
            )
        ).add_to(m)

    colormap.caption = "Qualidade de Vida Urbana"
    colormap.add_to(m)


    m.save("mapa_qualidade_vida_ac.html")

    print("Mapa salvo: mapa_qualidade_vida_ac.html")

    webbrowser.open("mapa_qualidade_vida_ac.html")

    return m