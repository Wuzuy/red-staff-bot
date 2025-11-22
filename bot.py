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

    # Carregar cogs de comandos
    for folder in ['commands/geral', 'commands/setor_chat', 'commands/setor_call']:
        for filename in os.listdir(f'./{folder}'):
            if filename.endswith('.py'):
                await bot.load_extension(f'{folder.replace("/", ".")}.{filename[:-3]}')

    # Carregar cogs de listeners/eventos
    for filename in os.listdir('./listeners'):
        if filename.endswith('.py'):
            await bot.load_extension(f'listeners.{filename[:-3]}')

    await bot.start(DISCORD_TOKEN)

if __name__ == "__main__":
    asyncio.run(main())
