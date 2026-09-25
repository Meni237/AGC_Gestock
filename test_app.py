import sys
from datetime import datetime

sys.path.insert(0, ".")

from streamlit.testing.v1 import AppTest
import streamlit.testing.v1.element_tree as et

import database as db

FAILED = []


def check(name, condition, detail=""):
    print("[%s] %s %s" % ("PASS" if condition else "FAIL", name, detail))
    if not condition:
        FAILED.append(name)


# (AppTest compatibility fix is now built into app.py via current_lang())

at = AppTest.from_file("app.py", default_timeout=30)
at.run()
check("app boots without exception", not at.exception, str(at.exception)[:200])

at.text_input(key="login_email").set_value("admin@agc-assurances.com")
at.text_input(key="login_password").set_value("wrongpass")
at.button(key="login_submit").click().run()
check("wrong password rejected", any("Mot de passe incorrect." in e.value for e in at.error))

at.text_input(key="login_email").set_value("nobody@x.com")
at.button(key="login_submit").click().run()
check("unknown email rejected", any("Aucun compte administrateur" in e.value for e in at.error))

at.text_input(key="login_email").set_value("admin@agc-assurances.com")
at.text_input(key="login_password").set_value("AGC@2026")
at.button(key="login_submit").click().run()
check("login succeeds", at.session_state["admin"] is not None and not at.exception)

at.session_state["nav"] = "products"
at.run()
check("products page renders", not at.exception)
cards = " ".join(m.body for m in at.markdown)
check("product cards visible with codes", "INF-001" in cards, "")

at.button(key="add_product_btn").click().run()
check("product form opens", any(w.key == "pf_code" for w in at.text_input))

at.text_input(key="pf_code").set_value("INF-001")
at.text_input(key="pf_name").set_value("Doublon test")
at.button(key="pf_save").click().run()
check("exact duplicate message", any("Ce code produit existe déjà." in e.value for e in at.error),
      str([e.value for e in at.error])[:120])

at.text_input(key="pf_code").set_value("TST-001")
at.text_input(key="pf_name").set_value("Produit test")
at.button(key="pf_save").click().run()
check("unique product added", not at.exception)
row = db.one("SELECT id, stock FROM products WHERE code = 'TST-001'")
check("auto-increment id > seed max", row is not None and row["id"] > 12, "id=%s" % (row["id"] if row else None))
pid = row["id"]

db.exec("UPDATE products SET stock = 5 WHERE id = ?", (pid,))
over = db.create_dispatch(1, pid, 99, datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
check("over-stock blocked at db layer", over is not None and over[0] == "stock" and over[1] == 5)

at.session_state["nav"] = "dispatch"
at.run()
check("dispatch page renders", not at.exception)
at.session_state["disp_user"] = 1
at.session_state["disp_product"] = pid
at.session_state["disp_qty"] = 2
at.run()
at.button(key="disp_submit").click().run()
check("valid dispatch accepted", not at.exception)
check("stock decremented 5 -> 3", db.one("SELECT stock FROM products WHERE id = ?", (pid,))["stock"] == 3)
dispatched = db.one("SELECT app_user_id, quantity FROM dispatches WHERE product_id = ?", (pid,))
check("dispatch row correct", dispatched is not None and dispatched["app_user_id"] == 1
      and dispatched["quantity"] == 2)

at.session_state["nav"] = "reports"
at.run()
check("reports page renders", not at.exception)

at.session_state["nav"] = "users"
at.run()
at.button(key="add_user_btn").click().run()
at.text_input(key="uf_name").set_value("Agent Test")
at.button(key="uf_save").click().run()
check("user added", db.one("SELECT id FROM app_users WHERE full_name = 'Agent Test'") is not None)

at.session_state["nav"] = "settings"
at.run()
check("settings page renders", not at.exception)
at.selectbox(key="set_acc").set_value("blue")
at.radio(key="set_layout").set_value("topbar")
at.button(key="set_save").click().run()
check("settings persisted", db.get_settings()["accent"] == "blue" and db.get_settings()["layout"] == "topbar")
check("topbar layout applied", not at.exception)
at.selectbox(key="set_acc").set_value("red")
at.radio(key="set_layout").set_value("sidebar")
at.button(key="set_save").click().run()
check("settings restored", db.get_settings()["accent"] == "red" and db.get_settings()["layout"] == "sidebar")

at.session_state["nav"] = "dashboard"
at.run()
check("dashboard renders after changes", not at.exception)

db.exec("DELETE FROM dispatches WHERE product_id = ?", (pid,))
db.exec("DELETE FROM products WHERE id = ?", (pid,))
db.exec("DELETE FROM app_users WHERE full_name = 'Agent Test'")

print()
if FAILED:
    print("FAILED: %d -> %s" % (len(FAILED), FAILED))
    sys.exit(1)
print("ALL STREAMLIT TESTS PASSED")
