import json
import os

import discord
from discord import app_commands
from discord.ext import commands

ECONOMY_FILE = "data/economy.json"


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


def normalize_title_entry(title_entry):
    if isinstance(title_entry, dict):
        return {
            "name": str(title_entry.get("name", "이름 없음")),
            "level": int(title_entry.get("level", 0)),
            "bonus_type": title_entry.get("bonus_type"),
            "bonus_value": int(title_entry.get("bonus_value", 0)),
            "role_id": title_entry.get("role_id"),
            "color": str(title_entry.get("color", "#000000"))
        }

    return {
        "name": str(title_entry),
        "level": 0,
        "bonus_type": None,
        "bonus_value": 0,
        "role_id": None,
        "color": "#000000"
    }


def parse_hex_color(color_text: str) -> discord.Color:
    raw = str(color_text).strip().replace("#", "").upper()

    if len(raw) != 6:
        return discord.Color.default()

    try:
        return discord.Color(int(raw, 16))
    except ValueError:
        return discord.Color.default()


def get_title_list_text(user_data: dict) -> str:
    titles = user_data.get("titles", [])
    equipped_title = str(user_data.get("equipped_title", "")).strip()

    if not titles:
        return "보유 중인 칭호가 없어요."

    lines = []
    for idx, raw_title in enumerate(titles, start=1):
        title = normalize_title_entry(raw_title)
        title_name = title["name"]
        title_level = title["level"]
        color_text = title.get("color", "#000000")
        role_id = title.get("role_id")

        prefix = "✅ " if equipped_title == title_name else ""
        level_text = f" (+{title_level})" if title_level > 0 else ""
        role_text = " | 역할 연동" if role_id else ""

        lines.append(f"{prefix}{idx}. {title_name}{level_text} | 색상: {color_text}{role_text}")

    return "\n".join(lines)


def find_title_by_index(user_data: dict, index: int):
    titles = user_data.get("titles", [])

    if index < 1 or index > len(titles):
        return None, None, None

    raw_title = titles[index - 1]
    normalized = normalize_title_entry(raw_title)
    return titles, raw_title, normalized


async def ensure_title_role(
    guild: discord.Guild,
    member: discord.Member,
    titles_list: list,
    raw_title_entry,
    normalized_title: dict
):
    """
    반환값:
    {
        "role": discord.Role | None,
        "created": bool,
        "granted": bool,
        "status_text": str
    }
    """
    title_name = normalized_title["name"]
    stored_role_id = normalized_title.get("role_id")
    color_text = normalized_title.get("color", "#000000")

    role = guild.get_role(stored_role_id) if isinstance(stored_role_id, int) else None
    created = False
    granted = False

    # role_id가 있는데 서버에서 역할이 삭제된 경우 같은 이름 역할 탐색
    if role is None:
        role = discord.utils.get(guild.roles, name=title_name)

        # 이름 역할도 없으면 새로 생성
        if role is None:
            try:
                role = await guild.create_role(
                    name=title_name,
                    colour=parse_hex_color(color_text),
                    reason=f"Dimo 칭호 역할 복구 - {member}"
                )
                created = True
            except discord.Forbidden:
                return {
                    "role": None,
                    "created": False,
                    "granted": False,
                    "status_text": "역할을 다시 만들 권한이 없어요."
                }
            except discord.HTTPException:
                return {
                    "role": None,
                    "created": False,
                    "granted": False,
                    "status_text": "역할 복구 중 오류가 발생했어요."
                }

        # 찾았거나 새로 만든 역할의 ID를 저장 데이터에 반영
        if isinstance(raw_title_entry, dict):
            raw_title_entry["role_id"] = role.id

    # 현재 장착하려는 칭호 역할이 멤버에게 없으면 다시 지급
    if role not in member.roles:
        try:
            await member.add_roles(role, reason="Dimo 칭호 역할 동기화")
            granted = True
        except discord.Forbidden:
            return {
                "role": role,
                "created": created,
                "granted": False,
                "status_text": "역할은 확인됐지만 지급 권한이 없어요."
            }
        except discord.HTTPException:
            return {
                "role": role,
                "created": created,
                "granted": False,
                "status_text": "역할 지급 중 오류가 발생했어요."
            }

    # 다른 칭호 역할은 제거
    title_role_ids = set()
    for item in titles_list:
        title = normalize_title_entry(item)
        role_id = title.get("role_id")
        if isinstance(role_id, int):
            title_role_ids.add(role_id)

    removable_roles = [
        r for r in member.roles
        if r.id in title_role_ids and r.id != role.id
    ]

    if removable_roles:
        try:
            await member.remove_roles(*removable_roles, reason="Dimo 칭호 역할 교체")
        except discord.Forbidden:
            pass
        except discord.HTTPException:
            pass

    if created and granted:
        status_text = "역할을 새로 복구하고 다시 지급했어요."
    elif created:
        status_text = "역할을 새로 복구했어요."
    elif granted:
        status_text = "칭호 역할을 다시 지급했어요."
    else:
        status_text = "칭호 역할이 이미 정상적으로 적용되어 있었어요."

    return {
        "role": role,
        "created": created,
        "granted": granted,
        "status_text": status_text
    }


