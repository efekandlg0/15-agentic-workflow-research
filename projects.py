"""Proje kayıt defteri — her araştırma konusu ayrı bir 'proje' (ayrı sekme gibi).

Kalıcılık iki parçadan oluşur (ikisi de data/ klasöründe, git'e gitmez):
- checkpoints.db : LangGraph SqliteSaver — akışın TAM durumu (hangi kapıda
  beklendiği, tüm ajan çıktıları). Uygulama kapansa da kaldığı yerden sürer.
- projects.json  : proje listesi (konu, durum, karar geçmişi, son açılan) —
  kenar çubuğundaki proje seçici bu dosyadan beslenir.

Her proje id'si aynı zamanda LangGraph thread_id'sidir; iki kayıt bu id ile eşleşir.
"""
import json
import os
import uuid
from datetime import datetime

# Test/izole çalıştırma için ARW_DATA_DIR ile başka klasöre yönlendirilebilir.
DATA_DIR = os.environ.get("ARW_DATA_DIR") or os.path.join(
    os.path.dirname(os.path.abspath(__file__)), "data")
_REGISTRY = os.path.join(DATA_DIR, "projects.json")


def _read():
    try:
        with open(_REGISTRY, encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {"projects": [], "last_opened": None}


def _write(data):
    os.makedirs(DATA_DIR, exist_ok=True)
    tmp = _REGISTRY + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    os.replace(tmp, _REGISTRY)  # atomik: yarım yazılmış dosya kalmaz


def list_projects():
    """Projeler, en yeni en üstte."""
    return sorted(_read()["projects"], key=lambda p: p["created"], reverse=True)


def get_project(pid):
    for p in _read()["projects"]:
        if p["id"] == pid:
            return p
    return None


def create_project(topic: str):
    data = _read()
    p = {
        "id": str(uuid.uuid4()),
        "topic": (topic or "").strip() or "(konu girilmedi)",
        "created": datetime.now().isoformat(timespec="seconds"),
        "status": "başlatılıyor",
        "history": [],
        "final": None,
    }
    data["projects"].append(p)
    data["last_opened"] = p["id"]
    _write(data)
    return p


def update_project(pid, **fields):
    data = _read()
    for p in data["projects"]:
        if p["id"] == pid:
            p.update(fields)
            break
    _write(data)


def append_history(pid, gate, karar):
    data = _read()
    for p in data["projects"]:
        if p["id"] == pid:
            p.setdefault("history", []).append({"gate": gate, "karar": karar})
            break
    _write(data)


def set_last_opened(pid):
    data = _read()
    data["last_opened"] = pid
    _write(data)


def last_opened():
    return _read().get("last_opened")


def delete_project(pid):
    data = _read()
    data["projects"] = [p for p in data["projects"] if p["id"] != pid]
    if data.get("last_opened") == pid:
        data["last_opened"] = None
    _write(data)
