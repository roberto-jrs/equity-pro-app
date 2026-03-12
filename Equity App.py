import streamlit as st
import pandas as pd
import websocket
import json
import threading
import time
from finnhub import Client
from datetime import datetime
import pytz 
import yfinance as yf
import plotly.express as px

# --- CONFIGURAÇÃO ---
st.set_page_config(page_title="Equity Pro - Terminal", layout="wide", page_icon="▣")

FINNHUB_KEY = "d6p1sfhr01qk3chijap0d6p1sfhr01qk3chijapg" 
finnhub_client = Client(api_key=FINNHUB_KEY)

# --- INICIALIZAÇÃO DA MEMÓRIA (SESSION STATE) ---
if 'live_data' not in st.session_state:
    st.session_state.live_data = {}
if 'moeda_save' not in st.session_state:
    st.session_state.moeda_save = "USD ($)"
if 'invest_save' not in st.session_state:
    st.session_state.invest_save = 0.00
if 'setor_save' not in st.session_state:
    st.session_state.setor_save = "Todos"

# --- DICIONÁRIO DE TRADUÇÃO (TRILÍNGUE COMPLETO) ---
idiomas = {
    "English": {
        "titulo_idioma": "LANGUAGE",
        "config": "PERSONAL SETTINGS",
        "moeda": "Display Currency:",
        "capital": "Simulation Capital:",
        "filtro": "Filter by Sector:",
        "todos": "All",
        "status_on": "STOCK MARKET OPEN (NYSE/NASDAQ)",
        "status_off": "STOCK MARKET CLOSED (SHOWING HISTORICAL DATA)",
        "alocacao": "📊 Asset Allocation",
        "terminal": "💡 Stock Terminal",
        "monitor": "Monitoring assets in sector:",
        "info_cambio": "The current exchange rate for conversion is",
        "info_detalhe": "All purchase fraction calculations are processed in real time based on the capital of",
        "compra": "Simulated quantity:",
        "atualizar": "▣ Refresh Global Flow",
        "historico": "HISTORICAL",
        "subtitulo": "Strategy and Clarity for the Global Market"
    },
    "Português (BR)": {
        "titulo_idioma": "IDIOMA",
        "config": "CONFIGURAÇÕES PESSOAIS",
        "moeda": "Moeda de Exibição:",
        "capital": "Capital para Simulação:",
        "filtro": "Filtrar por Setor:",
        "todos": "Todos",
        "status_on": "MERCADO DE AÇÕES ABERTO (NYSE/NASDAQ)",
        "status_off": "MERCADO DE AÇÕES FECHADO (EXIBINDO DADOS HISTÓRICOS)",
        "alocacao": "📊 Alocação de Ativos",
        "terminal": "💡 Terminal de Ações",
        "monitor": "Monitorando ativos do setor:",
        "info_cambio": "O câmbio atual para conversão é de",
        "info_detalhe": "Todos os cálculos de frações de compra são processados em tempo real com base no capital de",
        "compra": "Quantidade simulada:",
        "atualizar": "▣ Atualizar Fluxo Global",
        "historico": "HISTÓRICO",
        "subtitulo": "Estratégia e Clareza para o Mercado Global"
    },
    "Español": {
        "titulo_idioma": "IDIOMA",
        "config": "CONFIGURACIÓN PERSONAL",
        "moeda": "Moneda de Visualización:",
        "capital": "Capital de Simulación:",
        "filtro": "Filtrar por Sector:",
        "todos": "Todos",
        "status_on": "MERCADO DE VALORES ABIERTO (NYSE/NASDAQ)",
        "status_off": "MERCADO DE VALORES CERRADO (MOSTRANDO DATOS HISTÓRICOS)",
        "alocacao": "📊 Asignación de Activos",
        "terminal": "💡 Terminal de Acciones",
        "monitor": "Monitoreando activos del sector:",
        "info_cambio": "El tipo de cambio actual para la conversión es",
        "info_detalhe": "Todos los cálculos de fracciones de compra se procesan en tiempo real según el capital de",
        "compra": "Cantidad simulada:",
        "atualizar": "▣ Actualizar Flujo Global",
        "historico": "HISTÓRICO",
        "subtitulo": "Estrategia y Claridad para el Mercado Global"
    }
}

# --- FUNÇÃO PARA ATUALIZAR O IDIOMA IMEDIATAMENTE ---
def mudar_idioma():
    st.session_state.sel_idioma = st.session_state.idioma_temp

# --- INICIALIZAÇÃO DO ESTADO DO IDIOMA ---
if 'sel_idioma' not in st.session_state:
    st.session_state.sel_idioma = "English"

