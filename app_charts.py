import pandas as pd
import streamlit as st
import gspread
from google.oauth2.service_account import Credentials
from datetime import datetime, timedelta
import requests
import plotly.express as px
import plotly.graph_objects as go
from dotenv import load_dotenv
import os
import json
import pytz

# ─────────────────────────────────────────────
#  PAGE CONFIG & CUSTOM CSS
# ─────────────────────────────────────────────
st.set_page_config(
    page_title="Vybbe Charts",
    page_icon="🎵",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Syne:wght@400;600;700;800&family=DM+Sans:wght@300;400;500&display=swap');

/* ── Global ── */
html, body, [class*="css"] {
    font-family: 'DM Sans', sans-serif;
}

/* ── Background ── */
.stApp {
    background: #0a0a0f;
    color: #e8e8f0;
}

/* ── Sidebar ── */
section[data-testid="stSidebar"] {
    background: #111118 !important;
    border-right: 1px solid #1e1e2e;
}
section[data-testid="stSidebar"] .stRadio label,
section[data-testid="stSidebar"] .stRadio div {
    color: #c8c8d8 !important;
}
section[data-testid="stSidebar"] .stExpander {
    border: 1px solid #1e1e2e !important;
    border-radius: 8px;
}

/* ── Header / Title ── */
h1 { font-family: 'Syne', sans-serif; font-weight: 800; color: #ffffff; letter-spacing: -1px; }
h2 { font-family: 'Syne', sans-serif; font-weight: 700; color: #ffffff; }
h3 { font-family: 'Syne', sans-serif; font-weight: 600; color: #e0e0f0; }

/* ── Metric cards ── */
[data-testid="metric-container"] {
    background: linear-gradient(135deg, #16162a 0%, #1a1a2e 100%);
    border: 1px solid #2a2a45;
    border-radius: 12px;
    padding: 16px 20px;
}
[data-testid="metric-container"] label {
    color: #888aaa !important;
    font-size: 12px !important;
    text-transform: uppercase;
    letter-spacing: 1px;
}
[data-testid="metric-container"] [data-testid="stMetricValue"] {
    color: #a78bfa !important;
    font-family: 'Syne', sans-serif;
    font-size: 28px !important;
    font-weight: 700;
}

/* ── Chart rows ── */
.chart-row {
    background: #111118;
    border: 1px solid #1e1e2e;
    border-radius: 12px;
    padding: 10px 14px;
    margin-bottom: 6px;
    transition: border-color 0.2s;
}
.chart-row:hover { border-color: #a78bfa; }

.rank-badge {
    font-family: 'Syne', sans-serif;
    font-size: 22px;
    font-weight: 800;
    color: #a78bfa;
    min-width: 36px;
    display: inline-block;
}
.rank-badge.gold  { color: #fbbf24; }
.rank-badge.silver{ color: #94a3b8; }
.rank-badge.bronze{ color: #c07a45; }

.item-name {
    font-family: 'Syne', sans-serif;
    font-weight: 600;
    font-size: 15px;
    color: #f0f0ff;
    line-height: 1.3;
}
.artist-name {
    font-size: 13px;
    color: #7878a0;
    margin-top: 2px;
}
.stat-cell {
    font-size: 14px;
    color: #9090b8;
    text-align: center;
}
.stat-highlight {
    color: #a78bfa;
    font-weight: 600;
}

/* ── Dividers ── */
hr { border: none; border-top: 1px solid #1e1e2e; margin: 16px 0; }

/* ── Pill tag ── */
.pill {
    display: inline-block;
    background: #1e1e3a;
    border: 1px solid #3030a0;
    border-radius: 20px;
    padding: 3px 12px;
    font-size: 12px;
    color: #a78bfa;
    font-weight: 500;
    letter-spacing: 0.5px;
}

/* ── Platform badge colors ── */
.platform-spotify  { background:#1a2e1a; border-color:#1db954; color:#1db954; }
.platform-youtube  { background:#2e1a1a; border-color:#ff0000; color:#ff4444; }
.platform-deezer   { background:#1a1a2e; border-color:#a238ff; color:#b060ff; }
.platform-amazon   { background:#2e261a; border-color:#ff9900; color:#ff9900; }
.platform-apple    { background:#2e1a2a; border-color:#fa243c; color:#fa243c; }

/* ── Download button ── */
.stDownloadButton > button {
    background: linear-gradient(135deg, #7c3aed, #a855f7) !important;
    color: white !important;
    border: none !important;
    border-radius: 10px !important;
    font-family: 'Syne', sans-serif !important;
    font-weight: 600 !important;
    padding: 10px 24px !important;
    transition: opacity 0.2s !important;
}
.stDownloadButton > button:hover { opacity: 0.85 !important; }

/* ── Selectbox & date inputs ── */
.stSelectbox > div > div,
.stDateInput > div > div {
    background: #16162a !important;
    border-color: #2a2a45 !important;
    color: #e0e0f0 !important;
    border-radius: 8px !important;
}

/* ── Checkbox ── */
.stCheckbox label { color: #9090b8 !important; }

/* ── Info / warning boxes ── */
.stInfo    { background: #0f1a2e !important; border-left-color: #3b82f6 !important; color: #90b8f0 !important; }
.stWarning { background: #2e1f0a !important; border-left-color: #f59e0b !important; color: #f0c070 !important; }
.stError   { background: #2e0a0a !important; border-left-color: #ef4444 !important; color: #f08080 !important; }

/* ── Plotly chart background ── */
.js-plotly-plot .plotly .main-svg { background: transparent !important; }
</style>
""", unsafe_allow_html=True)

# ─────────────────────────────────────────────
#  TIMEZONE & ENV
# ─────────────────────────────────────────────
load_dotenv()

try:
    TZ = pytz.timezone("America/Sao_Paulo")
except Exception:
    TZ = None

# ─────────────────────────────────────────────
#  GOOGLE SHEETS AUTH  ← CORREÇÃO PRINCIPAL
#  Usa google-auth em vez de oauth2client
#  Lê direto do secrets sem arquivo temporário
# ─────────────────────────────────────────────
planilha_completa = None

@st.cache_resource
def get_gspread_client():
    """Autentica no Google Sheets de forma segura, sem arquivo temporário."""
    # Tenta st.secrets primeiro (Streamlit Cloud), depois variável de ambiente
    creds_raw = None

    try:
        creds_raw = st.secrets["GOOGLE_SHEETS_CREDENTIALS"]
    except (KeyError, FileNotFoundError):
        creds_raw = os.getenv("GOOGLE_SHEETS_CREDENTIALS")

    if not creds_raw:
        st.error("❌ Credencial GOOGLE_SHEETS_CREDENTIALS não encontrada.")
        return None

    # Se vier como string JSON, converte para dict
    if isinstance(creds_raw, str):
        try:
            creds_dict = json.loads(creds_raw)
        except json.JSONDecodeError as e:
            st.error(f"❌ JSON de credenciais inválido: {e}")
            return None
    else:
        # st.secrets pode retornar um objeto AttrDict — converte para dict comum
        creds_dict = dict(creds_raw)

    scopes = [
        "https://www.googleapis.com/auth/spreadsheets",
        "https://www.googleapis.com/auth/drive",
    ]

    try:
        creds = Credentials.from_service_account_info(creds_dict, scopes=scopes)
        client = gspread.authorize(creds)
        return client
    except Exception as e:
        st.error(f"❌ Falha na autenticação: {e}")
        return None


client = get_gspread_client()

if client:
    try:
        planilha_completa = client.open(title="BD_Charts")
    except Exception as e:
        st.error(f"❌ Erro ao abrir a planilha 'BD_Charts': {e}")

# ─────────────────────────────────────────────
#  DATA LOADING
# ─────────────────────────────────────────────
@st.cache_data(ttl=300)
def load_data(sheet_index):
    if not planilha_completa:
        return pd.DataFrame()
    try:
        worksheet = planilha_completa.get_worksheet(sheet_index)
        if sheet_index == 5:
            expected_headers = [
                "DATA", "Rank", "uri", "Artista", "Música", "source",
                "peak_rank", "previous_rank", "days_on_chart",
                "Corte charts", "Data de Pico", "Streams",
            ]
            data = worksheet.get_all_records(expected_headers=expected_headers)
        else:
            data = worksheet.get_all_records()
        return pd.DataFrame(data)
    except gspread.exceptions.APIError as e:
        st.error(f"Erro ao acessar planilha (sheet {sheet_index}): {e}")
        return pd.DataFrame()


# ─────────────────────────────────────────────
#  DEEZER IMAGE API
# ─────────────────────────────────────────────
@st.cache_data(ttl=3600)
def get_artist_image(artist_name):
    try:
        primary = artist_name.split(",")[0].strip() if isinstance(artist_name, str) else artist_name
        r = requests.get(f"https://api.deezer.com/search/artist?q={primary}", timeout=5).json()
        if r.get("data"):
            return r["data"][0]["picture_medium"]
    except Exception:
        pass
    return None


@st.cache_data(ttl=3600)
def get_album_image(album_name):
    try:
        r = requests.get(f"https://api.deezer.com/search/album?q={album_name}", timeout=5).json()
        if r.get("data"):
            return r["data"][0]["cover_medium"]
    except Exception:
        pass
    return None


@st.cache_data(ttl=3600)
def get_track_album_image(track_name, artist_name):
    try:
        primary = artist_name.split(",")[0].strip() if isinstance(artist_name, str) else artist_name
        url = f'https://api.deezer.com/search?q=track:"{track_name}" artist:"{primary}"'
        r = requests.get(url, timeout=5).json()
        if r.get("data"):
            return r["data"][0]["album"]["cover_medium"]
    except Exception:
        pass
    return get_artist_image(artist_name)


# ─────────────────────────────────────────────
#  FORMATTERS
# ─────────────────────────────────────────────
def format_br_number(number):
    try:
        s = str(number).strip().replace(".", "").replace(",", "")
        n = int(float(s))
        return f"{n:,}".replace(",", "X").replace(".", ",").replace("X", ".")
    except (ValueError, TypeError):
        return str(number)


def format_br_date(date_str):
    try:
        return datetime.strptime(date_str, "%d/%m/%Y").strftime("%d/%m/%Y")
    except (ValueError, TypeError):
        return str(date_str)


def rank_badge_class(rank):
    try:
        r = int(rank)
        if r == 1: return "rank-badge gold"
        if r == 2: return "rank-badge silver"
        if r == 3: return "rank-badge bronze"
    except Exception:
        pass
    return "rank-badge"


def platform_class(platform):
    return {
        "Spotify": "platform-spotify",
        "Youtube": "platform-youtube",
        "YouTube": "platform-youtube",
        "Deezer": "platform-deezer",
        "Amazon": "platform-amazon",
        "Apple Music": "platform-apple",
    }.get(platform, "")


# ─────────────────────────────────────────────
#  DATE RANGE HELPER
# ─────────────────────────────────────────────
def update_date_range(key_suffix, df_original, item_col, date_col_name):
    selected_item = st.session_state.get(f"selectbox_{key_suffix}")
    df_f = df_original[df_original[item_col] == selected_item] if selected_item else pd.DataFrame()
    if not df_f.empty:
        mn = df_f[date_col_name].min().date()
        mx = df_f[date_col_name].max().date()
    else:
        today = datetime.now(TZ).date() if TZ else datetime.today().date()
        mn = mx = today
    st.session_state[f"start_date_state_{key_suffix}"] = mn
    st.session_state[f"end_date_state_{key_suffix}"] = mx


# ─────────────────────────────────────────────
#  MAIN CHART DISPLAY
# ─────────────────────────────────────────────
def display_chart(sheet_index, section_title, item_type, key_suffix, chart_type, platform):
    # ── Header with platform pill ──
    pcls = platform_class(platform)
    st.markdown(
        f"""<div style="display:flex;align-items:center;gap:12px;margin-bottom:8px;">
              <h2 style="margin:0;">{section_title}</h2>
              <span class="pill {pcls}">{platform}</span>
           </div>""",
        unsafe_allow_html=True,
    )

    df = load_data(sheet_index)

    if df.empty:
        st.info("😪 Nenhum dado disponível para este chart.")
        st.write("---")
        return

    item_col = (
        "Música" if "Música" in df.columns
        else ("Álbum" if "Álbum" in df.columns
              else ("Faixa" if "Faixa" in df.columns else "Artista"))
    )
    date_col_name = "DATA" if "DATA" in df.columns else "Data"

    if date_col_name not in df.columns:
        st.warning("Coluna de data não encontrada.")
        st.write("---")
        return

    df[date_col_name] = pd.to_datetime(df[date_col_name], format="%d/%m/%Y", errors="coerce")

    today_br = datetime.now(TZ).date() if TZ else datetime.today().date()
    yesterday = today_br - timedelta(days=1)
    latest_date_available = df[date_col_name].max().date()

    df_display = pd.DataFrame()
    selected_date_display = None

    show_date_selector = st.checkbox("🗓 Pesquisar por datas anteriores?", key=f"checkbox_{key_suffix}")

    if chart_type == "daily":
        if show_date_selector:
            selected_date = st.date_input("Selecione a data", latest_date_available, key=f"date_input_{key_suffix}")
            df_display = df[df[date_col_name].dt.date == selected_date].copy()
            selected_date_display = selected_date
        else:
            df_display = df[df[date_col_name].dt.date == yesterday].copy()
            selected_date_display = yesterday
            if df_display.empty:
                df_display = df[df[date_col_name].dt.date == latest_date_available].copy()
                selected_date_display = latest_date_available

    elif chart_type == "weekly":
        if show_date_selector:
            selected_date = st.date_input("Selecione a data", latest_date_available, key=f"date_input_{key_suffix}")
            df_display = df[df[date_col_name].dt.date == selected_date].copy()
            selected_date_display = selected_date
        else:
            df_display = df[df[date_col_name].dt.date == latest_date_available].copy()
            selected_date_display = latest_date_available

    if df_display.empty:
        st.info(f"😪 Nenhum dado para {selected_date_display.strftime('%d/%m/%Y') if selected_date_display else 'a data selecionada'}.")
        st.write("---")
        return

    # ── Metrics ──
    total_artistas = df_display["Artista"].nunique() if "Artista" in df_display.columns else 0
    total_items = df_display[item_col].nunique() if item_col in df_display.columns else 0

    m_cols = st.columns(3)
    with m_cols[0]:
        st.metric("📅 Data", selected_date_display.strftime("%d/%m/%Y") if selected_date_display else "-")
    with m_cols[1]:
        st.metric("🎤 Artistas", total_artistas)
    with m_cols[2]:
        if item_type == "o artista":
            st.metric("📊 Total", total_artistas)
        else:
            st.metric(f"🎵 {item_col}s", total_items)

    if "Daily Top Songs Brasil" in section_title and "Corte charts" in df_display.columns:
        corte = df_display["Corte charts"].iloc[0]
        if corte and corte != "N/A":
            st.markdown(f"<span class='pill'>✂ Corte: {corte}</span>", unsafe_allow_html=True)

    st.markdown("<hr>", unsafe_allow_html=True)

    # ── Column flags ──
    has_streams = (
        platform == "Spotify"
        and "Streams" in df_display.columns
        and not df_display["Streams"].isna().all()
        and "Artists" not in section_title
        and "Albums" not in section_title
    )
    has_views = (
        platform in ("Youtube", "YouTube")
        and "Visualizações Semanais" in df_display.columns
        and not df_display["Visualizações Semanais"].isna().all()
    )
    has_peak_date = "Data de Pico" in df_display.columns or "Data do Pico" in df_display.columns
    time_header = "Semanas" if ("Weekly" in section_title or "Semanal" in section_title) else "Dias"

    # ── Table header ──
    col_ratios = [0.5, 3.5, 0.6, 0.6, 0.7]
    if has_streams or has_views: col_ratios.append(1.4)
    if has_peak_date:            col_ratios.append(1.1)

    hcols = st.columns(col_ratios)
    header_labels = ["#",
                     "ARTISTA" if "Top Artists" in section_title or "Top Artistas" in section_title
                     else ("ÁLBUM" if "Albums" in section_title else "MÚSICA / FAIXA"),
                     "🏆 PICO", "↩ ANT.", f"📆 {time_header.upper()}"]
    if has_streams or has_views:
        header_labels.append("▶ STREAMS" if has_streams else "👁 VIEWS")
    if has_peak_date:
        header_labels.append("📅 PICO")

    for hc, hl in zip(hcols, header_labels):
        with hc:
            st.markdown(f"<span style='font-size:11px;color:#555580;font-weight:700;letter-spacing:1px;text-transform:uppercase;'>{hl}</span>", unsafe_allow_html=True)

    st.markdown("<hr style='margin:4px 0 8px 0;'>", unsafe_allow_html=True)

    # ── Rows ──
    image_width = 56
    for _, row in df_display.iterrows():
        rank = row.get("Rank", "N/A")
        item_name = str(row.get(item_col, "")).strip()
        artist_col = "Artista" if "Artista" in df_display.columns else "Criador"
        artist_name = str(row.get(artist_col, "")).strip()
        peak_rank    = row.get("peak_rank", "N/A")
        previous_rank = row.get("previous_rank", "N/A")
        streak = row.get("days_on_chart", "N/A")
        if "Weekly" in section_title or "Semanal" in section_title:
            streak = row.get("Weeks_on_chart", row.get("weeks_on_chart", "N/A"))
        streams_val = "N/A"
        if has_streams:
            streams_val = row.get("Streams", "N/A")
        elif has_views:
            streams_val = row.get("Visualizações Semanais", "N/A")
        peak_date = row.get("Data de Pico") or row.get("Data do Pico", "N/A")
        if peak_date and peak_date != "N/A":
            peak_date = format_br_date(str(peak_date))

        # Deezer image
        image_url = None
        if item_type == "o artista":
            image_url = get_artist_image(artist_name)
        elif item_type == "o álbum":
            image_url = get_album_image(item_name)
        elif item_type in ("a música", "a faixa"):
            image_url = get_track_album_image(item_name, artist_name)

        rcols = st.columns(col_ratios)
        with rcols[0]:
            st.markdown(f"<span class='{rank_badge_class(rank)}'>{rank}</span>", unsafe_allow_html=True)
        with rcols[1]:
            inner = st.columns([0.6, 3.4])
            with inner[0]:
                if image_url:
                    st.image(image_url, width=image_width)
                else:
                    st.markdown("<div style='width:56px;height:56px;background:#1e1e2e;border-radius:8px;display:flex;align-items:center;justify-content:center;font-size:22px;'>🎵</div>", unsafe_allow_html=True)
            with inner[1]:
                st.markdown(f"<div class='item-name'>{item_name}</div>", unsafe_allow_html=True)
                if item_type != "o artista":
                    st.markdown(f"<div class='artist-name'>{artist_name}</div>", unsafe_allow_html=True)
        with rcols[2]:
            st.markdown(f"<span class='stat-cell stat-highlight'>{peak_rank}</span>", unsafe_allow_html=True)
        with rcols[3]:
            st.markdown(f"<span class='stat-cell'>{previous_rank}</span>", unsafe_allow_html=True)
        with rcols[4]:
            st.markdown(f"<span class='stat-cell'>{streak}</span>", unsafe_allow_html=True)

        ci = 5
        if has_streams or has_views:
            with rcols[ci]:
                disp = format_br_number(streams_val) if streams_val != "N/A" else "N/A"
                st.markdown(f"<span class='stat-cell'>{disp}</span>", unsafe_allow_html=True)
            ci += 1
        if has_peak_date:
            with rcols[ci]:
                st.markdown(f"<span class='stat-cell'>{peak_date}</span>", unsafe_allow_html=True)

        st.markdown("<div style='border-top:1px solid #16162a;margin:4px 0;'></div>", unsafe_allow_html=True)

    # ── Evolution chart ──
    st.markdown("<hr>", unsafe_allow_html=True)
    df["Mês"] = df[date_col_name].dt.strftime("%B")
    df["Ano"]  = df[date_col_name].dt.year
    df_unique_items = sorted(df[item_col].unique())
    selectbox_key = f"selectbox_{key_suffix}"

    if selectbox_key not in st.session_state and df_unique_items:
        st.session_state[selectbox_key] = df_unique_items[0]
        update_date_range(key_suffix, df, item_col, date_col_name)

    initial_index = (
        df_unique_items.index(st.session_state.get(selectbox_key, df_unique_items[0]))
        if df_unique_items else 0
    )

    selected_item = st.selectbox(
        f"📈 Selecione {item_type} para análise de evolução",
        df_unique_items,
        index=initial_index,
        key=selectbox_key,
        on_change=update_date_range,
        args=(key_suffix, df, item_col, date_col_name),
    )

    s_key = f"start_date_state_{key_suffix}"
    e_key = f"end_date_state_{key_suffix}"
    if s_key not in st.session_state:
        update_date_range(key_suffix, df, item_col, date_col_name)

    df_filtered = df[df[item_col] == selected_item].copy()

    col1, col2 = st.columns(2)
    with col1:
        start_date = st.date_input("Data de início", value=st.session_state[s_key],
                                   min_value=st.session_state[s_key], max_value=st.session_state[e_key],
                                   key=f"start_date_{key_suffix}")
    with col2:
        end_date = st.date_input("Data de fim", value=st.session_state[e_key],
                                 min_value=st.session_state[s_key], max_value=st.session_state[e_key],
                                 key=f"end_date_{key_suffix}")

    df_chart = df_filtered[
        (df_filtered[date_col_name].dt.date >= start_date) &
        (df_filtered[date_col_name].dt.date <= end_date)
    ].copy()

    y_axis_col   = "Rank"
    y_axis_title = "Posição no Ranking"

    if item_type in ("a música", "a faixa"):
        chart_options = ["Ranking"]
        if "Streams" in df_chart.columns and not df_chart["Streams"].isna().all():
            chart_options.append("Streams")
        if "Visualizações Semanais" in df_chart.columns and not df_chart["Visualizações Semanais"].isna().all():
            chart_options.append("Visualizações")

        if len(chart_options) > 1:
            ct = st.radio("Tipo de visualização:", chart_options, key=f"radio_chart_type_{key_suffix}", horizontal=True)
            if ct == "Streams":       y_axis_col = "Streams";               y_axis_title = "Streams"
            elif ct == "Visualizações": y_axis_col = "Visualizações Semanais"; y_axis_title = "Visualizações"

    if y_axis_col in ("Streams", "Visualizações Semanais") and y_axis_col in df_chart.columns:
        df_chart["_num"] = df_chart[y_axis_col].astype(str).str.replace(".", "", regex=False).str.replace(",", "", regex=False)
        df_chart[y_axis_col] = pd.to_numeric(df_chart["_num"], errors="coerce")
        df_chart["y_fmt"] = df_chart[y_axis_col].apply(lambda x: format_br_number(x))
        df_chart.drop(columns=["_num"], inplace=True)

    text_col = "y_fmt" if "y_fmt" in df_chart.columns else y_axis_col

    # Image for chart header
    img_url = None
    if item_type == "o artista":
        img_url = get_artist_image(selected_item)
    elif item_type in ("a música", "a faixa"):
        s = df[df[item_col] == selected_item]["Artista"]
        an = s.iloc[0].split(",")[0].strip() if not s.empty else ""
        img_url = get_track_album_image(selected_item, an)
    elif item_type == "o álbum":
        img_url = get_album_image(selected_item)

    img_tag = f"<img src='{img_url}' width=48 style='border-radius:50%;margin-right:10px;vertical-align:middle;'>" if img_url else "🎵 "
    st.markdown(
        f"<div style='display:flex;align-items:center;margin-bottom:8px;'>"
        f"{img_tag}<span style='font-family:Syne,sans-serif;font-size:20px;font-weight:700;color:#f0f0ff;'>"
        f"Evolução de <span style='color:#a78bfa;'>{selected_item}</span></span></div>",
        unsafe_allow_html=True,
    )

    if not df_chart.empty:
        fig = go.Figure()
        fig.add_trace(go.Scatter(
            x=df_chart[date_col_name],
            y=df_chart[y_axis_col],
            mode="lines+markers+text",
            text=df_chart[text_col],
            textposition="top center",
            line=dict(color="#a78bfa", width=2.5, shape="spline"),
            marker=dict(color="#a78bfa", size=7),
            textfont=dict(color="#c8b4fa", size=11),
        ))
        yaxis_cfg = dict(title=y_axis_title, gridcolor="#1e1e2e", color="#7070a0")
        if y_axis_col == "Rank":
            yaxis_cfg["autorange"] = "reversed"
        fig.update_layout(
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="#0d0d18",
            xaxis=dict(title="Data", gridcolor="#1a1a2e", color="#7070a0"),
            yaxis=yaxis_cfg,
            font=dict(family="DM Sans", color="#9090b8"),
            margin=dict(l=0, r=0, t=20, b=0),
            height=340,
        )
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("Sem dados para o período selecionado.")

    st.markdown("<hr>", unsafe_allow_html=True)


# ─────────────────────────────────────────────
#  WEEKLY GLOBAL CHART (same design)
# ─────────────────────────────────────────────
def display_weekly_global_chart(global_sheet_index, global_section_title, global_item_type, global_key_suffix):
    pcls = platform_class("Spotify")
    st.markdown(
        f"""<div style="display:flex;align-items:center;gap:12px;margin-bottom:8px;">
              <h2 style="margin:0;">{global_section_title}</h2>
              <span class="pill {pcls}">Spotify</span>
           </div>""",
        unsafe_allow_html=True,
    )

    df = load_data(global_sheet_index)

    if df.empty:
        st.info(f"😪 Nenhum dado disponível para {global_section_title}.")
        st.write("---")
        return

    item_col = "Música" if "Música" in df.columns else ("Álbum" if "Álbum" in df.columns else "Artista")
    date_col_name = "Data" if "Data" in df.columns else "DATA"
    df[date_col_name] = pd.to_datetime(df[date_col_name], format="%d/%m/%Y", errors="coerce")

    latest_date = df[date_col_name].max().date()
    show_date_selector = st.checkbox("🗓 Pesquisar por datas anteriores?", key=f"checkbox_{global_key_suffix}")

    if show_date_selector:
        selected_date = st.date_input("Selecione a data", latest_date, key=f"date_input_{global_key_suffix}")
        df_display = df[df[date_col_name].dt.date == selected_date].copy()
        selected_date_display = selected_date
    else:
        df_display = df[df[date_col_name].dt.date == latest_date].copy()
        selected_date_display = latest_date

    if df_display.empty:
        st.info(f"😪 Nenhum dado para {selected_date_display.strftime('%d/%m/%Y')}.")
        st.write("---")
        return

    st.markdown(f"**Semana:** {selected_date_display.strftime('%d/%m/%Y')}")

    # Selectbox for trend chart
    df_unique_items = sorted(df[item_col].unique())
    selectbox_key = f"selectbox_{global_key_suffix}"

    if selectbox_key not in st.session_state and df_unique_items:
        st.session_state[selectbox_key] = df_unique_items[0]
        update_date_range(global_key_suffix, df, item_col, date_col_name)

    initial_index = (
        df_unique_items.index(st.session_state.get(selectbox_key, df_unique_items[0]))
        if df_unique_items else 0
    )

    selected_item = st.selectbox(
        f"📈 Selecione {global_item_type} para análise de evolução",
        df_unique_items,
        index=initial_index,
        key=selectbox_key,
        on_change=update_date_range,
        args=(global_key_suffix, df, item_col, date_col_name),
    )

    s_key = f"start_date_state_{global_key_suffix}"
    e_key = f"end_date_state_{global_key_suffix}"
    if s_key not in st.session_state:
        update_date_range(global_key_suffix, df, item_col, date_col_name)

    df_filtered = df[df[item_col] == selected_item].copy()

    col1, col2 = st.columns(2)
    with col1:
        start_date = st.date_input("Data de início", value=st.session_state[s_key],
                                   min_value=st.session_state[s_key], max_value=st.session_state[e_key],
                                   key=f"start_date_{global_key_suffix}")
    with col2:
        end_date = st.date_input("Data de fim", value=st.session_state[e_key],
                                 min_value=st.session_state[s_key], max_value=st.session_state[e_key],
                                 key=f"end_date_{global_key_suffix}")

    df_chart = df_filtered[
        (df_filtered[date_col_name].dt.date >= start_date) &
        (df_filtered[date_col_name].dt.date <= end_date)
    ].copy()

    img_url = None
    if global_item_type == "o artista":
        img_url = get_artist_image(selected_item)
    elif global_item_type in ("a música", "a faixa"):
        s = df[df[item_col] == selected_item]["Artista"]
        an = s.iloc[0].split(",")[0].strip() if not s.empty else ""
        img_url = get_track_album_image(selected_item, an)
    elif global_item_type == "o álbum":
        img_url = get_album_image(selected_item)

    img_tag = f"<img src='{img_url}' width=48 style='border-radius:50%;margin-right:10px;vertical-align:middle;'>" if img_url else "🎵 "
    st.markdown(
        f"<div style='display:flex;align-items:center;margin-bottom:8px;'>"
        f"{img_tag}<span style='font-family:Syne,sans-serif;font-size:20px;font-weight:700;color:#f0f0ff;'>"
        f"Evolução de <span style='color:#a78bfa;'>{selected_item}</span></span></div>",
        unsafe_allow_html=True,
    )

    if not df_chart.empty:
        fig = go.Figure()
        fig.add_trace(go.Scatter(
            x=df_chart[date_col_name],
            y=df_chart["Rank"],
            mode="lines+markers+text",
            text=df_chart["Rank"],
            textposition="top center",
            line=dict(color="#a78bfa", width=2.5, shape="spline"),
            marker=dict(color="#a78bfa", size=7),
            textfont=dict(color="#c8b4fa", size=11),
        ))
        fig.update_layout(
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="#0d0d18",
            xaxis=dict(title="Data", gridcolor="#1a1a2e", color="#7070a0"),
            yaxis=dict(title="Posição", autorange="reversed", gridcolor="#1e1e2e", color="#7070a0"),
            font=dict(family="DM Sans", color="#9090b8"),
            margin=dict(l=0, r=0, t=20, b=0),
            height=340,
        )
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("Sem dados para o período selecionado.")

    st.markdown("<hr>", unsafe_allow_html=True)


# ─────────────────────────────────────────────
#  WHATSAPP MESSAGE GENERATORS
# ─────────────────────────────────────────────
@st.cache_data
def generate_whatsapp_message():
    configs = [
        (5,  "Spotify - Diário Top Músicas Brasil",   "Música",  "Spotify",     False),
        (9,  "Spotify - Diário Viral Músicas Brasil",  "Música",  "Spotify",     False),
        (4,  "Spotify - Diário Top Músicas Global",   "Música",  "Spotify",     False),
        (8,  "Spotify - Diário Viral Músicas Global", "Música",  "Spotify",     False),
        (18, "YouTube - Top Vídeos Diários Brasil",   "Música",  "YouTube",     True),
        (12, "Deezer - Diário Top Músicas",           "Música",  "DEEZER",      False),
        (13, "Amazon - Diário Top Músicas",           "Música",  "Amazon",      False),
        (14, "Apple Music - Diário Top Músicas",      "Música",  "Apple Music", False),
    ]
    parts = []
    for sheet_index, title, item_col, platform_name, _ in configs:
        df = load_data(sheet_index)
        if df.empty: continue
        date_col = "DATA" if "DATA" in df.columns else "Data"
        df[date_col] = pd.to_datetime(df[date_col], format="%d/%m/%Y", errors="coerce")
        df = df.dropna(subset=[date_col])
        if df.empty: continue
        d = df[date_col].max().date()
        ddf = df[df[date_col].dt.date == d].copy()
        if ddf.empty: continue
        ddf["_rn"] = pd.to_numeric(ddf["Rank"], errors="coerce")
        ddf = ddf.sort_values("_rn").dropna(subset=["_rn"])
        parts.append(f"\n🎶 *{platform_name}* - *{title.split(' - ')[-1]}*")
        parts.append(f"📅 *Dados de:* {d.strftime('%d/%m/%Y')}")
        corte = ddf["Corte charts"].iloc[0] if "Corte charts" in ddf.columns else None
        if corte: parts.append(f"✂ *Corte:* {format_br_number(corte)}")
        parts.append("---------------------------------------")
        parts.append(f"*Chart Completo* ({len(ddf)} itens)")
        for _, row in ddf.iterrows():
            rk = row.get("Rank", "N/A")
            nm = str(row.get(item_col, "")).strip()
            ar = str(row.get("Artista" if "Artista" in row else "Criador", "N/A")).strip()
            st_v = row.get("Streams", None)
            vw   = row.get("Visualizações Semanais", None)
            prv  = row.get("previous_rank", "N/A")
            pk   = row.get("peak_rank", "N/A")
            dc   = row.get("days_on_chart", row.get("weeks_on_chart", row.get("Weeks_on_chart", "N/A")))
            label = "Dias" if sheet_index in [4, 5, 8, 9, 12, 13, 14, 18, 19] else "Semanas"
            extra = f" ({format_br_number(st_v)} Streams)" if st_v else (f" ({format_br_number(vw)} Views)" if vw else "")
            parts.append(f"*{rk}. {nm}* - {ar}{extra}")
            parts.append(f"   Ant.: {prv} | Pico: {pk} | {label}: {dc}")
        parts.append("---------------------------------------")
    parts.append("\n*Acesse o dashboard:* https://vybbestreams.streamlit.app/")
    return "\n".join(parts)


@st.cache_data
def generate_weekly_whatsapp_message():
    configs = [
        (6,  "Spotify - Semanal Top Músicas Global",  "Música",  "Spotify", False),
        (7,  "Spotify - Semanal Top Músicas Brasil",  "Música",  "Spotify", False),
        (2,  "Spotify - Semanal Top Artistas Global", "Artista", "Spotify", False),
        (3,  "Spotify - Semanal Top Artistas Brasil", "Artista", "Spotify", False),
        (10, "Spotify - Semanal Top Álbuns Global",   "Álbum",   "Spotify", False),
        (11, "Spotify - Semanal Top Álbuns Brasil",   "Álbuns",  "Spotify", False),
        (16, "YouTube - Top Faixas Semanal Brasil",   "Música",  "YouTube", True),
        (15, "YouTube - Top Artistas Semanal Brasil", "Artista", "YouTube", True),
    ]
    parts = []
    for sheet_index, title, item_col, platform_name, _ in configs:
        df = load_data(sheet_index)
        if df.empty: continue
        date_col = "DATA" if "DATA" in df.columns else "Data"
        df[date_col] = pd.to_datetime(df[date_col], format="%d/%m/%Y", errors="coerce")
        df = df.dropna(subset=[date_col])
        if df.empty: continue
        d = df[date_col].max().date()
        ddf = df[df[date_col].dt.date == d].copy()
        if ddf.empty: continue
        ddf["_rn"] = pd.to_numeric(ddf["Rank"], errors="coerce")
        ddf = ddf.sort_values("_rn").dropna(subset=["_rn"])
        parts.append(f"\n🎶 *{platform_name}* - *{title.split(' - ')[-1]}*")
        parts.append(f"📅 *Dados de:* {d.strftime('%d/%m/%Y')}")
        parts.append("---------------------------------------")
        parts.append(f"*Chart Completo* ({len(ddf)} itens)")
        for _, row in ddf.iterrows():
            rk  = row.get("Rank", "N/A")
            nm  = str(row.get(item_col, "")).strip()
            ar  = str(row.get("Artista" if "Artista" in row else "Criador", "N/A")).strip()
            prv = row.get("previous_rank", row.get("Previous_Rank", "N/A"))
            pk  = row.get("peak_rank", row.get("Peak_Rank", "N/A"))
            wk  = row.get("Weeks_on_chart", row.get("weeks_on_chart", "N/A"))
            parts.append(f"*{rk}. {nm}* - {ar}")
            parts.append(f"   Ant.: {prv} | Pico: {pk} | Semanas: {wk}")
        parts.append("---------------------------------------")
    parts.append("\n*Acesse o dashboard:* https://vybbestreams.streamlit.app/")
    return "\n".join(parts)


# ─────────────────────────────────────────────
#  PAGE HEADER
# ─────────────────────────────────────────────
st.markdown("""
<div style="padding:32px 0 16px 0;">
  <h1 style="font-size:42px;margin-bottom:4px;">🎵 Vybbe Charts</h1>
  <p style="color:#7070a0;font-size:16px;margin-top:0;">
    Inteligência de mercado musical · Dados em tempo real das principais plataformas
  </p>
</div>
""", unsafe_allow_html=True)

st.markdown(
    '<a href="https://ana-comparativa.streamlit.app/" target="_blank" style="color:#a78bfa;font-size:14px;">'
    '↗ Análise Comparativa Faixas Top 200 Spotify</a>',
    unsafe_allow_html=True,
)
st.markdown("<hr>", unsafe_allow_html=True)

# ─────────────────────────────────────────────
#  SIDEBAR
# ─────────────────────────────────────────────
st.sidebar.markdown(
    "<h2 style='font-family:Syne,sans-serif;font-size:20px;color:#a78bfa;margin-bottom:16px;'>🎛 Plataformas</h2>",
    unsafe_allow_html=True,
)
plataforma_selecionada = st.sidebar.radio(
    "Selecione:",
    ["Spotify", "Youtube", "Deezer", "Amazon", "Apple Music"],
)

# ─────────────────────────────────────────────
#  ROUTING
# ─────────────────────────────────────────────
if plataforma_selecionada == "Spotify":
    spotify_type = st.sidebar.radio("Tipo:", ["Daily Charts", "Weekly Charts"])

    if spotify_type == "Daily Charts":
        with st.sidebar.expander("Spotify Daily", expanded=True):
            opcao = st.radio("Opção:", ["Daily Top Songs", "Daily Top Artists", "Daily Viral Songs"], key="daily_menu_radio")

        if opcao == "Daily Top Songs":
            region = st.radio("Região:", ("Global", "Brasil"), key="sub_menu_songs")
            if region == "Global":
                display_chart(4, "Daily Top Songs Global", "a música", "songs_global", "daily", "Spotify")
            else:
                display_chart(5, "Daily Top Songs Brasil", "a música", "songs_brasil", "daily", "Spotify")

        elif opcao == "Daily Top Artists":
            region = st.radio("Região:", ("Global", "Brasil"), key="sub_menu_artists")
            if region == "Global":
                display_chart(0, "Daily Top Artists Global", "o artista", "artists_global", "daily", "Spotify")
            else:
                display_chart(1, "Daily Top Artists Brasil", "o artista", "artists_brasil", "daily", "Spotify")

        elif opcao == "Daily Viral Songs":
            region = st.radio("Região:", ("Global", "Brasil"), key="sub_menu_viral")
            if region == "Global":
                display_chart(8, "Daily Viral Songs Global", "a música", "viral_songs_global", "daily", "Spotify")
            else:
                display_chart(9, "Daily Viral Songs Brasil", "a música", "viral_songs_brasil", "daily", "Spotify")

    elif spotify_type == "Weekly Charts":
        with st.sidebar.expander("Spotify Weekly", expanded=True):
            opcao = st.radio("Opção:", ["Weekly Top Songs", "Weekly Top Artists", "Weekly Top Albums"], key="weekly_menu_radio")

        if opcao == "Weekly Top Songs":
            region = st.radio("Região:", ("Global", "Brasil"), key="sub_menu_songs_weekly")
            if region == "Global":
                display_weekly_global_chart(6, "Weekly Top Songs Global", "a música", "weekly_songs_global")
            else:
                display_chart(7, "Weekly Top Songs Brasil", "a música", "weekly_songs_brasil", "weekly", "Spotify")

        elif opcao == "Weekly Top Artists":
            region = st.radio("Região:", ("Global", "Brasil"), key="sub_menu_artists_weekly")
            if region == "Global":
                display_weekly_global_chart(2, "Weekly Top Artists Global", "o artista", "weekly_artists_global")
            else:
                display_chart(3, "Weekly Top Artists Brasil", "o artista", "weekly_artists_brasil", "weekly", "Spotify")

        elif opcao == "Weekly Top Albums":
            region = st.radio("Região:", ("Global", "Brasil"), key="sub_menu_albums_weekly")
            if region == "Global":
                display_weekly_global_chart(10, "Weekly Top Albums Global", "o álbum", "weekly_albums_global")
            else:
                display_chart(11, "Weekly Top Albums Brasil", "o álbum", "weekly_albums_brasil", "weekly", "Spotify")

elif plataforma_selecionada == "Youtube":
    with st.sidebar.expander("YouTube Charts", expanded=True):
        opcao_yt = st.radio(
            "Opção:",
            ["Top Videos Diários", "Top Shorts Diários", "Top Clipes Semanal", "Top Faixas Semanal", "Top Artistas Semanal"],
            key="youtube_menu_radio",
        )
    chart_map = {
        "Top Videos Diários":  (18, "Top Videos Diários Brasil",              "a música",  "videos_diarios_br",  "daily",  "Youtube"),
        "Top Shorts Diários":  (19, "Músicas mais tocadas nos Shorts",         "a música",  "shorts_diarios_br",  "daily",  "Youtube"),
        "Top Clipes Semanal":  (17, "Top Clipes Semanal Brasil",               "a música",  "clipes_semanal_br",  "weekly", "Youtube"),
        "Top Faixas Semanal":  (16, "Top Faixas Semanal Brasil",               "a faixa",   "faixas_semanal_br",  "weekly", "Youtube"),
        "Top Artistas Semanal":(15, "Top Artistas Semanal Brasil",             "o artista", "artistas_semanal_br","weekly", "Youtube"),
    }
    display_chart(*chart_map[opcao_yt])

elif plataforma_selecionada == "Deezer":
    display_chart(12, "Daily Top Songs Deezer", "a música", "songs_deezer", "daily", "Deezer")

elif plataforma_selecionada == "Amazon":
    display_chart(13, "Daily Top Songs Amazon", "a música", "songs_amazon", "daily", "Amazon")

elif plataforma_selecionada == "Apple Music":
    display_chart(14, "Daily Top Songs Apple Music", "a música", "songs_apple", "daily", "Apple Music")

# ─────────────────────────────────────────────
#  FOOTER + DOWNLOAD
# ─────────────────────────────────────────────
st.markdown("<hr>", unsafe_allow_html=True)
st.markdown(
    "<p style='color:#555580;font-size:13px;'>Desenvolvido com Python e Streamlit · Vybbe Charts</p>",
    unsafe_allow_html=True,
)

today_br = datetime.now(TZ).date() if TZ else datetime.today().date()
today_fmt = today_br.strftime("%Y%m%d")

dl_type = st.radio("Download:", ("Diário", "Semanal"), key="download_chart_type", horizontal=True)

if dl_type == "Diário":
    content   = generate_whatsapp_message()
    fname     = f"Daily_Charts_Vybbe_{today_fmt}.txt"
    btn_label = "📲 Baixar Charts Diários (.txt)"
else:
    content   = generate_weekly_whatsapp_message()
    fname     = f"Weekly_Charts_Vybbe_{today_fmt}.txt"
    btn_label = "📲 Baixar Charts Semanais (.txt)"

st.download_button(
    label=btn_label,
    data=content,
    file_name=fname,
    mime="text/plain",
    help="Baixe os rankings consolidados para compartilhar no WhatsApp.",
)