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


def remove_one_item(user_data: dict, item_name: str) -> bool:
    inventory = user_data.setdefault("inventory", {})
    current_amount = inventory.get(item_name, 0)

    if current_amount <= 0:
        return False

    inventory[item_name] = current_amount - 1
    if inventory[item_name] <= 0:
        del inventory[item_name]

    return True


def parse_hex_color(color_text: str) -> discord.Color | None:
    text = color_text.strip().replace("#", "").upper()

    if len(text) != 6:
        return None

    try:
        value = int(text, 16)
    except ValueError:
        return None

    return discord.Color(value)


def title_exists(user_data: dict, title_name: str) -> bool:
    for title in user_data.get("titles", []):
        if isinstance(title, dict):
            if str(title.get("name", "")).strip() == title_name:
                return True
        else:
            if str(title).strip() == title_name:
                return True
    return False


def get_inventory_usable_items(user_id: str) -> list[tuple[str, int, dict]]:
    economy_data = load_economy()
    shop_data = load_shop()

    user_data = ensure_user(economy_data, user_id)
    inventory = user_data.get("inventory", {})

    results = []
    for item_name, amount in inventory.items():
        if amount <= 0:
            continue

        item_info = shop_data["items"].get(item_name)
        if not item_info:
            continue

        if not item_info.get("usable", False):
            continue

        results.append((item_name, amount, item_info))

    return results


async def use_item_autocomplete(
    interaction: discord.Interaction,
    current: str
) -> list[app_commands.Choice[str]]:
    usable_items = get_inventory_usable_items(str(interaction.user.id))
    results = []

    for item_name, amount, _item_info in usable_items:
        if current.lower() not in item_name.lower():
            continue

        results.append(
            app_commands.Choice(
                name=f"{item_name} ({amount}개 보유)",
                value=item_name
            )
        )

    return results[:25]


class TitleCreateModal(discord.ui.Modal, title="칭호 생성"):
    칭호이름 = discord.ui.TextInput(
        label="새 칭호 이름",
        placeholder="예: 전설의 도박왕",
        min_length=1,
        max_length=20,
        required=True
    )

    색상코드 = discord.ui.TextInput(
        label="역할 색상 코드",
        placeholder="예: #FFAA00",
        min_length=7,
        max_length=7,
        required=True
    )

    def __init__(self, item_name: str):
        super().__init__()
        self.item_name = item_name

    async def on_submit(self, interaction: discord.Interaction):
        if interaction.guild is None:
            await interaction.response.send_message(
                "칭호 생성은 서버에서만 사용할 수 있어요.",
                ephemeral=True
            )
            return

        member = interaction.guild.get_member(interaction.user.id)
        if member is None:
            await interaction.response.send_message(
                "서버 멤버 정보를 찾을 수 없어요.",
                ephemeral=True
            )
            return

        economy_data = load_economy()
        user_data = ensure_user(economy_data, str(interaction.user.id))

        inventory = user_data.get("inventory", {})
        if inventory.get(self.item_name, 0) <= 0:
            await interaction.response.send_message(
                "칭호생성권을 보유하고 있지 않아요.",
                ephemeral=True
            )
            return

        raw_title = str(self.칭호이름).strip()
        title_name = " ".join(raw_title.split())

        raw_color = str(self.색상코드).strip().upper()
        if not raw_color.startswith("#"):
            raw_color = f"#{raw_color}"

        if not title_name:
            await interaction.response.send_message(
                "칭호 이름은 비워둘 수 없어요.",
                ephemeral=True
            )
            return

        if "[" in title_name or "]" in title_name:
            await interaction.response.send_message(
                "칭호에는 `[` 또는 `]` 문자를 사용할 수 없어요.",
                ephemeral=True
            )
            return

        if len(title_name) > 20:
            await interaction.response.send_message(
                "칭호는 20자 이하로 입력해 주세요.",
                ephemeral=True
            )
            return

        role_color = parse_hex_color(raw_color)
        if role_color is None:
            await interaction.response.send_message(
                "색상 코드는 `#RRGGBB` 형식으로 입력해 주세요. 예: `#FFAA00`",
                ephemeral=True
            )
            return

        if title_exists(user_data, title_name):
            await interaction.response.send_message(
                "이미 같은 이름의 칭호를 보유하고 있어요.",
                ephemeral=True
            )
            return

        existing_role = discord.utils.get(interaction.guild.roles, name=title_name)
        if existing_role is not None:
            await interaction.response.send_message(
                "이미 같은 이름의 역할이 서버에 존재해요. 다른 칭호 이름을 입력해 주세요.",
                ephemeral=True
            )
            return

        try:
            new_role = await interaction.guild.create_role(
                name=title_name,
                colour=role_color,
                reason=f"Dimo 칭호 생성 - {interaction.user}"
            )
        except discord.Forbidden:
            await interaction.response.send_message(
                "역할을 생성할 권한이 없어요. 봇 권한과 역할 위치를 확인해 주세요.",
                ephemeral=True
            )
            return
        except discord.HTTPException:
            await interaction.response.send_message(
                "역할 생성 중 오류가 발생했어요.",
                ephemeral=True
            )
            return

        role_added = True
        try:
            await member.add_roles(new_role, reason="Dimo 칭호 역할 지급")
        except discord.Forbidden:
            role_added = False
        except discord.HTTPException:
            role_added = False

        user_data.setdefault("titles", []).append({
            "name": title_name,
            "level": 0,
            "bonus_type": None,
            "bonus_value": 0,
            "role_id": new_role.id,
            "color": raw_color
        })

        removed = remove_one_item(user_data, self.item_name)
        if not removed:
            await interaction.response.send_message(
                "아이템 차감 중 오류가 발생했어요.",
                ephemeral=True
            )
            return

        save_economy(economy_data)

        embed = discord.Embed(
            title="🏷 칭호 생성 완료",
            description=f"새 칭호 **[{title_name}]** 를 만들었어요.",
            color=role_color
        )
        embed.add_field(
            name="🎨 선택한 색상",
            value=raw_color,
            inline=False
        )
        embed.add_field(
            name="🎭 생성된 역할",
            value=new_role.mention,
            inline=False
        )
        embed.add_field(
            name="📦 남은 칭호생성권",
            value=f"{user_data.get('inventory', {}).get(self.item_name, 0)}개",
            inline=False
        )

        if not role_added:
            embed.add_field(
                name="⚠ 역할 지급 상태",
                value="역할은 생성됐지만 자동 지급은 실패했어요. 봇 권한과 역할 위치를 확인해 주세요.",
                inline=False
            )

        embed.set_footer(text="생성한 칭호는 /칭호목록, /칭호장착 에서 확인할 수 있어요.")
        await interaction.response.send_message(embed=embed, ephemeral=True)


