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
import json

# --- SİSTEM LOGLAMA ---
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("LightningFloraNASAPro")

try:
    from streamlit_geolocation import streamlit_geolocation
except ImportError:
    streamlit_geolocation = None

# Streamlit Sayfa Yapılandırması
st.set_page_config(
    page_title="Lightning Flora - NASA Space Apps Observatory Pro",
    page_icon="🛰️",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# --- COĞRAFİ KONUM ÇÖZÜCÜ (GEOCODING API) ---
@st.cache_data(ttl=3600, show_spinner=False)
def konum_bul(isim):
    if not isim or not isinstance(isim, str) or not isim.strip():
        return None, None
    clean_name = isim.strip()
    normalized = clean_name.casefold().replace("ı", "i").strip()
    if normalized in ("batman", "batman turkey", "batman turkiye", "batman türkiye"):
        return (37.8859, 41.1198), "Batman, Türkiye"
    url = "https://geocoding-api.open-meteo.com/v1/search"
    params = {"name": clean_name, "count": 10, "language": "tr", "format": "json", "countryCode": "TR"}
    try:
        response = requests.get(url, params=params, timeout=5)
        if response.status_code == 200:
            results = response.json().get("results", [])
            if results:
                r = next((x for x in results if x.get("country_code") == "TR"), results[0])
                return (float(r.get("latitude")), float(r.get("longitude"))), f"{r.get('name')}, {r.get('country', 'Türkiye')}"
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

# --- YÜKSEK ÇÖZÜNÜRLÜKLÜ 3D ARAZİ MODELİ ---
@st.cache_data(ttl=86400, show_spinner=False)
def gercek_yukseklik_matrisi(
    merkez_lat,
    merkez_lon,
    grid_boyutu=15,
    yari_cap_km=15
):
    """Yardımcı 3D yükseklik katmanı; kaynak Open-Meteo, NASA verisi değildir."""
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
    koordinat_sayisi = len(lat_duz)
    yukseklikler = []
    url = "https://api.open-meteo.com/v1/elevation"

    # Servise tek seferde aşırı uzun koordinat listesi göndermemek için
    # noktaları 100'lük paketler halinde al.
    for baslangic in range(0, koordinat_sayisi, 100):
        bitis = min(baslangic + 100, koordinat_sayisi)
        params = {
            "latitude": ",".join(f"{v:.6f}" for v in lat_duz[baslangic:bitis]),
            "longitude": ",".join(f"{v:.6f}" for v in lon_duz[baslangic:bitis])
        }
        yanit = None

        for deneme in range(3):
            try:
                yanit = requests.get(url, params=params, timeout=30)
                if yanit.status_code == 429:
                    bekleme = yanit.headers.get("Retry-After")
                    time.sleep(float(bekleme) if bekleme and bekleme.isdigit() else 5 * (deneme + 1))
                    continue
                yanit.raise_for_status()
                break
            except requests.RequestException:
                if deneme == 2:
                    raise
                time.sleep(3 * (deneme + 1))

        if yanit is None or yanit.status_code == 429:
            raise RuntimeError(
                "Yükseklik servisi istek sınırına ulaştı. "
                "Lütfen biraz sonra yeniden deneyin."
            )

        paket = yanit.json().get("elevation", [])
        beklenen = bitis - baslangic
        if len(paket) != beklenen:
            raise ValueError(
                f"Eksik arazi verisi: {len(paket)} / {beklenen} nokta."
            )
        yukseklikler.extend(paket)

    if len(yukseklikler) != koordinat_sayisi:
        raise ValueError("Arazi yükseklik matrisi tamamlanamadı.")

    Z = np.asarray(yukseklikler, dtype=float).reshape(
        grid_boyutu, grid_boyutu
    )
    if not np.isfinite(Z).all():
        raise ValueError("Arazi verisinde geçersiz yükseklik değeri var.")

    x_km = (lon_dizi - merkez_lon) * 111.32 * cos_lat
    y_km = (lat_dizi - merkez_lat) * 111.32
    X_km, Y_km = np.meshgrid(x_km, y_km)

    return X_km, Y_km, Z



# --- NASA POWER VERI MOTORU ---
@st.cache_data(ttl=43200, show_spinner=False)
def gercek_veri_cek(lat, lon, secilen_tarih):
    """Yalnızca seçilen günün NASA POWER gözlemini döndürür; başka güne geri düşmez."""
    tarih_kodu = secilen_tarih.strftime("%Y%m%d")
    ortak = {
        "latitude": round(float(lat), 4), "longitude": round(float(lon), 4),
        "start": tarih_kodu, "end": tarih_kodu, "format": "JSON",
        "time-standard": "LST"
    }

    def request_parameters(community, parameters):
        params = dict(ortak)
        params.update({"community": community, "parameters": parameters})
        response = requests.get(
            "https://power.larc.nasa.gov/api/temporal/daily/point",
            params=params, timeout=25
        )
        response.raise_for_status()
        return response.json().get("properties", {}).get("parameter", {})

    def value(data, key):
        raw = data.get(key, {}).get(tarih_kodu)
        if raw is None or raw in (-999, -999.0):
            return None
        return float(raw)

    try:
        ag = request_parameters(
            "AG",
            "T2M,T2M_MAX,T2M_MIN,RH2M,PRECTOTCORR,WS10M,WD10M,PS,ALLSKY_SFC_SW_DWN"
        )
        hy = request_parameters("HY", "GWETTOP,GWETROOT,GWETPROF")
    except Exception as exc:
        logger.exception("NASA POWER veri isteği başarısız")
        raise RuntimeError(f"NASA POWER servisine erişilemedi: {exc}")

    temp = value(ag, "T2M")
    if temp is None:
        raise RuntimeError(
            f"NASA POWER {secilen_tarih:%d.%m.%Y} tarihi için bu koordinatta sıcaklık verisi yayımlamamış. "
            "Başka bir tarihe ait değer gösterilmedi."
        )

    pressure = value(ag, "PS")
    wet = value(hy, "GWETTOP")
    return {
        "sicaklik": temp, "sicaklik_max": value(ag, "T2M_MAX"),
        "sicaklik_min": value(ag, "T2M_MIN"), "nem": value(ag, "RH2M"),
        "yagis": value(ag, "PRECTOTCORR"), "ruzgar": value(ag, "WS10M"),
        "ruzgar_yon": value(ag, "WD10M"),
        "basinc": None if pressure is None else pressure * 10.0,
        "radyasyon": value(ag, "ALLSKY_SFC_SW_DWN"),
        "toprak_ust": wet, "toprak_kok": value(hy, "GWETROOT"),
        "toprak_profil": value(hy, "GWETPROF"),
        "veri_tarihi": secilen_tarih, "gun_farki": 0
    }


@st.cache_data(ttl=21600, show_spinner=False)
def zaman_serisi_cek(lat, lon, merkez_tarih):
    """NASA POWER'dan 30 günlük gerçek günlük sıcaklık, yağış ve rüzgâr serisi."""
    bitis = min(merkez_tarih, datetime.now().date() - timedelta(days=1))
    baslangic = bitis - timedelta(days=29)
    params = {
        "latitude": round(float(lat), 4), "longitude": round(float(lon), 4),
        "start": baslangic.strftime("%Y%m%d"), "end": bitis.strftime("%Y%m%d"),
        "community": "AG", "parameters": "T2M,PRECTOTCORR,WS10M",
        "format": "JSON", "time-standard": "LST"
    }
    res = requests.get("https://power.larc.nasa.gov/api/temporal/daily/point", params=params, timeout=30)
    res.raise_for_status()
    p = res.json().get("properties", {}).get("parameter", {})
    temp, rain, wind = p.get("T2M", {}), p.get("PRECTOTCORR", {}), p.get("WS10M", {})
    rows = []
    for day in sorted(temp.keys()):
        vals = (temp.get(day), rain.get(day), wind.get(day))
        if any(v is None or v == -999 for v in vals):
            continue
        rows.append({
            "Tarih": pd.to_datetime(day, format="%Y%m%d"),
            "Sıcaklık (°C)": float(vals[0]),
            "Yağış (mm/gün)": float(vals[1]),
            "Rüzgar (m/s)": float(vals[2])
        })
    if not rows:
        raise RuntimeError("NASA POWER bu tarih aralığı için zaman serisi döndürmedi.")
    return pd.DataFrame(rows)


def analiz_uret(lat, lon, secilen_tarih):
    nasa = gercek_veri_cek(lat, lon, secilen_tarih)
    wet = nasa["toprak_ust"]
    wet_percent = None if wet is None else max(0.0, min(100.0, wet * 100.0))
    return {
        "sicaklik": nasa["sicaklik"], "sicaklik_max": nasa["sicaklik_max"],
        "sicaklik_min": nasa["sicaklik_min"], "nem": nasa["nem"],
        "yagis": nasa["yagis"], "ruzgar": nasa["ruzgar"],
        "ruzgar_yon": nasa["ruzgar_yon"], "basinc": nasa["basinc"],
        "radyasyon": nasa["radyasyon"],
        "smap_soil": None if wet_percent is None else round(wet_percent, 1),
        "toprak_kok": nasa["toprak_kok"], "toprak_profil": nasa["toprak_profil"],
        "ndvi_val": None, "ndvi_is_proxy": False,
        "veri_tarihi": nasa["veri_tarihi"], "gun_farki": 0,
        "kaynak": "NASA POWER"
    }


@st.cache_data(ttl=86400, show_spinner=False)
def nasa_gibs_harita_katalogu():
    """NASA GIBS WMS kataloğundan gerçek görüntü katmanlarını alır."""
    url = "https://gibs.earthdata.nasa.gov/wms/epsg3857/best/wms.cgi"
    response = requests.get(url, params={"SERVICE": "WMS", "REQUEST": "GetCapabilities", "VERSION": "1.3.0"}, timeout=30)
    response.raise_for_status()
    import xml.etree.ElementTree as ET
    root = ET.fromstring(response.content)
    katmanlar = []
    disla = ("no data", "mask", "graticule", "coastline", "border", "place label", "orbit")
    for node in root.iter():
        if node.tag.split("}")[-1] != "Layer":
            continue
        name = title = None
        for child in list(node):
            tag = child.tag.split("}")[-1]
            if tag == "Name":
                name = child.text
            elif tag == "Title":
                title = child.text
        if name and title and not any(x in (name + " " + title).casefold() for x in disla):
            katmanlar.append({"name": name, "title": title})
    # Keep a deterministic, broad Earth-observation catalogue, not arbitrary generated layers.
    unique = {item["name"]: item for item in katmanlar}
    result = sorted(unique.values(), key=lambda x: x["title"].casefold())
    if len(result) < 51:
        raise RuntimeError(f"NASA GIBS kataloğundan yalnızca {len(result)} uygun katman alındı.")
    return result[:51]


# --- NASA POWER GERCEK VERI KATALOGU ---
def genis_veri_havuzu_uret(d):
    entries = [
        ("Atmosfer", "2 metre hava sıcaklığı", d["sicaklik"], "°C", "NASA POWER / T2M"),
        ("Atmosfer", "Günlük maksimum sıcaklık", d["sicaklik_max"], "°C", "NASA POWER / T2M_MAX"),
        ("Atmosfer", "Günlük minimum sıcaklık", d["sicaklik_min"], "°C", "NASA POWER / T2M_MIN"),
        ("Atmosfer", "2 metre bağıl nem", d["nem"], "%", "NASA POWER / RH2M"),
        ("Yağış", "Düzeltilmiş toplam yağış", d["yagis"], "mm/gün", "NASA POWER / PRECTOTCORR"),
        ("Rüzgâr", "10 metre rüzgâr hızı", d["ruzgar"], "m/s", "NASA POWER / WS10M"),
        ("Rüzgâr", "10 metre rüzgâr yönü", d["ruzgar_yon"], "derece", "NASA POWER / WD10M"),
        ("Basınç", "Yüzey atmosfer basıncı", d["basinc"], "hPa", "NASA POWER / PS"),
        ("Güneş", "Günlük kısa dalga güneş radyasyonu", d["radyasyon"], "kWh/m²/gün", "NASA POWER / ALLSKY_SFC_SW_DWN"),
        ("Toprak", "Üst katman toprak ıslaklığı", d["smap_soil"], "%", "NASA POWER HY / GWETTOP"),
        ("Toprak", "Kök bölgesi toprak ıslaklığı", d["toprak_kok"], "kesir", "NASA POWER HY / GWETROOT"),
        ("Toprak", "Toprak profil ıslaklığı", d["toprak_profil"], "kesir", "NASA POWER HY / GWETPROF")
    ]
    rows = []
    for category, name, value, unit, source in entries:
        if value is None:
            shown, status = "Veri yok", "NASA kaynağında mevcut değil"
        else:
            shown = f"{value:.2f}" if isinstance(value, (int, float, np.number)) else str(value)
            status = "NASA kaynaklı veri"
        rows.append({
            "Kategori": category, "Parametre Adı": name, "Değer": shown,
            "Birim": unit, "Kaynak / Parametre": source, "Durum": status
        })
    return pd.DataFrame(rows)


if "secilen_lat" not in st.session_state:
    st.session_state.secilen_lat = 37.8859
if "secilen_lon" not in st.session_state:
    st.session_state.secilen_lon = 41.1198
if "mekan_adi" not in st.session_state:
    st.session_state.mekan_adi = "Batman (Gerçek İstasyon)"

# Veriler tarih seçildikten sonra tek kez istenir; başlangıçta mükerrer API çağrısı yapılmaz.

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

try:
    d = analiz_uret(st.session_state.secilen_lat, st.session_state.secilen_lon, secilen_tarih)
    nasa_veri_hazir = True
except Exception as nasa_hata:
    d = None
    nasa_veri_hazir = False
    st.error(f"NASA verisi alınamadı: {nasa_hata}")


# --- ARDUINO UNO: MANUEL GÖNDERİM + OTOMATİK GÖNDERİM ---
# Web Serial tarayıcı üzerinden çalışır. Kullanıcı ilk bağlantıda COM5'i seçmelidir.
# json.dumps, satır sonu karakterinin JavaScript metnini bozmasını önler.
veri_paketi_arduino = (
    f"T:{-1 if d is None or d['sicaklik'] is None else d['sicaklik']:.1f},"
    f"H:{-1 if d is None or d['nem'] is None else d['nem']},"
    f"P:{-1 if d is None or d['basinc'] is None else d['basinc']},"
    f"W:{-1 if d is None or d['ruzgar'] is None else d['ruzgar']:.1f},"
    f"N:-1,S:{-1 if d is None or d['smap_soil'] is None else d['smap_soil']:.1f}\n"
)
js_veri_paketi = json.dumps(veri_paketi_arduino, ensure_ascii=False)

with st.sidebar:
    st.markdown("### 🔌 Arduino UNO — COM5")
    st.caption("İlk bağlantıda açılan pencereden COM5 portunu seç.")
    otomatik_gonder = st.checkbox(
        "Veriler değiştiğinde otomatik gönder",
        value=False,
        key="arduino_otomatik_gonder"
    )
    components.html(f"""
    <div style="padding:8px;font-family:Arial,sans-serif;color:#e2e8f0;">
      <button id="connectBtn" style="width:100%;padding:12px;border:0;border-radius:10px;background:#0369a1;color:white;font-weight:700;cursor:pointer;margin-bottom:8px;">
        🔌 Arduino'ya Bağlan (COM5)
      </button>
      <button id="sendBtn" style="width:100%;padding:12px;border:0;border-radius:10px;background:#6d28d9;color:white;font-weight:700;cursor:pointer;">
        📤 Verileri Şimdi Gönder
      </button>
      <div id="serialStatus" style="font-size:12px;margin-top:10px;text-align:center;color:#7dd3fc;">
        Bağlantı bekleniyor
      </div>
    </div>
    <script>
    (() => {{
      const packet = {js_veri_paketi};
      const autoEnabled = {str(bool(otomatik_gonder)).lower()};
      const connectBtn = document.getElementById('connectBtn');
      const sendBtn = document.getElementById('sendBtn');
      const status = document.getElementById('serialStatus');
      let port = null;

      function showStatus(message, color='#7dd3fc') {{
        status.textContent = message;
        status.style.color = color;
      }}

      async function openGrantedPort() {{
        if (!('serial' in navigator)) {{
          throw new Error('Web Serial desteklenmiyor. Güncel Chrome ve HTTPS gerekir.');
        }}
        if (port && port.writable) return port;
        const grantedPorts = await navigator.serial.getPorts();
        if (grantedPorts.length > 0) {{
          port = grantedPorts[0];
        }} else {{
          throw new Error("Önce Arduino'ya Bağlan düğmesine basıp COM5'i seç.");
        }}
        if (!port.writable) await port.open({{ baudRate: 9600 }});
        return port;
      }}

      async function sendPacket() {{
        const activePort = await openGrantedPort();
        const writer = activePort.writable.getWriter();
        try {{
          await writer.write(new TextEncoder().encode(packet));
        }} finally {{
          writer.releaseLock();
        }}
        showStatus('Veri gönderildi ✓', '#4ade80');
      }}

      connectBtn.addEventListener('click', async () => {{
        try {{
          if (!('serial' in navigator)) throw new Error('Bu tarayıcı Web Serial desteklemiyor.');
          // requestPort çağrısı kullanıcı tıklaması içinde yapılmalıdır.
          port = await navigator.serial.requestPort();
          if (!port.writable) await port.open({{ baudRate: 9600 }});
          showStatus('Arduino bağlandı. COM5 seçimini kontrol et.', '#4ade80');
          await sendPacket();
        }} catch (err) {{
          showStatus('Bağlantı hatası: ' + err.message, '#f87171');
        }}
      }});

      sendBtn.addEventListener('click', async () => {{
        try {{ await sendPacket(); }}
        catch (err) {{ showStatus('Gönderim hatası: ' + err.message, '#f87171'); }}
      }});

      // Streamlit yeniden çalıştığında izin verilmiş portu bulup yeni veriyi yollar.
      // Bu, otomatik gönderimin tarayıcıdaki izin ve iframe politikasına bağlı olduğu anlamına gelir.
      if (autoEnabled) {{
        openGrantedPort()
          .then(() => sendPacket())
          .catch(err => showStatus('Otomatik gönderim bekliyor: ' + err.message, '#fbbf24'));
      }}
    }})();
    </script>
    """, height=175)


zaman_aciklama = f"NASA POWER gözlem tarihi: {d['veri_tarihi'].strftime('%d.%m.%Y')}"

render_box(
    title=f"📍 Aktif Gözlem Noktası ve Zaman Modu: {zaman_aciklama}",
    subtitle=f"🎯 Konum: <b>{st.session_state.mekan_adi}</b><br>📌 Koordinat: <b>{st.session_state.secilen_lat:.4f}° N, {st.session_state.secilen_lon:.4f}° E</b> | Seçilen Tarih: <b>{secilen_tarih.strftime('%d.%m.%Y')}</b>",
    border_color="rgba(168, 85, 247, 0.75)",
    glow_color="rgba(168, 85, 247, 0.55)",
    bg_gradient="linear-gradient(135deg, rgba(49, 46, 129, 0.55) 0%, rgba(15, 23, 42, 0.9) 100%)"
)

# --- YALNIZCA SEÇİLEN SEKMENİN İÇERİĞİNİ ÇİZ: HIZ PERFORMANS İYİLEŞTİRMESİ ---
sekme_adlari = [
    "NASA Uydu Haritası", "NASA Trendleri", "NASA Gözlem Özeti",
    "Bölgesel Karşılaştırma", "NASA Veri Kataloğu", "NASA Kaynak Bilgisi",
    "NASA Hidroloji Verileri"
]
aktif_sekme = st.radio("Görünüm", sekme_adlari, horizontal=True, key="aktif_nasa_sekmesi")

if aktif_sekme == "NASA Uydu Haritası":
    render_box(
        title="NASA Earth Observation — 51 Uydu ve Bilimsel Harita Katmanı",
        subtitle="Tüm görüntü katmanları NASA GIBS servisinden gelir. Harita tabanı ve seçilen bilimsel katman NASA verisidir.",
        border_color="rgba(16, 185, 129, 0.75)",
        glow_color="rgba(16, 185, 129, 0.55)",
        bg_gradient="linear-gradient(135deg, rgba(6, 78, 59, 0.55) 0%, rgba(15, 23, 42, 0.9) 100%)"
    )
    try:
        nasa_layers = nasa_gibs_harita_katalogu()
        layer_titles = [x["title"] for x in nasa_layers]
        layer_names = [x["name"] for x in nasa_layers]
        selected_title = st.selectbox("51 NASA haritasından birini seç", layer_titles, index=0, key="nasa_51_layer")
        selected_layer = layer_names[layer_titles.index(selected_title)]
        map_date = st.date_input(
            "Uydu gözlem tarihi",
            value=datetime.now().date() - timedelta(days=3),
            max_value=datetime.now().date(),
            key="nasa_map_date"
        ).strftime("%Y-%m-%d")
        st.caption(f"Seçili NASA GIBS ürünü: {selected_title} · Katman kodu: {selected_layer}")
        map_html = f"""
        <div id="nasa-earth-map" style="height:590px;width:100%;border-radius:18px;overflow:hidden;border:1px solid rgba(56,189,248,.45);"></div>
        <link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css"/>
        <script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>
        <script>
          const map = L.map('nasa-earth-map').setView([{st.session_state.secilen_lat}, {st.session_state.secilen_lon}], 5);
          const nasa = L.tileLayer.wms('https://gibs.earthdata.nasa.gov/wms/epsg3857/best/wms.cgi', {{
            layers: {json.dumps(selected_layer)}, format: 'image/png', transparent: false,
            version: '1.1.1', time: '{map_date}', attribution: 'NASA GIBS / EOSDIS',
            tiled: true
          }}).addTo(map);
          L.marker([{st.session_state.secilen_lat}, {st.session_state.secilen_lon}])
            .addTo(map).bindPopup('Lightning Flora observation point');
          L.control.scale({{metric:true, imperial:false}}).addTo(map);
        </script>
        """
        components.html(map_html, height=605, scrolling=False)
    except Exception as map_error:
        st.error(f"NASA GIBS harita kataloğu yüklenemedi: {map_error}")


if aktif_sekme == "NASA Trendleri":
        render_box(
            title=f"📊 {secilen_tarih.strftime('%d.%m.%Y')} Tarihli Gerçek Veri Trendleri",
            subtitle=f"Seçilen Koordinat: {st.session_state.secilen_lat:.4f}, {st.session_state.secilen_lon:.4f}.",
            border_color="rgba(56, 189, 248, 0.75)",
            glow_color="rgba(56, 189, 248, 0.55)",
            bg_gradient="linear-gradient(135deg, rgba(14, 116, 144, 0.45) 0%, rgba(15, 23, 42, 0.9) 100%)"
        )
        c1, c2, c3, c4 = st.columns(4)
        with c1:
            render_metric_card("1️⃣ Sıcaklık", f"{d['sicaklik']:.1f} °C", "Sıcaklık", "rgba(56, 189, 248, 0.75)", "#38bdf8", "rgba(56, 189, 248, 0.45)", "linear-gradient(135deg, rgba(14, 165, 233, 0.35) 0%, rgba(15, 23, 42, 0.9) 100%)")
        with c2:
            render_metric_card("2️⃣ Rüzgar", "Veri yok" if d['ruzgar'] is None else f"{d['ruzgar']:.1f} m/s", "NASA POWER ölçümü" if d['ruzgar_yon'] is None else f"Yön: {d['ruzgar_yon']:.0f}°", "rgba(16, 185, 129, 0.75)", "#34d399", "rgba(16, 185, 129, 0.45)", "linear-gradient(135deg, rgba(16, 185, 129, 0.35) 0%, rgba(15, 23, 42, 0.9) 100%)")
        with c3:
            render_metric_card("3️⃣ NDVI", "Harita katmanı", "Sayısal MODIS NDVI entegrasyonu henüz yok", "rgba(245, 158, 11, 0.75)", "#fbbf24", "rgba(245, 158, 11, 0.45)", "linear-gradient(135deg, rgba(245, 158, 11, 0.35) 0%, rgba(15, 23, 42, 0.9) 100%)")
        with c4:
            render_metric_card("4️⃣ Basınç", "Veri yok" if d['basinc'] is None else f"{d['basinc']:.1f} hPa", "Basınç", "rgba(168, 85, 247, 0.75)", "#c084fc", "rgba(168, 85, 247, 0.45)", "linear-gradient(135deg, rgba(168, 85, 247, 0.35) 0%, rgba(15, 23, 42, 0.9) 100%)")
    
        df_trend = zaman_serisi_cek(st.session_state.secilen_lat, st.session_state.secilen_lon, secilen_tarih)
        fig_temp = px.line(df_trend, x="Tarih", y="Sıcaklık (°C)", title="30 Günlük Sıcaklık Trendi", template="plotly_dark")
        fig_temp.update_traces(line=dict(color="#38bdf8", width=3))
        fig_temp.update_layout(paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)")
        st.plotly_chart(fig_temp, use_container_width=True)
    
    if aktif_sekme == "NASA Gözlem Özeti":
    render_box(
        title="NASA POWER — Gözlem Özeti",
        subtitle=f"{st.session_state.mekan_adi} · {d['veri_tarihi']:%d.%m.%Y}",
        border_color="rgba(34, 197, 94, 0.75)",
        glow_color="rgba(34, 197, 94, 0.45)",
        bg_gradient="linear-gradient(135deg, rgba(20, 83, 45, 0.45) 0%, rgba(15, 23, 42, 0.9) 100%)"
    )
    summary = [
        {"NASA parametresi": "T2M", "Gözlem": "2 m hava sıcaklığı", "Değer": d["sicaklik"], "Birim": "°C"},
        {"NASA parametresi": "RH2M", "Gözlem": "2 m bağıl nem", "Değer": d["nem"], "Birim": "%"},
        {"NASA parametresi": "PRECTOTCORR", "Gözlem": "Günlük yağış", "Değer": d["yagis"], "Birim": "mm/gün"},
        {"NASA parametresi": "WS10M", "Gözlem": "10 m rüzgâr hızı", "Değer": d["ruzgar"], "Birim": "m/s"},
        {"NASA parametresi": "PS", "Gözlem": "Yüzey basıncı", "Değer": d["basinc"], "Birim": "hPa"}
    ]
    st.dataframe(pd.DataFrame(summary), use_container_width=True, hide_index=True)
    st.caption("Bu ekranda yapay zekâ tahmini, risk puanı veya simülasyon yoktur; yalnızca NASA POWER gözlemleri listelenir.")


if aktif_sekme == "Bölgesel Karşılaştırma":
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
            render_metric_card(f"📍 {yer_1}", f"{d1['sicaklik']:.1f} °C", "NASA nem verisi yok" if d1['nem'] is None else f"Nem: %{d1['nem']:.1f}", "rgba(56, 189, 248, 0.75)", "#38bdf8", "rgba(56, 189, 248, 0.45)", "linear-gradient(135deg, rgba(14, 165, 233, 0.35) 0%, rgba(15, 23, 42, 0.9) 100%)")
        with c_res2:
            render_metric_card(f"📍 {yer_2}", f"{d2['sicaklik']:.1f} °C", "NASA nem verisi yok" if d2['nem'] is None else f"Nem: %{d2['nem']:.1f}", "rgba(168, 85, 247, 0.75)", "#c084fc", "rgba(168, 85, 247, 0.45)", "linear-gradient(135deg, rgba(168, 85, 247, 0.35) 0%, rgba(15, 23, 42, 0.9) 100%)")
    
    if aktif_sekme == "NASA Veri Kataloğu":
        render_box(
            title="🔍 NASA POWER Gerçek Veri Kataloğu",
            subtitle=f"Konum: {st.session_state.mekan_adi}",
            border_color="rgba(2, 132, 199, 0.75)",        glow_color="rgba(2, 132, 199, 0.55)",
            bg_gradient="linear-gradient(135deg, rgba(2, 132, 199, 0.35) 0%, rgba(15, 23, 42, 0.9) 100%)"
        )
        veri_arama = st.text_input("🔎 NASA parametrelerinde ara:", "", key="data_search_bar")
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
                "Değer": st.column_config.TextColumn("NASA Değeri", width="small"),
                "Birim": st.column_config.TextColumn("Birim", width="small"),
                "Durum": st.column_config.TextColumn("Veri Durumu", width="medium"),
            }
        )
    
    if aktif_sekme == "NASA Kaynak Bilgisi":
    render_box(
        title="NASA Veri Kaynakları ve Ölçüm Şeffaflığı",
        subtitle="Uygulama yalnızca NASA tarafından yayımlanan çevresel ölçüm ve uydu ürünlerini kullanır.",
        border_color="rgba(236, 72, 153, 0.75)",
        glow_color="rgba(236, 72, 153, 0.55)",
        bg_gradient="linear-gradient(135deg, rgba(131, 24, 67, 0.45) 0%, rgba(15, 23, 42, 0.9) 100%)"
    )
    st.markdown("""
    - **NASA POWER Daily API:** atmosfer, meteoroloji ve güneş enerjisi parametreleri.
    - **NASA POWER Hydrology:** üst toprak, kök bölgesi ve profil ıslaklığı.
    - **NASA GIBS / EOSDIS:** uydu görüntüleri ve bilimsel harita katmanları.
    - **NDVI:** yalnızca NASA MODIS ürününden sayısal veri elde edildiğinde değer olarak gösterilir; harita görüntüsü sayısal nokta ölçümü gibi sunulmaz.
    
    NASA'nın ilgili koordinat ve tarih için yayımlamadığı hiçbir değer tahmin edilmez, doldurulmaz veya başka tarihten kopyalanmaz.
    """)


