import sqlite3
import bcrypt

DB_NAME = "equity_pro.db"

def get_connection():
    return sqlite3.connect(DB_NAME)

def init_db():
    """Cria a tabela de usuários se não existir."""
    with get_connection() as conn:
        cursor = conn.cursor()
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
        # Tabela de alertas personalizados (cada usuário tem seus alertas)
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

def cadastrar_usuario(username, nome, senha, email=None, telefone=None):
    """Insere um novo usuário com senha criptografada."""
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
    """Retorna o usuário se a senha estiver correta, senão None."""
    with get_connection() as conn:
        cursor = conn.execute("SELECT id, username, nome, email, telefone, senha_hash FROM usuarios WHERE username = ?", (username,))
        user = cursor.fetchone()
    if user and bcrypt.checkpw(senha.encode('utf-8'), user[5].encode('utf-8')):
        return {"id": user[0], "username": user[1], "nome": user[2], "email": user[3], "telefone": user[4]}
    return None

def salvar_preferencias(usuario_id, email=None, telefone=None):
    """Atualiza e-mail e telefone do usuário."""
    with get_connection() as conn:
        conn.execute("UPDATE usuarios SET email = COALESCE(?, email), telefone = COALESCE(?, telefone) WHERE id = ?",
                     (email, telefone, usuario_id))
        conn.commit()

def adicionar_alerta(usuario_id, ticker, preco_alvo, direcao):
    with get_connection() as conn:
        conn.execute(
            "INSERT INTO alertas (usuario_id, ticker, preco_alvo, direcao) VALUES (?, ?, ?, ?)",
            (usuario_id, ticker.upper(), preco_alvo, direcao)
        )
        conn.commit()

def listar_alertas_usuario(usuario_id):
    with get_connection() as conn:
        cursor = conn.execute("SELECT id, ticker, preco_alvo, direcao FROM alertas WHERE usuario_id = ? AND ativo = 1", (usuario_id,))
        return cursor.fetchall()
