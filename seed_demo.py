import json
from datetime import datetime, timedelta
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
DATA_FILE = BASE_DIR / "data.json"
PHOTOS_DIR = BASE_DIR / "photos"
PHOTOS_DIR.mkdir(exist_ok=True)

# Данные на основе реального каталога velosklad.ru (2026)
PRODUCTS = [
    # --- Велосипеды (10) ---
    {"name": "Горный велосипед Forward Sporting SX 27.5", "sku": "BK-001", "category": "Велосипеды",
     "cost": 13200, "price": 18950, "stock": 3, "emoji": "🚵", "c1": "#0d9488", "c2": "#134e4a"},
    {"name": "Горный велосипед Stels Navigator 500 MD 26", "sku": "BK-002", "category": "Велосипеды",
     "cost": 14800, "price": 20500, "stock": 4, "emoji": "🚵", "c1": "#2563eb", "c2": "#1e3a8a"},
    {"name": "Горный велосипед Benort Raptor 27.5", "sku": "BK-003", "category": "Велосипеды",
     "cost": 24500, "price": 33950, "stock": 2, "emoji": "🚵", "c1": "#7c3aed", "c2": "#4c1d95"},
    {"name": "Детский велосипед Stels Pilot 850 V 26", "sku": "BK-004", "category": "Велосипеды",
     "cost": 12800, "price": 18590, "stock": 5, "emoji": "🚲", "c1": "#f59e0b", "c2": "#b45309"},
    {"name": "Горный велосипед Cube Attention 29", "sku": "BK-005", "category": "Велосипеды",
     "cost": 42000, "price": 56990, "stock": 2, "emoji": "🚵", "c1": "#ef4444", "c2": "#7f1d1d"},
    {"name": "Горный велосипед Foxx Aragon 27.5", "sku": "BK-006", "category": "Велосипеды",
     "cost": 18500, "price": 25990, "stock": 3, "emoji": "🚵", "c1": "#0ea5e9", "c2": "#0c4a6e"},
    {"name": "Женский велосипед Forward Sporty 27.5", "sku": "BK-007", "category": "Велосипеды",
     "cost": 15200, "price": 21500, "stock": 2, "emoji": "🚲", "c1": "#ec4899", "c2": "#9d174d"},
    {"name": "Детский велосипед Royal Baby 16 Space", "sku": "BK-008", "category": "Велосипеды",
     "cost": 6800, "price": 9990, "stock": 7, "emoji": "🚲", "c1": "#f97316", "c2": "#7c2d12"},
    {"name": "Подростковый велосипед Stark Storm 24", "sku": "BK-009", "category": "Велосипеды",
     "cost": 11500, "price": 16500, "stock": 4, "emoji": "🚲", "c1": "#6366f1", "c2": "#312e81"},
    {"name": "Шоссейный велосипед Merida Scultura 100", "sku": "BK-010", "category": "Велосипеды",
     "cost": 48000, "price": 64990, "stock": 1, "emoji": "🚴", "c1": "#14b8a6", "c2": "#134e4a"},

    # --- Электротранспорт (4) ---
    {"name": "Электросамокат Ninebot KickScooter E2 Plus", "sku": "EL-001", "category": "Электротранспорт",
     "cost": 28500, "price": 34990, "stock": 3, "emoji": "🛴", "c1": "#7c3aed", "c2": "#4c1d95"},
    {"name": "Электровелосипед Haibike HardSeven 4", "sku": "EL-002", "category": "Электротранспорт",
     "cost": 185000, "price": 239990, "stock": 1, "emoji": "⚡", "c1": "#059669", "c2": "#064e3b"},
    {"name": "Электросамокат Eltreco Cruiser 10", "sku": "EL-003", "category": "Электротранспорт",
     "cost": 32000, "price": 42990, "stock": 2, "emoji": "🛴", "c1": "#8b5cf6", "c2": "#5b21b6"},
    {"name": "Электровелосипед Stark E-City 28", "sku": "EL-004", "category": "Электротранспорт",
     "cost": 68000, "price": 89990, "stock": 1, "emoji": "⚡", "c1": "#10b981", "c2": "#065f46"},

    # --- Комплектующие (8) ---
    {"name": "Камера Kenda 26x1.95", "sku": "CP-001", "category": "Комплектующие",
     "cost": 280, "price": 490, "stock": 30, "emoji": "🔧", "c1": "#64748b", "c2": "#334155"},
    {"name": "Покрышка Schwalbe Smart Sam 27.5x2.25", "sku": "CP-002", "category": "Комплектующие",
     "cost": 1800, "price": 2990, "stock": 12, "emoji": "⚙️", "c1": "#94a3b8", "c2": "#475569"},
    {"name": "Тормозные колодки Shimano B01S", "sku": "CP-003", "category": "Комплектующие",
     "cost": 350, "price": 690, "stock": 20, "emoji": "🛑", "c1": "#ef4444", "c2": "#7f1d1d"},
    {"name": "Цепь KMC X11 11-скор", "sku": "CP-004", "category": "Комплектующие",
     "cost": 1200, "price": 1990, "stock": 8, "emoji": "🔗", "c1": "#a3a3a3", "c2": "#525252"},
    {"name": "Переключатель задний Shimano Altus M2000", "sku": "CP-005", "category": "Комплектующие",
     "cost": 2400, "price": 3890, "stock": 5, "emoji": "⚙️", "c1": "#0f766e", "c2": "#134e4a"},
    {"name": "Руль Forward Alloy 720mm", "sku": "CP-006", "category": "Комплектующие",
     "cost": 900, "price": 1590, "stock": 6, "emoji": "🔧", "c1": "#78716c", "c2": "#44403c"},
    {"name": "Седло Velo VL-3078", "sku": "CP-007", "category": "Комплектующие",
     "cost": 650, "price": 1190, "stock": 10, "emoji": "🪑", "c1": "#1c1917", "c2": "#0c0a09"},
    {"name": "Педали Wellgo M111 алюм.", "sku": "CP-008", "category": "Комплектующие",
     "cost": 480, "price": 890, "stock": 14, "emoji": "⚙️", "c1": "#71717a", "c2": "#3f3f46"},

    # --- Аксессуары (7) ---
    {"name": "Фонарь передний Cateye Volt 300", "sku": "AC-001", "category": "Аксессуары",
     "cost": 2100, "price": 3290, "stock": 9, "emoji": "🔦", "c1": "#eab308", "c2": "#713f12"},
    {"name": "Замок вело Kryptonite Keeper 785", "sku": "AC-002", "category": "Аксессуары",
     "cost": 2800, "price": 4290, "stock": 6, "emoji": "🔒", "c1": "#6366f1", "c2": "#312e81"},
    {"name": "Велокомпьютер Sigma BC 5.16", "sku": "AC-003", "category": "Аксессуары",
     "cost": 1400, "price": 2290, "stock": 8, "emoji": "💻", "c1": "#3b82f6", "c2": "#1e3a8a"},
    {"name": "Насос ручной Lezyne Sport Drive HP", "sku": "AC-004", "category": "Аксессуары",
     "cost": 950, "price": 1590, "stock": 11, "emoji": "🔧", "c1": "#f59e0b", "c2": "#92400e"},
    {"name": "Флягодержатель Elite Custom Race", "sku": "AC-005", "category": "Аксессуары",
     "cost": 380, "price": 690, "stock": 15, "emoji": "🍶", "c1": "#22c55e", "c2": "#166534"},
    {"name": "Крылья SKS Shockboard 26-29", "sku": "AC-006", "category": "Аксессуары",
     "cost": 750, "price": 1290, "stock": 10, "emoji": "🛡️", "c1": "#64748b", "c2": "#334155"},
    {"name": "Зеркало вело Busch+Müller Cycle Star", "sku": "AC-007", "category": "Аксессуары",
     "cost": 850, "price": 1490, "stock": 7, "emoji": "🪞", "c1": "#a1a1aa", "c2": "#52525b"},

    # --- Экипировка (5) ---
    {"name": "Велошлем Giro Tremor M", "sku": "EQ-001", "category": "Экипировка",
     "cost": 2400, "price": 3900, "stock": 7, "emoji": "⛑️", "c1": "#0ea5e9", "c2": "#0c4a6e"},
    {"name": "Перчатки вело Fox Dirtpaw L", "sku": "EQ-002", "category": "Экипировка",
     "cost": 1500, "price": 2450, "stock": 12, "emoji": "🧤", "c1": "#f97316", "c2": "#7c2d12"},
    {"name": "Очки вело Uvex Sportstyle 231", "sku": "EQ-003", "category": "Экипировка",
     "cost": 2800, "price": 4490, "stock": 5, "emoji": "🕶️", "c1": "#1e293b", "c2": "#0f172a"},
    {"name": "Велорюкзак Deuter Compact EXP 12", "sku": "EQ-004", "category": "Экипировка",
     "cost": 4500, "price": 6990, "stock": 4, "emoji": "🎒", "c1": "#84cc16", "c2": "#3f6212"},
    {"name": "Велошлем Abus Hyban 2.0 M", "sku": "EQ-005", "category": "Экипировка",
     "cost": 3200, "price": 4990, "stock": 6, "emoji": "⛑️", "c1": "#dc2626", "c2": "#7f1d1d"},

    # --- Услуги (3) ---
    {"name": "Замена камеры (услуга)", "sku": "SV-001", "category": "Услуги",
     "cost": 100, "price": 500, "stock": 0, "emoji": "🛠️", "c1": "#16a34a", "c2": "#14532d"},
    {"name": "Полное ТО велосипеда (услуга)", "sku": "SV-002", "category": "Услуги",
     "cost": 400, "price": 1500, "stock": 0, "emoji": "🧰", "c1": "#14b8a6", "c2": "#134e4a"},
    {"name": "Настройка переключателя (услуга)", "sku": "SV-003", "category": "Услуги",
     "cost": 150, "price": 600, "stock": 0, "emoji": "🔧", "c1": "#0d9488", "c2": "#064e3b"},
]

