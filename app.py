import html
import io
from datetime import datetime

import pandas as pd
import streamlit as st
import streamlit.components.v1 as components

import database as db
from translations import TRANSLATIONS, MONTHS

st.set_page_config(page_title="AGC Assurances — Gestion de stock", page_icon="🛡️", layout="wide")

ACCENTS = {
    "red": "#E8354B",
    "blue": "#1A22B8",
    "emerald": "#0E9F6E",
    "graphite": "#374151",
    "amber": "#C77700",
}

db.init_db()

FALLBACK_LANG = "fr"


def current_lang():
    global FALLBACK_LANG
    try:
        lang = st.session_state.lang
    except (AttributeError, KeyError):
        return FALLBACK_LANG
    if lang in TRANSLATIONS:
        FALLBACK_LANG = lang
    return lang


def T(key):
    return TRANSLATIONS[current_lang()].get(key, key)


def month_label(ym):
    year, month = ym.split("-")
    return MONTHS[current_lang()][int(month) - 1] + " " + year


ss = st.session_state
ss.setdefault("lang", "fr")
ss.setdefault("admin", None)
ss.setdefault("nav", "dashboard")
ss.setdefault("show_product_form", False)
ss.setdefault("edit_product_id", None)
ss.setdefault("show_cat_form", False)
ss.setdefault("edit_cat_id", None)
ss.setdefault("show_user_form", False)
ss.setdefault("edit_user_id", None)
ss.setdefault("confirm_del_prod", None)
ss.setdefault("confirm_del_cat", None)
ss.setdefault("confirm_del_user", None)


def e(text):
    return html.escape(str(text if text is not None else ""))


def brand_svg(size=44):
    return (
        '<svg viewBox="0 0 96 96" width="%d" height="%d" role="img" aria-label="AGC Assurances">'
        '<rect width="96" height="55" fill="#F94152"/>'
        '<text x="48" y="41" text-anchor="middle" font-family="Arial,Helvetica,sans-serif" '
        'font-size="31" font-weight="bold" fill="#FFFFFF">AGC</text>'
        '<rect y="55" width="96" height="41" fill="#131C9C"/>'
        '<text x="48" y="74" text-anchor="middle" font-family="Arial,Helvetica,sans-serif" '
        'font-size="11.5" font-weight="bold" fill="#FFFFFF" letter-spacing="1.4">ASSURANCES</text>'
        '<rect x="26" y="78" width="44" height="2.6" fill="#F94152"/>'
        '<text x="48" y="90.5" text-anchor="middle" font-family="Arial,Helvetica,sans-serif" '
        'font-size="6.8" fill="#FFFFFF" letter-spacing="0.4">GÉNÉRALES DU CAMEROUN</text>'
        "</svg>" % (size, size)
    )


def brand_html(settings, size=44):
    return (
        '<div style="display:flex;align-items:center;gap:11px">' + brand_svg(size)
        + '<div><div style="font-weight:800;font-size:17px;color:#131C9C;line-height:1.2">'
        + e(settings["app_name"]) + "</div>"
        + '<div style="font-size:11.5px;color:#6B7280;font-style:italic">'
        + e(settings["tagline"]) + "</div>"
        + '<div style="font-size:10px;color:#9AA3B2;letter-spacing:1px;text-transform:uppercase">'
        + e(T("app.company")) + "</div></div></div>"
    )


def inject_css(accent_hex, layout):
    hide_sidebar = "[data-testid='stSidebar']{display:none;}" if layout == "topbar" else ""
    st.markdown(
        """
        <style>
        :root { --primary-color: %(accent)s; }
        #MainMenu { visibility: hidden; }
        footer { visibility: hidden; }
        [data-testid='stToolbar'] { display: none; }
        %(hide_sidebar)s
        .block-container { padding-top: 1.3rem; max-width: 1240px; }
        div[data-testid='stMetric'] {
            background: #FFFFFF; border: 1px solid #E7EBF2; border-radius: 12px;
            padding: 16px 18px; border-top: 3px solid %(accent)s;
        }
        .ph { height: 150px; display: flex; align-items: center; justify-content: center;
              font-size: 58px; border-radius: 10px;
              background: linear-gradient(140deg, #EEF1F7 55%%, #F8FAFD); }
        .chip { font-family: Consolas, monospace; font-weight: 700; font-size: 12px;
                color: #131C9C; background: #EEF2FF; border: 1px solid #D9DFF8;
                padding: 2px 9px; border-radius: 6px; }
        .pid { color: #9AA3B2; font-size: 11.5px; }
        .stockline { margin-top: 2px; }
        .brandline { display: flex; align-items: center; gap: 11px; }
        .login-hero { background: linear-gradient(150deg, #FFFFFF, #F2F5FB);
                      border: 1px solid #E3E7EF; border-radius: 16px; padding: 30px 30px 22px; }
        </style>
        """
        % {"accent": accent_hex, "hide_sidebar": hide_sidebar},
        unsafe_allow_html=True,
    )


