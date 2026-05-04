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
import numpy as np
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from database import cadastrar_usuario, verificar_login, salvar_preferencias, buscar_usuario_por_username
from database import criar_alerta, listar_alertas_usuario, desativar_alerta
from email_utils import enviar_email_gmail
import hashlib
import time


# Gera um token único para o usuário
def gerar_token(username):
    secret = st.secrets.get("SESSION_SECRET", "equitypro2024")  # segredo fixo (pode guardar no secrets.toml)
    timestamp = int(time.time())
    raw = f"{username}|{timestamp}|{secret}"
    token = hashlib.sha256(raw.encode()).hexdigest()
    return f"{username}|{timestamp}|{token}"

# Valida o token e retorna o username se válido (e dentro do prazo de validade)
def validar_token(token_str, dias_validade=30):
    try:
        username, timestamp_str, token = token_str.split("|")
        timestamp = int(timestamp_str)
        # Verifica se não expirou (dias_validade)
        if time.time() - timestamp > dias_validade * 86400:
            return None
        # Verifica o hash
        secret = st.secrets.get("SESSION_SECRET", "equitypro2024")
        raw = f"{username}|{timestamp}|{secret}"
        expected = hashlib.sha256(raw.encode()).hexdigest()
        if token == expected:
            return username
    except:
        pass
    return None

# ===================================================================
# FUNÇÕES AUXILIARES 
# ===================================================================
@st.cache_data(ttl=30)   # atualiza a cada 30 segundos
def get_rates():
    try:
        usd_brl = yf.Ticker("USDBRL=X").fast_info.get('last_price', 5.15)
        usd_eur = yf.Ticker("EUR=X").fast_info.get('last_price', 0.92)
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
    df = yf.download(ticker, start=data_inicio, end=data_fim, progress=False)
    if df.empty:
        return None, None, None
    df['MA_short'] = sma(df['Close'], short_ma)
    df['MA_long'] = sma(df['Close'], long_ma)
    df['Signal'] = 0
    df.loc[df['MA_short'] > df['MA_long'], 'Signal'] = 1
    df.loc[df['MA_short'] <= df['MA_long'], 'Signal'] = -1
    df['Returns'] = df['Close'].pct_change()
    df['Strategy_Returns'] = df['Signal'].shift(1) * df['Returns']
    df['Cumulative_Returns'] = (1 + df['Returns']).cumprod()
    df['Cumulative_Strategy'] = (1 + df['Strategy_Returns']).cumprod()
    total_return = df['Cumulative_Strategy'].iloc[-1] - 1 if not df.empty else 0
    return df, total_return

def send_email_alert(subject, body, config):
    """Envia e-mail usando configuração SMTP (não utilizado atualmente)"""
    if not config['enabled']:
        return
    try:
        msg = MIMEMultipart()
        msg['From'] = config['email_from']
        msg['To'] = config['email_to']
        msg['Subject'] = subject
        msg.attach(MIMEText(body, 'plain'))
        server = smtplib.SMTP(config['smtp_server'], config['smtp_port'])
        server.starttls()
        server.login(config['email_from'], config['email_password'])
        server.send_message(msg)
        server.quit()
    except Exception as e:
        st.warning(f"Falha ao enviar e-mail: {e}")

def generate_report_html(ticker, nome, price, change, hist, indicadores, capital):
    """Gera relatório HTML do ativo para download"""
    html = f"""
    <html>
    <head><title>Relatório {ticker}</title>
    <style>
        body {{ font-family: Arial; margin: 20px; }}
        h1 {{ color: #007bff; }}
        .metric {{ background: #f0f2f6; padding: 10px; border-radius: 5px; margin: 10px 0; }}
    </style>
    </head>
    <body>
    <h1>Relatório de Análise - {nome} ({ticker})</h1>
    <div class="metric">
        <p>Preço atual: ${price:.2f}</p>
        <p>Variação: {change:.2f}%</p>
        <p>Capital simulado: ${capital:,.2f}</p>
    </div>
    <p>Relatório gerado em: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
    <p><em>Gráficos técnicos estão anexados nas imagens ou visualize no app.</em></p>
    </body>
    </html>
    """
    return html

def formatar_valor_moeda(valor, moeda_destino, simbolo=None):
    """
    Formata valor numérico (float) no padrão de moeda escolhido.
    Exemplos:
        USD: $ 1,234,567.89
        BRL: R$ 1.234.567,89
        EUR: € 1.234.567,89
    """
    if simbolo is None:
        if moeda_destino == "USD ($)":
            simbolo = "$"
        elif moeda_destino == "BRL (R$)":
            simbolo = "R$"
        else:  # EUR
            simbolo = "€"
    
    # Formata o número com 2 decimais e separador americano (vírgula milhar, ponto decimal)
    s = f"{valor:,.2f}"
    
    if moeda_destino == "USD ($)":
        return f"{simbolo} {s}"
    else:
        # Troca os separadores: vírgula milhar -> ponto; ponto decimal -> vírgula
        partes = s.split('.')
        inteiro = partes[0].replace(',', '.')  # troca vírgulas por pontos
        decimal = partes[1]
        return f"{simbolo} {inteiro},{decimal}"

