import discord
from discord.ext import commands
import os
import logging
from dotenv import load_dotenv

from state import game
from ui import AdminView, ParticipantView

load_dotenv()
TOKEN = os.getenv('DISCORD_BOT_TOKEN')
APP_ENV = os.getenv('APP_ENV', 'production')
LOG_LEVEL = os.getenv('LOG_LEVEL', 'INFO')

logging.basicConfig(level=getattr(logging, LOG_LEVEL.upper(), logging.INFO))
logger = logging.getLogger(__name__)

intents = discord.Intents.default()

bot = commands.Bot(command_prefix='!', intents=intents)

@bot.event
async def on_ready():
    logger.info(f'Logged in as {bot.user} (ID: {bot.user.id})')
    logger.info('------')
    try:
        synced = await bot.tree.sync()
        logger.info(f"Synced {len(synced)} command(s)")
    except Exception as e:
        logger.error(f"Failed to sync commands: {e}")

from typing import Union

@bot.tree.command(name="setup", description="ビンゴ大会のチャンネル設定と管理者パネルを設置します。")
async def setup(
    interaction: discord.Interaction, 
    admin_channel: discord.TextChannel, 
    participant_channel: discord.TextChannel, 
    stage_channel: Union[discord.TextChannel, discord.StageChannel, discord.VoiceChannel]
):
    try:
        # 管理者権限のチェック（厳密な検証）
        if not interaction.user.guild_permissions.administrator:
            logger.warning(f"Unauthorized setup attempt by {interaction.user.id}")
            await interaction.response.send_message("このコマンドは管理者のみ実行できます。", ephemeral=True)
            return

        game.admin_channel_id = admin_channel.id
        game.participant_channel_id = participant_channel.id
        game.stage_channel_id = stage_channel.id
        
        # 既存のキーワードファイルがあれば読み込む
        keywords_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "keywords.txt")
        try:
            with open(keywords_path, "r", encoding="utf-8") as f:
                keywords = [line.strip() for line in f if line.strip()]
                game.load_keywords(keywords)
                kw_msg = f"キーワードリストから {len(keywords)} 個の単語を読み込みました。"
        except FileNotFoundError:
            logger.warning("keywords.txt not found during setup.")
            kw_msg = "⚠️ `keywords.txt` が見つかりません。BOTの同じディレクトリに作成してください。"

        # 管理者チャンネルにパネルを設置
        embed = discord.Embed(title="ビンゴ管理パネル", description="大会の進行を管理します。", color=discord.Color.blue())
        embed.add_field(name="参加者チャンネル", value=participant_channel.mention, inline=False)
        embed.add_field(name="発表チャンネル", value=stage_channel.mention, inline=False)
        embed.add_field(name="キーワード", value=kw_msg, inline=False)
        
        view = AdminView(bot)
        await admin_channel.send(embed=embed, view=view)
        
        await interaction.response.send_message("セットアップが完了しました。管理者チャンネルをご確認ください。", ephemeral=True)

    except Exception as e:
        logger.exception("Setup command failed")
        msg = f"システムエラーが発生しました: {e}" if APP_ENV == 'development' else "システムエラーが発生しました。管理者にお問い合わせください。"
        if not interaction.response.is_done():
            await interaction.response.send_message(msg, ephemeral=True)
        else:
            await interaction.followup.send(msg, ephemeral=True)


if __name__ == '__main__':
    if not TOKEN:
        logger.error("Error: DISCORD_BOT_TOKEN is not set in .env file.")
    else:
        bot.run(TOKEN)
