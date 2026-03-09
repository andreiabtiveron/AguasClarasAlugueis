import osmnx as ox
import geopandas as gpd

def obter_infra_aguas_claras():

    local = "Águas Claras, Brasília, Brazil"

    tags = {
        'amenity': ['hospital', 'school', 'university', 'pharmacy'],
        'leisure': ['park', 'recreation_ground']
    }

    print("Baixando dados do OpenStreetMap...")

    gdf = ox.features_from_place(local, tags)

    gdf = gdf.reset_index()

    gdf = gdf[['name', 'amenity', 'leisure', 'geometry']]

    # projetar para calcular centroid 
    gdf = gdf.to_crs(epsg=3857)

    gdf['geometry'] = gdf.geometry.centroid

    gdf = gdf.to_crs(epsg=4326)

    return gdf