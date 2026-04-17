# -*- coding: utf-8 -*-

import streamlit as st
import geopandas as gpd
import pandas as pd
from shapely.geometry import Point
import os

st.set_page_config(page_title="Calculador de Proximidade Costeira", layout="wide")

st.title("📏 Cálculo de Menor Distância à Costa")
st.write("Determine o município costeiro mais próximo de qualquer ponto.")

# Função para carregar os dados (com cache para ser instantâneo após o primeiro load)
@st.cache_data
def carregar_dados(caminho_shp):
    # O geopandas lê o .shp mas precisa do .dbf e .shx na mesma pasta
    gdf = gpd.read_file(caminho_shp)
    # Garante que o sistema de coordenadas original é WGS84 (Lat/Lon)
    if gdf.crs is None:
        gdf.set_crs(epsg=4326, inplace=True)
    return gdf

# Caminho para o seu arquivo
arquivo_shp = "Munic_Mar_Sud_Pontos.shp"

if not os.path.exists(arquivo_shp):
    st.error(f"Erro: O ficheiro '{arquivo_shp}' não foi encontrado. Verifique se os ficheiros .shp, .shx e .dbf estão na mesma pasta.")
else:
    gdf_costa = carregar_dados(arquivo_shp)

    # Sidebar para entrada de coordenadas
    st.sidebar.header("Coordenadas do Ponto")
    user_lat = st.sidebar.number_input("Latitude (ex: -23.01)", format="%.6f", value=-23.0)
    user_lon = st.sidebar.number_input("Longitude (ex: -43.15)", format="%.6f", value=-43.0)

    if st.sidebar.button("Calcular"):
        # 1. Criar o ponto do utilizador e projetar para métrico (EPSG:5880)
        # Usamos 5880 para garantir que o cálculo da distância em metros seja preciso no Brasil
        ponto_usuario = gpd.GeoSeries([Point(user_lon, user_lat)], crs="EPSG:4326").to_crs(epsg=5880).iloc[0]
        
        # 2. Projetar o shapefile da costa para o mesmo sistema métrico
        gdf_proj = gdf_costa.to_crs(epsg=5880)

        # 3. Calcular a distância de todos os pontos da costa ao ponto do utilizador
        distancias = gdf_proj.distance(ponto_usuario)
        
        # 4. Encontrar o índice da menor distância
        idx_minimo = distancias.idxmin()
        menor_distancia_km = distancias.min() / 1000
        
        # 5. Recuperar os dados do ponto mais próximo
        resultado = gdf_costa.iloc[idx_minimo]
        
        # Exibição dos resultados
        st.success(f"### Distância calculada: {menor_distancia_km:.2f} km")
        
        col1, col2 = st.columns(2)
        with col1:
            st.metric("Município", resultado.get('NM_MUN', 'Não encontrado')) # Ajuste 'NM_MUN' se o nome da coluna for diferente
        with col2:
            st.metric("UF", resultado.get('SIGLA_UF', 'Não encontrado'))

        # Mostrar mapa simples
        df_mapa = pd.DataFrame({'lat': [user_lat], 'lon': [user_lon]})
        st.map(df_mapa)

st.info("Nota técnica: O cálculo utiliza a distância euclidiana (linha reta) após projeção para o sistema SIRGAS 2000 / Brazil Polyconic.")