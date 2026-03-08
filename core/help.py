import discord
from discord import app_commands
from discord.ext import commands


HELP_CATEGORIES = {
    "메인": {
        "emoji": "📘",
        "description": (
            "디모(Dimo) 도움말이에요.\n\n"
            "아래 선택 메뉴에서 원하는 카테고리를 골라 확인할 수 있어요.\n"
            "디모는 경제, 도박, 상점, 칭호, 관리 기능을 제공하는 봇이에요."
        ),
        "fields": [
            ("📌 주요 기능", "경제 시스템 / 도박 / 슬롯 / 상점 / 칭호 / 관리 기능", False),
            ("🧭 이용 방법", "아래 메뉴를 눌러 각 카테고리 명령어를 확인하세요.", False),
        ],
        "color": discord.Color.blurple()
    },
    "경제": {
        "emoji": "💰",
        "description": "재화 획득, 송금, 지갑, 랭킹 관련 명령어예요.",
        "fields": [
            ("/출석", "24시간마다 1회 출석하고 재화를 받아요.", False),
            ("/일하기", "30분마다 일을 해서 재화를 벌어요.", False),
            ("/지갑 [대상]", "내 지갑 또는 다른 유저의 지갑 정보를 확인해요.", False),
            ("/송금 [대상] [금액]", "다른 유저에게 재화를 송금해요. 송금 시 세금이 적용돼요.", False),
            ("/재화랭킹", "서버 내 재화 보유 랭킹을 확인해요.", False),
            ("/부동산", "구매 가능한 부동산 목록을 확인합니다.", False),
            ("/부동산구매", "부동산을 구매합니다.", False),
            ("/부동산목록", "보유 중인 부동산을 확인합니다.", False),
            ("/임대료", "부동산에서 발생한 임대료를 수령합니다.", False),
        ],
        "color": discord.Color.gold()
    },
    "도박": {
        "emoji": "🎲",
        "description": "도박, 올인, 하드모드 슬롯 관련 명령어예요.",
        "fields": [
            ("/도박 [금액]", "재화를 걸고 승패를 겨뤄요. 행운권 효과가 적용될 수 있어요.", False),
            ("/올인", "현재 보유한 재화로 한 번에 도박해요. 최대 배팅 제한이 적용돼요.", False),
            ("/슬롯 [금액]", "하드모드 슬롯을 돌려요. 5개 전부 같으면 100배를 받아요.", False),
            ("/도박랭킹", "도박 승수를 기준으로 서버 랭킹을 확인해요.", False),
        ],
        "color": discord.Color.red()
    },
    "상점": {
        "emoji": "🛒",
        "description": "아이템 구매와 사용, 인벤토리 확인 관련 명령어예요.",
        "fields": [
            ("/상점", "구매 가능한 아이템 목록을 확인해요.", False),
            ("/구매 [아이템] [수량]", "상점에서 아이템을 구매해요.", False),
            ("/사용 [아이템]", "보유 중인 아이템을 사용해요.", False),
            ("/인벤토리 [대상]", "내 인벤토리 또는 다른 유저의 인벤토리를 확인해요.", False),
        ],
        "color": discord.Color.green()
    },
    "칭호": {
        "emoji": "🏷",
        "description": "칭호 생성, 장착, 강화, 시즌 랭킹 관련 명령어예요.",
        "fields": [
            ("/내정보 [대상]", "내 프로필 정보와 장착한 칭호, 전적을 확인해요.", False),
            ("/칭호목록", "내가 보유 중인 칭호 목록을 확인해요.", False),
            ("/칭호장착 [번호]", "보유 중인 칭호를 장착해요. 장착한 칭호는 /내정보에 표시돼요.", False),
            ("/칭호강화 [번호]", "보유 중인 칭호를 강화해요. 강화에는 재화가 들어가요.", False),
            ("/칭호자랑 [번호]", "보유 중인 칭호를 채널에 자랑해요.", False),
            ("/칭호강화랭킹", "이번 달 칭호 강화 랭킹을 확인해요.", False),
        ],
        "color": discord.Color.purple()
    },
    "관리": {
        "emoji": "🛠",
        "description": "관리자 전용 재화 관리 명령어예요.",
        "fields": [
            ("/재화지급 [대상] [금액]", "유저에게 재화를 지급해요. 관리자 전용이에요.", False),
            ("/재화차감 [대상] [금액]", "유저의 재화를 차감해요. 관리자 전용이에요.", False),
            ("/재화설정 [대상] [금액]", "유저의 재화를 원하는 값으로 설정해요. 관리자 전용이에요.", False),
            ("/재화로그", "최근 관리자 재화 로그를 확인해요. 관리자 전용이에요.", False),
        ],
        "color": discord.Color.orange()
    },
    "기타": {
        "emoji": "✨",
        "description": "기타 편의 명령어와 시스템 설명이에요.",
        "fields": [
            ("출석보너스권", "출석 시 자동으로 사용되어 추가 보상을 지급해요.", False),
            ("행운권", "다음 도박/슬롯 1회에 행운 효과가 적용돼요.", False),
            ("칭호생성권", "새 칭호를 생성할 수 있는 아이템이에요.", False),
            ("닉네임변경권", "서버 닉네임을 변경할 수 있는 아이템이에요.", False),
        ],
        "color": discord.Color.teal()
    }
}


