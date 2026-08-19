import base64
import hashlib
import io
import json
import uuid
import zipfile
from datetime import datetime, timedelta
from pathlib import Path
from secrets import token_hex

import pandas as pd
import streamlit as st

# --- 1. ПУТИ И КОНСТАНТЫ ---

BASE_DIR = Path(__file__).resolve().parent
DATA_FILE = BASE_DIR / "data.json"
PHOTOS_DIR = BASE_DIR / "photos"
PHOTOS_DIR.mkdir(exist_ok=True)

DEFAULT_CATEGORIES = ["Велосипеды", "Электротранспорт", "Комплектующие", "Аксессуары", "Экипировка", "Услуги"]
TASK_STATUSES = ["Новая", "В работе", "Ожидает ответа", "Завершена", "Отменена"]
DONE_STATUSES = {"Завершена", "Отменена"}
CALL_RESULTS = ["Не дозвонился", "Перезвонить", "Назначена встреча", "Оформлен заказ", "Консультация", "Отказ", "Другое"]
SHOP_NAME = "Велоцентр"
SHOP_PHONE = "+7 (920) 497-47-87"
SHOP_ADDRESS = "Магистральная ул., 1Б, Тамбов"

CATEGORY_PRESETS = {
    "Велосипедный магазин": ["Велосипеды", "Электротранспорт", "Комплектующие", "Аксессуары", "Экипировка", "Услуги"],
    "Магазин одежды": ["Верхняя одежда", "Обувь", "Аксессуары", "Детская одежда", "Спортивная одежда", "Бельё"],
    "Электроника и техника": ["Смартфоны", "Компьютеры и ноутбуки", "Аудио и наушники", "Бытовая техника", "Аксессуары", "Сервис"],
    "Продуктовый магазин": ["Фрукты и овощи", "Молочные продукты", "Мясо и рыба", "Хлебобулочные изделия", "Напитки", "Бакалея"],
    "Канцтовары": ["Письменные принадлежности", "Бумага и офис", "Расходные материалы", "Творчество", "Учебные материалы", "Хранение"],
    "Спорттовары": ["Фитнес", "Командные виды спорта", "Туризм и походы", "Плавание", "Игры и развлечения", "Спортпит"],
    "Автозапчасти": ["Двигатель", "Подвеска", "Тормозная система", "Электрика", "Расходники", "Сервис"],
    "Товары для дома": ["Мебель", "Текстиль", "Посуда", "Декор", "Кухня", "Хранение"],
}

data = {}

# --- 2. УПРАВЛЕНИЕ ДАННЫМИ ---

def load_data():
    """Загружает данные из JSON-файла (или создаёт пустую структуру)."""
    global data
    try:
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        data = {}
    for key in ("products", "clients", "tasks", "categories", "calls"):
        data.setdefault(key, [])
    migrate_categories()
    migrate_auth()
    seed_shop_client()


def migrate_categories():
    """Создаёт категории по умолчанию и переносит старые строковые категории товаров в category_id."""
    cats = data.setdefault("categories", [])
    if not cats:
        for name in DEFAULT_CATEGORIES:
            cats.append({"id": next_id("categories"), "name": name})
    name_to_id = {c.get("name"): c.get("id") for c in cats if c.get("name")}
    for p in data["products"]:
        if p.get("category_id") is not None:
            continue
        old = p.get("category", "")
        if old:
            if old not in name_to_id:
                cid = next_id("categories")
                cats.append({"id": cid, "name": old})
                name_to_id[old] = cid
            p["category_id"] = name_to_id[old]
        else:
            p["category_id"] = None


def migrate_auth():
    """Создаёт учётную запись по умолчанию и переносит старый дефолт admin/admin → velocentr/demo."""
    auth = data.get("auth")
    if not auth or not auth.get("username") or not auth.get("password_hash") or not auth.get("salt"):
        salt = token_hex(16)
        data["auth"] = {
            "username": "velocentr",
            "salt": salt,
            "password_hash": hash_password("demo", salt),
        }
        save_data()
    elif auth.get("username") == "admin" and hash_password("admin", auth.get("salt", "")) == auth.get("password_hash"):
        salt = token_hex(16)
        auth["username"] = "velocentr"
        auth["salt"] = salt
        auth["password_hash"] = hash_password("demo", salt)
        save_data()


def seed_shop_client():
    """Добавляет контакт магазина в CRM при первом запуске (если клиентов нет)."""
    if data["clients"]:
        return
    data["clients"].append({
        "id": next_id("clients"),
        "name": f"{SHOP_NAME} (собственный магазин)",
        "phone": SHOP_PHONE,
        "email": "",
        "created_at": datetime.now().isoformat(timespec="seconds"),
    })
    save_data()


def save_data():
    """Сохраняет текущее состояние данных в JSON-файл."""
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def next_id(collection):
    """Возвращает следующий свободный id для коллекции."""
    ids = [int(item.get("id", 0)) for item in data[collection]]
    return (max(ids) if ids else 0) + 1


def get_client_name(client_id):
    """Возвращает имя клиента по id."""
    for client in data["clients"]:
        if client.get("id") == client_id:
            return client.get("name", "N/A")
    return "Без привязки"


def category_name(category_id):
    """Возвращает имя категории по id."""
    for c in data.get("categories", []):
        if c.get("id") == category_id:
            return c.get("name", "")
    return ""


def product_category_name(product):
    """Возвращает имя категории товара (с учётом старых данных)."""
    name = category_name(product.get("category_id"))
    return name or product.get("category", "") or "Без категории"


def category_names():
    """Возвращает список названий категорий в порядке следования."""
    return [c.get("name", "") for c in data.get("categories", [])]


def parse_date(value):
    """Преобразует ISO-строку даты в объект date."""
    if not value:
        return None
    try:
        return datetime.strptime(str(value)[:10], "%Y-%m-%d").date()
    except ValueError:
        return None


def format_currency(value):
    return f"{value:,.0f} ₽".replace(",", " ")


def hash_password(password, salt):
    """Возвращает хэш пароля с солью."""
    return hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt.encode("utf-8"), 100_000).hex()


def verify_password(password, salt, expected_hash):
    """Проверяет пароль по сохранённому хэшу."""
    return hash_password(password, salt) == expected_hash


def auth_credentials():
    """Возвращает учётные данные администратора."""
    return data.get("auth", {})


# --- 3. РАБОТА С ФОТОГРАФИЯМИ ---

def save_photo(uploaded, old_photo=None):
    """Сохраняет загруженный файл в папку photos и возвращает имя файла."""
    if uploaded is None:
        return old_photo
    ext = Path(uploaded.name).suffix.lower()
    if ext not in (".jpg", ".jpeg", ".png", ".webp", ".gif"):
        ext = ".jpg"
    fname = f"{datetime.now().strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:8]}{ext}"
    (PHOTOS_DIR / fname).write_bytes(uploaded.getbuffer())
    if old_photo and old_photo != fname:
        old = PHOTOS_DIR / old_photo
        if old.exists():
            old.unlink()
    return fname


def delete_photo(fname):
    """Удаляет файл фото из папки, если он существует."""
    if fname:
        old = PHOTOS_DIR / fname
        if old.exists():
            old.unlink()


def photo_uri(fname):
    """Возвращает data-URI фотографии для отображения в таблице."""
    if not fname:
        return None
    path = PHOTOS_DIR / fname
    if not path.exists():
        return None
    mime = {
        ".jpg": "image/jpeg", ".jpeg": "image/jpeg", ".png": "image/png",
        ".webp": "image/webp", ".gif": "image/gif", ".svg": "image/svg+xml",
    }.get(path.suffix.lower(), "image/jpeg")
    b64 = base64.b64encode(path.read_bytes()).decode()
    return f"data:{mime};base64,{b64}"


def excel_download(df, filename, label):
    """Кнопка скачивания DataFrame в Excel."""
    buf = io.BytesIO()
    with pd.ExcelWriter(buf, engine="openpyxl") as writer:
        df.to_excel(writer, index=False, sheet_name="Данные")
    return st.download_button(
        label,
        data=buf.getvalue(),
        file_name=filename,
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )


# --- 4. ПАНЕЛЬ СТАТИСТИКИ (Дашборд) ---

