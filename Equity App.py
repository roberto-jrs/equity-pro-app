import streamlit as st
import pandas as pd
import yfinance as yf
import plotly.express as px
import plotly.graph_objects as go
from finnhub import Client
from datetime import datetime, time as dt_time, timedelta
import pytz
from streamlit_autorefresh import st_autorefresh
import os
import io
import numpy as np

# ===================================================================
# 1. CONFIGURAÇÃO DE PÁGINA
# ===================================================================
st.set_page_config(page_title="Equity Pro - Advanced", layout="wide", page_icon="▣")

# ===================================================================
# 2. CONFIGURAÇÃO DA API (USANDO ST.SECRETS)
# ===================================================================
try:
    FINNHUB_KEY = st.secrets["FINNHUB_KEY"]
except Exception:
    FINNHUB_KEY = os.getenv("FINNHUB_KEY")
    if not FINNHUB_KEY:
        st.error("❌ Chave da API não encontrada. Configure st.secrets ou a variável de ambiente FINNHUB_KEY.")
        st.stop()
finnhub_client = Client(api_key=FINNHUB_KEY)

# ===================================================================
# 3. FUNÇÕES DE INDICADORES TÉCNICOS (MANUAIS)
# ===================================================================
def sma(series, length):
    """Simple Moving Average"""
    return series.rolling(window=length).mean()

def rsi(series, length=14):
    """Relative Strength Index"""
    delta = series.diff()
    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)
    avg_gain = gain.rolling(window=length).mean()
    avg_loss = loss.rolling(window=length).mean()
    rs = avg_gain / avg_loss
    return 100 - (100 / (1 + rs))

def macd(series, fast=12, slow=26, signal=9):
    """MACD line, signal line, histogram"""
    ema_fast = series.ewm(span=fast, adjust=False).mean()
    ema_slow = series.ewm(span=slow, adjust=False).mean()
    macd_line = ema_fast - ema_slow
    signal_line = macd_line.ewm(span=signal, adjust=False).mean()
    histogram = macd_line - signal_line
    return macd_line, signal_line, histogram

# ===================================================================
# 4. ESTADO DA SESSÃO (inicialização completa)
# ===================================================================
if 'sel_idioma' not in st.session_state:
    st.session_state.sel_idioma = "English"
if 'setor_selector' not in st.session_state:
    st.session_state.setor_selector = "All"
if 'moeda_save' not in st.session_state:
    st.session_state.moeda_save = "USD ($)"
if 'invest_save' not in st.session_state:
    st.session_state.invest_save = 10000.00
if 'sel_fuso' not in st.session_state:
    st.session_state.sel_fuso = 'America/New_York'
if 'show_all_charts' not in st.session_state:
    st.session_state.show_all_charts = False
if 'modo_noturno' not in st.session_state:
    st.session_state.modo_noturno = False
if 'carteira' not in st.session_state:
    st.session_state.carteira = pd.DataFrame(columns=["Data", "Ticker", "Operacao", "Quantidade", "Preco", "Total", "Moeda"])
if 'saldo' not in st.session_state:
    st.session_state.saldo = st.session_state.invest_save
if 'alertas' not in st.session_state:
    st.session_state.alertas = []
if 'meus_ativos' not in st.session_state:
    st.session_state.meus_ativos = [
        {"ticker": "AAPL", "nome": "Apple Inc.", "setor": "Tecnologia", "moeda_base": "USD"},
        {"ticker": "NVDA", "nome": "NVIDIA Corp.", "setor": "Tecnologia", "moeda_base": "USD"},
        {"ticker": "MSFT", "nome": "Microsoft Corp.", "setor": "Tecnologia", "moeda_base": "USD"},
        {"ticker": "GOOGL", "nome": "Alphabet Inc.", "setor": "Tecnologia", "moeda_base": "USD"},
        {"ticker": "TSLA", "nome": "Tesla, Inc.", "setor": "Automotivo", "moeda_base": "USD"},
        {"ticker": "AMZN", "nome": "Amazon.com", "setor": "Varejo Digital", "moeda_base": "USD"},
        {"ticker": "META", "nome": "Meta Platforms", "setor": "Tecnologia", "moeda_base": "USD"},
        {"ticker": "V", "nome": "Visa Inc.", "setor": "Financeiro", "moeda_base": "USD"},
        {"ticker": "JPM", "nome": "JPMorgan Chase", "setor": "Financeiro", "moeda_base": "USD"},
        {"ticker": "KO", "nome": "Coca-Cola Co.", "setor": "Consumo", "moeda_base": "USD"},
        {"ticker": "DIS", "nome": "Walt Disney Co.", "setor": "Entretenimento", "moeda_base": "USD"},
        {"ticker": "NFLX", "nome": "Netflix, Inc.", "setor": "Entretenimento", "moeda_base": "USD"},
        {"ticker": "BTC-USD", "nome": "Bitcoin", "setor": "Cripto", "moeda_base": "USD"},
        {"ticker": "ETH-USD", "nome": "Ethereum", "setor": "Cripto", "moeda_base": "USD"}
    ]

