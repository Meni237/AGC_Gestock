import hashlib
import hmac
import os
import sqlite3
from datetime import datetime, timedelta

DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "agc_inventory.db")


def _conn():
    conn = sqlite3.connect(DB_PATH, timeout=20)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    return conn


def q(sql, params=()):
    conn = _conn()
    try:
        return conn.execute(sql, params).fetchall()
    finally:
        conn.close()


def one(sql, params=()):
    rows = q(sql, params)
    return rows[0] if rows else None


def exec(sql, params=()):
    conn = _conn()
    try:
        cur = conn.execute(sql, params)
        conn.commit()
        return cur.lastrowid
    finally:
        conn.close()


def hash_password(password):
    salt = os.urandom(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, 120000)
    return salt.hex() + "$" + digest.hex()


def check_password(password, stored):
    try:
        salt_hex, digest_hex = stored.split("$", 1)
        digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), bytes.fromhex(salt_hex), 120000)
        return hmac.compare_digest(digest.hex(), digest_hex)
    except (ValueError, AttributeError):
        return False


SCHEMA = """
CREATE TABLE IF NOT EXISTS admins (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    email TEXT NOT NULL UNIQUE,
    password TEXT NOT NULL,
    language TEXT NOT NULL DEFAULT 'fr'
);
CREATE TABLE IF NOT EXISTS settings (
    id INTEGER PRIMARY KEY,
    app_name TEXT NOT NULL DEFAULT 'AGC Assurances',
    tagline TEXT NOT NULL DEFAULT 'Le gage de votre sécurité',
    accent TEXT NOT NULL DEFAULT 'red',
    layout TEXT NOT NULL DEFAULT 'sidebar'
);
CREATE TABLE IF NOT EXISTS categories (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    description TEXT DEFAULT ''
);
CREATE TABLE IF NOT EXISTS products (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    code TEXT NOT NULL UNIQUE,
    name TEXT NOT NULL,
    category_id INTEGER DEFAULT 0,
    stock INTEGER NOT NULL DEFAULT 0,
    low_stock_at INTEGER NOT NULL DEFAULT 5,
    image_blob BLOB,
    image_mime TEXT DEFAULT ''
);
CREATE TABLE IF NOT EXISTS app_users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    full_name TEXT NOT NULL,
    service TEXT DEFAULT '',
    email TEXT DEFAULT '',
    phone TEXT DEFAULT ''
);
CREATE TABLE IF NOT EXISTS dispatches (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    app_user_id INTEGER NOT NULL,
    product_id INTEGER NOT NULL,
    quantity INTEGER NOT NULL,
    dispatched_at TEXT NOT NULL
);
"""

CATEGORIES = [
    ("Informatique", "Ordinateurs, écrans et accessoires"),
    ("Mobilier de bureau", "Chaises, tables et rangements"),
    ("Fournitures de bureau", "Papeterie et consommables"),
    ("Équipements réseau", "Routeurs, switchs et câblage"),
]

PRODUCTS = [
    ("INF-001", "Ordinateur portable Dell Latitude", 1, 12, 4),
    ("INF-002", "Écran 24 pouces", 1, 3, 5),
    ("INF-003", "Clavier sans fil", 1, 25, 8),
    ("INF-004", "Souris ergonomique", 1, 0, 5),
    ("INF-005", "Station d'accueil USB-C", 1, 6, 3),
    ("MOB-001", "Chaise de bureau ergonomique", 2, 9, 4),
    ("MOB-002", "Bureau 140 cm", 2, 5, 2),
    ("FOU-001", "Rame papier A4 (500 feuilles)", 3, 48, 20),
    ("FOU-002", "Cartouche encre noire", 3, 7, 10),
    ("FOU-003", "Stylo roller (boîte de 50)", 3, 15, 6),
    ("RES-001", "Routeur Wi-Fi entreprise", 4, 4, 3),
    ("RES-002", "Câble RJ45 (3 m)", 4, 32, 10),
]

USERS = [
    ("Marie-Claire Ngo Bassong", "Comptabilité", "mc.ngobassong@agc-assurances.com", "+237 690 11 45 78"),
    ("Jean-Paul Etoundi", "Sinistres", "jp.etoundi@agc-assurances.com", "+237 691 22 36 49"),
    ("Sandrine Abena", "Ressources Humaines", "s.abena@agc-assurances.com", "+237 694 55 81 23"),
    ("Cyrille Foumane", "Commercial", "c.foumane@agc-assurances.com", "+237 677 90 14 65"),
    ("Brice Tchoumi", "Informatique", "b.tchoumi@agc-assurances.com", "+237 699 63 27 08"),
]

