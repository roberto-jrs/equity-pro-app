import streamlit as st
import pandas as pd
import websocket
import json
import threading
import time  # Este é o módulo de tempo do sistema
from finnhub import Client
from datetime import datetime, time as dt_time # Importamos o 'time' do datetime com apelido
import pytz 
import yfinance as yf
import plotly.express as px
from streamlit_autorefresh import st_autorefresh

# --- 1. CONFIGURAÇÃO DE PÁGINA ---
st.set_page_config(page_title="Equity Pro - Terminal", layout="wide", page_icon="▣")

# --- 2. DEFINIÇÃO DAS FUNÇÕES ---

def check_market_status():
    """Verifica se a bolsa de NY está aberta."""
    # 1. Pega a hora atual em NY
    ny_now = datetime.now(pytz.timezone('America/New_York'))
    
    # 2. Verifica se é dia de semana (0=Segunda, 4=Sexta)
    is_weekday = ny_now.weekday() < 5 
    
    # 3. Define os horários de abertura e fechamento
    current_time = ny_now.time()
    market_open = dt_time(9, 30)
    market_close = dt_time(16, 0)

    # 4. Verifica se está dentro do intervalo
    is_hours = market_open <= current_time < market_close
    
    if is_weekday and is_hours:
        return "ON", "#26a69a"
    else:
        return "OFF", "#ef5350"

# --- 3. LÓGICA DE REFRESH CONDICIONAL ---
status_mercado, cor_status = check_market_status()

if status_mercado == "ON":
    # Atualiza a cada 30 segundos se aberto
    st_autorefresh(interval=30000, key="equity_global_refresh")
else:
    # Atualiza a cada 10 minutos se fechado (apenas para manter o app vivo)
    st_autorefresh(interval=600000, key="equity_idle_refresh")

# --- 4. CONFIGURAÇÕES DA API E MEMÓRIA ---
FINNHUB_KEY = "d6p1sfhr01qk3chijap0d6p1sfhr01qk3chijapg" 
finnhub_client = Client(api_key=FINNHUB_KEY)

if 'sel_idioma' not in st.session_state:
    st.session_state.sel_idioma = "English"
if 'setor_selector' not in st.session_state:
    st.session_state.setor_selector = "All"
if 'moeda_save' not in st.session_state:
    st.session_state.moeda_save = "USD ($)"
if 'invest_save' not in st.session_state:
    st.session_state.invest_save = 0.00
if 'sel_fuso' not in st.session_state:
    st.session_state.sel_fuso = 'America/New_York'
if 'live_data' not in st.session_state:
    st.session_state.live_data = {}
if 'show_all_charts' not in st.session_state:
    st.session_state.show_all_charts = False

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
        "ultima_at": "Last update:",
        "grafico_h": "Historical Chart",
        "btn_expandir": "📈 Expand Charts",
        "btn_recolher": "📈 Collapse Charts",
        "help_graficos": "Expand/Collapse all charts"
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
        "ultima_at": "Última atualização:",
        "grafico_h": "Gráfico Histórico",
        "btn_expandir": "📈 Expandir Gráficos",
        "btn_recolher": "📈 Recolher Gráficos",
        "help_graficos": "Expandir/Recolher todos os gráficos"
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
        "subtitulo": "Estrategia y Claridad para el Mercado Global",
        "ultima_at": "Última actualización:",
        "grafico_h": "Gráfico Histórico",
        "btn_expandir": "📈 Expandir Gráficos",
        "btn_recolher": "📈 Contraer Gráficos",
        "help_graficos": "Expandir/Contraer todos los gráficos"
    }
}

def mudar_idioma():
    st.session_state.sel_idioma = st.session_state.idioma_temp

# --- CSS PERSONALIZADO ---
st.markdown("""
    <style>
        button[data-testid="stSidebarCollapsedControl"] svg { display: none !important; }
        button[data-testid="stSidebarCollapsedControl"]::after {
            content: "⚙️";
            font-size: 26px !important;
            display: block !important;
        }
        .refresh-text { font-size: 0.8rem; color: #888; text-align: right; margin-bottom: 0; }
        header[data-testid="stHeader"] { background-color: rgba(0,0,0,0) !important; }
    </style>
""", unsafe_allow_html=True)

def get_safe_quote(ticker):
    try:
        # O yfinance busca PETR4.SA, AAPL, BTC-USD, etc.
        data = yf.Ticker(ticker)
        # Usamos fast_info para ser rápido no seu monitor 4k
        info = data.fast_info
        
        preco = info['last_price']
        abertura = info['open']
        
        # Se não houver preço de abertura, evitamos erro de divisão por zero
        variacao = ((preco - abertura) / abertura) * 100 if abertura else 0
        
        return {
            "price": preco, 
            "change": variacao,
            "status": "success"
        }
    except Exception as e:
        # Se der erro (ex: ticker errado), retorna 0.0 para não quebrar o app
        return {"price": 0.0, "change": 0.0, "status": "error"}

