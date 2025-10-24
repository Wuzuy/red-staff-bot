# Importa a classe do bot e o token
from core import RedCommunityBot
from config import DISCORD_TOKEN

if __name__ == "__main__":
    if not DISCORD_TOKEN:
        print("Erro: O DISCORD_TOKEN não foi encontrado. Verifique seu arquivo .env")
    else:
        bot = RedCommunityBot()
        bot.run(DISCORD_TOKEN)