# ===================================================================
# 5. DICIONÁRIO DE TRADUÇÃO (completo)
# ===================================================================
idiomas = {
    "English": {
        "titulo_idioma": "LANGUAGE", "config": "PERSONAL SETTINGS", "moeda": "Display Currency:",
        "capital": "Initial Capital:", "filtro": "Filter by Sector:", "fuso": "User Timezone:",
        "todos": "All", "status_on": "STOCK MARKET OPEN", "status_off": "STOCK MARKET CLOSED",
        "alocacao": "📊 Asset Allocation", "terminal": "💡 Stock Terminal",
        "monitor": "Monitoring assets in sector:", "info_cambio": "Exchange rate:",
        "info_detalhe": "Purchase calculations based on capital of", "compra": "Simulated quantity:",
        "atualizar": "⟲ Refresh", "historico": "HISTORICAL", "subtitulo": "Advanced Trading Terminal",
        "ultima_at": "Last update:", "grafico_h": "Technical Charts", "btn_expandir": "📈 Expand",
        "btn_recolher": "📐 Collapse", "help_graficos": "Expand/Collapse charts",
        "carteira_titulo": "💼 Portfolio", "extrato": "Transaction History", "comprar": "Buy",
        "vender": "Sell", "saldo": "Balance", "alertas_titulo": "🔔 Price Alerts",
        "criar_alerta": "Create Alert", "ticker_alerta": "Ticker", "preco_alerta": "Target Price",
        "acima_abaixo": "When price goes", "acima": "above", "abaixo": "below",
        "backtest_titulo": "📈 Backtesting (MA Crossover)", "periodo_back": "Period",
        "executar_back": "Run Backtest", "exportar": "Export Data", "modo_noturno": "Night Mode"
    },
    "Português (BR)": {
        "titulo_idioma": "IDIOMA", "config": "CONFIGURAÇÕES", "moeda": "Moeda de Exibição:",
        "capital": "Capital Inicial:", "filtro": "Filtrar por Setor:", "fuso": "Fuso Horário:",
        "todos": "Todos", "status_on": "MERCADO ABERTO", "status_off": "MERCADO FECHADO",
        "alocacao": "📊 Alocação", "terminal": "💡 Terminal", "monitor": "Monitorando setor:",
        "info_cambio": "Câmbio:", "info_detalhe": "Cálculos com capital de", "compra": "Quantidade simulada:",
        "atualizar": "⟲ Atualizar", "historico": "HISTÓRICO", "subtitulo": "Terminal Avançado",
        "ultima_at": "Última atualização:", "grafico_h": "Gráficos Técnicos",
        "btn_expandir": "📈 Expandir", "btn_recolher": "📐 Recolher", "help_graficos": "Expandir/Recolher",
        "carteira_titulo": "💼 Carteira", "extrato": "Histórico", "comprar": "Comprar",
        "vender": "Vender", "saldo": "Saldo", "alertas_titulo": "🔔 Alertas de Preço",
        "criar_alerta": "Criar Alerta", "ticker_alerta": "Ativo", "preco_alerta": "Preço Alvo",
        "acima_abaixo": "Quando o preço estiver", "acima": "acima", "abaixo": "abaixo",
        "backtest_titulo": "📈 Backtest (Médias Móveis)", "periodo_back": "Período",
        "executar_back": "Executar", "exportar": "Exportar Dados", "modo_noturno": "Modo Noturno"
    },
    "Español": {
        "titulo_idioma": "IDIOMA", "config": "CONFIGURACIÓN", "moeda": "Moneda:",
        "capital": "Capital Inicial:", "filtro": "Filtrar por Sector:", "fuso": "Zona Horaria:",
        "todos": "Todos", "status_on": "MERCADO ABIERTO", "status_off": "MERCADO CERRADO",
        "alocacao": "📊 Asignación", "terminal": "💡 Terminal", "monitor": "Monitoreando sector:",
        "info_cambio": "Tipo de cambio:", "info_detalhe": "Cálculos con capital de", "compra": "Cantidad simulada:",
        "atualizar": "⟲ Actualizar", "historico": "HISTÓRICO", "subtitulo": "Terminal Avanzado",
        "ultima_at": "Última actualización:", "grafico_h": "Gráficos Técnicos",
        "btn_expandir": "📈 Expandir", "btn_recolher": "📐 Contraer", "help_graficos": "Expandir/Contraer",
        "carteira_titulo": "💼 Cartera", "extrato": "Historial", "comprar": "Comprar",
        "vender": "Vender", "saldo": "Saldo", "alertas_titulo": "🔔 Alertas de Precio",
        "criar_alerta": "Crear Alerta", "ticker_alerta": "Activo", "preco_alerta": "Precio Objetivo",
        "acima_abaixo": "Cuando el precio esté", "acima": "encima", "abaixo": "debajo",
        "backtest_titulo": "📈 Backtest (Media Móvil)", "periodo_back": "Período",
        "executar_back": "Ejecutar", "exportar": "Exportar Datos", "modo_noturno": "Modo Nocturno"
    }
}

