import discord
from discord.ext import commands
import sqlite3
from database.database_manager import DB_FILE

CALL_SERVERS_IDS = [CALL_SERVER_ID, CALL_SERVER_ID_2]
CHAT_SERVERS_IDS = [CALL_SERVER_ID]

async def is_super_admin(ctx: commands.Context) -> bool:
    """Verifica se o autor é um Super Admin (definido no bot.py)."""
    return ctx.author.id in ctx.bot.super_admin_ids

async def has_admin_role(ctx: commands.Context) -> bool:
    """Verifica se o autor tem permissão de admin (Super, Nativa ou Cargo)."""
    if ctx.author.id in ctx.bot.super_admin_ids:
        return True

    if ctx.author.guild_permissions.administrator:
        return True

    with sqlite3.connect(DB_FILE) as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT role_id FROM perm_roles WHERE guild_id = ?", (ctx.guild.id,))
        perm_role_ids = {row[0] for row in cursor.fetchall()}
    
    if not perm_role_ids:
        return False

    author_role_ids = {role.id for role in ctx.author.roles}
    return not author_role_ids.isdisjoint(perm_role_ids)

def is_call_server():
    """Verifica se o comando foi usado em um servidor de 'call'."""
    async def predicate(ctx: commands.Context) -> bool:
        return ctx.guild.id in CALL_SERVERS_IDS
    predicate.is_sector_check = True # Atributo para identificação
    return commands.check(predicate)

def is_chat_server():
    """Verifica se o comando foi usado em um servidor de 'chat'."""
    async def predicate(ctx: commands.Context) -> bool:
        return ctx.guild.id in CHAT_SERVERS_IDS
    predicate.is_sector_check = True # Atributo para identificação
    return commands.check(predicate)