# ===================================================================
# TRADUÇÃO
# ===================================================================
idiomas = {
    "English": {
        "titulo_idioma": "LANGUAGE", "config": "PERSONAL SETTINGS", "moeda": "Display Currency:",
        "capital": "Simulation Capital:", "filtro": "Filter by Sector:", "fuso": "User Timezone:",
        "todos": "All", "status_on": "STOCK MARKET OPEN", "status_off": "STOCK MARKET CLOSED",
        "alocacao": "📊 Asset Allocation", "terminal": "💡 Stock Terminal",
        "monitor": "Monitoring assets in sector:", "info_cambio": "Exchange rate:",
        "info_detalhe": "Purchase calculation based on", "quantidade_sugerida": "Suggested quantity:",
        "atualizar": "⟲ Refresh", "historico": "HISTORICAL", "subtitulo": "Professional Analysis Suite",
        "ultima_at": "Last update:", "grafico_h": "Technical Charts", "btn_expandir": "📈 Expand All",
        "btn_recolher": "📐 Collapse All", "help_graficos": "Expand/Collapse all charts",
        "alertas_titulo": "🔔 Price Alerts", "criar_alerta": "Create Alert",
        "ticker_alerta": "Ticker", "preco_alerta": "Target Price",
        "acima_abaixo": "When price goes", "acima": "above", "abaixo": "below",
        "backtest_titulo": "📈 Backtesting (MA Crossover)", "periodo_back": "Period",
        "executar_back": "Run Backtest", "exportar": "Export Data", 
        "gerenciar_ativos": "📁 Asset Management", "adicionar_manual": "Add manually",
        "ticker_manual": "Ticker", "nome_manual": "Name", "setor_manual": "Sector",
        "moeda_base_manual": "Base Currency", "remover_ativos": "Remove Assets",
        "comparar": "📊 Compare Assets", "ativo1": "Asset 1", "ativo2": "Asset 2",
        "email_config": "📧 Email Notifications", "smtp_server": "SMTP Server",
        "smtp_port": "Port", "email_from": "From Email", "email_password": "Password (app password)",
        "email_to": "To Email", "enable_email": "Enable email alerts",
        "performance_sim": "📈 Simulated Performance", "periodo_graf": "Chart Period",
        "intervalo_graf": "Interval", "gerar_relatorio": "📄 Generate Report",
        "ola": "Hello",
        "email_alert_desc1": "The asset",
        "email_alert_desc2": "has reached the configured price",
        "preco_atual": "Current price",
        "condicao": "Condition",
        "preco": "Price",
        "email_alert_cta": "Access Equity Pro to see more details and make your investment decision.",
        "acessar_painel": "Access Dashboard",
        "email_footer": "This is an automated email from Equity Pro. Please do not reply.",
        "login_tab": "Login",
        "signup_tab": "Create Account",
        "username": "Username",
        "password": "Password",
        "confirm_password": "Confirm password",
        "full_name": "Full name",
        "email_optional": "Email (optional)",
        "phone_optional": "Phone (optional)",
        "login_button": "Login",
        "signup_button": "Sign up",
        "remember_me": "Remember me for 30 days",
    },
    "Português (BR)": {
        "titulo_idioma": "IDIOMA", "config": "CONFIGURAÇÕES", "moeda": "Moeda de Exibição:",
        "capital": "Capital para Simulação:", "filtro": "Filtrar por Setor:", "fuso": "Fuso Horário:",
        "todos": "Todos", "status_on": "MERCADO ABERTO", "status_off": "MERCADO FECHADO",
        "alocacao": "📊 Alocação", "terminal": "💡 Terminal", "monitor": "Monitorando setor:",
        "info_cambio": "Câmbio:", "info_detalhe": "Cálculo de compra com base em",
        "quantidade_sugerida": "Quantidade sugerida:",
        "atualizar": "⟲ Atualizar", "historico": "HISTÓRICO", "subtitulo": "Plataforma Profissional de Análise",
        "ultima_at": "Última atualização:", "grafico_h": "Gráficos Técnicos",
        "btn_expandir": "📈 Expandir Todos", "btn_recolher": "📐 Recolher Todos",
        "help_graficos": "Expandir/Recolher todos os gráficos",
        "alertas_titulo": "🔔 Alertas de Preço", "criar_alerta": "Criar Alerta",
        "ticker_alerta": "Ativo", "preco_alerta": "Preço Alvo",
        "acima_abaixo": "Quando o preço estiver", "acima": "acima", "abaixo": "abaixo",
        "backtest_titulo": "📈 Backtest (Médias Móveis)", "periodo_back": "Período",
        "executar_back": "Executar", "exportar": "Exportar Dados", 
        "gerenciar_ativos": "📁 Gerenciar Ativos", "adicionar_manual": "Adicionar manualmente",
        "ticker_manual": "Código", "nome_manual": "Nome", "setor_manual": "Setor",
        "moeda_base_manual": "Moeda Base", "remover_ativos": "Remover Ativos",
        "comparar": "📊 Comparar Ativos", "ativo1": "Ativo 1", "ativo2": "Ativo 2",
        "email_config": "📧 Notificações por E-mail", "smtp_server": "Servidor SMTP",
        "smtp_port": "Porta", "email_from": "E-mail de envio", "email_password": "Senha (app password)",
        "email_to": "E-mail destino", "enable_email": "Ativar alertas por e-mail",
        "performance_sim": "📈 Performance Simulada", "periodo_graf": "Período do gráfico",
        "intervalo_graf": "Intervalo", "gerar_relatorio": "📄 Gerar Relatório",
        "ola": "Olá",
        "email_alert_desc1": "O ativo",
        "email_alert_desc2": "atingiu o preço configurado",
        "preco_atual": "Preço atual",
        "condicao": "Condição",
        "preco": "Preço",
        "email_alert_cta": "Acesse o Equity Pro para ver mais detalhes e tomar sua decisão de investimento.",
        "acessar_painel": "Acessar Painel",
        "email_footer": "Este é um e-mail automático do Equity Pro. Por favor, não responda.",
        "login_tab": "Login",
        "signup_tab": "Criar Conta",
        "username": "Usuário",
        "password": "Senha",
        "confirm_password": "Confirmar senha",
        "full_name": "Nome completo",
        "email_optional": "E-mail (opcional)",
        "phone_optional": "Telefone (opcional)",
        "login_button": "Entrar",
        "signup_button": "Cadastrar",
        "remember_me": "Lembrar acesso por 30 dias",
    },
    "Español": {
        # (similar, por brevidade mantenho igual ao PT mas com tradução para ES, você pode completar depois)
        "titulo_idioma": "IDIOMA", "config": "CONFIGURACIÓN", "moeda": "Moneda:",
        "capital": "Capital de Simulación:", "filtro": "Filtrar por Sector:", "fuso": "Zona Horaria:",
        "todos": "Todos", "status_on": "MERCADO ABIERTO", "status_off": "MERCADO CERRADO",
        "alocacao": "📊 Asignación", "terminal": "💡 Terminal", "monitor": "Monitoreando sector:",
        "info_cambio": "Tipo de cambio:", "info_detalhe": "Cálculo de compra con base en",
        "quantidade_sugerida": "Cantidad sugerida:",
        "atualizar": "⟲ Actualizar", "historico": "HISTÓRICO", "subtitulo": "Plataforma Profesional de Análisis",
        "ultima_at": "Última actualización:", "grafico_h": "Gráficos Técnicos",
        "btn_expandir": "📈 Expandir Todos", "btn_recolher": "📐 Contraer Todos",
        "help_graficos": "Expandir/Contraer todos los gráficos",
        "alertas_titulo": "🔔 Alertas de Precio", "criar_alerta": "Crear Alerta",
        "ticker_alerta": "Activo", "preco_alerta": "Precio Objetivo",
        "acima_abaixo": "Cuando el precio esté", "acima": "encima", "abaixo": "debajo",
        "backtest_titulo": "📈 Backtest (Media Móvil)", "periodo_back": "Período",
        "executar_back": "Ejecutar", "exportar": "Exportar Datos",
        "gerenciar_ativos": "📁 Gestionar Activos", "adicionar_manual": "Agregar manualmente",
        "ticker_manual": "Ticker", "nome_manual": "Nombre", "setor_manual": "Sector",
        "moeda_base_manual": "Moneda Base", "remover_ativos": "Eliminar Activos",
        "comparar": "📊 Comparar Activos", "ativo1": "Activo 1", "ativo2": "Activo 2",
        "email_config": "📧 Notificaciones por Email", "smtp_server": "Servidor SMTP",
        "smtp_port": "Puerto", "email_from": "Email origen", "email_password": "Contraseña",
        "email_to": "Email destino", "enable_email": "Activar alertas por email",
        "performance_sim": "📈 Rendimiento Simulado", "periodo_graf": "Período del gráfico",
        "intervalo_graf": "Intervalo", "gerar_relatorio": "📄 Generar Informe",
        "ola": "Hola",
        "email_alert_desc1": "El activo",
        "email_alert_desc2": "alcanzó el precio configurado",
        "preco_atual": "Precio actual",
        "condicao": "Condición",
        "preco": "Precio",
        "email_alert_cta": "Acceda a Equity Pro para ver más detalles y tomar su decisión de inversión.",
        "acessar_painel": "Acceder al Panel",
        "email_footer": "Este es un correo automático de Equity Pro. Por favor, no responda.",
        "login_tab": "Iniciar sesión",
        "signup_tab": "Crear cuenta",
        "username": "Usuario",
        "password": "Contraseña",
        "confirm_password": "Confirmar contraseña",
        "full_name": "Nombre completo",
        "email_optional": "Correo electrónico (opcional)",
        "phone_optional": "Teléfono (opcional)",
        "login_button": "Iniciar sesión",
        "signup_button": "Registrarse",
        "remember_me": "Recordar acceso por 30 días",
    }
}