def stock_badge(stock, threshold):
    if stock <= 0:
        return "🔴 " + T("badge.out")
    if stock <= threshold:
        return "🟠 " + T("badge.low")
    return "🟢 " + T("badge.in")


def dispatch_table(rows):
    data = [
        {
            "#": r["id"],
            T("col.datetime"): datetime.strptime(r["dispatched_at"], "%Y-%m-%d %H:%M:%S").strftime("%d/%m/%Y %H:%M"),
            T("col.user"): r["full_name"],
            T("col.service"): r["service"],
            T("col.item"): r["product"],
            T("col.code"): r["code"],
            T("col.quantity"): "×" + str(r["quantity"]),
        }
        for r in rows
    ]
    st.dataframe(pd.DataFrame(data), hide_index=True)


def printable_html(settings, ym, rows):
    total_units = sum(r["quantity"] for r in rows)
    body_rows = []
    for i, r in enumerate(rows, start=1):
        when = datetime.strptime(r["dispatched_at"], "%Y-%m-%d %H:%M:%S").strftime("%d/%m/%Y %H:%M")
        body_rows.append(
            "<tr><td class='num'>%d</td><td>%s</td><td>%s</td><td>%s</td><td>%s</td><td>%s</td>"
            "<td class='num'><b>×%d</b></td></tr>"
            % (i, when, e(r["full_name"]), e(r["service"]), e(r["product"]), e(r["code"]), r["quantity"])
        )
    css = """
    <style>
      * { box-sizing: border-box; margin: 0; padding: 0; }
      body { font-family: Arial, Helvetica, sans-serif; color: #111827; background: #EEF1F6; font-size: 12.5px; }
      .bar { max-width: 210mm; margin: 0 auto; padding: 12px 0; display: flex; gap: 10px; justify-content: flex-end; }
      .bar button { font: inherit; font-weight: bold; padding: 9px 22px; border: 0; border-radius: 8px;
                    background: #E8354B; color: #fff; cursor: pointer; }
      .sheet { max-width: 210mm; margin: 0 auto 24px; background: #fff; padding: 14mm 12mm;
               box-shadow: 0 10px 30px rgba(15,23,42,.15); }
      .doc-header { display: flex; justify-content: space-between; align-items: flex-start; gap: 16px;
                    border-bottom: 3px solid #131C9C; padding-bottom: 12px; }
      .doc-brand { display: flex; gap: 12px; align-items: center; }
      .doc-brand h2 { font-size: 16px; color: #131C9C; }
      .doc-brand small { display: block; color: #6B7280; font-size: 10.5px; margin-top: 2px; }
      .doc-title { text-align: right; }
      .doc-title h1 { font-size: 15px; color: #E8354B; letter-spacing: .5px; text-transform: uppercase; }
      .doc-title p { color: #374151; font-size: 11px; margin-top: 4px; }
      .meta { margin: 12px 0; font-size: 11.5px; color: #374151; }
      table { width: 100%%; border-collapse: collapse; }
      th, td { border: 1px solid #C7CDD9; padding: 6px 8px; text-align: left; }
      th { background: #131C9C; color: #fff; font-size: 11px; text-transform: uppercase; }
      tr:nth-child(even) td { background: #F5F7FB; }
      td.num, th.num { text-align: center; }
      .total-row td { background: #FBE9EB !important; font-weight: bold; border-top: 2px solid #E8354B; }
      .signatures { display: flex; justify-content: space-between; gap: 40px; margin-top: 46px; }
      .signature { flex: 1; text-align: center; font-size: 11px; color: #374151; }
      .signature .line { margin-top: 52px; border-top: 1px solid #6B7280; padding-top: 5px; }
      .doc-footer { margin-top: 16px; font-size: 9.5px; color: #9AA3B2; text-align: center;
                    border-top: 1px solid #E3E7EF; padding-top: 8px; }
      @media print { body { background: #fff; } .bar { display: none; }
                     .sheet { box-shadow: none; } @page { size: A4; margin: 14mm 12mm; } }
    </style>
    """
    parts = [
        "<html><head><meta charset='UTF-8'><title>", e(T("rep.print_title")), " — ", e(month_label(ym)),
        "</title>", css, "</head><body>",
        "<div class='bar'><button onclick='window.print()'>", e(T("btn.print")), "</button></div>",
        "<div class='sheet'><div class='doc-header'><div class='doc-brand'>", brand_svg(64),
        "<div><h2>", e(settings["app_name"]), "</h2><small>", e(settings["tagline"]), "<br>",
        e(T("app.company")), "</small></div></div>",
        "<div class='doc-title'><h1>", e(T("rep.print_title")), "</h1><p>", e(T("rep.period")),
        " : <b>", e(month_label(ym)), "</b></p><p>", e(T("rep.generated")), " : ",
        datetime.now().strftime("%d/%m/%Y %H:%M"), "</p></div></div>",
        "<table><tr><th class='num'>#</th><th>", e(T("col.datetime")), "</th><th>", e(T("col.user")),
        "</th><th>", e(T("col.service")), "</th><th>", e(T("col.item")), "</th><th>", e(T("col.code")),
        "</th><th class='num'>", e(T("col.quantity")), "</th></tr>",
        "".join(body_rows),
        "<tr class='total-row'><td colspan='6'>", e(T("rep.total_entries")), " : ", str(len(rows)),
        "</td><td class='num'>", str(total_units), "</td></tr></table>",
        "<div class='signatures'><div class='signature'><div class='line'>", e(T("rep.sign1")),
        "</div></div><div class='signature'><div class='line'>", e(T("rep.sign2")),
        "</div></div></div>",
        "<p class='doc-footer'>", e(settings["app_name"]), " • ", e(T("rep.doc_ref")), " • © ",
        datetime.now().strftime("%Y"), " ", e(T("app.company")), "</p></div></body></html>",
    ]
    return "".join(parts)


