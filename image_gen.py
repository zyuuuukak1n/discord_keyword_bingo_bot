import os
import io
from PIL import Image, ImageDraw, ImageFont

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
FONT_FILE = os.path.join(BASE_DIR, "fonts", "NotoSansJP-Regular.ttf")

def get_font(size: int) -> ImageFont.FreeTypeFont:
    try:
        return ImageFont.truetype(FONT_FILE, size)
    except IOError:
        # フォントが見つからない場合のフォールバック（日本語は文字化けする可能性あり）
        return ImageFont.load_default()

def draw_text_centered(draw: ImageDraw.ImageDraw, text: str, x: int, y: int, w: int, h: int, font: ImageFont.FreeTypeFont, fill=(0, 0, 0)):
    """指定した矩形領域の中央にテキストを描画する（長すぎる場合は改行）"""
    # 簡易的な折り返し処理（長すぎる単語を2行にする等）
    # 今回はシンプルに、文字数が多ければフォントサイズを縮小するか、改行を入れるアプローチを取る
    max_len = 7
    lines = []
    if len(text) > max_len:
        split_idx = len(text) // 2
        lines.append(text[:split_idx])
        lines.append(text[split_idx:])
    else:
        lines.append(text)
        
    line_h = font.size + 2
    total_h = line_h * len(lines)
    
    current_y = y + (h - total_h) / 2
    
    for line in lines:
        try:
            bbox = draw.textbbox((0, 0), line, font=font)
            text_w = bbox[2] - bbox[0]
        except AttributeError:
            # 古いPillowのフォールバック
            text_w, _ = draw.textsize(line, font=font)
            
        current_x = x + (w - text_w) / 2
        draw.text((current_x, current_y), line, fill=fill, font=font)
        current_y += line_h

def generate_card_image(user_id: int, card_keywords: list[list[str]], marked: list[list[bool]]) -> io.BytesIO:
    """
    ビンゴカードの画像を生成し、BytesIOオブジェクトとして返す。
    :param user_id: 透かしに入れるDiscord User ID
    :param card_keywords: 5x5のキーワード行列
    :param marked: 5x5の穴あき状態行列
    """
    width, height = 800, 800
    margin = 50
    cell_size = (width - margin * 2) // 5
    
    # 背景
    img = Image.new("RGB", (width, height), "white")
    draw = ImageDraw.Draw(img)
    
    # フォントの準備
    title_font = get_font(40)
    keyword_font = get_font(24)
    watermark_font = get_font(60)
    
    # 透かしの描画
    watermark_layer = Image.new("RGBA", (width, height), (0,0,0,0))
    watermark_draw = ImageDraw.Draw(watermark_layer)
    watermark_text = f"User ID: {user_id}"
    try:
        bbox = watermark_draw.textbbox((0, 0), watermark_text, font=watermark_font)
        tw = bbox[2] - bbox[0]
        th = bbox[3] - bbox[1]
    except AttributeError:
        tw, th = watermark_draw.textsize(watermark_text, font=watermark_font)
        
    # 中央に斜めに配置
    watermark_draw.text(((width-tw)/2, (height-th)/2), watermark_text, font=watermark_font, fill=(200, 200, 200, 100))
    watermark_layer = watermark_layer.rotate(30, expand=False, center=(width/2, height/2))
    img.paste(watermark_layer, (0,0), watermark_layer)

    # タイトル
    draw.text((margin, 10), "KEYWORD BINGO", font=title_font, fill=(0, 0, 0))

    # グリッドとテキストの描画
    start_y = 70
    start_x = margin
    
    for r in range(5):
        for c in range(5):
            x = start_x + c * cell_size
            y = start_y + r * cell_size
            
            # セルの枠
            draw.rectangle([x, y, x + cell_size, y + cell_size], outline="black", width=2)
            
            # キーワードの描画
            word = card_keywords[r][c]
            draw_text_centered(draw, word, x, y, cell_size, cell_size, keyword_font)
            
            # 穴あき（済）の描画
            if marked[r][c]:
                # 赤い半透明の丸を描画するためのレイヤー
                overlay = Image.new("RGBA", (cell_size, cell_size), (0,0,0,0))
                overlay_draw = ImageDraw.Draw(overlay)
                
                pad = 10
                overlay_draw.ellipse([pad, pad, cell_size-pad, cell_size-pad], fill=(255, 0, 0, 100), outline=(255, 0, 0, 200), width=3)
                
                # 画像の合成
                img.paste(overlay, (x, y), overlay)

    # バッファに保存
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    buf.seek(0)
    return buf

# テスト用
if __name__ == "__main__":
    test_card = [
        ["りんご", "みかん", "ばなな", "すいか", "めろん"],
        ["きかく", "うんえい", "デザイン", "プログラミング", "テスト"],
        ["あか", "あお", "きいろ", "みどり", "むらさき"],
        ["いぬ", "ねこ", "うさぎ", "とり", "さかな"],
        ["やま", "かわ", "うみ", "そら", "ほし"],
    ]
    test_marked = [
        [False, True, False, False, False],
        [False, False, True, False, False],
        [False, False, False, True, False],
        [False, False, False, False, True],
        [True, False, False, False, False],
    ]
    buf = generate_card_image(123456789012345678, test_card, test_marked)
    with open("test_card.png", "wb") as f:
        f.write(buf.getvalue())
    print("Test card generated: test_card.png")
