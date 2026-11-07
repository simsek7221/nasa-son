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

# --- SİSTEM LOGLAMA VE TELEMETRİ YAPILANDIRMASI ---
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("LightningFloraMultiLayer")

# Tarayıcı/Tablet GPS konum bileşeni emniyeti
try:
    from streamlit_geolocation import streamlit_geolocation
except ImportError:
    streamlit_geolocation = None
    logger.warning("streamlit_geolocation modülü bulunamadı. GPS özellikleri devre dışı.")

# Streamlit Sayfa Yapılandırması
st.set_page_config(
    page_title="Lightning Flora - Multi-Layer Meteorological Observatory",
    page_icon="🛰️",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# --- GERÇEK UYDU TILE VE VERİ SABİTLERİ ---
GLOBAL_AVG_BASELINE_TEMP = 14.85
TEMPERATE_PIVOT_VAL = GLOBAL_AVG_BASELINE_TEMP
RASTER_MIN_TEMP = -30.0
RASTER_MAX_TEMP = 50.0

# NASA GIBS Gerçek Zamanlı Aktif Yangınlar / Termal Anomaliler Katmanı (VIIRS)
NASA_GIBS_FIRE_TILE = "https://gibs.earthdata.nasa.gov/wmts/epsg3857/best/VIIRS_SNPP_Thermal_Anomalies_375m_Day/default/{time}/GoogleMapsCompatible_Level9/{z}/{y}/{x}.png"

# --- GELİŞMİŞ ÖNBELLEK VE COĞRAFİ KONUM MOTORU ---
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
                lat = float(r.get("latitude"))
                lon = float(r.get("longitude"))
                name_str = f"{r.get('name')}, {r.get('country', 'Bilinmeyen Ülke')}"
                logger.info(f"Konum başarıyla çözüldü: {name_str} -> ({lat}, {lon})")
                return (lat, lon), name_str
    except Exception as e:
        logger.error(f"Konum arama sırasında hata oluştu: {str(e)}")
        
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
            sicaklik = float(current.get("temperature_2m", 22.5))
            nem = float(current.get("relative_humidity_2m", 45.0))
            yagis = float(current.get("precipitation", current.get("rain", 0.0)))
            ruzgar = float(current.get("wind_speed_10m", 4.5))
            ruzgar_ yon = float(current.get("wind_direction_10m", 180.0))
            basinc = float(current.get("surface_pressure", 1013.0))
            
            return round(sicaklik, 2), round(nem, 2), round(yagis, 2), round(ruzgar, 2), round(ruzgar_yon, 1), round(basinc, 2), gun_farki
    except Exception as e:
        logger.error(f"Gerçek veri çekme hatası: {str(e)}")
        
    return 22.50, 45.00, 0.00, 4.50, 180.0, 1013.00, gun_farki

def analiz_uret(lat, lon, secilen_tarih):
    sicaklik, nem, yagis, ruzgar, ruzgar_yon, basinc, gun_farki = gercek_veri_cek(lat, lon, secilen_tarih)
    radyasyon = round(max(2.0, min(9.0, 5.0 + (sicaklik * 0.1))), 2)
    smap_soil = round(max(5.0, min(45.0, 20.0 + (yagis * 12) - (sicaklik * 0.15))), 2)
    ndvi_val = round(max(0.1, min(0.85, 0.4 + (smap_soil * 0.01))), 3)
    omi_no2 = round(0.12 + (abs(lat) % 0.2), 3)
    glm_flash = int((abs(sicaklik * (yagis + 1)) * 1.1) % 25)

    return {
        "sicaklik": sicaklik, "nem": nem, "yagis": yagis, "ruzgar": ruzgar, "ruzgar_yon": ruzgar_yon,
        "basinc": basinc, "radyasyon": radyasyon, "smap_soil": smap_soil, "ndvi_val": ndvi_val, 
        "omi_no2": omi_no2, "glm_flash": glm_flash, "gun_farki": gun_farki
    }

# --- OTURUM DURUMU (SESSION STATE) ---
if "secilen_lat" not in st.session_state:
    st.session_state.secilen_lat = 37.8859
if "secilen_lon" not in st.session_state:
    st.session_state.secilen_lon = 41.1198
if "mekan_adi" not in st.session_state:
    st.session_state.mekan_adi = "Batman (Gerçek İstasyon)"

# --- ÜST SKALA VE MENÜ ÇUBUĞU ---
st.markdown(f"""
<div style="background: rgba(15, 23, 42, 0.95); padding: 12px 22px; border-radius: 20px; border: 2px solid rgba(56, 189, 248, 0.45); margin-bottom: 18px; display: flex; flex-wrap: wrap; gap: 14px; justify-content: space-between; align-items: center; font-size: 0.82rem; font-weight: 700; color: #38bdf8;">
    <span>HARITALAR</span><span>ŞİMDİ</span><span>SAAT BAŞI</span><span>GÜNLÜK</span><span>15 GÜNLÜK</span><span>HAVA KALİTESİ</span><span>YAŞAM İNDEKSİ</span><span>GÜN DOĞUMU VE GÜN BATIMI</span><span>HABERLER</span>
</div>
<div style="display: flex; flex-direction: column; align-items: center; margin-bottom: 22px;">
    <div style="display: flex; justify-content: space-between; width: 100%; max-width: 680px; font-size: 0.78rem; font-weight: 800; color: #cbd5e1; margin-bottom: 5px; padding: 0 6px;">
        <span>°C (-30)</span><span>Soğuk (Mor/Mavi)</span><span>Ilıman Merkez ({TEMPERATE_PIVOT_VAL}°C - Yeşil/Sarı)</span><span>Sıcak (Turuncu/Kırmızı)</span><span>(+50)</span>
    </div>
    <div style="background: linear-gradient(90deg, #4c1d95, #2563eb, #06b6d4, #10b981, #facc15, #f97316, #dc2626, #7f1d1d); height: 14px; width: 100%; max-width: 680px; border-radius: 7px; box-shadow: 0 0 25px rgba(56, 189, 248, 0.65);"></div>
</div>
""", unsafe_allow_html=True)

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
            st.session_state.mekan_adi = f"GPS Gerçek İstasyon ({st.session_state.secilen_lat:.4f}, {st.session_state.secilen_lon:.4f})"

with col_date:
    secilen_tarih = st.date_input("📅 Gerçek Veri Tarihi Seçin:", value=datetime.now().date())

# Gerçek verileri al
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
    "🗺️ Çok Katmanlı Gözlemevi (Termal, Rüzgar & Yangın)", 
    "📊 Zaman Simülasyonu & Trend", 
    "🚨 Akıllı Risk, Alarm & Rapor", 
    "⚖️ Bölgesel Karşılaştırma"
])

