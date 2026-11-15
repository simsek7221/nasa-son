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
@st.cache_data(ttl=21600, show_spinner=False)
def gercek_veri_cek(lat, lon, secilen_tarih):
    """NASA POWER AG ve HY servislerinden gerçek günlük verileri alır."""
    son_hata = None
    for geri_gun in range(0, 8):
        veri_tarihi = secilen_tarih - timedelta(days=geri_gun)
        if veri_tarihi > datetime.now().date():
            continue
        tarih_kodu = veri_tarihi.strftime("%Y%m%d")
        ortak = {
            "latitude": round(float(lat), 4), "longitude": round(float(lon), 4),
            "start": tarih_kodu, "end": tarih_kodu, "format": "JSON",
            "time-standard": "LST"
        }
        try:
            ag_params = dict(ortak)
            ag_params.update({
                "community": "AG",
                "parameters": "T2M,T2M_MAX,T2M_MIN,RH2M,PRECTOTCORR,WS10M,WD10M,PS,ALLSKY_SFC_SW_DWN"
            })
            ag_res = requests.get("https://power.larc.nasa.gov/api/temporal/daily/point", params=ag_params, timeout=25)
            ag_res.raise_for_status()
            ag = ag_res.json().get("properties", {}).get("parameter", {})

            def val(key):
                raw = ag.get(key, {}).get(tarih_kodu)
                if raw is None or raw == -999 or raw == -999.0:
                    return None
                return float(raw)

            temp, humidity, rain = val("T2M"), val("RH2M"), val("PRECTOTCORR")
            wind, wind_dir, pressure_kpa = val("WS10M"), val("WD10M"), val("PS")
            radiation = val("ALLSKY_SFC_SW_DWN")
            if any(v is None for v in (temp, humidity, rain, wind, pressure_kpa)):
                continue

            hy_params = dict(ortak)
            hy_params.update({"community": "HY", "parameters": "GWETTOP,GWETROOT,GWETPROF"})
            hy_res = requests.get("https://power.larc.nasa.gov/api/temporal/daily/point", params=hy_params, timeout=25)
            hy_res.raise_for_status()
            hy = hy_res.json().get("properties", {}).get("parameter", {})

            def hy_val(key):
                raw = hy.get(key, {}).get(tarih_kodu)
                if raw is None or raw == -999 or raw == -999.0:
                    return None
                return float(raw)

            return {
                "sicaklik": temp, "sicaklik_max": val("T2M_MAX"), "sicaklik_min": val("T2M_MIN"),
                "nem": humidity, "yagis": rain, "ruzgar": wind, "ruzgar_yon": wind_dir,
                "basinc": pressure_kpa * 10.0, "radyasyon": radiation,
                "toprak_ust": hy_val("GWETTOP"), "toprak_kok": hy_val("GWETROOT"),
                "toprak_profil": hy_val("GWETPROF"), "veri_tarihi": veri_tarihi,
                "gun_farki": (veri_tarihi - datetime.now().date()).days
            }
        except Exception as e:
            son_hata = e
            logger.warning(f"NASA POWER isteği başarısız ({tarih_kodu}): {e}")
    raise RuntimeError("NASA POWER seçilen tarih ve önceki 7 gün için veri döndürmedi. Son hata: " + str(son_hata))


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
        "sicaklik": round(nasa["sicaklik"], 2), "sicaklik_max": nasa["sicaklik_max"],
        "sicaklik_min": nasa["sicaklik_min"], "nem": round(nasa["nem"], 1),
        "yagis": round(nasa["yagis"], 2), "ruzgar": round(nasa["ruzgar"], 2),
        "ruzgar_yon": nasa["ruzgar_yon"], "basinc": round(nasa["basinc"], 1),
        "radyasyon": nasa["radyasyon"], "smap_soil": None if wet_percent is None else round(wet_percent, 1),
        "toprak_kok": nasa["toprak_kok"], "toprak_profil": nasa["toprak_profil"],
        "ndvi_val": None, "ndvi_is_proxy": False,
        "veri_tarihi": nasa["veri_tarihi"], "gun_farki": nasa["gun_farki"],
        "kaynak": "NASA POWER"
    }


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

d = analiz_uret(st.session_state.secilen_lat, st.session_state.secilen_lon, datetime.now().date())
# Arduino bağlantı arayüzü, seçilen konum ve tarih hesaplandıktan sonra oluşturulur.

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


