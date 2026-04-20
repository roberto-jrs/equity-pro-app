import streamlit as st
import pandas as pd
import yfinance as yf
import plotly.express as px
from finnhub import Client
from datetime import datetime, time as dt_time
import pytz
from streamlit_autorefresh import st_autorefresh

# ===================================================================
# 1. CONFIGURAÇÃO DE PÁGINA
# ===================================================================
st.set_page_config(page_title="Equity Pro - Terminal", layout="wide", page_icon="▣")

# ===================================================================
# 2. CONFIGURAÇÃO DA API (USANDO ST.SECRETS)
# ===================================================================
try:
    FINNHUB_KEY = st.secrets["FINNHUB_KEY"]
except Exception:
    # Se não houver segredo, tenta variável de ambiente (para execução local)
    import os
    FINNHUB_KEY = os.getenv("FINNHUB_KEY")
    if not FINNHUB_KEY:
        st.error("❌ Chave da API não encontrada. Configure st.secrets ou a variável de ambiente FINNHUB_KEY.")
        st.stop()

finnhub_client = Client(api_key=FINNHUB_KEY)

# ===================================================================
# 3. ESTADO DA SESSÃO (inicialização)
# ===================================================================
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
if 'show_all_charts' not in st.session_state:
    st.session_state.show_all_charts = False
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
# 4. DICIONÁRIO DE TRADUÇÃO (com correções)
# ===================================================================
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
        "atualizar": "⟲ Actualizar Valores Globales",
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

# ===================================================================
# 5. FUNÇÕES PRINCIPAIS
# ===================================================================
@st.cache_data(ttl=3600)
def get_rates():
    """Obtém taxas de câmbio (USD -> BRL, USD -> EUR)"""
    try:
        usd_brl = yf.Ticker("USDBRL=X").fast_info['last_price']
        usd_eur = yf.Ticker("EUR=X").fast_info['last_price']
        return usd_brl, usd_eur
    except Exception:
        return 5.15, 0.92  # fallback seguro

def get_moeda_base(ticker):
    """Determina a moeda original do ativo baseado no ticker."""
    if ticker.endswith(".SA"):
        return "BRL"
    if ticker.startswith("BTC-") or ticker.startswith("ETH-") or "BINANCE" in ticker:
        return "USD"
    # Para ações americanas e demais, assumimos USD
    return "USD"

@st.cache_data(ttl=10)  # cache curto para dados de preço
def get_safe_quote(ticker):
    """Retorna preço e variação percentual com fallback robusto."""
    try:
        # Tenta Finnhub primeiro
        res = finnhub_client.quote(ticker)
        price = res.get('c', 0.0)
        change = res.get('dp', 0.0)
        if price and price > 0:
            return price, change
    except Exception:
        pass

    # Fallback: yfinance
    try:
        # Para ações brasileiras, garantir .SA (já deve vir com .SA, mas reforçar)
        yf_ticker = ticker if not (len(ticker) <= 6 and not ticker.endswith(".SA")) else f"{ticker}.SA"
        data = yf.Ticker(yf_ticker).fast_info
        price = data.get('last_price', 0.0)
        # Variação não disponível no fast_info, calculamos com histórico recente?
        change = 0.0
        if price > 0:
            return price, change
    except Exception:
        pass

    return 0.0, 0.0

def check_market_status():
    """Verifica se a bolsa de NY está aberta. Retorna (status_label, cor_hex, texto_traduzido)."""
    ny_now = datetime.now(pytz.timezone('America/New_York'))
    is_weekday = ny_now.weekday() < 5
    current_time = ny_now.time()
    market_open = dt_time(9, 30)
    market_close = dt_time(16, 0)
    is_hours = market_open <= current_time < market_close

    t = idiomas[st.session_state.sel_idioma]  # pega texto atual
    if is_weekday and is_hours:
        return "ON", "#26a69a", t["status_on"]
    else:
        return "OFF", "#ef5350", t["status_off"]

def get_now_local():
    return datetime.now(pytz.utc).astimezone(pytz.timezone(st.session_state.sel_fuso))

def converter_preco(preco_original, moeda_base, moeda_destino, taxa_brl, taxa_eur):
    """
    Converte preço de moeda_base para moeda_destino.
    moeda_base: "USD", "BRL"
    moeda_destino: "USD ($)", "BRL (R$)", "EUR (€)"
    """
    if moeda_destino == "USD ($)":
        if moeda_base == "BRL":
            return preco_original / taxa_brl, "$"
        else:  # USD
            return preco_original, "$"
    elif moeda_destino == "BRL (R$)":
        if moeda_base == "USD":
            return preco_original * taxa_brl, "R$"
        else:  # BRL
            return preco_original, "R$"
    elif moeda_destino == "EUR (€)":
        if moeda_base == "USD":
            return preco_original * taxa_eur, "€"
        elif moeda_base == "BRL":
            # BRL -> USD -> EUR
            return (preco_original / taxa_brl) * taxa_eur, "€"
        else:
            return preco_original, "€"
    return preco_original, "$"

