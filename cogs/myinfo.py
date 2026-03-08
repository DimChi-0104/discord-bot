import discord
from discord import app_commands
from discord.ext import commands
import json
import os

DATA_FILE = "data/economy.json"


def load_data():
    os.makedirs("data", exist_ok=True)

    if not os.path.exists(DATA_FILE):
        with open(DATA_FILE, "w", encoding="utf-8") as f:
            json.dump({"users": {}}, f, ensure_ascii=False, indent=4)
        return {"users": {}}

    try:
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)

        if not isinstance(data, dict):
            data = {"users": {}}

        if "users" not in data or not isinstance(data["users"], dict):
            data["users"] = {}

        return data

    except (json.JSONDecodeError, OSError):
        with open(DATA_FILE, "w", encoding="utf-8") as f:
            json.dump({"users": {}}, f, ensure_ascii=False, indent=4)
        return {"users": {}}


def save_data(data):
    os.makedirs("data", exist_ok=True)

    if not isinstance(data, dict):
        data = {"users": {}}

    if "users" not in data or not isinstance(data["users"], dict):
        data["users"] = {}

    temp_file = DATA_FILE + ".tmp"
    with open(temp_file, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=4)

    os.replace(temp_file, DATA_FILE)


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


def parse_embed_color(hex_color: str) -> discord.Color:
    if not isinstance(hex_color, str):
        return discord.Color.blurple()

    value = hex_color.strip().upper()
    if value.startswith("#"):
        value = value[1:]

    if len(value) != 6:
        return discord.Color.blurple()

    try:
        return discord.Color(int(value, 16))
    except ValueError:
        return discord.Color.blurple()


def get_equipped_title(user: dict):
    titles = user.get("titles", [])
    if not isinstance(titles, list):
        return None

    for title in titles:
        if isinstance(title, dict) and title.get("equipped", False):
            return title

    return None


class MyInfo(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="내정보", description="내 프로필 정보와 장착한 칭호, 통계를 확인합니다.")
    async def my_info(self, interaction: discord.Interaction, 대상: discord.Member = None):
        if interaction.guild is None:
            await interaction.response.send_message("이 명령어는 서버에서만 사용할 수 있어요.", ephemeral=True)
            return

        target = 대상 or interaction.user

        if target.bot:
            await interaction.response.send_message("봇 계정의 정보는 확인할 수 없어요.", ephemeral=True)
            return

        data = load_data()
        user = get_user_data(data, target.id)
        save_data(data)

        money = user.get("money", 0)
        streak = user.get("streak", 0)
        total_attendance = user.get("total_attendance", 0)
        win = user.get("win", 0)
        lose = user.get("lose", 0)
        slot_win = user.get("slot_win", 0)
        slot_lose = user.get("slot_lose", 0)

        inventory = user.get("inventory", {})
        active_effects = user.get("active_effects", {})
        equipped_title = get_equipped_title(user)

        if equipped_title:
            title_name = str(equipped_title.get("name", "")).strip()
            title_color = str(equipped_title.get("color", "#FFFFFF")).strip()
            title_level = equipped_title.get("level", 1)
            if not isinstance(title_level, int) or title_level < 1:
                title_level = 1
        else:
            title_name = ""
            title_color = "#5865F2"
            title_level = 0

        embed_color = parse_embed_color(title_color)

        effect_name_map = {
            "luck": "🍀 행운 효과",
            "title_create": "🏷 칭호 생성 가능",
            "nickname_change": "✏️ 닉네임 변경 가능"
        }

        active_effect_list = []
        for effect_name, value in active_effects.items():
            if isinstance(value, int) and value > 0:
                active_effect_list.append(effect_name_map.get(effect_name, effect_name))

        active_effect_text = "\n".join(active_effect_list) if active_effect_list else "없음"

        item_lines = []
        total_items = 0
        for item_name, amount in inventory.items():
            if isinstance(amount, int) and amount > 0:
                item_lines.append(f"• {item_name} x{amount}")
                total_items += amount

        if item_lines:
            inventory_text = "\n".join(item_lines[:5])
            if len(item_lines) > 5:
                inventory_text += f"\n... 외 {len(item_lines) - 5}종"
        else:
            inventory_text = "없음"

        total_gamble = win + lose
        gamble_rate = round((win / total_gamble) * 100, 1) if total_gamble > 0 else 0

        total_slot = slot_win + slot_lose
        slot_rate = round((slot_win / total_slot) * 100, 2) if total_slot > 0 else 0

        profile_title = f"🏷 {title_name} +{title_level}" if equipped_title else "🏷 장착한 칭호 없음"
        profile_subtitle = f"{target.mention}님의 프로필 카드"

        embed = discord.Embed(
            title=f"👤 {target.display_name}",
            description=f"{profile_title}\n{profile_subtitle}",
            color=embed_color
        )

        embed.set_thumbnail(url=target.display_avatar.url)

        embed.add_field(
            name="💰 경제",
            value=(
                f"보유 재화: `{money:,} 코인`\n"
                f"보유 아이템: `{total_items}개`\n"
                f"보유 칭호: `{len(user.get('titles', []))}개`"
            ),
            inline=True
        )

        embed.add_field(
            name="📅 출석",
            value=(
                f"연속 출석: `{streak}일`\n"
                f"총 출석: `{total_attendance}회`"
            ),
            inline=True
        )

        embed.add_field(
            name="🎨 장착 칭호",
            value=(
                f"이름: `{title_name if equipped_title else '없음'}`\n"
                f"색상: `{title_color if equipped_title else '없음'}`"
            ),
            inline=True
        )

        embed.add_field(
            name="🎲 도박 전적",
            value=(
                f"전적: `{win}승 / {lose}패`\n"
                f"승률: `{gamble_rate}%`"
            ),
            inline=True
        )

        embed.add_field(
            name="🎰 슬롯 전적",
            value=(
                f"전적: `{slot_win}승 / {slot_lose}패`\n"
                f"당첨률: `{slot_rate}%`"
            ),
            inline=True
        )

        embed.add_field(
            name="✨ 활성 효과",
            value=active_effect_text,
            inline=True
        )

        embed.add_field(
            name="🎒 인벤토리 요약",
            value=inventory_text,
            inline=False
        )

        embed.set_footer(text=f"User ID: {target.id}")
        await interaction.response.send_message(embed=embed)


async def setup(bot):
    await bot.add_cog(MyInfo(bot))