async def remove_all_title_roles(guild: discord.Guild, member: discord.Member, user_data: dict):
    title_role_ids = set()

    for raw_title in user_data.get("titles", []):
        title = normalize_title_entry(raw_title)
        role_id = title.get("role_id")
        if isinstance(role_id, int):
            title_role_ids.add(role_id)

    removable_roles = [role for role in member.roles if role.id in title_role_ids]

    if removable_roles:
        try:
            await member.remove_roles(*removable_roles, reason="Dimo 칭호 해제")
        except discord.Forbidden:
            pass
        except discord.HTTPException:
            pass


class TitleSelect(discord.ui.Select):
    def __init__(self, member: discord.Member, user_data: dict):
        self.member = member
        titles = user_data.get("titles", [])

        options = []
        for idx, raw_title in enumerate(titles[:25], start=1):
            title = normalize_title_entry(raw_title)
            label = f"{idx}. {title['name']}"
            description = f"레벨 {title['level']} / 색상 {title['color']}"
            options.append(
                discord.SelectOption(
                    label=label[:100],
                    description=description[:100],
                    value=str(idx)
                )
            )

        super().__init__(
            placeholder="장착할 칭호를 선택하세요.",
            min_values=1,
            max_values=1,
            options=options
        )

    async def callback(self, interaction: discord.Interaction):
        if interaction.user.id != self.member.id:
            await interaction.response.send_message(
                "이 메뉴는 명령어를 실행한 사용자만 조작할 수 있어요.",
                ephemeral=True
            )
            return

        cog = self.view.cog
        title_index = int(self.values[0])
        await cog.equip_title_logic(interaction, title_index)


class TitleListView(discord.ui.View):
    def __init__(self, cog, member: discord.Member, user_data: dict):
        super().__init__(timeout=300)
        self.cog = cog

        if user_data.get("titles"):
            self.add_item(TitleSelect(member, user_data))


