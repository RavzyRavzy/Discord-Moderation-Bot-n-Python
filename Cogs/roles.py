import discord
from discord.ext import commands
from datetime import datetime, timezone

class Roles(commands.Cog):
    def __init__(self, bot, db_manager):
        self.bot = bot
        self.db = db_manager

    async def get_log_channel(self, guild: discord.Guild):
        channel = discord.utils.get(guild.text_channels, name="denetim-log")
        if not channel:
            overwrites = {guild.default_role: discord.PermissionOverwrite(send_messages=True)}
            channel = await guild.create_text_channel("denetim-log", overwrites=overwrites)
        return channel

    async def log_role_action(self, guild, user, target, action, role):
        channel = await self.get_log_channel(guild)
        embed = discord.Embed(title=f"Rol {action}", color=0x00ff00, timestamp=datetime.now(timezone.utc))
        embed.add_field(name="Yetkili", value=f"{user}", inline=True)
        embed.add_field(name="Hedef", value=f"{target}", inline=True)
        embed.add_field(name="Rol", value=f"{role.name}", inline=False)
        await channel.send(embed=embed)

    @commands.command(name="rolver")
    @commands.has_permissions(administrator=True)
    async def rolver(self, ctx, member: discord.Member, role: discord.Role):
        try:
            await member.add_roles(role)
            await ctx.send(f"{member.mention} kullanıcısına {role.name} rolü verildi!")
            await self.log_role_action(ctx.guild, ctx.author, member, "verildi", role)
        except Exception as e:
            await ctx.send("Rol verme işlemi başarısız!")
            self.bot.logger.error("Rolver hatası", exc_info=e)

    @commands.command(name="rolal")
    @commands.has_permissions(administrator=True)
    async def rolal(self, ctx, member: discord.Member, role: discord.Role):
        try:
            await member.remove_roles(role)
            await ctx.send(f"{member.mention} kullanıcısından {role.name} rolü alındı!")
            await self.log_role_action(ctx.guild, ctx.author, member, "alındı", role)
        except Exception as e:
            await ctx.send("Rol alma işlemi başarısız!")
            self.bot.logger.error("RolaL hatası", exc_info=e)

async def setup(bot):
    from main import db_manager
    await bot.add_cog(Roles(bot, db_manager))
