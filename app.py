import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import feedparser
from datetime import datetime, timedelta
import time

# ==========================================
# 1. CONFIGURATION
# ==========================================
st.set_page_config(page_title="Algo Trading - Weighted Model", layout="wide", page_icon="💎")

# Liste nettoyée (Sans LVMH ni BNP)
ACTIONS = {
    "TotalEnergies": "TTE.PA",
    "Hermès": "RMS.PA",
    "Dassault Systèmes": "DSY.PA",
    "Sopra Steria": "SOP.PA",
    "Airbus": "AIR.PA"
}


# ==========================================
# 2. FONCTIONS DONNÉES & CONSENSUS
# ==========================================
def get_data_and_consensus(ticker):
    """
    Récupère historique + infos fondamentales (Dividende/Rendement) + CONSENSUS
    """
    stock = yf.Ticker(ticker)

    # 1. Historique
    df = stock.history(period="2y")

    # Récupération du dernier prix connu (pour le calcul du rendement)
    if not df.empty:
        last_price = df['Close'].iloc[-1]
    else:
        last_price = 0

    # 2. Infos Fondamentales & Consensus
    try:
        info = stock.info

        # Consensus
        rec_key = info.get('recommendationKey', 'none')
        target_price = info.get('targetMeanPrice', 0)

        # Mapping Consensus
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

        # Fondamentaux
        per = info.get('trailingPE') or info.get('forwardPE', 0)

        # --- CORRECTION DU RENDEMENT ---
        # On récupère le montant en Euros (ex: 3.50)
        div_rate = info.get('dividendRate')

        # Si Yahoo ne donne pas le montant, on essaie 'trailingAnnualDividendRate'
        if div_rate is None:
            div_rate = info.get('trailingAnnualDividendRate', 0)

        # CALCUL MANUEL DU RENDEMENT (Plus fiable)
        # Rendement = Dividende / Prix Actuel
        if div_rate and last_price > 0:
            div_yield = div_rate / last_price
        else:
            # Si calcul impossible, fallback sur la donnée Yahoo
            div_yield = info.get('dividendYield', 0)
            if div_yield is None: div_yield = 0
            if div_yield > 1: div_yield = div_yield / 100

        fonda = {
            "per": per,
            "yield": div_yield,  # Format décimal (ex: 0.05 pour 5%)
            "div_amt": div_rate,  # Montant en Euros
            "consensus_txt": rec_key.replace('_', ' ').upper(),
            "consensus_score": consensus_score,
            "target_price": target_price
        }
    except Exception as e:
        # print(f"Erreur data: {e}") # Debug
        fonda = {"per": 0, "yield": 0, "div_amt": 0, "consensus_txt": "INCONNU", "consensus_score": 2.5,
                 "target_price": 0}

    return df, fonda


def get_fresh_news(company_name):
    """ Récupère les news de moins de 24h """
    query = company_name.replace(" ", "+")
    rss_url = f"https://news.google.com/rss/search?q={query}+bourse+finance&hl=fr&gl=FR&ceid=FR:fr"
    feed = feedparser.parse(rss_url)

    news_list = []
    positive_words = ['hausse', 'bondit', 'record', 'achat', 'surperforme', 'contrat', 'succès', 'approbation',
                      'dividende']
    negative_words = ['chute', 'baisse', 'perte', 'alerte', 'dette', 'procès', 'échec', 'sanction', 'démission']
    time_threshold = datetime.now() - timedelta(days=1)

    raw_sentiment = 0
    count = 0

    for entry in feed.entries:
        try:
            pub_date = datetime.fromtimestamp(time.mktime(entry.published_parsed))
        except:
            continue

        if pub_date < time_threshold: continue  # Filtre 24h

        title = entry.title
        link = entry.link

        color = "grey"
        score_mod = 0
        title_lower = title.lower()

        if any(w in title_lower for w in positive_words):
            color = "green"
            score_mod = 1
        elif any(w in title_lower for w in negative_words):
            color = "red"
            score_mod = -1

        raw_sentiment += score_mod
        count += 1

        news_list.append({"title": title, "date": pub_date.strftime('%H:%M'), "link": link, "color": color})
        if count >= 5: break

    if raw_sentiment > 0:
        final_news_score = 4 + (min(raw_sentiment, 2) * 0.5)
    elif raw_sentiment < 0:
        final_news_score = 1
    else:
        final_news_score = 2.5

    return news_list, final_news_score


# ==========================================
# 3. INDICATEURS TECHNIQUES
# ==========================================
def calculate_indicators(df):
    # RSI
    delta = df['Close'].diff()
    gain = (delta.where(delta > 0, 0)).rolling(14).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
    rs = gain / loss
    df['RSI'] = 100 - (100 / (1 + rs))

    # Bollinger
    df['SMA_20'] = df['Close'].rolling(20).mean()
    df['STD_20'] = df['Close'].rolling(20).std()
    df['Upper'] = df['SMA_20'] + (2 * df['STD_20'])
    df['Lower'] = df['SMA_20'] - (2 * df['STD_20'])

    # SMA 200
    df['SMA_200'] = df['Close'].rolling(200).mean()

    return df


