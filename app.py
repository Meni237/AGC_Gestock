import streamlit as st
import pandas as pd
from sqlalchemy import create_engine, text
import hashlib

# 1. Configuration de la page
st.set_page_config(
    page_title="AGC_Gestock",
    page_icon="📦",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# 2. Base de données SQLite
DB_PATH = "gestock.db"
engine = create_engine(f"sqlite:///{DB_PATH}")

def init_db():
    with engine.connect() as conn:
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL,
                password_hash TEXT NOT NULL,
                nom_complet TEXT NOT NULL
            );
        """))
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS produits (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                code_produit TEXT UNIQUE NOT NULL,
                nom_produit TEXT NOT NULL,
                categorie TEXT,
                quantite INTEGER DEFAULT 0,
                stock_seuil INTEGER DEFAULT 5
            );
        """))
        default_pass = hashlib.sha256("admin123".encode()).hexdigest()
        conn.execute(text(f"""
            INSERT OR IGNORE INTO users (username, password_hash, nom_complet)
            VALUES ('admin', '{default_pass}', 'Administrateur AGC');
        """))
        conn.commit()

init_db()

def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()

# 3. Session & Authentification
if "logged_in" not in st.session_state:
    st.session_state["logged_in"] = False

if not st.session_state["logged_in"]:
    st.markdown("<h2 style='text-align: center;'>🔒 AGC_Gestock - Connexion</h2>", unsafe_allow_html=True)
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        with st.form("login_form"):
            username = st.text_input("Identifiant")
            password = st.text_input("Mot de passe", type="password")
            submit = st.form_submit_button("Se connecter", use_container_width=True)
            
            if submit:
                hashed_p = hash_password(password)
                with engine.connect() as conn:
                    res = conn.execute(
                        text("SELECT nom_complet FROM users WHERE username = :u AND password_hash = :p"),
                        {"u": username, "p": hashed_p}
                    ).fetchone()
                    if res:
                        st.session_state["logged_in"] = True
                        st.session_state["nom_complet"] = res[0]
                        st.rerun()
                    else:
                        st.error("Identifiant ou mot de passe incorrect.")
else:
    # 4. Application Principale
    st.sidebar.title(f"👤 {st.session_state.get('nom_complet', 'Admin')}")
    if st.sidebar.button("Déconnexion"):
        st.session_state["logged_in"] = False
        st.rerun()

    st.title("📦 AGC_Gestock - Gestion de Stock")
    
    tab1, tab2 = st.tabs(["📊 État du Stock", "➕ Ajouter Produit"])
    
    with tab1:
        df_stock = pd.read_sql("SELECT * FROM produits", engine)
        if not df_stock.empty:
            st.dataframe(df_stock, use_container_width=True, hide_index=True)
        else:
            st.info("Aucun produit enregistré.")

    with tab2:
        with st.form("add_product"):
            code_p = st.text_input("Code Produit")
            nom_p = st.text_input("Nom du Produit")
            cat_p = st.text_input("Catégorie")
            qte = st.number_input("Quantité Initial", min_value=0, value=10)
            seuil = st.number_input("Seuil d'Alerte", min_value=1, value=5)
            
            if st.form_submit_button("Ajouter", use_container_width=True):
                if code_p and nom_p:
                    try:
                        with engine.connect() as conn:
                            conn.execute(
                                text("INSERT INTO produits (code_produit, nom_produit, categorie, quantite, stock_seuil) VALUES (:c, :n, :cat, :q, :s)"),
                                {"c": code_p, "n": nom_p, "cat": cat_p, "q": qte, "s": seuil}
                            )
                            conn.commit()
                        st.success("Produit ajouté !")
                        st.rerun()
                    except Exception:
                        st.error("Ce code produit existe déjà.")
                else:
                    st.warning("Veuillez remplir les champs obligatoires.")
