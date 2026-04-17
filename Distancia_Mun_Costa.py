import streamlit as st
import geopandas as gpd
import pandas as pd
from shapely.geometry import Point
import os
import pydeck as pdk # Biblioteca para mapas avançados

st.set_page_config(page_title="Calculador Costeiro - IBAMA", layout="wide")

st.title("📏 Cálculo de Menor Distância e Traçado à Costa")

@st.cache_data
def carregar_dados():
    gdf = gpd.read_parquet("Munic_Mar_Sud_Pontos.parquet").reset_index(drop=True)
    if gdf.crs is None:
        gdf.set_crs(epsg=4326, inplace=True)
    return gdf

if not os.path.exists("Munic_Mar_Sud_Pontos.parquet"):
    st.error("Arquivo Parquet não encontrado!")
else:
    gdf_costa = carregar_dados()

    # Sidebar
    st.sidebar.header("Coordenadas de Entrada")
    user_lat = st.sidebar.number_input("Latitude", format="%.6f", value=-23.0)
    user_lon = st.sidebar.number_input("Longitude", format="%.6f", value=-43.0)

    if st.sidebar.button("Calcular e Traçar Linha"):
        # 1. Cálculos de Distância (Métrico EPSG:5880)
        ponto_usuario_geo = Point(user_lon, user_lat)
        ponto_usuario_met = gpd.GeoSeries([ponto_usuario_geo], crs="EPSG:4326").to_crs(epsg=5880).iloc[0]
        
        gdf_proj = gdf_costa.to_crs(epsg=5880)
        distancias = gdf_proj.distance(ponto_usuario_met)
        idx_minimo = distancias.idxmin()
        distancia_km = distancias.min() / 1000
        
        # 2. Obter coordenadas do ponto de destino (Costa)
        ponto_costa_geo = gdf_costa.iloc[idx_minimo].geometry
        resultado = gdf_costa.loc[idx_minimo]

        # Resultados em texto
        st.success(f"### Distância: {distancia_km:.2f} km")
        c1, c2 = st.columns(2)
        c1.metric("Município da Costa", str(resultado['NM_MUN']))
        c2.metric("Sigla UF", str(resultado['SIGLA']))

        # --- CONFIGURAÇÃO DO MAPA COM PYDECK ---
        
        # Dados para a linha (origem e destino)
        dados_linha = [{
            "start": [user_lon, user_lat],
            "end": [ponto_costa_geo.x, ponto_costa_geo.y],
            "name": "Trajeto à Costa"
        }]

        # Camada da Linha
        layer_linha = pdk.Layer(
            "LineLayer",
            dados_linha,
            get_source_position="start",
            get_target_position="end",
            get_color=[255, 0, 0, 200], # Vermelho
            get_width=3,
        )

        # Camada dos Pontos (Input e Costa)
        dados_pontos = pd.DataFrame([
            {"lon": user_lon, "lat": user_lat, "tipo": "Entrada", "color": [255, 255, 255]},
            {"lon": ponto_costa_geo.x, "lat": ponto_costa_geo.y, "tipo": "Costa", "color": [0, 255, 0]}
        ])

        layer_pontos = pdk.Layer(
            "ScatterplotLayer",
            dados_pontos,
            get_position="[lon, lat]",
            get_color="color",
            get_radius=1000, # Raio em metros
        )

        # Renderização do Mapa
        view_state = pdk.ViewState(
            longitude=(user_lon + ponto_costa_geo.x) / 2,
            latitude=(user_lat + ponto_costa_geo.y) / 2,
            zoom=8,
            pitch=0
        )

        st.pydeck_chart(pdk.Deck(
            layers=[layer_linha, layer_pontos],
            initial_view_state=view_state,
            tooltip={"text": "{tipo}"},
            map_style="mapbox://styles/mapbox/light-v9" # Estilo claro para melhor contraste
        ))

        with st.expander("Ver coordenadas dos vértices"):
            st.write(f"**Início (Input):** {user_lat}, {user_lon}")
            st.write(f"**Fim (Costa):** {ponto_costa_geo.y}, {ponto_costa_geo.x}")
