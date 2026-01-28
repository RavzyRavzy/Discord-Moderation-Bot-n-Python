import discord
from discord.ext import commands
from datetime import datetime, timezone
import aiosqlite

class Log(commands.Cog):
    def __init__(self, bot, db_manager):
        self.bot = bot
        self.db = db_manager

    async def get_log_channel(self, guild: discord.Guild):
        """Denetim kanalı varsa döndür, yoksa oluştur"""
        channel = discord.utils.get(guild.text_channels, name="denetim-log")
        if not channel:
            overwrites = {guild.default_role: discord.PermissionOverwrite(send_messages=True)}
            channel = await guild.create_text_channel("denetim-log", overwrites=overwrites)
        return channel

    async def send_embed(self, guild_id, title, fields: dict):
        guild = self.bot.get_guild(guild_id)
        if not guild:
            return
        channel = await self.get_log_channel(guild)
        embed = discord.Embed(title=title, color=0xff5500, timestamp=datetime.now(timezone.utc))
        for name, value in fields.items():
            embed.add_field(name=name, value=value, inline=False)
        await channel.send(embed=embed)

    @commands.Cog.listener()
    async def on_member_join(self, member):
        await self.send_embed(member.guild.id, "Üye Katıldı", {"Üye": f"{member} ({member.id})"})

    @commands.Cog.listener()
    async def on_member_remove(self, member):
        await self.send_embed(member.guild.id, "Üye Ayrıldı", {"Üye": f"{member} ({member.id})"})

    @commands.Cog.listener()
    async def on_message_delete(self, message):
        if message.author.bot:
            return
        await self.send_embed(message.guild.id, "Mesaj Silindi", {
            "Kullanıcı": f"{message.author} ({message.author.id})",
            "Kanal": message.channel.mention,
            "Mesaj": message.content or "Boş mesaj"
        })

    @commands.Cog.listener()
    async def on_message_edit(self, before, after):
        if before.author.bot or before.content == after.content:
            return
        await self.send_embed(before.guild.id, "Mesaj Düzenlendi", {
            "Kullanıcı": f"{before.author} ({before.author.id})",
            "Kanal": before.channel.mention,
            "Önce": before.content or "Boş",
            "Sonra": after.content or "Boş"
        })

    @commands.Cog.listener()
    async def on_guild_role_create(self, role):
        await self.send_embed(role.guild.id, "Rol Oluşturuldu", {"Rol": f"{role.name} ({role.id})"})

    @commands.Cog.listener()
    async def on_guild_role_delete(self, role):
        await self.send_embed(role.guild.id, "Rol Silindi", {"Rol": f"{role.name} ({role.id})"})

    @commands.Cog.listener()
    async def on_guild_role_update(self, before, after):
        await self.send_embed(before.guild.id, "Rol Güncellendi", {
            "Önce": f"{before.name}",
            "Sonra": f"{after.name}"
        })

async def setup(bot):
    from main import db_manager
    await bot.add_cog(Log(bot, db_manager))