def mudar_idioma():
    st.session_state.sel_idioma = st.session_state.idioma_temp

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
# 1. CONFIGURAÇÃO DE PÁGINA
# ===================================================================
st.set_page_config(page_title="Equity Pro - Advanced", layout="wide", page_icon="▣")

# ========== CONTROLE DE AUTENTICAÇÃO ==========
if "autenticado" not in st.session_state:
    st.session_state["autenticado"] = False

# Tenta restaurar login a partir do token na URL
if not st.session_state["autenticado"]:
    token_url = st.query_params.get("session")
    if token_url:
        username = validar_token(token_url)
        if username:
            # Busca os dados do usuário pelo username (já temos função verificar_login? vamos adaptar)
            # Precisamos de uma função para buscar usuário por username. Vamos criar abaixo.
            user = buscar_usuario_por_username(username)
            if user:
                st.session_state["autenticado"] = True
                st.session_state["usuario"] = user
                st.rerun()

def login_ui():
    # Seletor de idioma (acima das abas)
    idioma_choices = list(idiomas.keys())
    col_lang, _ = st.columns([1, 2])
    with col_lang:
        selected_lang = st.selectbox(
            "Language / Idioma / Idioma",
            idioma_choices,
            index=idioma_choices.index(st.session_state.sel_idioma),
            key="login_lang_selector"
        )
        if selected_lang != st.session_state.sel_idioma:
            st.session_state.sel_idioma = selected_lang
            st.rerun()
    
    t = idiomas[st.session_state.sel_idioma]
    
    st.title("〽️ Equity Pro - " + t["login_tab"])
    
    if "aba_atual" not in st.session_state:
        st.session_state["aba_atual"] = t["login_tab"]
    
    if st.session_state.get("cadastro_sucesso", False):
        st.session_state["aba_atual"] = t["login_tab"]
        st.session_state["cadastro_sucesso"] = False
    
    aba = st.radio(
        "",
        [t["login_tab"], t["signup_tab"]],
        index=0 if st.session_state["aba_atual"] == t["login_tab"] else 1,
        horizontal=True,
        key="selecao_aba"
    )
    st.session_state["aba_atual"] = aba
    
    if aba == t["login_tab"]:
        username = st.text_input(t["username"], key="login_user")
        senha = st.text_input(t["password"], type="password", key="login_pass")
        lembrar = st.checkbox(t["remember_me"])
        if st.button(t["login_button"], key="btn_login"):
            user = verificar_login(username, senha)
            if user:
                st.session_state["autenticado"] = True
                st.session_state["usuario"] = user
                if lembrar:
                    token = gerar_token(username)
                    st.query_params["session"] = token
                st.rerun()
            else:
                st.error(t.get("login_error", "Usuário ou senha inválidos"))
    
    else:  # Criar conta
        new_username = st.text_input(t["username"], key="cad_user")
        new_nome = st.text_input(t["full_name"], key="cad_nome")
        new_email = st.text_input(t["email_optional"], key="cad_email")
        new_telefone = st.text_input(t["phone_optional"], key="cad_telefone")
        new_senha = st.text_input(t["password"], type="password", key="cad_pass")
        new_senha2 = st.text_input(t["confirm_password"], type="password", key="cad_pass2")
        if st.button(t["signup_button"], key="btn_cad"):
            if new_senha != new_senha2:
                st.error("Senhas não coincidem")
            elif len(new_username) < 3:
                st.error(t.get("username_min", "Usuário deve ter pelo menos 3 caracteres"))
            else:
                ok = cadastrar_usuario(new_username, new_nome, new_senha, new_email, new_telefone)
                if ok:
                    st.session_state["cadastro_sucesso"] = True
                    st.success(t.get("signup_success", "Usuário criado! Redirecionando para o login..."))
                    st.rerun()
                else:
                    st.error(t.get("signup_error", "Usuário já existe"))

