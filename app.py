import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import feedparser
from datetime import datetime, timedelta
import time
from streamlit_autorefresh import st_autorefresh

# ==========================================
# 1. CONFIGURATION
# ==========================================
st.set_page_config(
    page_title="ESIG'Trade Terminal",
    layout="wide",
    page_icon="⚡",
    initial_sidebar_state="expanded"
)

# Gestion de la navigation
if 'page' not in st.session_state: st.session_state.page = 'home'


def navigate_to(page): st.session_state.page = page; st.rerun()


# --- SIDEBAR GLOBALE & PARAMÈTRES ---
with st.sidebar:
    try:
        st.image("logo_esigelec.png", width=120)
    except:
        st.markdown("### ESIGELEC")

    # Toggle Dark Mode
    is_dark_mode = st.toggle("🌙 Mode Sombre", value=True)

    st.divider()

    # Navigation contextuelle
    if st.session_state.page == 'analysis':
        st.markdown("### ⚡ PARAMÈTRES")

        # 1. Choix de l'Action
        ACTIONS = {"TotalEnergies": "TTE.PA", "Hermès": "RMS.PA", "Dassault Systèmes": "DSY.PA",
                   "Sopra Steria": "SOP.PA", "Airbus": "AIR.PA", "LVMH": "MC.PA", "Schneider Electric": "SU.PA"}

        LOGOS = {"TotalEnergies": "logo_total.png", "Hermès": "logo_hermes.png",
                 "Dassault Systèmes": "logo_dassault.png", "Sopra Steria": "logo_sopra.png",
                 "Airbus": "logo_airbus.png"}

        choix = st.selectbox("Actif", list(ACTIONS.keys()))

        # 2. Choix de la Période
        st.markdown("<br>", unsafe_allow_html=True)
        PERIOD_MAP = {
            "1 Jour": "1d",
            "5 Jours": "5d",
            "1 Mois": "1mo",
            "3 Mois": "3mo",
            "6 Mois": "6mo",
            "1 An": "1y",
            "2 Ans": "2y",
            "5 Ans": "5y",
            "Max": "max"
        }
        choix_periode = st.selectbox("Période d'analyse", list(PERIOD_MAP.keys()), index=6)  # Default 2y
        selected_period = PERIOD_MAP[choix_periode]

        st.markdown("<br>", unsafe_allow_html=True)
        if st.button("⬅ ACCUEIL"): navigate_to('home')
        st.caption("⏱️ SYNC : 60s")
        st_autorefresh(interval=60 * 1000, key="marketupdater")
    else:
        # Variables vides pour la home pour éviter les erreurs
        ACTIONS = {"TotalEnergies": "TTE.PA"}
        LOGOS = {}
        choix = "TotalEnergies"
        selected_period = "1y"

# ==========================================
# 2. GESTION DES THÈMES (CSS)
# ==========================================

# CSS Commun
common_css = """
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600;800&display=swap');
    html, body, [class*="css"] { font-family: 'Inter', sans-serif; }

    .ticker-wrap {
        position: fixed; top: 0; left: 0; width: 100%; overflow: hidden; height: 40px; 
        background-color: #000; border-bottom: 1px solid #333; z-index: 999999; display: block;
    }
    .ticker { display: inline-block; line-height: 40px; white-space: nowrap; padding-right: 100%; box-sizing: content-box; animation: ticker 80s linear infinite; }
    .ticker__item { display: inline-block; padding: 0 1.5rem; font-size: 0.9rem; color: #ccc; font-family: 'Inter', monospace; font-weight: 600; }
    .up { color: #00ff88; } .down { color: #ff3131; }
    @keyframes ticker { 0% { transform: translate3d(0, 0, 0); } 100% { transform: translate3d(-100%, 0, 0); } }

    div[data-testid="stImage"] { display: flex; justify-content: center; align-items: center; width: 100%; }
    div[data-testid="stImage"] > img { object-fit: contain; max-width: 100%; }

    div.stButton > button:first-child {
        width: 100%; border-radius: 60px; font-weight: 900; height: 5em; font-size: 1.8em;
        text-transform: uppercase; letter-spacing: 3px; color: white; border: none;
        background: linear-gradient(135deg, #ff3131 0%, #ff914d 100%);
        transition: all 0.4s; position: relative; overflow: hidden; margin-top: 20px;
    }
    div.stButton > button:first-child:hover { transform: scale(1.02); }
</style>
"""

