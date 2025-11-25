from core import RedCommunityBot
import os
from dotenv import load_dotenv
import asyncio

load_dotenv()
DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")

async def main():
    """Função principal para inicializar e rodar o bot."""
    if not DISCORD_TOKEN:
        print("Erro: O DISCORD_TOKEN não foi encontrado. Verifique seu arquivo .env")
        return

    bot = RedCommunityBot()

    # O carregamento de cogs agora é feito automaticamente
    # pelo método setup_hook() na classe RedCommunityBot em core.py
    await bot.start(DISCORD_TOKEN)

if __name__ == "__main__":
    asyncio.run(main())
