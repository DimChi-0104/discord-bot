import asyncio
import json
import os

import discord
from discord.ext import commands
from discord import app_commands

RECORD_FILE = "data/rps_records.json"
TIMEOUT = 30


def load_records():
    os.makedirs("data", exist_ok=True)

    if not os.path.exists(RECORD_FILE):
        with open(RECORD_FILE, "w", encoding="utf-8") as f:
            json.dump({}, f, ensure_ascii=False, indent=4)
        return {}

    try:
        with open(RECORD_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)

        if not isinstance(data, dict):
            return {}

        return data
    except (json.JSONDecodeError, OSError):
        with open(RECORD_FILE, "w", encoding="utf-8") as f:
            json.dump({}, f, ensure_ascii=False, indent=4)
        return {}


def save_records(data):
    os.makedirs("data", exist_ok=True)

    if not isinstance(data, dict):
        data = {}

    with open(RECORD_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=4)


def ensure_user(data, user: discord.Member):
    uid = str(user.id)
    if uid not in data or not isinstance(data[uid], dict):
        data[uid] = {
            "name": user.display_name,
            "win": 0,
            "lose": 0,
            "draw": 0
        }

    data[uid]["name"] = user.display_name

    for key in ("win", "lose", "draw"):
        if key not in data[uid] or not isinstance(data[uid][key], int) or data[uid][key] < 0:
            data[uid][key] = 0


def judge(a, b):
    if a == b:
        return 0
    if (a == "가위" and b == "보") or (a == "바위" and b == "가위") or (a == "보" and b == "바위"):
        return 1
    return 2


