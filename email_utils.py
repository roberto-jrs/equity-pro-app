import streamlit as st
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

def enviar_email_gmail(destino_email, nome_destino, assunto, mensagem_html):
    """
    Envia e-mail usando servidor SMTP do Gmail.
    O remetente e a senha são lidos dos segredos.
    """
    try:
        remetente = st.secrets["GMAIL_USER"]
        senha_app = st.secrets["GMAIL_PASSWORD"]
        
        # Monta a mensagem
        msg = MIMEMultipart()
        msg['From'] = remetente
        msg['To'] = destino_email
        msg['Subject'] = assunto
        
        # Anexa o corpo HTML
        msg.attach(MIMEText(mensagem_html, 'html'))
        
        # Conecta ao servidor Gmail e envia
        with smtplib.SMTP('smtp.gmail.com', 587) as server:
            server.starttls()
            server.login(remetente, senha_app)
            server.send_message(msg)
        
        print(f"E-mail enviado para {destino_email}")
        return True
    except Exception as e:
        print(f"Erro ao enviar e-mail: {e}")
        return False
