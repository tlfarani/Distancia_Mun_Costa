import streamlit as st
import geopandas as gpd
import pandas as pd
from shapely.geometry import Point
import os

st.set_page_config(page_title="Calculador Costeiro IBAMA", layout="wide")

st.title("📏 Cálculo de Menor Distância à Costa")

@st.cache_data
def carregar_dados():
    # Lendo o Parquet (muito mais rápido e leve)
    gdf = gpd.read_parquet("Munic_Mar_Sud_Pontos.parquet")
    if gdf.crs is None:
        gdf.set_crs(epsg=4326, inplace=True)
    return gdf

if not os.path.exists("Munic_Mar_Sud_Pontos.parquet"):
    st.error("Arquivo 'Munic_Mar_Sud_Pontos.parquet' não encontrado. Converta o shapefile primeiro!")
else:
    gdf_costa = carregar_dados()

    # Inputs
    st.sidebar.header("Coordenadas de Entrada")
    user_lat = st.sidebar.number_input("Latitude", format="%.6f", value=-23.0)
    user_lon = st.sidebar.number_input("Longitude", format="%.6f", value=-43.0)

    if st.sidebar.button("Calcular Ponto mais Próximo"):
        # 1. Projeção métrica para cálculo preciso em KM (SIRGAS 2000 Polyconic)
        ponto_usuario = gpd.GeoSeries([Point(user_lon, user_lat)], crs="EPSG:4326").to_crs(epsg=5880).iloc[0]
        gdf_proj = gdf_costa.to_crs(epsg=5880)

        # 2. Cálculo da distância
        distancias = gdf_proj.distance(ponto_usuario)
        idx_minimo = distancias.idxmin()
        distancia_km = distancias.min() / 1000
        
        # 3. Pegar a linha correspondente no dado original
        resultado = gdf_costa.iloc[idx_minimo]
        
        st.success(f"### Distância: {distancia_km:.2f} km")

        # 4. Exibição Inteligente (Tenta achar a coluna certa)
        col1, col2 = st.columns(2)
        
        # Procura por colunas que contenham 'MUN' ou 'UF'
        col_mun = [c for c in gdf_costa.columns if 'MUN' in c.upper()]
        col_uf = [c for c in gdf_costa.columns if 'UF' in c.upper() or 'ESTADO' in c.upper()]

        with col1:
            valor_mun = resultado[col_mun[0]] if col_mun else "Não encontrada"
            st.metric("Município da Costa", valor_mun)
        with col2:
            valor_uf = resultado[col_uf[0]] if col_uf else "Não encontrada"
            st.metric("UF", valor_uf)

        # Mostra os dados brutos da linha encontrada para conferência
        with st.expander("Ver detalhes do ponto encontrado no Shapefile"):
            st.write(resultado.drop('geometry'))
