import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import feedparser  # Pour lire les flux RSS de Google News

# ==========================================
# 1. CONFIGURATION & DONNÉES DE SECOURS
# ==========================================
st.set_page_config(page_title="Terminal Ingénieur Financier", layout="wide", page_icon="📈")

# Dictionnaire des actions (Tickers Yahoo Finance)
ACTIONS = {
    "TotalEnergies": "TTE.PA",
    "Hermès": "RMS.PA",
    "Dassault Systèmes": "DSY.PA",
    "Sopra Steria": "SOP.PA",
    "Airbus": "AIR.PA"
}

# Données de "Fallback" (Sauvegarde) si l'API Yahoo ne répond pas
BACKUP_DATA = {
    "TTE.PA": {"per": 7.5, "yield": 0.05, "secteur_per": 11},
    "RMS.PA": {"per": 48.0, "yield": 0.01, "secteur_per": 25},
    "DSY.PA": {"per": 35.0, "yield": 0.005, "secteur_per": 30},
    "SOP.PA": {"per": 12.0, "yield": 0.02, "secteur_per": 18},
    "AIR.PA": {"per": 25.0, "yield": 0.015, "secteur_per": 22}
}


# ==========================================
# 2. FONCTIONS D'ACQUISITION DE DONNÉES
# ==========================================
def get_historical_data(ticker):
    """Télécharge l'historique des prix sur 2 ans"""
    stock = yf.Ticker(ticker)
    df = stock.history(period="2y")
    return df


def get_fundamental_data(ticker):
    """
    Récupère les fondamentaux en temps réel avec Failover & Correction d'échelle.
    """
    stock = yf.Ticker(ticker)
    try:
        info = stock.info
        per = info.get('trailingPE') or info.get('forwardPE')
        div_yield = info.get('dividendYield')

        if per is None or div_yield is None:
            raise ValueError("Données manquantes")

        # --- CORRECTIF RENDEMENT ---
        # Si Yahoo renvoie "6.08" (pourcentage brut), on convertit en "0.0608" (décimal)
        if div_yield > 1:
            div_yield = div_yield / 100

        return {
            "per": round(per, 2),
            "yield": div_yield,
            "secteur_per": BACKUP_DATA[ticker]["secteur_per"],
            "source": "🟢 API Live"
        }
    except Exception:
        data = BACKUP_DATA[ticker]
        data["source"] = "🟠 Mode Secours (Offline)"
        return data


def get_market_news(company_name):
    """
    Récupère les news Google Actualités et fait une analyse de sentiment basique.
    """
    query = company_name.replace(" ", "+")
    rss_url = f"https://news.google.com/rss/search?q={query}+bourse&hl=fr&gl=FR&ceid=FR:fr"

    feed = feedparser.parse(rss_url)
    news_list = []
    sentiment_score = 0

    # Mots-clés simples pour la démo
    positive_words = ['hausse', 'bondit', 'record', 'profit', 'achat', 'surperforme', 'dividende', 'contrat', 'succès']
    negative_words = ['chute', 'baisse', 'perte', 'recule', 'crise', 'alerte', 'dette', 'procès', 'échec']

    for entry in feed.entries[:5]:  # Top 5 news
        title = entry.title
        link = entry.link
        published = entry.published

        sentiment = "Neutre"
        color = "grey"

        title_lower = title.lower()
        if any(word in title_lower for word in positive_words):
            sentiment = "Positif"
            color = "green"
            sentiment_score += 1
        elif any(word in title_lower for word in negative_words):
            sentiment = "Négatif"
            color = "red"
            sentiment_score -= 1

        news_list.append({
            "title": title,
            "link": link,
            "date": published,
            "sentiment": sentiment,
            "color": color
        })

    return news_list, sentiment_score


# ==========================================
# 3. MOTEUR DE CALCUL (INDICATEURS)
# ==========================================
def calculate_indicators(df):
    # 1. Momentum (Demande du prof)
    df['Momentum'] = df['Close'].diff(10)

    # 2. Volume Moyen (Demande du prof)
    df['Vol_Moyen'] = df['Volume'].rolling(window=20).mean()

    # 3. RSI
    delta = df['Close'].diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
    rs = gain / loss
    df['RSI'] = 100 - (100 / (1 + rs))

    # 4. SMA (Moyennes Mobiles)
    df['SMA_200'] = df['Close'].rolling(window=200).mean()

    # 5. Bandes de Bollinger
    df['SMA_20'] = df['Close'].rolling(window=20).mean()
    df['STD_20'] = df['Close'].rolling(window=20).std()
    df['Bollinger_Upper'] = df['SMA_20'] + (2 * df['STD_20'])
    df['Bollinger_Lower'] = df['SMA_20'] - (2 * df['STD_20'])

    return df