# --- SIDEBAR ---
with st.sidebar:
    st.header(idiomas[st.session_state.sel_idioma]["titulo_idioma"])
    st.selectbox(
        "Select / Selecione:", 
        list(idiomas.keys()), 
        index=list(idiomas.keys()).index(st.session_state.sel_idioma),
        key="idioma_temp",
        on_change=mudar_idioma
    )
    t = idiomas[st.session_state.sel_idioma]

    # LÓGICA DE FILTRO DINÂMICA
    
    if 'meus_ativos' not in st.session_state:
        st.session_state.meus_ativos = [
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
    
    st.divider()
    
    # --- NOVO: CAMPO DE BUSCA ---
    st.header("BUSCAR ATIVOS")
    busca = st.text_input("Ticker ou Nome (Ex: PETR4, AMZN):")
    if busca:
        res = finnhub_client.symbol_lookup(busca)
        if res['count'] > 0:
            # Pega os 10 primeiros resultados para não poluir
            opcoes = {item['symbol']: item['description'] for item in res['result'][:10]}
            escolha = st.selectbox("Resultado:", list(opcoes.keys()), format_func=lambda x: f"{x} - {opcoes[x]}")
            
            # APENAS UM BOTÃO COM A LÓGICA DO .SA
            if st.button("➕ Adicionar ao Terminal"):
                ticker_escolhido = escolha
                
                # MÁGICA: Se for brasileiro (ex: PETR4, VALE3), adicionamos o .SA para o motor de preços
                if len(ticker_escolhido) <= 6 and not ticker_escolhido.endswith(".SA") and ":" not in ticker_escolhido:
                    ticker_escolhido = f"{ticker_escolhido}.SA"
                
                novo = {"ticker": ticker_escolhido, "nome": opcoes[escolha], "setor": "Personalizado"}
                
                # Adiciona à lista da sessão
                st.session_state.meus_ativos.append(novo)
                st.success(f"{ticker_escolhido} adicionado com sucesso!")
                time.sleep(0.5)
                st.rerun()
    st.divider()
    
    st.header(t["config"])
    fusos_lista = ['America/New_York', 'America/Sao_Paulo', 'Europe/London', 'Europe/Paris', 'Asia/Tokyo', 'UTC']
    st.selectbox(t["fuso"], fusos_lista, key='sel_fuso')
    st.selectbox(t["moeda"], ["USD ($)", "BRL (R$)", "EUR (€)"], key="moeda_save")
    st.number_input(t["capital"], min_value=0.0, step=500.0, key="invest_save")

    st.divider()
    setores_lista = sorted(list(set([a['setor'] for a in st.session_state.meus_ativos])))
    filtro_setor = st.selectbox(t["filtro"], [t["todos"]] + setores_lista, key="setor_selector")

# --- FUNÇÕES DE DADOS ---
def get_now_local():
    return datetime.now(pytz.utc).astimezone(pytz.timezone(st.session_state.sel_fuso))

@st.cache_data(ttl=5) # Reduzido para 5s para acompanhar o refresh
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

# --- INTERFACE ---
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

c_top1, c_top2 = st.columns([3, 1])
with c_top2:
    col_btn1, col_btn2 = st.columns(2)
    with col_btn1:
        if st.button(t["atualizar"], use_container_width=True):
            st.rerun()
    with col_btn2:
        label_btn = t["btn_expandir"] if not st.session_state.show_all_charts else t["btn_recolher"]
        
        if st.button(label_btn, use_container_width=True, help=t["help_graficos"]):
            st.session_state.show_all_charts = not st.session_state.show_all_charts
            st.rerun()
            
    st.markdown(f"<p class='refresh-text'>{t['ultima_at']} {get_now_local().strftime('%H:%M:%S')}</p>", unsafe_allow_html=True)

status_label, status_color, status_text = check_market_status()
st.markdown(f"<div style='background-color: {status_color}; padding: 8px; border-radius: 4px; text-align: center; color: white; font-weight: bold; margin-bottom: 20px; font-size: 0.8rem;'>STATUS: {status_label} | {status_text}</div>", unsafe_allow_html=True)

# --- TERMINAL E CARDS ---
col_stats1, col_stats2 = st.columns([1, 2])
with col_stats1:
    st.subheader(t["alocacao"])
    # ALTERADO AQUI: O gráfico de pizza agora reflete os ativos da sua sessão
    df_pizza = pd.DataFrame(st.session_state.meus_ativos) 
    
    if filtro_setor != t["todos"]: 
        df_pizza = df_pizza[df_pizza['setor'] == filtro_setor]
        
    fig = px.pie(df_pizza, names='setor', hole=0.4, template="plotly_dark", color_discrete_sequence=px.colors.qualitative.Set2)
    fig.update_layout(margin=dict(l=0, r=0, t=10, b=0), height=230, showlegend=False)
    st.plotly_chart(fig, use_container_width=True, config={'displaylogo': False})

with col_stats2:
    st.subheader(t["terminal"])
    st.write(f"{t['monitor']} **{filtro_setor}**")
    taxa_ex = brl_rate if "BRL" in st.session_state.moeda_save else (eur_rate if "EUR" in st.session_state.moeda_save else 1.0)
    simb_m = "BRL" if "BRL" in st.session_state.moeda_save else ("EUR" if "EUR" in st.session_state.moeda_save else "USD")
    st.info(f"{t['info_cambio']} **1 USD = {taxa_ex:.2f} {simb_m}**. {t['info_detalhe']} {st.session_state.moeda_save}.")

st.divider()
ativos_f = st.session_state.meus_ativos if filtro_setor == t["todos"] else [a for a in st.session_state.meus_ativos if a['setor'] == filtro_setor]

cols = st.columns(3)
def converter(val):
    if "BRL" in st.session_state.moeda_save: return val * brl_rate, "R$"
    if "EUR" in st.session_state.moeda_save: return val * eur_rate, "€"
    return val, "$"

for i, ativo in enumerate(ativos_f):
    with cols[i % 3]:
        ticker = ativo['ticker']
        data = st.session_state.live_data.get(ticker)
        q = get_safe_quote(ticker)
        fech_ant = q.get('pc', 0)
        
        label_status = ""
        if status_label == "OFF": 
            label_status = t.get("historico", "HISTÓRICO")
        elif data: 
            label_status = "LIVE"

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
            
            taxa_c = brl_rate if "BRL" in st.session_state.moeda_save else (eur_rate if "EUR" in st.session_state.moeda_save else 1)
            invest_atual = st.session_state.invest_save
            st.write(f"{t['compra']} **{(invest_atual / taxa_c) / price if price > 0 else 0:.5f}**")
            st.caption(f"Code: `{ticker}` | Ref: {time_ref}")
            
            # --- EXPANDER PARA O GRÁFICO ---
            # O 'expanded' agora obedece ao estado global do botão de abrir/fechar tudo
            with st.expander(f"📈 {t.get('grafico_h', 'Gráfico Histórico')}", expanded=st.session_state.show_all_charts):
                try:
                    # 1. TRADUÇÃO DO TICKER PARA O GRÁFICO
                    yf_ticker = ticker
                    if "BINANCE:" in ticker:
                        yf_ticker = ticker.replace("BINANCE:", "").replace("USDT", "-USD")
                    
                    # 2. DEFINIÇÃO DO PERÍODO
                    is_crypto = "BINANCE" in ticker
                    periodo_grafico = "1d" if (status_mercado == "ON" and not is_crypto) else "5d"
                    intervalo_grafico = "5m" if periodo_grafico == "1d" else "60m"
                    
                    hist_data = yf.download(yf_ticker, period=periodo_grafico, interval=intervalo_grafico, progress=False)
                    
                    if not hist_data.empty:
                        if isinstance(hist_data.columns, pd.MultiIndex):
                            hist_data.columns = hist_data.columns.get_level_values(0)
                        
                        # --- FUSO HORÁRIO NO GRÁFICO ---
                        # Converte as horas do gráfico para o fuso que você selecionou no Sidebar
                        user_tz = pytz.timezone(st.session_state.sel_fuso)
                        hist_data.index = hist_data.index.tz_convert(user_tz)
                        
                        # --- CONVERSÃO DE MOEDA NO GRÁFICO ---
                        taxa_c = brl_rate if "BRL" in st.session_state.moeda_save else (eur_rate if "EUR" in st.session_state.moeda_save else 1.0)
                        hist_data['Close'] = hist_data['Close'] * taxa_c
                        
                        # Criando o gráfico
                        fig_in = px.line(hist_data, y="Close", template="plotly_dark", color_discrete_sequence=["#007bff"])
                        
                        fig_in.update_layout(
                            margin=dict(l=0, r=0, t=10, b=10), 
                            height=180,
                            showlegend=False
                        )
                        
                        # --- LÓGICA DE ATUALIZAÇÃO DO EIXO X (1 EM 1 HORA) ---
                        if periodo_grafico == "1d" and not is_crypto:
                            fig_in.update_xaxes(
                                title=None,
                                showgrid=False,
                                tickformat="%H:%M",
                                dtick=3600000, # Alterado para 3.600.000ms = 1 hora
                                tickangle=0
                            )
                        else:
                            fig_in.update_xaxes(
                                title=None,
                                showgrid=False,
                                tickformat="%H:%M" if periodo_grafico == "1d" else "%d/%m"
                            )
                        
                        fig_in.update_yaxes(title=None, showgrid=True, gridcolor="#333")
                        
                        st.plotly_chart(fig_in, use_container_width=True, config={'displayModeBar': False, 'displaylogo': False})
                    else:
                        st.warning("Dados indisponíveis.")
                except Exception as e:
                    st.error(f"Erro técnico: {e}")