def clear_product_form():
    for key in ("pf_code", "pf_name", "pf_cat", "pf_stock", "pf_low", "pf_image"):
        ss.pop(key, None)
    ss.show_product_form = False
    ss.edit_product_id = None


def login_page():
    st.markdown("<style>[data-testid='stSidebar']{display:none;}</style>", unsafe_allow_html=True)
    left, mid, right = st.columns([1, 1.15, 1])
    with mid:
        l1, l2 = st.columns(2)
        if l1.button("Français", width="stretch",
                     type="primary" if ss.lang == "fr" else "secondary", key="lang_fr_btn"):
            ss.lang = "fr"
            st.rerun()
        if l2.button("English", width="stretch",
                     type="primary" if ss.lang == "en" else "secondary", key="lang_en_btn"):
            ss.lang = "en"
            st.rerun()

        with st.container(border=True):
            st.markdown(
                '<div style="text-align:center;margin-bottom:6px">' + brand_svg(88) + "</div>",
                unsafe_allow_html=True,
            )
            st.markdown(
                "<div style='text-align:center'><div style='font-weight:800;font-size:24px;"
                "color:#131C9C'>AGC Assurances</div>"
                "<div style='color:#6B7280;font-style:italic'>Le gage de votre sécurité</div></div>",
                unsafe_allow_html=True,
            )
            st.markdown("---")
            st.subheader(T("login.title"))
            st.caption(T("login.subtitle"))

            email = st.text_input(T("login.email"), key="login_email", placeholder="admin@agc-assurances.com")
            password = st.text_input(T("login.password"), type="password", key="login_password")
            if st.button(T("login.signin"), width="stretch", type="primary", key="login_submit"):
                if not email.strip() or not password:
                    st.error(T("err.email_password"))
                else:
                    account = db.get_admin_by_email(email.strip())
                    if account is None:
                        st.error(T("err.user_not_found"))
                    elif not db.check_password(password, account["password"]):
                        st.error(T("err.invalid_credentials"))
                    else:
                        ss.admin = {"id": account["id"], "name": account["name"], "email": account["email"]}
                        ss.lang = account["language"]
                        st.rerun()
            st.caption(T("login.demo"))


