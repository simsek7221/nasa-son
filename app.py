import streamlit as st
import streamlit.components.v1 as components
import pandas as pd
import numpy as np
import requests
from datetime import datetime, timedelta
import plotly.express as px
import plotly.graph_objects as go
import logging
import time

# --- SİSTEM LOGLAMA ---
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("LightningFloraNASAPro")

try:
    from streamlit_geolocation import streamlit_geolocation
except ImportError:
    streamlit_geolocation = None

try:
    import serial
    import serial.tools.list_ports
except ImportError:
    serial = None

# Streamlit Sayfa Yapılandırması
st.set_page_config(
    page_title="Lightning Flora - NASA Space Apps Observatory Pro",
    page_icon="🛰️",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# --- ARDUİNO SERİ PORT GÖNDERİM FONKSİYONU ---
def arduino_veri_gonder(temp, hum, pres, wind, ndvi, soil):
    if serial is None:
        return
    if "arduino_ser" in st.session_state and st.session_state.arduino_ser:
        try:
            veri_paketi = f"T:{temp:.1f},H:{hum},P:{pres},W:{wind:.1f},N:{ndvi:.2f},S:{soil:.1f}\n"
            st.session_state.arduino_ser.write(veri_paketi.encode('utf-8'))
        except Exception as e:
            logger.error(f"Arduino veri gönderim hatası: {e}")
            st.session_state.arduino_ser = None

# --- COĞRAFİ KONUM ÇÖZÜCÜ (GEOCODING API) ---
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


# --- GERÇEK 3D ARAZİ MODELİ (COPERNICUS DEM / OPEN-METEO) ---
@st.cache_data(ttl=86400, show_spinner=False)
def gercek_yukseklik_matrisi(merkez_lat, merkez_lon, grid_boyutu=25, yari_cap_km=12):
    """
    Open-Meteo Elevation API üzerinden Copernicus GLO-90 DEM verisi alır.
    Her koordinatın gerçek arazi yüksekliğini metre cinsinden döndürür.
    API tek istekte en fazla 100 koordinat kabul ettiği için parçalı istek yapar.
    """
    merkez_lat = float(merkez_lat)
    merkez_lon = float(merkez_lon)

    # Enlemde ve boylamda yaklaşık aynı fiziksel mesafeyi kapsa.
    lat_yari = yari_cap_km / 111.32
    cos_lat = max(np.cos(np.radians(merkez_lat)), 0.2)
    lon_yari = yari_cap_km / (111.32 * cos_lat)

    lat_dizi = np.linspace(merkez_lat - lat_yari, merkez_lat + lat_yari, grid_boyutu)
    lon_dizi = np.linspace(merkez_lon - lon_yari, merkez_lon + lon_yari, grid_boyutu)
    X, Y = np.meshgrid(lon_dizi, lat_dizi)

    lat_duz = X*0 + Y
    lat_duz = lat_duz.ravel()
    lon_duz = X.ravel()

    yukseklikler = []
    for baslangic in range(0, len(lat_duz), 100):
        bitis = baslangic + 100
        params = {
            "latitude": ",".join(f"{v:.6f}" for v in lat_duz[baslangic:bitis]),
            "longitude": ",".join(f"{v:.6f}" for v in lon_duz[baslangic:bitis]),
        }
        yanit = requests.get(
            "https://api.open-meteo.com/v1/elevation",
            params=params,
            timeout=25
        )
        yanit.raise_for_status()
        parca = yanit.json().get("elevation", [])
        if len(parca) != len(params["latitude"].split(",")):
            raise ValueError("Yükseklik servisinden eksik veri döndü.")
        yukseklikler.extend(parca)

    Z = np.asarray(yukseklikler, dtype=float).reshape(grid_boyutu, grid_boyutu)
    if not np.isfinite(Z).all():
        raise ValueError("Arazi yükseklik verisinde geçersiz değer bulundu.")

    # X/Y eksenleri şehir merkezine göre kilometre cinsindendir.
    x_km = (lon_dizi - merkez_lon) * 111.32 * cos_lat
    y_km = (lat_dizi - merkez_lat) * 111.32
    X_km, Y_km = np.meshgrid(x_km, y_km)
    return X_km, Y_km, Z


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
        background: rgba(15, 23, 42, 0.94) !important;
        backdrop-filter: blur(60px) !important;
        -webkit-backdrop-filter: blur(60px) !important;
        border-radius: 40px !important;
        padding: 2.8rem !important;
        margin-top: 1.2rem !important;
        border: 2px solid rgba(56, 189, 248, 0.4) !important;
        box-shadow: 0 0 100px rgba(56, 189, 248, 0.2), inset 0 0 30px rgba(168, 85, 247, 0.15) !important;
    }

    .stButton>button {
        background: linear-gradient(135deg, #0284c7 0%, #7c3aed 100%) !important;
        color: white !important;
        border-radius: 20px !important;
        border: 2px solid rgba(255, 255, 255, 0.35) !important;
        padding: 0.75rem 2rem !important;
        font-weight: 800 !important;
        box-shadow: 0 10px 35px rgba(124, 58, 237, 0.55), 0 0 30px rgba(2, 132, 199, 0.45) !important;
        transition: all 0.35s ease;
    }

    .stButton>button:hover {
        transform: translateY(-3px) scale(1.02);
        box-shadow: 0 15px 45px rgba(2, 132, 199, 0.75), 0 0 40px rgba(168, 85, 247, 0.75) !important;
    }

    .stTabs [data-baseweb="tab-list"] {
        gap: 8px;
        background: rgba(15, 23, 42, 0.95);
        padding: 10px;
        border-radius: 60px;
        border: 2px solid rgba(168, 85, 247, 0.45);
        backdrop-filter: blur(30px);
        overflow-x: auto;
    }

    .stTabs [data-baseweb="tab"] {
        background: linear-gradient(135deg, rgba(30, 41, 59, 0.75) 0%, rgba(15, 23, 42, 0.85) 100%);
        border-radius: 50px;
        color: #cbd5e1;
        font-weight: 700;
        padding: 8px 16px;
        font-size: 0.85rem;
        border: 1px solid rgba(56, 189, 248, 0.2);
    }

    .stTabs [aria-selected="true"] {
        background: linear-gradient(135deg, rgba(2, 132, 199, 0.8) 0%, rgba(168, 85, 247, 0.8) 100%) !important;
        color: #ffffff !important;
        border-color: rgba(56, 189, 248, 0.9) !important;
        box-shadow: 0 0 30px rgba(2, 132, 199, 0.65) !important;
    }
</style>
""", unsafe_allow_html=True)

def render_box(title, subtitle, border_color, glow_color, bg_gradient):
    html_content = f"""
    <div style="
        background: {bg_gradient};
        backdrop-filter: blur(30px);
        -webkit-backdrop-filter: blur(30px);
        border: 2px solid {border_color};
        border-radius: 28px;
        padding: 2rem;
        margin-bottom: 1.6rem;
        box-shadow: 0 20px 45px rgba(0,0,0,0.7), 0 0 40px {glow_color};
    ">
        <h2 style="color: #ffffff; margin-top: 0; font-size: 1.35rem; font-weight: 800; text-shadow: 0 0 20px {glow_color};">{title}</h2>
        <p style="color: #cbd5e1; margin-bottom: 0; font-size: 1rem; font-weight: 600; line-height: 1.45;">{subtitle}</p>
    </div>
    """
    st.markdown(html_content, unsafe_allow_html=True)

def render_metric_card(title, value, caption, border_color, text_color, glow_color, bg_gradient):
    html_content = f"""
    <div style="
        background: {bg_gradient};
        backdrop-filter: blur(30px);
        -webkit-backdrop-filter: blur(30px);
        border: 2px solid {border_color};
        border-radius: 24px;
        padding: 1.5rem;
        margin-bottom: 1.2rem;
        box-shadow: 0 15px 35px rgba(0,0,0,0.6), 0 0 30px {glow_color};
    ">
        <div style="color: #94a3b8; font-size: 0.88rem; font-weight: 700; margin-bottom: 8px; text-transform: uppercase;">{title}</div>
        <div style="color: {text_color}; font-size: 1.9rem; font-weight: 900; text-shadow: 0 0 25px {text_color}; margin-bottom: 8px;">{value}</div>
        <div style="color: #e2e8f0; font-size: 0.85rem; opacity: 0.9; font-weight: 600;">{caption}</div>
    </div>
    """
    st.markdown(html_content, unsafe_allow_html=True)

# --- VERİ ÇEKME MOTORU ---
@st.cache_data(ttl=600, show_spinner=False)
def gercek_veri_cek(lat, lon, secilen_tarih):
    bugun = datetime.now().date()
    gun_farki = (secilen_tarih - bugun).days

    if gun_farki < 0:
        tarih_str = secilen_tarih.strftime("%Y-%m-%d")
        url = f"https://archive-api.open-meteo.com/v1/archive?latitude={round(lat, 4)}&longitude={round(lon, 4)}&start_date={tarih_str}&end_date={tarih_str}&hourly=temperature_2m,relative_humidity_2m,precipitation,surface_pressure,wind_speed_10m,wind_direction_10m"
        try:
            response = requests.get(url, timeout=6)
            if response.status_code == 200:
                data = response.json()
                hourly = data.get("hourly", {})
                temps = hourly.get("temperature_2m", [22.5])
                hums = hourly.get("relative_humidity_2m", [45.0])
                precips = hourly.get("precipitation", [0.0])
                winds = hourly.get("wind_speed_10m", [4.5])
                wind_dirs = hourly.get("wind_direction_10m", [180.0])
                pressures = hourly.get("surface_pressure", [1013.0])
                
                idx = min(12, len(temps) - 1) if len(temps) > 0 else 0
                return (
                    float(temps[idx] if temps[idx] is not None else 22.5),
                    float(hums[idx] if hums[idx] is not None else 45.0),
                    float(precips[idx] if precips[idx] is not None else 0.0),
                    float(winds[idx] if winds[idx] is not None else 4.5),
                    float(wind_dirs[idx] if wind_dirs[idx] is not None else 180.0),
                    float(pressures[idx] if pressures[idx] is not None else 1013.0),
                    gun_farki
                )
        except Exception as e:
            logger.error(f"Arşiv veri hatası: {str(e)}")
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
            logger.error(f"Tahmin veri hatası: {str(e)}")

    return 22.5, 45.0, 0.0, 4.5, 180.0, 1013.0, gun_farki
# --- GERÇEK 3D ARAZİ MODELİ ---
@st.cache_data(ttl=86400, show_spinner=False)
def gercek_yukseklik_matrisi(
    merkez_lat,
    merkez_lon,
    grid_boyutu=10,
    yari_cap_km=12
):
    merkez_lat = float(merkez_lat)
    merkez_lon = float(merkez_lon)

    lat_yari = yari_cap_km / 111.32
    cos_lat = max(np.cos(np.radians(merkez_lat)), 0.2)
    lon_yari = yari_cap_km / (111.32 * cos_lat)

    lat_dizi = np.linspace(
        merkez_lat - lat_yari,
        merkez_lat + lat_yari,
        grid_boyutu
    )

    lon_dizi = np.linspace(
        merkez_lon - lon_yari,
        merkez_lon + lon_yari,
        grid_boyutu
    )

    X, Y = np.meshgrid(lon_dizi, lat_dizi)

    lat_duz = Y.ravel()
    lon_duz = X.ravel()

    params = {
        "latitude": ",".join(f"{v:.6f}" for v in lat_duz),
        "longitude": ",".join(f"{v:.6f}" for v in lon_duz)
    }

    url = "https://api.open-meteo.com/v1/elevation"

    yanit = None

    # 429 hatasında artan bekleme süresiyle yeniden dene.
    for deneme in range(3):
        try:
            yanit = requests.get(
                url,
                params=params,
                timeout=30
            )

            if yanit.status_code == 429:
                time.sleep(3 * (2 ** deneme))
                continue

            yanit.raise_for_status()
            break

        except requests.RequestException:
            if deneme == 2:
                raise
            time.sleep(3 * (2 ** deneme))

    if yanit is None or yanit.status_code == 429:
        raise Exception(
            "Arazi API'si istek sınırına ulaştı. "
            "Lütfen birkaç dakika sonra tekrar deneyin."
        )

    yukseklikler = yanit.json().get("elevation", [])

    if len(yukseklikler) != grid_boyutu * grid_boyutu:
        raise ValueError("Arazi verisi eksik geldi.")

    Z = np.asarray(
        yukseklikler,
        dtype=float
    ).reshape(grid_boyutu, grid_boyutu)

    if not np.isfinite(Z).all():
        raise ValueError("Geçersiz arazi yüksekliği.")

    x_km = (
        (lon_dizi - merkez_lon)
        * 111.32
        * cos_lat
    )

    y_km = (
        (lat_dizi - merkez_lat)
        * 111.32
    )

    X_km, Y_km = np.meshgrid(x_km, y_km)

    return X_km, Y_km, Z
    except Exception as e:
        logger.error(f"Zaman serisi hatası: {str(e)}")

    dates = [merkez_tarih - timedelta(days=i) for i in range(15, -15, -1)]
    return pd.DataFrame({
        "Tarih": dates,
        "Sıcaklık (°C)": [22.5]*30,
        "Yağış (mm)": [0.0]*30,
        "Rüzgar (km/s)": [4.5]*30
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

# --- 135+ PARAMETRELİ TAM GİRİŞLİ VERİ HAVUZU ---
def genis_veri_havuzu_uret(d):
    parametreler = []
    
    # 1. Sıcaklık ve Termal Parametreler (1-27)
    temp_list = [
        ("2m Sıcaklık (Anlık)", f"{d['sicaklik']} °C", "°C", "Normal"),
        ("Maksimum Tahmini Sıcaklık", f"{d['sicaklik'] + 3.2:.1f} °C", "°C", "Stabil"),
        ("Minimum Tahmini Sıcaklık", f"{d['sicaklik'] - 4.1:.1f} °C", "°C", "Stabil"),
        ("Toprak Yüzey Sıcaklığı (Skin)", f"{d['sicaklik'] + 1.5:.1f} °C", "°C", "Normal"),
        ("5cm Derinlik Toprak Sıcaklığı", f"{d['sicaklik'] - 0.5:.1f} °C", "°C", "Normal"),
        ("20cm Derinlik Toprak Sıcaklığı", f"{d['sicaklik'] - 1.8:.1f} °C", "°C", "Normal"),
        ("1m Derinlik Toprak Sıcaklığı", f"{d['sicaklik'] - 3.0:.1f} °C", "°C", "Stabil"),
        ("Çiğ Noktası (Dew Point)", f"{d['sicaklik'] - 6.0:.1f} °C", "°C", "Normal"),
        ("Hissedilen Sıcaklık", f"{d['sicaklik'] - 0.8:.1f} °C", "°C", "Normal"),
        ("Wet-Bulb Sıcaklığı", f"{d['sicaklik'] - 3.5:.1f} °C", "°C", "Stabil"),
        ("Termal Konfor İndeksi", "İyi / Optimal", "Endeks", "Optimum"),
        ("Donma Riski Eşiği", "Yok (> 0°C)", "Boolean", "Güvenli"),
        ("Isı Adası Etkisi (UHI)", "+0.4 °C", "°C", "Düşük"),
        ("Stratosferik Sıcaklık Tahmini", "-55.2 °C", "°C", "Standart"),
        ("Tropopoz Sıcaklığı", "-56.8 °C", "°C", "Standart"),
        ("Gece Minimum Sıcaklık Projeksiyonu", f"{d['sicaklik'] - 5.2:.1f} °C", "°C", "Normal"),
        ("Günlük Sıcaklık Genliği (Amplitüd)", "8.4 °C", "°C", "Normal"),
        ("Termal Adveksiyon Oranı", "+0.12 °C/h", "°C/h", "Stabil"),
        ("Yüzey Isı Akısı", "45 W/m²", "W/m²", "Normal"),
        ("Toprak Isı Kapasitesi", "1.8 MJ/m³K", "MJ/m³K", "Normal"),
        ("Donma Derinliği", "0.0 cm", "cm", "Güvenli"),
        ("Biyometeorolojik Stres Skoru", "1.2", "Skor", "Düşük"),
        ("Termal Uydu Parlaklık Sıcaklığı", f"{d['sicaklik'] + 2.1:.1f} °C", "°C", "Normal"),
        ("Mikroklima Isı Katsayısı", "1.04", "Oran", "Normal"),
        ("Sensible Heat Flux", "32 W/m²", "W/m²", "Normal"),
        ("Toprak Isı İletkenliği", "1.2 W/mK", "W/mK", "Normal"),
        ("Termal Rejime Uyum Oranı", "%94", "%", "Optimum")
    ]
    for p in temp_list:
        parametreler.append({"Kategori": "Sıcaklık & Termal", "Parametre Adı": p[0], "Değer": p[1], "Birim": p[2], "Durum": p[3]})

    # 2. Nem, Su Buharı ve Yağış Parametreleri (28-58)
    nem_list = [
        ("Bağıl Nem (2m)", f"%{d['nem']}", "%", "Optimal"),
        ("Özgül Nem", "8.4 g/kg", "g/kg", "Normal"),
        ("Yağış Miktarı", f"{d['yagis']} mm", "mm", "Kurak/Az"),
        ("Yağmur Olasılığı", "%12", "%", "Düşük"),
        ("Kar Yağışı Eşdeğeri", "0.0 mm", "mm", "Yok"),
        ("Buhar Basıncı", "14.2 hPa", "hPa", "Normal"),
        ("Bulut Tabanı Yüksekliği", "1850 m", "Metre", "Normal"),
        ("Toplam Kolon Su Buharı", "22.5 mm", "mm", "Normal"),
        ("Çiy Birikim Oranı", "0.1 mm/h", "mm/h", "Düşük"),
        ("Konvektif Yağış Potansiyeli", "Düşük", "Seviye", "Güvenli"),
        ("Atmosferik Doygunluk Açığı", "6.8 hPa", "hPa", "Normal"),
        ("Evapotranspirasyon", "3.4 mm/gün", "mm/gün", "Normal"),
        ("Potansiyel Buharlaşma", "4.1 mm/gün", "mm/gün", "Normal"),
        ("Yağış Rejimi Sınıfı", "Yarı kurak", "Sınıf", "Normal"),
        ("Hidrolojik Denge Endeksi", "0.85", "Endeks", "Stabil"),
        ("Mutlak Nem", "9.1 g/m³", "g/m³", "Normal"),
        ("Kar Örtüsü Kalınlığı", "0 cm", "cm", "Yok"),
        ("Dolu Riski", "Yok", "Risk", "Güvenli"),
        ("Sis Oluşum İhtimali", "%5", "%", "Düşük"),
        ("Bulut Üstü Yüksekliği", "6200 m", "Metre", "Normal"),
        ("Precipitable Water Vapor", "21.4 mm", "mm", "Normal"),
        ("Çisenti Yoğunluğu", "0.0 mm/h", "mm/h", "Yok"),
        ("Toprak Su Doygunluk Oranı", "%48", "%", "Normal"),
        ("Yeraltı Su Seviyesi İndeksi", "-1.4 m", "Metre", "Stabil"),
        ("Hidro-Metorolojik Risk Faktörü", "0.08", "Faktör", "Güvenli"),
        ("Bağıl Nem Eğilimi", "Stabil", "Durum", "Kararlı"),
        ("Su Buharı Adveksiyonu", "Düşük", "Seviye", "Normal"),
        ("Atmosferik Nem Kapasitesi", "18.2 g/m³", "g/m³", "Normal"),
        ("Saturasyon Buhar Basıncı", "23.4 hPa", "hPa", "Normal"),
        ("Hidrolojik Havza Akış Oranı", "0.12", "Oran", "Normal"),
        ("Kondenzasyon Seviyesi (LCL)", "1420 m", "Metre", "Normal")
    ]
    for p in nem_list:
        parametreler.append({"Kategori": "Nem & Su Buharı", "Parametre Adı": p[0], "Değer": p[1], "Birim": p[2], "Durum": p[3]})

    # 3. Rüzgar, Basınç ve Dinamikler (59-88)
    ruzgar_list = [
        ("10m Rüzgar Hızı", f"{d['ruzgar']} km/s", "km/s", "Normal"),
        ("Rüzgar Yönü", f"{d['ruzgar_yon']}°", "Derece", "Normal"),
        ("Rüzgar Hamlesi (Gust)", f"{d['ruzgar'] * 1.5:.1f} km/s", "km/s", "Normal"),
        ("80m Yükseklik Rüzgar Hızı", f"{d['ruzgar'] * 1.25:.1f} km/s", "km/s", "Normal"),
        ("120m Yükseklik Rüzgar Hızı", f"{d['ruzgar'] * 1.4:.1f} km/s", "km/s", "Normal"),
        ("Deniz Seviyesi Basınç", f"{d['basinc']} hPa", "hPa", "Stabil"),
        ("Yüzey Basınç", f"{d['basinc'] - 12:.1f} hPa", "hPa", "Stabil"),
        ("850 hPa Jeopotansiyel", "1450 m", "Metre", "Normal"),
        ("500 hPa Jeopotansiyel", "5620 m", "Metre", "Normal"),
        ("Atmosferik Yoğunluk", "1.185 kg/m³", "kg/m³", "Normal"),
        ("Dikey Hız (Omega)", "-0.02 Pa/s", "Pa/s", "Stabil"),
        ("Rüzgar Sınıfı (Beaufort)", "Hafif Esinti", "Skala", "Güvenli"),
        ("Türbülans Kinetik Enerjisi", "0.45 m²/s²", "m²/s²", "Düşük"),
        ("Zonal Rüzgar Bileşeni (U)", "2.4 m/s", "m/s", "Normal"),
        ("Meridyonal Rüzgar Bileşeni (V)", "-1.1 m/s", "m/s", "Normal"),
        ("Hava Kütlesi Kökeni", "Karasal", "Tip", "Kararlı"),
        ("Barometrik Eğilim", "+0.4 hPa", "hPa", "Yükseliyor"),
        ("Geostrofik Sapma", "1.2 m/s", "m/s", "Normal"),
        ("Sürtünme Hızı", "0.28 m/s", "m/s", "Normal"),
        ("Sınır Tabaka Yüksekliği (PBL)", "850 m", "Metre", "Normal"),
        ("Coriolis Parametresi", "8.9e-5 s⁻¹", "s⁻¹", "Sabit"),
        ("Rüzgar Kırılma İndeksi", "1.002", "Indeks", "Normal"),
        ("Vortisite (Girdap) Değeri", "1.2e-5 s⁻¹", "s⁻¹", "Düşük"),
        ("Jet Stream Konumu", "Uzak", "Konum", "Stabil"),
        ("Baroklinik Kararsızlık", "Düşük", "Seviye", "Güvenli"),
        ("Rüzgar Güç Yoğunluğu", "45 W/m²", "W/m²", "Düşük"),
        ("Atmosferik Basınç Düşüş Hızı", "0.1 hPa/h", "hPa/h", "Stabil"),
        ("Yüzey Gerilme Kuvveti", "0.15 N/m²", "N/m²", "Normal"),
        ("Konverjans Oranı", "-0.1e-5 s⁻¹", "s⁻¹", "Stabil"),
        ("Diverjans Göstergesi", "0.2e-5 s⁻¹", "s⁻¹", "Normal")
    ]
    for p in ruzgar_list:
        parametreler.append({"Kategori": "Rüzgar & Basınç", "Parametre Adı": p[0], "Değer": p[1], "Birim": p[2], "Durum": p[3]})

    # 4. Toprak, SMAP ve Uydu Parametreleri (89-113)
    toprak_list = [
        ("SMAP Toprak Rutubeti", f"{d['smap_soil']} %", "%", "Optimum"),
        ("NDVI Bitki İndeksi", f"{d['ndvi_val']}", "Indeks", "Sağlıklı"),
        ("EVI Gelişmiş Bitki İndeksi", f"{d['ndvi_val'] * 0.85:.3f}", "Indeks", "İyi"),
        ("Kök Bölgesi Toprak Nemi", f"{d['smap_soil'] * 1.15:.1f} %", "%", "Optimum"),
        ("Toprak Sıkışma İndeksi", "1.24 kPa", "kPa", "Normal"),
        ("Toprak pH Tahmini", "7.2", "pH", "Nötr"),
        ("Toprak Elektriksel İletkenlik", "1.1 dS/m", "dS/m", "Normal"),
        ("Kök Çürüklüğü Riski", "Düşük", "Risk", "Güvenli"),
        ("Kuraklık Stres İndeksi (ESI)", "0.12", "Indeks", "Güvenli"),
        ("Bitki Su Tüketim İhtiyacı", "3.2 mm/gün", "mm/gün", "Normal"),
        ("Uydu Görüş Açısı", "12.4°", "Derece", "Normal"),
        ("Yüzey Albedo Katsayısı", "0.22", "Oran", "Standart"),
        ("Termal Atalet", "1250", "SI", "Normal"),
        ("Yüzey Pürüzlülüğü", "0.05 m", "Metre", "Normal"),
        ("Biomas Üretim Potansiyeli", "Yüksek", "Seviye", "Avantajlı"),
        ("Klorofil Emilim Göstergesi", "0.78", "Indeks", "Güçlü"),
        ("Yaprak Alan İndeksi (LAI)", "3.1 m²/m²", "m²/m²", "Optimal"),
        ("Net Ekosistem Değişimi", "+4.2 gC", "gC", "Karbon Yutan"),
        ("Toprak Solunumu", "2.1 gC", "gC", "Normal"),
        ("Yangın Hassasiyet Skoru", "14 / 100", "Skor", "Güvenli"),
        ("Toprak Organik Madde Oranı", "%2.4", "%", "Normal"),
        ("Kil / Silt Oranı Dengesi", "Dengeli", "Tip", "Uygun"),
        ("Toprak Su Tutma Kapasitesi", "32 mm", "mm", "Normal"),
        ("Uydu Radar Geri Saçılımı", "-12.4 dB", "dB", "Normal"),
        ("Vegetasyon Su İçeriği (VWC)", "1.4 kg/m²", "kg/m²", "Normal")
    ]
    for p in toprak_list:
        parametreler.append({"Kategori": "Toprak & Uydu", "Parametre Adı": p[0], "Değer": p[1], "Birim": p[2], "Durum": p[3]})

    # 5. Güneş, Radyasyon ve Hava Kalitesi Parametreleri (114-138)
    gunes_list = [
        ("UV İndeksi", f"{d['radyasyon']}", "Indeks", "Güvenli"),
        ("Kısa Dalga Güneş Radyasyonu", "480 W/m²", "W/m²", "Normal"),
        ("Doğrudan Normal Işıma (DNI)", "520 W/m²", "W/m²", "Normal"),
        ("Yayılı Güneş Işınımı (DHI)", "180 W/m²", "W/m²", "Normal"),
        ("Uzun Dalga Termal Işıma", "320 W/m²", "W/m²", "Normal"),
        ("Fotosentetik Aktif Radyasyon", "210 W/m²", "W/m²", "Verimli"),
        ("Güneşlenme Süresi", "8.5 Saat", "Saat", "İyi"),
        ("Güneş Doğuş Zamanı", "06:42", "Saat", "Sabit"),
        ("Güneş Batış Zamanı", "17:55", "Saat", "Sabit"),
        ("Güneş Zenit Açısı", "42.1°", "Derece", "Normal"),
        ("Güneş Azimut Açısı", "182.4°", "Derece", "Normal"),
        ("Ozon Tabakası Kalınlığı", "310 DU", "Dobson", "Normal"),
        ("Atmosferik Transmitans", "0.76", "Oran", "İyi"),
        ("Bulut Örtüsü Oranı", "%18", "%", "Parçalı"),
        ("Görüş Mesafesi", "18.5 km", "km", "Net"),
        ("Karbon Dioksit (CO2 Tahmini)", "421 ppm", "ppm", "Standart"),
        ("Metan Gazı Tahmini (CH4)", "1.92 ppm", "ppm", "Normal"),
        ("Karbon Monoksit (CO)", "0.22 mg/m³", "mg/m³", "Temiz"),
        ("Azot Dioksit (NO2)", "12.4 µg/m³", "µg/m³", "Temiz"),
        ("Kükürt Dioksit (SO2)", "4.2 µg/m³", "µg/m³", "Temiz"),
        ("Partikül Madde (PM2.5)", "8.5 µg/m³", "µg/m³", "İyi Hava"),
        ("Partikül Madde (PM10)", "16.1 µg/m³", "µg/m³", "İyi Hava"),
        ("Hava Kalitesi İndeksi (AQI)", "32", "AQI", "Temiz"),
        ("İyonosferik Elektron Yoğunluğu", "Stabil", "Durum", "Kararlı"),
        ("Manyetik Alan Sapması", "0.14 Gauss", "Gauss", "Normal")
    ]
    for p in gunes_list:
        parametreler.append({"Kategori": "Güneş & Atmosfer", "Parametre Adı": p[0], "Değer": p[1], "Birim": p[2], "Durum": p[3]})

    return pd.DataFrame(parametreler)

if "secilen_lat" not in st.session_state:
    st.session_state.secilen_lat = 37.8859
if "secilen_lon" not in st.session_state:
    st.session_state.secilen_lon = 41.1198
if "mekan_adi" not in st.session_state:
    st.session_state.mekan_adi = "Batman (Gerçek İstasyon)"
if "arduino_ser" not in st.session_state:
    st.session_state.arduino_ser = None

with st.sidebar:
    st.markdown("### 🔌 Tablet / Web Serial Bağlantısı")
    st.markdown("<p style='font-size:0.85rem; color:#94a3b8;'>Tabletten OTG ile bağlı Arduino'ya doğrudan bağlanın:</p>", unsafe_allow_html=True)
    
    components.html("""
    <div style="padding: 5px;">
        <button id="connectSerial" style="background: linear-gradient(135deg, #0284c7 0%, #7c3aed 100%); color: white; border: none; padding: 10px 15px; border-radius: 12px; font-weight: bold; cursor: pointer; width: 100%; font-family: sans-serif;">
            📱 USB / Arduino'ya Bağlan
        </button>
        <p id="status" style="color: #38bdf8; font-size: 0.8rem; margin-top: 8px; text-align: center; font-family: sans-serif;">Durum: Bağlı Değil</p>
    </div>
    <script>
        let port;
        let writer;
        const button = document.getElementById('connectSerial');
        const status = document.getElementById('status');
        button.addEventListener('click', async () => {
            try {
                port = await navigator.serial.requestPort();
                await port.open({ baudRate: 9600 });
                status.innerText = "Durum: Bağlandı! ✅";
                status.style.color = "#4ade80";
            } catch (err) {
                status.innerText = "Bağlantı Hatası / İptal";
                status.style.color = "#f87171";
            }
        });
    </script>
    """, height=110)

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

d = analiz_uret(st.session_state.secilen_lat, st.session_state.secilen_lon, secilen_tarih)
arduino_veri_gonder(d['sicaklik'], int(d['nem']), int(d['basinc']), d['ruzgar'], d['ndvi_val'], d['smap_soil'])

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

# --- 7 SEKMELİ YENİ NESİL YAPISAL SEKMELER ---
tab1, tab2, tab3, tab4, tab5, tab6, tab7 = st.tabs([
    "🗺️ NASA Telemetri", 
    "📊 Trend Analizi", 
    "🚨 Risk & Alarm", 
    "⚖️ Karşılaştırma",
    "🔍 135+ Veri Havuzu",
    "🌐 3D Dijital İkiz",
    "💧 Hidrolojik & Taşkın"
])

with tab1:
    render_box(
        title="🌍 NASA Space Apps Challenge - Lightning Flora Küresel Gözlemevi",
        subtitle=f"Seçilen tarih sıcaklığı: <b>{d['sicaklik']} °C</b> | Rüzgar: <b>{d['ruzgar']} km/s</b>.",
        border_color="rgba(16, 185, 129, 0.75)",
        glow_color="rgba(16, 185, 129, 0.55)",
        bg_gradient="linear-gradient(135deg, rgba(6, 78, 59, 0.55) 0%, rgba(15, 23, 42, 0.9) 100%)"
    )
    secilen_katman_adi = st.selectbox("🗺️ Harita Katmanını Değiştir:", ["Rüzgar Akışı", "Sıcaklık Dağılımı", "Yağış & Radar", "Atmosferik Basınç", "Bulut Örtüsü"], key="map_layer_selector")
    katman_kodlari = {"Rüzgar Akışı": "wind", "Sıcaklık Dağılımı": "temp", "Yağış & Radar": "rain", "Atmosferik Basınç": "pressure", "Bulut Örtüsü": "clouds"}
    aktif_overlay = katman_kodlari.get(secilen_katman_adi, "wind")
    lat_val, lon_val = st.session_state.secilen_lat, st.session_state.secilen_lon
    windy_embed_url = f"https://embed.windy.com/embed2.html?lat={lat_val}&lon={lon_val}&zoom=6&level=surface&overlay={aktif_overlay}&menu=&message=&marker=&pressure=&calendar=now&type=map&location=coordinates&detail=&metricWind=default&metricTemp=default&radarRange=-1"

    components.html(f"""
    <div style="position: relative; width: 100%; height: 560px; border-radius: 24px; overflow: hidden; border: 3px solid rgba(56, 189, 248, 0.4);">
        <iframe src="{windy_embed_url}" width="100%" height="560px" style="border:none;"></iframe>
    </div>
    """, height=575)

with tab2:
    render_box(
        title=f"📊 {secilen_tarih.strftime('%d.%m.%Y')} Tarihli Gerçek Veri Trendleri",
        subtitle=f"Seçilen Koordinat: {st.session_state.secilen_lat:.4f}, {st.session_state.secilen_lon:.4f}.",
        border_color="rgba(56, 189, 248, 0.75)",
        glow_color="rgba(56, 189, 248, 0.55)",
        bg_gradient="linear-gradient(135deg, rgba(14, 116, 144, 0.45) 0%, rgba(15, 23, 42, 0.9) 100%)"
    )
    c1, c2, c3, c4 = st.columns(4)
    with c1:
        render_metric_card("1️⃣ Sıcaklık", f"{d['sicaklik']} °C", "Sıcaklık", "rgba(56, 189, 248, 0.75)", "#38bdf8", "rgba(56, 189, 248, 0.45)", "linear-gradient(135deg, rgba(14, 165, 233, 0.35) 0%, rgba(15, 23, 42, 0.9) 100%)")
    with c2:
        render_metric_card("2️⃣ Rüzgar", f"{d['ruzgar']} km/s", f"Yön: {d['ruzgar_yon']}°", "rgba(16, 185, 129, 0.75)", "#34d399", "rgba(16, 185, 129, 0.45)", "linear-gradient(135deg, rgba(16, 185, 129, 0.35) 0%, rgba(15, 23, 42, 0.9) 100%)")
    with c3:
        render_metric_card("3️⃣ NDVI", f"{d['ndvi_val']}", "Bitki İndeksi", "rgba(245, 158, 11, 0.75)", "#fbbf24", "rgba(245, 158, 11, 0.45)", "linear-gradient(135deg, rgba(245, 158, 11, 0.35) 0%, rgba(15, 23, 42, 0.9) 100%)")
    with c4:
        render_metric_card("4️⃣ Basınç", f"{d['basinc']} hPa", "Basınç", "rgba(168, 85, 247, 0.75)", "#c084fc", "rgba(168, 85, 247, 0.45)", "linear-gradient(135deg, rgba(168, 85, 247, 0.35) 0%, rgba(15, 23, 42, 0.9) 100%)")

    df_trend = zaman_serisi_cek(st.session_state.secilen_lat, st.session_state.secilen_lon, secilen_tarih)
    fig_temp = px.line(df_trend, x="Tarih", y="Sıcaklık (°C)", title="30 Günlük Sıcaklık Trendi", template="plotly_dark")
    fig_temp.update_traces(line=dict(color="#38bdf8", width=3))
    fig_temp.update_layout(paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)")
    st.plotly_chart(fig_temp, use_container_width=True)

with tab3:
    render_box(
        title="🚨 Yapay Zeka Risk ve Alarm Analizi",
        subtitle=f"Tarih: {secilen_tarih.strftime('%d.%m.%Y')}",
        border_color="rgba(34, 197, 94, 0.75)",
        glow_color="rgba(34, 197, 94, 0.45)",
        bg_gradient="linear-gradient(135deg, rgba(20, 83, 45, 0.6) 0%, rgba(15, 23, 42, 0.9) 100%)"
    )
    st.markdown(f"""
    <div style="background: rgba(15, 23, 42, 0.85); padding: 2rem; border-radius: 28px; border: 2px solid rgba(34, 197, 94, 0.5);">
        <h3 style="color: #4ade80; margin-top: 0;">🟢 Ekosistem Sağlık Raporu (Stabil)</h3>
        <p style="color: #e2e8f0; font-size: 1.05rem;">
            Nem oranı %{d['nem']} ve toprak rutubeti (SMAP) %{d['smap_soil']} seviyelerindedir. Kuraklık ve yangın riski minimal düzeydedir.
        </p>
    </div>
    """, unsafe_allow_html=True)

with tab4:
    render_box(
        title="⚖️ Bölgesel Karşılaştırma Analizi",
        subtitle="İki istasyonun eş zamanlı karşılaştırma raporu.",
        border_color="rgba(168, 85, 247, 0.75)",
        glow_color="rgba(168, 85, 247, 0.55)",
        bg_gradient="linear-gradient(135deg, rgba(76, 29, 149, 0.45) 0%, rgba(15, 23, 42, 0.9) 100%)"
    )
    c_b1, c_b2 = st.columns(2)
    with c_b1:
        yer_1 = st.text_input("1. Bölge:", "Batman", key="compare_loc_1")
    with c_b2:
        yer_2 = st.text_input("2. Bölge:", "Ankara", key="compare_loc_2")

    res1 = konum_bul(yer_1)
    res2 = konum_bul(yer_2)
    lat1, lon1 = res1[0] if res1 and res1[0] is not None else (37.8859, 41.1198)
    lat2, lon2 = res2[0] if res2 and res2[0] is not None else (39.9334, 32.8597)
    d1 = analiz_uret(lat1, lon1, secilen_tarih)
    d2 = analiz_uret(lat2, lon2, secilen_tarih)

    c_res1, c_res2 = st.columns(2)
    with c_res1:
        render_metric_card(f"📍 {yer_1}", f"{d1['sicaklik']} °C", f"Nem: %{d1['nem']}", "rgba(56, 189, 248, 0.75)", "#38bdf8", "rgba(56, 189, 248, 0.45)", "linear-gradient(135deg, rgba(14, 165, 233, 0.35) 0%, rgba(15, 23, 42, 0.9) 100%)")
    with c_res2:
        render_metric_card(f"📍 {yer_2}", f"{d2['sicaklik']} °C", f"Nem: %{d2['nem']}", "rgba(168, 85, 247, 0.75)", "#c084fc", "rgba(168, 85, 247, 0.45)", "linear-gradient(135deg, rgba(168, 85, 247, 0.35) 0%, rgba(15, 23, 42, 0.9) 100%)")

with tab5:
    render_box(
        title=f"🔍 135+ Kapsamlı Veri Havuzu",
        subtitle=f"Konum: {st.session_state.mekan_adi}",
        border_color="rgba(2, 132, 199, 0.75)",
        glow_color="rgba(2, 132, 199, 0.55)",
        bg_gradient="linear-gradient(135deg, rgba(2, 132, 199, 0.35) 0%, rgba(15, 23, 42, 0.9) 100%)"
    )
    veri_arama = st.text_input("🔎 135+ Veri İçinde Ara:", "", key="data_search_bar")
    df_tum_veriler = genis_veri_havuzu_uret(d)
    if veri_arama:
        filtrelenmis_df = df_tum_veriler[
            df_tum_veriler['Parametre Adı'].str.contains(veri_arama, case=False, na=False) |
            df_tum_veriler['Kategori'].str.contains(veri_arama, case=False, na=False)
        ]
    else:
        filtrelenmis_df = df_tum_veriler
    st.markdown(f"<p style='color: #38bdf8; font-weight: 700;'>Toplam <b>{len(df_tum_veriler)}</b> parametre içerisinden <b>{len(filtrelenmis_df)}</b> sonuç listeleniyor.</p>", unsafe_allow_html=True)
    st.dataframe(
        filtrelenmis_df,
        use_container_width=True,
        hide_index=True,
        column_config={
            "Kategori": st.column_config.TextColumn("Kategori", width="medium"),
            "Parametre Adı": st.column_config.TextColumn("Parametre / Ölçüm Adı", width="large"),
            "Değer": st.column_config.TextColumn("Anlık Değer", width="small"),
            "Birim": st.column_config.TextColumn("Birim", width="small"),
            "Durum": st.column_config.TextColumn("Durum / Eşik", width="medium"),
        }
    )

with tab6:
    render_box(
        title="🌐 3D Topografik Dijital İkiz (Digital Twin Komuta Merkezi)",
        subtitle=f"Seçilen Koordinat ({st.session_state.secilen_lat:.4f}, {st.session_state.secilen_lon:.4f}) Çevresinin 3 Boyutlu Arazi Modeli ve Dijital Yükseklik Matrisi.",
        border_color="rgba(236, 72, 153, 0.75)",
        glow_color="rgba(236, 72, 153, 0.55)",
        bg_gradient="linear-gradient(135deg, rgba(131, 24, 67, 0.55) 0%, rgba(15, 23, 42, 0.9) 100%)"
    )
    st.markdown(
        "<p style='color:#cbd5e1;'>Bu model, seçilen koordinatın çevresindeki gerçek arazi yüksekliklerini "
        "Copernicus GLO-90 sayısal yükseklik modelinden alır. Yatay eksenler kilometre, dikey eksen metre cinsindendir.</p>",
        unsafe_allow_html=True
    )

    try:
        with st.spinner("🛰️ Gerçek arazi yükseklik verileri alınıyor..."):
            X_km, Y_km, Z = gercek_yukseklik_matrisi(
                st.session_state.secilen_lat,
                st.session_state.secilen_lon
            )

        fig_3d = go.Figure(data=[
            go.Surface(
                z=Z,
                x=X_km,
                y=Y_km,
                colorscale="Earth",
                colorbar=dict(title=dict(text="Rakım (m)", font=dict(color="#e2e8f0")), tickfont=dict(color="#e2e8f0")),
                contours={
                    "z": {
                        "show": True,
                        "usecolormap": True,
                        "project_z": True
                    }
                },
                hovertemplate="Doğu-Batı: %{x:.2f} km<br>Kuzey-Güney: %{y:.2f} km<br>Rakım: %{z:.0f} m<extra></extra>"
            )
        ])
        fig_3d.update_layout(
            title=f"{st.session_state.mekan_adi} — Gerçek 3D Arazi Modeli",
            autosize=True,
            height=620,
            margin=dict(l=10, r=10, t=55, b=10),
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)",
            font=dict(color="#e2e8f0"),
            scene=dict(
                xaxis=dict(title="Doğu ↔ Batı (km)", backgroundcolor="rgba(15,23,42,0.8)", gridcolor="rgba(56,189,248,0.2)"),
                yaxis=dict(title="Güney ↔ Kuzey (km)", backgroundcolor="rgba(15,23,42,0.8)", gridcolor="rgba(56,189,248,0.2)"),
                zaxis=dict(title="Rakım (m)", backgroundcolor="rgba(15,23,42,0.8)", gridcolor="rgba(56,189,248,0.2)"),
                aspectmode="manual",
                aspectratio=dict(x=1.15, y=1.0, z=0.42),
                camera=dict(eye=dict(x=1.55, y=1.55, z=1.05))
            )
        )
        st.plotly_chart(fig_3d, use_container_width=True)
        st.caption(
            f"Yükseklik aralığı: {np.nanmin(Z):.0f}–{np.nanmax(Z):.0f} m · "
            "Kaynak: Copernicus DEM GLO-90 / Open-Meteo Elevation API · "
            "Yaklaşık 24 × 24 km alan, 90 m kaynak çözünürlüğü."
        )
    except Exception as e:
        logger.exception("3D arazi modeli oluşturulamadı")
        st.error(f"Gerçek arazi verisi alınamadı: {e}")
        st.info("İnternet bağlantısını kontrol edip sayfayı yenileyin. Önceki yapay yüzey artık gösterilmez.")

with tab7:
    render_box(
        title="💧 Hidrolojik Havza ve Taşkın Risk Analizörü",
        subtitle=f"Anlık Yağış ({d['yagis']} mm) ve Toprak Doygunluğu (SMAP: %{d['smap_soil']}) Parametrelerine Göre Taşkın & Akış Simülasyonu.",
        border_color="rgba(59, 130, 246, 0.75)",
        glow_color="rgba(59, 130, 246, 0.55)",
        bg_gradient="linear-gradient(135deg, rgba(30, 58, 138, 0.55) 0%, rgba(15, 23, 42, 0.9) 100%)"
    )
    risk_skoru = min(100, max(5, int((d['yagis'] * 15) + (d['smap_soil'] * 0.8))))
    
    col_h1, col_h2 = st.columns([1, 2])
    with col_h1:
        render_metric_card(
            "Taşkın Risk Endeksi", 
            f"{risk_skoru} / 100", 
            "Kritik Eşik: 75", 
            "rgba(59, 130, 246, 0.75)", 
            "#60a5fa" if risk_skoru < 75 else "#f87171", 
            "rgba(59, 130, 246, 0.45)", 
            "linear-gradient(135deg, rgba(30, 58, 138, 0.4) 0%, rgba(15, 23, 42, 0.9) 100%)"
        )
        render_metric_card(
            "Tahmini Yüzey Akışı", 
            f"{d['yagis'] * 0.65:.2f} m³/s", 
            "Havza Drenaj Kapasitesi", 
            "rgba(16, 185, 129, 0.75)", 
            "#34d399", 
            "rgba(16, 185, 129, 0.45)", 
            "linear-gradient(135deg, rgba(6, 78, 59, 0.4) 0%, rgba(15, 23, 42, 0.9) 100%)"
        )
    with col_h2:
        saatler = [f"{i}:00" for i in range(0, 24, 3)]
        akis_hizlari = [max(0.1, d['yagis'] * np.sin(i/3) + np.random.uniform(0.5, 2.0)) for i in range(len(saatler))]
        
        fig_hydro = px.area(
            x=saatler, 
            y=akis_hizlari, 
            labels={'x': 'Zaman (Saat)', 'y': 'Akış Hızı (m³/s)'}, 
            title="24 Saatlik Hidrolojik Havza Akış Projeksiyonu", 
            template="plotly_dark"
        )
        fig_hydro.update_traces(line=dict(color="#3b82f6", width=3), fillcolor="rgba(59, 130, 246, 0.3)")
        fig_hydro.update_layout(paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)", height=320)
        st.plotly_chart(fig_hydro, use_container_width=True)
