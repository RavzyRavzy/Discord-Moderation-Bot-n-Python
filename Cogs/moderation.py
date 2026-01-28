import discord
from discord.ext import commands
from datetime import timedelta, datetime

class Moderation(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.warns = {}

    async def is_admin(self, ctx):
        return ctx.author.guild_permissions.administrator

    @commands.command()
    async def ban(self, ctx, member: discord.Member, *, reason="Sebep belirtilmedi"):
        if not await self.is_admin(ctx):
            return await ctx.send("Yetkin yok.")
        await member.ban(reason=reason)
        await ctx.send(f"{member} yasaklandı.")

    @commands.command()
    async def unban(self, ctx, user_id: int):
        if not await self.is_admin(ctx):
            return await ctx.send("Yetkin yok.")
        user = await self.bot.fetch_user(user_id)
        await ctx.guild.unban(user)
        await ctx.send(f"{user} yasağı kaldırıldı.")

    @commands.command()
    async def kick(self, ctx, member: discord.Member, *, reason="Sebep belirtilmedi"):
        if not await self.is_admin(ctx):
            return await ctx.send("Yetkin yok.")
        await member.kick(reason=reason)
        await ctx.send(f"{member} atıldı.")

    @commands.command()
    async def mute(self, ctx, member: discord.Member):
        if not await self.is_admin(ctx):
            return await ctx.send("Yetkin yok.")
        role = discord.utils.get(ctx.guild.roles, name="Muted")
        if not role:
            role = await ctx.guild.create_role(name="Muted")
            for ch in ctx.guild.channels:
                await ch.set_permissions(role, send_messages=False)
        await member.add_roles(role)
        await ctx.send(f"{member} susturuldu.")

    @commands.command()
    async def unmute(self, ctx, member: discord.Member):
        if not await self.is_admin(ctx):
            return await ctx.send("Yetkin yok.")
        role = discord.utils.get(ctx.guild.roles, name="Muted")
        if role:
            await member.remove_roles(role)
        await ctx.send(f"{member} susturması kaldırıldı.")

    @commands.command()
    async def timeout(self, ctx, member: discord.Member, dakika: int):
        if not await self.is_admin(ctx):
            return await ctx.send("Yetkin yok.")
        await member.timeout(timedelta(minutes=dakika))
        await ctx.send(f"{member} {dakika} dakika timeout yedi.")

    @commands.command()
    async def untimeout(self, ctx, member: discord.Member):
        if not await self.is_admin(ctx):
            return await ctx.send("Yetkin yok.")
        await member.timeout(None)
        await ctx.send(f"{member} timeout kaldırıldı.")

    @commands.command()
    async def purge(self, ctx, amount: int):
        if not await self.is_admin(ctx):
            return await ctx.send("Yetkin yok.")
        await ctx.channel.purge(limit=amount)
        await ctx.send("Mesajlar silindi.", delete_after=3)

    @commands.command()
    async def lock(self, ctx):
        if not await self.is_admin(ctx):
            return await ctx.send("Yetkin yok.")
        await ctx.channel.set_permissions(ctx.guild.default_role, send_messages=False)
        await ctx.send("Kanal kilitlendi.")

    @commands.command()
    async def unlock(self, ctx):
        if not await self.is_admin(ctx):
            return await ctx.send("Yetkin yok.")
        await ctx.channel.set_permissions(ctx.guild.default_role, send_messages=True)
        await ctx.send("Kanal açıldı.")

    @commands.command()
    async def slowmode(self, ctx, seconds: int):
        if not await self.is_admin(ctx):
            return await ctx.send("Yetkin yok.")
        await ctx.channel.edit(slowmode_delay=seconds)
        await ctx.send(f"Slowmode {seconds} saniye.")

    @commands.command()
    async def nick(self, ctx, member: discord.Member, *, nick):
        if not await self.is_admin(ctx):
            return await ctx.send("Yetkin yok.")
        await member.edit(nick=nick)
        await ctx.send("Nickname değiştirildi.")

    @commands.command()
    async def warn(self, ctx, member: discord.Member, *, reason="Sebep yok"):
        if not await self.is_admin(ctx):
            return await ctx.send("Yetkin yok.")
        self.warns.setdefault(member.id, [])
        self.warns[member.id].append({
            "reason": reason,
            "date": datetime.utcnow()
        })
        await ctx.send(f"{member} uyarıldı.")

    @commands.command()
    async def warns(self, ctx, member: discord.Member):
        if not await self.is_admin(ctx):
            return await ctx.send("Yetkin yok.")
        data = self.warns.get(member.id)
        if not data:
            return await ctx.send("Uyarısı yok.")
        msg = ""
        for i, w in enumerate(data, 1):
            msg += f"{i}. {w['reason']} ({w['date']})\n"
        await ctx.send(msg)

    @commands.command()
    async def clearwarns(self, ctx, member: discord.Member):
        if not await self.is_admin(ctx):
            return await ctx.send("Yetkin yok.")
        self.warns.pop(member.id, None)
        await ctx.send("Uyarılar silindi.")

async def setup(bot):
    await bot.add_cog(Moderation(bot))
   
