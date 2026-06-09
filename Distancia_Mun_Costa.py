import streamlit as st
import geopandas as gpd
import pandas as pd
from shapely.geometry import Point
from shapely.ops import nearest_points
import pydeck as pdk
import os

# --- CONFIGURAÇÃO DA PÁGINA ---
st.set_page_config(page_title="APRUMAR - IBAMA", layout="wide")

# --- CUSTOMIZAÇÃO DE CORES (Verde Escuro, Cinza Claro e Branco) ---
st.markdown("""
    <style>
        /* Cor de fundo da página principal (Branco) */
        .stApp {
            background-color: #FFFFFF;
            color: #1E293B;
        }
        /* Cor de fundo da Barra Lateral (Cinza Claro) */
        [data-testid="stSidebar"] {
            background-color: #F8F9FA;
            border-right: 1px solid #E5E7EB;
        }
        /* Títulos e Subtítulos em Verde Escuro */
        h1, h2, h3, .stSubheader {
            color: #064E3B !important;
        }
        /* Customização dos botões para Verde Escuro */
        div.stButton > button:first-child {
            background-color: #064E3B;
            color: white;
            border-radius: 6px;
            border: none;
        }
        div.stButton > button:first-child:hover {
            background-color: #0F5132;
            color: white;
        }
    </style>
""", unsafe_allow_html=True)

# --- FUNÇÃO AUXILIAR DE CONVERSÃO ---
def gms_para_decimal(graus, minutos, segundos, direcao):
    decimal = float(graus) + float(minutos)/60 + float(segundos)/3600
    if direcao in ['S', 'W', 'O']:
        decimal = -decimal
    return decimal

# --- CARREGAMENTO DE DADOS (CACHE) ---
@st.cache_data
def carregar_dados():
    if not os.path.exists("costa_brasil_otimizada.parquet"):
        return None
    gdf = gpd.read_parquet("costa_brasil_otimizada.parquet")
    if gdf.crs is None:
        gdf.set_crs(epsg=4326, inplace=True)
    return gdf

@st.cache_data
def carregar_bacias():
    if not os.path.exists("bacias_sedimentares_otimizadas.parquet"):
        return None
    gdf = gpd.read_parquet("bacias_sedimentares_otimizadas.parquet")
    if gdf.crs is None:
        gdf.set_crs(epsg=4326, inplace=True)
    return gdf

# --- CHAMADA DOS DATASETS ---
gdf_costa = carregar_dados()
gdf_bacias = carregar_bacias()

if gdf_costa is None or gdf_bacias is None:
    st.error("Erro: Arquivos '.parquet' de base não foram encontrados na raiz do repositório.")
    st.stop()

# --- INTERFACE PRINCIPAL ---
st.title("⚓ APRUMAR")
st.subheader("Análise de Proximidade Marítima e Resposta Ambiental")
st.markdown("""
Ferramenta espacial para cálculo da menor distância entre um ponto de incidente e a linha de costa brasileira (IBGE 2024), 
identificando simultaneamente a bacia sedimentar correspondente (ANP).
""")

# --- BARRA LATERAL (CONFIGURAÇÕES) ---
st.sidebar.header("Configurações de Entrada")
tipo_input = st.sidebar.radio("Formato das Coordenadas:", ("Decimal", "GMS (Graus, Min, Seg)"))

if tipo_input == "Decimal":
    user_lat = st.sidebar.number_input("Latitude (ex: -23.123)", format="%.6f", value=-23.5000)
    user_lon = st.sidebar.number_input("Longitude (ex: -42.123)", format="%.6f", value=-43.0000)
else:
    st.sidebar.subheader("Latitude")
    col_lat1, col_lat2, col_lat3 = st.sidebar.columns(3)
    lat_g = col_lat1.number_input("G", value=23, step=1, key="lat_g_input")
    lat_m = col_lat2.number_input("M", value=0, step=1, key="lat_m_input")
    lat_s = col_lat3.number_input("S", value=0.0, format="%.2f", key="lat_s_input")
    lat_dir = st.sidebar.selectbox("Direção Lat", ["S", "N"], index=0, key="lat_dir_input")
    
    st.sidebar.subheader("Longitude")
    col_lon1, col_lon2, col_lon3 = st.sidebar.columns(3)
    lon_g = col_lon1.number_input("G", value=43, step=1, key="lon_g_input")
    lon_m = col_lon2.number_input("M", value=0, step=1, key="lon_m_input")
    lon_s = col_lon3.number_input("S", value=0.0, format="%.2f", key="lon_s_input")
    lon_dir = st.sidebar.selectbox("Direção Lon", ["W", "E"], index=0, key="lon_dir_input")

    user_lat = gms_para_decimal(lat_g, lat_m, lat_s, lat_dir)
    user_lon = gms_para_decimal(lon_g, lon_m, lon_s, lon_dir)

