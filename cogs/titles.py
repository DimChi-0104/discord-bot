import discord
from discord import app_commands
from discord.ext import commands
import json
import os
from datetime import datetime, timedelta, timezone

DATA_FILE = "data/economy.json"
KST = timezone(timedelta(hours=9))

MAX_TITLE_LEVEL = 10
RANKING_TOP_LIMIT = 10


def load_data():
    os.makedirs("data", exist_ok=True)

    if not os.path.exists(DATA_FILE):
        with open(DATA_FILE, "w", encoding="utf-8") as f:
            json.dump({"users": {}, "title_ranking": {"season": "", "users": {}}}, f, ensure_ascii=False, indent=4)
        return {"users": {}, "title_ranking": {"season": "", "users": {}}}

    try:
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)

        if not isinstance(data, dict):
            data = {"users": {}, "title_ranking": {"season": "", "users": {}}}

        if "users" not in data or not isinstance(data["users"], dict):
            data["users"] = {}

        if "title_ranking" not in data or not isinstance(data["title_ranking"], dict):
            data["title_ranking"] = {"season": "", "users": {}}

        data["title_ranking"].setdefault("season", "")
        if not isinstance(data["title_ranking"]["season"], str):
            data["title_ranking"]["season"] = ""

        data["title_ranking"].setdefault("users", {})
        if not isinstance(data["title_ranking"]["users"], dict):
            data["title_ranking"]["users"] = {}

        return data

    except (json.JSONDecodeError, OSError):
        fallback = {"users": {}, "title_ranking": {"season": "", "users": {}}}
        with open(DATA_FILE, "w", encoding="utf-8") as f:
            json.dump(fallback, f, ensure_ascii=False, indent=4)
        return fallback


def save_data(data):
    os.makedirs("data", exist_ok=True)

    if not isinstance(data, dict):
        data = {"users": {}, "title_ranking": {"season": "", "users": {}}}

    if "users" not in data or not isinstance(data["users"], dict):
        data["users"] = {}

    if "title_ranking" not in data or not isinstance(data["title_ranking"], dict):
        data["title_ranking"] = {"season": "", "users": {}}

    data["title_ranking"].setdefault("season", "")
    if not isinstance(data["title_ranking"]["season"], str):
        data["title_ranking"]["season"] = ""

    data["title_ranking"].setdefault("users", {})
    if not isinstance(data["title_ranking"]["users"], dict):
        data["title_ranking"]["users"] = {}

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


def get_current_season() -> str:
    return datetime.now(KST).strftime("%Y-%m")


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

    return user


def get_upgrade_cost(level: int) -> int:
    return 5000 * (2 ** max(0, level - 1))


def find_title_by_id(titles: list, title_id: int):
    for title in titles:
        if isinstance(title, dict) and title.get("id") == title_id:
            return title
    return None


def get_equipped_title(user: dict):
    titles = user.get("titles", [])
    if not isinstance(titles, list):
        return None

    for title in titles:
        if isinstance(title, dict) and title.get("equipped", False):
            return title
    return None


def update_title_ranking_record(data: dict, user_id: int, title_name: str, level: int):
    ranking = data.setdefault("title_ranking", {})
    ranking.setdefault("season", get_current_season())
    ranking.setdefault("users", {})

    user_key = str(user_id)
    current_record = ranking["users"].get(user_key)

    if not isinstance(current_record, dict):
        ranking["users"][user_key] = {
            "best_level": level,
            "title_name": title_name
        }
        return

    current_best = current_record.get("best_level", 0)
    if not isinstance(current_best, int):
        current_best = 0

    if level > current_best:
        ranking["users"][user_key] = {
            "best_level": level,
            "title_name": title_name
        }