def display_dashboard():
    st.subheader("Панель статистики")
    products, clients, tasks = data["products"], data["clients"], data["tasks"]

    units = sum(int(p.get("stock_quantity", 0)) for p in products)
    total_cost = sum(float(p.get("actual_cost", 0)) * int(p.get("stock_quantity", 0)) for p in products)
    total_revenue = sum(float(p.get("selling_price", 0)) * int(p.get("stock_quantity", 0)) for p in products)
    open_tasks = [t for t in tasks if t.get("status") not in DONE_STATUSES]

    row1 = st.columns(3)
    row1[0].metric("Товаров на складе", len(products))
    row1[1].metric("Единиц в наличии", int(units))
    row1[2].metric("Себестоимость склада", format_currency(total_cost))

    row2 = st.columns(3)
    row2[0].metric("Потенциальная выручка", format_currency(total_revenue))
    row2[1].metric("Потенциальная прибыль", format_currency(total_revenue - total_cost))
    row2[2].metric("Клиентов в CRM", len(clients))

    col_left, col_right = st.columns(2)

    with col_left:
        st.markdown("### Остатки по категориям")
        if products:
            by_cat = {}
            for p in products:
                c = product_category_name(p)
                by_cat[c] = by_cat.get(c, 0) + int(p.get("stock_quantity", 0))
            st.bar_chart(pd.DataFrame({"Единиц": by_cat}))
        else:
            st.info("Нет данных о товарах.")

        st.markdown("### Топ-10 товаров по стоимости остатка")
        if products:
            ranked = sorted(
                ((p.get("name", "?"), float(p.get("actual_cost", 0)) * int(p.get("stock_quantity", 0)))
                 for p in products),
                key=lambda r: r[1], reverse=True,
            )[:10]
            st.bar_chart(pd.DataFrame({"Стоимость": dict(ranked)}))
        else:
            st.info("Нет данных.")

    with col_right:
        st.markdown("### Задачи по статусам")
        if tasks:
            by_status = {}
            for t in tasks:
                s = t.get("status") or "Новая"
                by_status[s] = by_status.get(s, 0) + 1
            st.bar_chart(pd.DataFrame({"Количество": by_status}))
        else:
            st.info("Задач пока нет.")

        st.markdown("### Ближайшие открытые задачи")
        if tasks:
            upcoming = [
                {
                    "Задача": t.get("description", ""),
                    "Клиент": get_client_name(t.get("client_id")),
                    "Срок": parse_date(t.get("due_date")),
                }
                for t in tasks
                if t.get("status") not in DONE_STATUSES and parse_date(t.get("due_date"))
            ]
            upcoming.sort(key=lambda r: r["Срок"])
            if upcoming:
                st.dataframe(
                    upcoming[:10],
                    use_container_width=True,
                    hide_index=True,
                    column_config={"Срок": st.column_config.DateColumn("Срок", format="DD.MM.YYYY")},
                )
            else:
                st.info("Открытых задач с указанным сроком нет.")
        else:
            st.info("Задач пока нет.")

    # ABC-анализ товаров
    st.markdown("---")
    st.markdown("### ABC-анализ товаров")
    if products:
        product_values = []
        for p in products:
            value = float(p.get("selling_price", 0)) * int(p.get("stock_quantity", 0))
            if value > 0:
                product_values.append({
                    "name": p.get("name", ""),
                    "category": product_category_name(p),
                    "value": value,
                    "stock": int(p.get("stock_quantity", 0)),
                    "price": float(p.get("selling_price", 0)),
                })

        if product_values:
            product_values.sort(key=lambda x: x["value"], reverse=True)
            total_value = sum(p["value"] for p in product_values)

            cumulative = 0
            for p in product_values:
                cumulative += p["value"]
                pct = cumulative / total_value * 100
                if pct <= 80:
                    p["abc"] = "A"
                elif pct <= 95:
                    p["abc"] = "B"
                else:
                    p["abc"] = "C"

            abc_a = [p for p in product_values if p["abc"] == "A"]
            abc_b = [p for p in product_values if p["abc"] == "B"]
            abc_c = [p for p in product_values if p["abc"] == "C"]

            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("A (80%)", f"{len(abc_a)} товаров")
            with col2:
                st.metric("B (15%)", f"{len(abc_b)} товаров")
            with col3:
                st.metric("C (5%)", f"{len(abc_c)} товаров")

            abc_df = pd.DataFrame([{
                "Товар": p["name"], "Категория": p["category"],
                "Остаток": p["stock"], "Цена": p["price"],
                "Стоимость": p["value"], "Группа": p["abc"],
            } for p in product_values[:20]])

            st.dataframe(abc_df, use_container_width=True, hide_index=True,
                column_config={
                    "Товар": st.column_config.TextColumn("Товар", width=250),
                    "Категория": st.column_config.TextColumn("Категория", width=130),
                    "Остаток": st.column_config.NumberColumn("Остаток", width=70),
                    "Цена": st.column_config.NumberColumn("Цена", format="%d ₽", width=90),
                    "Стоимость": st.column_config.NumberColumn("Стоимость", format="%d ₽", width=110),
                    "Группа": st.column_config.TextColumn("Группа", width=60),
                })
            st.caption("Топ-20 по стоимости. A = ключевые, B = контролируемые, C = на распродажу.")
        else:
            st.info("Нет товаров с ненулевым остатком.")
    else:
        st.info("Нет данных о товарах.")


# --- 5. МОДУЛЬ СКЛАДА ---

def display_inventory():
    st.subheader("Учёт склада")

    products = data["products"]
    col_search, col_cat = st.columns([2, 1])
    search = col_search.text_input("Поиск товара — введите название или артикул", key="inv_search")
    cats = ["Все"] + category_names()
    cat = col_cat.selectbox("Категория", cats, key="inv_cat")

    with st.expander("Дополнительные фильтры", expanded=False):
        col1, col2, col3, col4 = st.columns(4)
        in_stock = col1.checkbox("Только в наличии", key="inv_stock")
        sort_opt = col2.selectbox(
            "Сортировка",
            ["По названию", "По остатку ↑", "По остатку ↓", "По цене ↑", "По цене ↓", "По стоимости остатка ↓"],
            key="inv_sort",
        )
        min_price = col3.number_input("Цена от, ₽ (0 = без ограничения)", min_value=0.0, step=100.0, key="inv_price_min")
        max_price = col4.number_input("Цена до, ₽ (0 = без ограничения)", min_value=0.0, step=100.0, key="inv_price_max")

    filtered = [
        p for p in products
        if (cat == "Все" or product_category_name(p) == cat)
        and (not search or search.lower() in (f"{p.get('name', '')} {p.get('sku', '')}").lower())
        and (not in_stock or int(p.get("stock_quantity", 0)) > 0)
        and (float(min_price) == 0 or float(p.get("selling_price", 0)) >= float(min_price))
        and (float(max_price) == 0 or float(p.get("selling_price", 0)) <= float(max_price))
    ]

    sort_map = {
        "По названию": lambda p: str(p.get("name", "")).lower(),
        "По остатку ↑": lambda p: int(p.get("stock_quantity", 0)),
        "По остатку ↓": lambda p: -int(p.get("stock_quantity", 0)),
        "По цене ↑": lambda p: float(p.get("selling_price", 0)),
        "По цене ↓": lambda p: -float(p.get("selling_price", 0)),
        "По стоимости остатка ↓": lambda p: -float(p.get("actual_cost", 0)) * int(p.get("stock_quantity", 0)),
    }
    filtered.sort(key=sort_map[sort_opt])

    if not filtered:
        st.warning("Склад пуст или ничего не найдено по заданным условиям. Добавьте товары ниже или измените фильтры.")
        return

    rows = []
    for p in filtered:
        rows.append({
            "id": p.get("id"),
            "Наименование": p.get("name", ""),
            "Артикул": p.get("sku", ""),
            "Категория": product_category_name(p),
            "Себестоимость": p.get("actual_cost", 0),
            "Цена": p.get("selling_price", 0),
            "Остаток": p.get("stock_quantity", 0),
            "Стоимость остатка": round(float(p.get("actual_cost", 0)) * int(p.get("stock_quantity", 0)), 2),
        })

    st.dataframe(
        rows,
        use_container_width=True,
        hide_index=True,
        column_config={
            "id": st.column_config.NumberColumn("ID", width=40),
            "Наименование": st.column_config.TextColumn("Наименование", width=280),
            "Артикул": st.column_config.TextColumn("Артикул", width=100),
            "Категория": st.column_config.TextColumn("Категория", width=130),
            "Себестоимость": st.column_config.NumberColumn("Себестоимость", format="%d ₽", width=90),
            "Цена": st.column_config.NumberColumn("Цена", format="%d ₽", width=90),
            "Остаток": st.column_config.NumberColumn("Остаток", width=70),
            "Стоимость остатка": st.column_config.NumberColumn("Стоимость остатка", format="%d ₽", width=110),
        },
    )
    st.caption(f"Показано товаров: {len(filtered)} · Единиц в наличии: {sum(int(p.get('stock_quantity', 0)) for p in filtered)}")

    export_df = pd.DataFrame([{
        "ID": p.get("id"),
        "Наименование": p.get("name", ""),
        "Артикул": p.get("sku", ""),
        "Категория": product_category_name(p),
        "Себестоимость": p.get("actual_cost", 0),
        "Цена": p.get("selling_price", 0),
        "Остаток": p.get("stock_quantity", 0),
        "Стоимость остатка": round(float(p.get("actual_cost", 0)) * int(p.get("stock_quantity", 0)), 2),
    } for p in filtered])
    excel_download(export_df, "velocentr_sklad.xlsx", "Экспорт товаров в Excel")