def mudar_idioma():
    st.session_state.sel_idioma = st.session_state.idioma_temp

# ===================================================================
# 6. FUNÇÕES AUXILIARES DE DADOS
# ===================================================================
@st.cache_data(ttl=3600)
def get_rates():
    try:
        usd_brl = yf.Ticker("USDBRL=X").fast_info['last_price']
        usd_eur = yf.Ticker("EUR=X").fast_info['last_price']
        return usd_brl, usd_eur
    except:
        return 5.15, 0.92

def get_moeda_base(ticker):
    if ticker.endswith(".SA"):
        return "BRL"
    if ticker.startswith("BTC-") or ticker.startswith("ETH-"):
        return "USD"
    return "USD"

@st.cache_data(ttl=10)
def get_safe_quote(ticker):
    try:
        res = finnhub_client.quote(ticker)
        price = res.get('c', 0.0)
        change = res.get('dp', 0.0)
        if price and price > 0:
            return price, change
    except:
        pass
    try:
        yf_ticker = ticker if not (len(ticker) <= 6 and not ticker.endswith(".SA")) else f"{ticker}.SA"
        data = yf.Ticker(yf_ticker).fast_info
        price = data.get('last_price', 0.0)
        return price, 0.0
    except:
        return 0.0, 0.0

def check_market_status():
    ny_now = datetime.now(pytz.timezone('America/New_York'))
    is_weekday = ny_now.weekday() < 5
    current_time = ny_now.time()
    market_open = dt_time(9, 30)
    market_close = dt_time(16, 0)
    is_hours = market_open <= current_time < market_close
    t = idiomas[st.session_state.sel_idioma]
    if is_weekday and is_hours:
        return "ON", "#26a69a", t["status_on"]
    else:
        return "OFF", "#ef5350", t["status_off"]

def get_now_local():
    return datetime.now(pytz.utc).astimezone(pytz.timezone(st.session_state.sel_fuso))

def converter_preco(preco_original, moeda_base, moeda_destino, taxa_brl, taxa_eur):
    if moeda_destino == "USD ($)":
        if moeda_base == "BRL":
            return preco_original / taxa_brl, "$"
        else:
            return preco_original, "$"
    elif moeda_destino == "BRL (R$)":
        if moeda_base == "USD":
            return preco_original * taxa_brl, "R$"
        else:
            return preco_original, "R$"
    elif moeda_destino == "EUR (€)":
        if moeda_base == "USD":
            return preco_original * taxa_eur, "€"
        elif moeda_base == "BRL":
            return (preco_original / taxa_brl) * taxa_eur, "€"
        else:
            return preco_original, "€"
    return preco_original, "$"

