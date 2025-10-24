import discord
from discord.ext import commands
import sqlite3
from database.database_manager import DB_FILE

import config
# --- CHECK FUNCTIONS ---

async def is_super_admin(ctx: commands.Context) -> bool:
    """Verifica se o autor é um Super Admin (definido no bot.py)."""
    # ctx.bot se refere à instância principal da classe RedCommunityBot
    return ctx.author.id in ctx.bot.super_admin_ids

async def has_admin_role(ctx: commands.Context) -> bool:
    """Verifica se o autor tem permissão de admin (Super, Nativa ou Cargo)."""
    # 1. Super Admin (definido no bot.py) pode usar
    if ctx.author.id in ctx.bot.super_admin_ids:
        return True

    # 2. Membros com permissão de "Administrador" no servidor podem usar
    if ctx.author.guild_permissions.administrator:
        return True

    # 3. Verifica cargos customizados no DB
    with sqlite3.connect(DB_FILE) as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT role_id FROM perm_roles WHERE guild_id = ?", (ctx.guild.id,))
        perm_role_ids = {row[0] for row in cursor.fetchall()}
    
    if not perm_role_ids:
        # Se nenhum cargo estiver configurado, a verificação falha.
        # Apenas Super Admins (verificados no início da função) terão acesso.
        return False

    author_role_ids = {role.id for role in ctx.author.roles}
    # Retorna True se houver qualquer intersecção entre os cargos do autor e os cargos permitidos
    return not author_role_ids.isdisjoint(perm_role_ids)

def is_call_server():
    """Verifica se o comando foi usado em um servidor de 'call'."""
    async def predicate(ctx: commands.Context) -> bool:
        return ctx.guild.id in config.CALL_SERVERS_IDS
    return commands.check(predicate)

def is_chat_server():
    """Verifica se o comando foi usado em um servidor de 'chat'."""
    async def predicate(ctx: commands.Context) -> bool:
        return ctx.guild.id in config.CHAT_SERVERS_IDS
    return commands.check(predicate)