if not st.session_state["autenticado"]:
    login_ui()
    st.stop()

# Se chegou aqui, está autenticado
usuario_logado = st.session_state["usuario"]
st.sidebar.success(f"👤 @{usuario_logado['username']}")
# Carrega alertas do banco de dados
alertas_db = listar_alertas_usuario(usuario_logado['id'])
st.session_state.alertas = []
for alerta_db in alertas_db:
    alerta_id, ticker, preco_alvo, direcao = alerta_db
    moeda_base = get_moeda_base(ticker)
    st.session_state.alertas.append({
        "id": alerta_id,
        "ticker": ticker,
        "preco_original": preco_alvo,
        "moeda_base": moeda_base,
        "direcao": direcao,
        "disparado": False
    })

# Botão de teste de e-mail (temporário) – DESABILITADO 
# with st.sidebar.expander("📧 Testar E-mail"):
#     st.write(f"E-mail cadastrado: **{usuario_logado.get('email', 'Nenhum e-mail cadastrado')}**")
#     if st.button("Enviar e-mail de teste agora"):
#         email_destino = usuario_logado.get('email')
#         if email_destino:
#             from email_utils import enviar_email_gmail
#             assunto = "Teste Equity Pro - Alerta"
#             corpo = f"""
#             <html>
#             <body>
#                 <h2>✅ Teste de notificação</h2>
#                 <p>Olá {usuario_logado['nome']},</p>
#                 <p>Este é um e-mail de teste enviado pelo <strong>Equity Pro</strong> via Gmail.</p>
#                 <p>Se você recebeu, a integração está funcionando perfeitamente!</p>
#                 <hr>
#                 <small>Equity Pro - Análise e Simulação</small>
#             </body>
#             </html>
#             """
#             sucesso = enviar_email_gmail(email_destino, usuario_logado['nome'], assunto, corpo)
#             if sucesso:
#                 st.success("E-mail enviado! Verifique sua caixa de entrada (e o spam).")
#             else:
#                 st.error("Falha no envio. Verifique as credenciais do Gmail nos segredos.")
#         else:
#             st.warning("Você não possui e-mail cadastrado. Cadastre um primeiro.")

if st.sidebar.button("Sair", key="sair"):
    # Limpa token da URL também
    st.query_params.clear()
    del st.session_state["autenticado"]
    del st.session_state["usuario"]
    st.rerun()
# ========== FIM DA AUTENTICAÇÃO ==========

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
    return series.rolling(window=length).mean()

def rsi(series, length=14):
    delta = series.diff()
    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)
    avg_gain = gain.rolling(window=length).mean()
    avg_loss = loss.rolling(window=length).mean()
    rs = avg_gain / avg_loss
    return 100 - (100 / (1 + rs))

def macd(series, fast=12, slow=26, signal=9):
    ema_fast = series.ewm(span=fast, adjust=False).mean()
    ema_slow = series.ewm(span=slow, adjust=False).mean()
    macd_line = ema_fast - ema_slow
    signal_line = macd_line.ewm(span=signal, adjust=False).mean()
    histogram = macd_line - signal_line
    return macd_line, signal_line, histogram

def bollinger_bands(series, length=20, std=2):
    """Calcula Bollinger Bands"""
    rolling_mean = series.rolling(window=length).mean()
    rolling_std = series.rolling(window=length).std()
    upper = rolling_mean + (rolling_std * std)
    lower = rolling_mean - (rolling_std * std)
    return upper, rolling_mean, lower

def stochastic(high, low, close, k_period=14, d_period=3):
    """Calcula Estocástico %K e %D"""
    low_min = low.rolling(window=k_period).min()
    high_max = high.rolling(window=k_period).max()
    stoch_k = 100 * ((close - low_min) / (high_max - low_min))
    stoch_d = stoch_k.rolling(window=d_period).mean()
    return stoch_k, stoch_d

