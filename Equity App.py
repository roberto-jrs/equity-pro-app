import streamlit as st
import pandas as pd
import yfinance as yf
import plotly.express as px
from finnhub import Client
from datetime import datetime
import pytz 
from streamlit_autorefresh import st_autorefresh

# --- CONFIGURAÇÃO ---
st.set_page_config(page_title="Equity Pro - Terminal", layout="wide", page_icon="▣")

# (30.000 milissegundos = 30 segundos)
st_autorefresh(interval=30000, key="equity_global_refresh")

FINNHUB_KEY = "d6p1sfhr01qk3chijap0d6p1sfhr01qk3chijapg" 
finnhub_client = Client(api_key=FINNHUB_KEY)

# --- INICIALIZAÇÃO DA MEMÓRIA ---
if 'live_data' not in st.session_state:
    st.session_state.live_data = {}
if 'moeda_save' not in st.session_state:
    st.session_state.moeda_save = "USD ($)"
if 'invest_save' not in st.session_state:
    st.session_state.invest_save = 0.00
if 'setor_save' not in st.session_state:
    st.session_state.setor_save = "Todos"
if 'sel_idioma' not in st.session_state:
    st.session_state.sel_idioma = "Português (BR)"

# --- DICIONÁRIO DE TRADUÇÃO ---
idiomas = {
    "English": {
        "titulo_idioma": "LANGUAGE",
        "config": "PERSONAL SETTINGS",
        "moeda": "Display Currency:",
        "capital": "Simulation Capital:",
        "filtro": "Filter by Sector:",
        "fuso": "User Timezone:",
        "todos": "All",
        "status_on": "STOCK MARKET OPEN (NYSE/NASDAQ)",
        "status_off": "STOCK MARKET CLOSED (SHOWING HISTORICAL DATA)",
        "alocacao": "📊 Asset Allocation",
        "terminal": "💡 Stock Terminal",
        "monitor": "Monitoring assets in sector:",
        "info_cambio": "The current exchange rate for conversion is",
        "info_detalhe": "All purchase fraction calculations are processed in real time based on the capital of",
        "compra": "Simulated quantity:",
        "atualizar": "⟲ Refresh Global Values",
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
        "fuso": "Fuso Horário do Usuário:",
        "todos": "Todos",
        "status_on": "MERCADO DE AÇÕES ABERTO (NYSE/NASDAQ)",
        "status_off": "MERCADO DE AÇÕES FECHADO (EXIBINDO DADOS HISTÓRICOS)",
        "alocacao": "📊 Alocação de Ativos",
        "terminal": "💡 Terminal de Ações",
        "monitor": "Monitorando ativos do setor:",
        "info_cambio": "O câmbio atual para conversão é de",
        "info_detalhe": "Todos os cálculos de frações de compra são processados em tempo real com base no capital de",
        "compra": "Quantidade simulada:",
        "atualizar": "⟲ Atualizar Valores Globais",
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
        "fuso": "Zona Horaria:",
        "todos": "Todos",
        "status_on": "MERCADO DE VALORES ABIERTO (NYSE/NASDAQ)",
        "status_off": "MERCADO DE VALORES CERRADO (MOSTRANDO DATOS HISTÓRICOS)",
        "alocacao": "📊 Asignación de Activos",
        "terminal": "💡 Terminal de Acciones",
        "monitor": "Monitoreando activos del sector:",
        "info_cambio": "El tipo de cambio actual para la conversión es",
        "info_detalhe": "Todos los cálculos de fracciones de compra se procesan en tiempo real según el capital de",
        "compra": "Cantidad simulada:",
        "atualizar": "⟲ Atualizar Valores Globales",
        "historico": "HISTÓRICO",
        "subtitulo": "Estratégia y Claridad para el Mercado Global",
        "ultima_at": "Última atualização:"
    }
}

def mudar_idioma():
    st.session_state.sel_idioma = st.session_state.idioma_temp

# --- CSS PERSONALIZADO ---
st.markdown("""
    <style>
        button[data-testid="stSidebarCollapsedControl"]::after {
            content: "⚙️";
            font-size: 26px !important;
            display: block !important;
        }
        .refresh-text { font-size: 0.8rem; color: #888; text-align: right; margin-bottom: 0; }
        .stContainer { border: 1px solid #333; transition: transform 0.2s; border-radius: 10px; }
        .stContainer:hover { border-color: #007bff; transform: translateY(-3px); }
        [data-testid="stMetricValue"] { font-size: 1.8rem; }
    </style>
""", unsafe_allow_html=True)

# --- SIDEBAR (CONFIGURAÇÕES) ---
with st.sidebar:
    st.header(idiomas[st.session_state.sel_idioma]["titulo_idioma"])
    st.selectbox("Select:", list(idiomas.keys()), index=list(idiomas.keys()).index(st.session_state.sel_idioma), key="idioma_temp", on_change=mudar_idioma)
    t = idiomas[st.session_state.sel_idioma]
    st.divider()
    st.header(t["config"])
    fusos_lista = ['America/Sao_Paulo', 'America/New_York', 'UTC']
    sel_fuso = st.selectbox(t["fuso"], fusos_lista, index=0)
    moeda = st.selectbox(t["moeda"], ["USD ($)", "BRL (R$)", "EUR (€)"], key="moeda_selector")
    st.session_state.moeda_save = moeda
    investimento = st.number_input(t["capital"], min_value=0.0, value=st.session_state.invest_save, step=500.0, key="invest_selector")
    st.session_state.invest_save = investimento

    ativos_db = [
        {"ticker": "AAPL", "nome": "Apple Inc.", "setor": "Tecnologia"},
        {"ticker": "NVDA", "nome": "NVIDIA Corp.", "setor": "Tecnologia"},
        {"ticker": "MSFT", "nome": "Microsoft Corp.", "setor": "Tecnologia"},
        {"ticker": "TSLA", "nome": "Tesla, Inc.", "setor": "Automotivo"},
        {"ticker": "AMZN", "nome": "Amazon.com", "setor": "Varejo Digital"},
        {"ticker": "META", "nome": "Meta Platforms", "setor": "Tecnologia"},
        {"ticker": "BINANCE:BTCUSDT", "nome": "Bitcoin", "setor": "Cripto"}
    ]
    setores_lista = sorted(list(set([a['setor'] for a in ativos_db])))
    filtro_setor = st.selectbox(t["filtro"], [t["todos"]] + setores_lista, key="setor_selector")