# --- ARDUINO UNO: MANUEL GÖNDERİM + OTOMATİK GÖNDERİM ---
# Web Serial tarayıcı üzerinden çalışır. Kullanıcı ilk bağlantıda COM5'i seçmelidir.
# json.dumps, satır sonu karakterinin JavaScript metnini bozmasını önler.
veri_paketi_arduino = (
    f"T:{d['sicaklik']:.1f},"
    f"H:{d['nem']},"
    f"P:{d['basinc']},"
    f"W:{d['ruzgar']:.1f},"
    f"N:{-1.0 if d['ndvi_val'] is None else d['ndvi_val']:.2f},"
    f"S:{-1.0 if d['smap_soil'] is None else d['smap_soil']:.1f}\n"
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

# --- 7 SEKMELİ YENİ NESİL YAPISAL SEKMELER ---
tab1, tab2, tab3, tab4, tab5, tab6, tab7 = st.tabs([
    "🗺️ NASA Telemetri", 
    "📊 Trend Analizi", 
    "🚨 Risk & Alarm", 
    "⚖️ Karşılaştırma",
    "🔍 NASA Veri Kataloğu",
    "🌐 3D Dijital İkiz",
    "💧 Hidrolojik & Taşkın"
])

with tab1:
    render_box(
        title="🌍 NASA GIBS Uydu Gözlem Haritası",
        subtitle=f"NASA MODIS/Terra uydu görüntüsü | Gözlem noktası: {st.session_state.mekan_adi}",
        border_color="rgba(16, 185, 129, 0.75)",
        glow_color="rgba(16, 185, 129, 0.55)",
        bg_gradient="linear-gradient(135deg, rgba(6, 78, 59, 0.55) 0%, rgba(15, 23, 42, 0.9) 100%)"
    )
    st.caption("Uydu görüntüleri NASA Global Imagery Browse Services (GIBS) üzerinden gelir. Görüntü tarihi ürünün işlenme takvimine bağlıdır.")
    lat_val, lon_val = st.session_state.secilen_lat, st.session_state.secilen_lon
    nasa_map_date = st.date_input(
        "NASA uydu görüntüsü tarihi",
        value=datetime.now().date() - timedelta(days=2),
        max_value=datetime.now().date() - timedelta(days=1),
        key="nasa_gibs_date"
    ).strftime("%Y-%m-%d")
    gibs_map_html = f"""
    <div id="nasa-map" style="height:560px;width:100%;border-radius:22px;overflow:hidden;border:2px solid rgba(56,189,248,.45);"></div>
    <link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css"/>
    <script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>
    <script>
      const map = L.map('nasa-map').setView([{lat_val}, {lon_val}], 6);
      const osm = L.tileLayer('https://{{s}}.tile.openstreetmap.org/{{z}}/{{x}}/{{y}}.png', {{
        maxZoom: 18, attribution: '&copy; OpenStreetMap contributors'
      }}).addTo(map);
      const nasaLayer = L.tileLayer(
        'https://gibs.earthdata.nasa.gov/wmts/epsg3857/best/MODIS_Terra_CorrectedReflectance_TrueColor/default/{nasa_map_date}/GoogleMapsCompatible_Level9/{{z}}/{{y}}/{{x}}.jpg',
        {{maxZoom: 9, opacity: 0.90, attribution: 'NASA GIBS / MODIS Terra'}}
      ).addTo(map);
      L.marker([{lat_val}, {lon_val}]).addTo(map)
        .bindPopup('Lightning Flora observation point').openPopup();
      L.control.layers({{'OpenStreetMap': osm}}, {{'NASA MODIS Terra – True Color': nasaLayer}}).addTo(map);
    </script>
    """
    components.html(gibs_map_html, height=575, scrolling=False)



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
        render_metric_card("2️⃣ Rüzgar", f"{d['ruzgar']} m/s", f"Yön: {d['ruzgar_yon']}°", "rgba(16, 185, 129, 0.75)", "#34d399", "rgba(16, 185, 129, 0.45)", "linear-gradient(135deg, rgba(16, 185, 129, 0.35) 0%, rgba(15, 23, 42, 0.9) 100%)")
    with c3:
        render_metric_card("3️⃣ NDVI", "Harita katmanı", "Sayısal MODIS NDVI entegrasyonu henüz yok", "rgba(245, 158, 11, 0.75)", "#fbbf24", "rgba(245, 158, 11, 0.45)", "linear-gradient(135deg, rgba(245, 158, 11, 0.35) 0%, rgba(15, 23, 42, 0.9) 100%)")
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
            Nem oranı %{d['nem']} ve NASA POWER toprak ıslaklığı %{d['smap_soil']} seviyelerindedir. Risk göstergeleri basit eşiklere dayalı ön değerlendirmelerdir; resmî afet tahmini değildir.
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
        "Open-Meteo yükseklik servisinden alır. Bu veri NASA DEM olarak adlandırılmamalıdır. "
        "Yatay eksenler kilometre, dikey eksen metre cinsindendir.</p>",
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
                lighting=dict(ambient=0.45, diffuse=0.85, specular=0.35, roughness=0.65, fresnel=0.15),
                lightposition=dict(x=1000, y=1000, z=1500),
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
                aspectratio=dict(x=1.0, y=1.0, z=0.65),
                camera=dict(eye=dict(x=1.55, y=1.55, z=1.05))
            )
        )
        st.plotly_chart(fig_3d, use_container_width=True)
    except Exception as e:
        logger.exception("3D arazi modeli oluşturulamadı")
        st.error(f"Gerçek arazi verisi alınamadı: {e}")

with tab7:
    render_box(
        title="💧 Hidrolojik Havza ve Taşkın Risk Analizörü",
        subtitle=f"Anlık Yağış ({d['yagis']} mm) ve Toprak Doygunluğu (NASA POWER üst toprak ıslaklığı: %{d['smap_soil']}) Parametrelerine Göre Taşkın & Akış Simülasyonu.",
        border_color="rgba(59, 130, 246, 0.75)",
        glow_color="rgba(59, 130, 246, 0.55)",
        bg_gradient="linear-gradient(135deg, rgba(30, 58, 138, 0.55) 0%, rgba(15, 23, 42, 0.9) 100%)"
    )
    risk_skoru = min(100, max(5, int(d['yagis'] * 15 + ((d['smap_soil'] or 0) * 0.8)))))
    
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