# ===================================================================
# 8. SIDEBAR (configurações, gerenciamento de ativos, e-mail)
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
    st.number_input(t["capital"], min_value=0.0, step=1000.0, value=st.session_state.invest_save, key="invest_save")

    st.divider()
    st.header(t["gerenciar_ativos"])
    with st.expander(t["adicionar_manual"]):
        col1m, col2m = st.columns(2)
        with col1m:
            novo_ticker = st.text_input(t["ticker_manual"], key="novo_ticker")
            novo_nome = st.text_input(t["nome_manual"], key="novo_nome")
        with col2m:
            novo_setor = st.text_input(t["setor_manual"], key="novo_setor")
            nova_moeda = st.selectbox(t["moeda_base_manual"], ["USD", "BRL"], key="nova_moeda")
        if st.button("➕ Adicionar"):
            if novo_ticker and novo_nome:
                st.session_state.meus_ativos.append({
                    "ticker": novo_ticker.upper(),
                    "nome": novo_nome,
                    "setor": novo_setor if novo_setor else "Personalizado",
                    "moeda_base": nova_moeda
                })
                st.success(f"{novo_ticker} adicionado!")
                st.rerun()
    with st.expander(t["remover_ativos"]):
        for idx, ativo in enumerate(st.session_state.meus_ativos):
            col_rem1, col_rem2 = st.columns([3,1])
            col_rem1.write(f"{ativo['ticker']} - {ativo['nome']}")
            if col_rem2.button("🗑️", key=f"rem_{idx}"):
                st.session_state.meus_ativos.pop(idx)
                st.rerun()
    
    st.divider()
    st.header("" + t["alertas_titulo"])

    # Criação de alerta (sempre visível)
    st.subheader("" + t["criar_alerta"])
    col_a1, col_a2 = st.columns(2)
    with col_a1:
        ticker_alerta = st.text_input(t["ticker_alerta"], key="alert_ticker")
    with col_a2:
        preco_alerta = st.number_input(t["preco_alerta"], min_value=0.0, step=1.0, key="alert_price")
    direcao = st.radio(t["acima_abaixo"], [t["acima"], t["abaixo"]], horizontal=True)
    
    if st.button("➕ " + t["criar_alerta"], key="criar_alerta_btn"):
        if ticker_alerta and preco_alerta > 0:
            ticker = ticker_alerta.upper()
            moeda_base = get_moeda_base(ticker)
            brl_rate, eur_rate = get_rates()
            moeda_usuario = st.session_state.moeda_save
    
            # Converte o preço digitado para a moeda original do ativo
            if moeda_usuario == "USD ($)":
                preco_original = preco_alerta * brl_rate if moeda_base == "BRL" else preco_alerta
            elif moeda_usuario == "BRL (R$)":
                preco_original = preco_alerta / brl_rate if moeda_base == "USD" else preco_alerta
            else:
                if moeda_base == "USD":
                    preco_original = preco_alerta / eur_rate
                elif moeda_base == "BRL":
                    preco_original = (preco_alerta / eur_rate) * brl_rate
                else:
                    preco_original = preco_alerta
    
            direcao_sql = "above" if direcao == t["acima"] else "below"
            criar_alerta(usuario_logado['id'], ticker, preco_original, direcao_sql)
    
            # Recarrega lista de alertas do banco
            alertas_db = listar_alertas_usuario(usuario_logado['id'])
            st.session_state.alertas = []
            for alerta_db in alertas_db:
                aid, aticker, apreco, adir = alerta_db
                amoeda_base = get_moeda_base(aticker)
                st.session_state.alertas.append({
                    "id": aid,
                    "ticker": aticker,
                    "preco_original": apreco,
                    "moeda_base": amoeda_base,
                    "direcao": adir,
                    "disparado": False
                })
            st.success(f"Alerta criado para {ticker}")
            st.rerun()
        else:
            st.error("Preencha ticker e preço válido.")
    
    # Listagem de alertas ativos
    if st.session_state.alertas:
        st.write("**Alertas ativos:**")
        brl_rate, eur_rate = get_rates()
        for i, alert in enumerate(st.session_state.alertas):
            preco_visual, simbolo = converter_preco(
                alert["preco_original"],
                alert["moeda_base"],
                st.session_state.moeda_save,
                brl_rate,
                eur_rate
            )
            preco_formatado = formatar_valor_moeda(preco_visual, st.session_state.moeda_save, simbolo)
            st.caption(
                f"{alert['ticker']} - {'acima' if alert['direcao']=='above' else 'abaixo'} "
                f"{preco_formatado}"
            )
        if st.button("🗑️ Limpar todos", key="limpar_todos_alertas"):
            for alert in st.session_state.alertas:
                if alert.get("id"):
                    desativar_alerta(alert["id"])
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
                st.success(f"Backtest concluído. Retorno: {ret*100:.2f}%")
            else:
                st.error("Dados insuficientes.")
        else:
            st.warning("Informe um ticker.")

# ===================================================================
# 9. HEADER E STATUS (com botões)
# ===================================================================
st.markdown(f"<h1 style='font-size:2.5rem;'>〽︎ EQUITY PRO</h1><p>{t['subtitulo']}</p>", unsafe_allow_html=True)

status_label, status_color, status_text = check_market_status()
st.markdown(f"<div style='background-color: {status_color}; padding: 8px; border-radius: 4px; text-align: center; color: white; font-weight: bold; margin-bottom: 20px;'>{status_text}</div>", unsafe_allow_html=True)

col_refresh, col_expand, col_export = st.columns([2, 1, 1])
with col_refresh:
    if st.button(t["atualizar"], use_container_width=True):
        st.rerun()
with col_expand:
    label_btn = t["btn_expandir"] if not st.session_state.show_all_charts else t["btn_recolher"]
    if st.button(label_btn, use_container_width=True, help=t["help_graficos"]):
        st.session_state.show_all_charts = not st.session_state.show_all_charts
        st.rerun()
with col_export:
    if st.button(f"📥 {t['exportar']}", use_container_width=True):
        if ativos_f:
            ticker_exp = ativos_f[0]['ticker']
            yf_ticker = ticker_exp.replace("BINANCE:", "").replace("USDT", "-USD")
            hist_exp = yf.download(yf_ticker, period="1mo", progress=False)
            if not hist_exp.empty:
                if isinstance(hist_exp.columns, pd.MultiIndex):
                    hist_exp.columns = hist_exp.columns.get_level_values(0)
                csv = hist_exp.to_csv().encode('utf-8')
                st.download_button("Download CSV", csv, f"{ticker_exp}_data.csv", "text/csv", key="export_csv_btn")
            else:
                st.warning("Sem dados.")
        else:
            st.warning("Nenhum ativo.")

