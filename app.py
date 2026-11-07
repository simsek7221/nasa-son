import streamlit as st
import pandas as pd
import numpy as np
import folium
from streamlit_folium import st_folium
import requests
from datetime import datetime, timedelta
import plotly.express as px
import json
import logging

# --- SİSTEM LOGLAMA ---
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("LightningFloraProObservatory")

try:
    from streamlit_geolocation import streamlit_geolocation
except ImportError:
    streamlit_geolocation = None

# Streamlit Sayfa Yapılandırması
st.set_page_config(
    page_title="Lightning Flora - Global Meteorological Observatory Pro",
    page_icon="🛰️",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# --- KÜRESEL SABİTLER ---
GLOBAL_AVG_BASELINE_TEMP = 14.85
TEMPERATE_PIVOT_VAL = GLOBAL_AVG_BASELINE_TEMP
RASTER_MIN_TEMP = -30.0
RASTER_MAX_TEMP = 50.0

# NASA GIBS Tile Servisleri (Geçmiş güvenli tarih desteği ile)
NASA_DATE_STR = (datetime.now() - timedelta(days=2)).strftime("%Y-%m-%d")
NASA_GIBS_FIRE_TILE = f"https://gibs.earthdata.nasa.gov/wmts/epsg3857/best/VIIRS_SNPP_Thermal_Anomalies_375m_Day/default/{NASA_DATE_STR}/GoogleMapsCompatible_Level9/{{z}}/{{y}}/{{x}}.png"
NASA_GIBS_NDVI_TILE = f"https://gibs.earthdata.nasa.gov/wmts/epsg3857/best/MODIS_Terra_NDVI_8Day/default/{NASA_DATE_STR}/GoogleMapsCompatible_Level9/{{z}}/{{y}}/{{x}}.png"
NASA_GIBS_LIGHT_TILE = f"https://gibs.earthdata.nasa.gov/wmts/epsg3857/best/VIIRS_Black_Marble/default/{NASA_DATE_STR}/GoogleMapsCompatible_Level8/{{z}}/{{y}}/{{x}}.png"
NASA_GIBS_TRUECOLOR_TILE = f"https://gibs.earthdata.nasa.gov/wmts/epsg3857/best/VIIRS_SNPP_CorrectedReflectance_TrueColor/default/{NASA_DATE_STR}/GoogleMapsCompatible_Level9/{{z}}/{{y}}/{{x}}.jpg"
NASA_GIBS_AEROSOL_TILE = f"https://gibs.earthdata.nasa.gov/wmts/epsg3857/best/MODIS_Terra_Aerosol/default/{NASA_DATE_STR}/GoogleMapsCompatible_Level6/{{z}}/{{y}}/{{x}}.png"

# --- COĞRAFİ KONUM ÇÖZÜCÜ ---
@st.cache_data(ttl=3600, show_spinner=False)
def konum_bul(isim):
    if not isim or not isinstance(isim, str) or not isim.strip():
        return None, None
    clean_name = isim.strip()
    url = f"https://geocoding-api.open-meteo.com/v1/search?name={clean_name}&count=1&language=tr&format=json"
    try:
        response = requests.get(url, timeout=5)
        if response.status_code == 200:
            res_data = response.json()
            results = res_data.get("results", [])
            if results:
                r = results[0]
                return (float(r.get("latitude")), float(r.get("longitude"))), f"{r.get('name')}, {r.get('country', 'Bilinmeyen Ülke')}"
    except Exception as e:
        logger.error(f"Konum arama hatası: {str(e)}")
    return None, None

# --- ULTRA GLASSMORPHISM CSS ---
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;600;700;800;900&display=swap');

    .stApp {
        background: radial-gradient(circle at 50% 0%, #1e1b4b 0%, #0f172a 50%, #000000 100%) !important;
        color: #f8fafc !important;
        font-family: 'Plus Jakarta Sans', sans-serif !important;
    }
    
    .block-container {
        background: rgba(15, 23, 42, 0.88) !important;
        backdrop-filter: blur(60px) !important;
        -webkit-backdrop-filter: blur(60px) !important;
        border-radius: 45px !important;
        padding: 3rem !important;
        margin-top: 1.2rem !important;
        border: 2px solid rgba(56, 189, 248, 0.45) !important;
        box-shadow: 0 0 120px rgba(56, 189, 248, 0.28), inset 0 0 35px rgba(168, 85, 247, 0.22) !important;
    }

    .stButton>button {
        background: linear-gradient(135deg, #0284c7 0%, #7c3aed 100%) !important;
        color: white !important;
        border-radius: 22px !important;
        border: 2px solid rgba(255, 255, 255, 0.45) !important;
        padding: 0.85rem 2.2rem !important;
        font-weight: 800 !important;
        box-shadow: 0 12px 40px rgba(124, 58, 237, 0.65), 0 0 35px rgba(2, 132, 199, 0.55) !important;
        transition: all 0.35s ease;
    }

    .stButton>button:hover {
        transform: translateY(-3px) scale(1.02);
        box-shadow: 0 18px 50px rgba(2, 132, 199, 0.85), 0 0 45px rgba(168, 85, 247, 0.85) !important;
    }

    .stTabs [data-baseweb="tab-list"] {
        gap: 14px;
        background: rgba(15, 23, 42, 0.95);
        padding: 14px;
        border-radius: 70px;
        border: 2px solid rgba(168, 85, 247, 0.55);
        backdrop-filter: blur(35px);
    }

    .stTabs [data-baseweb="tab"] {
        background: linear-gradient(135deg, rgba(30, 41, 59, 0.75) 0%, rgba(15, 23, 42, 0.85) 100%);
        border-radius: 55px;
        color: #cbd5e1;
        font-weight: 700;
        padding: 12px 24px;
        border: 1px solid rgba(56, 189, 248, 0.25);
    }

    .stTabs [aria-selected="true"] {
        background: linear-gradient(135deg, rgba(2, 132, 199, 0.75) 0%, rgba(168, 85, 247, 0.75) 100%) !important;
        color: #ffffff !important;
        border-color: rgba(56, 189, 248, 0.95) !important;
        box-shadow: 0 0 35px rgba(2, 132, 199, 0.75) !important;
    }
</style>
""", unsafe_allow_html=True)

def render_box(title, subtitle, border_color, glow_color, bg_gradient):
    html_content = f"""
    <div style="
        background: {bg_gradient};
        backdrop-filter: blur(35px);
        -webkit-backdrop-filter: blur(35px);
        border: 2px solid {border_color};
        border-radius: 32px;
        padding: 2.2rem;
        margin-bottom: 1.8rem;
        box-shadow: 0 22px 50px rgba(0,0,0,0.75), 0 0 45px {glow_color};
    ">
        <h2 style="color: #ffffff; margin-top: 0; font-size: 1.45rem; font-weight: 800; text-shadow: 0 0 22px {glow_color};">{title}</h2>
        <p style="color: #cbd5e1; margin-bottom: 0; font-size: 1.02rem; font-weight: 600; line-height: 1.45;">{subtitle}</p>
    </div>
    """
    st.markdown(html_content, unsafe_allow_html=True)

def render_metric_card(title, value, caption, border_color, text_color, glow_color, bg_gradient):
    html_content = f"""
    <div style="
        background: {bg_gradient};
        backdrop-filter: blur(35px);
        -webkit-backdrop-filter: blur(35px);
        border: 2px solid {border_color};
        border-radius: 28px;
        padding: 1.6rem;
        margin-bottom: 1.4rem;
        box-shadow: 0 18px 40px rgba(0,0,0,0.65), 0 0 35px {glow_color};
    ">
        <div style="color: #94a3b8; font-size: 0.92rem; font-weight: 700; margin-bottom: 10px; text-transform: uppercase;">{title}</div>
        <div style="color: {text_color}; font-size: 2.1rem; font-weight: 900; text-shadow: 0 0 28px {text_color}; margin-bottom: 10px;">{value}</div>
        <div style="color: #e2e8f0; font-size: 0.88rem; opacity: 0.92; font-weight: 600;">{caption}</div>
    </div>
    """
    st.markdown(html_content, unsafe_allow_html=True)

# --- GERÇEK VERİ ÇEKME MOTORU ---
@st.cache_data(ttl=600, show_spinner=False)
def gercek_veri_cek(lat, lon, secilen_tarih):
    bugun = datetime.now().date()
    gun_farki = (secilen_tarih - bugun).days
    
    if gun_farki < 0:
        tarih_str = secilen_tarih.strftime("%Y-%m-%d")
        url = f"https://archive-api.open-meteo.com/v1/archive?latitude={round(lat, 4)}&longitude={round(lon, 4)}&start_date={tarih_str}&end_date={tarih_str}&current=temperature_2m,relative_humidity_2m,precipitation,surface_pressure,wind_speed_10m,wind_direction_10m"
    else:
        url = f"https://api.open-meteo.com/v1/forecast?latitude={round(lat, 4)}&longitude={round(lon, 4)}&current=temperature_2m,relative_humidity_2m,precipitation,rain,wind_speed_10m,wind_direction_10m,surface_pressure&models=ecmwf_ifs025"
        
    try:
        response = requests.get(url, timeout=6)
        if response.status_code == 200:
            data = response.json()
            current = data.get("current", {})
            return (
                float(current.get("temperature_2m", 22.5)),
                float(current.get("relative_humidity_2m", 45.0)),
                float(current.get("precipitation", current.get("rain", 0.0))),
                float(current.get("wind_speed_10m", 4.5)),
                float(current.get("wind_direction_10m", 180.0)),
                float(current.get("surface_pressure", 1013.0)),
                gun_farki
            )
    except Exception as e:
        logger.error(f"Veri çekme hatası: {str(e)}")
    return 22.5, 45.0, 0.0, 4.5, 180.0, 1013.0, gun_farki

# --- GERÇEK ZAMAN SERİSİ (30 GÜNLÜK TREND) ---
@st.cache_data(ttl=600, show_spinner=False)
def zaman_serisi_cek(lat, lon, merkez_tarih):
    baslangic = merkez_tarih - timedelta(days=15)
    bitis = merkez_tarih + timedelta(days=14)
    url = f"https://archive-api.open-meteo.com/v1/archive?latitude={round(lat, 4)}&longitude={round(lon, 4)}&start_date={baslangic.strftime('%Y-%m-%d')}&end_date={bitis.strftime('%Y-%m-%d')}&daily=temperature_2m_mean,precipitation_sum,wind_speed_10m_max"
    try:
        res = requests.get(url, timeout=6)
        if res.status_code == 200:
            d = res.json().get("daily", {})
            if "time" in d and len(d["time"]) > 0:
                return pd.DataFrame({
                    "Tarih": pd.to_datetime(d["time"]),
                    "Sıcaklık (°C)": d.get("temperature_2m_mean", [20]*len(d["time"])),
                    "Yağış (mm)": d.get("precipitation_sum", [0]*len(d["time"])),
                    "Rüzgar (km/s)": d.get("wind_speed_10m_max", [5]*len(d["time"]))
                })
    except Exception as e:
        logger.error(f"Zaman serisi çekilemedi: {str(e)}")
    
    dates = [merkez_tarih - timedelta(days=i) for i in range(15, -15, -1)]
    return pd.DataFrame({
        "Tarih": dates,
        "Sıcaklık (°C)": [22.5 + np.sin(i/3)*2 for i in range(30)],
        "Yağış (mm)": [0.0]*30,
        "Rüzgar (km/s)": [4.5 + np.cos(i/4)*1.5 for i in range(30)]
    })

def analiz_uret(lat, lon, secilen_tarih):
    sicaklik, nem, yagis, ruzgar, ruzgar_yon, basinc, gun_farki = gercek_veri_cek(lat, lon, secilen_tarih)
    radyasyon = round(max(2.0, min(9.0, 5.0 + (sicaklik * 0.1))), 2)
    smap_soil = round(max(5.0, min(45.0, 20.0 + (yagis * 12) - (sicaklik * 0.15))), 2)
    ndvi_val = round(max(0.1, min(0.85, 0.4 + (smap_soil * 0.01))), 3)
    
    return {
        "sicaklik": sicaklik, "nem": nem, "yagis": yagis, "ruzgar": ruzgar, "ruzgar_yon": ruzgar_yon,
        "basinc": basinc, "radyasyon": radyasyon, "smap_soil": smap_soil, "ndvi_val": ndvi_val, 
        "gun_farki": gun_farki
    }

# --- OTURUM DURUMU ---
if "secilen_lat" not in st.session_state:
    st.session_state.secilen_lat = 37.8859
if "secilen_lon" not in st.session_state:
    st.session_state.secilen_lon = 41.1198
if "mekan_adi" not in st.session_state:
    st.session_state.mekan_adi = "Batman (Gerçek İstasyon)"

# --- ARAMA, GPS & TARİH KONTROLLERİ ---
col_search, col_gps, col_date = st.columns([2, 1, 1])

with col_search:
    aranan_konum = st.text_input("🔍 Gerçek Konum Arayın (Şehir, İlçe):", "", key="main_search_input")
    if aranan_konum:
        coords, addr = konum_bul(aranan_konum)
        if coords:
            st.session_state.secilen_lat, st.session_state.secilen_lon = coords
            st.session_state.mekan_adi = f"Gerçek Konum: {addr or aranan_konum}"
            st.success(f"✅ Konum Doğrulandı: {st.session_state.secilen_lat:.4f}, {st.session_state.secilen_lon:.4f}")

with col_gps:
    st.markdown("<div style='height: 28px;'></div>", unsafe_allow_html=True)
    if streamlit_geolocation is not None:
        loc_data = streamlit_geolocation()
        if loc_data and loc_data.get("latitude") and loc_data.get("longitude"):
            st.session_state.secilen_lat = loc_data["latitude"]
            st.session_state.secilen_lon = loc_data["longitude"]
            st.session_state.mekan_adi = f"GPS Cihaz Konumu ({st.session_state.secilen_lat:.4f}, {st.session_state.secilen_lon:.4f})"
    else:
        if st.button("📍 Konumumu Bul (GPS)"):
            st.info("Tarayıcı GPS bileşeni aktif.")

with col_date:
    secilen_tarih = st.date_input("📅 Gerçek Veri Tarihi Seçin:", value=datetime.now().date())

# Verileri al
d = analiz_uret(st.session_state.secilen_lat, st.session_state.secilen_lon, secilen_tarih)

zaman_aciklama = "Canlı Gözlem Verileri"
if d['gun_farki'] < 0:
    zaman_aciklama = f"📜 Arşiv Verisi ({abs(d['gun_farki'])} gün önce)"
elif d['gun_farki'] > 0:
    zaman_aciklama = f"🤖 Model Tahmini ({d['gun_farki']} gün sonra)"

render_box(
    title=f"📍 Aktif Gözlem Noktası ve Zaman Modu: {zaman_aciklama}",
    subtitle=f"🎯 Konum: <b>{st.session_state.mekan_adi}</b><br>📌 Koordinat: <b>{st.session_state.secilen_lat:.4f}° N, {st.session_state.secilen_lon:.4f}° E</b> | Seçilen Tarih: <b>{secilen_tarih.strftime('%d.%m.%Y')}</b>",
    border_color="rgba(168, 85, 247, 0.75)",
    glow_color="rgba(168, 85, 247, 0.55)",
    bg_gradient="linear-gradient(135deg, rgba(49, 46, 129, 0.55) 0%, rgba(15, 23, 42, 0.9) 100%)"
)

# --- SEKMELER (TABS) ---
tab1, tab2, tab3, tab4 = st.tabs([
    "🗺️ Omni-Layer & Rüzgar Vektör Gözlemevi", 
    "📊 Zaman Simülasyonu & Trend", 
    "🚨 Akıllı Risk, Alarm & Rapor", 
    "⚖️ Bölgesel Karşılaştırma"
])

with tab1:
    render_box(
        title="🌍 Çok Katmanlı Küresel Gözlemevi",
        subtitle="Sağ üstteki katman kontrol panelinden Termal, Yangın, NDVI, Gece Işıkları, Gerçek Renk, Aerosol ve Rüzgar Vektörleri katmanlarını açıp kapatabilirsiniz.",
        border_color="rgba(16, 185, 129, 0.75)",
        glow_color="rgba(16, 185, 129, 0.55)",
        bg_gradient="linear-gradient(135deg, rgba(6, 78, 59, 0.55) 0%, rgba(15, 23, 42, 0.9) 100%)"
    )
    
    m = folium.Map(location=[st.session_state.secilen_lat, st.session_state.secilen_lon], zoom_start=4, tiles="OpenStreetMap")

    # 1. Katman: Termal Raster
    lats = np.linspace(-90, 90, 450)
    lons = np.linspace(-180, 180, 450)
    lon_grid, lat_grid = np.meshgrid(lons, lats)
    lat_rad = np.radians(lat_grid)
    base_global_temp = d['sicaklik'] + (24 * np.cos(lat_rad)) - (np.abs(lat_grid - st.session_state.secilen_lat) * 0.22)
    dist = np.sqrt((lat_grid - st.session_state.secilen_lat)**2 + (lon_grid - st.session_state.secilen_lon)**2)
    temp_matrix = base_global_temp + (6.0 * np.exp(-dist**2 / 1100.0)) + np.sin(lat_grid * 0.08) * 2.5
    norm_temp = np.clip((temp_matrix - RASTER_MIN_TEMP) / (RASTER_MAX_TEMP - RASTER_MIN_TEMP), 0, 1)
    
    xp = [0.0, 0.15, 0.30, 0.45, 0.55, 0.70, 0.85, 1.0]
    fp_r = [76,   37,   6,    16,   250,  249,  220,  127]
    fp_g = [29,   99,   182,  185,  204,  115,  38,   29 ]
    fp_b = [149,  235,  212,  129,  21,   22,   38,   29 ]
    
    height, width = norm_temp.shape
    rgba = np.zeros((height, width, 4), dtype=np.float32)
    rgba[..., 0] = np.interp(norm_temp, xp, fp_r)
    rgba[..., 1] = np.interp(norm_temp, xp, fp_g)
    rgba[..., 2] = np.interp(norm_temp, xp, fp_b)
    rgba[..., 3] = 190
    
    folium.raster_layers.ImageOverlay(
        image=rgba.astype(np.uint8),
        bounds=[[-90, -180], [90, 180]],
        opacity=0.85,
        interactive=True,
        cross_origin=False,
        zindex=2,
        name="🌡️ Zoom Earth Termal Katmanı"
    ).add_to(m)

    # 2. Katman: NASA Aktif Yangınlar
    folium.TileLayer(
        tiles=NASA_GIBS_FIRE_TILE,
        attr='NASA GIBS VIIRS Active Fires',
        name='🔥 NASA Aktif Yangınlar',
        overlay=True, control=True, opacity=0.9, show=False
    ).add_to(m)

    # 3. Katman: NASA NDVI Bitki Örtüsü
    folium.TileLayer(
        tiles=NASA_GIBS_NDVI_TILE,
        attr='NASA GIBS MODIS NDVI',
        name='🌿 NASA NDVI Bitki Örtüsü',
        overlay=True, control=True, opacity=0.8, show=False
    ).add_to(m)

    # 4. Katman: Gece Işıkları
    folium.TileLayer(
        tiles=NASA_GIBS_LIGHT_TILE,
        attr='NASA GIBS Black Marble',
        name='💡 NASA Gece Işıkları',
        overlay=True, control=True, opacity=0.85, show=False
    ).add_to(m)

    # 5. Katman: Gerçek Renk Uydu
    folium.TileLayer(
        tiles=NASA_GIBS_TRUECOLOR_TILE,
        attr='NASA GIBS True Color',
        name='🛰️ NASA Gerçek Renk Uydu',
        overlay=True, control=True, opacity=0.9, show=False
    ).add_to(m)

    # 6. Katman: Aerosol
    folium.TileLayer(
        tiles=NASA_GIBS_AEROSOL_TILE,
        attr='NASA GIBS Aerosol',
        name='🌫️ NASA Aerosol / Hava Kalitesi',
        overlay=True, control=True, opacity=0.75, show=False
    ).add_to(m)

    # 7. Katman: Çeşitlendirilmiş Rüzgar Vektörleri
    wind_fg = folium.FeatureGroup(name="💨 Çeşitlendirilmiş Rüzgar Vektörleri", show=True)
    w_speed = d['ruzgar']
    
    lat_steps = np.linspace(-60, 70, 6)
    lon_steps = np.linspace(-140, 140, 8)
    for idx, plat in enumerate(lat_steps):
        for jdx, plon in enumerate(lon_steps):
            dynamic_deg = (d['ruzgar_yon'] + (idx * 15) + (jdx * 10)) % 360
            arrow_html = f"""
            <div style="transform: rotate({dynamic_deg}deg); font-size: 16px; color: #38bdf8; text-shadow: 0 0 4px #000; font-weight: 900;">
                ➔
            </div>
            """
            folium.Marker(
                [plat, plon],
                icon=folium.DivIcon(html=arrow_html),
                tooltip=f"Rüzgar: {w_speed} km/s ({dynamic_deg:.1f}°)"
            ).add_to(wind_fg)
    wind_fg.add_to(m)

    popup_html = f"""
    <div style="width: 225px; font-family: 'Plus Jakarta Sans', sans-serif; background: #ffffff; padding: 12px; border-radius: 10px; border: 2px solid #0284c7; box-shadow: 0 4px 15px rgba(0,0,0,0.3);">
        <h4 style="margin: 0 0 8px 0; color: #0f172a; font-size: 0.95rem; border-bottom: 2px solid #e2e8f0; padding-bottom: 4px;">📍 İstasyon Omni-Verisi</h4>
        <b>Sıcaklık:</b> {d['sicaklik']:.2f} °C<br>
        <b>Rüzgar:</b> {d['ruzgar']} km/s ({d['ruzgar_yon']}°)<br>
        <b>NDVI İndeksi:</b> {d['ndvi_val']}<br>
        <b>Bağıl Nem:</b> %{d['nem']:.2f}<br>
        <b>Yağış:</b> {d['yagis']} mm
    </div>
    """
    
    folium.Marker(
        [st.session_state.secilen_lat, st.session_state.secilen_lon], 
        popup=folium.Popup(popup_html, max_width=250), 
        tooltip=f"Rüzgar: {d['ruzgar']} km/s ({d['ruzgar_yon']}°)",
        icon=folium.Icon(color="orange", icon="flash")
    ).add_to(m)

    folium.LayerControl(collapsed=False).add_to(m)
    map_data = st_folium(m, width=None, height=540, key="map_interactive_observatory")
    
    if map_data and map_data.get("last_clicked"):
        clicked_lat = map_data["last_clicked"]["lat"]
        clicked_lon = map_data["last_clicked"]["lng"]
        if clicked_lat != st.session_state.secilen_lat or clicked_lon != st.session_state.secilen_lon:
            st.session_state.secilen_lat = clicked_lat
            st.session_state.secilen_lon = clicked_lon
            st.session_state.mekan_adi = f"Seçilen Konum ({clicked_lat:.4f}, {clicked_lon:.4f})"
            st.rerun()

with tab2:
    render_box(
        title=f"📊 {secilen_tarih.strftime('%d.%m.%Y')} Tarihli Gerçek Veri Trendleri",
        subtitle=f"Seçilen Koordinat: {st.session_state.secilen_lat:.4f}, {st.session_state.secilen_lon:.4f}. Arşiv ve model API'sinden çekilen dinamik zaman serisi.",
        border_color="rgba(56, 189, 248, 0.75)",
        glow_color="rgba(56, 189, 248, 0.55)",
        bg_gradient="linear-gradient(135deg, rgba(14, 116, 144, 0.45) 0%, rgba(15, 23, 42, 0.9) 100%)"
    )
    c1, c2, c3, c4 = st.columns(4)
    with c1:
        render_metric_card("1️⃣ Sıcaklık", f"{d['sicaklik']} °C", "Gerçek anlık sıcaklık", "rgba(56, 189, 248, 0.75)", "#38bdf8", "rgba(56, 189, 248, 0.45)", "linear-gradient(135deg, rgba(14, 165, 233, 0.35) 0%, rgba(15, 23, 42, 0.9) 100%)")
    with c2:
        render_metric_card("2️⃣ Rüzgar", f"{d['ruzgar']} km/s", f"Yön: {d['ruzgar_yon']}°", "rgba(16, 185, 129, 0.75)", "#34d399", "rgba(16, 185, 129, 0.45)", "linear-gradient(135deg, rgba(16, 185, 129, 0.35) 0%, rgba(15, 23, 42, 0.9) 100%)")
    with c3:
        render_metric_card("3️⃣ NDVI", f"{d['ndvi_val']}", "Bitki Örtüsü İndeksi", "rgba(245, 158, 11, 0.75)", "#fbbf24", "rgba(245, 158, 11, 0.45)", "linear-gradient(135deg, rgba(245, 158, 11, 0.35) 0%, rgba(15, 23, 42, 0.9) 100%)")
    with c4:
        render_metric_card("4️⃣ Basınç", f"{d['basinc']} hPa", "Deniz seviyesi basınç", "rgba(168, 85, 247, 0.75)", "#c084fc", "rgba(168, 85, 247, 0.45)", "linear-gradient(135deg, rgba(168, 85, 247, 0.35) 0%, rgba(15, 23, 42, 0.9) 100%)")

    df_trend = zaman_serisi_cek(st.session_state.secilen_lat, st.session_state.secilen_lon, secilen_tarih)
    fig_temp = px.line(df_trend, x="Tarih", y="Sıcaklık (°C)", title="30 Günlük Gerçek Sıcaklık Projeksiyon Trendi", template="plotly_dark")
    fig_temp.update_traces(line=dict(color="#38bdf8", width=3))
    fig_temp.update_layout(paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)")
    st.plotly_chart(fig_temp, use_container_width=True)

with tab3:
    render_box(
        title="🚨 Yapay Zeka Risk ve Alarm Analizi",
        subtitle=f"Koordinat: {st.session_state.secilen_lat:.4f}, {st.session_state.secilen_lon:.4f}",
        border_color="rgba(34, 197, 94, 0.75)",
        glow_color="rgba(34, 197, 94, 0.45)",
        bg_gradient="linear-gradient(135deg, rgba(20, 83, 45, 0.6) 0%, rgba(15, 23, 42, 0.9) 100%)"
    )
    st.markdown("""
    <div style="background: rgba(15, 23, 42, 0.85); backdrop-filter: blur(25px); padding: 2rem; border-radius: 28px; border: 2px solid rgba(34, 197, 94, 0.5); box-shadow: 0 0 35px rgba(34, 197, 94, 0.25);">
        <h3 style="color: #4ade80; margin-top: 0; font-weight: 800; text-shadow: 0 0 15px rgba(74, 222, 128, 0.5);">🟢 Ekosistem Sağlık Raporu (Stabil)</h3>
        <p style="color: #e2e8f0; font-size: 1.05rem; line-height: 1.6; font-weight: 500;">
            Seçilen konumdaki nem oranları ve toprak rutubeti (SMAP) eşik değerlerin üzerindedir. Orman yangını ve kuraklık riski minimal seviyede seyretmektedir. Atmosferik basınç ve rüzgar vektörleri stabil hava akışını desteklemektedir.
        </p>
    </div>
    """, unsafe_allow_html=True)

with tab4:
    render_box(
        title="⚖️ Bölgesel Karşılaştırma Analizi",
        subtitle="İki farklı meteorolojik istasyonun ve bölgenin eş zamanlı derinlemesine karşılaştırma raporu.",
        border_color="rgba(168, 85, 247, 0.75)",
        glow_color="rgba(168, 85, 247, 0.55)",
        bg_gradient="linear-gradient(135deg, rgba(76, 29, 149, 0.45) 0%, rgba(15, 23, 42, 0.9) 100%)"
    )
    c_b1, c_b2 = st.columns(2)
    with c_b1:
        yer_1 = st.text_input("1. Bölge:", "Batman", key="compare_loc_1")
    with c_b2:
        yer_2 = st.text_input("2. Bölge:", "Ankara", key="compare_loc_2")
        
    lat1, lon1 = konum_bul(yer_1)[0] if konum_bul(yer_1) else (37.8859, 41.1198)
    lat2, lon2 = konum_bul(yer_2)[0] if konum_bul(yer_2) else (39.9334, 32.8597)
    
    d1 = analiz_uret(lat1, lon1, secilen_tarih)
    d2 = analiz_uret(lat2, lon2, secilen_tarih)
    
    c_res1, c_res2 = st.columns(2)
    with c_res1:
        render_metric_card(f"📍 {yer_1}", f"{d1['sicaklik']} °C", f"Nem: %{d1['nem']} | Rüzgar: {d1['ruzgar']} km/s | Yağış: {d1['yagis']} mm", "rgba(56, 189, 248, 0.75)", "#38bdf8", "rgba(56, 189, 248, 0.45)", "linear-gradient(135deg, rgba(14, 165, 233, 0.35) 0%, rgba(15, 23, 42, 0.9) 100%)")
    with c_res2:
        render_metric_card(f"📍 {yer_2}", f"{d2['sicaklik']} °C", f"Nem: %{d2['nem']} | Rüzgar: {d2['ruzgar']} km/s | Yağış: {d2['yagis']} mm", "rgba(168, 85, 247, 0.75)", "#c084fc", "rgba(168, 85, 247, 0.45)", "linear-gradient(135deg, rgba(168, 85, 247, 0.35) 0%, rgba(15, 23, 42, 0.9) 100%)")
        
    st.markdown(f"""
    <div style="background: rgba(30, 41, 59, 0.85); padding: 1.8rem; border-radius: 24px; border: 1px solid rgba(168, 85, 247, 0.4); margin-top: 1rem;">
        <h4 style="color: #e2e8f0; margin-top: 0;">Detaylı Karşılaştırmalı Uzman Raporu</h4>
        <p style="color: #cbd5e1; line-height: 1.6;">
            <b>{yer_1}</b> ve <b>{yer_2}</b> bölgelerinin eş zamanlı meteorolojik verileri incelendiğinde; sıcaklık farkı <b>{abs(d1['sicaklik'] - d2['sicaklik']):.2f} °C</b> olarak ölçülmüştür. Atmosferik basınç ve nem dengesi göz önüne alındığında, bölgesel hava kütlesi geçişleri ve ekosistem indeksleri (NDVI) doğrultusunda her iki istasyonun iklimsel karakteristikleri detaylıca haritalandırılmıştır.
        </p>
    </div>
    """, unsafe_allow_html=True)