class Titles(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    def build_title_list_embed(self, member: discord.Member) -> discord.Embed:
        economy_data = load_economy()
        user_data = ensure_user(economy_data, str(member.id))

        embed = discord.Embed(
            title=f"🏷 {member.display_name}님의 칭호 목록",
            description="보유 중인 칭호를 확인하고 장착할 수 있어요.",
            color=discord.Color.purple()
        )

        embed.add_field(
            name="📜 보유 칭호",
            value=get_title_list_text(user_data)[:1024],
            inline=False
        )

        equipped_title = str(user_data.get("equipped_title", "")).strip()
        embed.add_field(
            name="✨ 현재 장착 중",
            value=equipped_title if equipped_title else "장착한 칭호가 없어요.",
            inline=False
        )

        embed.set_footer(text=f"{member.display_name}님의 칭호 정보")
        if member.display_avatar:
            embed.set_thumbnail(url=member.display_avatar.url)

        return embed

    async def equip_title_logic(self, interaction: discord.Interaction, 번호: int):
        if interaction.guild is None:
            await interaction.response.send_message(
                "칭호 장착은 서버에서만 사용할 수 있어요.",
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
        user_data = ensure_user(economy_data, str(member.id))

        titles_list, raw_title, title = find_title_by_index(user_data, 번호)
        if title is None:
            await interaction.response.send_message(
                "해당 번호의 칭호가 없어요.",
                ephemeral=True
            )
            return

        title_name = title["name"]

        if not user_data.get("base_nickname"):
            current_display = member.display_name
            current_equipped = str(user_data.get("equipped_title", "")).strip()

            if current_equipped and current_display.startswith(f"[{current_equipped}] "):
                current_display = current_display[len(f"[{current_equipped}] "):]

            user_data["base_nickname"] = current_display

        base_nickname = user_data.get("base_nickname", member.display_name).strip()
        final_nickname = f"[{title_name}] {base_nickname}"

        user_data["equipped_title"] = title_name

        role_result = await ensure_title_role(
            guild=interaction.guild,
            member=member,
            titles_list=titles_list,
            raw_title_entry=raw_title,
            normalized_title=title
        )

        save_economy(economy_data)

        nickname_changed = True
        try:
            await member.edit(nick=final_nickname)
        except discord.Forbidden:
            nickname_changed = False
        except discord.HTTPException:
            nickname_changed = False

        embed = discord.Embed(
            title="✅ 칭호 장착 완료",
            description=f"**{title_name}** 칭호를 장착했어요.",
            color=discord.Color.purple()
        )
        embed.add_field(
            name="🏷 장착 칭호",
            value=title_name,
            inline=False
        )
        embed.add_field(
            name="👤 적용 닉네임",
            value=final_nickname if nickname_changed else "닉네임 변경 권한이 없어 닉네임은 바꾸지 못했어요.",
            inline=False
        )

        role = role_result.get("role")
        embed.add_field(
            name="🎭 역할 상태",
            value=role.name if role else "연동된 역할이 없거나 복구하지 못했어요.",
            inline=False
        )
        embed.add_field(
            name="🛠 역할 동기화",
            value=role_result.get("status_text", "처리 결과를 확인할 수 없어요."),
            inline=False
        )

        await interaction.response.send_message(embed=embed, ephemeral=True)

    @app_commands.command(name="칭호목록", description="보유 중인 칭호 목록을 확인합니다.")
    async def title_list_command(self, interaction: discord.Interaction):
        if interaction.guild is None:
            await interaction.response.send_message(
                "칭호 목록은 서버에서만 사용할 수 있어요.",
                ephemeral=True
            )
            return

        economy_data = load_economy()
        user_data = ensure_user(economy_data, str(interaction.user.id))

        embed = self.build_title_list_embed(interaction.user)
        view = TitleListView(self, interaction.user, user_data)

        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)

    @app_commands.command(name="칭호장착", description="보유한 칭호를 장착합니다.")
    @app_commands.describe(번호="장착할 칭호 번호")
    async def title_equip_command(self, interaction: discord.Interaction, 번호: int):
        await self.equip_title_logic(interaction, 번호)

    @app_commands.command(name="칭호해제", description="현재 장착 중인 칭호를 해제합니다.")
    async def title_unequip_command(self, interaction: discord.Interaction):
        if interaction.guild is None:
            await interaction.response.send_message(
                "칭호 해제는 서버에서만 사용할 수 있어요.",
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
        user_data = ensure_user(economy_data, str(member.id))

        equipped_title = str(user_data.get("equipped_title", "")).strip()
        if not equipped_title:
            await interaction.response.send_message(
                "현재 장착 중인 칭호가 없어요.",
                ephemeral=True
            )
            return

        base_nickname = user_data.get("base_nickname", "").strip() or member.display_name

        user_data["equipped_title"] = ""
        save_economy(economy_data)

        nickname_changed = True
        try:
            await member.edit(nick=base_nickname)
        except discord.Forbidden:
            nickname_changed = False
        except discord.HTTPException:
            nickname_changed = False

        await remove_all_title_roles(interaction.guild, member, user_data)

        embed = discord.Embed(
            title="🗑 칭호 해제 완료",
            description=f"**{equipped_title}** 칭호를 해제했어요.",
            color=discord.Color.orange()
        )
        embed.add_field(
            name="👤 현재 닉네임",
            value=base_nickname if nickname_changed else "닉네임 변경 권한이 없어 닉네임은 바꾸지 못했어요.",
            inline=False
        )
        embed.add_field(
            name="🎭 역할 상태",
            value="연동된 칭호 역할도 함께 해제했어요.",
            inline=False
        )

        await interaction.response.send_message(embed=embed, ephemeral=True)


async def setup(bot):
    await bot.add_cog(Titles(bot))