# CSS Dark
dark_css = """
<style>
    .stApp { background: radial-gradient(circle at center top, #1a1c2e 0%, #090a0f 100%); }
    h1, h2, h3, p, span, div { color: #e0e0e0; }
    h1 { text-shadow: 0 0 20px rgba(255, 75, 75, 0.4); }
    .feature-card { background: rgba(255, 255, 255, 0.03); border: 1px solid rgba(255, 255, 255, 0.05); border-radius: 20px; padding: 30px; text-align: center; height: 100%; }
    div[data-testid="stMetric"], .glass-container { background: rgba(255, 255, 255, 0.03) !important; border: 1px solid rgba(255, 255, 255, 0.1); border-radius: 16px; padding: 20px !important; }
    div[data-testid="stMetricValue"] { color: white; text-shadow: 0 0 10px rgba(255, 255, 255, 0.5); }
    div[data-testid="stMetricLabel"] { color: #aaa; }
</style>
"""

# CSS Light
light_css = """
<style>
    .stApp { background: linear-gradient(135deg, #f5f7fa 0%, #c3cfe2 100%); }
    h1, h2, h3, p, span, div { color: #2c3e50; }
    h1 { color: #1a1a1a !important; text-shadow: none; }
    h3 { color: #555 !important; }
    .feature-card { background: rgba(255, 255, 255, 0.6); border: 1px solid rgba(255, 255, 255, 0.4); box-shadow: 0 10px 30px rgba(0,0,0,0.05); border-radius: 20px; padding: 30px; text-align: center; height: 100%; }
    div[data-testid="stMetric"], .glass-container { background: rgba(255, 255, 255, 0.8) !important; border: 1px solid white; box-shadow: 0 4px 15px rgba(0,0,0,0.05); border-radius: 16px; padding: 20px !important; }
    div[data-testid="stMetricValue"] { color: #1a1a1a; text-shadow: none; }
    div[data-testid="stMetricLabel"] { color: #666; }
    .js-plotly-plot .plotly .main-svg { background: transparent !important; }
</style>
"""

st.markdown(common_css, unsafe_allow_html=True)
if is_dark_mode:
    st.markdown(dark_css, unsafe_allow_html=True)
    graph_template = "plotly_dark"
    graph_bg = "rgba(0,0,0,0)"
    graph_grid = "rgba(255,255,255,0.1)"
else:
    st.markdown(light_css, unsafe_allow_html=True)
    graph_template = "plotly_white"
    graph_bg = "rgba(255,255,255,0.5)"
    graph_grid = "rgba(0,0,0,0.1)"


# ==========================================
# 3. LOGIQUE MÉTIER & CALCULS
# ==========================================
def get_data_and_consensus(ticker, period="2y"):
    """ Récupère les données avec période et intervalle intelligents """
    stock = yf.Ticker(ticker)

    if period == "1d":
        interval = "2m"
    elif period == "5d":
        interval = "15m"
    else:
        interval = "1d"

    df = stock.history(period=period, interval=interval)

    if not df.empty:
        last_price = df['Close'].iloc[-1]
    else:
        last_price = 0

    try:
        info = stock.info
        rec_key = info.get('recommendationKey', 'none')
        target_price = info.get('targetMeanPrice', 0)
        consensus_score = 2.5

        if rec_key == 'strong_buy':
            consensus_score = 5
        elif rec_key == 'buy':
            consensus_score = 4
        elif rec_key == 'outperform':
            consensus_score = 4
        elif rec_key == 'hold':
            consensus_score = 2.5
        elif rec_key == 'underperform':
            consensus_score = 1
        elif rec_key == 'sell':
            consensus_score = 0

        per = info.get('trailingPE') or info.get('forwardPE', 0)
        div_rate = info.get('dividendRate')
        if div_rate is None: div_rate = info.get('trailingAnnualDividendRate', 0)

        if div_rate and last_price > 0:
            div_yield = div_rate / last_price
        else:
            div_yield = info.get('dividendYield', 0)
            if div_yield is None: div_yield = 0
            if div_yield > 1: div_yield = div_yield / 100

        fonda = {"per": per, "yield": div_yield, "div_amt": div_rate,
                 "consensus_txt": rec_key.replace('_', ' ').upper(), "consensus_score": consensus_score,
                 "target_price": target_price}
    except:
        fonda = {"per": 0, "yield": 0, "div_amt": 0, "consensus_txt": "N/A", "consensus_score": 2.5, "target_price": 0}
    return df, fonda


