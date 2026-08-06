#!/bin/bash
# =============================================================
# Utonium.app oluşturucu (macOS)
# - assets/logo.png'den .icns uygulama ikonu üretir (sips + iconutil)
# - ~/Applications/Utonium.app paketini kurar
# Çalıştır:  bash launcher/build_mac_app.sh
# Sonra Utonium.app'i çift tıkla; istersen Dock'a sabitle.
# =============================================================
set -e
PROJECT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
APP_DIR="$HOME/Applications/Utonium.app"
ICONSET="$(mktemp -d)/utonium.iconset"

echo ">> Proje: $PROJECT_DIR"

# ---- 1) İkon (.icns) üret ----
# Kaynak: yuvarlak köşeli, kenar boşluklu macOS ikonu (launcher/make_icons.py üretir).
mkdir -p "$ICONSET"
SRC="$PROJECT_DIR/assets/icon_mac.png"
if [ ! -f "$SRC" ]; then
    echo ">> icon_mac.png yok, logodan üretiliyor..."
    python3 "$PROJECT_DIR/launcher/make_icons.py"
fi
for s in 16 32 128 256 512; do
    sips -z $s $s "$SRC" --out "$ICONSET/icon_${s}x${s}.png" >/dev/null
    d=$((s*2))
    sips -z $d $d "$SRC" --out "$ICONSET/icon_${s}x${s}@2x.png" >/dev/null
done
mkdir -p "$APP_DIR/Contents/MacOS" "$APP_DIR/Contents/Resources"
iconutil -c icns "$ICONSET" -o "$APP_DIR/Contents/Resources/utonium.icns"

# ---- 2) Info.plist ----
cat > "$APP_DIR/Contents/Info.plist" <<PLIST
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN"
  "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>CFBundleName</key><string>Utonium</string>
    <key>CFBundleDisplayName</key><string>Utonium</string>
    <key>CFBundleIdentifier</key><string>com.roblab.utonium</string>
    <key>CFBundleVersion</key><string>1.0</string>
    <key>CFBundlePackageType</key><string>APPL</string>
    <key>CFBundleExecutable</key><string>utonium</string>
    <key>CFBundleIconFile</key><string>utonium</string>
    <key>NSHighResolutionCapable</key><true/>
</dict>
</plist>
PLIST

# ---- 3) Başlatıcı (çift tıklayınca çalışan program) ----
cat > "$APP_DIR/Contents/MacOS/utonium" <<LAUNCH
#!/bin/bash
PROJECT_DIR="$PROJECT_DIR"
cd "\$PROJECT_DIR" || exit 1
# .env varsa gerçek model, yoksa MOCK (ücretsiz) mod
if [ -f .env ]; then unset MOCK_LLM; else export MOCK_LLM=1; fi
# Sunucu zaten açıksa yenisini başlatma, sadece pencereyi aç
if ! curl -s -o /dev/null --max-time 2 http://localhost:8501; then
    nohup .venv/bin/python -m streamlit run app.py \\
        --server.headless true --server.port 8501 > /tmp/utonium.log 2>&1 &
    for i in \$(seq 1 40); do
        curl -s -o /dev/null --max-time 1 http://localhost:8501 && break
        sleep 0.5
    done
fi
open "http://localhost:8501"
LAUNCH
chmod +x "$APP_DIR/Contents/MacOS/utonium"

echo ">> Kuruldu: $APP_DIR"
echo ">> Çift tıklayarak başlatabilirsin; Dock'a da sabitleyebilirsin."
