import os

async def load_cogs(bot):

    for folder in ["cogs", "core"]:

        for file in os.listdir(folder):

            if file.endswith(".py") and file != "__init__.py":

                name = file[:-3]

                try:

                    await bot.load_extension(f"{folder}.{name}")
                    print(f"로드 완료: {folder}.{name}")

                except Exception as e:

                    print(f"로드 실패: {name}")
                    print(e)