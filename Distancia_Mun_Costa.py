import streamlit as st
import geopandas as gpd
import pandas as pd
from shapely.geometry import Point
import os
import pydeck as pdk

st.set_page_config(page_title="Calculador de Distância Costeira", layout="wide")

st.title("📏 Cálculo de Menor Distância e Traçado à Costa")

@st.cache_data
def carregar_dados():
    # Carrega o Parquet e garante o CRS
    gdf = gpd.read_parquet("Munic_Mar_Sud_Pontos.parquet").reset_index(drop=True)
    if gdf.crs is None:
        gdf.set_crs(epsg=4326, inplace=True)
    return gdf

if not os.path.exists("Munic_Mar_Sud_Pontos.parquet"):
    st.error("Arquivo Parquet não encontrado no repositório!")
else:
    gdf_costa = carregar_dados()

    # Barra Lateral
    st.sidebar.header("Coordenadas de Entrada")
    user_lat = st.sidebar.number_input("Latitude", format="%.6f", value=-23.0)
    user_lon = st.sidebar.number_input("Longitude", format="%.6f", value=-43.0)

    if st.sidebar.button("Calcular e Visualizar"):
        # --- 1. PROCESSAMENTO GEOGRÁFICO ---
        ponto_usuario_geo = Point(user_lon, user_lat)
        
        # Projeção métrica (SIRGAS 2000 Polyconic) para cálculo de KM
        ponto_usuario_met = gpd.GeoSeries([ponto_usuario_geo], crs="EPSG:4326").to_crs(epsg=5880).iloc[0]
        gdf_proj = gdf_costa.to_crs(epsg=5880)
        
        distancias = gdf_proj.distance(ponto_usuario_met)
        idx_minimo = distancias.idxmin()
        distancia_km = distancias.min() / 1000
        
        # Dados do ponto de destino
        resultado = gdf_costa.iloc[idx_minimo]
        ponto_costa_geo = resultado.geometry

        # --- 2. EXIBIÇÃO DOS RESULTADOS (TEXTO) ---
        # Colocamos o texto antes do mapa para garantir que seja lido
        st.success(f"### 📍 Resultado do Cálculo")
        
        col_m1, col_m2, col_m3 = st.columns(3)
        col_m1.metric("Distância", f"{distancia_km:.2f} km")
        col_m2.metric("Município da Costa", str(resultado['NM_MUN']))
        col_m3.metric("UF", str(resultado['SIGLA']))

        # --- 3. CONFIGURAÇÃO DO MAPA (PYDECK) ---
        
        # Camada de Linha
        dados_linha = [{
            "start": [user_lon, user_lat],
            "end": [ponto_costa_geo.x, ponto_costa_geo.y]
        }]
                
        # Camada de Linha corrigida para evitar o efeito de "bloco"
        layer_linha = pdk.Layer(
            "LineLayer",
            dados_linha,
            get_source_position="start",
            get_target_position="end",
            get_color=[230, 0, 0, 200], # Vermelho com leve transparência
            get_width=2,                # Valor base da largura
            width_units="pixels",       # Define a unidade como pixels
            width_min_pixels=2,         # Força a largura mínima em 2px (não some ao tirar o zoom)
            width_max_pixels=2,         # Força a largura máxima em 2px (não vira um bloco ao dar zoom)
            pickable=True,
        )

        # Camada de Pontos com nomes para o Tooltip
        # Camada de Pontos com tamanho em pixels para escala dinâmica
        dados_pontos = pd.DataFrame([
            {"lon": user_lon, "lat": user_lat, "local": "Ponto de Origem", "cor": [0, 0, 255]}, 
            {"lon": ponto_costa_geo.x, "lat": ponto_costa_geo.y, "local": f"Costa: {resultado['NM_MUN']}", "cor": [0, 150, 0]}
        ])
        
        layer_pontos = pdk.Layer(
            "ScatterplotLayer",
            dados_pontos,
            get_position="[lon, lat]",
            get_fill_color="cor",
            # Alterações aqui:
            get_radius=8,           # Tamanho base em pixels
            radius_units="pixels",  # Faz com que o ponto use pixels da tela, não metros no mapa
            radius_min_pixels=5,    # Garante que ele não suma ao tirar muito o zoom
            radius_max_pixels=15,   # Garante que ele não cresça demais ao dar muito zoom
            pickable=True,
        )

        # Estado inicial da visão (centralizado entre os pontos)
        view_state = pdk.ViewState(
            longitude=(user_lon + ponto_costa_geo.x) / 2,
            latitude=(user_lat + ponto_costa_geo.y) / 2,
            zoom=9,
            pitch=0
        )

        # Renderização do Mapa
        st.pydeck_chart(pdk.Deck(
            map_style=None, # Usa o padrão do sistema se o estilo 'light' falhar
            initial_view_state=view_state,
            layers=[layer_linha, layer_pontos],
            tooltip={
                "html": "<b>{local}</b>",
                "style": {"backgroundColor": "steelblue", "color": "white", "fontSize": "12px"}
            }
        ))

        with st.expander("Ver detalhes técnicos do ponto"):
            st.write(resultado.drop('geometry'))
