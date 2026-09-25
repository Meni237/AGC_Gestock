# AGC Assurances — Gestion de Stock (version Streamlit / Python)

Application de gestion de stock pour **AGC Assurances** (*Le gage de votre sécurité*),
portée en **Python / Streamlit** avec base de données **SQLite** (créée et remplie
automatiquement au premier lancement — aucune installation manuelle).

> La version **PHP / MySQL** (pour XAMPP) reste disponible dans le dossier `agc-inventory`.

## 1. Lancer localement

```bash
pip install -r requirements.txt
streamlit run app.py
```

**Compte administrateur unique :** `admin@agc-assurances.com` / `AGC@2026`

## 2. Déployer sur Streamlit Community Cloud (gratuit)

1. Créer un dépôt GitHub et y téléverser : `app.py`, `database.py`,
   `translations.py`, `requirements.txt`, le dossier `.streamlit/`.
2. Aller sur <https://share.streamlit.io> → **New app**.
3. Sélectionner le dépôt, la branche `main` et le fichier `app.py` → **Deploy**.

> Remarque : sur Streamlit Cloud, les données (SQLite) sont réinitialisées à chaque
> redémarrage de l'application. Pour une démonstration c'est suffisant ; pour des
> données permanentes, héberger l'application sur un serveur ou brancher une base externe.

## 3. Fonctionnalités (identiques à la version PHP)

| Module | Description |
|---|---|
| **Tableau de bord** | Total stock, alertes de stock faible, dernières sorties, actions rapides |
| **Produits** | Grille de cartes avec image (ou icône par défaut), recherche, filtre par catégorie, IDs auto-incrémentés, interdiction des doublons : **« Ce code produit existe déjà. »** |
| **Catégories** | CRUD complet avec protection « utilisée par des produits » |
| **Sorties de stock** | Utilisateur destinataire, article, quantité retirée, date et heure ; stock décrémenté automatiquement, contrôle de disponibilité |
| **Utilisateurs** | Annuaire interne (entités de référence, sans connexion ni rôle) |
| **Registre mensuel** | Historique groupé par mois, document A4 imprimable / PDF + téléchargement HTML |
| **Paramètres** | Nom du système, slogan, disposition (barre latérale / supérieure), couleur d'accent, langue, compte administrateur |
| **Langues** | Bascule FR / EN partout (message de doublon volontairement conservé en français) |

Aucun champ fournisseur, aucun champ prix.

## 4. Fichiers

```
app.py            Application Streamlit (toutes les pages)
database.py       SQLite : schéma, données initiales, toutes les requêtes
translations.py   Textes français / anglais
requirements.txt  Dépendances (streamlit)
.streamlit/       Thème et configuration du serveur
```

Sécurité : mots de passe hachés (PBKDF2-SHA256), requêtes paramétrées,
échappement HTML, validation du stock côté base.

---
© AGC Assurances — Assurances Générales du Cameroun. Usage interne.