def get_fresh_news(company_name):
    query = company_name.replace(" ", "+")
    rss_url = f"https://news.google.com/rss/search?q={query}+bourse+finance&hl=fr&gl=FR&ceid=FR:fr"
    feed = feedparser.parse(rss_url)
    news_list = []
    positive_words = ['hausse', 'bondit', 'record', 'achat', 'surperforme', 'contrat', 'succès', 'approbation',
                      'dividende', 'solide', 'profit']
    negative_words = ['chute', 'baisse', 'perte', 'alerte', 'dette', 'procès', 'échec', 'sanction', 'démission',
                      'faible', 'incertitude']
    time_threshold = datetime.now() - timedelta(hours=48)
    raw_sentiment = 0;
    count = 0

    for entry in feed.entries:
        try:
            pub_date = datetime.fromtimestamp(time.mktime(entry.published_parsed))
        except:
            continue
        if pub_date < time_threshold: continue

        title = entry.title;
        link = entry.link;
        color = "grey";
        score_mod = 0
        title_lower = title.lower()

        if any(w in title_lower for w in positive_words):
            color = "green";
            score_mod = 1
        elif any(w in title_lower for w in negative_words):
            color = "red";
            score_mod = -1

        raw_sentiment += score_mod;
        count += 1
        news_list.append({"title": title, "date": pub_date.strftime('%d/%m %H:%M'), "link": link, "color": color})
        if count >= 6: break

    if raw_sentiment > 0:
        final_news_score = 4 + (min(raw_sentiment, 2) * 0.5)
    elif raw_sentiment < 0:
        final_news_score = 1
    else:
        final_news_score = 2.5
    return news_list, final_news_score


def calculate_indicators(df):
    if len(df) < 50:
        # Sécurité si pas assez de données
        for col in ['RSI', 'Upper', 'Lower', 'SMA_200', 'SMA_50', 'MACD', 'Signal_Line']:
            df[col] = 0
        df['Upper'] = df['Close'];
        df['Lower'] = df['Close']
        return df

    # 1. RSI
    delta = df['Close'].diff()
    gain = (delta.where(delta > 0, 0)).rolling(14).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
    rs = gain / loss
    df['RSI'] = 100 - (100 / (1 + rs))

    # 2. Bollinger Bands
    df['SMA_20'] = df['Close'].rolling(20).mean()
    df['STD_20'] = df['Close'].rolling(20).std()
    df['Upper'] = df['SMA_20'] + (2 * df['STD_20'])
    df['Lower'] = df['SMA_20'] - (2 * df['STD_20'])

    # 3. SMA 200 (Tendance Long terme)
    df['SMA_200'] = df['Close'].rolling(200).mean()

    # --- NOUVEAUX INDICATEURS ---

    # 4. SMA 50 (Tendance Moyen terme)
    df['SMA_50'] = df['Close'].rolling(50).mean()

    # 5. MACD (Moving Average Convergence Divergence)
    # EMA 12 et 26
    ema12 = df['Close'].ewm(span=12, adjust=False).mean()
    ema26 = df['Close'].ewm(span=26, adjust=False).mean()
    df['MACD'] = ema12 - ema26
    # Ligne de Signal (EMA 9 du MACD)
    df['Signal_Line'] = df['MACD'].ewm(span=9, adjust=False).mean()

    return df