CLIENTS = [
    {"name": "Иван Петров", "phone": "+7 900 111-22-33"},
    {"name": "Ольга Смирнова", "phone": "+7 900 222-33-44"},
    {"name": "Дмитрий Кузнецов", "phone": "+7 900 333-44-55"},
    {"name": "Мария Иванова", "phone": "+7 900 444-55-66"},
    {"name": "Алексей Соколов", "phone": "+7 900 555-66-77"},
    {"name": "Наталья Павлова", "phone": "+7 900 666-77-88"},
    {"name": "Сергей Морозов", "phone": "+7 900 777-88-99"},
    {"name": "Екатерина Волкова", "phone": "+7 900 888-99-00"},
    {"name": "Андрей Лебедев", "phone": "+7 900 999-00-11"},
    {"name": "Анна Новикова", "phone": "+7 900 000-11-22"},
]

TASKS = [
    {"client": "Иван Петров", "desc": "Замена камеры заднего колеса", "days": 1, "status": "В работе"},
    {"client": "Ольга Смирнова", "desc": "Полное техобслуживание перед продажей", "days": 3, "status": "Новая"},
    {"client": "Дмитрий Кузнецов", "desc": "Подобрать горный велосипед 27.5 в наличии", "days": 2, "status": "В работе"},
    {"client": "Алексей Соколов", "desc": "Настроить переключатель Shimano Altus", "days": 1, "status": "Ожидает ответа"},
    {"client": "Наталья Павлова", "desc": "Замена спицы и правка колеса", "days": 4, "status": "Новая"},
    {"client": "Екатерина Волкова", "desc": "Заказ электровелосипеда Haibike HardSeven", "days": 7, "status": "В работе"},
    {"client": "Андрей Лебедев", "desc": "Замена тормозных колодок Shimano", "days": 2, "status": "Новая"},
    {"client": "Анна Новикова", "desc": "Подобрать детский велосипед Royal Baby (6 лет)", "days": 3, "status": "Ожидает ответа"},
    {"client": "Мария Иванова", "desc": "Перезвонить по поводу велошлема Giro Tremor", "days": 1, "status": "Новая"},
    {"client": "Сергей Морозов", "desc": "Подготовить Cube Attention к примерке", "days": 2, "status": "Новая"},
]

