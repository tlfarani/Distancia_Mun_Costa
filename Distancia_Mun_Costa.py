import streamlit as st
import geopandas as gpd
import pandas as pd
from shapely.geometry import Point
from shapely.ops import nearest_points
import pydeck as pdk
import os

# --- CONFIGURAÇÃO DA PÁGINA ---
st.set_page_config(page_title="Calculador Costeiro Nacional - IBAMA", layout="wide")

# --- FUNÇÃO AUXILIAR DE CONVERSÃO ---
def gms_para_decimal(graus, minutos, segundos, direcao):
    decimal = float(graus) + float(minutos)/60 + float(segundos)/3600
    if direcao in ['S', 'W', 'O']:
        decimal = -decimal
    return decimal

# --- CARREGAMENTO DE DADOS (CACHE) ---
@st.cache_data
def carregar_dados():
    if not os.path.exists("costa_brasil_2024.parquet"):
        return None
    gdf = gpd.read_parquet("costa_brasil_2024.parquet")
    if gdf.crs is None:
        gdf.set_crs(epsg=4326, inplace=True)
    return gdf

# --- INTERFACE PRINCIPAL ---
st.title("📏 Distância à Costa Brasileira (IBGE 2024)")
st.markdown("""
Esta ferramenta calcula a menor distância entre um ponto e a linha de costa de qualquer município defrontante com o mar no Brasil.
""")

gdf_costa = carregar_dados()

if gdf_costa is None:
    st.error("Erro: Arquivo 'costa_brasil_2024.parquet' não encontrado. Execute o script de preparação primeiro.")
    st.stop()

# --- BARRA LATERAL ---
st.sidebar.header("Configurações de Entrada")
tipo_input = st.sidebar.radio("Formato das Coordenadas:", ("Decimal", "GMS (Graus, Min, Seg)"))

if tipo_input == "Decimal":
    user_lat = st.sidebar.number_input("Latitude (ex: -23.123)", format="%.6f", value=-23.5000)
    user_lon = st.sidebar.number_input("Longitude (ex: -42.123)", format="%.6f", value=-43.0000)
else:
    col_lat1, col_lat2, col_lat3 = st.sidebar.columns(3)
    lat_g = col_lat1.number_input("Lat G", value=23, step=1)
    lat_m = col_lat2.number_input("M", value=0, step=1)
    lat_s = col_lat3.number_input("S", value=0.0, format="%.2f")
    lat_dir = st.sidebar.selectbox("Dir Lat", ["S", "N"], index=0)
    
    col_lon1, col_lon2, col_lon3 = st.sidebar.columns(3)
    lon_g = col_lon1.number_input("Lon G", value=43, step=1)
    lon_m = col_lon2.number_input("M", value=0, step=1)
    lon_s = col_lon3.number_input("S", value=0.0, format="%.2f")
    lon_dir = st.sidebar.selectbox("Dir Lon", ["W", "E"], index=0)

    user_lat = gms_para_decimal(lat_g, lat_m, lat_s, lat_dir)
    user_lon = gms_para_decimal(lon_g, lon_m, lon_s, lon_dir)

st.sidebar.markdown("---")
calcular = st.sidebar.button("Calcular Menor Distância", use_container_width=True)

# --- LÓGICA DE CÁLCULO ---
if calcular:
    ponto_usuario_geo = Point(user_lon, user_lat)
    
    # 1. Encontrar o polígono municipal mais próximo (Índice Espacial)
    # Retorna o índice da linha no GeoDataFrame
    idx_vizinho = gdf_costa.sindex.nearest(ponto_usuario_geo)[1][0]
    municipio_alvo = gdf_costa.iloc[idx_vizinho]
    
    # 2. Encontrar o ponto exato na borda do município mais próximo do usuário
    ponto_costa_geo = nearest_points(ponto_usuario_geo, municipio_alvo.geometry)[1]
    
    # 3. Cálculo de distância com projeção correta (SIRGAS 2000 Brasil Polyconic)
    gs_dist = gpd.GeoSeries([ponto_usuario_geo, ponto_costa_geo], crs="EPSG:4326")
    gs_dist_proj = gs_dist.to_crs(epsg=5880)
    distancia_km = gs_dist_proj[0].distance(gs_dist_proj[1]) / 1000

    # --- RESULTADOS ---
    st.success("### 📍 Resultado")
    m1, m2, m3 = st.columns(3)
    m1.metric("Distância", f"{distancia_km:.2f} km")
    m2.metric("Município", str(municipio_alvo['NM_MUN']))
    m3.metric("UF", str(municipio_alvo['SIGLA']))

    # --- MAPA PYDECK ---
    dados_linha = [{"start": [user_lon, user_lat], "end": [ponto_costa_geo.x, ponto_costa_geo.y]}]
    
    layer_linha = pdk.Layer(
        "LineLayer", dados_linha,
        get_source_position="start", get_target_position="end",
        get_color=[255, 0, 0, 200], get_width=3,
    )

    dados_pontos = pd.DataFrame([
        {"lon": user_lon, "lat": user_lat, "local": "Ponto de Origem", "cor": [0, 0, 255]},
        {"lon": ponto_costa_geo.x, "lat": ponto_costa_geo.y, "local": f"Ponto na Costa ({municipio_alvo['NM_MUN']})", "cor": [0, 200, 0]}
    ])

    layer_pontos = pdk.Layer(
        "ScatterplotLayer", dados_pontos,
        get_position="[lon, lat]", get_fill_color="cor",
        get_radius=10, radius_units="pixels", pickable=True,
    )

    view_state = pdk.ViewState(
        longitude=(user_lon + ponto_costa_geo.x) / 2,
        latitude=(user_lat + ponto_costa_geo.y) / 2,
        zoom=7, pitch=0
    )

    st.pydeck_chart(pdk.Deck(
        initial_view_state=view_state,
        layers=[layer_linha, layer_pontos],
        tooltip={"html": "<b>{local}</b>"}
    ))

# --- RODAPÉ ---
st.sidebar.markdown("---")
st.sidebar.info(f"""
**Desenvolvido por:** Tiago Luz Farani  
*Analista Ambiental - IBAMA - Nupaem/SP* Base de dados: IBGE 2024
""")