def executar_backtest(ticker, data_inicio, data_fim, short_ma=20, long_ma=50):
    """Backtest de cruzamento de médias móveis sem pandas_ta"""
    df = yf.download(ticker, start=data_inicio, end=data_fim, progress=False)
    if df.empty:
        return None, None, None
    df['MA_short'] = sma(df['Close'], short_ma)
    df['MA_long'] = sma(df['Close'], long_ma)
    df['Signal'] = 0
    df.loc[df['MA_short'] > df['MA_long'], 'Signal'] = 1
    df.loc[df['MA_short'] <= df['MA_long'], 'Signal'] = -1
    df['Position'] = df['Signal'].diff()
    df['Returns'] = df['Close'].pct_change()
    df['Strategy_Returns'] = df['Signal'].shift(1) * df['Returns']
    df['Cumulative_Returns'] = (1 + df['Returns']).cumprod()
    df['Cumulative_Strategy'] = (1 + df['Strategy_Returns']).cumprod()
    total_return = df['Cumulative_Strategy'].iloc[-1] - 1 if not df.empty else 0
    return df, total_return

# ===================================================================
# 7. CSS PERSONALIZADO + MODO NOTURNO MANUAL
# ===================================================================
if st.session_state.modo_noturno:
    st.markdown("""
        <style>
            .stApp { background-color: #0E1117; color: #FAFAFA; }
            .css-1d391kg { background-color: #1E1E1E; }
            .st-bw { color: #FAFAFA; }
            div[data-testid="stExpander"] { background-color: #1E1E1E; }
        </style>
    """, unsafe_allow_html=True)
else:
    st.markdown("""
        <style>
            .stApp { background-color: #FFFFFF; }
        </style>
    """, unsafe_allow_html=True)

# ===================================================================
# 8. SIDEBAR (todas as configurações)
# ===================================================================
with st.sidebar:
    st.header(idiomas[st.session_state.sel_idioma]["titulo_idioma"])
    st.selectbox("Select / Selecione:", list(idiomas.keys()),
                 index=list(idiomas.keys()).index(st.session_state.sel_idioma),
                 key="idioma_temp", on_change=mudar_idioma)
    t = idiomas[st.session_state.sel_idioma]

    st.divider()
    st.header(t["config"])
    fusos_lista = ['America/New_York', 'America/Sao_Paulo', 'Europe/London', 'Europe/Paris', 'Asia/Tokyo', 'UTC']
    st.selectbox(t["fuso"], fusos_lista, key='sel_fuso')
    st.selectbox(t["moeda"], ["USD ($)", "BRL (R$)", "EUR (€)"], key="moeda_save")

    novo_capital = st.number_input(t["capital"], min_value=0.0, step=1000.0, value=st.session_state.invest_save)
    if novo_capital != st.session_state.invest_save:
        st.session_state.invest_save = novo_capital
        st.session_state.saldo = novo_capital

    st.toggle(t["modo_noturno"], key="modo_noturno")

    st.divider()
    st.header("🔔 " + t["alertas_titulo"])
    with st.expander(t["criar_alerta"]):
        col_a1, col_a2 = st.columns(2)
        with col_a1:
            ticker_alerta = st.text_input(t["ticker_alerta"], key="alert_ticker")
        with col_a2:
            preco_alerta = st.number_input(t["preco_alerta"], min_value=0.0, step=1.0, key="alert_price")
        direcao = st.radio(t["acima_abaixo"], [t["acima"], t["abaixo"]], horizontal=True)
        if st.button("➕ " + t["criar_alerta"]):
            if ticker_alerta and preco_alerta > 0:
                st.session_state.alertas.append({
                    "ticker": ticker_alerta.upper(),
                    "preco": preco_alerta,
                    "direcao": "above" if direcao == t["acima"] else "below"
                })
                st.success(f"Alerta criado para {ticker_alerta.upper()} {direcao} {preco_alerta}")
            else:
                st.error("Preencha ticker e preço válido.")

    if st.session_state.alertas:
        st.write("**Alertas ativos:**")
        for i, alert in enumerate(st.session_state.alertas):
            st.caption(f"{alert['ticker']} - {'acima' if alert['direcao']=='above' else 'abaixo'} ${alert['preco']:.2f}")
        if st.button("🗑️ Limpar todos"):
            st.session_state.alertas = []
            st.rerun()

    st.divider()
    st.header("📊 " + t["backtest_titulo"])
    ticker_bt = st.text_input("Ativo (ex: AAPL)", key="bt_ticker")
    data_inicio = st.date_input("Data início", datetime.now() - timedelta(days=365))
    data_fim = st.date_input("Data fim", datetime.now())
    if st.button(t["executar_back"]):
        if ticker_bt:
            df_bt, ret = executar_backtest(ticker_bt, data_inicio, data_fim)
            if df_bt is not None:
                st.session_state.backtest_result = (df_bt, ret, ticker_bt)
                st.success(f"Backtest concluído. Retorno estratégia: {ret*100:.2f}%")
            else:
                st.error("Dados insuficientes para o backtest.")
        else:
            st.warning("Informe um ticker.")