def calculate_weighted_score(df, fonda, news_score):
    if len(df) < 50: return 2.5, ["Données insuffisantes pour l'analyse technique complète"]

    last = df.iloc[-1]
    prev = df.iloc[-2]  # Pour voir les croisements récents
    reasons = []
    tech_points = 0

    # --- RSI (Max 1 pt) ---
    if pd.notna(last['RSI']):
        if last['RSI'] < 35:
            tech_points += 1;
            reasons.append("Tech: RSI en Survente (Rebond probable)")
        elif last['RSI'] > 70:
            tech_points -= 1;
            reasons.append("Tech: RSI en Surachat (Correction probable)")
        else:
            tech_points += 0.5;
            reasons.append(f"Tech: RSI Neutre ({int(last['RSI'])})")

    # --- Bollinger (Max 1.5 pts) ---
    if pd.notna(last['Lower']):
        if last['Close'] < last['Lower']:
            tech_points += 1.5;
            reasons.append("Tech: Prix sous Bollinger Basse (Signal Achat fort)")
        elif last['Close'] > last['Upper']:
            tech_points -= 1;
            reasons.append("Tech: Prix sur Bollinger Haute (Signal Vente)")
        else:
            tech_points += 0.5;
            reasons.append("Tech: Volatilité normale (Bandes Bollinger)")

    # --- SMA 50 & 200 (Max 1.5 pts) ---
    if pd.notna(last['SMA_50']):
        if last['Close'] > last['SMA_50']:
            tech_points += 0.5;
            reasons.append("Tech: Prix > Moyenne Mobile 50j (Hausse moyen terme)")
        else:
            reasons.append("Tech: Prix < Moyenne Mobile 50j (Pression baissière)")

    if pd.notna(last['SMA_200']):
        if last['Close'] > last['SMA_200']:
            tech_points += 0.5;
            reasons.append("Tech: Prix > SMA 200 (Tendance fond Haussière)")

        # Golden Cross check
        if last['SMA_50'] > last['SMA_200'] and prev['SMA_50'] <= prev['SMA_200']:
            tech_points += 1;
            reasons.append("Tech: 🌟 GOLDEN CROSS DÉTECTÉE (SMA 50 croise SMA 200)")
        elif last['SMA_50'] > last['SMA_200']:
            tech_points += 0.25;
            reasons.append("Tech: Configuration Golden Cross active")

    # --- MACD (Max 1 pt) ---
    if pd.notna(last['MACD']):
        if last['MACD'] > last['Signal_Line']:
            tech_points += 1;
            reasons.append("Tech: MACD au-dessus du Signal (Momentum Acheteur)")
        else:
            tech_points -= 1;
            reasons.append("Tech: MACD sous le Signal (Momentum Vendeur)")

    # Normalisation du score technique sur 5
    # Total potentiel max ~ 5.5 points. On divise par 5.5 et remet sur 5
    tech_score_5 = (max(0, tech_points) / 5.5) * 5

    # Analyse Fondamentale
    fund_points = 0
    if fonda['per'] > 0 and fonda['per'] < 15:
        fund_points += 1;
        reasons.append(f"Fonda: Action sous-évaluée (PER {fonda['per']:.1f})")
    elif fonda['per'] > 35:
        fund_points -= 1;
        reasons.append(f"Fonda: Valorisation élevée (PER {fonda['per']:.1f})")
    else:
        reasons.append(f"Fonda: PER Standard ({fonda['per']:.1f})")

    if fonda['yield'] > 0.035:
        fund_points += 1;
        reasons.append(f"Fonda: Dividende attractif ({fonda['yield'] * 100:.1f}%)")

    fund_score_5 = (max(0, fund_points) / 2) * 5
    reasons.append(f"Consensus: Analystes '{fonda['consensus_txt']}'")

    # Calcul Final
    # Tech 40%, Consensus 20%, Fonda 20%, News 20%
    final_score = (
                (tech_score_5 * 0.40) + (fonda['consensus_score'] * 0.20) + (fund_score_5 * 0.20) + (news_score * 0.20))

    return round(final_score, 2), reasons