CALLS = [
    {"client": "Мария Иванова", "days": -1, "result": "Не дозвонился", "note": "Перезвонить после 18:00, вопрос про велошлем Giro Tremor"},
    {"client": "Сергей Морозов", "days": 0, "result": "Назначена встреча", "note": "Придёт на примерку Cube Attention в субботу в 11:00"},
    {"client": "Анна Новикова", "days": -2, "result": "Консультация", "note": "Спрашивала про детские Royal Baby для ребёнка 6 лет"},
    {"client": "Иван Петров", "days": -1, "result": "Не дозвонился", "note": "Звонил насчёт записи на замену камеры Kenda"},
    {"client": "Екатерина Волкова", "days": -3, "result": "Оформлен заказ", "note": "Интересуется рассрочкой на электровелосипед Haibike"},
]


def svg_photo(fname, title, emoji, c1, c2):
    svg = f"""<svg xmlns="http://www.w3.org/2000/svg" width="400" height="300" viewBox="0 0 400 300">
  <defs><linearGradient id="g" x1="0" y1="0" x2="1" y2="1">
    <stop offset="0" stop-color="{c1}"/><stop offset="1" stop-color="{c2}"/>
  </linearGradient></defs>
  <rect width="400" height="300" fill="url(#g)"/>
  <circle cx="200" cy="130" r="95" fill="rgba(255,255,255,0.12)"/>
  <text x="200" y="145" font-size="100" text-anchor="middle" dominant-baseline="middle">{emoji}</text>
  <rect x="20" y="240" width="360" height="46" rx="10" fill="rgba(0,0,0,0.4)"/>
  <text x="200" y="270" font-size="20" text-anchor="middle" fill="#ffffff" font-family="Arial, sans-serif" font-weight="bold">{title[:40]}</text>
</svg>"""
    (PHOTOS_DIR / fname).write_text(svg, encoding="utf-8")