# --- BARRA LATERAL (LÓGICA CORRIGIDA) ---
with st.sidebar:
    # 1. Pegamos a tradução ATUAL da memória para o título
    t_topo = idiomas[st.session_state.sel_idioma]
    
    # 2. Desenhamos o Título (Agora ele sempre virá da memória atualizada)
    st.header(t_topo["titulo_idioma"])
    
    # 3. O Seletor com a "mágica" do on_change
    # Quando você muda aqui, ele chama a função mudar_idioma e limpa o atraso
    sel_idioma = st.selectbox(
        "Select / Selecione:", 
        list(idiomas.keys()), 
        index=list(idiomas.keys()).index(st.session_state.sel_idioma),
        key="idioma_temp",
        on_change=mudar_idioma
    )
    
    # 4. Atualizamos a variável 't' para o resto do código abaixo
    t = idiomas[st.session_state.sel_idioma]
    
    st.divider()

# --- PROTEÇÃO E DADOS ---
@st.cache_data(ttl=60)
def get_safe_quote(ticker):
    try: return finnhub_client.quote(ticker)
    except: return {"c": 0, "pc": 0}

def check_market_status():
    ny_tz = pytz.timezone('America/New_York')
    ny_now = datetime.now(ny_tz)
    is_weekday = ny_now.weekday() < 5 
    is_hours = ny_now.hour >= 9 and (ny_now.hour < 16 or (ny_now.hour == 16 and ny_now.minute == 0))
    if ny_now.hour == 9 and ny_now.minute < 30: is_hours = False
    return ("ON", "#26a69a", t["status_on"]) if (is_weekday and is_hours) else ("OFF", "#ef5350", t["status_off"])

@st.cache_data(ttl=3600)
def get_rates():
    try:
        usd_brl = yf.Ticker("USDBRL=X").fast_info['last_price']
        usd_eur = yf.Ticker("EUR=X").fast_info['last_price']
        return usd_brl, usd_eur
    except: return 5.15, 0.92

brl_rate, eur_rate = get_rates()

# --- WEBSOCKET ---
def on_message(ws, message):
    msg = json.loads(message)
    if msg['type'] == 'trade':
        for trade in msg['data']:
            st.session_state.live_data[trade['s']] = {
                'price': trade['p'], 'time': datetime.now().strftime('%H:%M:%S'), 'type': 'LIVE'
            }

def run_ws(symbols):
    def on_open(ws):
        for s in symbols: ws.send(f'{{"type":"subscribe","symbol":"{s}"}}')
    ws = websocket.WebSocketApp(f"wss://ws.finnhub.io?token={FINNHUB_KEY}", on_message=on_message, on_open=on_open)
    ws.run_forever()

ativos_db = [
    {"ticker": "AAPL", "nome": "Apple Inc.", "setor": "Tecnologia"},
    {"ticker": "NVDA", "nome": "NVIDIA Corp.", "setor": "Tecnologia"},
    {"ticker": "MSFT", "nome": "Microsoft Corp.", "setor": "Tecnologia"},
    {"ticker": "GOOGL", "nome": "Alphabet Inc.", "setor": "Tecnologia"},
    {"ticker": "TSLA", "nome": "Tesla, Inc.", "setor": "Automotivo"},
    {"ticker": "AMZN", "nome": "Amazon.com", "setor": "Varejo Digital"},
    {"ticker": "META", "nome": "Meta Platforms", "setor": "Tecnologia"},
    {"ticker": "V", "nome": "Visa Inc.", "setor": "Financeiro"},
    {"ticker": "JPM", "nome": "JPMorgan Chase", "setor": "Financeiro"},
    {"ticker": "KO", "nome": "Coca-Cola Co.", "setor": "Consumo"},
    {"ticker": "DIS", "nome": "Walt Disney Co.", "setor": "Entretenimento"},
    {"ticker": "NFLX", "nome": "Netflix, Inc.", "setor": "Entretenimento"},
    {"ticker": "BINANCE:BTCUSDT", "nome": "Bitcoin", "setor": "Cripto"},
    {"ticker": "BINANCE:ETHUSDT", "nome": "Ethereum", "setor": "Cripto"}
]

if 'ws_started' not in st.session_state:
    threading.Thread(target=run_ws, args=([a['ticker'] for a in ativos_db],), daemon=True).start()
    st.session_state.ws_started = True

# --- CONFIGURAÇÕES PESSOAIS (COM MEMÓRIA) ---
with st.sidebar:
    st.header(t["config"])
    
    # Moeda com memória
    moedas_lista = ["USD ($)", "BRL (R$)", "EUR (€)"]
    idx_moeda = moedas_lista.index(st.session_state.moeda_save)
    moeda = st.selectbox(t["moeda"], moedas_lista, index=idx_moeda, key="moeda_selector")
    st.session_state.moeda_save = moeda

    # Investimento com memória
    investimento = st.number_input(t["capital"], min_value=0.0, value=st.session_state.invest_save, step=500.0, key="invest_selector")
    st.session_state.invest_save = investimento

    # Filtro de setor com memória
    setores_lista = sorted(list(set([a['setor'] for a in ativos_db])))
    opcoes_setor = [t["todos"]] + setores_lista
    idx_setor = 0 
    if st.session_state.setor_save in opcoes_setor:
        idx_setor = opcoes_setor.index(st.session_state.setor_save)
    
    filtro_setor = st.selectbox(t["filtro"], opcoes_setor, index=idx_setor, key="setor_selector")
    st.session_state.setor_save = filtro_setor