# ==========================================
# 4. INTERFACES
# ==========================================

def show_home_page():
    # TICKER TAPE
    st.markdown("""
    <div class="ticker-wrap">
        <div class="ticker">
            <div class="ticker__item">BTC/USD <span class="up">▲ 98,450 $</span></div>
            <div class="ticker__item">ETH/USD <span class="up">▲ 3,890 $</span></div>
            <div class="ticker__item">TOTALENERGIES <span class="up">▲ 62.8 €</span></div>
            <div class="ticker__item">LVMH <span class="down">▼ 615.4 €</span></div>
            <div class="ticker__item">AIRBUS <span class="up">▲ 142.5 €</span></div>
            <div class="ticker__item">HERMÈS <span class="up">▲ 2,050 €</span></div>
            <div class="ticker__item">SANOFI <span class="down">▼ 88.2 €</span></div>
            <div class="ticker__item">CAC 40 <span class="up">▲ 7,650</span></div>
            <div class="ticker__item">S&P 500 <span class="up">▲ 5,900</span></div>
            <div class="ticker__item">NASDAQ <span class="up">▲ 19,500</span></div>
            <div class="ticker__item">GOLD <span class="up">▲ 2,610 $</span></div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    st.markdown("<br><br><br><br><br>", unsafe_allow_html=True)

    # HERO
    c_logo, c_hero, c_btn = st.columns([1, 3, 1], gap="medium")
    with c_logo:
        try:
            st.image("logo_esigelec.png", use_container_width=True)
        except:
            pass

    with c_hero:
        title_color = "white" if is_dark_mode else "#2c3e50"
        subtitle_color = "#ccc" if is_dark_mode else "#555"
        st.markdown(f"""
        <div style="text-align: center;">
            <h1 style='color: {title_color}; font-size: 4.5em; font-weight: 900; letter-spacing: -2px; margin-bottom: 5px; text-shadow: 0 0 40px rgba(255, 75, 75, 0.4); line-height: 1.1; text-transform: uppercase;'>
                ESIG'TRADE <span style="color: #FF4B4B;">PRO</span>
            </h1>
            <h3 style='color: {subtitle_color}; font-weight: 400; font-size: 1.2em; margin-top: 10px; letter-spacing: 2px; text-transform: uppercase;'>
                L'INTELLIGENCE ARTIFICIELLE AU SERVICE DE VOTRE ALPHA
            </h3>
        </div>
        """, unsafe_allow_html=True)

    with c_btn:
        st.markdown('<div style="height: 30px;"></div>', unsafe_allow_html=True)
        if st.button("🚀 LANCER LE TERMINAL"):
            navigate_to('analysis')

    st.markdown("<br><br><br>", unsafe_allow_html=True)

    # FEATURES
    c1, c2, c3 = st.columns(3)
    with c1:
        st.markdown("""
        <div class="feature-card">
            <div class="feature-icon">⚡</div>
            <div class="feature-title">Multi-Indicateurs</div>
            <div class="feature-desc">RSI, Bollinger, MACD, SMA 50/200 combinés pour une précision maximale.</div>
        </div>
        """, unsafe_allow_html=True)
    with c2:
        st.markdown("""
        <div class="feature-card">
            <div class="feature-icon">🧠</div>
            <div class="feature-title">Algorithme Hybride</div>
            <div class="feature-desc">Fusionne l'analyse technique quantitative et l'analyse de sentiment (News).</div>
        </div>
        """, unsafe_allow_html=True)
    with c3:
        st.markdown("""
        <div class="feature-card">
            <div class="feature-icon">💎</div>
            <div class="feature-title">Institutional Grade</div>
            <div class="feature-desc">Visualisation professionnelle via Plotly et flux de données Yahoo Finance.</div>
        </div>
        """, unsafe_allow_html=True)


def show_analysis_page():
    # HEADER DASHBOARD
    c_logo, c_title = st.columns([1, 4])

    with c_logo:
        logo_file = LOGOS.get(choix, "logo_esigelec.png")
        try:
            st.image(logo_file, use_container_width=True)
        except:
            st.write("")

    with c_title:
        title_color = "white" if is_dark_mode else "#2c3e50"
        st.markdown(f"""
        <div style="display: flex; align-items: center; height: 100%;">
            <h1 style='font-size: 3.5em; margin: 0; color: {title_color};'>
                SCAN EN COURS : <span style='color:#FF4B4B'>{choix.upper()}</span>
            </h1>
        </div>
        """, unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)

    with st.spinner('Calcul des indicateurs MACD & SMA50 en cours...'):
        df, fonda = get_data_and_consensus(ACTIONS[choix], period=selected_period)
        df = calculate_indicators(df)
        news, news_score_5 = get_fresh_news(choix)
        global_score, args = calculate_weighted_score(df, fonda, news_score_5)
        current_price = df['Close'].iloc[-1]

    # KPI
    kpi1, kpi3, kpi4 = st.columns(3)
    kpi1.metric("PRIX ACTUEL", f"{current_price:.2f} €", f"🎯 {fonda['target_price']} €")
    kpi3.metric("DIVIDENDE", f"{fonda['div_amt']} €")
    kpi4.metric("RENDEMENT", f"{fonda['yield'] * 100:.2f}%")

    st.markdown("<br>", unsafe_allow_html=True)

    # SCORE & DETAILS
    col_score, col_details = st.columns([1.5, 2.5])
    with col_score:
        st.markdown("""<div class="glass-container">""", unsafe_allow_html=True)
        st.markdown("### 🎯 SIGNAL IA GLOBAL")
        st.progress(global_score / 5)
        st.metric("SCORE DE CONFIANCE", f"{global_score} / 5.0")
        if global_score >= 3.8:
            st.success("🚀 ACHAT FORT (STRONG BUY)")
        elif global_score >= 3.0:
            st.info("↗️ ACCUMULER (BUY)")
        elif global_score <= 1.5:
            st.error("⛔ VENTE FORTE (STRONG SELL)")
        elif global_score <= 2.2:
            st.warning("↘️ ALLÉGER (SELL)")
        else:
            st.warning("⏸️ NEUTRE (HOLD)")
        st.markdown("</div>", unsafe_allow_html=True)

    with col_details:
        with st.expander("🔍 MATRICE DÉCISIONNELLE (DÉTAILS)", expanded=True):
            for a in args:
                if "Tech" in a:
                    icon = "📈"
                elif "Fonda" in a:
                    icon = "🏢"
                elif "Consensus" in a:
                    icon = "🧠"
                else:
                    icon = "ℹ️"
                st.write(f"{icon} {a}")

    st.markdown("<br>", unsafe_allow_html=True)

    # GRAPHIQUES (ADAPTATIF DARK/LIGHT)
    tab1, tab2 = st.tabs(["📈 CHARTING COMPLET (MACD/RSI)", "📰 FLUX D'ACTUALITÉS"])
    with tab1:
        # Création de 3 sous-graphiques : Prix, RSI, MACD
        fig = make_subplots(rows=3, cols=1, shared_xaxes=True,
                            row_heights=[0.6, 0.2, 0.2],
                            vertical_spacing=0.05)

        candle_up = '#00ff88' if is_dark_mode else '#007bff'
        candle_down = '#ff3131' if is_dark_mode else '#dc3545'

        # ROW 1 : PRIX + BOLLINGER + SMA 50/200
        fig.add_trace(
            go.Candlestick(x=df.index, open=df['Open'], close=df['Close'], high=df['High'], low=df['Low'], name="Prix",
                           increasing_line_color=candle_up, decreasing_line_color=candle_down), row=1, col=1)
        fig.add_trace(
            go.Scatter(x=df.index, y=df['Upper'], line=dict(color='rgba(128,128,128,0.3)', width=1), showlegend=False),
            row=1, col=1)
        fig.add_trace(
            go.Scatter(x=df.index, y=df['Lower'], line=dict(color='rgba(128,128,128,0.3)', width=1), fill='tonexty',
                       fillcolor='rgba(128,128,128,0.05)', name="Bollinger"), row=1, col=1)

        # SMA 200 (Cyan)
        if 'SMA_200' in df.columns and not df['SMA_200'].isnull().all():
            fig.add_trace(go.Scatter(x=df.index, y=df['SMA_200'], line=dict(color='#00f2ff', width=2), name="SMA 200"),
                          row=1, col=1)
        # SMA 50 (Jaune)
        if 'SMA_50' in df.columns and not df['SMA_50'].isnull().all():
            fig.add_trace(go.Scatter(x=df.index, y=df['SMA_50'], line=dict(color='#FFD700', width=1.5, dash='dash'),
                                     name="SMA 50"), row=1, col=1)

        # ROW 2 : RSI
        fig.add_trace(go.Scatter(x=df.index, y=df['RSI'], line=dict(color='#bc13fe', width=2), name="RSI"), row=2,
                      col=1)
        fig.add_hline(y=30, line_color="#00ff88", line_dash="dot", row=2, col=1)
        fig.add_hline(y=70, line_color="#ff3131", line_dash="dot", row=2, col=1)

        # ROW 3 : MACD
        # Histogramme
        colors_macd = ['#00ff88' if val >= 0 else '#ff3131' for val in (df['MACD'] - df['Signal_Line'])]
        fig.add_trace(
            go.Bar(x=df.index, y=(df['MACD'] - df['Signal_Line']), marker_color=colors_macd, name="MACD Hist"), row=3,
            col=1)
        # Lignes MACD
        fig.add_trace(go.Scatter(x=df.index, y=df['MACD'], line=dict(color='#2962FF', width=1.5), name="MACD"), row=3,
                      col=1)
        fig.add_trace(go.Scatter(x=df.index, y=df['Signal_Line'], line=dict(color='#FF6D00', width=1.5), name="Signal"),
                      row=3, col=1)

        fig.update_layout(height=800, xaxis_rangeslider_visible=False,
                          paper_bgcolor=graph_bg, plot_bgcolor=graph_bg,
                          font=dict(color="#aaa" if is_dark_mode else "#333"),
                          hovermode="x unified", legend=dict(bgcolor='rgba(0,0,0,0)'), template=graph_template)
        fig.update_xaxes(showgrid=True, gridwidth=1, gridcolor=graph_grid)
        fig.update_yaxes(showgrid=True, gridwidth=1, gridcolor=graph_grid)

        st.plotly_chart(fig, use_container_width=True)

    with tab2:
        if len(news) == 0:
            st.info("Aucun signal détecté sur les dernières 48h.")
        else:
            for n in news:
                title_col = "white" if is_dark_mode else "#2c3e50"
                st.markdown(f"""
                <div class="glass-container" style="padding: 15px; margin-bottom: 10px; display: flex; justify-content: space-between; align-items: center;">
                    <div><a href="{n['link']}" target="_blank" style="text-decoration: none; color: {title_col}; font-weight: bold; font-size: 1.1em;">{n['title']}</a><br><span style="color: #888; font-size: 0.8em;">📅 {n['date']}</span></div>
                    <div style="font-weight: bold; color: {'#00ff88' if n['color'] == 'green' else '#ff3131' if n['color'] == 'red' else '#888'};">{'POSITIF ▲' if n['color'] == 'green' else 'NÉGATIF ▼' if n['color'] == 'red' else 'NEUTRE ■'}</div>
                </div>
                """, unsafe_allow_html=True)


if st.session_state.page == 'home':
    show_home_page()
else:
    show_analysis_page()