st.caption(f"{t['ultima_at']} {get_now_local().strftime('%H:%M:%S')}")

# ===================================================================
# 10. ALOACAO E TERMINAL
# ===================================================================
col1, col2 = st.columns([1, 2])
with col1:
    st.subheader(t["alocacao"])
    df_pizza = pd.DataFrame(st.session_state.meus_ativos)
    if st.session_state.setor_selector != t["todos"] and st.session_state.setor_selector in df_pizza['setor'].values:
        df_pizza = df_pizza[df_pizza['setor'] == st.session_state.setor_selector]
    fig_pizza = px.pie(df_pizza, names='setor', hole=0.4, template="plotly_dark", color_discrete_sequence=px.colors.qualitative.Set2)
    fig_pizza.update_layout(margin=dict(l=0, r=0, t=10, b=0), height=230, showlegend=False)
    st.plotly_chart(fig_pizza, use_container_width=True, config={'displaylogo': False})

with col2:
    st.subheader(t["terminal"])
    st.write(f"{t['monitor']} **{st.session_state.setor_selector if st.session_state.setor_selector != t['todos'] else t['todos']}**")
    brl_rate, eur_rate = get_rates()
    taxa_ex = brl_rate if "BRL" in st.session_state.moeda_save else (eur_rate if "EUR" in st.session_state.moeda_save else 1.0)
    simb_m = "BRL" if "BRL" in st.session_state.moeda_save else ("EUR" if "EUR" in st.session_state.moeda_save else "USD")
    st.info(f"{t['info_cambio']} **1 USD = {taxa_ex:.2f} {simb_m}**.")

st.divider()

# ===================================================================
# 11. FILTRO DE SETOR E LISTA DE ATIVOS
# ===================================================================
setores_lista = sorted(list(set([a['setor'] for a in st.session_state.meus_ativos])))
filtro_setor = st.selectbox(t["filtro"], [t["todos"]] + setores_lista, key="setor_selector")
ativos_f = st.session_state.meus_ativos if filtro_setor == t["todos"] else [a for a in st.session_state.meus_ativos if a['setor'] == filtro_setor]