# ===================================================================
# 9. HEADER E STATUS
# ===================================================================
st.markdown(f"<h1 style='font-size:2.5rem;'>▣ EQUITY PRO</h1><p>{t['subtitulo']}</p>", unsafe_allow_html=True)

status_label, status_color, status_text = check_market_status()
st.markdown(f"<div style='background-color: {status_color}; padding: 8px; border-radius: 4px; text-align: center; color: white; font-weight: bold; margin-bottom: 20px;'>{status_text}</div>", unsafe_allow_html=True)

col_refresh, col_export = st.columns([4,1])
with col_refresh:
    if st.button(t["atualizar"], use_container_width=True):
        st.rerun()
with col_export:
    if st.button(f"📥 {t['exportar']}"):
        if not st.session_state.carteira.empty:
            csv = st.session_state.carteira.to_csv(index=False).encode('utf-8')
            st.download_button("Download CSV", csv, "carteira.csv", "text/csv", key="export_csv_btn")
        else:
            st.warning("Nenhuma transação para exportar.")

st.caption(f"{t['ultima_at']} {get_now_local().strftime('%H:%M:%S')}")

# ===================================================================
# 10. CARTEIRA E SALDO
# ===================================================================
col1, col2 = st.columns([1,2])
with col1:
    st.subheader(t["carteira_titulo"])
    saldo_exibido = st.session_state.saldo
    if st.session_state.moeda_save == "USD ($)":
        st.metric(t["saldo"], f"$ {saldo_exibido:,.2f}")
    elif st.session_state.moeda_save == "BRL (R$)":
        st.metric(t["saldo"], f"R$ {saldo_exibido:,.2f}")
    else:
        st.metric(t["saldo"], f"€ {saldo_exibido:,.2f}")
    if not st.session_state.carteira.empty:
        st.dataframe(st.session_state.carteira, use_container_width=True)
    else:
        st.info("Nenhuma operação realizada ainda.")
with col2:
    st.subheader(t["terminal"])
    st.write(f"{t['monitor']} **{st.session_state.setor_selector if 'setor_selector' in st.session_state else 'All'}**")
    brl_rate, eur_rate = get_rates()

# ===================================================================
# 11. FILTRO DE SETOR
# ===================================================================
setores_lista = sorted(list(set([a['setor'] for a in st.session_state.meus_ativos])))
filtro_setor = st.selectbox(t["filtro"], [t["todos"]] + setores_lista, key="setor_selector")
ativos_f = st.session_state.meus_ativos if filtro_setor == t["todos"] else [a for a in st.session_state.meus_ativos if a['setor'] == filtro_setor]