def page_dashboard(settings):
    st.subheader(T("dash.title"))

    m = st.columns(4)
    m[0].metric(T("stat.products"), db.count_products())
    m[1].metric(T("stat.stock"), db.count_stock_units())
    m[2].metric(T("stat.categories"), db.count_categories())
    m[3].metric(T("stat.users"), db.count_users())

    st.markdown("#### " + T("panel.quick"))
    q1, q2, q3, q4 = st.columns(4)
    if q1.button("📤 " + T("qa.dispatch"), width="stretch", key="qa_dispatch"):
        ss.nav = "dispatch"
        st.rerun()
    if q2.button("📦 " + T("qa.product"), width="stretch", key="qa_product"):
        ss.show_product_form = True
        ss.nav = "products"
        st.rerun()
    if q3.button("👤 " + T("qa.user"), width="stretch", key="qa_user"):
        ss.show_user_form = True
        ss.nav = "users"
        st.rerun()
    current = datetime.now().strftime("%Y-%m")
    if q4.button("🗓 " + T("qa.report"), width="stretch", key="qa_report"):
        ss.nav = "reports"
        st.rerun()

    left, right = st.columns(2, gap="medium")
    with left:
        st.markdown("#### " + T("panel.low"))
        low = db.low_stock_products()
        if not low:
            st.info(T("msg.nothing"))
        for p in low:
            c1, c2 = st.columns([3, 1])
            c1.markdown("**" + e(p["name"]) + "**")
            c1.caption(e(p["code"]))
            c2.markdown(stock_badge(p["stock"], p["low_stock_at"]) + "  \n**" + str(p["stock"]) + "**")
    with right:
        st.markdown("#### " + T("panel.recent"))
        recent = db.recent_dispatches(8)
        if not recent:
            st.info(T("msg.nothing"))
        else:
            dispatch_table(recent)


def page_products():
    st.subheader(T("prod.title"))
    bar = st.columns([1.1, 1.6, 1])
    with bar[0]:
        if st.button("+ " + T("btn.add_product"), type="primary", key="add_product_btn"):
            ss.show_product_form = True
            ss.edit_product_id = None
            st.rerun()
    with bar[1]:
        search = st.text_input("Recherche", key="prod_search", placeholder=T("ph.search_products"),
                               label_visibility="collapsed")
    cats = db.list_categories()
    cat_names = {c["id"]: c["name"] for c in cats}
    with bar[2]:
        cat_id = st.selectbox(
            "Catégorie",
            options=[0] + [c["id"] for c in cats],
            format_func=lambda x: T("prod.all") if x == 0 else cat_names.get(x, str(x)),
            key="prod_cat",
            label_visibility="collapsed",
        )

    edit_id = ss.edit_product_id
    if ss.show_product_form or edit_id is not None:
        render_product_form(edit_id)

    products = db.list_products(search.strip(), cat_id)
    if not products:
        st.info(T("msg.no_products"))
        return
    for start in range(0, len(products), 3):
        cols = st.columns(3, gap="medium")
        for col, product in zip(cols, products[start:start + 3]):
            with col:
                render_product_card(product)


def render_product_form(edit_id):
    product = db.get_product(edit_id) if edit_id is not None else None
    with st.container(border=True):
        st.markdown("### " + T("prod.details"))
        c1, c2 = st.columns(2)
        code = c1.text_input(T("prod.code"), value=product["code"] if product else "",
                             key="pf_code", placeholder="INF-001")
        name = c2.text_input(T("prod.designation"), value=product["name"] if product else "",
                             key="pf_name")
        cats = db.list_categories()
        cat_names = {c["id"]: c["name"] for c in cats}
        c3, c4, c5 = st.columns(3)
        cat_id = c3.selectbox(
            T("col.category"),
            options=[0] + [c["id"] for c in cats],
            format_func=lambda x: T("req.select") if x == 0 else cat_names.get(x, str(x)),
            index=([0] + [c["id"] for c in cats]).index(product["category_id"]) if product else 0,
            key="pf_cat",
        )
        stock = c4.number_input(T("col.stock"), min_value=0,
                                value=int(product["stock"]) if product else 0, key="pf_stock")
        low = c5.number_input(T("col.threshold"), min_value=0,
                              value=int(product["low_stock_at"]) if product else 5, key="pf_low")
        image = st.file_uploader(T("prod.image"), type=["jpg", "jpeg", "png", "webp"], key="pf_image")
        st.caption(T("prod.image_hint"))

        b1, b2 = st.columns([1, 1])
        save = b1.button(T("btn.save") if product else T("btn.add"), type="primary", key="pf_save",
                         width="stretch")
        cancel = b2.button(T("btn.cancel"), key="pf_cancel", width="stretch")

        if cancel:
            clear_product_form()
            st.rerun()

        if save:
            code_val = code.strip().upper()
            name_val = name.strip()
            if not code_val or not name_val:
                st.error(T("msg.required_fields"))
            elif db.code_exists(code_val, edit_id or 0):
                st.error(T("err.duplicate_code"))
            else:
                blob = None
                mime = ""
                if image is not None and image.size <= 3 * 1024 * 1024:
                    blob = image.getvalue()
                    mime = image.type or ""
                if product:
                    db.update_product(product["id"], code_val, name_val, int(cat_id),
                                      int(stock), int(low), blob, mime)
                    message = T("msg.product_updated")
                else:
                    db.add_product(code_val, name_val, int(cat_id), int(stock), int(low), blob, mime)
                    message = T("msg.product_added")
                clear_product_form()
                st.success(message)
                st.rerun()