def product_editor():
    st.markdown("---")
    st.header("Управление товарами")
    mode = st.radio("Режим", ["Добавить", "Редактировать", "Удалить"], horizontal=True, key="prod_mode")

    if mode == "Добавить":
        with st.form("add_product"):
            st.subheader("Добавить новый товар")
            name = st.text_input("Наименование товара")
            sku = st.text_input("Артикул (SKU)")
            if category_names():
                category_sel = st.selectbox("Категория", category_names())
                category_id = {c.get("name"): c.get("id") for c in data["categories"]}.get(category_sel)
            else:
                category_sel = ""
                category_id = None
                st.info("Сначала создайте категории в разделе «Категории».")
            col1, col2, col3 = st.columns(3)
            actual_cost = col1.number_input("Себестоимость, ₽", min_value=0.0, step=0.5)
            selling_price = col2.number_input("Продажная цена, ₽", min_value=0.0, step=0.5)
            stock = col3.number_input("Остаток на складе", min_value=0, step=1)
            if st.form_submit_button("Добавить товар"):
                if not name.strip() or not sku.strip():
                    st.error("Заполните наименование и артикул.")
                else:
                    data["products"].append({
                        "id": next_id("products"),
                        "name": name.strip(),
                        "sku": sku.strip(),
                        "category_id": category_id,
                        "category": category_sel,
                        "actual_cost": float(actual_cost),
                        "selling_price": float(selling_price),
                        "stock_quantity": int(stock),
                        "photo": None,
                        "created_at": datetime.now().isoformat(timespec="seconds"),
                    })
                    save_data()
                    st.success(f"Товар «{name.strip()}» добавлен.")

    elif mode == "Редактировать":
        if not data["products"]:
            st.info("Товаров пока нет.")
            return
        labels = {f"#{p.get('id')} · {p.get('name', '')} ({p.get('sku', '')})": p for p in data["products"]}
        sel = st.selectbox("Выберите товар", list(labels.keys()), key="prod_edit_sel")
        p = labels[sel]
        pid = p.get("id")
        with st.form(f"edit_product_{pid}"):
            st.subheader(f"Редактирование: {p.get('name', '')}")
            name = st.text_input("Наименование", value=p.get("name", ""), key=f"ep_name_{pid}")
            sku = st.text_input("Артикул (SKU)", value=p.get("sku", ""), key=f"ep_sku_{pid}")
            cat_names = category_names()
            cat_ids = {c.get("name"): c.get("id") for c in data.get("categories", [])}
            if cat_names:
                cur_name = category_name(p.get("category_id"))
                cat_index = cat_names.index(cur_name) if cur_name in cat_names else 0
                category_sel = st.selectbox("Категория", cat_names, index=cat_index, key=f"ep_cat_{pid}")
            else:
                category_sel = ""
                st.info("Сначала создайте категории в разделе «Категории».")
            col1, col2, col3 = st.columns(3)
            actual_cost = col1.number_input("Себестоимость, ₽", min_value=0.0, value=float(p.get("actual_cost", 0)), key=f"ep_cost_{pid}")
            selling_price = col2.number_input("Продажная цена, ₽", min_value=0.0, value=float(p.get("selling_price", 0)), key=f"ep_price_{pid}")
            stock = col3.number_input("Остаток", min_value=0, value=int(p.get("stock_quantity", 0)), key=f"ep_stock_{pid}")
            if st.form_submit_button("Сохранить изменения"):
                p.update({
                    "name": name.strip(),
                    "sku": sku.strip(),
                    "category_id": cat_ids.get(category_sel) if category_sel else None,
                    "category": category_sel,
                    "actual_cost": float(actual_cost),
                    "selling_price": float(selling_price),
                    "stock_quantity": int(stock),
                })
                save_data()
                st.success("Изменения сохранены.")

    else:
        if not data["products"]:
            st.info("Товаров пока нет.")
            return
        labels = {f"#{p.get('id')} · {p.get('name', '')} ({p.get('sku', '')})": p for p in data["products"]}
        sel = st.selectbox("Выберите товар для удаления", list(labels.keys()), key="prod_del_sel")
        p = labels[sel]
        confirm = st.checkbox("Я подтверждаю удаление этого товара", key="prod_del_confirm")
        if st.button("Удалить товар", disabled=not confirm):
            data["products"] = [x for x in data["products"] if x.get("id") != p.get("id")]
            delete_photo(p.get("photo"))
            save_data()
            st.success(f"Товар «{p.get('name')}» удалён.")
            st.rerun()


# --- 6. МОДУЛЬ CRM ---

def crm_page():
    """Единая страница CRM — вкладки: Клиенты / Задачи / Звонки."""
    tab_clients, tab_tasks, tab_calls = st.tabs(["Клиенты", "Задачи", "Звонки"])

    with tab_clients:
        crm_clients_section()

    with tab_tasks:
        crm_tasks_section()

    with tab_calls:
        crm_calls_section()


def crm_clients_section():
    """Клиенты — карточки + добавление + редактирование по клику."""
    st.subheader("Клиенты")

    # Кнопка добавления
    if st.button("Новый клиент", key="btn_add_client"):
        st.session_state["edit_client_id"] = "new"
        st.rerun()

    # Если выбран клиент для редактирования
    edit_id = st.session_state.get("edit_client_id")
    if edit_id is not None:
        client_edit_form(edit_id)
        return

    # Список клиентов — карточки
    clients = data.get("clients", [])
    if not clients:
        st.info("Клиентов пока нет. Нажмите «Новый клиент».")
        return

    # Поиск
    search = st.text_input("Поиск клиента", key="client_search", placeholder="Имя или телефон...")
    if search:
        clients = [c for c in clients if search.lower() in f"{c.get('name','')} {c.get('phone','')}".lower()]

    for c in clients:
        cid = c.get("id")
        tasks_count = len([t for t in data.get("tasks", []) if t.get("client_id") == cid and t.get("status") not in DONE_STATUSES])
        calls_count = len([x for x in data.get("calls", []) if x.get("client_id") == cid])
        order = c.get("order_number", "")
        comment = c.get("comment", "")

        # Карточка клиента
        with st.container():
            col1, col2, col3 = st.columns([5, 2, 1])
            with col1:
                st.markdown(f"**{c.get('name', '')}** · {c.get('phone', '')}")
                if order:
                    st.caption(f"Заказ: {order}")
                if comment:
                    st.caption(f"{comment[:60]}")
            with col2:
                st.caption(f"{tasks_count} задач · {calls_count} звонков")
            with col3:
                if st.button("Ред.", key=f"edit_c_{cid}", help="Редактировать"):
                    st.session_state["edit_client_id"] = cid
                    st.rerun()
            st.divider()


