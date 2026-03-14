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
        with open(ECONOMY_FILE, "w", encoding="utf-8") as f:
            json.dump({"users": {}}, f, ensure_ascii=False, indent=4)
        return {"users": {}}

    try:
        with open(ECONOMY_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)

        if not isinstance(data, dict):
            data = {"users": {}}

        if "users" not in data or not isinstance(data["users"], dict):
            data["users"] = {}

        return data

    except (json.JSONDecodeError, OSError):
        with open(ECONOMY_FILE, "w", encoding="utf-8") as f:
            json.dump({"users": {}}, f, ensure_ascii=False, indent=4)
        return {"users": {}}


def save_economy(data):
    ensure_data_dir()
    with open(ECONOMY_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=4)


def load_shop():
    ensure_data_dir()

    if not os.path.exists(SHOP_FILE):
        with open(SHOP_FILE, "w", encoding="utf-8") as f:
            json.dump({"items": {}}, f, ensure_ascii=False, indent=4)
        return {"items": {}}

    try:
        with open(SHOP_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)

        if not isinstance(data, dict):
            data = {"items": {}}

        if "items" not in data or not isinstance(data["items"], dict):
            data["items"] = {}

        return data

    except (json.JSONDecodeError, OSError):
        with open(SHOP_FILE, "w", encoding="utf-8") as f:
            json.dump({"items": {}}, f, ensure_ascii=False, indent=4)
        return {"items": {}}


def ensure_user(data: dict, user_id: str):
    if user_id not in data["users"]:
        data["users"][user_id] = {
            "money": 0,
            "last_attendance": "",
            "streak": 0,
            "total_attendance": 0,
            "win": 0,
            "lose": 0,
            "inventory": {},
            "active_effects": {},
            "titles": [],
            "equipped_title": "",
            "base_nickname": ""
        }

    user_data = data["users"][user_id]

    if "money" not in user_data:
        user_data["money"] = 0
    if "inventory" not in user_data or not isinstance(user_data["inventory"], dict):
        user_data["inventory"] = {}
    if "active_effects" not in user_data or not isinstance(user_data["active_effects"], dict):
        user_data["active_effects"] = {}
    if "titles" not in user_data or not isinstance(user_data["titles"], list):
        user_data["titles"] = []
    if "equipped_title" not in user_data:
        user_data["equipped_title"] = ""
    if "base_nickname" not in user_data:
        user_data["base_nickname"] = ""

    return user_data


def get_shop_categories() -> list[str]:
    shop_data = load_shop()
    categories = []

    for item_info in shop_data["items"].values():
        category = item_info.get("category", "기타")
        if category not in categories:
            categories.append(category)

    preferred_order = ["소모품", "칭호", "기타"]
    ordered = [c for c in preferred_order if c in categories]
    extras = [c for c in categories if c not in preferred_order]

    result = ordered + extras
    return result if result else ["소모품", "칭호", "기타"]


def build_shop_main_embed(user: discord.abc.User) -> discord.Embed:
    economy_data = load_economy()
    user_data = ensure_user(economy_data, str(user.id))

    embed = discord.Embed(
        title="🛒 Dimo Shop",
        description=(
            "디모 상점이에요.\n\n"
            "아래 선택 메뉴에서 카테고리를 골라 상품을 확인할 수 있어요.\n"
            "구매는 `/구매`, 보유품 확인은 `/인벤토리`로 할 수 있어요."
        ),
        color=discord.Color.green()
    )

    embed.add_field(
        name="📌 카테고리",
        value="소모품 / 칭호 / 기타",
        inline=False
    )
    embed.add_field(
        name="💰 보유 코인",
        value=f"{user_data['money']:,} 코인",
        inline=False
    )
    embed.add_field(
        name="🧭 이용 방법",
        value="아래 메뉴를 눌러 카테고리별 상품을 확인하세요.",
        inline=False
    )

    embed.set_footer(text=f"{user.display_name}님의 상점")
    if user.display_avatar:
        embed.set_thumbnail(url=user.display_avatar.url)

    return embed