DISPATCHES = [
    (1, 8, 5, 2), (2, 2, 1, 4), (5, 3, 4, 6), (3, 6, 1, 9),
    (4, 9, 2, 12), (1, 12, 6, 34), (5, 11, 1, 38), (2, 1, 2, 41),
]


def init_db():
    conn = _conn()
    try:
        conn.executescript(SCHEMA)
        conn.commit()
    finally:
        conn.close()
    if one("SELECT id FROM admins LIMIT 1") is None:
        seed()


def seed():
    exec("INSERT INTO settings (id) VALUES (1)")
    exec("INSERT INTO admins (name, email, password, language) VALUES (?, ?, ?, ?)",
         ("Administrateur AGC", "admin@agc-assurances.com", hash_password("AGC@2026"), "fr"))
    for name, desc in CATEGORIES:
        exec("INSERT INTO categories (name, description) VALUES (?, ?)", (name, desc))
    for code, name, cat, stock, low in PRODUCTS:
        exec("INSERT INTO products (code, name, category_id, stock, low_stock_at) VALUES (?, ?, ?, ?, ?)",
             (code, name, cat, stock, low))
    for full_name, service, email, phone in USERS:
        exec("INSERT INTO app_users (full_name, service, email, phone) VALUES (?, ?, ?, ?)",
             (full_name, service, email, phone))
    for user_id, product_id, qty, days_ago in DISPATCHES:
        when = (datetime.now() - timedelta(days=days_ago)).strftime("%Y-%m-%d %H:%M:%S")
        exec("INSERT INTO dispatches (app_user_id, product_id, quantity, dispatched_at) VALUES (?, ?, ?, ?)",
             (user_id, product_id, qty, when))


def get_admin_by_email(email):
    return one("SELECT * FROM admins WHERE email = ?", (email,))


def update_admin_language(admin_id, language):
    exec("UPDATE admins SET language = ? WHERE id = ?", (language, admin_id))


def update_admin_account(admin_id, name, email, password=None):
    if password:
        exec("UPDATE admins SET name = ?, email = ?, password = ? WHERE id = ?",
             (name, email, hash_password(password), admin_id))
    else:
        exec("UPDATE admins SET name = ?, email = ? WHERE id = ?", (name, email, admin_id))


def get_settings():
    row = one("SELECT * FROM settings WHERE id = 1")
    if row:
        return dict(row)
    return {"app_name": "AGC Assurances", "tagline": "Le gage de votre sécurité",
            "accent": "red", "layout": "sidebar"}


def update_settings(app_name, tagline, accent, layout):
    exec("UPDATE settings SET app_name = ?, tagline = ?, accent = ?, layout = ? WHERE id = 1",
         (app_name, tagline, accent, layout))


def list_categories():
    return q("SELECT c.*, (SELECT COUNT(*) FROM products p WHERE p.category_id = c.id) AS product_count "
             "FROM categories c ORDER BY c.id DESC")


def add_category(name, description):
    return exec("INSERT INTO categories (name, description) VALUES (?, ?)", (name, description))


def update_category(cat_id, name, description):
    exec("UPDATE categories SET name = ?, description = ? WHERE id = ?", (name, description, cat_id))


def category_in_use(cat_id):
    return one("SELECT COUNT(*) AS n FROM products WHERE category_id = ?", (cat_id,))["n"] > 0


def delete_category(cat_id):
    exec("DELETE FROM categories WHERE id = ?", (cat_id,))


def list_products(search="", category_id=0):
    sql = ("SELECT p.*, c.name AS category_name FROM products p "
           "LEFT JOIN categories c ON c.id = p.category_id "
           "WHERE (p.name LIKE ? OR p.code LIKE ?)")
    params = ["%" + search + "%", "%" + search + "%"]
    if category_id:
        sql += " AND p.category_id = ?"
        params.append(category_id)
    sql += " ORDER BY p.id DESC"
    return q(sql, tuple(params))


def get_product(product_id):
    return one("SELECT * FROM products WHERE id = ?", (product_id,))


def code_exists(code, exclude_id=0):
    return one("SELECT id FROM products WHERE code = ? AND id <> ?", (code, exclude_id)) is not None