def client_edit_form(edit_id):
    """Форма редактирования/добавления клиента."""
    if edit_id == "new":
        st.subheader("Новый клиент")
        c = {"name": "", "phone": "", "order_number": "", "comment": ""}
    else:
        c = next((x for x in data["clients"] if x.get("id") == edit_id), None)
        if not c:
            st.error("Клиент не найден.")
            st.session_state["edit_client_id"] = None
            return
        st.subheader(c.get('name', ''))

    name = st.text_input("Имя", value=c.get("name", ""), key="cef_name")
    phone = st.text_input("Телефон", value=c.get("phone", ""), key="cef_phone")
    order_number = st.text_input("Номер заказа", value=c.get("order_number", ""), key="cef_order")
    comment = st.text_area("Комментарий", value=c.get("comment", ""), key="cef_comment")

    col1, col2, col3 = st.columns(3)
    with col1:
        if st.button("Сохранить", type="primary", use_container_width=True):
            if not name.strip() or not phone.strip():
                st.error("Имя и телефон обязательны.")
            elif edit_id == "new":
                data["clients"].append({
                    "id": next_id("clients"),
                    "name": name.strip(),
                    "phone": phone.strip(),
                    "order_number": order_number.strip(),
                    "comment": comment.strip(),
                    "created_at": datetime.now().isoformat(timespec="seconds"),
                })
                save_data()
                st.session_state["edit_client_id"] = None
                st.success(f"Клиент «{name.strip()}» добавлен.")
                st.rerun()
            else:
                c.update({
                    "name": name.strip(),
                    "phone": phone.strip(),
                    "order_number": order_number.strip(),
                    "comment": comment.strip(),
                })
                save_data()
                st.session_state["edit_client_id"] = None
                st.success("Сохранено.")
                st.rerun()
    with col2:
        if st.button("Назад", use_container_width=True):
            st.session_state["edit_client_id"] = None
            st.rerun()
    with col3:
        if edit_id != "new":
            if st.button("Удалить", use_container_width=True):
                data["clients"] = [x for x in data["clients"] if x.get("id") != edit_id]
                for t in data["tasks"]:
                    if t.get("client_id") == edit_id:
                        t["client_id"] = None
                save_data()
                st.session_state["edit_client_id"] = None
                st.success("Удалён.")
                st.rerun()

    # Задачи клиента
    if edit_id != "new":
        client_tasks = [t for t in data.get("tasks", []) if t.get("client_id") == edit_id]
        if client_tasks:
            st.markdown("---")
            st.markdown("**Задачи клиента:**")
            for t in client_tasks:
                due = parse_date(t.get("due_date"))
                status = t.get("status", "Новая")
                status_icon = {"Новая": "", "В работе": "", "Ожидает ответа": "", "Завершена": "", "Отменена": ""}.get(status, "")
                st.caption(f"{status_icon} {t.get('description', '')} — до {due.strftime('%d.%m') if due else '—'} [{status}]")


def crm_tasks_section():
    """Задачи — Kanban-доска с колонками по статусам."""
    st.subheader("Задачи")

    if st.button("Новая задача", key="btn_add_task"):
        st.session_state["edit_task_id"] = "new"
        st.rerun()

    edit_id = st.session_state.get("edit_task_id")
    if edit_id is not None:
        task_edit_form(edit_id)
        return

    tasks = data.get("tasks", [])
    if not tasks:
        st.info("Задач пока нет.")
        return

    today = datetime.now().date()
    kanban_statuses = ["Новая", "В работе", "Ожидает ответа", "Завершена"]
    status_colors = {"Новая": "#3b82f6", "В работе": "#f59e0b", "Ожидает ответа": "#8b5cf6", "Завершена": "#10b981"}

    # Kanban-доска — 4 колонки
    cols = st.columns(4)
    for i, status in enumerate(kanban_statuses):
        with cols[i]:
            st.markdown(f"""
            <div style="text-align:center; padding:8px; border-radius:10px;
                        background:{status_colors[status]}22; border:1px solid {status_colors[status]}44;
                        margin-bottom:10px;">
                <b style="color:{status_colors[status]}; font-size:0.9rem;">{status}</b>
            </div>
            """, unsafe_allow_html=True)

            status_tasks = [t for t in tasks if t.get("status") == status]
            # Сортировка: просрочные первыми
            def sk(t):
                d = parse_date(t.get("due_date"))
                return (0, d) if d and d < today and status not in DONE_STATUSES else (1, d or today)
            status_tasks.sort(key=sk)

            if not status_tasks:
                st.caption("—")

            for t in status_tasks:
                tid = t.get("id")
                due = parse_date(t.get("due_date"))
                client = get_client_name(t.get("client_id"))
                is_overdue = due and due < today and status not in DONE_STATUSES

                overdue_badge = " (!)" if is_overdue else ""
                due_str = due.strftime("%d.%m") if due else "—"

                st.markdown(f"""
                <div class="kanban-card" style="{'border-left:3px solid #ef4444;' if is_overdue else ''}">
                    <b>{t.get('description', '')[:35]}{overdue_badge}</b><br>
                    <span>{client} · {due_str}</span>
                </div>
                """, unsafe_allow_html=True)

                # Кнопки действий
                btn_cols = st.columns(2)
                with btn_cols[0]:
                    if st.button("Ред.", key=f"kb_edit_{tid}", help="Редактировать"):
                        st.session_state["edit_task_id"] = tid
                        st.rerun()
                with btn_cols[1]:
                    # Кнопка перемещения вправо
                    next_map = {"Новая": "В работе", "В работе": "Завершена", "Ожидает ответа": "Завершена"}
                    if status in next_map:
                        if st.button("→", key=f"kb_next_{tid}", help=f"→ {next_map[status]}"):
                            t["status"] = next_map[status]
                            save_data()
                            st.rerun()


def task_edit_form(edit_id):
    """Форма редактирования/добавления задачи."""
    if edit_id == "new":
        st.subheader("Новая задача")
        t = {"description": "", "client_id": None, "due_date": (datetime.now().date() + timedelta(days=3)).isoformat(), "status": "Новая"}
    else:
        t = next((x for x in data["tasks"] if x.get("id") == edit_id), None)
        if not t:
            st.error("Задача не найдена.")
            st.session_state["edit_task_id"] = None
            return
        st.subheader(f"Задача #{edit_id}")

    desc = st.text_area("Описание", value=t.get("description", ""), key="tef_desc")

    # Выбор клиента
    client_labels = {"Без привязки": None}
    client_labels.update({f"{c.get('name', '')} ({c.get('phone', '')})": c.get("id") for c in data.get("clients", [])})
    current_client = next((k for k, v in client_labels.items() if v == t.get("client_id")), "Без привязки")
    client_sel = st.selectbox("Клиент", list(client_labels.keys()),
                              index=list(client_labels.keys()).index(current_client), key="tef_client")

    col1, col2 = st.columns(2)
    with col1:
        due = st.date_input("Срок", value=parse_date(t.get("due_date")) or datetime.now().date(), key="tef_due")
    with col2:
        status_index = TASK_STATUSES.index(t.get("status")) if t.get("status") in TASK_STATUSES else 0
        status = st.selectbox("Статус", TASK_STATUSES, index=status_index, key="tef_status")

    # Связь со складом — показать релевантные товары
    products_in_stock = [p for p in data.get("products", []) if int(p.get("stock_quantity", 0)) > 0]
    if products_in_stock:
        with st.expander("Товары на складе (для подбора)", expanded=False):
            # Поиск по товарам
            stock_search = st.text_input("Найти товар", key="tef_stock_search", placeholder="Название или артикул...")
            filtered_products = products_in_stock
            if stock_search:
                filtered_products = [p for p in products_in_stock
                                     if stock_search.lower() in f"{p.get('name','')} {p.get('sku','')}".lower()]
            if filtered_products:
                stock_df = pd.DataFrame([{
                    "Товар": p.get("name", ""),
                    "Артикул": p.get("sku", ""),
                    "Цена": p.get("selling_price", 0),
                    "Остаток": p.get("stock_quantity", 0),
                } for p in filtered_products[:15]])
                st.dataframe(stock_df, use_container_width=True, hide_index=True,
                    column_config={
                        "Товар": st.column_config.TextColumn("Товар", width=250),
                        "Артикул": st.column_config.TextColumn("Артикул", width=100),
                        "Цена": st.column_config.NumberColumn("Цена", format="%d ₽", width=90),
                        "Остаток": st.column_config.NumberColumn("Остаток", width=70),
                    })
            else:
                st.caption("Ничего не найдено.")

    col1, col2, col3 = st.columns(3)
    with col1:
        if st.button("Сохранить", type="primary", use_container_width=True):
            if not desc.strip():
                st.error("Опишите задачу.")
            elif edit_id == "new":
                data["tasks"].append({
                    "id": next_id("tasks"),
                    "description": desc.strip(),
                    "client_id": client_labels[client_sel],
                    "due_date": due.isoformat(),
                    "status": status,
                    "created_at": datetime.now().isoformat(timespec="seconds"),
                })
                save_data()
                st.session_state["edit_task_id"] = None
                st.success("Задача добавлена.")
                st.rerun()
            else:
                t.update({
                    "description": desc.strip(),
                    "client_id": client_labels[client_sel],
                    "due_date": due.isoformat(),
                    "status": status,
                })
                save_data()
                st.session_state["edit_task_id"] = None
                st.success("Сохранено.")
                st.rerun()
    with col2:
        if st.button("Назад", use_container_width=True):
            st.session_state["edit_task_id"] = None
            st.rerun()
    with col3:
        if edit_id != "new":
            if st.button("Удалить", use_container_width=True):
                data["tasks"] = [x for x in data["tasks"] if x.get("id") != edit_id]
                save_data()
                st.session_state["edit_task_id"] = None
                st.success("Удалена.")
                st.rerun()