# ===================================================================
# 12. CARDS DE ATIVOS (com gráficos interativos e período selecionável)
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
            preco_formatado = formatar_valor_moeda(p_conv, st.session_state.moeda_save, simb)
            st.markdown(f"### {preco_formatado}")
            cor_var = '#26a69a' if change >= 0 else '#ef5350'
            seta = '▲' if change >= 0 else '▼'
            st.markdown(f"<p style='color:{cor_var}; font-weight:bold;'>{seta} {abs(change):.2f}%</p>", unsafe_allow_html=True)

            # Quantidade sugerida
            invest_usd = st.session_state.invest_save
            if st.session_state.moeda_save == "BRL (R$)":
                invest_usd = invest_usd / brl_rate
            elif st.session_state.moeda_save == "EUR (€)":
                invest_usd = invest_usd / eur_rate
            if moeda_base == "BRL":
                invest_local = invest_usd * brl_rate
                qtd_sugerida = invest_local / price if price > 0 else 0
            else:
                qtd_sugerida = invest_usd / price if price > 0 else 0
                capital_formatado = formatar_valor_moeda(st.session_state.invest_save, st.session_state.moeda_save, simb_m)
                st.caption(f"{t['info_detalhe']} {capital_formatado} → {t['quantidade_sugerida']} **{qtd_sugerida:.4f}**")
                st.caption(f"Code: `{ticker}`")

            # GRÁFICOS COM SELETOR DE PERÍODO E INDICADORES AVANÇADOS
            with st.expander(f"📈 {t['grafico_h']}", expanded=st.session_state.show_all_charts):
                # Seletor de período e intervalo
                periodo_map = {
                    "1d": ("1d", "1m"),
                    "5d": ("5d", "5m"),
                    "1mo": ("1mo", "1d"),
                    "3mo": ("3mo", "1d"),
                    "1y": ("1y", "1wk")
                }
                periodo_esc = st.selectbox(t["periodo_graf"], list(periodo_map.keys()), key=f"per_{ticker}_{i}")
                intervalo_esc = periodo_map[periodo_esc][1]
                
                try:
                    yf_ticker = ticker.replace("BINANCE:", "").replace("USDT", "-USD")
                    hist = yf.download(yf_ticker, period=periodo_esc, interval=intervalo_esc, progress=False)
                    if not hist.empty and len(hist) > 20:
                        # Simplificar colunas
                        if isinstance(hist.columns, pd.MultiIndex):
                            hist.columns = hist.columns.get_level_values(0)
                        
                        # Calcular indicadores
                        hist['SMA20'] = sma(hist['Close'], 20)
                        hist['SMA50'] = sma(hist['Close'], 50)
                        hist['RSI'] = rsi(hist['Close'], 14)
                        macd_line, signal_line, hist['MACD_hist'] = macd(hist['Close'])
                        hist['MACD'] = macd_line
                        hist['MACD_signal'] = signal_line
                        # Bollinger Bands
                        upper_bb, middle_bb, lower_bb = bollinger_bands(hist['Close'])
                        hist['BB_upper'] = upper_bb
                        hist['BB_middle'] = middle_bb
                        hist['BB_lower'] = lower_bb
                        # Estocástico
                        stoch_k, stoch_d = stochastic(hist['High'], hist['Low'], hist['Close'])
                        hist['Stoch_K'] = stoch_k
                        hist['Stoch_D'] = stoch_d
                        
                        # Detectar coluna de volume
                        col_volume = next((col for col in hist.columns if 'volume' in col.lower()), None)
                        
                        # Seletor de tipo de gráfico (expandido)
                        tipo_grafico = st.radio(
                            "Tipo de gráfico:",
                            ["Candlestick", "Volume", "RSI", "MACD", "Bollinger Bands", "Estocástico"],
                            horizontal=True,
                            key=f"graf_sel_{ticker}_{i}"
                        )
                        
                        if tipo_grafico == "Candlestick":
                            fig = go.Figure()
                            fig.add_trace(go.Candlestick(x=hist.index, open=hist['Open'], high=hist['High'],
                                                         low=hist['Low'], close=hist['Close'], name='Candlestick'))
                            fig.add_trace(go.Scatter(x=hist.index, y=hist['SMA20'], mode='lines', name='SMA20', line=dict(color='orange')))
                            fig.add_trace(go.Scatter(x=hist.index, y=hist['SMA50'], mode='lines', name='SMA50', line=dict(color='purple')))
                            fig.update_layout(title=f"{ticker} - Candle + Médias", height=400, xaxis_rangeslider_visible=False)
                            st.plotly_chart(fig, use_container_width=True)
                            
                        elif tipo_grafico == "Volume":
                            if col_volume:
                                fig = px.bar(hist, x=hist.index, y=col_volume, title="Volume", color_discrete_sequence=['lightblue'])
                                fig.update_layout(height=400)
                                st.plotly_chart(fig, use_container_width=True)
                            else:
                                st.info("Dados de volume não disponíveis")
                                
                        elif tipo_grafico == "RSI":
                            fig = px.line(hist, x=hist.index, y='RSI', title="RSI (14)")
                            fig.add_hline(y=70, line_dash="dash", line_color="red")
                            fig.add_hline(y=30, line_dash="dash", line_color="green")
                            fig.update_yaxes(range=[0,100])
                            fig.update_layout(height=400)
                            st.plotly_chart(fig, use_container_width=True)
                            
                        elif tipo_grafico == "MACD":
                            fig = go.Figure()
                            fig.add_trace(go.Scatter(x=hist.index, y=hist['MACD'], name='MACD'))
                            fig.add_trace(go.Scatter(x=hist.index, y=hist['MACD_signal'], name='Signal'))
                            fig.add_bar(x=hist.index, y=hist['MACD_hist'], name='Histogram')
                            fig.update_layout(title="MACD", height=400)
                            st.plotly_chart(fig, use_container_width=True)
                            
                        elif tipo_grafico == "Bollinger Bands":
                            fig = go.Figure()
                            fig.add_trace(go.Scatter(x=hist.index, y=hist['Close'], name='Preço', line=dict(color='blue')))
                            fig.add_trace(go.Scatter(x=hist.index, y=hist['BB_upper'], name='BB Superior', line=dict(color='red', dash='dash')))
                            fig.add_trace(go.Scatter(x=hist.index, y=hist['BB_lower'], name='BB Inferior', line=dict(color='green', dash='dash')))
                            fig.add_trace(go.Scatter(x=hist.index, y=hist['BB_middle'], name='Média', line=dict(color='orange')))
                            fig.update_layout(title="Bollinger Bands", height=400)
                            st.plotly_chart(fig, use_container_width=True)
                            
                        elif tipo_grafico == "Estocástico":
                            fig = go.Figure()
                            fig.add_trace(go.Scatter(x=hist.index, y=hist['Stoch_K'], name='%K'))
                            fig.add_trace(go.Scatter(x=hist.index, y=hist['Stoch_D'], name='%D'))
                            fig.add_hline(y=80, line_dash="dash", line_color="red")
                            fig.add_hline(y=20, line_dash="dash", line_color="green")
                            fig.update_yaxes(range=[0,100])
                            fig.update_layout(title="Estocástico", height=400)
                            st.plotly_chart(fig, use_container_width=True)
                            
                        # Performance simulada
                        st.subheader(t["performance_sim"])
                        capital_inicial = st.session_state.invest_save
                        # Converter preços para moeda de exibição para simulação (simplificado)
                        retornos = hist['Close'].pct_change().dropna()
                        patrimonio = capital_inicial * (1 + retornos).cumprod()
                        fig_perf = px.line(x=patrimonio.index, y=patrimonio, title="Evolução do Patrimônio", labels={"x": "Data", "y": f"Patrimônio ({simb})"})
                        fig_perf.update_layout(height=300)
                        st.plotly_chart(fig_perf, use_container_width=True)
                        patrimonio_final_formatado = formatar_valor_moeda(patrimonio.iloc[-1], st.session_state.moeda_save, simb)
                        st.caption(f"Patrimônio final: {patrimonio_final_formatado}")

                        # Botão gerar relatório
                        if st.button(t["gerar_relatorio"], key=f"rel_{ticker}_{i}"):
                            html_report = generate_report_html(ticker, ativo['nome'], price, change, hist, "", capital_inicial)
                            st.download_button("Download Relatório HTML", html_report, f"relatorio_{ticker}.html", "text/html")
                            
                    else:
                        st.warning("Dados históricos insuficientes para gráficos avançados.")
                except Exception as e:
                    st.error(f"Erro no gráfico: {str(e)}")

# ===================================================================
# 13. COMPARAÇÃO DE DOIS ATIVOS
# ===================================================================
st.divider()
st.header(t["comparar"])
col_c1, col_c2 = st.columns(2)
with col_c1:
    ativo1 = st.selectbox(t["ativo1"], [a['ticker'] for a in st.session_state.meus_ativos], key="comp1")
with col_c2:
    ativo2 = st.selectbox(t["ativo2"], [a['ticker'] for a in st.session_state.meus_ativos], key="comp2")