def render_product_card(product):
    if product["image_blob"]:
        st.image(io.BytesIO(product["image_blob"]), width="stretch")
    else:
        st.markdown("<div class='ph'>📦</div>", unsafe_allow_html=True)
    st.markdown(
        "<span class='chip'>" + e(product["code"]) + "</span> <span class='pid'>#" + str(product["id"]) + "</span>",
        unsafe_allow_html=True,
    )
    st.markdown("**" + e(product["name"]) + "**")
    st.caption(e(product["category_name"]) if product["category_name"] else "—")
    st.markdown(
        "<span class='stockline'>" + stock_badge(product["stock"], product["low_stock_at"])
        + " &nbsp;<b>" + str(product["stock"]) + "</b></span>",
        unsafe_allow_html=True,
    )
    btn1, btn2 = st.columns(2)
    if btn1.button(T("btn.edit"), key="pedit_%d" % product["id"], width="stretch"):
        ss.edit_product_id = product["id"]
        ss.show_product_form = False
        st.rerun()
    if ss.confirm_del_prod == product["id"]:
        st.warning(T("msg.confirm_delete"))
        yes, no = st.columns(2)
        if yes.button(T("btn.confirm"), key="pdel_yes_%d" % product["id"], type="primary",
                      width="stretch"):
            if db.delete_product(product["id"]):
                st.success(T("msg.product_deleted"))
            else:
                st.error(T("err.product_in_use"))
            ss.confirm_del_prod = None
            st.rerun()
        if no.button(T("btn.cancel"), key="pdel_no_%d" % product["id"], width="stretch"):
            ss.confirm_del_prod = None
            st.rerun()
    else:
        if btn2.button(T("btn.delete"), key="pdel_%d" % product["id"], width="stretch"):
            ss.confirm_del_prod = product["id"]
            st.rerun()


