import os
from dotenv import load_dotenv

# Carrega as variáveis do arquivo .env
load_dotenv()

# --- TOKENS E IDs ---
DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")

# IDs dos Super Admins (donos do bot)
SUPER_ADMIN_IDS = [SUPER_ADMIN_ID, SUPER_ADMIN_ID_2, DEVELOPER_ID]

# IDs dos servidores para comandos específicos
CALL_SERVERS_IDS = [CALL_SERVER_ID, CALL_SERVER_ID_2]
CHAT_SERVERS_IDS = [CALL_SERVER_ID]