class NicknameChangeModal(discord.ui.Modal, title="닉네임 변경"):
    새닉네임 = discord.ui.TextInput(
        label="새 서버 닉네임",
        placeholder="예: 김 / 도박왕김 / 디모유저",
        min_length=1,
        max_length=24,
        required=True
    )

    def __init__(self, item_name: str):
        super().__init__()
        self.item_name = item_name

    async def on_submit(self, interaction: discord.Interaction):
        if interaction.guild is None:
            await interaction.response.send_message(
                "닉네임 변경은 서버에서만 사용할 수 있어요.",
                ephemeral=True
            )
            return

        member = interaction.guild.get_member(interaction.user.id)
        if member is None:
            await interaction.response.send_message(
                "서버 멤버 정보를 찾을 수 없어요.",
                ephemeral=True
            )
            return

        economy_data = load_economy()
        user_data = ensure_user(economy_data, str(interaction.user.id))

        inventory = user_data.get("inventory", {})
        if inventory.get(self.item_name, 0) <= 0:
            await interaction.response.send_message(
                "닉네임변경권을 보유하고 있지 않아요.",
                ephemeral=True
            )
            return

        raw_nickname = str(self.새닉네임).strip()
        new_nickname = " ".join(raw_nickname.split())

        if not new_nickname:
            await interaction.response.send_message(
                "닉네임은 비워둘 수 없어요.",
                ephemeral=True
            )
            return

        if len(new_nickname) > 24:
            await interaction.response.send_message(
                "닉네임은 24자 이하로 입력해 주세요.",
                ephemeral=True
            )
            return

        if "[" in new_nickname or "]" in new_nickname:
            await interaction.response.send_message(
                "닉네임에는 `[` 또는 `]` 문자를 사용할 수 없어요.",
                ephemeral=True
            )
            return

        equipped_title = str(user_data.get("equipped_title", "")).strip()

        if not user_data.get("base_nickname"):
            current_name = member.display_name
            if equipped_title and current_name.startswith(f"[{equipped_title}] "):
                current_name = current_name[len(f"[{equipped_title}] "):]
            user_data["base_nickname"] = current_name

        final_nickname = f"[{equipped_title}] {new_nickname}" if equipped_title else new_nickname

        try:
            await member.edit(nick=final_nickname)
        except discord.Forbidden:
            await interaction.response.send_message(
                "닉네임을 변경할 권한이 없어요. 봇 역할 위치와 권한을 확인해 주세요.",
                ephemeral=True
            )
            return
        except discord.HTTPException:
            await interaction.response.send_message(
                "닉네임 변경 중 오류가 발생했어요.",
                ephemeral=True
            )
            return

        removed = remove_one_item(user_data, self.item_name)
        if not removed:
            await interaction.response.send_message(
                "아이템 차감 중 오류가 발생했어요.",
                ephemeral=True
            )
            return

        user_data["base_nickname"] = new_nickname
        save_economy(economy_data)

        embed = discord.Embed(
            title="✨ 닉네임 변경 완료",
            description=f"새 닉네임이 **{final_nickname}** 로 적용되었어요.",
            color=discord.Color.teal()
        )
        embed.add_field(
            name="📦 남은 닉네임변경권",
            value=f"{user_data.get('inventory', {}).get(self.item_name, 0)}개",
            inline=False
        )

        await interaction.response.send_message(embed=embed, ephemeral=True)