# ==========================================
# 4. ALGORITHME DE PONDÉRATION
# ==========================================
def calculate_weighted_score(df, fonda, news_score):
    last = df.iloc[-1]
    reasons = []

    # --- A. Score TECHNIQUE (40%) ---
    tech_points = 0

    # 1. RSI
    if last['RSI'] < 35:
        tech_points += 1
        reasons.append("Tech: RSI bas (Rebond possible)")
    elif last['RSI'] > 70:
        tech_points -= 1
        reasons.append("Tech: RSI trop haut (Risque)")
    else:
        tech_points += 0.5

    # 2. Bollinger
    if last['Close'] < last['Lower']:
        tech_points += 1.5
        reasons.append("Tech: Prix sous Bollinger (Achat fort)")
    elif last['Close'] > last['Upper']:
        tech_points -= 1
        reasons.append("Tech: Prix sur Bollinger (Vente)")
    else:
        tech_points += 0.5

    # 3. Tendance
    if last['Close'] > last['SMA_200']:
        tech_points += 1
        reasons.append("Tech: Tendance long terme haussière")

    tech_score_5 = (max(0, tech_points) / 4) * 5

    # --- B. Score FONDAMENTAL (20%) ---
    fund_points = 0
    if fonda['per'] > 0 and fonda['per'] < 15:
        fund_points += 1
    elif fonda['per'] > 30:
        fund_points -= 1

    if fonda['yield'] > 0.03: fund_points += 1

    fund_score_5 = (max(0, fund_points) / 2) * 5

    # --- C. CALCUL FINAL ---
    final_score = (
            (tech_score_5 * 0.40) +
            (fonda['consensus_score'] * 0.20) +
            (fund_score_5 * 0.20) +
            (news_score * 0.20)
    )

    return round(final_score, 2), tech_score_5, fonda['consensus_score'], reasons


# ==========================================
# 5. INTERFACE
# ==========================================
st.sidebar.title("Paramètres")
choix = st.sidebar.selectbox("Action", list(ACTIONS.keys()))

st.title(f"🧠 Analyse Avancée : {choix}")

with st.spinner('Analyse multi-factorielle en cours...'):
    df, fonda = get_data_and_consensus(ACTIONS[choix])
    df = calculate_indicators(df)
    news, news_score_5 = get_fresh_news(choix)

    global_score, tech_sc, cons_sc, args = calculate_weighted_score(df, fonda, news_score_5)

    current_price = df['Close'].iloc[-1]

# --- DASHBOARD DU HAUT (MODIFIÉ) ---
c1, c2, c3, c4 = st.columns(4)

# Colonne 1 : Prix
c1.metric("Prix", f"{current_price:.2f} €", f"Cible: {fonda['target_price']} €")

# Colonne 2 : Consensus
c2.metric("Consensus Analystes", fonda['consensus_txt'], f"{cons_sc}/5")

# Colonne 3 : Dividende (Montant en €) - MODIFIÉ
c3.metric("Dividende (Annuel)", f"{fonda['div_amt']} €")

# Colonne 4 : Rendement (%) - MODIFIÉ
c4.metric("Rendement", f"{fonda['yield'] * 100:.2f}%")

# --- JAUGES DE SCORE ---
st.markdown("### 🎯 Score de Confiance Global")
st.progress(global_score / 5)
st.write(f"**NOTE FINALE : {global_score} / 5.0**")

if global_score >= 3.8:
    st.success("### ✅ ACHAT FORT (STRONG BUY)")
elif global_score >= 3.0:
    st.info("### ↗️ ACHAT PRUDENT (ACCUMULATE)")
elif global_score <= 1.5:
    st.error("### ⛔ VENTE FORTE")
elif global_score <= 2.2:
    st.warning("### ↘️ VENTE / ALLÉGER")
else:
    st.write("### ⏸️ NEUTRE / ATTENTE")

# --- DÉTAILS ---
col_g, col_n = st.columns([2, 1])

with col_g:
    st.subheader("Analyse Technique")
    fig = make_subplots(rows=2, cols=1, shared_xaxes=True, row_heights=[0.7, 0.3])

    # Prix + BB
    fig.add_trace(
        go.Candlestick(x=df.index, open=df['Open'], close=df['Close'], high=df['High'], low=df['Low'], name="Prix"),
        row=1, col=1)
    fig.add_trace(go.Scatter(x=df.index, y=df['Upper'], line=dict(color='gray', width=1), showlegend=False), row=1,
                  col=1)
    fig.add_trace(go.Scatter(x=df.index, y=df['Lower'], line=dict(color='gray', width=1), fill='tonexty',
                             fillcolor='rgba(200,200,200,0.1)', name="Bollinger"), row=1, col=1)

    # RSI
    fig.add_trace(go.Scatter(x=df.index, y=df['RSI'], line=dict(color='purple'), name="RSI"), row=2, col=1)
    fig.add_hline(y=30, line_color="green", row=2, col=1)
    fig.add_hline(y=70, line_color="red", row=2, col=1)

    fig.update_layout(height=600, xaxis_rangeslider_visible=False)
    st.plotly_chart(fig, width="stretch")

with col_n:
    st.subheader("Actualités (< 24h)")
    if len(news) == 0:
        st.caption("Aucune news détectée depuis 24h.")

    for n in news:
        st.markdown(f"**{n['date']}** - :{n['color']}[{n['title']}]")
        st.markdown(f"[Lire]({n['link']})")
        st.divider()

    st.write("---")
    st.write("**Facteurs de Décision :**")
    for a in args:
        st.caption(f"{a}")
