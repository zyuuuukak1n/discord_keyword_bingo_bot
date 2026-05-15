import os
import urllib.request
import zipfile

FONT_URL = "https://github.com/googlefonts/noto-cjk/raw/main/Sans/Variable/TTF/NotoSansCJKjp-VF.ttf"
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
FONT_DIR = os.path.join(BASE_DIR, "fonts")
FONT_FILE = os.path.join(FONT_DIR, "NotoSansJP-Regular.ttf")

def download_font():
    if not os.path.exists(FONT_DIR):
        os.makedirs(FONT_DIR)

    if os.path.exists(FONT_FILE):
        print(f"Font already exists at {FONT_FILE}")
        return

    print("Downloading Japanese font (NotoSansJP)...")
    try:
        urllib.request.urlretrieve(FONT_URL, FONT_FILE)
        print("Font downloaded successfully.")
    except Exception as e:
        print(f"Error downloading font: {e}")
        print("Please manually download a Japanese TTF font and place it at 'fonts/NotoSansJP-Regular.ttf'")

if __name__ == "__main__":
    download_font()
