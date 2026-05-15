import discord
from discord.ui import View, Button
import logging
import asyncio
import os
import random

from state import game
from image_gen import generate_card_image

APP_ENV = os.getenv('APP_ENV', 'production')
logger = logging.getLogger(__name__)

class KeywordSelectView(View):
    def __init__(self, user_id: int):
        super().__init__(timeout=300)
        self.user_id = user_id
        
        # 最大25個まで取得（システム制限）
        available_pool = [k for k in game.keywords_pool if k.upper() != "FREE"]
        disp_count = min(25, len(available_pool))
        options_pool = random.sample(available_pool, disp_count)
        
        options = [
            discord.SelectOption(label=kw, value=kw) for kw in options_pool
        ]
        
        self.select = discord.ui.Select(
            placeholder="好きなキーワードを4つ選んでください！",
            min_values=4,
            max_values=4,
            options=options
        )
        self.select.callback = self.select_callback
        self.add_item(self.select)

    async def select_callback(self, interaction: discord.Interaction):
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("他の人の操作はできません。", ephemeral=True)
            return

        selected_keywords = self.select.values
        
        await interaction.response.defer(ephemeral=True)
        try:
            participant = game.add_participant(interaction.user.id, selected_keywords)
            img_buf = await asyncio.to_thread(generate_card_image, participant.user_id, participant.card_keywords, participant.marked)
            file = discord.File(fp=img_buf, filename="bingo_card.png")
            
            dm_channel = await interaction.user.create_dm()
            await dm_channel.send("あなたのビンゴカードです！抽選をお待ちください。", file=file)
            
            # 元の選択メッセージを消す・更新する
            await interaction.edit_original_response(content="カードを発行し、DMに送信しました！", view=None)
        except Exception as e:
            logger.exception("Failed to issue bingo card")
            msg = f"エラーが発生しました: {e}" if APP_ENV == 'development' else "システムエラーが発生しました。"
            await interaction.followup.send(msg, ephemeral=True)
            if interaction.user.id in game.participants:
                del game.participants[interaction.user.id]

class ReportReachView(View):
    def __init__(self, bot, user_id):
        super().__init__(timeout=None)
        self.bot = bot
        self.user_id = user_id

    @discord.ui.button(label="リーチを申告する！", style=discord.ButtonStyle.primary, custom_id="report_reach")
    async def report_button(self, interaction: discord.Interaction, button: Button):
        if interaction.user.id != self.user_id:
            return
            
        stage_channel = self.bot.get_channel(game.stage_channel_id)
        if stage_channel:
            await stage_channel.send(f"{interaction.user.mention} が **リーチ** になりました！")
            
        button.disabled = True
        button.label = "申告済み"
        await interaction.response.edit_message(view=self)

class ReportBingoView(View):
    def __init__(self, bot, user_id):
        super().__init__(timeout=None)
        self.bot = bot
        self.user_id = user_id

    @discord.ui.button(label="ビンゴを申告する！！", style=discord.ButtonStyle.success, custom_id="report_bingo")
    async def report_button(self, interaction: discord.Interaction, button: Button):
        if interaction.user.id != self.user_id:
            return
            
        stage_channel = self.bot.get_channel(game.stage_channel_id)
        if stage_channel and self.user_id in game.participants:
            p = game.participants[self.user_id]
            img_buf = await asyncio.to_thread(generate_card_image, p.user_id, p.card_keywords, p.marked)
            file = discord.File(fp=img_buf, filename="bingo_win.png")
            msg = f"🎉 **BINGO!!** {interaction.user.mention} がビンゴになりました！ 🎉"
            await stage_channel.send(content=msg, file=file)
            
        button.disabled = True
        button.label = "申告済み"
        await interaction.response.edit_message(view=self)


class ParticipantView(View):
    def __init__(self):
        super().__init__(timeout=None)
        
    @discord.ui.button(label="ビンゴカード発行", style=discord.ButtonStyle.success, custom_id="issue_bingo_card")
    async def issue_card(self, interaction: discord.Interaction, button: Button):
        if not game.is_active:
            await interaction.response.send_message("現在ビンゴ大会は開催されていません。", ephemeral=True)
            return
            
        if interaction.user.id in game.participants:
            await interaction.response.send_message("すでにカードを発行済みです。", ephemeral=True)
            return
            
        view = KeywordSelectView(interaction.user.id)
        await interaction.response.send_message("配置したいキーワードを4つ選んでください！", view=view, ephemeral=True)