class ChoiceView(discord.ui.View):
    def __init__(self, cog, gid: str, player: discord.Member):
        super().__init__(timeout=TIMEOUT)
        self.cog = cog
        self.gid = gid
        self.player = player

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user.id != self.player.id:
            await interaction.response.send_message(
                "이 버튼은 당신의 선택창이 아니에요.",
                ephemeral=True
            )
            return False
        return True

    async def choose(self, interaction: discord.Interaction, choice: str):
        game = self.cog.active_games.get(self.gid)
        if not game:
            await interaction.response.send_message(
                "이미 종료된 게임이에요.",
                ephemeral=True
            )
            return

        if interaction.user.id in game["selected"]:
            await interaction.response.send_message(
                "이미 선택을 완료했어요.",
                ephemeral=True
            )
            return

        game["choices"][interaction.user.id] = choice
        game["selected"].add(interaction.user.id)

        await interaction.response.send_message(
            f"✅ **{choice}** 선택 완료!",
            ephemeral=True
        )

        await self.cog.update_status(self.gid)

        if len(game["selected"]) == 2:
            await self.cog.finish_game(self.gid)

    @discord.ui.button(label="✂ 가위", style=discord.ButtonStyle.primary)
    async def scissor(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.choose(interaction, "가위")

    @discord.ui.button(label="🪨 바위", style=discord.ButtonStyle.primary)
    async def rock(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.choose(interaction, "바위")

    @discord.ui.button(label="📄 보", style=discord.ButtonStyle.primary)
    async def paper(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.choose(interaction, "보")


class RematchView(discord.ui.View):
    def __init__(self, cog, p1: discord.Member, p2: discord.Member):
        super().__init__(timeout=60)
        self.cog = cog
        self.p1 = p1
        self.p2 = p2

    @discord.ui.button(label="🔄 재대결", style=discord.ButtonStyle.success)
    async def rematch(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id not in (self.p1.id, self.p2.id):
            await interaction.response.send_message(
                "참가자가 아닙니다.",
                ephemeral=True
            )
            return

        if interaction.channel is None:
            await interaction.response.send_message(
                "채널 정보를 확인할 수 없어요.",
                ephemeral=True
            )
            return

        if self.cog.is_user_in_game(self.p1.id) or self.cog.is_user_in_game(self.p2.id):
            await interaction.response.send_message(
                "이미 진행 중인 게임이 있어요.",
                ephemeral=True
            )
            return

        await interaction.response.send_message("🔄 재대결을 시작합니다!")
        await self.cog.start_game(interaction.channel, self.p1, self.p2)


class RPS(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.active_games = {}

    def make_game_id(self, channel_id: int, p1_id: int, p2_id: int) -> str:
        ids = sorted([p1_id, p2_id])
        return f"{channel_id}-{ids[0]}-{ids[1]}"

    def is_user_in_game(self, user_id: int) -> bool:
        for game in self.active_games.values():
            p1, p2 = game["players"]
            if user_id in (p1.id, p2.id):
                return True
        return False

    async def update_status(self, gid: str):
        game = self.active_games.get(gid)
        if not game:
            return

        p1, p2 = game["players"]

        def mark(user):
            return "✅" if user.id in game["selected"] else "⏳"

        embed = discord.Embed(
            title="👁 선택 현황",
            description=(
                f"{mark(p1)} {p1.mention}\n"
                f"{mark(p2)} {p2.mention}"
            ),
            color=0x00FFF8
        )

        try:
            await game["status_message"].edit(embed=embed)
        except discord.HTTPException:
            pass

    async def finish_game(self, gid: str):
        game = self.active_games.get(gid)
        if not game:
            return

        p1, p2 = game["players"]
        c1 = game["choices"].get(p1.id)
        c2 = game["choices"].get(p2.id)
        channel = game["channel"]

        data = load_records()
        ensure_user(data, p1)
        ensure_user(data, p2)

        if not c1 or not c2:
            await channel.send("⏱ **시간 초과로 게임이 무효 처리되었습니다.**")
            self.active_games.pop(gid, None)
            return

        result_code = judge(c1, c2)

        if result_code == 0:
            data[str(p1.id)]["draw"] += 1
            data[str(p2.id)]["draw"] += 1
            result_text = "🤝 무승부!"
        elif result_code == 1:
            data[str(p1.id)]["win"] += 1
            data[str(p2.id)]["lose"] += 1
            result_text = f"🏆 {p1.mention} 승리!"
        else:
            data[str(p2.id)]["win"] += 1
            data[str(p1.id)]["lose"] += 1
            result_text = f"🏆 {p2.mention} 승리!"

        save_records(data)

        embed = discord.Embed(
            title="✌ 가위바위보 결과",
            description=(
                f"{p1.mention} : **{c1}**\n"
                f"{p2.mention} : **{c2}**\n\n"
                f"{result_text}"
            ),
            color=0x00FFAA
        )

        await channel.send(embed=embed, view=RematchView(self, p1, p2))
        self.active_games.pop(gid, None)

    async def start_game(self, channel: discord.abc.Messageable, p1: discord.Member, p2: discord.Member):
        gid = self.make_game_id(channel.id, p1.id, p2.id)

        self.active_games[gid] = {
            "players": (p1, p2),
            "choices": {},
            "selected": set(),
            "channel": channel,
            "status_message": None
        }

        embed = discord.Embed(
            title="✌ 가위바위보 시작",
            description=f"{p1.mention} vs {p2.mention}\nDM에서 선택하세요!",
            color=0x00FFF8
        )

        status_message = await channel.send(embed=embed)
        self.active_games[gid]["status_message"] = status_message

        try:
            await p1.send("✌ 가위바위보 선택", view=ChoiceView(self, gid, p1))
        except discord.Forbidden:
            self.active_games.pop(gid, None)
            await channel.send(f"{p1.mention}님이 DM을 막아두어서 게임을 시작할 수 없어요.")
            return

        try:
            await p2.send("✌ 가위바위보 선택", view=ChoiceView(self, gid, p2))
        except discord.Forbidden:
            self.active_games.pop(gid, None)
            await channel.send(f"{p2.mention}님이 DM을 막아두어서 게임을 시작할 수 없어요.")
            return

        await asyncio.sleep(TIMEOUT)
        if gid in self.active_games:
            await self.finish_game(gid)

    @app_commands.command(name="가위바위보", description="사람 vs 사람 가위바위보")
    @app_commands.describe(상대="대결할 상대")
    async def rps(self, interaction: discord.Interaction, 상대: discord.Member):
        if interaction.guild is None or interaction.channel is None:
            await interaction.response.send_message(
                "이 명령어는 서버에서만 사용할 수 있어요.",
                ephemeral=True
            )
            return

        if 상대.bot or 상대.id == interaction.user.id:
            await interaction.response.send_message(
                "올바른 상대를 선택하세요.",
                ephemeral=True
            )
            return

        if self.is_user_in_game(interaction.user.id) or self.is_user_in_game(상대.id):
            await interaction.response.send_message(
                "이미 진행 중인 가위바위보 게임이 있어요.",
                ephemeral=True
            )
            return

        await interaction.response.send_message("🎮 게임을 시작합니다!")
        await self.start_game(interaction.channel, interaction.user, 상대)

    @app_commands.command(name="전적", description="가위바위보 전적 확인")
    @app_commands.describe(유저="확인할 유저 (없으면 본인)")
    async def record(self, interaction: discord.Interaction, 유저: discord.Member = None):
        user = 유저 or interaction.user

        if user.bot:
            await interaction.response.send_message(
                "봇 계정의 전적은 확인할 수 없어요.",
                ephemeral=True
            )
            return

        data = load_records()
        uid = str(user.id)

        if uid not in data:
            await interaction.response.send_message("전적이 없습니다.", ephemeral=True)
            return

        r = data[uid]
        embed = discord.Embed(
            title=f"📊 {r['name']}의 전적",
            description=(
                f"🏆 승: {r['win']}\n"
                f"💀 패: {r['lose']}\n"
                f"🤝 무: {r['draw']}"
            ),
            color=0x00FFAA
        )
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="랭킹", description="가위바위보 랭킹 TOP")
    async def ranking(self, interaction: discord.Interaction):
        data = load_records()

        if not data:
            await interaction.response.send_message("랭킹 데이터가 없습니다.", ephemeral=True)
            return

        ranked = sorted(
            data.values(),
            key=lambda x: x.get("win", 0),
            reverse=True
        )[:10]

        desc = ""
        for i, user in enumerate(ranked, 1):
            desc += f"**{i}위** {user.get('name', '알 수 없음')} 🏆 {user.get('win', 0)}승\n"

        embed = discord.Embed(
            title="🏆 가위바위보 랭킹",
            description=desc,
            color=0xFFD700
        )
        await interaction.response.send_message(embed=embed)


async def setup(bot):
    await bot.add_cog(RPS(bot))