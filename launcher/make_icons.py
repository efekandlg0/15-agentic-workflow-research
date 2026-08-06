"""Logodan yuvarlak köşeli ikonları üretir (macOS uygulama ikonu stili).

Üretilenler (assets/ altına):
  logo.png       — arayüzde kullanılan yuvarlak köşeli logo (1024px)
  logo_small.png — sekme ikonu / kenar çubuğu logosu (256px)
  icon_mac.png   — .icns için macOS yerleşimi: kenar boşluklu + squircle köşeli

Çalıştır:  python3 launcher/make_icons.py [kaynak.png]
Kaynak verilmezse assets/logo_source.png kullanılır.
"""
import os
import sys

from PIL import Image, ImageDraw

HERE = os.path.dirname(os.path.abspath(__file__))
ASSETS = os.path.join(os.path.dirname(HERE), "assets")

# macOS Big Sur+ ikon oranları: içerik tuvalin ~%80'i, köşe yarıçapı içeriğin ~%22.5'i
MAC_CONTENT_RATIO = 0.80
MAC_RADIUS_RATIO = 0.225
# Arayüz logosunda daha hafif bir yuvarlatma yeterli
UI_RADIUS_RATIO = 0.18


def rounded(img: Image.Image, radius_ratio: float) -> Image.Image:
    """Kareye kırpıp köşeleri yuvarlatır (köşeler saydam olur)."""
    side = min(img.size)
    left = (img.width - side) // 2
    top = (img.height - side) // 2
    img = img.crop((left, top, left + side, top + side)).convert("RGBA")

    # Kenar yumuşatma için maskeyi 4 kat büyük çizip küçültüyoruz.
    scale = 4
    mask = Image.new("L", (side * scale, side * scale), 0)
    ImageDraw.Draw(mask).rounded_rectangle(
        (0, 0, side * scale - 1, side * scale - 1),
        radius=int(side * scale * radius_ratio), fill=255)
    mask = mask.resize((side, side), Image.LANCZOS)

    out = Image.new("RGBA", (side, side), (0, 0, 0, 0))
    out.paste(img, (0, 0), mask)
    return out


def mac_icon(img: Image.Image, size: int = 1024) -> Image.Image:
    """macOS yerleşimi: saydam tuval üzerinde ortalanmış, kenar boşluklu yuvarlak ikon."""
    content = int(size * MAC_CONTENT_RATIO)
    inner = rounded(img, MAC_RADIUS_RATIO).resize((content, content), Image.LANCZOS)
    canvas = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    off = (size - content) // 2
    canvas.paste(inner, (off, off), inner)
    return canvas


def main():
    src_path = sys.argv[1] if len(sys.argv) > 1 else os.path.join(ASSETS, "logo_source.png")
    src = Image.open(src_path)
    os.makedirs(ASSETS, exist_ok=True)

    ui = rounded(src, UI_RADIUS_RATIO)
    ui.resize((1024, 1024), Image.LANCZOS).save(os.path.join(ASSETS, "logo.png"))
    ui.resize((256, 256), Image.LANCZOS).save(os.path.join(ASSETS, "logo_small.png"))
    mac_icon(src).save(os.path.join(ASSETS, "icon_mac.png"))
    print("Üretildi: assets/logo.png, logo_small.png, icon_mac.png")


if __name__ == "__main__":
    main()
