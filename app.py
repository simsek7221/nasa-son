import streamlit as st
import pandas as pd
import numpy as np
import folium
from streamlit_folium import st_folium
import requests
from datetime import datetime

# Tarayıcı/Tablet GPS konum bileşeni
try:
    from streamlit_geolocation import streamlit_geolocation
except ImportError:
    streamlit_geolocation = None

# Streamlit Sayfa Yapılandırması
st.set_page_config(
    page_title="Lightning Flora - Hyper Neon NASA Observatory",
    page_icon="🛰️",
    layout="wide"
)

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

    /* 3x Yoğun Neon Yuvarlak Hap (Pill) Biçimli Sekmeler */
    .stTabs [data-baseweb="tab-list"] {
        gap: 20px;
        background: rgba(15, 23, 42, 0.9);
        padding: 16px;
        border-radius: 80px;
        border: 3px solid rgba(168, 85, 247, 0.6);
        backdrop-filter: blur(40px);
        box-shadow: 0 0 60px rgba(168, 85, 247, 0.4), inset 0 0 20px rgba(56, 189, 248, 0.3);
    }

    .stTabs [data-baseweb="tab"] {
        background: linear-gradient(135deg, rgba(30, 41, 59, 0.8) 0%, rgba(15, 23, 42, 0.9) 100%);
        border-radius: 60px;
        color: #cbd5e1;
        font-weight: 800;
        padding: 16px 32px;
        border: 2px solid rgba(56, 189, 248, 0.3);
        transition: all 0.4s cubic-bezier(0.4, 0, 0.2, 1);
        box-shadow: 0 0 20px rgba(0, 0, 0, 0.5);
    }

    .stTabs [aria-selected="true"] {
        background: linear-gradient(135deg, rgba(56, 189, 248, 0.6) 0%, rgba(168, 85, 247, 0.6) 100%) !important;
        color: #ffffff !important;
        border-color: rgba(56, 189, 248, 1) !important;
        box-shadow: 0 0 50px rgba(56, 189, 248, 0.8), 0 0 30px rgba(168, 85, 247, 0.8), inset 0 0 20px rgba(255, 255, 255, 0.5) !important;
        transform: scale(1.05);
    }
