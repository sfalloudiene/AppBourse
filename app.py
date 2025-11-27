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
# 1. CONFIGURATION & STYLE 
# ==========================================
st.set_page_config(
    page_title="ESIG'Trade Terminal",
    layout="wide",
    page_icon="⚡",
    initial_sidebar_state="collapsed"
)

# --- CSS ULTRA PREMIUM ---
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600;800&display=swap');
    html, body, [class*="css"] { font-family: 'Inter', sans-serif; }

    /* FOND ANIMÉ */
    .stApp {
        background: radial-gradient(circle at center top, #1a1c2e 0%, #090a0f 100%);
        overflow-x: hidden;
    }

    /* ANIMATION D'ENTRÉE (FADE IN) */
    .element-container, .stMarkdown, .stMetric {
        animation: fadeInAnimation 1s ease-in-out;
    }

    @keyframes fadeInAnimation {
        0% { opacity: 0; transform: translateY(20px); }
        100% { opacity: 1; transform: translateY(0); }
    }

    /* BACKGROUND CHANDELIERS */
    .trading-bg-animation {
        position: fixed; top: 0; left: 0; width: 100%; height: 100%; z-index: -1; pointer-events: none;
        background-image: linear-gradient(rgba(255, 75, 75, 0.05) 1px, transparent 1px),
                          linear-gradient(90deg, rgba(255, 75, 75, 0.05) 1px, transparent 1px);
        background-size: 60px 60px; perspective: 1000px; transform: rotateX(60deg) scale(2); opacity: 0.3;
    }
    .candle {
        position: absolute; bottom: -150px; width: 6px; border-radius: 4px; opacity: 0.7;
        animation: floatUp cubic-bezier(0.4, 0.0, 0.2, 1) infinite; filter: blur(2px);
    }
    .c-green { background: #00ff88; box-shadow: 0 0 20px #00ff88; }
    .c-red { background: #ff3131; box-shadow: 0 0 20px #ff3131; }
    @keyframes floatUp {
        0% { transform: translateY(0) scale(1); opacity: 0; }
        10% { opacity: 0.9; }
        90% { opacity: 0.5; transform: translateY(-110vh) scale(3); }
        100% { transform: translateY(-130vh) scale(4); opacity: 0; }
    }

    /* TICKER TAPE CORRIGÉ */
    .ticker-wrap {
        position: fixed; top: 0; left: 0; width: 100%; overflow: hidden; height: 40px; background-color: rgba(0,0,0,0.8); border-bottom: 1px solid #333; z-index: 9999;
    }
    .ticker { display: inline-block; line-height: 40px; white-space: nowrap; padding-right: 100%; box-sizing: content-box; animation: ticker 40s linear infinite; }
    .ticker__item { display: inline-block; padding: 0 2rem; font-size: 0.9rem; color: #ccc; font-family: monospace; }
    .up { color: #00ff88; } .down { color: #ff3131; }

    @keyframes ticker { 
        0% { transform: translate3d(0, 0, 0); } 
        100% { transform: translate3d(-100%, 0, 0); } 
    }

    /* GLASSMORPHISM CARDS */
    .feature-card {
        background: rgba(255, 255, 255, 0.03); backdrop-filter: blur(10px);
        border: 1px solid rgba(255, 255, 255, 0.05); border-radius: 20px; padding: 30px; text-align: center; transition: transform 0.3s; height: 100%;
    }
    .feature-card:hover { transform: translateY(-10px); border-color: #FF4B4B; box-shadow: 0 10px 30px rgba(255, 75, 75, 0.2); }
    .feature-icon { font-size: 3em; margin-bottom: 15px; }
    .feature-title { font-weight: 800; font-size: 1.2em; color: white; margin-bottom: 10px; text-transform: uppercase; }
    .feature-desc { color: #aaa; font-size: 0.9em; }

    /* BOUTON RÉACTEUR */
    div.stButton > button:first-child {
        width: 100%; border-radius: 60px; font-weight: 900; height: 5em; font-size: 1.8em;
        text-transform: uppercase; letter-spacing: 3px; color: white; border: none;
        background: linear-gradient(135deg, #ff3131 0%, #ff914d 50%, #ff0f0f 100%);
        box-shadow: inset 0 0 20px rgba(255, 255, 255, 0.3), 0 0 30px rgba(255, 50, 50, 0.6);
        transition: all 0.4s; position: relative; overflow: hidden; margin-top: 20px;
    }
    div.stButton > button:first-child:hover { transform: scale(1.05); box-shadow: inset 0 0 30px rgba(255, 255, 255, 0.5), 0 0 60px rgba(255, 50, 50, 0.8); }

    /* METRIQUES DASHBOARD */
    div[data-testid="stMetric"], .glass-container {
        background: rgba(255, 255, 255, 0.03) !important;
        backdrop-filter: blur(12px); border-radius: 16px; border: 1px solid rgba(255, 255, 255, 0.1);
        box-shadow: 0 4px 30px rgba(0, 0, 0, 0.5); padding: 20px !important; transition: all 0.3s ease;
    }
    div[data-testid="stMetric"]:hover { transform: translateY(-5px); border: 1px solid rgba(255, 75, 75, 0.5); }
    div[data-testid="stMetricValue"] { font-size: 2.2em !important; font-weight: 800 !important; color: white; text-shadow: 0 0 10px rgba(255, 255, 255, 0.5); }

    /* CENTRAGE DES IMAGES */
    div[data-testid="stImage"] { display: flex; justify-content: center; align-items: center; width: 100%; }
    div[data-testid="stImage"] > img { object-fit: contain; max-width: 100%; }

    /* PROGRESS BAR PLASMA */
    div[data-testid="stProgress"] > div > div { background: linear-gradient(90deg, #ff3131, #ff914d, #00ff88); box-shadow: 0 0 15px rgba(255, 145, 77, 0.6); height: 12px; border-radius: 10px; }

</style>
""", unsafe_allow_html=True)

# Gestion navigation
if 'page' not in st.session_state: st.session_state.page = 'home'


def navigate_to(page): st.session_state.page = page; st.rerun()


# --- CONFIGURATION DES ACTIONS & LOGOS ---
ACTIONS = {
    "TotalEnergies": "TTE.PA",
    "Hermès": "RMS.PA",
    "Dassault Systèmes": "DSY.PA",
    "Sopra Steria": "SOP.PA",
    "Airbus": "AIR.PA"
}

LOGOS = {
    "TotalEnergies": "logo_total.png",
    "Hermès": "logo_hermes.png",
    "Dassault Systèmes": "logo_dassault.png",
    "Sopra Steria": "logo_sopra.png",
    "Airbus": "logo_airbus.png"
}


# ==========================================
# 2. LOGIQUE MÉTIER
# ==========================================
def get_data_and_consensus(ticker):
    stock = yf.Ticker(ticker)
    df = stock.history(period="2y")
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
                      'dividende', 'solide']
    negative_words = ['chute', 'baisse', 'perte', 'alerte', 'dette', 'procès', 'échec', 'sanction', 'démission',
                      'faible']
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
            color = "green"; score_mod = 1
        elif any(w in title_lower for w in negative_words):
            color = "red"; score_mod = -1
        raw_sentiment += score_mod;
        count += 1
        news_list.append({"title": title, "date": pub_date.strftime('%d/%m %H:%M'), "link": link, "color": color})
        if count >= 5: break
    if raw_sentiment > 0:
        final_news_score = 4 + (min(raw_sentiment, 2) * 0.5)
    elif raw_sentiment < 0:
        final_news_score = 1
    else:
        final_news_score = 2.5
    return news_list, final_news_score


def calculate_indicators(df):
    delta = df['Close'].diff()
    gain = (delta.where(delta > 0, 0)).rolling(14).mean();
    loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
    rs = gain / loss;
    df['RSI'] = 100 - (100 / (1 + rs))
    df['SMA_20'] = df['Close'].rolling(20).mean();
    df['STD_20'] = df['Close'].rolling(20).std()
    df['Upper'] = df['SMA_20'] + (2 * df['STD_20']);
    df['Lower'] = df['SMA_20'] - (2 * df['STD_20'])
    df['SMA_200'] = df['Close'].rolling(200).mean()
    return df


def calculate_weighted_score(df, fonda, news_score):
    last = df.iloc[-1];
    reasons = [];
    tech_points = 0
    if last['RSI'] < 35:
        tech_points += 1; reasons.append("Tech: RSI en zone de Survente (Rebond possible)")
    elif last['RSI'] > 70:
        tech_points -= 1; reasons.append("Tech: RSI en zone de Surachat (Risque de baisse)")
    else:
        tech_points += 0.5; reasons.append(f"Tech: RSI Neutre ({int(last['RSI'])}) - Zone stable")
    if last['Close'] < last['Lower']:
        tech_points += 1.5; reasons.append("Tech: Prix sous la Bollinger Basse (Signal d'Achat)")
    elif last['Close'] > last['Upper']:
        tech_points -= 1; reasons.append("Tech: Prix dépasse la Bollinger Haute (Signal de Vente)")
    else:
        tech_points += 0.5; reasons.append("Tech: Prix à l'intérieur des Bandes (Normal)")
    if last['Close'] > last['SMA_200']:
        tech_points += 1; reasons.append("Tech: Tendance de fond Haussière (> SMA200)")
    else:
        reasons.append("Tech: Tendance de fond Baissière (< SMA200)")
    tech_score_5 = (max(0, tech_points) / 4) * 5
    fund_points = 0
    if fonda['per'] > 0 and fonda['per'] < 15:
        fund_points += 1; reasons.append(f"Fonda: Action bon marché (PER {fonda['per']:.1f})")
    elif fonda['per'] > 30:
        fund_points -= 1; reasons.append(f"Fonda: Action chère (PER {fonda['per']:.1f})")
    else:
        reasons.append(f"Fonda: Valorisation Standard (PER {fonda['per']:.1f})")
    if fonda['yield'] > 0.03:
        fund_points += 1; reasons.append(f"Fonda: Bon rendement de dividende ({fonda['yield'] * 100:.1f}%)")
    else:
        reasons.append(f"Fonda: Rendement faible ou nul ({fonda['yield'] * 100:.1f}%)")
    fund_score_5 = (max(0, fund_points) / 2) * 5
    reasons.append(f"Consensus: Recommandation '{fonda['consensus_txt']}'")
    final_score = (
                (tech_score_5 * 0.40) + (fonda['consensus_score'] * 0.20) + (fund_score_5 * 0.20) + (news_score * 0.20))
    return round(final_score, 2), reasons


# ==========================================
# 3. INTERFACES
# ==========================================

def show_home_page():
    # --- TICKER TAPE SEULEMENT (PAS D'ANIMATION DE FOND) ---
    st.markdown("""
    <div class="ticker-wrap">
        <div class="ticker">
            <div class="ticker__item">BTC/USD <span class="up">▲ 65,400 $</span></div>
            <div class="ticker__item">ETH/USD <span class="up">▲ 3,500 $</span></div>
            <div class="ticker__item">TOTALENERGIES <span class="up">▲ 62.5 €</span></div>
            <div class="ticker__item">AIRBUS <span class="down">▼ 135.2 €</span></div>
            <div class="ticker__item">NVIDIA <span class="up">▲ 850 $</span></div>
            <div class="ticker__item">TESLA <span class="down">▼ 175 $</span></div>
            <div class="ticker__item">CAC 40 <span class="down">▼ 7,250</span></div>
            <div class="ticker__item">S&P 500 <span class="up">▲ 5,100</span></div>
            <div class="ticker__item">GOLD <span class="up">▲ 2,350 $</span></div>
            <div class="ticker__item">BTC/USD <span class="up">▲ 65,400 $</span></div>
            <div class="ticker__item">ETH/USD <span class="up">▲ 3,500 $</span></div>
            <div class="ticker__item">TOTALENERGIES <span class="up">▲ 62.5 €</span></div>
        </div>
    </div>
    <style>
        /* Animation Ticker Infinie */
        .ticker-wrap {
            position: fixed; top: 0; left: 0; width: 100%; overflow: hidden; height: 40px; 
            background-color: rgba(0,0,0,0.9); border-bottom: 1px solid #333; z-index: 9999;
        }
        .ticker { 
            display: inline-block; line-height: 40px; white-space: nowrap; 
            padding-right: 100%; box-sizing: content-box; 
            animation: ticker 40s linear infinite; /* BOUCLE INFINIE */
        }
        .ticker__item { 
            display: inline-block; padding: 0 2rem; font-size: 0.9rem; 
            color: #ccc; font-family: monospace; font-weight: bold;
        }
        .up { color: #00ff88; } 
        .down { color: #ff3131; }

        @keyframes ticker { 
            0% { transform: translate3d(0, 0, 0); } 
            100% { transform: translate3d(-100%, 0, 0); } 
        }
    </style>
    """, unsafe_allow_html=True)

    # Espace pour descendre le contenu sous le ticker
    st.markdown("<br><br><br><br><br>", unsafe_allow_html=True)

    # --- SECTION HERO (LOGO - TITRE - BOUTON ALIGNÉS) ---
    # Grille [1, 3, 1] pour un alignement parfait sur une ligne
    c_logo, c_hero, c_btn = st.columns([1, 3, 1], gap="medium")

    with c_logo:
        try:
            st.image("logo_esigelec.png", use_container_width=True)
        except:
            st.warning("⚠️ Logo")

    with c_hero:
        # Titre et Sous-titre au centre
        st.markdown("""
        <div style="text-align: center;">
            <h1 style='color: white; font-size: 4.5em; font-weight: 900; letter-spacing: -2px; margin-bottom: 5px; text-shadow: 0 0 40px rgba(255, 75, 75, 0.4); line-height: 1.1; text-transform: uppercase;'>
                ESIG'TRADE <span style="color: #FF4B4B;">PRO</span>
            </h1>
            <h3 style='color: #ccc; font-weight: 400; font-size: 1.2em; margin-top: 10px; letter-spacing: 2px; text-transform: uppercase;'>
                L'INTELLIGENCE ARTIFICIELLE AU SERVICE DE VOTRE ALPHA
            </h3>
        </div>
        """, unsafe_allow_html=True)

    with c_btn:
        # Bouton "Lancer" à droite, aligné verticalement avec un spacer
        st.markdown('<div style="height: 30px;"></div>', unsafe_allow_html=True)
        if st.button("🚀 LANCER LE TERMINAL"):
            navigate_to('analysis')

    st.markdown("<br><br><br>", unsafe_allow_html=True)

    # --- ARGUMENTS MARKETING (CARDS) ---
    c1, c2, c3 = st.columns(3)

    with c1:
        st.markdown("""
        <div class="feature-card">
            <div class="feature-icon">⚡</div>
            <div class="feature-title">Temps Réel</div>
            <div class="feature-desc">Connexion directe aux flux boursiers mondiaux pour une réactivité milliseconde.</div>
        </div>
        """, unsafe_allow_html=True)

    with c2:
        st.markdown("""
        <div class="feature-card">
            <div class="feature-icon">🧠</div>
            <div class="feature-title">Algorithmes IA</div>
            <div class="feature-desc">Analyse sémantique (NLP) et modèles quantitatifs pour prédire les tendances.</div>
        </div>
        """, unsafe_allow_html=True)

    with c3:
        st.markdown("""
        <div class="feature-card">
            <div class="feature-icon">💎</div>
            <div class="feature-title">Consensus Pro</div>
            <div class="feature-desc">Accédez aux stratégies des plus grandes banques d'investissement.</div>
        </div>
        """, unsafe_allow_html=True)

    st.markdown("<br><br><br>", unsafe_allow_html=True)
    st.markdown(
        "<p style='text-align: center; color: #555; font-size: 0.8em;'>© 2025 ESIGELEC QUANT LABS - INSTITUTIONAL GRADE ANALYTICS</p>",
        unsafe_allow_html=True)


def show_analysis_page():
    with st.sidebar:
        try:
            st.image("logo_esigelec.png", width=120)
        except:
            st.write("ESIGELEC")
        st.markdown("### ⚡ PARAMÈTRES ACTIF")
        choix = st.selectbox("", list(ACTIONS.keys()), label_visibility="collapsed")
        st.markdown("<br>", unsafe_allow_html=True)
        if st.button("⬅ DÉCONNEXION"): navigate_to('home')
        st.markdown("<br>", unsafe_allow_html=True)
        st.caption("⏱️ SYNC TEMPS RÉEL : 60s")
        st_autorefresh(interval=60 * 1000, key="marketupdater")

    # --- HEADER DASHBOARD (LOGO A GAUCHE, TITRE A DROITE) ---
    c_logo, c_title = st.columns([1, 4])

    with c_logo:
        logo_file = LOGOS.get(choix, "logo_esigelec.png")
        try:
            st.image(logo_file, use_container_width=True)
        except:
            st.write("")

    with c_title:
        st.markdown(f"""
        <div style="display: flex; align-items: center; height: 100%;">
            <h1 style='font-size: 3.5em; margin: 0; color: white;'>
                SCAN EN COURS : <span style='color:#FF4B4B'>{choix.upper()}</span>
            </h1>
        </div>
        """, unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)

    with st.spinner('Calcul des indicateurs en cours...'):
        df, fonda = get_data_and_consensus(ACTIONS[choix])
        df = calculate_indicators(df)
        news, news_score_5 = get_fresh_news(choix)
        global_score, args = calculate_weighted_score(df, fonda, news_score_5)
        current_price = df['Close'].iloc[-1]

    # KPI
    kpi1, kpi2, kpi3, kpi4 = st.columns(4)
    kpi1.metric("PRIX ACTUEL", f"{current_price:.2f} €", f"🎯 {fonda['target_price']} €")
    kpi2.metric("CONSENSUS PRO", fonda['consensus_txt'], delta=None)
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

    # GRAPHIQUES
    tab1, tab2 = st.tabs(["📈 CHARTING AVANCÉ", "📰 FLUX D'ACTUALITÉS (48H)"])
    with tab1:
        fig = make_subplots(rows=2, cols=1, shared_xaxes=True, row_heights=[0.7, 0.3])
        fig.add_trace(
            go.Candlestick(x=df.index, open=df['Open'], close=df['Close'], high=df['High'], low=df['Low'], name="Prix",
                           increasing_line_color='#00ff88', decreasing_line_color='#ff3131'), row=1, col=1)
        fig.add_trace(
            go.Scatter(x=df.index, y=df['Upper'], line=dict(color='rgba(255,255,255,0.1)', width=1), showlegend=False),
            row=1, col=1)
        fig.add_trace(
            go.Scatter(x=df.index, y=df['Lower'], line=dict(color='rgba(255,255,255,0.1)', width=1), fill='tonexty',
                       fillcolor='rgba(255,255,255,0.05)', name="Bollinger"), row=1, col=1)
        fig.add_trace(go.Scatter(x=df.index, y=df['SMA_200'], line=dict(color='#00f2ff', width=2), name="SMA 200"),
                      row=1, col=1)
        fig.add_trace(go.Scatter(x=df.index, y=df['RSI'], line=dict(color='#bc13fe', width=2), name="RSI"), row=2,
                      col=1)
        fig.add_hline(y=30, line_color="#00ff88", line_dash="dot", row=2, col=1);
        fig.add_hline(y=70, line_color="#ff3131", line_dash="dot", row=2, col=1)
        fig.update_layout(height=650, xaxis_rangeslider_visible=False, paper_bgcolor='rgba(0,0,0,0)',
                          plot_bgcolor='rgba(0,0,0,0)', font=dict(color='#aaa'), hovermode="x unified",
                          legend=dict(bgcolor='rgba(0,0,0,0)'))
        fig.update_xaxes(showgrid=True, gridwidth=1, gridcolor='rgba(255,255,255,0.1)');
        fig.update_yaxes(showgrid=True, gridwidth=1, gridcolor='rgba(255,255,255,0.1)');
        st.plotly_chart(fig, use_container_width=True)

    with tab2:
        if len(news) == 0:
            st.info("Aucun signal détecté sur les dernières 48h.")
        else:
            for n in news:
                st.markdown(f"""
                <div class="glass-container" style="padding: 15px; margin-bottom: 10px; display: flex; justify-content: space-between; align-items: center;">
                    <div><a href="{n['link']}" target="_blank" style="text-decoration: none; color: white; font-weight: bold; font-size: 1.1em;">{n['title']}</a><br><span style="color: #888; font-size: 0.8em;">📅 {n['date']}</span></div>
                    <div style="font-weight: bold; color: {'#00ff88' if n['color'] == 'green' else '#ff3131' if n['color'] == 'red' else '#888'};">{'POSITIF ▲' if n['color'] == 'green' else 'NÉGATIF ▼' if n['color'] == 'red' else 'NEUTRE ■'}</div>
                </div>
                """, unsafe_allow_html=True)


if st.session_state.page == 'home':
    show_home_page()
else:
    show_analysis_page()