# --- LÓGICA DE INTERFACE ---
def converter(val):
    if "BRL" in moeda: return val * brl_rate, "R$"
    if "EUR" in moeda: return val * eur_rate, "€"
    return val, "$"

def render_logo_jr():
    st.markdown(f"""
        <div style="display: flex; align-items: center; margin-bottom: 10px;">
            <svg width="40" height="40" viewBox="0 0 100 100" fill="none" xmlns="http://www.w3.org/2000/svg">
                <path d="M10 10H90V90H10V10Z" stroke="#4a4a4a" stroke-width="8"/>
                <path d="M30 30H70V70H30V30Z" stroke="#7a7a7a" stroke-width="6"/>
                <path d="M50 10V30" stroke="#4a4a4a" stroke-width="6"/><path d="M50 70V90" stroke="#4a4a4a" stroke-width="6"/>
                <path d="M10 50H30" stroke="#4a4a4a" stroke-width="6"/><path d="M70 50H90" stroke="#4a4a4a" stroke-width="6"/>
                <path d="M50 50L85 15" stroke="#007bff" stroke-width="10" stroke-linecap="round"/>
                <path d="M70 15H85V30" stroke="#007bff" stroke-width="10" stroke-linecap="round" stroke-linejoin="round"/>
            </svg>
            <h1 style="margin: 0; margin-left: 15px; font-weight: 800; letter-spacing: -1px;">EQUITY PRO</h1>
        </div>
        <p style="margin-top: -10px; color: #666; font-size: 0.9rem;">{t["subtitulo"]}</p>
    """, unsafe_allow_html=True)

render_logo_jr()
status_label, status_color, status_text = check_market_status()
st.markdown(f"<div style='background-color: {status_color}; padding: 8px; border-radius: 4px; text-align: center; color: white; font-weight: bold; margin-bottom: 20px; font-size: 0.8rem;'>STATUS: {status_label} | {status_text}</div>", unsafe_allow_html=True)
st.markdown("---")

col_stats1, col_stats2 = st.columns([1, 2])
with col_stats1:
    st.subheader(t["alocacao"])
    df_pizza = pd.DataFrame(ativos_db)
    if filtro_setor != t["todos"]: df_pizza = df_pizza[df_pizza['setor'] == filtro_setor]
    fig = px.pie(df_pizza, names='setor', hole=0.4, template="plotly_dark", color_discrete_sequence=px.colors.qualitative.Set2)
    fig.update_layout(margin=dict(l=0, r=0, t=10, b=0), height=230, showlegend=False)
    st.plotly_chart(fig, use_container_width=True)

with col_stats2:
    st.subheader(t["terminal"])
    st.write(f"{t['monitor']} **{filtro_setor}**")
    taxa_exibida = brl_rate if "BRL" in moeda else (eur_rate if "EUR" in moeda else 1.0)
    simbolo_moeda = "BRL" if "BRL" in moeda else ("EUR" if "EUR" in moeda else "USD")
    st.info(f"{t['info_cambio']} **1 USD = {taxa_exibida:.2f} {simbolo_moeda}**. {t['info_detalhe']} {moeda}.")

st.divider()
ativos_f = ativos_db if filtro_setor == t["todos"] else [a for a in ativos_db if a['setor'] == filtro_setor]
cols = st.columns(3)

for i, ativo in enumerate(ativos_f):
    with cols[i % 3]:
        ticker = ativo['ticker']
        data = st.session_state.live_data.get(ticker)
        q = get_safe_quote(ticker)
        fech_ant = q.get('pc', 0)
        label_status = "LIVE" if data else t["historico"]
        if not data: data = {'price': q.get('c', 0), 'time': '--:--', 'type': label_status}
        var = ((data['price'] - fech_ant) / fech_ant * 100) if fech_ant > 0 else 0
        p_c, simb = converter(data['price'])
        with st.container(border=True):
            ch, cs = st.columns([2, 1])
            ch.markdown(f"**{ativo['nome']}**")
            cs.markdown(f"<span style='background:{'#26a69a' if data['type']=='LIVE' else '#546e7a'}; color:white; padding:2px 6px; border-radius:4px; font-size:9px; font-weight:bold;'>{label_status}</span>", unsafe_allow_html=True)
            st.markdown(f"### {simb} {p_c:,.2f}")
            st.markdown(f"<p style='color:{'#26a69a' if var >= 0 else '#ef5350'}; font-weight:bold; margin-top:-15px;'>{'▲' if var >= 0 else '▼'} {var:.2f}%</p>", unsafe_allow_html=True)
            taxa_conversao = brl_rate if "BRL" in moeda else (eur_rate if "EUR" in moeda else 1)
            inv_usd = investimento / taxa_conversao
            st.write(f"{t['compra']} **{inv_usd / data['price'] if data['price'] > 0 else 0:.5f}**")
            st.caption(f"Code: `{ticker}` | Ref: {data['time']}")

st.divider()
st.button(t["atualizar"], on_click=st.rerun)