async def process_monthly_title_reset(bot: commands.Bot, guild: discord.Guild, data: dict):
    current_season = get_current_season()
    ranking = data.setdefault("title_ranking", {"season": "", "users": {}})
    ranking.setdefault("season", "")
    ranking.setdefault("users", {})

    previous_season = ranking["season"]

    if previous_season == "":
        ranking["season"] = current_season
        ranking["users"] = {}
        save_data(data)
        return

    if previous_season == current_season:
        return

    season_users = ranking.get("users", {})
    winner_user_id = None
    winner_best_level = -1
    winner_title_name = ""

    for user_id, record in season_users.items():
        if not isinstance(record, dict):
            continue

        best_level = record.get("best_level", 0)
        title_name = str(record.get("title_name", "")).strip()

        if not isinstance(best_level, int):
            best_level = 0

        if best_level > winner_best_level and title_name:
            winner_best_level = best_level
            winner_user_id = user_id
            winner_title_name = title_name

    if winner_user_id is not None and winner_title_name:
        winner_member = guild.get_member(int(winner_user_id))
        if winner_member is not None and not winner_member.bot:
            role_name = f"🏆 {previous_season} {winner_title_name}"
            role = discord.utils.get(guild.roles, name=role_name)

            if role is None:
                try:
                    role = await guild.create_role(
                        name=role_name,
                        reason=f"{previous_season} 칭호 시즌 1위 보상 역할"
                    )
                except discord.Forbidden:
                    role = None
                except discord.HTTPException:
                    role = None

            if role is not None:
                try:
                    await winner_member.add_roles(role, reason=f"{previous_season} 칭호 시즌 1위 보상")
                except discord.Forbidden:
                    pass
                except discord.HTTPException:
                    pass

    for _, user in data.get("users", {}).items():
        if not isinstance(user, dict):
            continue

        titles = user.get("titles", [])
        if not isinstance(titles, list):
            user["titles"] = []
            continue

        filtered_titles = []
        equipped_found = False

        for title in titles:
            if not isinstance(title, dict):
                continue

            level = title.get("level", 1)
            if not isinstance(level, int) or level < 1:
                level = 1
                title["level"] = 1

            if level >= 2:
                continue

            if title.get("equipped", False) and not equipped_found:
                equipped_found = True
                filtered_titles.append(title)
            else:
                title["equipped"] = False
                filtered_titles.append(title)

        if filtered_titles:
            if not any(isinstance(t, dict) and t.get("equipped", False) for t in filtered_titles):
                filtered_titles[0]["equipped"] = True
        user["titles"] = filtered_titles

    ranking["season"] = current_season
    ranking["users"] = {}
    save_data(data)