st.sidebar.markdown("---")
calcular = st.sidebar.button("Calcular Análise Espacial", use_container_width=True)

# --- LÓGICA DE CÁLCULO ---
if calcular:
    ponto_usuario_geo = Point(user_lon, user_lat)
    
    # 1. Identificação do Município Costeiro mais próximo
    idx_vizinho = gdf_costa.sindex.nearest(ponto_usuario_geo)[1][0]
    municipio_alvo = gdf_costa.iloc[idx_vizinho]
    
    # 2. Encontrar o ponto exato na borda da costa
    ponto_costa_geo = nearest_points(ponto_usuario_geo, municipio_alvo.geometry)[1]
    
    # 3. Cálculo de distância projetada (SIRGAS 2000 Polyconic)
    gs_dist = gpd.GeoSeries([ponto_usuario_geo, ponto_costa_geo], crs="EPSG:4326")
    gs_dist_proj = gs_dist.to_crs(epsg=5880)
    distancia_km = gs_dist_proj[0].distance(gs_dist_proj[1]) / 1000

    # 4. Cruzamento Espacial com as Bacias Sedimentares (Coluna 'name')
    indices_bacia = gdf_bacias.sindex.query(ponto_usuario_geo, predicate="intersects")
    if len(indices_bacia) > 0:
        bacia_alvo = gdf_bacias.iloc[indices_bacia[0]]
        nome_bacia = str(bacia_alvo['name']).strip()
    else:
        nome_bacia = "Fora de Bacia Mapeada"

    # --- PAINEL DE RESULTADOS (4 COLUNAS) ---
    st.success("### 📍 Resultados do Cruzamento")
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Distância à Costa", f"{distancia_km:.2f} km")
    m2.metric("Município Defrontante", str(municipio_alvo['NM_MUN']))
    m3.metric("UF", str(municipio_alvo['SIGLA_UF']))
    m4.metric("Bacia Sedimentar", nome_bacia)

    # --- CONFIGURAÇÃO DO MAPA (TEMA CLARO E PONTOS CORRIGIDOS) ---
    dados_linha = [{"start": [user_lon, user_lat], "end": [ponto_costa_geo.x, ponto_costa_geo.y]}]
    
    layer_linha = pdk.Layer(
        "LineLayer", dados_linha,
        get_source_position="start", get_target_position="end",
        get_color=[185, 28, 28, 200], get_width=3,  # Linha vermelha de destaque
    )

    dados_pontos = pd.DataFrame([
        {"lon": user_lon, "lat": user_lat, "local": "Ponto do Incidente", "cor": [37, 99, 235]},        # Azul
        {"lon": ponto_costa_geo.x, "lat": ponto_costa_geo.y, "local": f"Ponto na Costa ({municipio_alvo['NM_MUN']})", "cor": [6, 78, 59]} # Verde Escuro
    ])

    layer_pontos = pdk.Layer(
        "ScatterplotLayer", dados_pontos,
        get_position="[lon, lat]", get_fill_color="cor",
        get_radius=1000, 
        radius_min_pixels=6,   # Correção dinâmica do tamanho mínimo do ponto
        radius_max_pixels=15,  # Correção dinâmica do tamanho máximo do ponto
        pickable=True,
    )

    view_state = pdk.ViewState(
        longitude=(user_lon + ponto_costa_geo.x) / 2,
        latitude=(user_lat + ponto_costa_geo.y) / 2,
        zoom=7, pitch=0
    )

    st.pydeck_chart(pdk.Deck(
        initial_view_state=view_state,
        map_style="light",  # Tema Claro ativado
        layers=[layer_linha, layer_pontos],
        tooltip={"html": "<b>{local}</b>"}
    ))

# --- RODAPÉ ---
st.sidebar.markdown("---")
st.sidebar.info(f"""
**Desenvolvido por:** Tiago Luz Farani  
*Analista Ambiental - IBAMA - Nupaem/SP* Bases: IBGE 2024 / ANP
""")