# ===================================================================
# 6. CSS PERSONALIZADO
# ===================================================================
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

# ===================================================================
# 7. SIDEBAR (configurações, filtros, busca de ativos)
# ===================================================================
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

    st.divider()

    # BUSCA DE ATIVOS (CORRIGIDA)
    st.header("BUSCAR ATIVOS")
    busca = st.text_input("Ticker ou Nome (Ex: AAPL, PETR4, BTC-USD):")
    if busca:
        try:
            res = finnhub_client.symbol_lookup(busca)
            if res['count'] > 0:
                opcoes = {item['symbol']: item['description'] for item in res['result'][:10]}
                escolha = st.selectbox("Resultado:", list(opcoes.keys()), format_func=lambda x: f"{x} - {opcoes[x]}")
                if st.button("➕ Adicionar ao Terminal"):
                    ticker_escolhido = escolha
                    # Detecção de ativo brasileiro: se o símbolo tem 5-6 caracteres e não contém ponto,
                    # provavelmente é ação brasileira sem .SA. Mas vamos perguntar explicitamente.
                    if (len(ticker_escolhido) <= 6 and '.' not in ticker_escolhido and ':' not in ticker_escolhido):
                        # Pergunta se é brasileiro
                        is_br = st.radio("Este ativo é da B3 (Brasil)?", ("Não", "Sim"), key=f"br_{ticker_escolhido}")
                        if is_br == "Sim":
                            ticker_escolhido = f"{ticker_escolhido}.SA"
                    moeda = get_moeda_base(ticker_escolhido)
                    novo = {"ticker": ticker_escolhido, "nome": opcoes[escolha], "setor": "Personalizado", "moeda_base": moeda}
                    st.session_state.meus_ativos.append(novo)
                    st.success(f"{ticker_escolhido} adicionado com sucesso!")
                    st.rerun()
            else:
                st.warning("Nenhum resultado encontrado.")
        except Exception as e:
            st.error(f"Erro na busca: {e}")

    st.divider()

    st.header(t["config"])
    fusos_lista = ['America/New_York', 'America/Sao_Paulo', 'Europe/London', 'Europe/Paris', 'Asia/Tokyo', 'UTC']
    st.selectbox(t["fuso"], fusos_lista, key='sel_fuso')
    st.selectbox(t["moeda"], ["USD ($)", "BRL (R$)", "EUR (€)"], key="moeda_save")
    st.number_input(t["capital"], min_value=0.0, step=500.0, key="invest_save")

    st.divider()
    setores_lista = sorted(list(set([a['setor'] for a in st.session_state.meus_ativos])))
    filtro_setor = st.selectbox(t["filtro"], [t["todos"]] + setores_lista, key="setor_selector")

# ===================================================================
# 8. ATUALIZAÇÃO CONDICIONAL (REFRESH)
# ===================================================================
status_label, _, _ = check_market_status()
if status_label == "ON":
    st_autorefresh(interval=30000, key="equity_global_refresh")
else:
    st_autorefresh(interval=600000, key="equity_idle_refresh")

# ===================================================================
# 9. CABEÇALHO E STATUS DO MERCADO
# ===================================================================
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

_, status_color, status_text = check_market_status()
st.markdown(f"<div style='background-color: {status_color}; padding: 8px; border-radius: 4px; text-align: center; color: white; font-weight: bold; margin-bottom: 20px; font-size: 0.8rem;'>{status_text}</div>", unsafe_allow_html=True)

# ===================================================================
# 10. TAXAS DE CÂMBIO E INFORMAÇÕES
# ===================================================================
brl_rate, eur_rate = get_rates()

col_stats1, col_stats2 = st.columns([1, 2])
with col_stats1:
    st.subheader(t["alocacao"])
    df_pizza = pd.DataFrame(st.session_state.meus_ativos)
    if filtro_setor != t["todos"]:
        df_pizza = df_pizza[df_pizza['setor'] == filtro_setor]
    fig = px.pie(df_pizza, names='setor', hole=0.4, template="plotly_dark", color_discrete_sequence=px.colors.qualitative.Set2)
    fig.update_layout(margin=dict(l=0, r=0, t=10, b=0), height=230, showlegend=False)
    st.plotly_chart(fig, use_container_width=True, config={'displaylogo': False})

with col_stats2:
    st.subheader(t["terminal"])
    st.write(f"{t['monitor']} **{filtro_setor}**")
    # Mostra taxa de câmbio relevante
    if "BRL" in st.session_state.moeda_save:
        taxa_ex = brl_rate
        simb_m = "BRL"
    elif "EUR" in st.session_state.moeda_save:
        taxa_ex = eur_rate
        simb_m = "EUR"
    else:
        taxa_ex = 1.0
        simb_m = "USD"
    st.info(f"{t['info_cambio']} **1 USD = {taxa_ex:.2f} {simb_m}**. {t['info_detalhe']} {st.session_state.moeda_save}.")

st.divider()