# ===================================================================
# 12. CARDS DE ATIVOS COM GRÁFICOS AVANÇADOS + COMPRA/VENDA
# ===================================================================
cols = st.columns(3)
for i, ativo in enumerate(ativos_f):
    with cols[i % 3]:
        ticker = ativo['ticker']
        moeda_base = ativo.get('moeda_base', get_moeda_base(ticker))
        price, change = get_safe_quote(ticker)
        if price == 0:
            with st.container(border=True):
                st.markdown(f"**{ativo['nome']}**")
                st.markdown("🔴 Dados indisponíveis")
                st.caption(f"Code: `{ticker}`")
            continue

        p_conv, simb = converter_preco(price, moeda_base, st.session_state.moeda_save, brl_rate, eur_rate)
        status_label, _, _ = check_market_status()
        is_live = (status_label == "ON" and moeda_base == "USD" and not ticker.endswith(".SA"))
        label_status = "LIVE" if is_live else "HIST"

        with st.container(border=True):
            col_nome, col_badge = st.columns([2,1])
            col_nome.markdown(f"**{ativo['nome']}**")
            col_badge.markdown(f"<span style='background:#26a69a; color:white; padding:2px 6px; border-radius:4px; font-size:9px;'>{label_status}</span>", unsafe_allow_html=True)
            st.markdown(f"### {simb} {p_conv:,.2f}")
            cor_var = '#26a69a' if change >= 0 else '#ef5350'
            seta = '▲' if change >= 0 else '▼'
            st.markdown(f"<p style='color:{cor_var}; font-weight:bold;'>{seta} {abs(change):.2f}%</p>", unsafe_allow_html=True)

            # Compra/Venda
            col_comprar, col_vender = st.columns(2)
            with col_comprar:
                qtd_compra = st.number_input("Qtd", min_value=0.0, step=0.01, key=f"comprar_{ticker}", format="%.4f")
                if st.button(t["comprar"], key=f"btn_c_{ticker}"):
                    custo = qtd_compra * price
                    if custo <= st.session_state.saldo:
                        st.session_state.saldo -= custo
                        nova_trans = pd.DataFrame([{
                            "Data": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                            "Ticker": ticker, "Operacao": "COMPRA", "Quantidade": qtd_compra,
                            "Preco": price, "Total": custo, "Moeda": moeda_base
                        }])
                        st.session_state.carteira = pd.concat([st.session_state.carteira, nova_trans], ignore_index=True)
                        st.success(f"Compra de {qtd_compra} {ticker} realizada!")
                        st.rerun()
                    else:
                        st.error("Saldo insuficiente.")
            with col_vender:
                qtd_venda = st.number_input("Qtd", min_value=0.0, step=0.01, key=f"vender_{ticker}", format="%.4f")
                if st.button(t["vender"], key=f"btn_v_{ticker}"):
                    st.session_state.saldo += qtd_venda * price
                    nova_trans = pd.DataFrame([{
                        "Data": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                        "Ticker": ticker, "Operacao": "VENDA", "Quantidade": qtd_venda,
                        "Preco": price, "Total": qtd_venda * price, "Moeda": moeda_base
                    }])
                    st.session_state.carteira = pd.concat([st.session_state.carteira, nova_trans], ignore_index=True)
                    st.success(f"Venda de {qtd_venda} {ticker} realizada!")
                    st.rerun()

            st.caption(f"Code: `{ticker}`")

            # EXPANDER COM GRÁFICOS AVANÇADOS (candlestick, volume, RSI, MACD)
            with st.expander(f"📈 {t['grafico_h']}", expanded=st.session_state.show_all_charts):
                try:
                    yf_ticker = ticker.replace("BINANCE:", "").replace("USDT", "-USD")
                    # Para B3, manter .SA
                    hist = yf.download(yf_ticker, period="1mo", interval="1d", progress=False)
                    if not hist.empty and len(hist) > 20:
                        # Calcular indicadores
                        hist['SMA20'] = sma(hist['Close'], 20)
                        hist['SMA50'] = sma(hist['Close'], 50)
                        hist['RSI'] = rsi(hist['Close'], 14)
                        macd_line, signal_line, hist['MACD_hist'] = macd(hist['Close'])
                        hist['MACD'] = macd_line
                        hist['MACD_signal'] = signal_line

                        # Candlestick + Médias
                        fig = go.Figure()
                        fig.add_trace(go.Candlestick(x=hist.index,
                                                     open=hist['Open'], high=hist['High'],
                                                     low=hist['Low'], close=hist['Close'],
                                                     name='Candlestick'))
                        fig.add_trace(go.Scatter(x=hist.index, y=hist['SMA20'], mode='lines', name='SMA20', line=dict(color='orange')))
                        fig.add_trace(go.Scatter(x=hist.index, y=hist['SMA50'], mode='lines', name='SMA50', line=dict(color='purple')))
                        fig.update_layout(title=f"{ticker} - Candle + Médias", height=400, xaxis_rangeslider_visible=False)
                        fig.update_xaxes(title=None)
                        fig.update_yaxes(title="Preço")
                        st.plotly_chart(fig, use_container_width=True)

                        # Volume
                        fig_vol = px.bar(hist, x=hist.index, y='Volume', title="Volume", color_discrete_sequence=['lightblue'])
                        st.plotly_chart(fig_vol, use_container_width=True)

                        # RSI
                        fig_rsi = px.line(hist, x=hist.index, y='RSI', title="RSI (14)")
                        fig_rsi.add_hline(y=70, line_dash="dash", line_color="red")
                        fig_rsi.add_hline(y=30, line_dash="dash", line_color="green")
                        fig_rsi.update_yaxes(range=[0,100])
                        st.plotly_chart(fig_rsi, use_container_width=True)

                        # MACD
                        fig_macd = go.Figure()
                        fig_macd.add_trace(go.Scatter(x=hist.index, y=hist['MACD'], name='MACD'))
                        fig_macd.add_trace(go.Scatter(x=hist.index, y=hist['MACD_signal'], name='Signal'))
                        fig_macd.add_bar(x=hist.index, y=hist['MACD_hist'], name='Histogram')
                        fig_macd.update_layout(title="MACD")
                        st.plotly_chart(fig_macd, use_container_width=True)
                    else:
                        st.warning("Dados históricos insuficientes para gráficos avançados.")
                except Exception as e:
                    st.error(f"Erro no gráfico: {str(e)}")

