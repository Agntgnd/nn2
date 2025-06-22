
import discord
from discord.ext import commands
import random
import os
import asyncio
from datetime import datetime, timedelta
from database import database, create_tables, get_user, update_user

intents = discord.Intents.default()
intents.message_content = True
intents.members = True

bot = commands.Bot(command_prefix="!", intents=intents)


def parse_last_farm(dt):
    if dt is None:
        return datetime(1970, 1, 1)
    if isinstance(dt, str):
        return datetime.fromisoformat(dt)
    if isinstance(dt, datetime):
        return dt
    return datetime(1970, 1, 1)


class MainMenu(discord.ui.View):
    def __init__(self, author):
        super().__init__(timeout=None)
        self.author = author

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user.id != self.author.id:
            await interaction.response.send_message("❌ Это не ваша панель управления!", ephemeral=True)
            return False
        return True

    @discord.ui.button(label="Патриот", style=discord.ButtonStyle.primary, emoji="🇷🇺")
    async def patriot_button(self, button: discord.ui.Button, interaction: discord.Interaction):
        data = await get_user(interaction.user.id)
        chance = random.random()
        if chance <= 0.33:
            role_name = "Патриот"
            role = discord.utils.get(interaction.guild.roles, name=role_name)
            if not role:
                role = await interaction.guild.create_role(name=role_name)
            if role not in interaction.user.roles:
                await interaction.user.add_roles(role)
                data["roles"].append(role_name)
            data["credits"] += 100
            await update_user(interaction.user.id, data["credits"], data["roles"], data["last_farm"])
            await interaction.response.send_message(f"🎉 {interaction.user.mention}, вы получили роль **{role_name}** и 100 соц. кредитов!")
        else:
            await interaction.response.send_message(f"😞 {interaction.user.mention}, к сожалению, не повезло. Попробуйте ещё раз!")

    @discord.ui.button(label="Баланс", style=discord.ButtonStyle.secondary, emoji="💰")
    async def balance_button(self, button: discord.ui.Button, interaction: discord.Interaction):
        data = await get_user(interaction.user.id)
        await interaction.response.send_message(f"💰 {interaction.user.mention}, у вас **{data['credits']}** соц. кредитов.")

    @discord.ui.button(label="Фарм", style=discord.ButtonStyle.success, emoji="⛏️")
    async def farm_button(self, button: discord.ui.Button, interaction: discord.Interaction):
        data = await get_user(interaction.user.id)
        now = datetime.utcnow()
        last_farm = parse_last_farm(data["last_farm"])
        if now - last_farm < timedelta(minutes=5):
            remaining = timedelta(minutes=5) - (now - last_farm)
            await interaction.response.send_message(f"⏳ {interaction.user.mention}, вы уже фармили недавно. Попробуйте через {int(remaining.total_seconds())} секунд.")
            return
        reward = random.randint(40, 70)
        data["credits"] += reward
        data["last_farm"] = now.isoformat()
        await update_user(interaction.user.id, data["credits"], data["roles"], data["last_farm"])
        await interaction.response.send_message(f"💸 {interaction.user.mention}, вы нафармили **{reward}** соц. кредитов!")

    @discord.ui.button(label="Профиль", style=discord.ButtonStyle.primary, emoji="👤")
    async def profile_button(self, button: discord.ui.Button, interaction: discord.Interaction):
        data = await get_user(interaction.user.id)
        roles = data["roles"]
        roles_str = ", ".join(roles) if roles else "Нет ролей"
        embed = discord.Embed(title=f"Профиль пользователя {interaction.user.display_name}", color=discord.Color.blue())
        embed.set_thumbnail(url=interaction.user.avatar.url if interaction.user.avatar else "")
        embed.add_field(name="Соц. кредиты", value=str(data["credits"]), inline=False)
        embed.add_field(name="Роли", value=roles_str, inline=False)
        await interaction.response.send_message(embed=embed)

    @discord.ui.button(label="Своя роль", style=discord.ButtonStyle.secondary, emoji="⚙️")
    async def custom_role_button(self, button: discord.ui.Button, interaction: discord.Interaction):
        data = await get_user(interaction.user.id)
        if data["credits"] < 3000:
            await interaction.response.send_message(f"❌ {interaction.user.mention}, недостаточно кредитов (нужно 3000).")
            return

        await interaction.response.send_message(f"🛠️ {interaction.user.mention}, напишите название роли (без @), которую хотите получить:", ephemeral=True)

        def check(m):
            return m.author.id == interaction.user.id and m.channel == interaction.channel

        try:
            msg = await bot.wait_for("message", check=check, timeout=30)
            role_name = msg.content.strip()
            role = discord.utils.get(interaction.guild.roles, name=role_name)
            if not role:
                role = await interaction.guild.create_role(name=role_name)
            await interaction.user.add_roles(role)
            if role_name not in data["roles"]:
                data["roles"].append(role_name)
            data["credits"] -= 3000
            await update_user(interaction.user.id, data["credits"], data["roles"], data["last_farm"])
            await interaction.followup.send(f"✅ {interaction.user.mention}, роль '{role_name}' добавлена!", ephemeral=True)
        except asyncio.TimeoutError:
            await interaction.followup.send(f"⌛ {interaction.user.mention}, время ожидания истекло.", ephemeral=True)


@bot.event
async def on_ready():
    await database.connect()
    await create_tables()
    print(f"Бот запущен как {bot.user}")


@bot.command()
async def меню(ctx):
    view = MainMenu(ctx.author)
    await ctx.send(f"Привет, {ctx.author.mention}! Используйте кнопки ниже для взаимодействия:", view=view)


@bot.event
async def on_command_error(ctx, error):
    if isinstance(error, commands.CommandNotFound):
        await ctx.send("❌ Команда не найдена. Введите !меню для вызова кнопок.")
    else:
        await ctx.send(f"❌ Произошла ошибка: {str(error)}")


bot.run(os.getenv("DISCORD_TOKEN"))
