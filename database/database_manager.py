import sqlite3
import os

# Define o caminho para o arquivo do banco de dados na pasta raiz do projeto
# __file__ é o caminho deste arquivo (database/database_manager.py)
# os.path.dirname(__file__) é a pasta 'database'
# '..' sobe um nível, para a pasta raiz 'RedCommunity'
DB_FILE = os.path.join(os.path.dirname(__file__), '..', 'database.db')

def initialize_database():
    """Cria as tabelas do banco de dados se elas não existirem."""
    
    with sqlite3.connect(DB_FILE) as conn:
        cursor = conn.cursor()
        
        print("Verificando e criando tabelas do banco de dados...")
        
        # Tabela de configurações de log por servidor
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS server_configs (
            guild_id INTEGER PRIMARY KEY, 
            log_channel_id INTEGER,
            birthday_channel_id INTEGER,
            birthday_message_id INTEGER
        )
        """)
        
        # Tabela de cargos com permissão de admin por servidor
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS perm_roles (
            guild_id INTEGER,
            role_id INTEGER,
            PRIMARY KEY (guild_id, role_id)
        )
        """)

        # Tabela de cargos que receberão DMs em massa
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS dm_roles (
            guild_id INTEGER,
            role_id INTEGER,
            PRIMARY KEY (guild_id, role_id)
        )
        """)

        # Tabela para armazenar aniversários
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS birthdays (
            guild_id INTEGER,
            user_id INTEGER,
            birthday_month INTEGER,
            birthday_day INTEGER,
            PRIMARY KEY (guild_id, user_id)
        )
        """)
        
        conn.commit()
    print("Banco de dados inicializado com sucesso.")