# ===================================================================
# 13. BACKTEST RESULTADOS (se existir)
# ===================================================================
if 'backtest_result' in st.session_state:
    df_bt, ret, ticker_bt = st.session_state.backtest_result
    st.divider()
    st.subheader(f"Backtest para {ticker_bt}")
    col_r1, col_r2 = st.columns(2)
    col_r1.metric("Retorno Estratégia", f"{ret*100:.2f}%")
    col_r2.metric("Retorno Buy&Hold", f"{(df_bt['Cumulative_Returns'].iloc[-1]-1)*100:.2f}%")
    fig_bt = go.Figure()
    fig_bt.add_trace(go.Scatter(x=df_bt.index, y=df_bt['Cumulative_Strategy'], name='Estratégia'))
    fig_bt.add_trace(go.Scatter(x=df_bt.index, y=df_bt['Cumulative_Returns'], name='Buy & Hold'))
    st.plotly_chart(fig_bt, use_container_width=True)

# ===================================================================
# 14. VERIFICAÇÃO DE ALERTAS (a cada refresh)
# ===================================================================
if st.session_state.alertas:
    for alerta in st.session_state.alertas:
        preco_atual, _ = get_safe_quote(alerta["ticker"])
        if preco_atual > 0:
            if alerta["direcao"] == "above" and preco_atual >= alerta["preco"]:
                st.toast(f"🔔 ALERTA: {alerta['ticker']} atingiu ${preco_atual:.2f} (acima de ${alerta['preco']})", icon="⚠️")
            elif alerta["direcao"] == "below" and preco_atual <= alerta["preco"]:
                st.toast(f"🔔 ALERTA: {alerta['ticker']} caiu para ${preco_atual:.2f} (abaixo de ${alerta['preco']})", icon="⚠️")

# ===================================================================
# 15. REFRESH AUTOMÁTICO CONDICIONAL
# ===================================================================
status_label, _, _ = check_market_status()
if status_label == "ON":
    st_autorefresh(interval=30000, key="refresh_on")
else:
    st_autorefresh(interval=600000, key="refresh_off")
