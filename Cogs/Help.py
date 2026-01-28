import discord
from discord.ext import commands
from datetime import datetime, timezone

class Help(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(name="help")
    async def help_command(self, ctx):
        embed = discord.Embed(
            title="Moderasyon Botu Komutları",
            description="Tüm komutlar ve açıklamaları",
            color=0x00ff00,
            timestamp=datetime.now(timezone.utc)
        )
        
        embed.add_field(
            name="/ban <@user> [sebep]",
            value="Kullanıcıyı sunucudan yasaklar (Yönetici)",
            inline=False
        )
        embed.add_field(
            name="/unban <user_id>",
            value="Yasaklı kullanıcının yasağını kaldırır (Yönetici)",
            inline=False
        )
        embed.add_field(
            name="/kick <@user> [sebep]",
            value="Kullanıcıyı sunucudan atar (Yönetici)",
            inline=False
        )
        embed.add_field(
            name="/mute <@user> [sebep]",
            value="Kullanıcıyı susturur (Yönetici)",
            inline=False
        )
        embed.add_field(
            name="/unmute <@user>",
            value="Kullanıcının susturmasını kaldırır (Yönetici)",
            inline=False
        )
        embed.add_field(
            name="/rolver <@user> <@role>",
            value="Kullanıcıya rol verir (Yönetici)",
            inline=False
        )
        embed.add_field(
            name="/rolal <@user> <@role>",
            value="Kullanıcıdan rol alır (Yönetici)",
            inline=False
        )
        embed.add_field(
            name="/nuke",
            value="Kanaldaki tüm mesajları siler (Yönetici)",
            inline=False
        )
        embed.add_field(
            name="/log",
            value="Denetim-log kanalını gösterir veya oluşturur",
            inline=False
        )
        embed.add_field(
            name="/help",
            value="Komutları ve açıklamalarını gösterir",
            inline=False
        )
        
        await ctx.send(embed=embed)

async def setup(bot):
    await bot.add_cog(Help(bot))