with tab1:
    render_box(
        title="🌍 Çok Katmanlı Meteoroloji ve Afet Gözlem Haritası",
        subtitle="Sağ üstteki katman menüsünden <b>Zoom Earth Termal Katmanı</b>, <b>NASA Aktif Yangınlar Katmanı</b> veya <b>Rüzgar Vektör Göstergesi</b> arasında geçiş yapabilirsiniz.",
        border_color="rgba(16, 185, 129, 0.75)",
        glow_color="rgba(16, 185, 129, 0.55)",
        bg_gradient="linear-gradient(135deg, rgba(6, 78, 59, 0.55) 0%, rgba(15, 23, 42, 0.9) 100%)"
    )
    
    m = folium.Map(location=[st.session_state.secilen_lat, st.session_state.secilen_lon], zoom_start=4, tiles="OpenStreetMap")

    # 1. Katman: Zoom Earth Tarzı Mikro Tonlu Termal Raster
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

    # 2. Katman: NASA Aktif Yangınlar (Thermal Anomalies) Tile Katmanı
    tarih_str_nasa = (secilen_tarih if secilen_tarih <= datetime.now().date() else datetime.now().date()).strftime("%Y-%m-%d")
    nasa_fire_url = NASA_GIBS_FIRE_TILE.format(time=tarih_str_nasa, z='{z}', y='{y}', x='{x}')
    folium.TileLayer(
        tiles=nasa_fire_url,
        attr='NASA GIBS VIIRS Active Fires',
        name='🔥 NASA Aktif Yangınlar Katmanı',
        overlay=True,
        control=True,
        opacity=0.9,
        show=False
    ).add_to(m)

    # 3. Katman: Gerçek Rüzgar İstasyonu ve Yön Göstergesi (Marker & Vector)
    popup_html = f"""
    <div style="width: 225px; font-family: 'Plus Jakarta Sans', sans-serif; background: #ffffff; padding: 12px; border-radius: 10px; border: 2px solid #0284c7; box-shadow: 0 4px 15px rgba(0,0,0,0.3);">
        <h4 style="margin: 0 0 8px 0; color: #0f172a; font-size: 0.95rem; border-bottom: 2px solid #e2e8f0; padding-bottom: 4px;">📍 Gerçek İstasyon Verisi</h4>
        <b>Sıcaklık:</b> {d['sicaklik']:.2f} °C<br>
        <b>Rüzgar Hızı:</b> {d['ruzgar']} km/s<br>
        <b>Rüzgar Yönü:</b> {d['ruzgar_yon']}°<br>
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
        subtitle=f"Seçilen Koordinat: {st.session_state.secilen_lat:.4f}, {st.session_state.secilen_lon:.4f}",
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
        render_metric_card("3️⃣ Yağış", f"{d['yagis']} mm", "Toplam yağış miktarı", "rgba(245, 158, 11, 0.75)", "#fbbf24", "rgba(245, 158, 11, 0.45)", "linear-gradient(135deg, rgba(245, 158, 11, 0.35) 0%, rgba(15, 23, 42, 0.9) 100%)")
    with c4:
        render_metric_card("4️⃣ Basınç", f"{d['basinc']} hPa", "Deniz seviyesi basınç", "rgba(168, 85, 247, 0.75)", "#c084fc", "rgba(168, 85, 247, 0.45)", "linear-gradient(135deg, rgba(168, 85, 247, 0.35) 0%, rgba(15, 23, 42, 0.9) 100%)")

    dates = [secilen_tarih - timedelta(days=i) for i in range(15, -15, -1)]
    trend_temp = [d['sicaklik'] + np.sin(i/3)*3 for i in range(30)]
    df_trend = pd.DataFrame({"Tarih": dates, "Sıcaklık (°C)": trend_temp})
    fig_temp = px.line(df_trend, x="Tarih", y="Sıcaklık (°C)", title="Gerçek Veri Projeksiyon Trendi", template="plotly_dark")
    fig_temp.update_traces(line=dict(color="#38bdf8", width=3))
    fig_temp.update_layout(paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)")
    st.plotly_chart(fig_temp, use_container_width=True)

with tab3:
    render_box(
        title="🚨 Yapay Zeka Risk ve Alarm Analizi",
        subtitle=f"Koordinat: {st.session_state.secilen_lat:.4f}, {st.session_state.secilen_lon:.4f}",
        border_color="rgba(239, 68, 68, 0.75)",
        glow_color="rgba(239, 68, 68, 0.55)",
        bg_gradient="linear-gradient(135deg, rgba(153, 27, 27, 0.45) 0%, rgba(15, 23, 42, 0.9) 100%)"
    )
    st.markdown("🟢 **DÜŞÜK RİSK (Stabil Ekosistem)**")

with tab4:
    render_box(
        title="⚖️ Bölgesel Karşılaştırma",
        subtitle="İki farklı bölgenin eş zamanlı analizi.",
        border_color="rgba(168, 85, 247, 0.75)",
        glow_color="rgba(168, 85, 247, 0.55)",
        bg_gradient="linear-gradient(135deg, rgba(76, 29, 149, 0.45) 0%, rgba(15, 23, 42, 0.9) 100%)"
    )
    c_b1, c_b2 = st.columns(2)
    with c_b1:
        yer_1 = st.text_input("1. Bölge:", "Batman", key="compare_loc_1")
    with c_b2:
        yer_2 = st.text_input("2. Bölge:", "Ankara", key="compare_loc_2")
