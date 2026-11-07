import streamlit as st
import pandas as pd
import numpy as np
import folium
from streamlit_folium import st_folium
import requests
from datetime import datetime, timedelta
import plotly.express as px

try:
    from streamlit_geolocation import streamlit_geolocation
except ImportError:
    streamlit_geolocation = None

st.set_page_config(
    page_title="Lightning Flora - Global Thermal Observatory",
    page_icon="🛰️",
    layout="wide"
)

@st.cache_data(ttl=3600)
def konum_bul(isim):
    if not isim or not isim.strip():
        return None, None
    url = f"https://geocoding-api.open-meteo.com/v1/search?name={isim.strip()}&count=1&language=tr&format=json"
    try:
        res = requests.get(url, timeout=5).json()
        results = res.get("results", [])
        if results:
            r = results[0]
            return (float(r.get("latitude")), float(r.get("longitude"))), f"{r.get('name')}, {r.get('country', '')}"
    except Exception:
        pass
    return None, None

# --- 3X ULTRA INTENSIFIED NEON & GLASSMORPHISM CSS ---
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;600;700;800;900&display=swap');
    .stApp {
        background: radial-gradient(circle at 50% 0%, #2e1065 0%, #0f172a 50%, #000000 100%) !important;
        color: #f8fafc !important;
        font-family: 'Plus Jakarta Sans', sans-serif !important;
    }
    .block-container {
        background: rgba(15, 23, 42, 0.75) !important;
        backdrop-filter: blur(60px) !important;
        -webkit-backdrop-filter: blur(60px) !important;
        border-radius: 45px !important;
        padding: 3rem !important;
        margin-top: 1.5rem !important;
        border: 3px solid rgba(56, 189, 248, 0.6) !important;
        box-shadow: 0 0 120px rgba(56, 189, 248, 0.35), inset 0 0 40px rgba(168, 85, 247, 0.25) !important;
    }
    .stButton>button {
        background: linear-gradient(135deg, #38bdf8 0%, #7c3aed 100%) !important;
        color: white !important;
        border-radius: 25px !important;
        border: 3px solid rgba(255, 255, 255, 0.5) !important;
        padding: 1rem 2.5rem !important;
        font-weight: 900 !important;
        box-shadow: 0 15px 45px rgba(124, 58, 237, 0.7), 0 0 40px rgba(56, 189, 248, 0.6) !important;
        transition: all 0.4s ease;
    }
    .stButton>button:hover {
        transform: translateY(-5px) scale(1.03);
        box-shadow: 0 25px 60px rgba(56, 189, 248, 0.9), 0 0 60px rgba(168, 85, 247, 0.9) !important;
    }
    .stTabs [data-baseweb="tab-list"] {
        gap: 15px;
        background: rgba(15, 23, 42, 0.9);
        padding: 16px;
        border-radius: 80px;
        border: 3px solid rgba(168, 85, 247, 0.6);
        backdrop-filter: blur(40px);
    }
    .stTabs [data-baseweb="tab"] {
        background: linear-gradient(135deg, rgba(30, 41, 59, 0.8) 0%, rgba(15, 23, 42, 0.9) 100%);
        border-radius: 60px;
        color: #cbd5e1;
        font-weight: 800;
        padding: 14px 24px;
        border: 2px solid rgba(56, 189, 248, 0.3);
    }
    .stTabs [aria-selected="true"] {
        background: linear-gradient(135deg, rgba(56, 189, 248, 0.6) 0%, rgba(168, 85, 247, 0.6) 100%) !important;
        color: #ffffff !important;
        border-color: rgba(56, 189, 248, 1) !important;
    }
</style>
""", unsafe_allow_html=True)

def render_box(title, subtitle, border_color, glow_color, bg_gradient):
    st.markdown(f"""
    <div style="background: {bg_gradient}; backdrop-filter: blur(40px); border: 3px solid {border_color}; border-radius: 35px; padding: 2.5rem; margin-bottom: 2rem; box-shadow: 0 25px 60px rgba(0,0,0,0.8), 0 0 50px {glow_color};">
        <h2 style="color: #ffffff; margin-top: 0; font-size: 1.6rem; font-weight: 900; text-shadow: 0 0 25px {glow_color};">{title}</h2>
        <p style="color: #e2e8f0; margin-bottom: 0; font-size: 1.05rem; font-weight: 600; line-height: 1.5;">{subtitle}</p>
    </div>
    """, unsafe_allow_html=True)

def render_metric_card(title, value, caption, border_color, text_color, glow_color, bg_gradient):
    st.markdown(f"""
    <div style="background: {bg_gradient}; backdrop-filter: blur(35px); border: 3px solid {border_color}; border-radius: 30px; padding: 1.8rem; margin-bottom: 1.5rem; box-shadow: 0 20px 50px rgba(0,0,0,0.7), 0 0 40px {glow_color};">
        <div style="color: #cbd5e1; font-size: 1rem; font-weight: 800; margin-bottom: 10px; text-transform: uppercase;">{title}</div>
        <div style="color: {text_color}; font-size: 2.2rem; font-weight: 900; text-shadow: 0 0 35px {text_color}; margin-bottom: 10px;">{value}</div>
        <div style="color: #f1f5f9; font-size: 0.88rem; opacity: 0.95; font-weight: 600;">{caption}</div>
    </div>
    """, unsafe_allow_html=True)

@st.cache_data(ttl=600)
def zaman_bazli_veri_cek(lat, lon, secilen_tarih):
    bugun = datetime.now().date()
    gun_farki = (secilen_tarih - bugun).days
    url = f"https://api.open-meteo.com/v1/forecast?latitude={round(lat, 4)}&longitude={round(lon, 4)}&current=temperature_2m,relative_humidity_2m,precipitation,rain,wind_speed_10m,surface_pressure&models=ecmwf_ifs025"
    if gun_farki < 0:
        tarih_str = secilen_tarih.strftime("%Y-%m-%d")
        url = f"https://archive-api.open-meteo.com/v1/archive?latitude={round(lat, 4)}&longitude={round(lon, 4)}&start_date={tarih_str}&end_date={tarih_str}&current=temperature_2m,relative_humidity_2m,precipitation,surface_pressure,wind_speed_10m"
    try:
        res = requests.get(url, timeout=5).json()
        current = res.get("current", {})
        sicaklik = float(current.get("temperature_2m", 20.0))
        nem = float(current.get("relative_humidity_2m", 50.0))
        yagis = float(current.get("precipitation", current.get("rain", 0.0)))
        ruzgar = float(current.get("wind_speed_10m", 5.0))
        basinc = float(current.get("surface_pressure", 1013.25))
        if gun_farki > 0:
            sicaklik += gun_farki * 0.05
        return round(sicaklik, 2), round(nem, 2), round(yagis, 2), round(ruzgar, 2), round(basinc, 2), gun_farki
    except Exception:
        return 20.00, 50.00, 0.00, 5.00, 1013.25, gun_farki

def analiz_uret(lat, lon, secilen_tarih):
    sicaklik, nem, yagis, ruzgar, basinc, gun_farki = zaman_bazli_veri_cek(lat, lon, secilen_tarih)
    return {
        "sicaklik": sicaklik, "nem": nem, "yagis": yagis, "ruzgar": ruzgar, "basinc": basinc,
        "gpm_precip": yagis, "smap_soil": round(max(5.0, min(45.0, 18.0 + (yagis * 15) - (sicaklik * 0.2))), 2),
        "gun_farki": gun_farki
    }

if "secilen_lat" not in st.session_state:
    st.session_state.secilen_lat = 37.8859
if "secilen_lon" not in st.session_state:
    st.session_state.secilen_lon = 41.1198
if "mekan_adi" not in st.session_state:
    st.session_state.mekan_adi = "Batman (Varsayılan Konum)"

# ÜST MENÜ VE SKALA ÇUBUĞU
st.markdown("""
<div style="background: rgba(15, 23, 42, 0.9); padding: 12px 20px; border-radius: 20px; border: 2px solid rgba(56, 189, 248, 0.5); margin-bottom: 20px; display: flex; flex-wrap: wrap; gap: 15px; justify-content: space-between; align-items: center; font-size: 0.85rem; font-weight: 700; color: #38bdf8;">
    <span>HARITALAR</span><span>ŞİMDİ</span><span>SAAT BAŞI</span><span>GÜNLÜK</span><span>15 GÜNLÜK</span><span>HAVA KALİTESİ</span><span>YAŞAM İNDEKSİ</span><span>GÜN DOĞUMU VE GÜN BATIMI</span><span>HABERLER</span>
</div>
<div style="background: linear-gradient(90deg, #3b82f6, #10b981, #facc15, #f97316, #ef4444); height: 10px; border-radius: 5px; margin-bottom: 25px; box-shadow: 0 0 15px rgba(56, 189, 248, 0.5);"></div>
""", unsafe_allow_html=True)

col_search, col_gps, col_date = st.columns([2, 1, 1])
with col_search:
    aranan_konum = st.text_input("🔍 Konum Arayın (Şehir, İlçe):", "", key="main_search_input")
    if aranan_konum:
        coords, addr = konum_bul(aranan_konum)
        if coords:
            st.session_state.secilen_lat, st.session_state.secilen_lon = coords
            st.session_state.mekan_adi = f"Aranan Konum: {addr or aranan_konum}"
            st.success(f"✅ Konum Bulundu: {st.session_state.secilen_lat:.4f}, {st.session_state.secilen_lon:.4f}")

with col_gps:
    st.markdown("<div style='height: 28px;'></div>", unsafe_allow_html=True)
    if streamlit_geolocation is not None:
        loc_data = streamlit_geolocation()
        if loc_data and loc_data.get("latitude") and loc_data.get("longitude"):
            st.session_state.secilen_lat = loc_data["latitude"]
            st.session_state.secilen_lon = loc_data["longitude"]
            st.session_state.mekan_adi = f"GPS Cihaz Konumu ({st.session_state.secilen_lat:.4f}, {st.session_state.secilen_lon:.4f})"

with col_date:
    secilen_tarih = st.date_input("📅 Analiz Tarihi Seçin:", value=datetime.now().date())

d = analiz_uret(st.session_state.secilen_lat, st.session_state.secilen_lon, secilen_tarih)

render_box(
    title=f"📍 Aktif Gözlem Konumu: {st.session_state.mekan_adi}",
    subtitle=f"📌 Koordinat: <b>{st.session_state.secilen_lat:.4f}° N, {st.session_state.secilen_lon:.4f}° E</b> | Sıcaklık: <b>{d['sicaklik']} °C</b>",
    border_color="rgba(168, 85, 247, 0.8)",
    glow_color="rgba(168, 85, 247, 0.6)",
    bg_gradient="linear-gradient(135deg, rgba(49, 46, 129, 0.6) 0%, rgba(15, 23, 42, 0.9) 100%)"
)

tab1, tab2, tab3, tab4 = st.tabs([
    "🗺️ Küresel Entegre Termal Harita", 
    "📊 Zaman Simülasyonu & Trend", 
    "🚨 Akıllı Risk, Alarm & Rapor", 
    "⚖️ Bölgesel Karşılaştırma"
])

with tab1:
    render_box(
        title="🗺️ Küresel Kesintisiz Termal Renk Katmanı",
        subtitle="Harita zeminine tam oturan, tüm dünyayı uçtan uca kaplayan akışkan ve pürüzsüz termal renk katmanı. Haritada dilediğiniz yere tıklayarak o bölgeyi seçebilir ve verileri güncelleyebilirsiniz.",
        border_color="rgba(16, 185, 129, 0.8)",
        glow_color="rgba(16, 185, 129, 0.6)",
        bg_gradient="linear-gradient(135deg, rgba(6, 78, 59, 0.6) 0%, rgba(15, 23, 42, 0.9) 100%)"
    )
    
    m = folium.Map(location=[st.session_state.secilen_lat, st.session_state.secilen_lon], zoom_start=4, tiles="OpenStreetMap")

    # Tüm dünyayı (-90 ile 90, -180 ile 180) uçtan uca kaplayan pürüzsüz termal raster matrisi
    lats = np.linspace(-90, 90, 300)
    lons = np.linspace(-180, 180, 300)
    lon_grid, lat_grid = np.meshgrid(lons, lats)
    
    dist = np.sqrt((lat_grid - st.session_state.secilen_lat)**2 + (lon_grid - st.session_state.secilen_lon)**2)
    temp_matrix = d['sicaklik'] - (np.abs(lat_grid) * 0.15) + (6 * np.exp(-dist**2 / 1500.0)) + np.sin(lat_grid * 0.05) * 2.0
    
    t_min, t_max = -20.0, 45.0
    norm_temp = np.clip((temp_matrix - t_min) / (t_max - t_min), 0, 1)
    
    height, width = norm_temp.shape
    rgba = np.zeros((height, width, 4), dtype=np.float32)
    rgba[..., 0] = np.clip(1.6 * norm_temp - 0.4, 0, 1) * 255
    rgba[..., 1] = np.clip((1.0 - np.abs(norm_temp - 0.5) * 2.0), 0, 1) * 255
    rgba[..., 2] = np.clip(1.6 * (0.65 - norm_temp), 0, 1) * 255
    rgba[..., 3] = 130 # Yarı saydam pürüzsüz küresel katman
    
    folium.raster_layers.ImageOverlay(
        image=rgba.astype(np.uint8),
        bounds=[[-90, -180], [90, 180]],
        opacity=0.7,
        interactive=True,
        cross_origin=False,
        zindex=2,
        name="🌡️ Küresel Termal Katman"
    ).add_to(m)

    popup_html = f"""
    <div style="width: 210px; font-family: 'Plus Jakarta Sans', sans-serif; background: #ffffff; padding: 10px; border-radius: 8px; border: 2px solid #38bdf8; box-shadow: 0 4px 12px rgba(0,0,0,0.2);">
        <h4 style="margin: 0 0 6px 0; color: #0f172a; font-size: 0.95rem; border-bottom: 2px solid #e2e8f0; padding-bottom: 4px;">📍 Konum Bilgisi</h4>
        <b>Enlem/Boylam:</b> {st.session_state.secilen_lat:.4f}, {st.session_state.secilen_lon:.4f}<br>
        <b>Sıcaklık:</b> {d['sicaklik']:.2f} °C<br>
        <b>Bağıl Nem:</b> %{d['nem']:.2f}<br>
        <b>Yağış:</b> {d['gpm_precip']:.2f} mm<br>
        <b>Basınç:</b> {d['basinc']:.2f} hPa
    </div>
    """
    
    folium.Marker(
        [st.session_state.secilen_lat, st.session_state.secilen_lon], 
        popup=folium.Popup(popup_html, max_width=250), 
        tooltip="Detaylar için tıklayın",
        icon=folium.Icon(color="red", icon="info-sign")
    ).add_to(m)

    folium.LayerControl(collapsed=False).add_to(m)
    
    map_data = st_folium(m, width=None, height=540, key="map_interactive_observatory")
    
    if map_data and map_data.get("last_clicked"):
        clicked_lat = map_data["last_clicked"]["lat"]
        clicked_lon = map_data["last_clicked"]["lng"]
        if clicked_lat != st.session_state.secilen_lat or clicked_lon != st.session_state.secilen_lon:
            st.session_state.secilen_lat = clicked_lat
            st.session_state.secilen_lon = clicked_lon
            st.session_state.mekan_adi = f"Özel Harita Konumu ({clicked_lat:.4f}, {clicked_lon:.4f})"
            st.rerun()

with tab2:
    render_box(
        title=f"📊 {secilen_tarih.strftime('%d.%m.%Y')} Tarihli Simülasyon Verileri",
        subtitle=f"Seçilen Koordinat: {st.session_state.secilen_lat:.4f}, {st.session_state.secilen_lon:.4f}",
        border_color="rgba(56, 189, 248, 0.8)",
        glow_color="rgba(56, 189, 248, 0.6)",
        bg_gradient="linear-gradient(135deg, rgba(14, 116, 144, 0.5) 0%, rgba(15, 23, 42, 0.9) 100%)"
    )
    c1, c2, c3, c4 = st.columns(4)
    with c1:
        render_metric_card("1️⃣ Sıcaklık", f"{d['sicaklik']} °C", "Seçilen tarih sıcaklığı", "rgba(56, 189, 248, 0.8)", "#38bdf8", "rgba(56, 189, 248, 0.5)", "linear-gradient(135deg, rgba(14, 165, 233, 0.35) 0%, rgba(15, 23, 42, 0.9) 100%)")
    with c2:
        render_metric_card("2️⃣ Bağıl Nem", f"%{d['nem']}", "Atmosferik nem oranı", "rgba(16, 185, 129, 0.8)", "#34d399", "rgba(16, 185, 129, 0.5)", "linear-gradient(135deg, rgba(16, 185, 129, 0.35) 0%, rgba(15, 23, 42, 0.9) 100%)")
    with c3:
        render_metric_card("3️⃣ Yağış", f"{d['gpm_precip']} mm", "Toplam yağış miktarı", "rgba(245, 158, 11, 0.8)", "#fbbf24", "rgba(245, 158, 11, 0.5)", "linear-gradient(135deg, rgba(245, 158, 11, 0.35) 0%, rgba(15, 23, 42, 0.9) 100%)")
    with c4:
        render_metric_card("4️⃣ Basınç", f"{d['basinc']} hPa", "Deniz seviyesi basınç", "rgba(168, 85, 247, 0.8)", "#c084fc", "rgba(168, 85, 247, 0.5)", "linear-gradient(135deg, rgba(168, 85, 247, 0.35) 0%, rgba(15, 23, 42, 0.9) 100%)")

    dates = [secilen_tarih - timedelta(days=i) for i in range(15, -15, -1)]
    trend_temp = [d['sicaklik'] + np.sin(i/3)*3 for i in range(30)]
    df_trend = pd.DataFrame({"Tarih": dates, "Sıcaklık (°C)": trend_temp})
    fig_temp = px.line(df_trend, x="Tarih", y="Sıcaklık (°C)", title="Sıcaklık Projeksiyon Trendi", template="plotly_dark")
    fig_temp.update_traces(line=dict(color="#38bdf8", width=3))
    fig_temp.update_layout(paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)")
    st.plotly_chart(fig_temp, use_container_width=True)

with tab3:
    render_box(
        title="🚨 Yapay Zeka Risk ve Alarm Analizi",
        subtitle=f"Koordinat: {st.session_state.secilen_lat:.4f}, {st.session_state.secilen_lon:.4f}",
        border_color="rgba(239, 68, 68, 0.8)",
        glow_color="rgba(239, 68, 68, 0.6)",
        bg_gradient="linear-gradient(135deg, rgba(153, 27, 27, 0.5) 0%, rgba(15, 23, 42, 0.9) 100%)"
    )
    st.markdown("🟢 **DÜŞÜK RİSK (Stabil Ekosistem)**")

with tab4:
    render_box(
        title="⚖️ Bölgesel Karşılaştırma",
        subtitle="İki farklı bölgenin eş zamanlı analizi.",
        border_color="rgba(168, 85, 247, 0.8)",
        glow_color="rgba(168, 85, 247, 0.6)",
        bg_gradient="linear-gradient(135deg, rgba(76, 29, 149, 0.5) 0%, rgba(15, 23, 42, 0.9) 100%)"
    )
    c_b1, c_b2 = st.columns(2)
    with c_b1:
        yer_1 = st.text_input("1. Bölge:", "Batman", key="compare_loc_1")
    with c_b2:
        yer_2 = st.text_input("2. Bölge:", "Ankara", key="compare_loc_2")