if ativo1 and ativo2 and ativo1 != ativo2:
    try:
        df1 = yf.download(ativo1, period="1mo", interval="1d", progress=False)
        df2 = yf.download(ativo2, period="1mo", interval="1d", progress=False)
        if not df1.empty and not df2.empty:
            # Normalizar preços (base 100)
            norm1 = df1['Close'] / df1['Close'].iloc[0] * 100
            norm2 = df2['Close'] / df2['Close'].iloc[0] * 100
            fig_comp = go.Figure()
            fig_comp.add_trace(go.Scatter(x=norm1.index, y=norm1, name=ativo1))
            fig_comp.add_trace(go.Scatter(x=norm2.index, y=norm2, name=ativo2))
            fig_comp.update_layout(title="Comparação de Preços (Base 100)", yaxis_title="Preço Normalizado", height=400)
            st.plotly_chart(fig_comp, use_container_width=True)
            
            # Correlação
            correl = df1['Close'].corr(df2['Close'])
            st.metric("Correlação", f"{correl:.4f}")
        else:
            st.warning("Dados insuficientes para comparação.")
    except Exception as e:
        st.error(f"Erro na comparação: {e}")

# ===================================================================
# 14. BACKTEST RESULTADOS
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
# 15. ALERTAS (com e-mail via Gmail e conversão de moeda)
# ===================================================================
if st.session_state.alertas:
    brl_rate, eur_rate = get_rates()   # taxas atualizadas
    for alerta in st.session_state.alertas:
        if alerta.get("disparado", False):
            continue

        # Preço atual na moeda original do ativo
        preco_atual, _ = get_safe_quote(alerta["ticker"])
        if preco_atual <= 0:
            continue

        # Comparação usando o preço original (armazenado)
        disparar = False
        if alerta["direcao"] == "above" and preco_atual >= alerta["preco_original"]:
            disparar = True
        elif alerta["direcao"] == "below" and preco_atual <= alerta["preco_original"]:
            disparar = True

        if disparar:
            msg = f"ALERTA: {alerta['ticker']} atingiu o preço!"
            st.toast(f"🔔 {msg}", icon="⚠️")

            # Envio de e-mail usando Gmail
            if usuario_logado.get('email'):
                from email_utils import enviar_email_gmail

                # Moeda de exibição atual do usuário
                moeda_destino = st.session_state.moeda_save

                # Converte preço atual e preço alvo para a moeda de exibição
                preco_atual_conv, simbolo = converter_preco(
                    preco_atual,
                    alerta["moeda_base"],
                    moeda_destino,
                    brl_rate,
                    eur_rate
                )
                preco_alvo_conv, _ = converter_preco(
                    alerta["preco_original"],
                    alerta["moeda_base"],
                    moeda_destino,
                    brl_rate,
                    eur_rate
                )

                # Tradução da direção
                texto_direcao = t["acima"] if alerta["direcao"] == "above" else t["abaixo"]

                assunto = f"🔔 {t['alertas_titulo']} - {alerta['ticker']}"

                preco_atual_formatado = formatar_valor_moeda(preco_atual_conv, moeda_destino, simbolo)
                preco_alvo_formatado = formatar_valor_moeda(preco_alvo_conv, moeda_destino, simbolo)
                
                corpo_html = f"""
                <html>
                <head>
                    <style>
                        body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
                        .container {{ max-width: 600px; margin: 0 auto; padding: 20px; border: 1px solid #ddd; border-radius: 8px; background-color: #f9f9f9; }}
                        .header {{ text-align: center; padding-bottom: 10px; border-bottom: 2px solid #007bff; }}
                        .price {{ font-size: 28px; font-weight: bold; color: #007bff; }}
                        .alert-detail {{ background-color: #fff3cd; padding: 10px; border-left: 4px solid #ffc107; margin: 15px 0; }}
                        .footer {{ font-size: 12px; color: #777; text-align: center; margin-top: 20px; border-top: 1px solid #ddd; padding-top: 10px; }}
                        .button {{ display: inline-block; background-color: #007bff; color: white; text-decoration: none; padding: 10px 20px; border-radius: 5px; margin-top: 15px; }}
                    </style>
                </head>
                <body>
                    <div class="container">
                        <div class="header">
                            <h2>🔔 {t['alertas_titulo']} - Equity Pro</h2>
                        </div>
                        <div class="content">
                            <p>{t['ola']} <strong>{usuario_logado['nome']}</strong>,</p>
                            <p>{t['email_alert_desc1']} <strong>{alerta['ticker']}</strong> {t['email_alert_desc2']}:</p>
                            <div class="alert-detail">
                                <p><strong>{t['preco_atual']}:</strong> <span class="price">{preco_atual_formatado}</span></p>
                                <p><strong>{t['condicao']}:</strong> {t['preco']} {texto_direcao} <strong>{preco_atual_formatado}</strong></p>
                            </div>
                            <p>{t['email_alert_cta']}</p>
                            <p style="text-align: center;">
                                <a href="https://equityproapp-jrsiqueira.streamlit.app" class="button">{t['acessar_painel']}</a>
                            </p>
                        </div>
                        <div class="footer">
                            <p>{t['email_footer']}</p>
                            <p>© 2025 Equity Pro - {t['subtitulo']}</p>
                        </div>
                    </div>
                </body>
                </html>
                """
                enviar_email_gmail(usuario_logado['email'], usuario_logado['nome'], assunto, corpo_html)
            else:
                st.warning("Usuário não possui e-mail cadastrado. Alerta não enviado.")

            # Desativa o alerta no banco de dados (para não reenviar e-mail na próxima verificação)
            if alerta.get("id"):
                from database import desativar_alerta
                desativar_alerta(alerta["id"])

            # Marca como disparado
            alerta["disparado"] = True

# ===================================================================
# 16. REFRESH AUTOMÁTICO
# ===================================================================
status_label, _, _ = check_market_status()
if status_label == "ON":
    st_autorefresh(interval=30000, key="refresh_on")
else:
    st_autorefresh(interval=600000, key="refresh_off")
