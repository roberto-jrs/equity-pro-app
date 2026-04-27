import streamlit as st
import streamlit_authenticator as stauth

config = {
    'credentials': {
        'usernames': {
            'teste': {
                'name': 'Usuário Teste',
                'password': '$2b$12$EixZaYVK1fsbw1ZfbX3OXePaWxn96p36WQoeG6Lruj3vjPGga31lW'  # senha 'teste'
            }
        }
    },
    'cookie': {'expiry_days': 30, 'key': 'some_key', 'name': 'some_cookie_name'},
    'preauthorized': {'emails': []}
}

authenticator = stauth.Authenticate(config['credentials'], config['cookie']['name'], config['cookie']['key'], config['cookie']['expiry_days'])
authenticator.login()