def is_admin(member: discord.Member) -> bool:
    return member.guild_permissions.administrator


def get_visible_categories(member: discord.Member) -> list[str]:
    base_categories = ["메인", "경제", "도박", "상점", "칭호", "기타"]

    if is_admin(member):
        base_categories.append("관리")

    return base_categories


def build_help_embed(category_name: str, user: discord.abc.User) -> discord.Embed:
    category = HELP_CATEGORIES[category_name]

    embed = discord.Embed(
        title=f"{category['emoji']} 디모 도움말 - {category_name}",
        description=category["description"],
        color=category["color"]
    )

    for name, value, inline in category["fields"]:
        embed.add_field(name=name, value=value, inline=inline)

    embed.set_footer(text=f"{user.display_name}님을 위한 도움말")
    if user.display_avatar:
        embed.set_thumbnail(url=user.display_avatar.url)

    return embed


class HelpCategorySelect(discord.ui.Select):
    def __init__(self, member: discord.Member):
        self.member = member
        visible_categories = get_visible_categories(member)

        options = [
            discord.SelectOption(
                label=name,
                emoji=HELP_CATEGORIES[name]["emoji"],
                description=HELP_CATEGORIES[name]["description"][:100]
            )
            for name in visible_categories
        ]

        super().__init__(
            placeholder="도움말 카테고리를 선택하세요.",
            min_values=1,
            max_values=1,
            options=options
        )

    async def callback(self, interaction: discord.Interaction):
        if interaction.user.id != self.member.id:
            await interaction.response.send_message(
                "이 도움말 메뉴는 명령어를 실행한 사용자만 조작할 수 있어요.",
                ephemeral=True
            )
            return

        category_name = self.values[0]

        if category_name == "관리" and not is_admin(interaction.user):
            await interaction.response.send_message(
                "관리 카테고리는 관리자만 볼 수 있어요.",
                ephemeral=True
            )
            return

        embed = build_help_embed(category_name, interaction.user)
        await interaction.response.edit_message(embed=embed, view=self.view)


class HelpView(discord.ui.View):
    def __init__(self, member: discord.Member):
        super().__init__(timeout=300)
        self.add_item(HelpCategorySelect(member))


class Help(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="도움말", description="디모의 명령어 도움말을 확인합니다.")
    async def help_command(self, interaction: discord.Interaction):
        if interaction.guild is None:
            await interaction.response.send_message(
                "도움말은 서버에서만 사용할 수 있어요.",
                ephemeral=True
            )
            return

        member = interaction.user
        embed = build_help_embed("메인", member)
        view = HelpView(member)
        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)


async def setup(bot):
    await bot.add_cog(Help(bot))