import streamlit as st
import geopandas as gpd
import pandas as pd
from shapely.geometry import Point
import os
import pydeck as pdk

# --- FUNÇÃO AUXILIAR DE CONVERSÃO ---
def gms_para_decimal(graus, minutos, segundos, direcao):
    decimal = float(graus) + float(minutos)/60 + float(segundos)/3600
    if direcao in ['S', 'W', 'O']:
        decimal = -decimal
    return decimal

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

    # --- BARRA LATERAL: ENTRADA DE DADOS ---
    st.sidebar.header("Configurações de Entrada")
    tipo_input = st.sidebar.radio("Formato das Coordenadas:", ("Decimal", "GMS (Graus, Min, Seg)"))

    if tipo_input == "Decimal":
        user_lat = st.sidebar.number_input("Latitude", format="%.6f", value=-23.0)
        user_lon = st.sidebar.number_input("Longitude", format="%.6f", value=-43.0)
    else:
        st.sidebar.subheader("Latitude")
        col_lat1, col_lat2, col_lat3 = st.sidebar.columns(3)
        lat_g = col_lat1.number_input("G", value=23, step=1, key="lat_g")
        lat_m = col_lat2.number_input("M", value=0, step=1, key="lat_m")
        lat_s = col_lat3.number_input("S", value=0.0, step=0.1, format="%.2f", key="lat_s")
        lat_dir = st.sidebar.selectbox("Direção Lat", ["S", "N"], index=0)
        
        st.sidebar.subheader("Longitude")
        col_lon1, col_lon2, col_lon3 = st.sidebar.columns(3)
        lon_g = col_lon1.number_input("G", value=43, step=1, key="lon_g")
        lon_m = col_lon2.number_input("M", value=0, step=1, key="lon_m")
        lon_s = col_lon3.number_input("S", value=0.0, step=0.1, format="%.2f", key="lon_s")
        lon_dir = st.sidebar.selectbox("Direção Lon", ["W", "E"], index=0)

        user_lat = gms_para_decimal(lat_g, lat_m, lat_s, lat_dir)
        user_lon = gms_para_decimal(lon_g, lon_m, lon_s, lon_dir)
        
        st.sidebar.info(f"Convertido: {user_lat:.6f}, {user_lon:.6f}")

    if st.sidebar.button("Calcular e Visualizar"):
        # 1. PROCESSAMENTO GEOGRÁFICO
        ponto_usuario_geo = Point(user_lon, user_lat)
        ponto_usuario_met = gpd.GeoSeries([ponto_usuario_geo], crs="EPSG:4326").to_crs(epsg=5880).iloc[0]
        gdf_proj = gdf_costa.to_crs(epsg=5880)
        
        distancias = gdf_proj.distance(ponto_usuario_met)
        idx_minimo = distancias.idxmin()
        distancia_km = distancias.min() / 1000
        
        resultado = gdf_costa.iloc[idx_minimo]
        ponto_costa_geo = resultado.geometry

        # 2. EXIBIÇÃO DOS RESULTADOS
        st.success(f"### 📍 Resultado do Cálculo")
        col_m1, col_m2, col_m3 = st.columns(3)
        col_m1.metric("Distância", f"{distancia_km:.2f} km")
        col_m2.metric("Município da Costa", str(resultado['NM_MUN']))
        col_m3.metric("UF", str(resultado['SIGLA']))

        # 3. MAPA (PYDECK)
        dados_linha = [{"start": [user_lon, user_lat], "end": [ponto_costa_geo.x, ponto_costa_geo.y]}]
        
        layer_linha = pdk.Layer(
            "LineLayer", dados_linha,
            get_source_position="start", get_target_position="end",
            get_color=[230, 0, 0, 200], get_width=2,
            width_units="pixels", width_min_pixels=2, width_max_pixels=2,
        )

        dados_pontos = pd.DataFrame([
            {"lon": user_lon, "lat": user_lat, "local": "Ponto de Entrada", "cor": [0, 0, 255]},
            {"lon": ponto_costa_geo.x, "lat": ponto_costa_geo.y, "local": f"Costa: {resultado['NM_MUN']}", "cor": [0, 150, 0]}
        ])

        layer_pontos = pdk.Layer(
            "ScatterplotLayer", dados_pontos,
            get_position="[lon, lat]", get_fill_color="cor",
            get_radius=8, radius_units="pixels", radius_min_pixels=5, radius_max_pixels=15,
            pickable=True,
        )

        view_state = pdk.ViewState(
            longitude=(user_lon + ponto_costa_geo.x) / 2,
            latitude=(user_lat + ponto_costa_geo.y) / 2,
            zoom=8, pitch=0
        )

        st.pydeck_chart(pdk.Deck(
            map_style=None,
            initial_view_state=view_state,
            layers=[layer_linha, layer_pontos],
            tooltip={"html": "<b>{local}</b>"}
        ))

    # Adicione isso ao final do seu bloco da barra lateral (st.sidebar)
    st.sidebar.markdown("---")
    st.sidebar.markdown(
        """
        **Desenvolvido por:** [Seu Nome Aqui]  
        *Analista Ambiental - IBAMA/Ceneac* """
    )
