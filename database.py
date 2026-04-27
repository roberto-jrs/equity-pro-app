import sqlite3
import bcrypt
import os

# Usa um nome único para evitar conflitos
DB_NAME = "equity_pro_final.db"

def get_connection():
    return sqlite3.connect(DB_NAME)

def init_db():
    """Cria a tabela de usuários se não existir."""
    with get_connection() as conn:
        cursor = conn.cursor()
        # Tabela de usuários com todos os campos necessários
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS usuarios (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL,
                nome TEXT NOT NULL,
                email TEXT,
                telefone TEXT,
                senha_hash TEXT NOT NULL,
                data_registro TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        # Tabela de alertas
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS alertas (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                usuario_id INTEGER,
                ticker TEXT NOT NULL,
                preco_alvo REAL NOT NULL,
                direcao TEXT CHECK(direcao IN ('above','below')),
                ativo BOOLEAN DEFAULT 1,
                ultimo_disparo TIMESTAMP,
                FOREIGN KEY(usuario_id) REFERENCES usuarios(id)
            )
        ''')
        conn.commit()

# Inicializa o banco imediatamente ao importar o módulo
init_db()

def cadastrar_usuario(username, nome, senha, email=None, telefone=None):
    hashed = bcrypt.hashpw(senha.encode('utf-8'), bcrypt.gensalt())
    with get_connection() as conn:
        try:
            conn.execute(
                "INSERT INTO usuarios (username, nome, senha_hash, email, telefone) VALUES (?, ?, ?, ?, ?)",
                (username, nome, hashed.decode('utf-8'), email, telefone)
            )
            conn.commit()
            return True
        except sqlite3.IntegrityError:
            return False

def verificar_login(username, senha):
    with get_connection() as conn:
        cursor = conn.execute(
            "SELECT id, username, nome, email, telefone, senha_hash FROM usuarios WHERE username = ?",
            (username,)
        )
        user = cursor.fetchone()
    if user and bcrypt.checkpw(senha.encode('utf-8'), user[5].encode('utf-8')):
        return {
            "id": user[0],
            "username": user[1],
            "nome": user[2],
            "email": user[3],
            "telefone": user[4]
        }
    return None

def salvar_preferencias(usuario_id, email=None, telefone=None):
    with get_connection() as conn:
        if email is not None:
            conn.execute("UPDATE usuarios SET email = ? WHERE id = ?", (email, usuario_id))
        if telefone is not None:
            conn.execute("UPDATE usuarios SET telefone = ? WHERE id = ?", (telefone, usuario_id))
        conn.commit()
