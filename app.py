import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots

# ==========================================
# 1. CONFIGURATION & DONNÉES STATIQUES
# ==========================================
st.set_page_config(page_title="Trading Algo - Ingénieur Fi", layout="wide")

# Dictionnaire des actions (Ticker Yahoo Finance)
ACTIONS = {
    "TotalEnergies": "TTE.PA",
    "Hermès": "RMS.PA",
    "Dassault Systèmes": "DSY.PA",
    "Sopra Steria": "SOP.PA",
    "Airbus": "AIR.PA"
}

# Données fondamentales simulées (Tu peux les ajuster ici ou via API plus tard)
# PER (Price Earning Ratio) moyen secteur ~15
FONDAMENTAUX = {
    "TotalEnergies": {"per": 7.5, "yield": 0.05, "secteur_per": 10},
    "Hermès": {"per": 48.0, "yield": 0.01, "secteur_per": 25},  # Luxe se paie cher
    "Dassault Systèmes": {"per": 35.0, "yield": 0.005, "secteur_per": 30},
    "Sopra Steria": {"per": 12.0, "yield": 0.02, "secteur_per": 18},
    "Airbus": {"per": 25.0, "yield": 0.015, "secteur_per": 22}
}


# ==========================================
# 2. FONCTIONS DE CALCUL (MOTEUR)
# ==========================================
def get_data(ticker):
    # On prend 2 ans pour bien voir les moyennes mobiles
    df = yf.Ticker(ticker).history(period="2y")
    return df


def calculate_indicators(df):
    # A. RSI (14 jours)
    delta = df['Close'].diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
    rs = gain / loss
    df['RSI'] = 100 - (100 / (1 + rs))

    # B. Moyennes Mobiles (SMA)
    df['SMA_50'] = df['Close'].rolling(window=50).mean()  # Tendance moyen terme
    df['SMA_200'] = df['Close'].rolling(window=200).mean()  # Tendance long terme

    return df


def generate_signal(df, symbol):
    last = df.iloc[-1]
    fonda = FONDAMENTAUX[symbol]
    score = 0
    reasons = []

    # --- ANALYSE TECHNIQUE ---
    # 1. RSI
    if last['RSI'] < 30:
        score += 2
        reasons.append("Technique: RSI en zone de survente (Opportunité d'achat)")
    elif last['RSI'] > 70:
        score -= 2
        reasons.append("Technique: RSI en zone de surachat (Risque de baisse)")

    # 2. Tendance (Prix vs SMA 200)
    if last['Close'] > last['SMA_200']:
        score += 1
        reasons.append("Technique: Tendance long terme haussière (Prix > SMA200)")
    else:
        score -= 1
        reasons.append("Technique: Tendance long terme baissière")

    # --- ANALYSE FONDAMENTALE ---
    # 3. Valorisation (PER)
    if fonda['per'] < fonda['secteur_per']:
        score += 1
        reasons.append(f"Fondamental: Action sous-évaluée (PER {fonda['per']} < {fonda['secteur_per']})")
    elif fonda['per'] > fonda['secteur_per'] * 1.5:
        score -= 1
        reasons.append("Fondamental: Action très chère (PER élevé)")

    return score, reasons


# ==========================================
# 3. INTERFACE UTILISATEUR (STREAMLIT)
# ==========================================
# Sidebar (Menu de gauche)
st.sidebar.title("paramètres")
choix_nom = st.sidebar.selectbox("Choisir l'action", list(ACTIONS.keys()))
ticker = ACTIONS[choix_nom]

st.title(f"📊 Analyse Financière : {choix_nom}")

# Chargement
with st.spinner('Chargement des données Yahoo Finance...'):
    df = get_data(ticker)
    df = calculate_indicators(df)
    current_price = df['Close'].iloc[-1]
    current_rsi = df['RSI'].iloc[-1]

# Affichage des métriques clés en haut
col1, col2, col3, col4 = st.columns(4)
col1.metric("Prix Actuel", f"{current_price:.2f} €", f"{df['Close'].iloc[-1] - df['Close'].iloc[-2]:.2f} €")
col2.metric("RSI (14)", f"{current_rsi:.1f}", delta_color="off")
col3.metric("PER Est.", FONDAMENTAUX[choix_nom]['per'])
col4.metric("Rendement", f"{FONDAMENTAUX[choix_nom]['yield'] * 100}%")

# --- GRAPHIQUES INTERACTIFS (Plotly) ---
st.subheader("Analyse Technique")

# Création du graphique bougies + RSI
fig = make_subplots(rows=2, cols=1, shared_xaxes=True,
                    vertical_spacing=0.03, row_heights=[0.7, 0.3])

# Graphique 1 : Chandeliers + Moyennes Mobiles
fig.add_trace(go.Candlestick(x=df.index, open=df['Open'], high=df['High'],
                             low=df['Low'], close=df['Close'], name='Prix'), row=1, col=1)
fig.add_trace(go.Scatter(x=df.index, y=df['SMA_50'], line=dict(color='orange', width=1), name='SMA 50'), row=1, col=1)
fig.add_trace(go.Scatter(x=df.index, y=df['SMA_200'], line=dict(color='blue', width=1), name='SMA 200'), row=1, col=1)

# Graphique 2 : RSI
fig.add_trace(go.Scatter(x=df.index, y=df['RSI'], line=dict(color='purple', width=2), name='RSI'), row=2, col=1)
# Lignes 30 et 70 pour le RSI
fig.add_hline(y=70, line_dash="dot", row=2, col=1, line_color="red")
fig.add_hline(y=30, line_dash="dot", row=2, col=1, line_color="green")

fig.update_layout(xaxis_rangeslider_visible=False, height=600)
st.plotly_chart(fig, use_container_width=True)

# --- CONCLUSION & ALGO ---
st.subheader("🤖 Verdict de l'Algorithme")

score, reasons = generate_signal(df, choix_nom)

# Logique d'affichage visuel du résultat
if score >= 2:
    st.success(f"### 🚀 RECOMMANDATION : ACHAT FORT (Score: {score})")
elif score >= 1:
    st.info(f"### ✅ RECOMMANDATION : ACCUMULER / ACHAT PRUDENT (Score: {score})")
elif score <= -2:
    st.error(f"### 🔻 RECOMMANDATION : VENTE FORTE (Score: {score})")
elif score <= -1:
    st.warning(f"### ⚠️ RECOMMANDATION : ALLÉGER / VENTE (Score: {score})")
else:
    st.write(f"### ⏸️ RECOMMANDATION : NEUTRE / CONSERVER (Score: {score})")

with st.expander("Voir les détails de l'analyse"):
    for reason in reasons:
        if "Technique" in reason:
            st.write(f"📈 {reason}")
        else:
            st.write(f"🏢 {reason}")