def build_shop_category_embed(category_name: str, user: discord.abc.User) -> discord.Embed:
    shop_data = load_shop()
    economy_data = load_economy()
    user_data = ensure_user(economy_data, str(user.id))

    embed = discord.Embed(
        title=f"🛒 Dimo Shop - {category_name}",
        description=f"현재 보유 코인: **{user_data['money']:,} 코인**",
        color=discord.Color.green()
    )

    found = False
    for item_name, item_info in shop_data["items"].items():
        if item_info.get("category", "기타") != category_name:
            continue

        if not item_info.get("buyable", True):
            continue

        price = item_info.get("price", 0)
        desc = item_info.get("description", "설명이 없어요.")
        usable = "사용 가능" if item_info.get("usable", False) else "사용 불가"

        embed.add_field(
            name=f"{item_name} · {price:,} 코인",
            value=f"{desc}\n`{usable}`",
            inline=False
        )
        found = True

    if not found:
        embed.add_field(
            name="등록된 상품 없음",
            value="이 카테고리에는 현재 구매 가능한 상품이 없어요.",
            inline=False
        )

    embed.set_footer(text=f"{user.display_name}님의 상점 카테고리")
    if user.display_avatar:
        embed.set_thumbnail(url=user.display_avatar.url)

    return embed


def build_inventory_embed(target: discord.Member) -> discord.Embed:
    economy_data = load_economy()
    user_data = ensure_user(economy_data, str(target.id))

    inventory = user_data.get("inventory", {})
    titles = user_data.get("titles", [])
    active_effects = user_data.get("active_effects", {})
    equipped_title = user_data.get("equipped_title", "")

    embed = discord.Embed(
        title=f"🎒 {target.display_name}님의 인벤토리",
        color=discord.Color.blurple()
    )

    embed.add_field(
        name="💰 보유 코인",
        value=f"{user_data.get('money', 0):,} 코인",
        inline=False
    )

    if inventory:
        inventory_text = "\n".join(
            f"• {item_name} × {amount}"
            for item_name, amount in inventory.items()
            if amount > 0
        )
        if not inventory_text.strip():
            inventory_text = "보유 중인 아이템이 없어요."
    else:
        inventory_text = "보유 중인 아이템이 없어요."

    embed.add_field(
        name="📦 보유 아이템",
        value=inventory_text[:1024],
        inline=False
    )

    if titles:
        title_lines = []
        for i, title in enumerate(titles, start=1):
            if isinstance(title, dict):
                title_name = title.get("name", "이름 없음")
                title_level = title.get("level", 0)
                if title_level > 0:
                    title_lines.append(f"{i}. {title_name} (+{title_level})")
                else:
                    title_lines.append(f"{i}. {title_name}")
            else:
                title_lines.append(f"{i}. {str(title)}")

        titles_text = "\n".join(title_lines)
    else:
        titles_text = "보유 중인 칭호가 없어요."

    embed.add_field(
        name="🏷 보유 칭호",
        value=titles_text[:1024],
        inline=False
    )

    embed.add_field(
        name="✨ 장착 중인 칭호",
        value=equipped_title if equipped_title else "장착한 칭호가 없어요.",
        inline=False
    )

    if active_effects:
        effects_text = "\n".join(
            f"• {effect_name}: {value}"
            for effect_name, value in active_effects.items()
        )
    else:
        effects_text = "현재 활성 효과가 없어요."

    embed.add_field(
        name="🪄 활성 효과",
        value=effects_text[:1024],
        inline=False
    )

    embed.set_footer(text=f"{target.display_name}님의 보유 정보")
    if target.display_avatar:
        embed.set_thumbnail(url=target.display_avatar.url)

    return embed


async def buy_item_autocomplete(
    interaction: discord.Interaction,
    current: str
) -> list[app_commands.Choice[str]]:
    shop_data = load_shop()
    results = []

    for item_name, item_info in shop_data["items"].items():
        if not item_info.get("buyable", True):
            continue

        if current.lower() not in item_name.lower():
            continue

        price = item_info.get("price", 0)
        results.append(
            app_commands.Choice(
                name=f"{item_name} ({price:,}코인)",
                value=item_name
            )
        )

    return results[:25]