def page_categories():
    st.subheader(T("cat.title"))
    if st.button("+ " + T("btn.add_category"), type="primary", key="add_cat_btn"):
        ss.show_cat_form = True
        ss.edit_cat_id = None
        st.rerun()

    if ss.show_cat_form or ss.edit_cat_id is not None:
        cat = db.one("SELECT * FROM categories WHERE id = ?", (ss.edit_cat_id,)) if ss.edit_cat_id else None
        with st.container(border=True):
            st.markdown("### " + T("cat.title"))
            name = st.text_input(T("col.name"), value=cat["name"] if cat else "", key="cf_name")
            desc = st.text_input(T("cat.description") if "cat.description" in TRANSLATIONS[ss.lang] else "Description",
                                 value=cat["description"] if cat else "", key="cf_desc")
            s1, s2 = st.columns(2)
            if s1.button(T("btn.save") if cat else T("btn.add"), type="primary", key="cf_save",
                         width="stretch"):
                if not name.strip():
                    st.error(T("msg.required_fields"))
                else:
                    if cat:
                        db.update_category(cat["id"], name.strip(), desc.strip())
                        st.success(T("msg.category_updated"))
                    else:
                        db.add_category(name.strip(), desc.strip())
                        st.success(T("msg.category_added"))
                    ss.show_cat_form = False
                    ss.edit_cat_id = None
                    ss.pop("cf_name", None)
                    ss.pop("cf_desc", None)
                    st.rerun()
            if s2.button(T("btn.cancel"), key="cf_cancel", width="stretch"):
                ss.show_cat_form = False
                ss.edit_cat_id = None
                ss.pop("cf_name", None)
                ss.pop("cf_desc", None)
                st.rerun()

    cats = db.list_categories()
    if not cats:
        st.info(T("msg.no_records"))
        return
    for c in cats:
        row = st.columns([0.5, 2.2, 3, 1, 1.2, 1.2])
        row[0].markdown("**%d**" % c["id"])
        row[1].markdown("**" + e(c["name"]) + "**")
        row[2].caption(e(c["description"]))
        row[3].markdown(str(c["product_count"]))
        if row[4].button(T("btn.edit"), key="cedit_%d" % c["id"], width="stretch"):
            ss.edit_cat_id = c["id"]
            ss.show_cat_form = False
            st.rerun()
        if ss.confirm_del_cat == c["id"]:
            st.warning(T("msg.confirm_delete"))
            yes, no = st.columns(2)
            if yes.button(T("btn.confirm"), key="cdel_yes_%d" % c["id"], type="primary"):
                if db.category_in_use(c["id"]):
                    st.error(T("err.category_in_use"))
                else:
                    db.delete_category(c["id"])
                    st.success(T("msg.category_deleted"))
                ss.confirm_del_cat = None
                st.rerun()
            if no.button(T("btn.cancel"), key="cdel_no_%d" % c["id"]):
                ss.confirm_del_cat = None
                st.rerun()
        else:
            if row[5].button(T("btn.delete"), key="cdel_%d" % c["id"], width="stretch"):
                ss.confirm_del_cat = c["id"]
                st.rerun()


def page_dispatch():
    st.subheader(T("disp.title"))
    users = db.list_users()
    products = db.list_products()

    if not users or not products:
        st.warning(T("msg.no_records"))
        return

    user_names = {u["id"]: u["full_name"] + (" — " + u["service"] if u["service"] else "") for u in users}
    product_labels = {p["id"]: p["code"] + " — " + p["name"] for p in products}

    c1, c2 = st.columns(2)
    user_id = c1.selectbox(T("disp.user"), options=[u["id"] for u in users],
                           format_func=lambda x: user_names.get(x, str(x)), key="disp_user")
    product_id = c2.selectbox(T("disp.item"), options=[p["id"] for p in products],
                              format_func=lambda x: product_labels.get(x, str(x)), key="disp_product")

    stock = db.get_product(product_id)["stock"]
    st.caption("📦 " + T("disp.available") + " : **%d**" % stock)

    c3, c4 = st.columns([1, 2])
    quantity = c3.number_input(T("disp.quantity"), min_value=1, max_value=max(stock, 1), value=1, key="disp_qty")
    when = c4.datetime_input(T("disp.datetime"), value=datetime.now(), key="disp_dt")

    if st.button(T("btn.validate"), type="primary", key="disp_submit"):
        result = db.create_dispatch(user_id, product_id, int(quantity), when.strftime("%Y-%m-%d %H:%M:%S"))
        if result is None:
            st.success(T("msg.dispatch_created"))
        elif result[0] == "stock":
            st.error(T("err.not_enough_stock").format(result[1]))
        else:
            st.error(T("msg.required_fields"))

    st.markdown("#### " + T("disp.recent"))
    recent = db.recent_dispatches()
    if not recent:
        st.info(T("msg.nothing"))
    else:
        dispatch_table(recent)


