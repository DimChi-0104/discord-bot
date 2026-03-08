import discord
from discord import app_commands
from discord.ext import commands
import json
import os

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

    if not isinstance(data, dict):
        data = {"users": {}}

    if "users" not in data or not isinstance(data["users"], dict):
        data["users"] = {}

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
                    "price": 350,
                    "description": "출석 시 자동으로 1개 사용되어 추가 보상 500코인을 지급합니다.",
                    "category": "소모품",
                    "buyable": True,
                    "usable": False,
                    "auto_use": True,
                    "effect_type": "attendance_bonus"
                },
                "행운권": {
                    "price": 7500,
                    "description": "직접 사용 시 다음 도박/슬롯 1회에 행운 효과가 적용됩니다.",
                    "category": "소모품",
                    "buyable": True,
                    "usable": True,
                    "auto_use": False,
                    "effect_type": "luck"
                },
                "칭호생성권": {
                    "price": 5000,
                    "description": "직접 사용 후 칭호 이름과 색상을 설정해 새 칭호를 만들 수 있습니다.",
                    "category": "장식",
                    "buyable": True,
                    "usable": True,
                    "auto_use": False,
                    "effect_type": "title_create"
                },
                "닉네임변경권": {
                    "price": 10000,
                    "description": "직접 사용 후 서버 닉네임을 변경할 수 있습니다.",
                    "category": "장식",
                    "buyable": True,
                    "usable": True,
                    "auto_use": False,
                    "effect_type": "nickname_change"
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

    if not isinstance(data, dict):
        data = {"items": {}}

    if "items" not in data or not isinstance(data["items"], dict):
        data["items"] = {}

    temp_file = SHOP_FILE + ".tmp"
    with open(temp_file, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=4)

    os.replace(temp_file, SHOP_FILE)


def normalize_hex_color(value: str) -> str | None:
    if not isinstance(value, str):
        return None

    value = value.strip().upper()
    if not value.startswith("#"):
        value = f"#{value}"

    if len(value) != 7:
        return None

    allowed = "0123456789ABCDEF"
    if all(ch in allowed for ch in value[1:]):
        return value

    return None


def get_next_title_id(titles: list) -> int:
    max_id = 0
    for title in titles:
        if isinstance(title, dict):
            title_id = title.get("id", 0)
            if isinstance(title_id, int) and title_id > max_id:
                max_id = title_id
    return max_id + 1


def migrate_legacy_title(user: dict):
    titles = user.get("titles", [])
    if not isinstance(titles, list):
        user["titles"] = []
        titles = user["titles"]

    title_data = user.get("title_data", {})
    if not isinstance(title_data, dict):
        return

    legacy_name = str(title_data.get("name", "")).strip()
    legacy_color = str(title_data.get("color", "#FFFFFF")).strip()

    if legacy_name and not titles:
        color = normalize_hex_color(legacy_color) or "#FFFFFF"
        titles.append({
            "id": 1,
            "name": legacy_name,
            "color": color,
            "level": 1,
            "equipped": True
        })


def get_user_data(data, user_id: int):
    user_id = str(user_id)

    if user_id not in data["users"] or not isinstance(data["users"][user_id], dict):
        data["users"][user_id] = {}

    user = data["users"][user_id]

    defaults = {
        "money": 0,
        "last_attendance": "",
        "streak": 0,
        "total_attendance": 0,
        "win": 0,
        "lose": 0,
        "slot_win": 0,
        "slot_lose": 0,
        "inventory": {},
        "titles": [],
        "active_effects": {
            "luck": 0,
            "title_create": 0,
            "nickname_change": 0
        },
        "title_data": {
            "name": "",
            "color": "#FFFFFF"
        }
    }

    for key, value in defaults.items():
        if key not in user or not isinstance(user[key], type(value)):
            user[key] = value

    if "inventory" not in user or not isinstance(user["inventory"], dict):
        user["inventory"] = {}

    if "titles" not in user or not isinstance(user["titles"], list):
        user["titles"] = []

    if "active_effects" not in user or not isinstance(user["active_effects"], dict):
        user["active_effects"] = {}

    user["active_effects"].setdefault("luck", 0)
    user["active_effects"].setdefault("title_create", 0)
    user["active_effects"].setdefault("nickname_change", 0)

    if "title_data" not in user or not isinstance(user["title_data"], dict):
        user["title_data"] = {"name": "", "color": "#FFFFFF"}

    user["title_data"].setdefault("name", "")
    user["title_data"].setdefault("color", "#FFFFFF")

    migrate_legacy_title(user)

    if user["money"] < 0:
        user["money"] = 0
    if user["streak"] < 0:
        user["streak"] = 0
    if user["total_attendance"] < 0:
        user["total_attendance"] = 0
    if user["win"] < 0:
        user["win"] = 0
    if user["lose"] < 0:
        user["lose"] = 0
    if user["slot_win"] < 0:
        user["slot_win"] = 0
    if user["slot_lose"] < 0:
        user["slot_lose"] = 0

    return user


class TitleCreateModal(discord.ui.Modal, title="칭호 생성"):
    칭호이름 = discord.ui.TextInput(
        label="칭호 이름",
        placeholder="예: 전설의 도박왕",
        min_length=1,
        max_length=20
    )

    칭호색상 = discord.ui.TextInput(
        label="칭호 색상 (HEX)",
        placeholder="#FFD700",
        min_length=6,
        max_length=7
    )

    def __init__(self, user_id: int):
        super().__init__()
        self.user_id = user_id

    async def on_submit(self, interaction: discord.Interaction):
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("이 창은 다른 사람이 사용할 수 없어요.", ephemeral=True)
            return

        data = load_economy()
        user = get_user_data(data, interaction.user.id)
        active_effects = user.get("active_effects", {})

        if active_effects.get("title_create", 0) <= 0:
            await interaction.response.send_message(
                "칭호생성권이 활성화되어 있지 않아요. 다시 아이템을 사용해주세요.",
                ephemeral=True
            )
            return

        title_name = str(self.칭호이름).strip()
        title_color = normalize_hex_color(str(self.칭호색상).strip())

        if not title_name:
            await interaction.response.send_message("칭호 이름은 비워둘 수 없어요.", ephemeral=True)
            return

        if title_color is None:
            await interaction.response.send_message(
                "색상 코드는 `#FFD700` 같은 HEX 형식으로 입력해주세요.",
                ephemeral=True
            )
            return

        titles = user.get("titles", [])

        for title in titles:
            if isinstance(title, dict) and str(title.get("name", "")).strip() == title_name:
                await interaction.response.send_message(
                    "이미 같은 이름의 칭호를 가지고 있어요.",
                    ephemeral=True
                )
                return

        new_title = {
            "id": get_next_title_id(titles),
            "name": title_name,
            "color": title_color,
            "level": 1,
            "equipped": False
        }
        titles.append(new_title)
        active_effects["title_create"] = 0
        save_economy(data)

        embed_color = int(title_color.replace("#", ""), 16)

        embed = discord.Embed(
            title="🏷 칭호 생성 완료",
            description=(
                f"칭호 이름: `{title_name}`\n"
                f"칭호 색상: `{title_color}`\n"
                f"강화 단계: `+1`\n\n"
                f"`/칭호목록`에서 확인하고 `/칭호장착 번호`로 장착할 수 있어요."
            ),
            color=embed_color
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)


class TitleCreateView(discord.ui.View):
    def __init__(self, user_id: int):
        super().__init__(timeout=300)
        self.user_id = user_id

    @discord.ui.button(label="칭호 생성하기", style=discord.ButtonStyle.primary)
    async def set_title(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("이 버튼은 다른 사람이 사용할 수 없어요.", ephemeral=True)
            return

        await interaction.response.send_modal(TitleCreateModal(self.user_id))


class NicknameChangeModal(discord.ui.Modal, title="닉네임 변경"):
    새닉네임 = discord.ui.TextInput(
        label="새 닉네임",
        placeholder="변경할 닉네임을 입력하세요.",
        min_length=1,
        max_length=32
    )

    def __init__(self, user_id: int):
        super().__init__()
        self.user_id = user_id

    async def on_submit(self, interaction: discord.Interaction):
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("이 창은 다른 사람이 사용할 수 없어요.", ephemeral=True)
            return

        if interaction.guild is None:
            await interaction.response.send_message("서버에서만 사용할 수 있어요.", ephemeral=True)
            return

        data = load_economy()
        user = get_user_data(data, interaction.user.id)
        active_effects = user.get("active_effects", {})

        if active_effects.get("nickname_change", 0) <= 0:
            await interaction.response.send_message(
                "닉네임변경권이 활성화되어 있지 않아요. 다시 아이템을 사용해주세요.",
                ephemeral=True
            )
            return

        new_nick = str(self.새닉네임).strip()

        try:
            await interaction.user.edit(nick=new_nick)
        except discord.Forbidden:
            await interaction.response.send_message(
                "닉네임을 변경할 권한이 없어요. 봇 권한과 역할 위치를 확인해주세요.",
                ephemeral=True
            )
            return
        except discord.HTTPException:
            await interaction.response.send_message("닉네임 변경 중 오류가 발생했어요.", ephemeral=True)
            return

        active_effects["nickname_change"] = 0
        save_economy(data)

        embed = discord.Embed(
            title="✅ 닉네임 변경 완료",
            description=f"새 닉네임이 `{new_nick}`(으)로 변경되었어요.",
            color=discord.Color.green()
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)


class NicknameChangeView(discord.ui.View):
    def __init__(self, user_id: int):
        super().__init__(timeout=300)
        self.user_id = user_id

    @discord.ui.button(label="닉네임 변경하기", style=discord.ButtonStyle.primary)
    async def change_nickname(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("이 버튼은 다른 사람이 사용할 수 없어요.", ephemeral=True)
            return

        await interaction.response.send_modal(NicknameChangeModal(self.user_id))


class Shop(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="상점", description="상점 아이템 목록을 확인합니다.")
    async def shop(self, interaction: discord.Interaction):
        if interaction.guild is None:
            await interaction.response.send_message("이 명령어는 서버에서만 사용할 수 있어요.", ephemeral=True)
            return

        if interaction.user.bot:
            await interaction.response.send_message("봇 계정은 사용할 수 없어요.", ephemeral=True)
            return

        shop_data = load_shop()
        items = shop_data.get("items", {})

        if not items:
            await interaction.response.send_message("현재 상점에 등록된 아이템이 없어요.", ephemeral=True)
            return

        embed = discord.Embed(
            title="🛒 디모 상점",
            description="구매 가능한 아이템 목록이에요.",
            color=discord.Color.blue()
        )

        visible_count = 0

        for item_name, item_info in items.items():
            if not isinstance(item_info, dict):
                continue
            if not item_info.get("buyable", False):
                continue

            price = item_info.get("price", 0)
            description = item_info.get("description", "설명이 없습니다.")
            category = item_info.get("category", "기타")
            auto_use = item_info.get("auto_use", False)
            usable = item_info.get("usable", False)

            if not isinstance(price, int) or price < 0:
                price = 0

            use_type = "자동 사용" if auto_use else ("직접 사용" if usable else "사용 불가")

            embed.add_field(
                name=f"{item_name} | {price:,} 코인",
                value=(
                    f"분류: `{category}`\n"
                    f"사용 방식: `{use_type}`\n"
                    f"{description}"
                ),
                inline=False
            )
            visible_count += 1

        if visible_count == 0:
            await interaction.response.send_message("현재 구매 가능한 아이템이 없어요.", ephemeral=True)
            return

        embed.set_footer(text="/구매 [아이템명] [수량], /사용 [아이템명]")
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="구매", description="상점에서 아이템을 구매합니다.")
    async def buy(self, interaction: discord.Interaction, 아이템: str, 수량: app_commands.Range[int, 1, 100]):
        if interaction.guild is None:
            await interaction.response.send_message("이 명령어는 서버에서만 사용할 수 있어요.", ephemeral=True)
            return

        if interaction.user.bot:
            await interaction.response.send_message("봇 계정은 사용할 수 없어요.", ephemeral=True)
            return

        economy_data = load_economy()
        shop_data = load_shop()

        user = get_user_data(economy_data, interaction.user.id)
        items = shop_data.get("items", {})

        if 아이템 not in items:
            await interaction.response.send_message("존재하지 않는 아이템이에요.", ephemeral=True)
            return

        item_info = items[아이템]

        if not isinstance(item_info, dict):
            await interaction.response.send_message("아이템 정보가 올바르지 않아요.", ephemeral=True)
            return

        if not item_info.get("buyable", False):
            await interaction.response.send_message("이 아이템은 현재 구매할 수 없어요.", ephemeral=True)
            return

        price = item_info.get("price", 0)
        if not isinstance(price, int) or price <= 0:
            await interaction.response.send_message("아이템 가격 정보가 올바르지 않아요.", ephemeral=True)
            return

        total_price = price * 수량

        if user["money"] < total_price:
            await interaction.response.send_message(
                f"재화가 부족해요.\n현재 보유 재화: `{user['money']} 코인`\n필요 재화: `{total_price} 코인`",
                ephemeral=True
            )
            return

        user["money"] -= total_price

        if user["money"] < 0:
            user["money"] = 0
            await interaction.response.send_message("오류 방지를 위해 구매가 취소되었어요.", ephemeral=True)
            return

        current_amount = user["inventory"].get(아이템, 0)
        if not isinstance(current_amount, int) or current_amount < 0:
            current_amount = 0

        user["inventory"][아이템] = current_amount + 수량
        save_economy(economy_data)

        embed = discord.Embed(
            title="✅ 아이템 구매 완료",
            description=(
                f"{interaction.user.mention}님이 아이템을 구매했어요.\n\n"
                f"아이템: `{아이템}`\n"
                f"수량: `{수량}개`\n"
                f"총 가격: `{total_price} 코인`\n"
                f"남은 재화: `{user['money']} 코인`"
            ),
            color=discord.Color.green()
        )
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="인벤토리", description="보유 중인 아이템을 확인합니다.")
    async def inventory(self, interaction: discord.Interaction, 대상: discord.Member = None):
        if interaction.guild is None:
            await interaction.response.send_message("이 명령어는 서버에서만 사용할 수 있어요.", ephemeral=True)
            return

        if interaction.user.bot:
            await interaction.response.send_message("봇 계정은 사용할 수 없어요.", ephemeral=True)
            return

        target = 대상 or interaction.user

        if target.bot:
            await interaction.response.send_message("봇 계정의 인벤토리는 확인할 수 없어요.", ephemeral=True)
            return

        economy_data = load_economy()
        user = get_user_data(economy_data, target.id)
        inventory_data = user.get("inventory", {})
        active_effects = user.get("active_effects", {})

        lines = []
        for item_name, amount in inventory_data.items():
            if isinstance(amount, int) and amount > 0:
                lines.append(f"• {item_name} x{amount}")

        effect_name_map = {
            "luck": "행운 효과",
            "title_create": "칭호 생성 가능",
            "nickname_change": "닉네임 변경 가능"
        }

        effect_lines = []
        for effect_name, value in active_effects.items():
            if isinstance(value, int) and value > 0:
                effect_lines.append(f"• {effect_name_map.get(effect_name, effect_name)}")

        embed = discord.Embed(
            title=f"🎒 {target.display_name}님의 인벤토리",
            color=discord.Color.gold()
        )

        embed.description = "\n".join(lines) if lines else "보유 중인 아이템이 없어요."

        if effect_lines:
            embed.add_field(name="현재 활성 효과", value="\n".join(effect_lines), inline=False)

        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="사용", description="보유 중인 아이템을 사용합니다.")
    async def use_item(self, interaction: discord.Interaction, 아이템: str):
        if interaction.guild is None:
            await interaction.response.send_message("이 명령어는 서버에서만 사용할 수 있어요.", ephemeral=True)
            return

        if interaction.user.bot:
            await interaction.response.send_message("봇 계정은 사용할 수 없어요.", ephemeral=True)
            return

        economy_data = load_economy()
        shop_data = load_shop()

        user = get_user_data(economy_data, interaction.user.id)
        items = shop_data.get("items", {})
        inventory = user.get("inventory", {})
        active_effects = user.get("active_effects", {})

        if 아이템 not in items:
            await interaction.response.send_message("존재하지 않는 아이템이에요.", ephemeral=True)
            return

        item_info = items[아이템]
        if not isinstance(item_info, dict):
            await interaction.response.send_message("아이템 정보가 올바르지 않아요.", ephemeral=True)
            return

        owned_count = inventory.get(아이템, 0)
        if not isinstance(owned_count, int) or owned_count <= 0:
            await interaction.response.send_message("해당 아이템을 보유하고 있지 않아요.", ephemeral=True)
            return

        if item_info.get("auto_use", False):
            await interaction.response.send_message(
                "이 아이템은 직접 사용하는 아이템이 아니라 자동 사용 아이템이에요.",
                ephemeral=True
            )
            return

        if not item_info.get("usable", False):
            await interaction.response.send_message("이 아이템은 현재 사용할 수 없어요.", ephemeral=True)
            return

        effect_type = item_info.get("effect_type", "")
        if not isinstance(effect_type, str) or not effect_type:
            await interaction.response.send_message("아이템 효과 정보가 올바르지 않아요.", ephemeral=True)
            return

        if effect_type not in active_effects:
            active_effects[effect_type] = 0

        if active_effects[effect_type] > 0:
            await interaction.response.send_message("이미 같은 효과가 활성화되어 있어요.", ephemeral=True)
            return

        inventory[아이템] -= 1
        if inventory[아이템] <= 0:
            del inventory[아이템]

        active_effects[effect_type] = 1
        save_economy(economy_data)

        if effect_type == "title_create":
            embed = discord.Embed(
                title="🏷 칭호생성권 사용 완료",
                description="아래 버튼을 눌러 새로운 칭호를 만들 수 있어요.",
                color=discord.Color.purple()
            )
            await interaction.response.send_message(
                embed=embed,
                view=TitleCreateView(interaction.user.id),
                ephemeral=True
            )
            return

        if effect_type == "nickname_change":
            embed = discord.Embed(
                title="✨ 닉네임변경권 사용 완료",
                description="아래 버튼을 눌러 서버 닉네임을 변경할 수 있어요.",
                color=discord.Color.purple()
            )
            await interaction.response.send_message(
                embed=embed,
                view=NicknameChangeView(interaction.user.id),
                ephemeral=True
            )
            return

        effect_text = {
            "luck": "행운 효과가 활성화되었어요. 다음 도박/슬롯 1회에 적용돼요."
        }.get(effect_type, "아이템 효과가 활성화되었어요.")

        embed = discord.Embed(
            title="✨ 아이템 사용 완료",
            description=(
                f"{interaction.user.mention}님이 `{아이템}` 아이템을 사용했어요.\n\n"
                f"{effect_text}\n"
                f"남은 보유 개수: `{inventory.get(아이템, 0)}개`"
            ),
            color=discord.Color.purple()
        )
        await interaction.response.send_message(embed=embed)


async def setup(bot):
    await bot.add_cog(Shop(bot))