def next_id(items):
    ids = [int(i.get("id", 0)) for i in items]
    return (max(ids) if ids else 0) + 1


def main():
    if DATA_FILE.exists():
        data = json.loads(DATA_FILE.read_text(encoding="utf-8"))
    else:
        data = {}
    for key in ("products", "clients", "tasks", "calls", "categories"):
        data.setdefault(key, [])

    if data.get("demo_seeded"):
        print("Демо-данные уже добавлены. Пропускаю.")
        return

    existing_skus = {p.get("sku") for p in data["products"]}
    for p in PRODUCTS:
        if p["sku"] in existing_skus:
            continue
        fname = f"demo_{p['sku'].lower().replace('-', '')}.svg"
        svg_photo(fname, p["name"], p["emoji"], p["c1"], p["c2"])
        cat_id = next((c.get("id") for c in data["categories"] if c.get("name") == p["category"]), None)
        data["products"].append({
            "id": next_id(data["products"]),
            "name": p["name"],
            "sku": p["sku"],
            "category_id": cat_id,
            "category": p["category"],
            "actual_cost": p["cost"],
            "selling_price": p["price"],
            "stock_quantity": p["stock"],
            "photo": fname,
            "created_at": datetime.now().isoformat(timespec="seconds"),
        })

    existing_phones = {c.get("phone") for c in data["clients"]}
    client_ids = {}
    for cl in CLIENTS:
        if cl["phone"] in existing_phones:
            client_ids[cl["name"]] = next(c.get("id") for c in data["clients"] if c.get("phone") == cl["phone"])
            continue
        cid = next_id(data["clients"])
        data["clients"].append({
            "id": cid,
            "name": cl["name"],
            "phone": cl["phone"],
            "email": "",
            "created_at": datetime.now().isoformat(timespec="seconds"),
        })
        client_ids[cl["name"]] = cid

    today = datetime.now().date()
    for t in TASKS:
        cid = client_ids.get(t["client"])
        if cid is None:
            continue
        data["tasks"].append({
            "id": next_id(data["tasks"]),
            "description": t["desc"],
            "client_id": cid,
            "due_date": (today + timedelta(days=t["days"])).isoformat(),
            "status": t["status"],
            "created_at": datetime.now().isoformat(timespec="seconds"),
        })

    for c in CALLS:
        cid = client_ids.get(c["client"])
        if cid is None:
            continue
        data["calls"].append({
            "id": next_id(data["calls"]),
            "client_id": cid,
            "date": (today + timedelta(days=c["days"])).isoformat(),
            "result": c["result"],
            "note": c["note"],
            "created_at": datetime.now().isoformat(timespec="seconds"),
        })

    data["demo_seeded"] = True
    DATA_FILE.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Готово: товаров={len(data['products'])}, клиентов={len(data['clients'])}, задач={len(data['tasks'])}, звонков={len(data['calls'])}")


if __name__ == "__main__":
    main()
