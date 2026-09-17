import streamlit as st
import pandas as pd
import sqlite3
import hashlib
import os
import streamlit.components.v1 as components

# 1. Configuration de la page
st.set_page_config(
    page_title="AGC_Gestock",
    page_icon="📦",
    layout="wide",
    initial_sidebar_state="expanded"
)

DB_PATH = "gestock.db"

def get_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    default_pass = hashlib.sha256("admin123".encode()).hexdigest()
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            nom_complet TEXT NOT NULL
        )
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS produits (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            code_produit TEXT UNIQUE NOT NULL,
            nom_produit TEXT NOT NULL,
            categorie TEXT,
            quantite INTEGER DEFAULT 0,
            stock_seuil INTEGER DEFAULT 5
        )
    """)
    cursor.execute("""
        INSERT OR IGNORE INTO users (username, password_hash, nom_complet)
        VALUES (?, ?, ?)
    """, ("admin", default_pass, "Administrateur AGC"))
    conn.commit()
    conn.close()

init_db()

def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()

# 2. Session & Authentification
if "logged_in" not in st.session_state:
    st.session_state["logged_in"] = False

if not st.session_state["logged_in"]:
    # Affichage du logo sur la page de connexion si présent
    if os.path.exists("actifs/logo_agc.JPEG"):
        st.image("actifs/logo_agc.JPEG", width=150)
    elif os.path.exists("assets/logo_agc.JPEG"):
        st.image("assets/logo_agc.JPEG", width=150)

    st.markdown("<h2 style='text-align: center;'>🔒 AGC_Gestock - Connexion</h2>", unsafe_allow_html=True)
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        with st.form("login_form"):
            username = st.text_input("Identifiant")
            password = st.text_input("Mot de passe", type="password")
            submit = st.form_submit_button("Se connecter", use_container_width=True)
            
            if submit:
                hashed_p = hash_password(password)
                conn = get_connection()
                cursor = conn.cursor()
                cursor.execute(
                    "SELECT nom_complet FROM users WHERE username = ? AND password_hash = ?",
                    (username, hashed_p)
                )
                res = cursor.fetchone()
                conn.close()
                
                if res:
                    st.session_state["logged_in"] = True
                    st.session_state["nom_complet"] = res["nom_complet"]
                    st.rerun()
                else:
                    st.error("Identifiant ou mot de passe incorrect.")
else:
    # 3. Barre Latérale avec Logo
    logo_path = "actifs/logo_agc.JPEG" if os.path.exists("actifs/logo_agc.JPEG") else "assets/logo_agc.JPEG"
    if os.path.exists(logo_path):
        st.sidebar.image(logo_path, use_container_width=True)
    
    st.sidebar.title(f"👤 {st.session_state.get('nom_complet', 'Admin')}")
    if st.sidebar.button("Déconnexion", use_container_width=True):
        st.session_state["logged_in"] = False
        st.rerun()

    st.title("📦 AGC_Gestock - Gestion de Stock")
    
    tab1, tab2, tab3 = st.tabs(["📊 État du Stock", "🖥️ Tableau de Bord HTML", "➕ Ajouter Produit"])
    
    with tab1:
        conn = get_connection()
        df_stock = pd.read_sql_query("SELECT * FROM produits", conn)
        conn.close()
        
        if not df_stock.empty:
            st.dataframe(df_stock, use_container_width=True, hide_index=True)
        else:
            st.info("Aucun produit enregistré.")

    with tab2:
        # Chargement du template HTML personnalisé
        html_file = "modèles/tableau de bord.html" if os.path.exists("modèles/tableau de bord.html") else "templates/tableau de bord.html"
        if os.path.exists(html_file):
            with open(html_file, "r", encoding="utf-8") as f:
                html_content = f.read()
            components.html(html_content, height=600, scrolling=True)
        else:
            st.warning("Fichier HTML du tableau de bord introuvable.")

    with tab3:
        with st.form("add_product"):
            code_p = st.text_input("Code Produit")
            nom_p = st.text_input("Nom du Produit")
            cat_p = st.text_input("Catégorie")
            qte = st.number_input("Quantité Initial", min_value=0, value=10)
            seuil = st.number_input("Seuil d'Alerte", min_value=1, value=5)
            
            if st.form_submit_button("Ajouter au Stock", use_container_width=True):
                if code_p and nom_p:
                    try:
                        conn = get_connection()
                        cursor = conn.cursor()
                        cursor.execute("""
                            INSERT INTO produits (code_produit, nom_produit, categorie, quantite, stock_seuil) 
                            VALUES (?, ?, ?, ?, ?)
                        """, (code_p, nom_p, cat_p, qte, seuil))
                        conn.commit()
                        conn.close()
                        st.success("Produit ajouté !")
                        st.rerun()
                    except sqlite3.IntegrityError:
                        st.error("Ce code produit existe déjà.")
                    except Exception as e:
                        st.error(f"Erreur : {e}")
                else:
                    st.warning("Veuillez remplir les champs obligatoires.")
