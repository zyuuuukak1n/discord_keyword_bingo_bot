# Discord Keyword Bingo Bot

Discordのステージチャンネルで利用可能な「キーワード式ビンゴ大会」ボットです。

## セットアップ

1. Python 3.10以上をインストール
2. 依存パッケージをインストールします：
   ```bash
   pip install -r requirements.txt
   ```
3. フォントのダウンロードスクリプトを実行し、日本語フォントを準備します。
   ```bash
   python download_font.py
   ```
4. `.env` ファイルを作成し、DiscordのBot Tokenを設定します。
   ```env
   DISCORD_BOT_TOKEN=your_token_here
   ```
5. 起動します。
   ```bash
   python bot.py
   ```

## 使用方法（Discord内）

1. 管理者権限を持つユーザーが、運用用のチャンネルで `/setup` コマンドを実行します。
   - `admin_channel`: 管理者用パネル（開始・抽選・終了）を設置するチャンネル
   - `participant_channel`: 参加者用パネル（カード発行）を設置するチャンネル
   - `stage_channel`: 抽選結果やビンゴ達成者のアナウンスを行うチャンネル
2. **[開始]** ボタンを押すと参加受付が始まり、`participant_channel` にカード発行ボタンが出現します。
3. 参加者が **[ビンゴカード発行]** を押すと、DMに5x5のキーワードビンゴカード画像が届きます。
4. 運営が **[抽選]** を押すと、未発表のキーワードが1つ選ばれ `stage_channel` で発表されます。
   - 全参加者のカードが自動判定され、マスが開いたユーザーには新しい状態のカード画像がDMで再送されます。
   - 縦・横・斜めのいずれかが揃う（ビンゴ）と、`stage_channel` でアナウンスされます。
5. **[終了]** ボタンで大会をリセットし、すべてのボタンを無効化します。