class ShopCategorySelect(discord.ui.Select):
    def __init__(self, member: discord.Member):
        self.member = member
        categories = get_shop_categories()

        options = [
            discord.SelectOption(
                label="메인",
                emoji="🛒",
                description="상점 메인 화면으로 이동해요."
            )
        ]

        for category in categories:
            options.append(
                discord.SelectOption(
                    label=category,
                    description=f"{category} 상품 목록을 확인해요."
                )
            )

        super().__init__(
            placeholder="상점 카테고리를 선택하세요.",
            min_values=1,
            max_values=1,
            options=options
        )

    async def callback(self, interaction: discord.Interaction):
        if interaction.user.id != self.member.id:
            await interaction.response.send_message(
                "이 상점 메뉴는 명령어를 실행한 사용자만 조작할 수 있어요.",
                ephemeral=True
            )
            return

        selected = self.values[0]

        if selected == "메인":
            embed = build_shop_main_embed(interaction.user)
        else:
            embed = build_shop_category_embed(selected, interaction.user)

        await interaction.response.edit_message(embed=embed, view=self.view)


class ShopView(discord.ui.View):
    def __init__(self, member: discord.Member):
        super().__init__(timeout=300)
        self.add_item(ShopCategorySelect(member))


class Shop(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="상점", description="디모 상점을 확인합니다.")
    async def shop_command(self, interaction: discord.Interaction):
        if interaction.guild is None:
            await interaction.response.send_message(
                "상점은 서버에서만 사용할 수 있어요.",
                ephemeral=True
            )
            return

        member = interaction.user
        embed = build_shop_main_embed(member)
        view = ShopView(member)

        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)

    @app_commands.command(name="구매", description="상점에서 아이템을 구매합니다.")
    @app_commands.describe(아이템="구매할 아이템 이름", 수량="구매할 수량")
    @app_commands.autocomplete(아이템=buy_item_autocomplete)
    async def buy_command(
        self,
        interaction: discord.Interaction,
        아이템: str,
        수량: app_commands.Range[int, 1, 999] = 1
    ):
        if interaction.guild is None:
            await interaction.response.send_message(
                "구매는 서버에서만 사용할 수 있어요.",
                ephemeral=True
            )
            return

        shop_data = load_shop()
        economy_data = load_economy()
        user_data = ensure_user(economy_data, str(interaction.user.id))

        item_info = shop_data["items"].get(아이템)
        if not item_info:
            await interaction.response.send_message(
                "존재하지 않는 상품이에요.",
                ephemeral=True
            )
            return

        if not item_info.get("buyable", True):
            await interaction.response.send_message(
                "이 상품은 구매할 수 없어요.",
                ephemeral=True
            )
            return

        price = item_info.get("price", 0)
        total_price = price * 수량
        current_money = user_data.get("money", 0)

        if current_money < total_price:
            await interaction.response.send_message(
                f"코인이 부족해요.\n"
                f"현재 보유: **{current_money:,} 코인**\n"
                f"필요 금액: **{total_price:,} 코인**",
                ephemeral=True
            )
            return

        inventory = user_data.setdefault("inventory", {})
        inventory[아이템] = inventory.get(아이템, 0) + 수량
        user_data["money"] = current_money - total_price

        save_economy(economy_data)

        embed = discord.Embed(
            title="✅ 구매 완료",
            description=(
                f"**{아이템}** 아이템을 **{수량}개** 구매했어요.\n"
                f"사용한 코인: **{total_price:,} 코인**"
            ),
            color=discord.Color.green()
        )
        embed.add_field(
            name="💰 남은 코인",
            value=f"{user_data['money']:,} 코인",
            inline=False
        )
        embed.add_field(
            name="📦 현재 보유 수량",
            value=f"{inventory.get(아이템, 0)}개",
            inline=False
        )

        await interaction.response.send_message(embed=embed, ephemeral=True)

    @app_commands.command(name="인벤토리", description="인벤토리 정보를 확인합니다.")
    @app_commands.describe(대상="인벤토리를 확인할 유저")
    async def inventory_command(
        self,
        interaction: discord.Interaction,
        대상: discord.Member | None = None
    ):
        if interaction.guild is None:
            await interaction.response.send_message(
                "인벤토리는 서버에서만 사용할 수 있어요.",
                ephemeral=True
            )
            return

        target = 대상 or interaction.user
        embed = build_inventory_embed(target)
        await interaction.response.send_message(embed=embed, ephemeral=True)


async def setup(bot):
    await bot.add_cog(Shop(bot))