class AdminView(View):
    def __init__(self, bot):
        super().__init__(timeout=None)
        self.bot = bot

    @discord.ui.button(label="開始", style=discord.ButtonStyle.primary, custom_id="admin_start")
    async def start_button(self, interaction: discord.Interaction, button: Button):
        if not interaction.user.guild_permissions.administrator:
            logger.warning(f"Unauthorized start_button access by User ID {interaction.user.id}")
            await interaction.response.send_message("管理者のみ実行可能です。", ephemeral=True)
            return

        if game.is_active:
            await interaction.response.send_message("既に開始しています。", ephemeral=True)
            return
            
        try:
            keywords_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "keywords.txt")
            with open(keywords_path, "r", encoding="utf-8") as f:
                keywords = [line.strip() for line in f if line.strip()]
                game.load_keywords(keywords)
                
            game.start_game()
            
            channel = self.bot.get_channel(game.participant_channel_id)
            if channel:
                embed = discord.Embed(title="ビンゴ大会 開催中！", description="下のボタンを押してビンゴカードを発行してください。", color=discord.Color.green())
                await channel.send(embed=embed, view=ParticipantView())
                await interaction.response.send_message("参加受付を開始しました。", ephemeral=True)
            else:
                await interaction.response.send_message("エラー: 参加者チャンネルが見つかりません。", ephemeral=True)
                
        except Exception as e:
            logger.exception("admin_start failed")
            msg = f"開始に失敗しました: {e}" if APP_ENV == 'development' else "開始中にシステムエラーが発生しました。"
            await interaction.response.send_message(msg, ephemeral=True)

    @discord.ui.button(label="抽選", style=discord.ButtonStyle.danger, custom_id="admin_draw")
    async def draw_button(self, interaction: discord.Interaction, button: Button):
        if not interaction.user.guild_permissions.administrator:
            logger.warning(f"Unauthorized draw_button access by User ID {interaction.user.id}")
            await interaction.response.send_message("管理者のみ実行可能です。", ephemeral=True)
            return

        if not game.is_active:
            await interaction.response.send_message("ビンゴ大会が開始されていません。", ephemeral=True)
            return
            
        try:
            await interaction.response.defer(ephemeral=True)
            
            drawn_word = game.draw_keyword()
            
            stage_channel = self.bot.get_channel(game.stage_channel_id)
            if stage_channel:
                await stage_channel.send(f"# {drawn_word}")
            
            matched, reached, bingos = game.evaluate_draw(drawn_word)
            
            for p in matched:
                try:
                    # N+1最適化: キャッシュから取得を優先
                    user = self.bot.get_user(p.user_id) or await self.bot.fetch_user(p.user_id)
                    # 画像生成を別スレッドで実行しイベントループブロックを防ぐ
                    img_buf = await asyncio.to_thread(generate_card_image, p.user_id, p.card_keywords, p.marked)
                    file = discord.File(fp=img_buf, filename="bingo_card_marked.png")
                    
                    view = None
                    msg = f"あなたのカードに「{drawn_word}」がありました！"
                    
                    if p.has_bingo and not p.notified_bingo:
                        view = ReportBingoView(self.bot, p.user_id)
                        msg += "\n🎉 **ビンゴ達成です！** 下のボタンで申告してください。"
                        p.notified_bingo = True
                    elif p.has_reach and not p.notified_reach:
                        view = ReportReachView(self.bot, p.user_id)
                        msg += "\n🔥 **リーチです！** 下のボタンで申告してください。"
                        p.notified_reach = True
                        
                    if view:
                        await user.send(msg, file=file, view=view)
                    else:
                        await user.send(msg, file=file)
                        
                except Exception as e:
                    logger.error(f"Failed to send DM to User ID {p.user_id}: {e}")
            
            await interaction.followup.send(f"「{drawn_word}」を抽選しました。（ヒット: {len(matched)}人, 新リーチ: {len(reached)}人, 新ビンゴ: {len(bingos)}人）", ephemeral=True)
            
        except Exception as e:
            logger.exception("admin_draw failed")
            msg = f"抽選エラー: {e}" if APP_ENV == 'development' else "抽選中にシステムエラーが発生しました。"
            if not interaction.response.is_done():
                await interaction.response.send_message(msg, ephemeral=True)
            else:
                await interaction.followup.send(msg, ephemeral=True)
                
    @discord.ui.button(label="全てリセット", style=discord.ButtonStyle.danger, custom_id="admin_reset")
    async def reset_button(self, interaction: discord.Interaction, button: Button):
        if not interaction.user.guild_permissions.administrator:
            logger.warning(f"Unauthorized reset_button access by User ID {interaction.user.id}")
            await interaction.response.send_message("管理者のみ実行可能です。", ephemeral=True)
            return

        if not game.is_active:
            await interaction.response.send_message("大会が開始されていません。", ephemeral=True)
            return
            
        game.reset_draws()
        await interaction.response.send_message("これまで引いたキーワード履歴と参加者のカード状態をリセットしました。", ephemeral=True)

    @discord.ui.button(label="終了", style=discord.ButtonStyle.secondary, custom_id="admin_end")
    async def end_button(self, interaction: discord.Interaction, button: Button):
        if not interaction.user.guild_permissions.administrator:
            logger.warning(f"Unauthorized end_button access by User ID {interaction.user.id}")
            await interaction.response.send_message("管理者のみ実行可能です。", ephemeral=True)
            return

        if not game.is_active:
            await interaction.response.send_message("ビンゴ大会はすでに終了しています。", ephemeral=True)
            return
            
        game.end_game()
        await interaction.response.send_message("ビンゴ大会を終了し、データを完全に削除しました。", ephemeral=True)