class Titles(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    async def ensure_season(self, guild: discord.Guild):
        data = load_data()
        await process_monthly_title_reset(self.bot, guild, data)

    @app_commands.command(name="칭호목록", description="보유 중인 칭호 목록을 확인합니다.")
    async def title_list(self, interaction: discord.Interaction):
        if interaction.guild is None:
            await interaction.response.send_message("이 명령어는 서버에서만 사용할 수 있어요.", ephemeral=True)
            return

        if interaction.user.bot:
            await interaction.response.send_message("봇 계정은 사용할 수 없어요.", ephemeral=True)
            return

        await self.ensure_season(interaction.guild)

        data = load_data()
        user = get_user_data(data, interaction.user.id)
        save_data(data)

        titles = user.get("titles", [])

        if not titles:
            await interaction.response.send_message(
                "보유 중인 칭호가 없어요.\n`/상점`에서 `칭호생성권`을 구매해보세요.",
                ephemeral=True
            )
            return

        lines = []
        for title in titles:
            if not isinstance(title, dict):
                continue

            title_id = title.get("id", 0)
            name = title.get("name", "이름없음")
            color = title.get("color", "#FFFFFF")
            level = title.get("level", 1)
            if not isinstance(level, int) or level < 1:
                level = 1

            equipped = " [장착중]" if title.get("equipped", False) else ""
            lines.append(f"`{title_id}번` • `{name} +{level}` • `{color}`{equipped}")

        embed = discord.Embed(
            title="🏷 내 칭호 목록",
            description="\n".join(lines),
            color=discord.Color.gold()
        )
        embed.set_footer(text="/칭호장착 [번호], /칭호강화 [번호], /칭호자랑 [번호]")
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="칭호장착", description="보유 중인 칭호를 장착합니다.")
    async def equip_title(self, interaction: discord.Interaction, 번호: int):
        if interaction.guild is None:
            await interaction.response.send_message("이 명령어는 서버에서만 사용할 수 있어요.", ephemeral=True)
            return

        if interaction.user.bot:
            await interaction.response.send_message("봇 계정은 사용할 수 없어요.", ephemeral=True)
            return

        if 번호 <= 0:
            await interaction.response.send_message("올바른 칭호 번호를 입력해주세요.", ephemeral=True)
            return

        await self.ensure_season(interaction.guild)

        data = load_data()
        user = get_user_data(data, interaction.user.id)
        titles = user.get("titles", [])

        target = find_title_by_id(titles, 번호)
        if target is None:
            await interaction.response.send_message("해당 번호의 칭호를 찾을 수 없어요.", ephemeral=True)
            return

        for title in titles:
            if isinstance(title, dict):
                title["equipped"] = False

        target["equipped"] = True
        save_data(data)

        embed = discord.Embed(
            title="✅ 칭호 장착 완료",
            description=(
                f"장착한 칭호: `{target.get('name', '이름없음')} +{target.get('level', 1)}`\n"
                f"색상: `{target.get('color', '#FFFFFF')}`\n\n"
                f"이제 `/내정보`에서 표시돼요."
            ),
            color=parse_embed_color(target.get("color", "#FFFFFF"))
        )
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="칭호강화", description="보유 중인 칭호를 강화합니다.")
    async def upgrade_title(self, interaction: discord.Interaction, 번호: int):
        if interaction.guild is None:
            await interaction.response.send_message("이 명령어는 서버에서만 사용할 수 있어요.", ephemeral=True)
            return

        if interaction.user.bot:
            await interaction.response.send_message("봇 계정은 사용할 수 없어요.", ephemeral=True)
            return

        if 번호 <= 0:
            await interaction.response.send_message("올바른 칭호 번호를 입력해주세요.", ephemeral=True)
            return

        await self.ensure_season(interaction.guild)

        data = load_data()
        user = get_user_data(data, interaction.user.id)
        titles = user.get("titles", [])

        target = find_title_by_id(titles, 번호)
        if target is None:
            await interaction.response.send_message("해당 번호의 칭호를 찾을 수 없어요.", ephemeral=True)
            return

        current_level = target.get("level", 1)
        if not isinstance(current_level, int) or current_level < 1:
            current_level = 1
            target["level"] = 1

        if current_level >= MAX_TITLE_LEVEL:
            await interaction.response.send_message(
                f"이 칭호는 이미 최대 강화 단계(`+{MAX_TITLE_LEVEL}`)예요.",
                ephemeral=True
            )
            return

        cost = get_upgrade_cost(current_level)

        if user["money"] < cost:
            await interaction.response.send_message(
                f"재화가 부족해요.\n필요 재화: `{cost:,} 코인`\n현재 재화: `{user['money']:,} 코인`",
                ephemeral=True
            )
            return

        user["money"] -= cost
        if user["money"] < 0:
            user["money"] = 0

        target["level"] = current_level + 1

        current_season = get_current_season()
        data["title_ranking"]["season"] = current_season
        update_title_ranking_record(
            data=data,
            user_id=interaction.user.id,
            title_name=str(target.get("name", "이름없음")),
            level=target["level"]
        )

        save_data(data)

        embed = discord.Embed(
            title="✨ 칭호 강화 성공",
            description=(
                f"강화한 칭호: `{target.get('name', '이름없음')}`\n"
                f"현재 단계: `+{target['level']}`\n"
                f"사용 재화: `{cost:,} 코인`\n"
                f"남은 재화: `{user['money']:,} 코인`\n"
                f"시즌 기록 반영: `{current_season}`"
            ),
            color=parse_embed_color(target.get("color", "#FFFFFF"))
        )
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="칭호자랑", description="보유 중인 칭호를 자랑합니다.")
    async def show_title(self, interaction: discord.Interaction, 번호: int):
        if interaction.guild is None:
            await interaction.response.send_message("이 명령어는 서버에서만 사용할 수 있어요.", ephemeral=True)
            return

        if interaction.user.bot:
            await interaction.response.send_message("봇 계정은 사용할 수 없어요.", ephemeral=True)
            return

        if 번호 <= 0:
            await interaction.response.send_message("올바른 칭호 번호를 입력해주세요.", ephemeral=True)
            return

        await self.ensure_season(interaction.guild)

        data = load_data()
        user = get_user_data(data, interaction.user.id)
        titles = user.get("titles", [])

        target = find_title_by_id(titles, 번호)
        if target is None:
            await interaction.response.send_message("해당 번호의 칭호를 찾을 수 없어요.", ephemeral=True)
            return

        name = target.get("name", "이름없음")
        color = target.get("color", "#FFFFFF")
        level = target.get("level", 1)
        if not isinstance(level, int) or level < 1:
            level = 1

        equipped_text = "장착 중" if target.get("equipped", False) else "미장착"

        embed = discord.Embed(
            title="🏷 칭호 자랑",
            description=(
                f"소유자: {interaction.user.mention}\n"
                f"칭호 이름: `{name}`\n"
                f"강화 단계: `+{level}`\n"
                f"색상: `{color}`\n"
                f"상태: `{equipped_text}`"
            ),
            color=parse_embed_color(color)
        )
        embed.set_footer(text=f"칭호 번호: {번호}")
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="칭호강화랭킹", description="이번 달 칭호 강화 랭킹을 확인합니다.")
    async def title_ranking(self, interaction: discord.Interaction):
        if interaction.guild is None:
            await interaction.response.send_message("이 명령어는 서버에서만 사용할 수 있어요.", ephemeral=True)
            return

        if interaction.user.bot:
            await interaction.response.send_message("봇 계정은 사용할 수 없어요.", ephemeral=True)
            return

        await self.ensure_season(interaction.guild)

        data = load_data()
        ranking = data.get("title_ranking", {})
        season = ranking.get("season", get_current_season())
        ranking_users = ranking.get("users", {})

        entries = []
        for user_id, record in ranking_users.items():
            if not isinstance(record, dict):
                continue

            try:
                member = interaction.guild.get_member(int(user_id))
            except ValueError:
                continue

            if member is None or member.bot:
                continue

            best_level = record.get("best_level", 0)
            title_name = str(record.get("title_name", "")).strip()

            if not isinstance(best_level, int):
                best_level = 0

            if best_level <= 0 or not title_name:
                continue

            entries.append((member, best_level, title_name))

        entries.sort(key=lambda x: x[1], reverse=True)
        top_entries = entries[:RANKING_TOP_LIMIT]

        if not top_entries:
            await interaction.response.send_message(
                "이번 달에는 아직 칭호 강화 기록이 없어요.",
                ephemeral=True
            )
            return

        medals = ["🥇", "🥈", "🥉"]
        lines = []

        for idx, (member, best_level, title_name) in enumerate(top_entries, start=1):
            prefix = medals[idx - 1] if idx <= 3 else f"{idx}위"
            lines.append(f"{prefix} {member.display_name} - `{title_name} +{best_level}`")

        embed = discord.Embed(
            title="🏆 월간 칭호 강화 랭킹",
            description="\n".join(lines),
            color=discord.Color.gold()
        )
        embed.set_footer(text=f"현재 시즌: {season} | 월이 바뀌면 랭킹이 초기화돼요.")
        await interaction.response.send_message(embed=embed)


async def setup(bot):
    await bot.add_cog(Titles(bot))