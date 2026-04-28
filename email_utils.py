import streamlit as st
import sib_api_v3_sdk
from sib_api_v3_sdk.rest import ApiException

def enviar_email_brevo(destino_email, nome_destino, assunto, mensagem_html):
    """
    Envia e-mail usando a API do Brevo (Sendinblue).
    """
    try:
        # Configuração da API com a chave armazenada nos segredos
        configuration = sib_api_v3_sdk.Configuration()
        configuration.api_key['api-key'] = st.secrets["BREVO_API_KEY"]
        
        api_instance = sib_api_v3_sdk.TransactionalEmailsApi(sib_api_v3_sdk.ApiClient(configuration))
        
        # Monta o e-mail
        email = sib_api_v3_sdk.SendSmtpEmail(
            to=[{"email": destino_email, "name": nome_destino}],
            sender={"email": "equity.pro.jr@gmail.com", "name": "Equity Pro"},
            subject=assunto,
            html_content=mensagem_html
        )
        
        # Envia
        api_instance.send_transac_email(email)
        return True
    except ApiException as e:
        print(f"Erro ao enviar e-mail via Brevo: {e}")
        return False