def crm_calls_section():
    """Звонки — журнал с добавлением."""
    st.subheader("Журнал звонков")

    if st.button("Новый звонок", key="btn_add_call"):
        st.session_state["edit_call_id"] = "new"
        st.rerun()

    edit_id = st.session_state.get("edit_call_id")
    if edit_id is not None:
        call_edit_form(edit_id)
        return

    calls = data.get("calls", [])
    if not calls:
        st.info("Звонков пока нет.")
        return

    for x in sorted(calls, key=lambda r: str(r.get("date", "")), reverse=True):
        due = parse_date(x.get("date"))
        client = get_client_name(x.get("client_id"))
        result = x.get("result", "")
        note = x.get("note", "")
        result_icons = {"Не дозвонился": "", "Перезвонить": "", "Назначена встреча": "",
                        "Оформлен заказ": "", "Консультация": "", "Отказ": "", "Другое": ""}
        icon = result_icons.get(result, "")

        with st.container():
            col1, col2 = st.columns([7, 1])
            with col1:
                st.markdown(f"**{icon} {client}** · {due.strftime('%d.%m.%Y') if due else '—'}")
                st.caption(f"{result} — {note[:80]}")
            with col2:
                if st.button("Ред.", key=f"edit_x_{x.get('id')}", help="Редактировать"):
                    st.session_state["edit_call_id"] = x.get("id")
                    st.rerun()
            st.divider()


def call_edit_form(edit_id):
    """Форма редактирования/добавления звонка."""
    if edit_id == "new":
        st.subheader("Новый звонок")
        x = {"client_id": None, "date": datetime.now().date().isoformat(), "result": "Консультация", "note": ""}
    else:
        x = next((c for c in data["calls"] if c.get("id") == edit_id), None)
        if not x:
            st.error("Звонок не найден.")
            st.session_state["edit_call_id"] = None
            return
        st.subheader(f"Звонок #{edit_id}")

    client_labels = {"Без привязки": None}
    client_labels.update({f"{c.get('name', '')} ({c.get('phone', '')})": c.get("id") for c in data.get("clients", [])})
    current_client = next((k for k, v in client_labels.items() if v == x.get("client_id")), "Без привязки")
    client_sel = st.selectbox("Клиент", list(client_labels.keys()),
                              index=list(client_labels.keys()).index(current_client), key="xef_client")

    col1, col2 = st.columns(2)
    with col1:
        date = st.date_input("Дата", value=parse_date(x.get("date")) or datetime.now().date(), key="xef_date")
    with col2:
        result_index = CALL_RESULTS.index(x.get("result")) if x.get("result") in CALL_RESULTS else 0
        result = st.selectbox("Результат", CALL_RESULTS, index=result_index, key="xef_result")

    note = st.text_area("Заметка", value=x.get("note", ""), key="xef_note")

    col1, col2, col3 = st.columns(3)
    with col1:
        if st.button("Сохранить", type="primary", use_container_width=True):
            if edit_id == "new":
                data["calls"].append({
                    "id": next_id("calls"),
                    "client_id": client_labels[client_sel],
                    "date": date.isoformat(),
                    "result": result,
                    "note": note.strip(),
                    "created_at": datetime.now().isoformat(timespec="seconds"),
                })
                save_data()
                st.session_state["edit_call_id"] = None
                st.success("Звонок записан.")
                st.rerun()
            else:
                x.update({
                    "client_id": client_labels[client_sel],
                    "date": date.isoformat(),
                    "result": result,
                    "note": note.strip(),
                })
                save_data()
                st.session_state["edit_call_id"] = None
                st.success("Сохранено.")
                st.rerun()
    with col2:
        if st.button("Назад", use_container_width=True):
            st.session_state["edit_call_id"] = None
            st.rerun()
    with col3:
        if edit_id != "new":
            if st.button("Удалить", use_container_width=True):
                data["calls"] = [c for c in data["calls"] if c.get("id") != edit_id]
                save_data()
                st.session_state["edit_call_id"] = None
                st.success("Удалён.")
                st.rerun()



# --- 7. МОДУЛЬ КАТЕГОРИЙ ---

def display_categories_overview():
    st.subheader("Категории товаров")
    cats = data.get("categories", [])
    if not cats:
        st.warning("Категорий пока нет — создайте их вручную или примените готовый шаблон.")
        return
    counts = {}
    for p in data["products"]:
        cid = p.get("category_id")
        counts[cid] = counts.get(cid, 0) + 1
    rows = [{
        "№": i + 1,
        "Категория": c.get("name", ""),
        "Товаров": counts.get(c.get("id"), 0),
    } for i, c in enumerate(cats)]
    st.dataframe(
        rows,
        use_container_width=True,
        hide_index=True,
        column_config={
            "№": st.column_config.NumberColumn("№", width=40),
            "Категория": st.column_config.TextColumn("Категория", width=300),
            "Товаров": st.column_config.NumberColumn("Товаров", width=100),
        },
    )
    st.caption(f"Всего категорий: {len(cats)} · Порядок влияет на список выбора в форме товара.")


def categories_presets():
    st.markdown("### Готовые структуры категорий")
    preset = st.selectbox("Выберите шаблон", list(CATEGORY_PRESETS.keys()), key="cat_preset_sel")
    st.markdown("Категории в шаблоне: **" + ", ".join(CATEGORY_PRESETS[preset]) + "**")
    mode = st.radio(
        "Способ применения",
        ["Дополнить текущие категории (существующие сохранятся)", "Заменить все текущие категории"],
        key="cat_preset_mode",
    )
    confirm = st.checkbox("Я понимаю, что категории будут изменены", key="cat_preset_confirm")
    if st.button("Применить шаблон", disabled=not confirm):
        existing = {c.get("name") for c in data["categories"]}
        if mode.startswith("Заменить"):
            data["categories"] = []
            for p in data["products"]:
                p["category_id"] = None
                p["category"] = ""
        for name in CATEGORY_PRESETS[preset]:
            if name not in existing or not data["categories"]:
                data["categories"].append({"id": next_id("categories"), "name": name})
        save_data()
        st.success(f"Шаблон «{preset}» применён.")
        st.rerun()


