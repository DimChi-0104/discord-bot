import json
import os

import discord
from discord import app_commands
from discord.ext import commands

ECONOMY_FILE = "data/economy.json"
SHOP_FILE = "data/shop.json"


def ensure_data_dir():
    os.makedirs("data", exist_ok=True)


def load_economy():
    ensure_data_dir()

    if not os.path.exists(ECONOMY_FILE):
        data = {"users": {}}
        save_economy(data)
        return data

    try:
        with open(ECONOMY_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)

        if not isinstance(data, dict):
            data = {"users": {}}

        if "users" not in data or not isinstance(data["users"], dict):
            data["users"] = {}

        return data

    except (json.JSONDecodeError, OSError):
        data = {"users": {}}
        save_economy(data)
        return data


def save_economy(data):
    ensure_data_dir()
    temp_file = ECONOMY_FILE + ".tmp"

    with open(temp_file, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=4)

    os.replace(temp_file, ECONOMY_FILE)


def load_shop():
    ensure_data_dir()

    if not os.path.exists(SHOP_FILE):
        default_shop = {
            "items": {
                "출석보너스권": {
                    "price": 3000,
                    "description": "출석 시 자동으로 1개 사용되어 추가 보상 500원을 지급합니다.",
                    "category": "소모품",
                    "buyable": True
                },
                "칭호이용권": {
                    "price": 5000,
                    "description": "추후 칭호 시스템에서 사용할 수 있는 아이템입니다.",
                    "category": "장식",
                    "buyable": True
                },
                "슬롯연출권": {
                    "price": 2500,
                    "description": "추후 슬롯 연출 기능에서 사용할 수 있는 아이템입니다.",
                    "category": "장식",
                    "buyable": True
                },
                "행운권": {
                    "price": 7500,
                    "description": "추후 확률형 시스템에서 사용할 수 있는 아이템입니다.",
                    "category": "소모품",
                    "buyable": True
                }
            }
        }
        save_shop(default_shop)
        return default_shop

    try:
        with open(SHOP_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)

        if not isinstance(data, dict):
            data = {"items": {}}

        if "items" not in data or not isinstance(data["items"], dict):
            data["items"] = {}

        return data

    except (json.JSONDecodeError, OSError):
        data = {"items": {}}
        save_shop(data)
        return data


def save_shop(data):
    ensure_data_dir()
    temp_file = SHOP_FILE + ".tmp"

    with open(temp_file, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=4)

    os.replace(temp_file, SHOP_FILE)


def get_user(data, user_id: int):
    user_id = str(user_id)

    if user_id not in data["users"]:
        data["users"][user_id] = {
            "money": 0,
            "last_attendance": "",
            "streak": 0,
            "total_attendance": 0,
            "win": 0,
            "lose": 0,
            "inventory": {}
        }

    user = data["users"][user_id]

    if "inventory" not in user or not isinstance(user["inventory"], dict):
        user["inventory"] = {}

    # 기존 구조 호환
    user.setdefault("money", 0)
    user.setdefault("last_attendance", "")
    user.setdefault("streak", 0)
    user.setdefault("total_attendance", 0)
    user.setdefault("win", 0)
    user.setdefault("lose", 0)

    return user


