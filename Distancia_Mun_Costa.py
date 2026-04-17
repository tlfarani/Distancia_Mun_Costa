import streamlit as st
import geopandas as gpd
import pandas as pd
from shapely.geometry import Point
import os

# Configuração da página
st.set_page_config(page_title="Calculador Costeiro - IBAMA", layout="centered")

st.title("📏 Cálculo de Menor Distância à Costa")
st.write("Encontre o município costeiro mais próximo a partir de coordenadas.")

@st.cache_data
def carregar_dados():
    # Carrega o Parquet e reseta o índice para garantir a busca correta pelo idxmin()
    gdf = gpd.read_parquet("Munic_Mar_Sud_Pontos.parquet").reset_index(drop=True)
    # Garante que o CRS inicial seja WGS84
    if gdf.crs is None:
        gdf.set_crs(epsg=4326, inplace=True)
    return gdf

# Caminho do arquivo
caminho_parquet = "Munic_Mar_Sud_Pontos.parquet"

if not os.path.exists(caminho_parquet):
    st.error(f"Arquivo '{caminho_parquet}' não encontrado no repositório GitHub.")
else:
    gdf_costa = carregar_dados()

    # Entrada de Coordenadas
    st.sidebar.header("Coordenadas de Entrada")
    user_lat = st.sidebar.number_input("Latitude", format="%.6f", value=-23.0)
    user_lon = st.sidebar.number_input("Longitude", format="%.6f", value=-43.0)

    if st.sidebar.button("Calcular Ponto Próximo"):
        # 1. Projeção métrica para cálculo preciso em KM (SIRGAS 2000 Polyconic)
        ponto_usuario = gpd.GeoSeries([Point(user_lon, user_lat)], crs="EPSG:4326").to_crs(epsg=5880).iloc[0]
        gdf_proj = gdf_costa.to_crs(epsg=5880)

        # 2. Cálculo da menor distância
        distancias = gdf_proj.distance(ponto_usuario)
        idx_minimo = distancias.idxmin()
        distancia_km = distancias.min() / 1000
        
        # 3. Busca os dados exatos usando o índice encontrado
        resultado = gdf_costa.loc[idx_minimo]
        
        # Exibição dos Resultados
        st.success(f"### Distância: {distancia_km:.2f} km")
        
        col1, col2 = st.columns(2)
        with col1:
            st.metric("Município da Costa", str(resultado['NM_MUN']))
        with col2:
            st.metric("Sigla UF", str(resultado['SIGLA']))

        # Mapa de referência
        st.subheader("Localização da Entrada")
        df_mapa = pd.DataFrame({'lat': [user_lat], 'lon': [user_lon]})
        st.map(df_mapa)

        # Detalhes adicionais
        with st.expander("Ver todos os detalhes do ponto na costa"):
            # Mostra todas as colunas que você listou para este ponto específico
            st.write(pd.DataFrame(resultado).T.drop(columns='geometry'))

st.divider()
st.caption("Desenvolvido para análise de proximidade costeira - Base de dados: Munic_Mar_Sud_Pontos")