def categories_editor():
    st.markdown("---")
    st.header("Управление категориями")
    cats = data.get("categories", [])

    with st.form("add_category", clear_on_submit=True):
        st.subheader("Добавить категорию")
        new_name = st.text_input("Название новой категории")
        if st.form_submit_button("Добавить категорию"):
            if not new_name.strip():
                st.error("Введите название категории.")
            elif any(c.get("name", "").lower() == new_name.strip().lower() for c in cats):
                st.error("Такая категория уже существует.")
            else:
                cats.append({
                    "id": next_id("categories"),
                    "name": new_name.strip(),
                })
                save_data()
                st.success(f"Категория «{new_name.strip()}» добавлена.")

    if not cats:
        st.info("Категорий пока нет — добавьте первую или примените готовый шаблон выше.")
        return

    labels = {f"#{c.get('id')} · {c.get('name', '')}": c for c in cats}
    sel = st.selectbox("Выберите категорию", list(labels.keys()), key="cat_mgmt_sel")
    c = labels[sel]
    cid = c.get("id")
    index = next((i for i, x in enumerate(cats) if x.get("id") == cid), 0)

    new_name = st.text_input("Новое название", value=c.get("name", ""), key=f"cat_rename_{cid}")
    col1, col2, col3 = st.columns(3)
    if col1.button("Переименовать"):
        if not new_name.strip():
            st.error("Название не может быть пустым.")
        elif any(x.get("name", "").lower() == new_name.strip().lower() and x.get("id") != cid for x in cats):
            st.error("Такая категория уже существует.")
        else:
            c["name"] = new_name.strip()
            save_data()
            st.success("Категория переименована.")

    if col2.button("Вверх", disabled=(index == 0)):
        cats[index], cats[index - 1] = cats[index - 1], cats[index]
        save_data()
        st.rerun()
    if col3.button("Вниз", disabled=(index == len(cats) - 1)):
        cats[index], cats[index + 1] = cats[index + 1], cats[index]
        save_data()
        st.rerun()

    linked = len([p for p in data["products"] if p.get("category_id") == cid])
    confirm_del = st.checkbox(
        f"Подтверждаю удаление. Товаров в этой категории: {linked} (они останутся без категории).",
        key=f"cat_del_confirm_{cid}",
    )
    if st.button("Удалить категорию", disabled=not confirm_del):
        data["categories"] = [x for x in data["categories"] if x.get("id") != cid]
        for p in data["products"]:
            if p.get("category_id") == cid:
                p["category_id"] = None
                p["category"] = ""
        delete_photo(c.get("photo"))
        save_data()
        st.success(f"Категория «{c.get('name')}» удалена.")
        st.rerun()


# --- 10. ВХОД И НАСТРОЙКИ ---

DEMO_DAYS = 7


def check_demo_expiry():
    """Проверяет, истёк ли демо-доступ. Возвращает (expired, days_left)."""
    demo = data.get("demo")
    if not demo:
        data["demo"] = {"activated": datetime.now().isoformat(timespec="seconds")}
        save_data()
        demo = data["demo"]
    activated = datetime.fromisoformat(demo["activated"])
    elapsed = (datetime.now() - activated).days
    if elapsed >= DEMO_DAYS:
        if not demo.get("expired"):
            # Блокируем: меняем пароль на случайный
            salt = token_hex(16)
            data["auth"]["salt"] = salt
            data["auth"]["password_hash"] = hash_password(token_hex(16), salt)
            demo["expired"] = True
            save_data()
        return True, 0
    return False, DEMO_DAYS - elapsed


def demo_blocked_screen():
    """Экран блокировки демо-доступа."""
    st.markdown("""
    <div style="text-align:center; padding:40px 20px;">
        <h1 style="font-size:2.5rem; color:#0f172a;">Демо-доступ истёк</h1>
        <p style="font-size:1.2rem; color:#64748b; margin-top:16px;">
            7-дневный тестовый период завершён.<br>
            Для продолжения работы приобретите полную версию.
        </p>
    </div>
    """, unsafe_allow_html=True)
    st.markdown("---")
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        st.markdown(f"""
        ### Свяжитесь с нами
        **ВелоЦентр**
        - Телефон: **{SHOP_PHONE}**
        - Адрес: **{SHOP_ADDRESS}**
        - Сайт: запустите ВелоЦентр у себя в магазине!
        """)
        st.markdown("---")
        st.markdown("""
        **Что вы получите:**
        - Полная версия системы — без ограничений
        - Настройка под ваш магазин
        - Загрузка ваших товаров и клиентов
        - Обучение персонала
        - Поддержка и обновления
        """)


def login_screen():
    expired, days_left = check_demo_expiry()
    if expired:
        demo_blocked_screen()
        return

    st.title("ВелоЦентр")
    if days_left <= 2:
        st.warning(f"Демо-доступ истекает через {days_left} дн. Сохраните данные и свяжитесь с нами для покупки полной версии.")
    st.markdown("### Склад и CRM — вход для администратора")
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        with st.form("login_form"):
            username = st.text_input("Логин", value="velocentr")
            password = st.text_input("Пароль", value="demo", type="password")
            submitted = st.form_submit_button("Войти", type="primary", use_container_width=True)
            if submitted:
                auth = auth_credentials()
                if username == auth.get("username") and verify_password(
                    password, auth.get("salt", ""), auth.get("password_hash", "")
                ):
                    st.session_state["logged_in"] = True
                    st.session_state["username"] = username
                    st.rerun()
                else:
                    st.error("Неверный логин или пароль.")


def settings_section():
    st.subheader("Настройки")
    auth = auth_credentials()

    st.markdown("### Логин")
    with st.form("change_login"):
        new_username = st.text_input("Новый логин", value=auth.get("username", ""))
        if st.form_submit_button("Сохранить логин"):
            if new_username.strip():
                auth["username"] = new_username.strip()
                save_data()
                st.session_state["username"] = new_username.strip()
                st.success("Логин обновлён.")
            else:
                st.error("Логин не может быть пустым.")

    st.markdown("---")
    st.markdown("### Смена пароля")
    with st.form("change_password"):
        old_pass = st.text_input("Текущий пароль", type="password")
        new_pass = st.text_input("Новый пароль (минимум 4 символа)", type="password")
        new_pass2 = st.text_input("Повторите новый пароль", type="password")
        if st.form_submit_button("Сменить пароль"):
            if not verify_password(old_pass, auth.get("salt", ""), auth.get("password_hash", "")):
                st.error("Текущий пароль неверен.")
            elif len(new_pass) < 4:
                st.error("Новый пароль слишком короткий (минимум 4 символа).")
            elif new_pass != new_pass2:
                st.error("Пароли не совпадают.")
            else:
                salt = token_hex(16)
                auth["salt"] = salt
                auth["password_hash"] = hash_password(new_pass, salt)
                save_data()
                st.success("Пароль успешно изменён.")

    st.markdown("---")
    st.markdown("### Резервная копия")
    if DATA_FILE.exists():
        st.download_button(
            "Скачать резервную копию данных (data.json)",
            data=DATA_FILE.read_bytes(),
            file_name="velocentr_backup_data.json",
            mime="application/json",
        )
    photo_files = [f for f in PHOTOS_DIR.iterdir() if f.is_file()]
    if photo_files:
        buf = io.BytesIO()
        with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as z:
            for f in photo_files:
                z.write(f, f.name)
        st.download_button(
            "Скачать архив фотографий (photos.zip)",
            data=buf.getvalue(),
            file_name="velocentr_backup_photos.zip",
            mime="application/zip",
        )
    st.caption("Резервная копия = файл данных + архив фото. Храните их в надёжном месте.")

    st.markdown("---")
    st.markdown("### О системе")
    st.write(f"**{SHOP_NAME}** · Тамбов")
    st.write(f"{SHOP_PHONE} · {SHOP_ADDRESS}")
    st.write("Версия 1.3 · ВелоЦентр — склад, клиенты, задачи, звонки и аналитика для веломагазина.")


# --- 11. ГЛАВНОЕ ПРИЛОЖЕНИЕ ---