def generate_signal(df, fonda_data, news_score):
    """Algorithme de décision global"""
    last = df.iloc[-1]
    score = 0
    reasons = []

    # --- ANALYSE TECHNIQUE ---
    if last['Momentum'] > 0:
        score += 1
        reasons.append("Technique : Momentum Positif (Hausse)")

    if last['Volume'] > last['Vol_Moyen']:
        score += 0.5
        reasons.append("Technique : Volume fort (Mouvement validé)")

    if last['RSI'] < 30:
        score += 1
        reasons.append("Technique : RSI en survente (Opportunité d'achat)")
    elif last['RSI'] > 70:
        score -= 1
        reasons.append("Technique : RSI en surachat (Attention)")

    if last['Close'] < last['Bollinger_Lower']:
        score += 1.5
        reasons.append("Technique : Prix sous Bollinger Basse (Rebond probable)")
    elif last['Close'] > last['Bollinger_Upper']:
        score -= 1
        reasons.append("Technique : Prix dépasse Bollinger Haute (Surchauffe)")

    if last['Close'] > last['SMA_200']:
        score += 0.5
        reasons.append("Technique : Tendance de fond haussière (> SMA200)")

    # --- ANALYSE FONDAMENTALE ---
    if fonda_data['per'] < fonda_data['secteur_per']:
        score += 1
        reasons.append(f"Fondamental : Action sous-évaluée (PER {fonda_data['per']} < Secteur)")

    if fonda_data['yield'] > 0.03:
        score += 1
        reasons.append(f"Fondamental : Bon rendement ({fonda_data['yield'] * 100:.2f}%)")

    # --- ANALYSE SENTIMENT (NEWS) ---
    if news_score > 0:
        score += 0.5
        reasons.append("Sentiment : Actualité favorable (Mots-clés positifs)")
    elif news_score < 0:
        score -= 0.5
        reasons.append("Sentiment : Actualité inquiétante (Mots-clés négatifs)")

    return score, reasons


# ==========================================
# 4. INTERFACE GRAPHIQUE (STREAMLIT)
# ==========================================
# Sidebar
st.sidebar.title("Paramètres")
choix_nom = st.sidebar.selectbox("Choisir l'action à analyser", list(ACTIONS.keys()))
ticker = ACTIONS[choix_nom]

st.title(f"📊 Analyse Financière : {choix_nom}")

# Chargement
with st.spinner('Analyse des données en cours...'):
    df = get_historical_data(ticker)
    df = calculate_indicators(df)
    fonda = get_fundamental_data(ticker)
    news_list, news_score = get_market_news(choix_nom)

    current_price = df['Close'].iloc[-1]
    var_day = df['Close'].iloc[-1] - df['Close'].iloc[-2]

# Métriques du haut
col1, col2, col3, col4 = st.columns(4)
col1.metric("Prix Actuel", f"{current_price:.2f} €", f"{var_day:.2f} €")
col2.metric("PER (Yahoo)", f"{fonda['per']}")
col3.metric("Rendement", f"{fonda['yield'] * 100:.2f}%")
col4.metric("Source Données", fonda['source'])

# --- GRAPHIQUES ---
st.subheader("Analyse Technique Multi-Indicateurs")

fig = make_subplots(rows=3, cols=1, shared_xaxes=True,
                    vertical_spacing=0.05,
                    row_heights=[0.5, 0.25, 0.25],
                    subplot_titles=("Prix, Moyennes Mobiles & Bollinger", "Momentum", "RSI"))

# 1. PRIX + BB + SMA
fig.add_trace(go.Scatter(x=df.index, y=df['Bollinger_Upper'], line=dict(color='gray', width=1), showlegend=False),
              row=1, col=1)
fig.add_trace(go.Scatter(x=df.index, y=df['Bollinger_Lower'], line=dict(color='gray', width=1), fill='tonexty',
                         fillcolor='rgba(128, 128, 128, 0.1)', name='Bandes Bollinger'), row=1, col=1)
fig.add_trace(
    go.Candlestick(x=df.index, open=df['Open'], high=df['High'], low=df['Low'], close=df['Close'], name='Prix'), row=1,
    col=1)
fig.add_trace(go.Scatter(x=df.index, y=df['SMA_200'], line=dict(color='blue', width=1), name='SMA 200'), row=1, col=1)

# 2. MOMENTUM
colors_mom = ['green' if val > 0 else 'red' for val in df['Momentum']]
fig.add_trace(go.Bar(x=df.index, y=df['Momentum'], marker_color=colors_mom, name='Momentum'), row=2, col=1)

# 3. RSI
fig.add_trace(go.Scatter(x=df.index, y=df['RSI'], line=dict(color='purple'), name='RSI'), row=3, col=1)
fig.add_hline(y=70, line_dash="dot", row=3, col=1, line_color="red")
fig.add_hline(y=30, line_dash="dot", row=3, col=1, line_color="green")

fig.update_layout(xaxis_rangeslider_visible=False, height=800, showlegend=True, margin=dict(l=20, r=20, t=40, b=20))
st.plotly_chart(fig, width="stretch")

# --- ACTUALITÉS ---
st.markdown("---")
col_news, col_verdict = st.columns([1, 1])

with col_news:
    st.subheader(f"📰 Actualités : {choix_nom}")
    if not news_list:
        st.info("Aucune actualité récente trouvée.")
    for item in news_list:
        with st.expander(f"{item['date'][0:16]} - {item['title']}"):
            st.write(f"Sentiment: :{item['color']}[{item['sentiment']}]")
            st.markdown(f"[Lire l'article]({item['link']})")

# --- VERDICT ---
score_final, arguments = generate_signal(df, fonda, news_score)

with col_verdict:
    st.subheader("🤖 Verdict de l'Algorithme")
    st.metric("Score de Confiance", f"{score_final} / 7")

    if score_final >= 3.5:
        st.success("### 🚀 RECOMMANDATION : ACHAT")
    elif score_final <= 0:
        st.error("### 🔻 RECOMMANDATION : VENTE")
    else:
        st.warning("### ⏸️ RECOMMANDATION : NEUTRE")

    st.write("**Facteurs de décision :**")
    for arg in arguments:
        if "Technique" in arg:
            st.caption(f"📈 {arg}")
        elif "Fondamental" in arg:
            st.caption(f"🏢 {arg}")
        else:
            st.caption(f"📰 {arg}")