if aktif_sekme == "NASA Hidroloji Verileri":
    render_box(
        title="NASA POWER — Gerçek Hidroloji Gözlemleri",
        subtitle="Bu bölüm yalnızca NASA tarafından döndürülen ölçümleri gösterir. Taşkın simülasyonu veya uydurma risk skoru üretilmez.",
        border_color="rgba(59, 130, 246, 0.75)",
        glow_color="rgba(59, 130, 246, 0.55)",
        bg_gradient="linear-gradient(135deg, rgba(30, 58, 138, 0.45) 0%, rgba(15, 23, 42, 0.9) 100%)"
    )
    hidro_rows = [
        {"NASA Parametresi": "PRECTOTCORR", "Ölçüm": "Günlük düzeltilmiş yağış", "Değer": d["yagis"], "Birim": "mm/gün"},
        {"NASA Parametresi": "GWETTOP", "Ölçüm": "Üst toprak ıslaklığı", "Değer": d["smap_soil"], "Birim": "% (ıslaklık kesrinden)"},
        {"NASA Parametresi": "GWETROOT", "Ölçüm": "Kök bölgesi ıslaklığı", "Değer": d["toprak_kok"], "Birim": "kesir"},
        {"NASA Parametresi": "GWETPROF", "Ölçüm": "Toprak profili ıslaklığı", "Değer": d["toprak_profil"], "Birim": "kesir"}
    ]
    st.dataframe(pd.DataFrame(hidro_rows), use_container_width=True, hide_index=True)
    st.caption(f"Kaynak: NASA POWER · Gözlem tarihi: {d['veri_tarihi']:%d.%m.%Y} · Boş değerler NASA tarafından sağlanmamıştır.")