def inject_styles():
    """Единый фирменный стиль ВелоЦентр + тёмная тема + мобильная адаптация."""
    dark = st.session_state.get("dark_theme", False)
    if dark:
        bg, bg2, txt, txt2 = "#0f172a", "#1e293b", "#e2e8f0", "#94a3b8"
        card_bg, card_border = "rgba(255,255,255,0.06)", "rgba(255,255,255,0.12)"
        input_bg, input_border = "#1e293b", "rgba(255,255,255,0.2)"
    else:
        bg, bg2, txt, txt2 = "#f4f6f9", "#ffffff", "#0f172a", "#64748b"
        card_bg, card_border = "#ffffff", "#e2e8f0"
        input_bg, input_border = "#ffffff", "#e2e8f0"

    dark_css = ""
    if dark:
        dark_css = f"""
        /* === Тёмная тема — все тексты === */
        .stApp, .stApp > header, [data-testid="stAppViewContainer"] {{ background: {bg} !important; color: {txt} !important; }}
        .block-container {{ color: {txt} !important; }}
        .block-container p, .block-container span, .block-container label,
        .block-container li, .block-container td, .block-container th,
        .stMarkdown p, .stMarkdown span, .stMarkdown li, .stMarkdown td,
        .stCaption, [data-testid="stCaption"] {{ color: {txt2} !important; }}
        h1, h2, h3, h4, h5, h6 {{ color: {txt} !important; }}
        .stSelectbox label, .stTextInput label, .stNumberInput label,
        .stTextArea label, .stDateInput label, .stCheckbox label,
        .stRadio label, .stSlider label, .stFileUploader label {{ color: {txt} !important; }}
        .stSelectbox [data-baseweb="select"] {{ background: {input_bg} !important; }}
        .stSelectbox [data-baseweb="select"] * {{ color: {txt} !important; }}
        .stTextInput input, .stNumberInput input, .stTextArea textarea,
        .stDateInput input {{ background: {input_bg} !important; color: {txt} !important;
                              border-color: {input_border} !important; }}
        [data-baseweb="popover"] {{ background: {bg2} !important; }}
        [data-baseweb="popover"] * {{ color: {txt} !important; }}
        [data-baseweb="menu"] {{ background: {bg2} !important; }}
        [data-baseweb="menu"] * {{ color: {txt} !important; }}
        [data-baseweb="option"]:hover {{ background: {card_bg} !important; }}
        .stDataFrame {{ background: {bg2} !important; }}
        .stDataFrame * {{ color: {txt} !important; }}
        .stDataFrame [data-testid="stTable"] {{ background: {bg2} !important; }}
        div[data-testid="stMetric"] {{ background: {card_bg} !important; border-color: {card_border} !important; }}
        div[data-testid="stMetric"] label {{ color: {txt2} !important; }}
        div[data-testid="stMetric"] [data-testid="stMetricValue"] {{ color: {txt} !important; }}
        .stAlert {{ background: {card_bg} !important; color: {txt} !important; }}
        .stAlert * {{ color: {txt} !important; }}
        .stTabs [data-baseweb="tab"] {{ color: {txt2} !important; }}
        .stTabs [aria-selected="true"] {{ color: {txt} !important; }}
        .stTabs [data-baseweb="tab-border"] {{ background: {card_border} !important; }}
        .stExpander {{ background: {card_bg} !important; border-color: {card_border} !important; }}
        .stExpander * {{ color: {txt} !important; }}
        .stForm {{ background: {card_bg} !important; border-color: {card_border} !important; }}
        .stForm * {{ color: {txt} !important; }}
        [data-testid="stWidgetLabel"] {{ color: {txt} !important; }}
        .stCheckbox span, .stRadio span {{ color: {txt} !important; }}
        [data-testid="stHeader"] {{ background: {bg} !important; }}
        .kanban-card {{ background: {card_bg} !important; border-color: {card_border} !important; }}
        .kanban-card b {{ color: {txt} !important; }}
        .kanban-card span {{ color: {txt2} !important; }}
        """

    st.markdown(f"""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap');
    html, body, [class*="css"] {{ font-family: 'Inter', 'Segoe UI', sans-serif; }}
    .stApp {{ background: {bg}; }}
    .block-container {{ padding-top: 1rem; padding-bottom: 1rem; }}

    /* Скрытие шапки Streamlit (Deploy, hamburger) */
    header[data-testid="stHeader"] {{ display: none !important; }}
    #MainMenu {{ display: none !important; }}
    .stDeployButton {{ display: none !important; }}
    footer {{ display: none !important; }}
    .block-container > div:first-child {{ padding-top: 0 !important; }}

    /* Колокольчик — компактный, прижат влево */
    [data-testid="stSidebar"] button[kind="secondary"]:first-of-type {{
        background: rgba(255,255,255,0.08) !important;
        border: 1px solid rgba(255,255,255,0.15) !important;
        border-radius: 4px !important;
        font-size: 0.8rem !important;
        min-height: 28px !important;
        text-align: left !important;
        justify-content: flex-start !important;
        padding-left: 8px !important;
        color: #e2e8f0 !important;
    }}
    h1 {{ color: {txt}; font-weight: 800; letter-spacing: -0.02em; }}
    h2, h3 {{ color: {txt}; font-weight: 700; }}
    [data-testid="stSidebar"] {{ background: #0b1220; }}
    [data-testid="stSidebar"] * {{
        color: #f8fafc !important;
        border-color: rgba(255,255,255,0.25) !important;
        font-size: 1.05rem !important;
    }}
    [data-testid="stSidebar"] .stMarkdown {{ text-align: center; }}
    [data-testid="stSidebar"] .stMarkdown h1,
    [data-testid="stSidebar"] .stMarkdown h2,
    [data-testid="stSidebar"] .stMarkdown h3 {{ font-size: 1.5rem !important; font-weight: 800 !important; }}
    [data-testid="stSidebar"] label p {{ font-size: 1.05rem !important; font-weight: 600 !important; line-height: 1.4 !important; }}
    [data-testid="stSidebar"] .stRadio label {{ justify-content: center; }}
    [data-testid="stSidebar"] div[role="radiogroup"] label > div:first-child {{
        background: rgba(255,255,255,0.10); border-radius: 10px; padding: 8px 12px; margin-bottom: 6px;
    }}
    [data-testid="stSidebar"] [data-testid="stButton"] > button {{
        background: #1e293b !important; color: #f8fafc !important; border: 1px solid rgba(255,255,255,0.25) !important;
        font-size: 1rem !important; font-weight: 600 !important;
    }}
    div[data-testid="stMetric"] {{
        background: {card_bg}; border: 1px solid {card_border}; border-radius: 14px;
        padding: 14px 18px; box-shadow: 0 1px 3px rgba(15,23,42,0.06);
    }}
    div[data-testid="stMetric"] label {{ color: {txt2}; }}
    div[data-testid="stMetric"] [data-testid="stMetricValue"] {{ color: {txt}; font-weight: 800; }}
    [data-testid="stButton"] > button {{ border-radius: 10px; font-weight: 600; }}
    [data-testid="stButton"] > button[kind="primary"] {{ background: #0d9488; }}
    [data-testid="stDataFrame"] {{ border-radius: 12px; overflow: hidden; border: 1px solid {card_border}; }}
    .stAlert {{ border-radius: 10px; }}
    [data-testid="stSidebar"] [data-testid="stButton"] > button {{ background: #1e293b; color: #f8fafc; border: none; }}

    .kanban-col {{ background: {card_bg}; border: 1px solid {card_border}; border-radius: 12px;
                   padding: 12px; min-height: 200px; }}
    .kanban-card {{ background: {card_bg}; border: 1px solid {card_border}; border-radius: 8px;
                    padding: 10px 12px; margin-bottom: 8px; }}
    .kanban-card b {{ color: {txt}; font-size: 0.9rem; }}
    .kanban-card span {{ color: {txt2}; font-size: 0.8rem; }}

    {dark_css}

    @media (max-width: 768px) {{
        .block-container {{ padding: 0.8rem 0.6rem !important; }}
        h1 {{ font-size: 1.4rem !important; }}
        h2 {{ font-size: 1.15rem !important; }}
        h3 {{ font-size: 1rem !important; }}
        div[data-testid="stMetric"] {{ padding: 10px 12px; }}
        div[data-testid="stMetric"] label {{ font-size: 0.75rem !important; }}
        div[data-testid="stMetric"] [data-testid="stMetricValue"] {{ font-size: 1.1rem !important; }}
        [data-testid="stDataFrame"] {{ font-size: 0.8rem; }}
        div[data-testid="stButton"] > button {{
            padding: 0.45rem 1rem !important; font-size: 0.9rem !important; min-height: 40px !important;
        }}
    }}
    </style>
    """, unsafe_allow_html=True)


def render_notifications():
    """Уведомления — компактный колокольчик и кликабельные задачи."""
    today = datetime.now().date()
    urgent = [t for t in data.get("tasks", [])
              if t.get("status") not in DONE_STATUSES
              and parse_date(t.get("due_date"))
              and parse_date(t.get("due_date")) <= today + timedelta(days=1)]

    count = len(urgent)
    is_open = st.session_state.get("notif_open", False)

    if count == 0:
        return

    icon = chr(128276)  # 🔔
    arrow = " v" if is_open else " >"
    if st.sidebar.button(f"  {icon} {count}{arrow}", key="notif_toggle", use_container_width=True):
        st.session_state["notif_open"] = not is_open
        st.rerun()

    if is_open:
        for t in urgent[:10]:
            due = parse_date(t.get("due_date"))
            desc = t.get('description', '')[:25]
            tid = t.get("id")
            client = get_client_name(t.get("client_id"))
            if due and due < today:
                tag = "!"
            elif due and due == today:
                tag = ">"
            else:
                tag = "~"
            if st.sidebar.button(f"[{tag}] {desc}", key=f"notif_{tid}", use_container_width=True):
                st.session_state["edit_task_id"] = tid
                st.session_state["main_menu"] = "CRM"
                st.rerun()