class Shop(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="상점", description="상점 아이템 목록을 확인합니다.")
    async def shop(self, interaction: discord.Interaction):
        if interaction.guild is None:
            await interaction.response.send_message(
                "이 명령어는 서버에서만 사용할 수 있어요.",
                ephemeral=True
            )
            return

        if interaction.user.bot:
            await interaction.response.send_message(
                "봇 계정은 사용할 수 없어요.",
                ephemeral=True
            )
            return

        shop_data = load_shop()
        items = shop_data.get("items", {})

        if not items:
            await interaction.response.send_message(
                "현재 상점에 등록된 아이템이 없어요.",
                ephemeral=True
            )
            return

        embed = discord.Embed(
            title="🛒 디모 상점",
            description="구매 가능한 아이템 목록이에요.",
            color=discord.Color.blue()
        )

        for item_name, item_info in items.items():
            if not item_info.get("buyable", False):
                continue

            price = item_info.get("price", 0)
            desc = item_info.get("description", "설명이 없습니다.")
            category = item_info.get("category", "기타")

            embed.add_field(
                name=f"{item_name} | {price:,}원",
                value=f"분류: {category}\n{desc}",
                inline=False
            )

        embed.set_footer(text="/구매 [아이템명] [수량] 으로 구매할 수 있어요.")
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="구매", description="상점에서 아이템을 구매합니다.")
    async def buy(
        self,
        interaction: discord.Interaction,
        아이템: str,
        수량: app_commands.Range[int, 1, 100]
    ):
        if interaction.guild is None:
            await interaction.response.send_message(
                "이 명령어는 서버에서만 사용할 수 있어요.",
                ephemeral=True
            )
            return

        if interaction.user.bot:
            await interaction.response.send_message(
                "봇 계정은 사용할 수 없어요.",
                ephemeral=True
            )
            return

        economy = load_economy()
        shop_data = load_shop()

        user = get_user(economy, interaction.user.id)
        items = shop_data.get("items", {})

        if 아이템 not in items:
            await interaction.response.send_message(
                "존재하지 않는 아이템이에요.",
                ephemeral=True
            )
            return

        item_info = items[아이템]

        if not item_info.get("buyable", False):
            await interaction.response.send_message(
                "이 아이템은 현재 구매할 수 없어요.",
                ephemeral=True
            )
            return

        price = int(item_info.get("price", 0))
        total_price = price * 수량

        if total_price <= 0:
            await interaction.response.send_message(
                "잘못된 가격 정보가 감지되었어요.",
                ephemeral=True
            )
            return

        if user["money"] < total_price:
            await interaction.response.send_message(
                f"재화가 부족해요.\n현재 보유 재화: {user['money']:,}원\n필요 재화: {total_price:,}원",
                ephemeral=True
            )
            return

        user["money"] -= total_price
        user["inventory"][아이템] = user["inventory"].get(아이템, 0) + 수량

        if user["money"] < 0:
            user["money"] = 0
            await interaction.response.send_message(
                "오류 방지를 위해 구매가 취소되었어요.",
                ephemeral=True
            )
            return

        save_economy(economy)

        embed = discord.Embed(
            title="✅ 아이템 구매 완료",
            color=discord.Color.green()
        )
        embed.add_field(name="구매 아이템", value=아이템, inline=True)
        embed.add_field(name="수량", value=str(수량), inline=True)
        embed.add_field(name="총 가격", value=f"{total_price:,}원", inline=True)
        embed.add_field(name="남은 재화", value=f"{user['money']:,}원", inline=False)

        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="인벤토리", description="보유 중인 아이템을 확인합니다.")
    async def inventory(self, interaction: discord.Interaction):
        if interaction.guild is None:
            await interaction.response.send_message(
                "이 명령어는 서버에서만 사용할 수 있어요.",
                ephemeral=True
            )
            return

        if interaction.user.bot:
            await interaction.response.send_message(
                "봇 계정은 사용할 수 없어요.",
                ephemeral=True
            )
            return

        economy = load_economy()
        user = get_user(economy, interaction.user.id)
        inventory = user.get("inventory", {})

        embed = discord.Embed(
            title=f"🎒 {interaction.user.display_name}님의 인벤토리",
            color=discord.Color.gold()
        )

        if not inventory:
            embed.description = "보유 중인 아이템이 없어요."
            await interaction.response.send_message(embed=embed)
            return

        lines = []
        for item_name, amount in inventory.items():
            if amount > 0:
                lines.append(f"• {item_name} x{amount}")

        if not lines:
            embed.description = "보유 중인 아이템이 없어요."
        else:
            embed.description = "\n".join(lines)

        await interaction.response.send_message(embed=embed)


async def setup(bot):
    await bot.add_cog(Shop(bot))