class Use(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    async def apply_luck_effect(
        self,
        interaction: discord.Interaction,
        item_name: str,
        add_value: int,
        user_data: dict,
        economy_data: dict
    ):
        active_effects = user_data.setdefault("active_effects", {})
        inventory = user_data.setdefault("inventory", {})

        removed = remove_one_item(user_data, item_name)
        if not removed:
            await interaction.response.send_message(
                "아이템 차감 중 오류가 발생했어요.",
                ephemeral=True
            )
            return

        active_effects["luck"] = active_effects.get("luck", 0) + add_value
        save_economy(economy_data)

        embed = discord.Embed(
            title="🍀 아이템 사용 완료",
            description=f"**{item_name}** 을(를) 사용했어요.",
            color=discord.Color.green()
        )
        embed.add_field(
            name="✨ 적용 효과",
            value=f"다음 도박/슬롯 1회 확률 **+{add_value}%**",
            inline=False
        )
        embed.add_field(
            name="🪄 현재 누적 행운 효과",
            value=f"{active_effects.get('luck', 0)}%",
            inline=False
        )
        embed.add_field(
            name="📦 남은 수량",
            value=f"{inventory.get(item_name, 0)}개",
            inline=False
        )

        await interaction.response.send_message(embed=embed, ephemeral=True)

    @app_commands.command(name="사용", description="보유 중인 아이템을 사용합니다.")
    @app_commands.describe(아이템="사용할 아이템")
    @app_commands.autocomplete(아이템=use_item_autocomplete)
    async def use_command(self, interaction: discord.Interaction, 아이템: str):
        if interaction.guild is None:
            await interaction.response.send_message(
                "아이템 사용은 서버에서만 사용할 수 있어요.",
                ephemeral=True
            )
            return

        economy_data = load_economy()
        shop_data = load_shop()
        user_data = ensure_user(economy_data, str(interaction.user.id))

        inventory = user_data.get("inventory", {})
        if inventory.get(아이템, 0) <= 0:
            await interaction.response.send_message(
                "해당 아이템을 보유하고 있지 않아요.",
                ephemeral=True
            )
            return

        item_info = shop_data["items"].get(아이템)
        if not item_info:
            await interaction.response.send_message(
                "존재하지 않는 아이템이에요.",
                ephemeral=True
            )
            return

        if not item_info.get("usable", False):
            await interaction.response.send_message(
                "이 아이템은 사용할 수 없어요.",
                ephemeral=True
            )
            return

        effect_type = item_info.get("effect_type")

        if effect_type == "luck_5":
            await self.apply_luck_effect(
                interaction=interaction,
                item_name=아이템,
                add_value=5,
                user_data=user_data,
                economy_data=economy_data
            )
            return

        if effect_type == "luck_10":
            await self.apply_luck_effect(
                interaction=interaction,
                item_name=아이템,
                add_value=10,
                user_data=user_data,
                economy_data=economy_data
            )
            return

        if effect_type == "title_create":
            await interaction.response.send_modal(TitleCreateModal(아이템))
            return

        if effect_type == "nickname_change":
            await interaction.response.send_modal(NicknameChangeModal(아이템))
            return

        await interaction.response.send_message(
            "아직 구현되지 않은 아이템 효과예요.",
            ephemeral=True
        )


async def setup(bot):
    await bot.add_cog(Use(bot))