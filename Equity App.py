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
from streamlit_autorefresh import st_autorefresh

# --- CONFIGURAÇÃO ---
st.set_page_config(page_title="Equity Pro - Terminal", layout="wide", page_icon="▣")

# 1. AUTO-REFRESH (Garante a atualização a cada 60s)
st_autorefresh(interval=60000, key="equity_refresh_counter")

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
if 'sel_idioma' not in st.session_state:
    st.session_state.sel_idioma = "Português (BR)" # Inicia em PT por padrão se preferir

# --- DICIONÁRIO DE TRADUÇÃO ---
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
        "subtitulo": "Strategy and Clarity for the Global Market",
        "ultima_at": "Last update:"
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
        "subtitulo": "Estratégia e Clareza para o Mercado Global",
        "ultima_at": "Última atualização:"
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
        "atualizar": "▣ Atualizar Flujo Global",
        "historico": "HISTÓRICO",
        "subtitulo": "Estrategia y Claridad para el Mercado Global",
        "ultima_at": "Última actualización:"
    }
}

def mudar_idioma():
    st.session_state.sel_idioma = st.session_state.idioma_temp

# --- CSS PARA CUSTOMIZAÇÃO ---
st.markdown("""
    <style>
        .refresh-text { font-size: 0.8rem; color: #888; text-align: right; margin-bottom: 0; }
        [data-testid="stSidebarNav"]::before {
            content: "⚙️ SETTINGS / OPÇÕES";
            margin-left: 20px; margin-top: 20px;
            font-size: 1.1rem; font-weight: bold; color: #7a7a7a;
        }
    </style>
""", unsafe_allow_html=True)

# --- BARRA LATERAL (LÓGICA DE IDIOMA PRIMEIRO) ---
with st.sidebar:
    st.header(idiomas[st.session_state.sel_idioma]["titulo_idioma"])
    st.selectbox(
        "Select / Selecione:", 
        list(idiomas.keys()), 
        index=list(idiomas.keys()).index(st.session_state.sel_idioma),
        key="idioma_temp",
        on_change=mudar_idioma
    )
    # ATUALIZA A VARIÁVEL 't' PARA O RESTANTE DO CÓDIGO
    t = idiomas[st.session_state.sel_idioma]
    st.divider()
    
    st.header(t["config"])
    moeda = st.selectbox(t["moeda"], ["USD ($)", "BRL (R$)", "EUR (€)"], key="moeda_selector")
    st.session_state.moeda_save = moeda
    investimento = st.number_input(t["capital"], min_value=0.0, value=st.session_state.invest_save, step=500.0, key="invest_selector")
    st.session_state.invest_save = investimento
    
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
    setores_lista = sorted(list(set([a['setor'] for a in ativos_db])))
    filtro_setor = st.selectbox(t["filtro"], [t["todos"]] + setores_lista, key="setor_selector")
    st.session_state.setor_save = filtro_setor

# --- FUNÇÕES DE APOIO ---
def get_now_br():
    return datetime.now(pytz.utc).astimezone(pytz.timezone('America/Sao_Paulo'))

@st.cache_data(ttl=60)
def get_safe_quote(ticker):
    try: return finnhub_client.quote(ticker)
    except: return {"c": 0, "pc": 0}

def check_market_status():
    ny_now = datetime.now(pytz.timezone('America/New_York'))
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

# --- CABEÇALHO ---
render_logo_jr()

c_top1, c_top2 = st.columns([3, 1])
with c_top2:
    if st.button(t["atualizar"], use_container_width=True):
        st.rerun()
    # HORÁRIO AJUSTADO PARA BRASIL
    st.markdown(f"<p class='refresh-text'>{t['ultima_at']} {get_now_br().strftime('%H:%M:%S')}</p>", unsafe_allow_html=True)

status_label, status_color, status_text = check_market_status()
st.markdown(f"<div style='background-color: {status_color}; padding: 8px; border-radius: 4px; text-align: center; color: white; font-weight: bold; margin-bottom: 20px; font-size: 0.8rem;'>STATUS: {status_label} | {status_text}</div>", unsafe_allow_html=True)

# --- GRÁFICO E TERMINAL ---
col_stats1, col_stats2 = st.columns([1, 2])
with col_stats1:
    st.subheader(t["alocacao"])
    df_pizza = pd.DataFrame(ativos_db)
    if filtro_setor != t["todos"]: df_pizza = df_pizza[df_pizza['setor'] == filtro_setor]
    fig = px.pie(df_pizza, names='setor', hole=0.4, template="plotly_dark", color_discrete_sequence=px.colors.qualitative.Set2)
    fig.update_layout(margin=dict(l=0, r=0, t=10, b=0), height=230, showlegend=False)
    st.plotly_chart(fig, use_container_width=True, config={'displaylogo': False})

with col_stats2:
    st.subheader(t["terminal"])
    st.write(f"{t['monitor']} **{filtro_setor}**")
    taxa_exibida = brl_rate if "BRL" in moeda else (eur_rate if "EUR" in moeda else 1.0)
    simbolo_moeda = "BRL" if "BRL" in moeda else ("EUR" if "EUR" in moeda else "USD")
    st.info(f"{t['info_cambio']} **1 USD = {taxa_exibida:.2f} {simbolo_moeda}**. {t['info_detalhe']} {moeda}.")

st.divider()
# --- CARDS DE ATIVOS ---
ativos_f = ativos_db if filtro_setor == t["todos"] else [a for a in ativos_db if a['setor'] == filtro_setor]
cols = st.columns(3)

def converter(val):
    if "BRL" in moeda: return val * brl_rate, "R$"
    if "EUR" in moeda: return val * eur_rate, "€"
    return val, "$"

for i, ativo in enumerate(ativos_f):
    with cols[i % 3]:
        ticker = ativo['ticker']
        data = st.session_state.live_data.get(ticker)
        q = get_safe_quote(ticker)
        fech_ant = q.get('pc', 0)
        
        # SÓ MOSTRA HISTÓRICO SE MERCADO OFF
        label_status = ""
        if status_label == "OFF": label_status = t["historico"]
        elif data: label_status = "LIVE"

        price = data['price'] if data else q.get('c', 0)
        time_ref = data['time'] if data else "--:--"
        var = ((price - fech_ant) / fech_ant * 100) if fech_ant > 0 else 0
        p_conv, simb = converter(price)
        
        with st.container(border=True):
            ch, cs = st.columns([2, 1])
            ch.markdown(f"**{ativo['nome']}**")
            if label_status:
                cs.markdown(f"<span style='background:{'#26a69a' if label_status=='LIVE' else '#546e7a'}; color:white; padding:2px 6px; border-radius:4px; font-size:9px; font-weight:bold;'>{label_status}</span>", unsafe_allow_html=True)
            st.markdown(f"### {simb} {p_conv:,.2f}")
            st.markdown(f"<p style='color:{'#26a69a' if var >= 0 else '#ef5350'}; font-weight:bold; margin-top:-15px;'>{'▲' if var >= 0 else '▼'} {var:.2f}%</p>", unsafe_allow_html=True)
            taxa_conv = brl_rate if "BRL" in moeda else (eur_rate if "EUR" in moeda else 1)
            st.write(f"{t['compra']} **{(investimento / taxa_conv) / price if price > 0 else 0:.5f}**")
            st.caption(f"Code: `{ticker}` | Ref: {time_ref}")