def page_users():
    st.subheader(T("usr.title"))
    if st.button("+ " + T("btn.add_user"), type="primary", key="add_user_btn"):
        ss.show_user_form = True
        ss.edit_user_id = None
        st.rerun()

    if ss.show_user_form or ss.edit_user_id is not None:
        user = db.one("SELECT * FROM app_users WHERE id = ?", (ss.edit_user_id,)) if ss.edit_user_id else None
        with st.container(border=True):
            st.markdown("### " + T("usr.details"))
            c1, c2 = st.columns(2)
            full_name = c1.text_input(T("usr.full_name"), value=user["full_name"] if user else "", key="uf_name")
            service = c2.text_input(T("col.service"), value=user["service"] if user else "", key="uf_service")
            c3, c4 = st.columns(2)
            email = c3.text_input(T("col.email"), value=user["email"] if user else "", key="uf_email")
            phone = c4.text_input(T("col.phone"), value=user["phone"] if user else "", key="uf_phone")
            s1, s2 = st.columns(2)
            if s1.button(T("btn.save") if user else T("btn.add"), type="primary", key="uf_save",
                         width="stretch"):
                if not full_name.strip():
                    st.error(T("msg.required_fields"))
                else:
                    if user:
                        db.update_user(user["id"], full_name.strip(), service.strip(), email.strip(), phone.strip())
                        st.success(T("msg.user_updated"))
                    else:
                        db.add_user(full_name.strip(), service.strip(), email.strip(), phone.strip())
                        st.success(T("msg.user_added"))
                    ss.show_user_form = False
                    ss.edit_user_id = None
                    for k in ("uf_name", "uf_service", "uf_email", "uf_phone"):
                        ss.pop(k, None)
                    st.rerun()
            if s2.button(T("btn.cancel"), key="uf_cancel", width="stretch"):
                ss.show_user_form = False
                ss.edit_user_id = None
                for k in ("uf_name", "uf_service", "uf_email", "uf_phone"):
                    ss.pop(k, None)
                st.rerun()

    st.markdown("#### " + T("usr.directory"))
    users = db.list_users()
    if not users:
        st.info(T("msg.no_records"))
        return
    for u in users:
        row = st.columns([2, 1.6, 2.2, 1.4, 0.8, 1, 1])
        row[0].markdown("**" + e(u["full_name"]) + "**")
        row[1].caption(e(u["service"]))
        row[2].caption(e(u["email"]))
        row[3].caption(e(u["phone"]))
        row[4].markdown(str(u["dispatch_count"]))
        if row[5].button(T("btn.edit"), key="uedit_%d" % u["id"], width="stretch"):
            ss.edit_user_id = u["id"]
            ss.show_user_form = False
            st.rerun()
        if ss.confirm_del_user == u["id"]:
            st.warning(T("msg.confirm_delete"))
            yes, no = st.columns(2)
            if yes.button(T("btn.confirm"), key="udel_yes_%d" % u["id"], type="primary"):
                if db.delete_user(u["id"]):
                    st.success(T("msg.user_deleted"))
                else:
                    st.error(T("err.user_in_use"))
                ss.confirm_del_user = None
                st.rerun()
            if no.button(T("btn.cancel"), key="udel_no_%d" % u["id"]):
                ss.confirm_del_user = None
                st.rerun()
        else:
            if row[6].button(T("btn.delete"), key="udel_%d" % u["id"], width="stretch"):
                ss.confirm_del_user = u["id"]
                st.rerun()


def page_reports(settings):
    st.subheader(T("rep.title"))
    months = db.dispatch_months()
    current = datetime.now().strftime("%Y-%m")
    if current not in months:
        months.insert(0, current)
    ym = st.selectbox(T("rep.month"), months, format_func=month_label, key="rep_month")

    rows = db.month_dispatches(ym)
    if not rows:
        st.info(T("rep.no_month"))
        return

    m1, m2 = st.columns(2)
    m1.metric(T("rep.total_entries"), len(rows))
    m2.metric(T("rep.total_units"), sum(r["quantity"] for r in rows))

    dispatch_table(rows)

    html_doc = printable_html(settings, ym, rows)
    dl1, _ = st.columns([1, 3])
    dl1.download_button("⬇️ " + T("btn.print"), data=html_doc, file_name="registre_%s.html" % ym,
                        mime="text/html", key="rep_download", width="stretch")
    if hasattr(st, "html"):
        st.html(html_doc)
    else:
        components.html(html_doc, height=780, scrolling=True)


