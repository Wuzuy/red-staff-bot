from core import RedCommunityBot
import os
from dotenv import load_dotenv

load_dotenv()
DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")

if __name__ == "__main__":
    if not DISCORD_TOKEN:
        print("Erro: O DISCORD_TOKEN não foi encontrado. Verifique seu arquivo .env")
    else:
        bot = RedCommunityBot()
        bot.run(DISCORD_TOKEN)