# ===================================================================
# 11. EXIBIÇÃO DOS CARDS DE ATIVOS
# ===================================================================
ativos_f = st.session_state.meus_ativos if filtro_setor == t["todos"] else [a for a in st.session_state.meus_ativos if a['setor'] == filtro_setor]

cols = st.columns(3)
for i, ativo in enumerate(ativos_f):
    with cols[i % 3]:
        ticker = ativo['ticker']
        moeda_base = ativo.get('moeda_base', get_moeda_base(ticker))
        price, change = get_safe_quote(ticker)

        # Se o preço for 0, mostra mensagem de erro discreta
        if price == 0:
            with st.container(border=True):
                st.markdown(f"**{ativo['nome']}**")
                st.markdown(f"<span style='background:#ef5350; color:white; padding:2px 6px; border-radius:4px; font-size:9px;'>ERRO</span>", unsafe_allow_html=True)
                st.markdown("Dados indisponíveis no momento.")
                st.caption(f"Code: `{ticker}`")
            continue

        # Conversão para moeda de exibição
        p_conv, simb = converter_preco(price, moeda_base, st.session_state.moeda_save, brl_rate, eur_rate)

        # Determina se é dado "LIVE" (mercado aberto e ticker não é cripto/BR)
        status_label, _, _ = check_market_status()
        is_live = (status_label == "ON" and moeda_base == "USD" and not ticker.endswith(".SA"))
        label_status = "LIVE" if is_live else t["historico"]

        with st.container(border=True):
            ch, cs = st.columns([2, 1])
            ch.markdown(f"**{ativo['nome']}**")
            cor_badge = '#26a69a' if label_status == 'LIVE' else '#546e7a'
            cs.markdown(f"<span style='background:{cor_badge}; color:white; padding:2px 6px; border-radius:4px; font-size:9px; font-weight:bold;'>{label_status}</span>", unsafe_allow_html=True)

            st.markdown(f"### {simb} {p_conv:,.2f}")

            cor_var = '#26a69a' if change >= 0 else '#ef5350'
            seta = '▲' if change >= 0 else '▼'
            st.markdown(f"<p style='color:{cor_var}; font-weight:bold; margin-top:-15px;'>{seta} {abs(change):.2f}%</p>", unsafe_allow_html=True)

            # Cálculo de quantidade simulada (sempre em USD para simplicidade)
            invest_usd = st.session_state.invest_save
            if st.session_state.moeda_save == "BRL (R$)":
                invest_usd = invest_usd / brl_rate
            elif st.session_state.moeda_save == "EUR (€)":
                invest_usd = invest_usd / eur_rate
            # Se o ativo está em BRL, precisamos converter o investimento para BRL
            if moeda_base == "BRL":
                invest_local = invest_usd * brl_rate
                qtd_compra = invest_local / price if price > 0 else 0
            else:
                qtd_compra = invest_usd / price if price > 0 else 0
            st.write(f"{t['compra']} **{qtd_compra:.5f}**")
            st.caption(f"Code: `{ticker}`")

            # GRÁFICO HISTÓRICO
            with st.expander(f"📈 {t.get('grafico_h', 'Historical Chart')}", expanded=st.session_state.show_all_charts):
                try:
                    # Ajusta ticker para yfinance
                    yf_ticker = ticker
                    if "BINANCE:" in ticker:
                        yf_ticker = ticker.replace("BINANCE:", "").replace("USDT", "-USD")
                    # Período e intervalo
                    is_crypto = "BTC" in ticker or "ETH" in ticker
                    if status_label == "ON" and not is_crypto and moeda_base == "USD":
                        periodo = "1d"
                        intervalo = "5m"
                    else:
                        periodo = "5d"
                        intervalo = "60m"
                    hist = yf.download(yf_ticker, period=periodo, interval=intervalo, progress=False)
                    if not hist.empty:
                        if isinstance(hist.columns, pd.MultiIndex):
                            hist.columns = hist.columns.get_level_values(0)
                        # Converte fuso horário
                        user_tz = pytz.timezone(st.session_state.sel_fuso)
                        hist.index = hist.index.tz_convert(user_tz)
                        # Converte preços para moeda de exibição
                        hist['Close'] = hist['Close'].apply(lambda x: converter_preco(x, moeda_base, st.session_state.moeda_save, brl_rate, eur_rate)[0])
                        fig_in = px.line(hist, y="Close", template="plotly_dark", color_discrete_sequence=["#007bff"])
                        fig_in.update_layout(margin=dict(l=0, r=0, t=10, b=10), height=180, showlegend=False)
                        if periodo == "1d":
                            fig_in.update_xaxes(title=None, showgrid=False, tickformat="%H:%M", dtick=3600000)
                        else:
                            fig_in.update_xaxes(title=None, showgrid=False, tickformat="%d/%m")
                        fig_in.update_yaxes(title=None, showgrid=True, gridcolor="#333")
                        st.plotly_chart(fig_in, use_container_width=True, config={'displayModeBar': False})
                    else:
                        st.warning("Sem dados históricos para este período.")
                except Exception as e:
                    st.error(f"Erro ao carregar gráfico: {e}")