def add_product(code, name, category_id, stock, low_stock_at, image_blob, image_mime):
    return exec("INSERT INTO products (code, name, category_id, stock, low_stock_at, image_blob, image_mime) "
                "VALUES (?, ?, ?, ?, ?, ?, ?)",
                (code, name, category_id, stock, low_stock_at, image_blob, image_mime))


def update_product(product_id, code, name, category_id, stock, low_stock_at, image_blob, image_mime):
    if image_blob is not None:
        exec("UPDATE products SET code = ?, name = ?, category_id = ?, stock = ?, low_stock_at = ?, "
             "image_blob = ?, image_mime = ? WHERE id = ?",
             (code, name, category_id, stock, low_stock_at, image_blob, image_mime, product_id))
    else:
        exec("UPDATE products SET code = ?, name = ?, category_id = ?, stock = ?, low_stock_at = ? "
             "WHERE id = ?",
             (code, name, category_id, stock, low_stock_at, product_id))


def product_in_use(product_id):
    return one("SELECT COUNT(*) AS n FROM dispatches WHERE product_id = ?", (product_id,))["n"] > 0


def delete_product(product_id):
    if product_in_use(product_id):
        return False
    exec("DELETE FROM products WHERE id = ?", (product_id,))
    return True


def list_users(search=""):
    sql = ("SELECT u.*, (SELECT COUNT(*) FROM dispatches d WHERE d.app_user_id = u.id) AS dispatch_count "
           "FROM app_users u")
    params = []
    if search:
        sql += " WHERE u.full_name LIKE ? OR u.service LIKE ? OR u.email LIKE ?"
        params = ["%" + search + "%"] * 3
    sql += " ORDER BY u.full_name"
    return q(sql, tuple(params))


def add_user(full_name, service, email, phone):
    return exec("INSERT INTO app_users (full_name, service, email, phone) VALUES (?, ?, ?, ?)",
                (full_name, service, email, phone))


def update_user(user_id, full_name, service, email, phone):
    exec("UPDATE app_users SET full_name = ?, service = ?, email = ?, phone = ? WHERE id = ?",
         (full_name, service, email, phone, user_id))


def user_in_use(user_id):
    return one("SELECT COUNT(*) AS n FROM dispatches WHERE app_user_id = ?", (user_id,))["n"] > 0


def delete_user(user_id):
    if user_in_use(user_id):
        return False
    exec("DELETE FROM app_users WHERE id = ?", (user_id,))
    return True


def create_dispatch(app_user_id, product_id, quantity, when_str):
    user = one("SELECT id FROM app_users WHERE id = ?", (app_user_id,))
    product = one("SELECT stock FROM products WHERE id = ?", (product_id,))
    if user is None or product is None or quantity < 1:
        return ("fields", 0)
    if quantity > product["stock"]:
        return ("stock", product["stock"])
    exec("INSERT INTO dispatches (app_user_id, product_id, quantity, dispatched_at) VALUES (?, ?, ?, ?)",
         (app_user_id, product_id, quantity, when_str))
    exec("UPDATE products SET stock = stock - ? WHERE id = ?", (quantity, product_id))
    return None


def recent_dispatches(limit=12):
    return q("SELECT d.*, u.full_name, u.service, p.name AS product, p.code "
             "FROM dispatches d "
             "JOIN app_users u ON u.id = d.app_user_id "
             "JOIN products p ON p.id = d.product_id "
             "ORDER BY d.dispatched_at DESC LIMIT ?", (limit,))


def dispatch_months():
    return [r["ym"] for r in
            q("SELECT DISTINCT strftime('%Y-%m', dispatched_at) AS ym FROM dispatches ORDER BY ym DESC")]


def month_dispatches(ym):
    return q("SELECT d.*, u.full_name, u.service, p.name AS product, p.code "
             "FROM dispatches d "
             "JOIN app_users u ON u.id = d.app_user_id "
             "JOIN products p ON p.id = d.product_id "
             "WHERE strftime('%Y-%m', d.dispatched_at) = ? "
             "ORDER BY d.dispatched_at ASC", (ym,))


def low_stock_products(limit=8):
    return q("SELECT * FROM products WHERE stock <= low_stock_at ORDER BY stock ASC LIMIT ?", (limit,))


def count_products():
    return one("SELECT COUNT(*) AS n FROM products")["n"]


def count_stock_units():
    return one("SELECT COALESCE(SUM(stock), 0) AS n FROM products")["n"]


def count_categories():
    return one("SELECT COUNT(*) AS n FROM categories")["n"]


def count_users():
    return one("SELECT COUNT(*) AS n FROM app_users")["n"]
