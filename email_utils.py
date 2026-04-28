import brevo_python
from brevo_python.rest import ApiException
import streamlit as st

def enviar_email_brevo(destino_email, nome_destino, assunto, mensagem_html):
    """
    Envia e-mail usando a API do Brevo.
    destino_email: string com e-mail do destinatário.
    nome_destino: nome da pessoa (opcional).
    assunto: assunto do e-mail.
    mensagem_html: corpo do e-mail em HTML.
    Retorna True se enviou com sucesso, False caso contrário.
    """
    try:
        config = brevo_python.Configuration()
        config.api_key['api-key'] = st.secrets["BREVO_API_KEY"]
        api_instance = brevo_python.TransactionalEmailsApi(brevo_python.ApiClient(config))
        
        email = {
            "to": [{"email": destino_email, "name": nome_destino}],
            "sender": {"email": "equitypro@seudominio.com", "name": "Equity Pro"},
            "subject": assunto,
            "html_content": mensagem_html
        }
        api_instance.send_transac_email(email)
        return True
    except ApiException as e:
        print(f"Erro Brevo: {e}")
        return False