def page_settings():
    settings = db.get_settings()
    st.subheader(T("set.title"))

    with st.container(border=True):
        st.markdown("### " + T("set.branding"))
        st.markdown(brand_html(settings), unsafe_allow_html=True)
        app_name = st.text_input(T("set.app_name"), value=settings["app_name"], key="set_app")
        tagline = st.text_input(T("set.tagline"), value=settings["tagline"], key="set_tag")

    with st.container(border=True):
        st.markdown("### " + T("set.appearance"))
        layout = st.radio(T("set.layout"), options=["sidebar", "topbar"],
                          format_func=lambda x: T("layout.sidebar") if x == "sidebar" else T("layout.topbar"),
                          horizontal=True, key="set_layout")
        accent_labels = {k: T("acc." + k) for k in ACCENTS}
        accent = st.selectbox(T("set.accent"), options=list(ACCENTS.keys()),
                              format_func=lambda x: accent_labels.get(x, x), key="set_acc")
        st.markdown(
            " ".join("<span style='display:inline-block;width:22px;height:22px;border-radius:50%%;"
                     "background:%s;margin-right:6px;border:2px solid #fff;"
                     "box-shadow:0 0 0 1px #ccc'></span>" % c for c in ACCENTS.values()),
            unsafe_allow_html=True,
        )

    with st.container(border=True):
        st.markdown("### " + T("set.account"))
        name = st.text_input(T("set.name"), value=ss.admin["name"], key="set_name")
        email = st.text_input(T("set.email"), value=ss.admin["email"], key="set_email")
        new_password = st.text_input(T("set.new_password"), type="password", key="set_pw")

    language = st.radio(T("set.language"), options=["fr", "en"],
                        format_func=lambda x: "Français" if x == "fr" else "English",
                        horizontal=True, key="set_lang")

    if st.button(T("btn.save"), type="primary", key="set_save"):
        if not app_name.strip() or not name.strip() or not email.strip():
            st.error(T("msg.required_fields"))
        elif new_password and len(new_password) < 6:
            st.error(T("msg.required_fields"))
        else:
            db.update_settings(app_name.strip(), tagline.strip(), accent, layout)
            db.update_admin_account(ss.admin["id"], name.strip(), email.strip(),
                                    new_password if new_password else None)
            ss.admin["name"] = name.strip()
            ss.admin["email"] = email.strip()
            ss.lang = language
            db.update_admin_language(ss.admin["id"], language)
            st.success(T("msg.settings_saved"))
            st.rerun()


def run_app():
    settings = db.get_settings()
    inject_css(ACCENTS.get(settings["accent"], "#E8354B"), settings["layout"])

    nav_items = [
        ("dashboard", T("nav.dashboard")),
        ("products", T("nav.products")),
        ("categories", T("nav.categories")),
        ("dispatch", T("nav.dispatch")),
        ("users", T("nav.users")),
        ("reports", T("nav.reports")),
        ("settings", T("nav.settings")),
    ]
    nav_keys = [k for k, _ in nav_items]
    nav_labels = dict(nav_items)

    def set_lang(value):
        ss.lang = value
        db.update_admin_language(ss.admin["id"], value)
        st.rerun()

    def do_logout():
        ss.admin = None
        st.rerun()

    if settings["layout"] == "topbar":
        head = st.columns([3.4, 0.45, 0.45, 1])
        with head[0]:
            st.markdown(brand_html(settings), unsafe_allow_html=True)
        with head[1]:
            if st.button("FR", key="tb_fr", width="stretch",
                         type="primary" if ss.lang == "fr" else "secondary"):
                set_lang("fr")
        with head[2]:
            if st.button("EN", key="tb_en", width="stretch",
                         type="primary" if ss.lang == "en" else "secondary"):
                set_lang("en")
        with head[3]:
            if st.button("⎋ " + T("nav.logout"), key="tb_logout", width="stretch"):
                do_logout()
        st.radio("Navigation", options=nav_keys, format_func=lambda k: nav_labels[k], key="nav",
                 horizontal=True, label_visibility="collapsed")
    else:
        with st.sidebar:
            st.markdown(brand_html(settings), unsafe_allow_html=True)
            st.caption(T("app.company"))
            l1, l2 = st.columns(2)
            if l1.button("FR", key="sb_fr", width="stretch",
                         type="primary" if ss.lang == "fr" else "secondary"):
                set_lang("fr")
            if l2.button("EN", key="sb_en", width="stretch",
                         type="primary" if ss.lang == "en" else "secondary"):
                set_lang("en")
            st.radio("Navigation", options=nav_keys, format_func=lambda k: nav_labels[k], key="nav",
                     label_visibility="collapsed")
            st.divider()
            st.caption("👤 **" + e(ss.admin["name"]) + "**  \n" + T("top.admin"))
            if st.button("⎋ " + T("nav.logout"), width="stretch", key="sb_logout"):
                do_logout()

    page = ss.nav
    if page == "dashboard":
        page_dashboard(settings)
    elif page == "products":
        page_products()
    elif page == "categories":
        page_categories()
    elif page == "dispatch":
        page_dispatch()
    elif page == "users":
        page_users()
    elif page == "reports":
        page_reports(settings)
    elif page == "settings":
        page_settings()


if ss.admin is None:
    login_page()
else:
    run_app()
