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
                log_channel_id INTEGER
            )
        """)

        # Adiciona colunas à tabela server_configs se não existirem (forma segura)
        try:
            cursor.execute("ALTER TABLE server_configs ADD COLUMN birthday_channel_id INTEGER;")
        except sqlite3.OperationalError: pass # Ignora se a coluna já existe
        try:
            cursor.execute("ALTER TABLE server_configs ADD COLUMN birthday_message_id INTEGER;")
        except sqlite3.OperationalError: pass # Ignora se a coluna já existe

        
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

        # Tabela para agendamento de DMs por servidor
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS scheduled_dms (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                guild_id INTEGER NOT NULL,
                message TEXT NOT NULL,
                send_time TEXT NOT NULL, -- Formato HH:MM
                days_of_week TEXT NOT NULL, -- "0,1,2,3,4,5,6" (Seg-Dom)
                created_by INTEGER NOT NULL
            )
        """)

        # Tabela para agendamento de DMs globais
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS scheduled_dmall (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                message TEXT NOT NULL,
                send_time TEXT NOT NULL, -- Formato HH:MM
                days_of_week TEXT NOT NULL, -- "0,1,2,3,4,5,6" (Seg-Dom)
                created_by INTEGER NOT NULL
            )
        """)
        
        conn.commit()
    print("Banco de dados inicializado com sucesso.")