def render_sidebar():
    """Боковая панель — лого по центру, демо-таймер, меню, выход."""
    st.sidebar.markdown("""
    <div style="text-align:center; padding:10px 0 4px 0;">
        <span style="font-size:1.1rem; font-weight:800; color:#f8fafc;">ВелоЦентр</span>
    </div>
    """, unsafe_allow_html=True)

    # Демо-таймер — по центру, компактный
    demo = data.get("demo", {})
    if demo.get("activated") and not demo.get("expired"):
        activated = datetime.fromisoformat(demo["activated"])
        days_left = DEMO_DAYS - (datetime.now() - activated).days
        if days_left <= 2:
            st.sidebar.markdown(f"""
            <div style="text-align:center; background:rgba(239,68,68,0.2); border:1px solid rgba(239,68,68,0.4);
                        border-radius:10px; padding:6px; margin:4px 0 10px 0;">
                <span style="font-size:0.8rem; color:#fca5a5;">Демо: <b>{days_left} дн.</b></span>
            </div>
            """, unsafe_allow_html=True)
        else:
            st.sidebar.markdown(f"""
            <div style="text-align:center; background:rgba(45,212,191,0.1); border:1px solid rgba(45,212,191,0.2);
                        border-radius:10px; padding:6px; margin:4px 0 10px 0;">
                <span style="font-size:0.8rem; color:#94a3b8;">Демо: <b style="color:#2dd4bf;">{days_left} дн.</b></span>
            </div>
            """, unsafe_allow_html=True)

    st.sidebar.markdown("---")

    menu = st.sidebar.radio(
        "Разделы",
        ("Дашборд", "Склад / Товары", "CRM", "Категории", "Настройки"),
        key="main_menu",
    )

    st.sidebar.markdown("---")

    # Тёмная тема
    dark = st.sidebar.toggle("Тёмная тема", value=st.session_state.get("dark_theme", False), key="dark_toggle")
    if dark != st.session_state.get("dark_theme", False):
        st.session_state["dark_theme"] = dark
        st.rerun()

    st.sidebar.markdown(f"""
    <div style="text-align:center; color:#64748b; font-size:0.75rem; margin-top:8px;">
        {st.session_state.get('username', 'velocentr')}
    </div>
    """, unsafe_allow_html=True)
    if st.sidebar.button("Выйти", use_container_width=True):
        st.session_state["logged_in"] = False
        st.rerun()

    return menu


def render_global_search():
    """Глобальный поиск — ищет по клиентам, задачам, звонкам."""
    col1, col2 = st.columns([5, 1])
    with col1:
        search = st.text_input("", placeholder="Поиск по клиентам, задачам, звонкам...", key="global_search", label_visibility="collapsed")
    with col2:
        if st.button("Добавить", type="primary", use_container_width=True):
            st.session_state["quick_add"] = True
            st.rerun()

    if search and len(search) >= 2:
        q = search.lower()
        results = []

        for c in data.get("clients", []):
            if q in f"{c.get('name','')} {c.get('phone','')} {c.get('order_number','')}".lower():
                results.append(("Клиент", f"{c.get('name', '')} ({c.get('phone', '')})", c.get("id"), "client"))

        for t in data.get("tasks", []):
            if q in f"{t.get('description','')} {get_client_name(t.get('client_id'))}".lower():
                results.append(("Задача", f"{t.get('description', '')[:50]} — {get_client_name(t.get('client_id'))}", t.get("id"), "task"))

        for x in data.get("calls", []):
            if q in f"{x.get('note','')} {get_client_name(x.get('client_id'))} {x.get('result','')}".lower():
                results.append(("Звонок", f"{get_client_name(x.get('client_id'))} — {x.get('result', '')}", x.get("id"), "call"))

        if results:
            for icon_label, text, item_id, item_type in results[:10]:
                col1, col2 = st.columns([6, 1])
                with col1:
                    st.caption(f"{icon_label} {text}")
                with col2:
                    if st.button("→", key=f"search_{item_type}_{item_id}", help="Открыть"):
                        if item_type == "client":
                            st.session_state["edit_client_id"] = item_id
                        elif item_type == "task":
                            st.session_state["edit_task_id"] = item_id
                        elif item_type == "call":
                            st.session_state["edit_call_id"] = item_id
                        st.session_state["main_menu"] = "CRM"
                        st.rerun()
        else:
            st.caption("Ничего не найдено.")


def render_quick_add():
    """Быстрое добавление — задача/звонок/клиент за 5 сек."""
    st.markdown("### Быстрое добавление")
    tab1, tab2, tab3 = st.tabs(["Задача", "Звонок", "Клиент"])

    with tab1:
        desc = st.text_input("Что сделать", key="qa_task_desc")
        client_opts = {"Без привязки": None}
        client_opts.update({c.get("name", ""): c.get("id") for c in data.get("clients", [])})
        client = st.selectbox("Клиент", list(client_opts.keys()), key="qa_task_client")
        col1, col2 = st.columns(2)
        due = col1.date_input("Срок", value=datetime.now().date() + timedelta(days=3), key="qa_task_due")
        if col2.button("Создать задачу", type="primary", use_container_width=True):
            if desc.strip():
                data["tasks"].append({
                    "id": next_id("tasks"), "description": desc.strip(),
                    "client_id": client_opts[client], "due_date": due.isoformat(),
                    "status": "Новая", "created_at": datetime.now().isoformat(timespec="seconds"),
                })
                save_data()
                st.success("Задача создана!")
                st.session_state["quick_add"] = False
                st.rerun()

    with tab2:
        client_opts = {"Без привязки": None}
        client_opts.update({c.get("name", ""): c.get("id") for c in data.get("clients", [])})
        client = st.selectbox("Клиент", list(client_opts.keys()), key="qa_call_client")
        result = st.selectbox("Результат", CALL_RESULTS, key="qa_call_result")
        note = st.text_input("Заметка", key="qa_call_note")
        if st.button("Записать звонок", type="primary", key="qa_call_save"):
            data["calls"].append({
                "id": next_id("calls"), "client_id": client_opts[client],
                "date": datetime.now().date().isoformat(), "result": result,
                "note": note.strip(), "created_at": datetime.now().isoformat(timespec="seconds"),
            })
            save_data()
            st.success("Звонок записан!")
            st.session_state["quick_add"] = False
            st.rerun()

    with tab3:
        name = st.text_input("Имя", key="qa_client_name")
        phone = st.text_input("Телефон", key="qa_client_phone")
        if st.button("Добавить клиента", type="primary", key="qa_client_save"):
            if name.strip() and phone.strip():
                data["clients"].append({
                    "id": next_id("clients"), "name": name.strip(),
                    "phone": phone.strip(), "order_number": "", "comment": "",
                    "created_at": datetime.now().isoformat(timespec="seconds"),
                })
                save_data()
                st.success(f"Клиент «{name.strip()}» добавлен!")
                st.session_state["quick_add"] = False
                st.rerun()

    if st.button("✕ Закрыть"):
        st.session_state["quick_add"] = False
        st.rerun()


def main():
    st.set_page_config(page_title="ВелоЦентр: склад и CRM", page_icon="🚲", layout="wide")
    load_data()
    inject_styles()

    if not st.session_state.get("logged_in"):
        login_screen()
        return

    render_notifications()
    menu = render_sidebar()

    # Глобальный поиск и быстрое добавление — на каждой странице
    render_global_search()

    # Быстрое добавление
    if st.session_state.get("quick_add"):
        render_quick_add()
        st.markdown("---")

    if menu == "Дашборд":
        display_dashboard()
    elif menu == "Склад / Товары":
        display_inventory()
        product_editor()
    elif menu == "Категории":
        display_categories_overview()
        categories_presets()
        categories_editor()
    elif menu == "Настройки":
        settings_section()
    elif menu == "CRM":
        crm_page()
    

if __name__ == "__main__":
    main()