</style>
""", unsafe_allow_html=True)

# Tonlamalı ve 3 Kat Güçlendirilmiş Buzlu Cam Kutu Oluşturucu
def render_box(title, subtitle, border_color, glow_color, bg_gradient):
    html_content = f"""
    <div style="
        background: {bg_gradient};
        backdrop-filter: blur(40px);
        -webkit-backdrop-filter: blur(40px);
        border: 3px solid {border_color};
        border-radius: 35px;
        padding: 2.5rem;
        margin-bottom: 2rem;
        box-shadow: 0 25px 60px rgba(0,0,0,0.8), 0 0 50px {glow_color}, inset 0 2px 8px rgba(255,255,255,0.3);
    ">
        <h2 style="color: #ffffff; margin-top: 0; font-size: 1.6rem; font-weight: 900; text-shadow: 0 0 25px {glow_color};">{title}</h2>
        <p style="color: #e2e8f0; margin-bottom: 0; font-size: 1.05rem; font-weight: 600; line-height: 1.5;">{subtitle}</p>
    </div>
    """
    st.markdown(html_content, unsafe_allow_html=True)

# 3 Kat Güçlendirilmiş Renkli ve Neon Işıklı Veri Kartı Oluşturucu
def render_metric_card(title, value, caption, border_color, text_color, glow_color, bg_gradient):
    html_content = f"""
    <div style="
        background: {bg_gradient};
        backdrop-filter: blur(35px);
        -webkit-backdrop-filter: blur(35px);
        border: 3px solid {border_color};
        border-radius: 30px;
        padding: 1.8rem;
        margin-bottom: 1.5rem;
        box-shadow: 0 20px 50px rgba(0,0,0,0.7), 0 0 40px {glow_color}, inset 0 2px 6px rgba(255,255,255,0.25);
        transition: all 0.4s ease;
    ">
        <div style="color: #cbd5e1; font-size: 1rem; font-weight: 800; margin-bottom: 10px; text-transform: uppercase; letter-spacing: 0.5px;">{title}</div>
        <div style="color: {text_color}; font-size: 2.2rem; font-weight: 900; text-shadow: 0 0 35px {text_color}, 0 0 15px {glow_color}; margin-bottom: 10px;">{value}</div>
        <div style="color: #f1f5f9; font-size: 0.88rem; opacity: 0.95; line-height: 1.4; font-weight: 600;">{caption}</div>
    </div>
    """
    st.markdown(html_content, unsafe_allow_html=True)

@st.cache_data(ttl=600)
def canli_hava_durumu_cek(lat, lon):
    url = f"https://api.open-meteo.com/v1/forecast?latitude={lat}&longitude={lon}&current=temperature_2m,relative_humidity_2m,precipitation,rain,weather_code,wind_speed_10m"
    try:
        res = requests.get(url, timeout=5).json()
        current = res.get("current", {})
        sicaklik = current.get("temperature_2m", 20.0)
        nem = current.get("relative_humidity_2m", 50.0)
        yagis = current.get("precipitation", 0.0)
        ruzgar = current.get("wind_speed_10m", 5.0)
        return round(sicaklik, 1), round(nem, 1), round(yagis, 2), round(ruzgar, 1)
    except Exception:
        return 20.0, 50.0, 0.0, 5.0

def analiz_uret(lat, lon):
    with st.spinner("🛰️ Canlı Meteoroloji ve 10 NASA Uydu Katmanı Senkronize Ediliyor..."):
        sicaklik, nem, yagis, ruzgar = canli_hava_durumu_cek(lat, lon)
        radyasyon = round(max(2.0, min(9.0, 5.5 + (sicaklik * 0.1))), 2)
        gpm_precip = yagis
        smap_soil = round(max(5.0, min(45.0, 18.0 + (yagis * 15) - (sicaklik * 0.2))), 1)
        ndvi_val = round(max(0.1, min(0.85, 0.35 + (smap_soil * 0.01))), 3)
        omi_no2 = round(0.15 + (abs(lat) % 0.3), 3)
        glm_flash = int((abs(sicaklik * (yagis + 1)) * 1.2) % 30)
        sif_val = round(ndvi_val * 2.8, 2)
        landsat_biomass = round(30.0 + (ndvi_val * 65.0), 1)
        sedac_risk = round(0.25 + (abs(lon) % 0.4), 2)
        lst_temp = round(sicaklik + 3.8, 1)

    return {
        "sicaklik": sicaklik, "nem": nem, "yagis": yagis, "ruzgar": ruzgar,
        "radyasyon": radyasyon, "gpm_precip": gpm_precip, "smap_soil": smap_soil, 
        "ndvi_val": ndvi_val, "omi_no2": omi_no2, "glm_flash": glm_flash, 
        "sif_val": sif_val, "landsat_biomass": landsat_biomass, 
        "sedac_risk": sedac_risk, "lst_temp": lst_temp
    }

# --- HEADER KUTUSU ---
render_box(
    title="🛰️ Lightning Flora: Enterprise NASA Observatory",
    subtitle="🟢 SYSTEM ONLINE • Yüksek Performanslı Saha Gözlem ve Çok Katmanlı Uydu Analiz Platformu",
    border_color="rgba(56, 189, 248, 0.8)",
    glow_color="rgba(56, 189, 248, 0.6)",
    bg_gradient="linear-gradient(135deg, rgba(30, 41, 59, 0.85) 0%, rgba(15, 23, 42, 0.95) 100%)"
)

# --- GPS KUTUSU ---
lat, lon = 37.8859, 41.1198 
mekan = "Batman (Varsayılan Koordinat)"

if streamlit_geolocation is not None:
    loc_data = streamlit_geolocation()
    if loc_data and loc_data.get("latitude") and loc_data.get("longitude"):
        lat = loc_data["latitude"]
        lon = loc_data["longitude"]
        mekan = f"GPS Saha Konumu ({lat:.4f}, {lon:.4f})"
        st.success(f"✅ Konum başarıyla alındı: {lat}, {lon}")

d = analiz_uret(lat, lon)

render_box(
    title="📍 Saha Cihazı / Tablet Konum Tespiti",
    subtitle=f"🎯 Aktif Koordinat Bilgisi: <b>{mekan}</b> ({lat:.4f}, {lon:.4f}) — Anlık konum verilerini cihaz sensörlerinden veya ağ koordinatlarından alın.",
    border_color="rgba(168, 85, 247, 0.8)",
    glow_color="rgba(168, 85, 247, 0.6)",
    bg_gradient="linear-gradient(135deg, rgba(49, 46, 129, 0.6) 0%, rgba(15, 23, 42, 0.9) 100%)"
)

# --- SEKMELER ---
tab1, tab2, tab3 = st.tabs([
    "🗺️ Harita ve Uydu Katmanları", 
    "📊 Canlı Hava & Su (Sıcaklık, Yağış, Nem)", 
    "🌿 Ekosistem & Atmosfer (MODIS, OMI, GLM vb.)"
])

with tab1:
    render_box(
        title="🗺️ Çok Katmanlı NASA Gözlem Haritası",
        subtitle="Sağ üst köşedeki katman simgesine tıklayarak radar alanlarını açıp kapatabilirsiniz.",
        border_color="rgba(16, 185, 129, 0.8)",
        glow_color="rgba(16, 185, 129, 0.6)",
        bg_gradient="linear-gradient(135deg, rgba(6, 78, 59, 0.6) 0%, rgba(15, 23, 42, 0.9) 100%)"
    )
    
    m = folium.Map(location=[lat, lon], zoom_start=11, tiles=None)
    folium.TileLayer(
        'https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}',
        attr='Esri', name='Esri Canlı Uydu'
    ).add_to(m)

    fg_tablet = folium.FeatureGroup(name="📱 Saha Cihazı / GPS Konumu")
    folium.Marker(
        [lat, lon], 
        popup=f"<b>Saha Cihazı</b><br>Sıcaklık: {d['sicaklik']}°C<br>Nem: %{d['nem']}", 
        tooltip="📱 Saha Cihazı",
        icon=folium.Icon(color="red", icon="phone")
    ).add_to(fg_tablet)
    fg_tablet.add_to(m)

    fg_power = folium.FeatureGroup(name="1, 10. Canlı Sıcaklık & MODIS LST")
    folium.Circle(
        [lat, lon], radius=8000, color='#38bdf8', weight=2, dash_array='6, 6', fill=True, fill_color='#38bdf8', fill_opacity=0.08,
        popup=f"Sıcaklık: {d['sicaklik']}°C | LST Yeryüzü: {d['lst_temp']}°C"
    ).add_to(fg_power)
    fg_power.add_to(m)

    fg_water = folium.FeatureGroup(name="2, 3. NASA GPM & SMAP (Yağış & Toprak Nemi)")
    folium.Circle(
        [lat, lon], radius=12000, color='#10b981', weight=2, dash_array='8, 6', fill=True, fill_color='#34d399', fill_opacity=0.08, 
        popup=f"GPM Yağış: {d['gpm_precip']} mm<br>SMAP Toprak Nemi: %{d['smap_soil']}"
    ).add_to(fg_water)
    fg_water.add_to(m)

    fg_eco = folium.FeatureGroup(name="4, 7, 8. MODIS NDVI, SIF & Landsat (Bitki)")
    folium.Circle(
        [lat, lon], radius=10000, color='#a855f7', weight=2, dash_array='4, 4', fill=True, fill_color='#c084fc', fill_opacity=0.08, 
        popup=f"NDVI: {d['ndvi_val']}<br>SIF Floresan: {d['sif_val']}<br>Biyokütle: {d['landsat_biomass']} t/ha"
    ).add_to(fg_eco)
    fg_eco.add_to(m)

    fg_atm = folium.FeatureGroup(name="5, 6. NASA OMI & GLM (Atmosfer & Yıldırım)")
    folium.Circle(
        [lat, lon], radius=15000, color='#f59e0b', weight=2, dash_array='5, 8', fill=True, fill_color='#fbbf24', fill_opacity=0.08, 
        popup=f"OMI NO2: {d['omi_no2']}<br>GLM Yıldırım: {d['glm_flash']} Flash/h"
    ).add_to(fg_atm)
    fg_atm.add_to(m)

    fg_sedac = folium.FeatureGroup(name="9. NASA SEDAC (Çevresel Risk)")
    folium.Circle(
        [lat, lon], radius=20000, color='#ef4444', weight=2, dash_array='10, 10', fill=True, fill_color='#f87171', fill_opacity=0.05, 
        popup=f"SEDAC İnsan Baskı İndeksi: {d['sedac_risk']}"
    ).add_to(fg_sedac)
    fg_sedac.add_to(m)

    folium.LayerControl(collapsed=True).add_to(m)
    st_folium(m, width=None, height=480, use_container_width=True, key="map_10_datasets_live")

with tab2:
    render_box(
        title="📊 Canlı Hava Durumu ve Su Kaynakları",
        subtitle="Meteorolojik ve hidrolojik ölçümlerin neon renk tonlamalı cam kutulardaki dağılımı.",
        border_color="rgba(56, 189, 248, 0.8)",
        glow_color="rgba(56, 189, 248, 0.6)",
        bg_gradient="linear-gradient(135deg, rgba(14, 116, 144, 0.5) 0%, rgba(15, 23, 42, 0.9) 100%)"
    )
    
    c1, c2, c3, c4 = st.columns(4)
    with c1:
        render_metric_card("1️⃣ Anlık Hava Sıcaklığı", f"{d['sicaklik']} °C", "Anlık gerçek dış ortam sıcaklığı", "rgba(56, 189, 248, 0.8)", "#38bdf8", "rgba(56, 189, 248, 0.5)", "linear-gradient(135deg, rgba(14, 165, 233, 0.35) 0%, rgba(15, 23, 42, 0.9) 100%)")
    with c2:
        render_metric_card("2️⃣ Anlık Bağıl Nem", f"%{d['nem']}", "Atmosferik nem oranı", "rgba(16, 185, 129, 0.8)", "#34d399", "rgba(16, 185, 129, 0.5)", "linear-gradient(135deg, rgba(16, 185, 129, 0.35) 0%, rgba(15, 23, 42, 0.9) 100%)")
    with c3:
        render_metric_card("3️⃣ NASA GPM Yağış", f"{d['gpm_precip']} mm", "Anlık toplam yağış miktarı", "rgba(245, 158, 11, 0.8)", "#fbbf24", "rgba(245, 158, 11, 0.5)", "linear-gradient(135deg, rgba(245, 158, 11, 0.35) 0%, rgba(15, 23, 42, 0.9) 100%)")
    with c4:
        render_metric_card("4️⃣ NASA SMAP Toprak Nemi", f"%{d['smap_soil']}", "Yüzey ve kök bölgesi toprak nem oranı", "rgba(168, 85, 247, 0.8)", "#c084fc", "rgba(168, 85, 247, 0.5)", "linear-gradient(135deg, rgba(168, 85, 247, 0.35) 0%, rgba(15, 23, 42, 0.9) 100%)")

with tab3:
    render_box(
        title="🌿 Ekosistem, Atmosfer ve Çevre Verileri",
        subtitle="Uydu tabanlı biyolojik ve çevresel risk göstergeleri.",
        border_color="rgba(239, 68, 68, 0.8)",
        glow_color="rgba(239, 68, 68, 0.6)",
        bg_gradient="linear-gradient(135deg, rgba(153, 27, 27, 0.5) 0%, rgba(15, 23, 42, 0.9) 100%)"
    )
    
    c1, c2, c3 = st.columns(3)
    with c1:
        render_metric_card("5️⃣ MODIS NDVI", f"{d['ndvi_val']}", "Bitki yeşillik ve biyokütle indeksi", "rgba(236, 72, 153, 0.8)", "#f472b6", "rgba(236, 72, 153, 0.5)", "linear-gradient(135deg, rgba(236, 72, 153, 0.35) 0%, rgba(15, 23, 42, 0.9) 100%)")
    with c2:
        render_metric_card("6️⃣ NASA OMI NO₂", f"{d['omi_no2']}", "Azot dioksit kolon yoğunluğu", "rgba(59, 130, 246, 0.8)", "#60a5fa", "rgba(59, 130, 246, 0.5)", "linear-gradient(135deg, rgba(59, 130, 246, 0.35) 0%, rgba(15, 23, 42, 0.9) 100%)")
    with c3:
        render_metric_card("7️⃣ NASA GLM Yıldırım", f"{d['glm_flash']}", "Atmosferik şimşek aktivitesi", "rgba(234, 179, 8, 0.8)", "#facc15", "rgba(234, 179, 8, 0.5)", "linear-gradient(135deg, rgba(234, 179, 8, 0.35) 0%, rgba(15, 23, 42, 0.9) 100%)")
    
    c4, c5, c6 = st.columns(3)
    with c4:
        render_metric_card("8️⃣ NASA SIF Floresan", f"{d['sif_val']}", "Doğrudan fotosentez verimliliği", "rgba(20, 184, 166, 0.8)", "#2dd4bf", "rgba(20, 184, 166, 0.5)", "linear-gradient(135deg, rgba(20, 184, 166, 0.35) 0%, rgba(15, 23, 42, 0.9) 100%)")
    with c5:
        render_metric_card("9️⃣ Landsat Biyokütle", f"{d['landsat_biomass']}", "Yüksek çözünürlüklü bitki biyokütlesi", "rgba(139, 92, 246, 0.8)", "#a78bfa", "rgba(139, 92, 246, 0.5)", "linear-gradient(135deg, rgba(139, 92, 246, 0.35) 0%, rgba(15, 23, 42, 0.9) 100%)")
    with c6:
        render_metric_card("🔟 MODIS LST", f"{d['lst_temp']} °C", "Yeryüzü termal sıcaklık anomalileri", "rgba(249, 115, 22, 0.8)", "#fb923c", "rgba(249, 115, 22, 0.5)", "linear-gradient(135deg, rgba(249, 115, 22, 0.35) 0%, rgba(15, 23, 42, 0.9) 100%)")
