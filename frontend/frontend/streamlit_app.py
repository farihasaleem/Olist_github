
import streamlit as st
import pandas as pd
import requests
import html
import math

st.set_page_config(
    page_title="Olist Analytics",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

API_BASE_URL = "http://127.0.0.1:8001"

TABLES = {
    "Customers": "customers",
    "Sellers": "sellers",
    "Products": "products",
    "Category Translation": "category_translation",
    "Orders": "orders",
    "Order Items": "order_items",
    "Order Payments": "order_payments",
    "Order Reviews": "order_reviews",
}

# ---------------- SESSION STATE ----------------
defaults = {
    "logged_in": False,
    "access_token": None,
    "username": None,
    "role": None,
}

for key, value in defaults.items():
    if key not in st.session_state:
        st.session_state[key] = value


# ---------------- API HELPERS ----------------
def api_request(method, endpoint, **kwargs):
    try:
        headers = kwargs.pop("headers", {}).copy()

        token = st.session_state.get("access_token")
        if token:
            headers["Authorization"] = f"Bearer {token}"

        response = requests.request(
            method,
            API_BASE_URL + endpoint,
            headers=headers,
            timeout=60,
            **kwargs
        )

        response.raise_for_status()
        return response.json() if response.content else {}

    except requests.exceptions.RequestException as error:
        detail = ""
        try:
            detail = response.json().get("detail", "")
        except Exception:
            pass

        st.error(f"API error: {detail or error}")
        return None


def get_api_data(endpoint, params=None):
    return api_request("GET", endpoint, params=params)


def logout():
    for key in defaults:
        st.session_state[key] = defaults[key]
    st.rerun()


# ---------------- TABLE MANAGER ----------------
def show_table_manager(label, table_name):
    st.subheader(f"🗂️ {label}")
    st.caption(f"MySQL table: {table_name}")

    columns_info = get_api_data(f"/api/tables/{table_name}/columns")
    table_data = get_api_data(f"/api/tables/{table_name}")

    if not columns_info or table_data is None:
        return

    columns = columns_info.get("columns", [])
    primary_keys = columns_info.get("primary_keys", [])
    records = table_data.get("records", [])

    search = st.text_input("Search records", key=f"search_{table_name}")

    if search.strip():
        result = get_api_data(
            f"/api/tables/{table_name}/search",
            params={"q": search}
        )
        if result is not None:
            records = result.get("records", [])

    df = pd.DataFrame(records, columns=columns)

    st.caption(f"Showing {len(df)} records (API currently returns up to 100).")
    st.dataframe(df, use_container_width=True, hide_index=True)

    # Viewers can only view and search records.
    if st.session_state.role != "admin":
        st.info("Read-only access: only the administrator can modify records.")
        return

    st.divider()

    tab_add, tab_edit, tab_delete = st.tabs(
        ["➕ Add Record", "✏️ Edit Record", "🗑️ Delete Record"]
    )

    with tab_add:
        with st.form(f"add_form_{table_name}"):
            st.write("Enter values for the new record.")
            new_values = {}

            for col in columns:
                value = st.text_input(
                    col,
                    key=f"add_{table_name}_{col}"
                )
                if value.strip():
                    new_values[col] = value.strip()

            if st.form_submit_button("Add Record"):
                if not new_values:
                    st.warning("Enter at least one value.")
                else:
                    result = api_request(
                        "POST",
                        f"/api/tables/{table_name}",
                        json={"values": new_values}
                    )
                    if result:
                        st.success("Record added.")
                        st.rerun()

    with tab_edit:
        if not primary_keys:
            st.warning("This table has no primary key.")
        elif not records:
            st.info("No records available to edit.")
        else:
            selected_index = st.selectbox(
                "Select record",
                list(range(len(records))),
                format_func=lambda i: " | ".join(
                    f"{key}: {records[i].get(key)}"
                    for key in primary_keys
                ),
                key=f"edit_select_{table_name}"
            )

            selected = records[selected_index]

            with st.form(f"edit_form_{table_name}"):
                st.write("Primary keys cannot be changed.")
                updated_values = {}

                for col in columns:
                    if col not in primary_keys:
                        old = selected.get(col)
                        default = "" if old is None else str(old)

                        updated_values[col] = st.text_input(
                            col,
                            value=default,
                            key=f"edit_{table_name}_{col}"
                        )

                if st.form_submit_button("Save Changes"):
                    payload_values = {
                        k: (v if v != "" else None)
                        for k, v in updated_values.items()
                    }

                    result = api_request(
                        "PUT",
                        f"/api/tables/{table_name}",
                        json={
                            "primary_key": {
                                key: selected.get(key)
                                for key in primary_keys
                            },
                            "values": payload_values
                        }
                    )

                    if result:
                        st.success("Record updated.")
                        st.rerun()

    with tab_delete:
        if not primary_keys:
            st.warning("This table has no primary key.")
        elif not records:
            st.info("No records available to delete.")
        else:
            delete_index = st.selectbox(
                "Select record to delete",
                list(range(len(records))),
                format_func=lambda i: " | ".join(
                    f"{key}: {records[i].get(key)}"
                    for key in primary_keys
                ),
                key=f"delete_select_{table_name}"
            )

            st.warning(
                "Deleting a record is permanent and may be blocked "
                "by related records."
            )

            if st.button(
                "Delete Selected Record",
                key=f"delete_btn_{table_name}"
            ):
                result = api_request(
                    "DELETE",
                    f"/api/tables/{table_name}",
                    json={
                        "primary_key": {
                            key: records[delete_index].get(key)
                            for key in primary_keys
                        }
                    }
                )

                if result:
                    st.success("Record deleted.")
                    st.rerun()


# ---------------- CHART DATA + SVG CHARTS ----------------
def _collect_arrays(obj, path=""):
    found = []

    if isinstance(obj, dict):
        for key, value in obj.items():
            child_path = f"{path}.{key}" if path else str(key)
            found.extend(_collect_arrays(value, child_path))

    elif isinstance(obj, list):
        if all(not isinstance(item, (dict, list)) for item in obj):
            found.append((path.lower(), obj))

    return found


def chart_dataframe(payload, label_names, value_names):
    if payload is None:
        return pd.DataFrame()

    if isinstance(payload, list):
        try:
            return pd.DataFrame(payload)
        except (ValueError, TypeError):
            return pd.DataFrame()

    if not isinstance(payload, dict):
        return pd.DataFrame()

    arrays = _collect_arrays(payload)

    if not arrays:
        return pd.DataFrame()

    label_names = tuple(str(x).lower() for x in label_names)
    value_names = tuple(str(x).lower() for x in value_names)

    def score(path, names):
        leaf = path.split(".")[-1]
        return (100 if leaf in names else 0) + sum(
            10 for name in names if name in path.split(".")
        )

    label_candidates = [
        (path, values)
        for path, values in arrays
        if values and all(isinstance(v, str) for v in values)
    ]

    value_candidates = [
        (path, values)
        for path, values in arrays
        if values and all(
            isinstance(v, (int, float)) and not isinstance(v, bool)
            for v in values
        )
    ]

    if label_candidates and value_candidates:
        label_candidates.sort(
            key=lambda item: score(item[0], label_names),
            reverse=True
        )
        value_candidates.sort(
            key=lambda item: score(item[0], value_names),
            reverse=True
        )

        labels = label_candidates[0][1]
        values = value_candidates[0][1]

        if len(labels) == len(values):
            return pd.DataFrame(
                {"Label": labels, "Value": values}
            ).set_index("Label")

    flat = {}

    for path, values in arrays:
        key = path.split(".")[-1] or f"column_{len(flat) + 1}"
        flat[key] = values

    try:
        return pd.DataFrame(flat)
    except (ValueError, TypeError):
        return pd.DataFrame()


def _format_value(value):
    try:
        value = float(value)

        if abs(value) >= 1_000_000:
            return f"{value / 1_000_000:.1f}M"

        if abs(value) >= 1_000:
            return f"{value / 1_000:.1f}K"

        return f"{value:,.0f}" if value.is_integer() else f"{value:,.1f}"

    except (ValueError, TypeError):
        return str(value)


def render_svg_chart(title, labels, values, chart_type="bar"):
    width, height = 680, 285
    left, right, top, bottom = 62, 18, 24, 58

    plot_w = width - left - right
    plot_h = height - top - bottom

    numeric_values = [float(v) for v in values]

    if not numeric_values:
        st.caption("No chart data available.")
        return

    low = min(0.0, min(numeric_values))
    high = max(numeric_values)

    if high == low:
        high = low + 1

    padding = (high - low) * 0.12
    low -= padding * 0.15
    high += padding

    y_min = min(0, low)
    y_max = high

    def x_pos(i):
        if len(labels) == 1:
            return left + plot_w / 2
        return left + i * plot_w / (len(labels) - 1)

    def y_pos(v):
        return top + (y_max - v) / (y_max - y_min) * plot_h

    svg = [
        f'<div class="chart-panel"><div class="chart-heading">{html.escape(title)}</div>',
        f'<svg viewBox="0 0 {width} {height}" role="img" aria-label="{html.escape(title)} chart" style="width:100%;height:auto;display:block;">',
        '<defs><filter id="neonGlow" x="-60%" y="-60%" width="220%" height="220%">'
        '<feGaussianBlur stdDeviation="4" result="blur1"/>'
        '<feGaussianBlur stdDeviation="8" result="blur2"/>'
        '<feMerge><feMergeNode in="blur2"/><feMergeNode in="blur1"/>'
        '<feMergeNode in="SourceGraphic"/></feMerge></filter></defs>'
    ]

    for tick in range(5):
        value = y_min + (y_max - y_min) * tick / 4
        y = y_pos(value)

        svg.append(
            f'<line x1="{left}" y1="{y:.1f}" '
            f'x2="{width-right}" y2="{y:.1f}" '
            'stroke="rgba(160,190,230,0.16)" stroke-width="1"/>'
        )

        svg.append(
            f'<text x="{left-9}" y="{y+4:.1f}" text-anchor="end" '
            'fill="#A9BCD8" font-size="10">'
            f'{html.escape(_format_value(value))}</text>'
        )

    if chart_type == "line":
        points = " ".join(
            f"{x_pos(i):.1f},{y_pos(v):.1f}"
            for i, v in enumerate(numeric_values)
        )

        svg.append(
            f'<polyline points="{points}" fill="none" stroke="#18CFFF" '
            'stroke-width="7" opacity="0.28" filter="url(#neonGlow)" '
            'stroke-linecap="round" stroke-linejoin="round"/>'
        )

        svg.append(
            f'<polyline points="{points}" fill="none" stroke="#38E8FF" '
            'stroke-width="3" filter="url(#neonGlow)" '
            'stroke-linecap="round" stroke-linejoin="round"/>'
        )

        for i, value in enumerate(numeric_values):
            x, y = x_pos(i), y_pos(value)

            svg.append(
                f'<circle cx="{x:.1f}" cy="{y:.1f}" r="5" fill="#F06CCB" '
                'stroke="#FFFFFF" stroke-width="1.5" filter="url(#neonGlow)"/>'
            )

    else:
        count = len(numeric_values)
        slot = plot_w / max(count, 1)
        bar_w = min(42, slot * 0.58)
        base_y = y_pos(0)

        for i, value in enumerate(numeric_values):
            x = left + i * slot + (slot - bar_w) / 2
            y = y_pos(value)
            bar_h = max(1, base_y - y)

            svg.append(
                f'<rect x="{x:.1f}" y="{y:.1f}" width="{bar_w:.1f}" '
                f'height="{bar_h:.1f}" rx="5" fill="#18CFFF" opacity="0.88" '
                'filter="url(#neonGlow)"/>'
            )

    step = max(1, math.ceil(len(labels) / 9))

    for i, label in enumerate(labels):
        if i % step == 0 or i == len(labels) - 1:
            x = (
                x_pos(i) if chart_type == "line"
                else left + i * (plot_w / max(len(labels), 1))
                + (plot_w / max(len(labels), 1)) / 2
            )

            text_label = str(label)

            if len(text_label) > 13:
                text_label = text_label[:12] + "…"

            svg.append(
                f'<text x="{x:.1f}" y="{height-25}" text-anchor="middle" '
                'fill="#B9C8DF" font-size="10">'
                f'{html.escape(text_label)}</text>'
            )

    svg.append("</svg></div>")
    st.markdown("".join(svg), unsafe_allow_html=True)


def show_analytics_chart(
    title,
    endpoint,
    chart_type="bar",
    label_names=("labels", "months", "categories", "states", "payment_types"),
    value_names=("values", "revenue", "counts", "orders", "scores")
):
    payload = get_api_data(endpoint)
    frame = chart_dataframe(payload, label_names, value_names)

    if frame.empty:
        st.markdown(
            f'<div class="chart-panel"><div class="chart-heading">{html.escape(title)}</div>'
            '<div class="chart-empty">No chart data available.</div></div>',
            unsafe_allow_html=True
        )
        return

    if isinstance(frame.index, pd.RangeIndex):
        if len(frame.columns) >= 2:
            frame = frame.set_index(frame.columns[0])
        elif len(frame.columns) == 1:
            frame.index = frame.iloc[:, 0].astype(str)
            frame = pd.DataFrame(
                {"Value": frame.iloc[:, 0].values},
                index=frame.index
            )

    numeric = frame.select_dtypes(include="number")

    if numeric.empty:
        st.markdown(
            f'<div class="chart-panel"><div class="chart-heading">{html.escape(title)}</div>'
            '<div class="chart-empty">No numeric values for this chart.</div></div>',
            unsafe_allow_html=True
        )
        return

    series = numeric.iloc[:, 0]

    render_svg_chart(
        title,
        [str(x) for x in series.index.tolist()],
        series.tolist(),
        chart_type
    )


# ---------------- DESIGN ----------------
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap');

.stApp {
    background-image:
        linear-gradient(rgba(24,207,255,0.045) 1px, transparent 1px),
        linear-gradient(90deg, rgba(232,77,173,0.045) 1px, transparent 1px),
        radial-gradient(circle at 10% 15%, #102F60, transparent 35%),
        radial-gradient(circle at 90% 80%, #48144F, transparent 35%),
        linear-gradient(135deg, #050B1B, #101B38, #080D20);
    background-size: 35px 35px, 35px 35px, auto, auto, auto;
    color: #F4F8FF;
    font-family: 'Inter', sans-serif;
}

header[data-testid="stHeader"] {
    background: transparent;
    height: 0;
    visibility: hidden;
}

#MainMenu, footer { visibility: hidden; }

.block-container {
    padding-top: 2rem;
    padding-bottom: 3rem;
    max-width: 1450px;
    position: relative;
    z-index: 1;
}

section[data-testid="stSidebar"] {
    background: linear-gradient(180deg, #091832, #142B55, #351A49);
    border-right: 1px solid rgba(24,207,255,0.5);
}

section[data-testid="stSidebar"] * {
    font-family: 'Inter', sans-serif;
}

div[data-testid="stVerticalBlockBorderWrapper"] {
    background: transparent !important;
    border: none !important;
    box-shadow: none !important;
    padding: 0 !important;
}

.sticker {
    position: fixed;
    width: 230px;
    height: 230px;
    display: flex;
    align-items: center;
    justify-content: center;
    border-radius: 50px;
    background: linear-gradient(135deg, rgba(24,207,255,0.09),
        rgba(232,77,173,0.035), transparent 85%);
    border: 1px solid rgba(24,207,255,0.13);
    box-shadow: 0 0 55px rgba(24,207,255,0.08),
        inset 0 0 35px rgba(232,77,173,0.04);
    opacity: 0.32;
    pointer-events: none;
    z-index: 0;
    backdrop-filter: blur(2px);
}

.sticker svg {
    width: 150px;
    height: 150px;
    stroke: rgba(98,232,255,0.75);
    stroke-width: 1.4;
    fill: none;
    filter: drop-shadow(0 0 15px rgba(24,207,255,0.35));
}

.sticker1 { top: 10%; left: 4%; }
.sticker2 { top: 36%; right: 4%; }
.sticker3 { bottom: 5%; left: 42%; }

.stButton > button, .stFormSubmitButton > button {
    background: linear-gradient(100deg, #087DCE, #18CFFF, #E84DAD);
    color: white;
    border: none;
    border-radius: 10px;
    font-weight: 700;
    padding: 8px 18px;
}

.stButton > button:hover, .stFormSubmitButton > button:hover {
    box-shadow: 0 0 18px #18CFFF99;
}

.stTextInput input {
    background: #102746;
    color: white;
    border: 1px solid #18CFFF;
    border-radius: 9px;
}

div[data-testid="stMetric"] {
    background: linear-gradient(135deg, rgba(16,45,85,0.62), rgba(66,32,77,0.62));
    border: 1px solid rgba(24,207,255,0.75);
    border-radius: 15px;
    padding: 18px;
    box-shadow: 0 0 16px rgba(24,207,255,0.28);
}

h1 { font-size: 27px !important; font-weight: 700 !important; }
h2 { font-size: 21px !important; font-weight: 600 !important; }
h3 { font-size: 17px !important; font-weight: 600 !important; }

h1, h2, h3 {
    color: #F4F8FF !important;
    font-family: 'Inter', sans-serif !important;
}

div[data-testid="stDataFrame"] {
    border: 1px solid rgba(24,207,255,0.3);
    border-radius: 10px;
}

.chart-panel {
    width: 100%;
    box-sizing: border-box;
    padding: 12px 13px 7px;
    margin: 5px 0 14px;
    border: 1px solid rgba(24,207,255,0.32);
    border-radius: 14px;
    background: rgba(11,25,52,0.20);
    box-shadow: 0 0 18px rgba(24,207,255,0.08),
                inset 0 0 20px rgba(232,77,173,0.035);
    backdrop-filter: blur(5px);
}

.chart-heading {
    color: #EAF8FF;
    font-family: 'Inter', sans-serif;
    font-size: 15px;
    font-weight: 650;
    padding: 1px 5px 3px;
}

.chart-empty {
    color: #B9C8DF;
    font-size: 12px;
    padding: 24px 5px;
}
</style>
""", unsafe_allow_html=True)

sticker_html = """
<div class="sticker sticker1"><svg viewBox="0 0 24 24">
<path d="M3 3v18h18 M7 14v4 M12 9v9 M17 4v14"/></svg></div>
<div class="sticker sticker2"><svg viewBox="0 0 24 24">
<path d="M3 3h2l3 12h11l3-9H6 M10 20h.01 M18 20h.01"/></svg></div>
<div class="sticker sticker3"><svg viewBox="0 0 24 24">
<path d="M3 7l9-4 9 4v10l-9 4-9-4z M3 7l9 4 9-4 M12 11v10"/></svg></div>
"""

st.markdown(sticker_html, unsafe_allow_html=True)


# ---------------- LOGIN AND REGISTRATION ----------------
if not st.session_state.logged_in:

    st.markdown("<br><br><br>", unsafe_allow_html=True)

    left, center, right = st.columns([1, 1.5, 1])

    with center:
        with st.container(border=True):

            st.markdown(
                "<h1 style='text-align:center;color:#24D5FF;'>OLIST ANALYTICS</h1>",
                unsafe_allow_html=True
            )

            st.markdown(
                "<p style='text-align:center;color:#F06CCB;'>Brazilian E-Commerce Analytics</p>",
                unsafe_allow_html=True
            )

            login_tab, register_tab = st.tabs(
                ["Login", "Register"]
            )

            with login_tab:
                st.markdown("### Welcome Back")

                with st.form("login_form"):
                    username = st.text_input("Username")
                    password = st.text_input("Password", type="password")

                    submitted = st.form_submit_button(
                        "LOGIN",
                        use_container_width=True
                    )

                    if submitted:
                        result = api_request(
                            "POST",
                            "/api/auth/login",
                            json={
                                "username": username,
                                "password": password
                            }
                        )

                        if result and result.get("access_token"):
                            st.session_state.access_token = result["access_token"]
                            st.session_state.username = result["username"]
                            st.session_state.role = result["role"]
                            st.session_state.logged_in = True
                            st.rerun()

            with register_tab:
                st.markdown("### Create an Account")
                st.caption("New accounts require administrator approval.")

                with st.form("register_form"):
                    new_username = st.text_input(
                        "Choose Username",
                        key="register_username"
                    )

                    new_password = st.text_input(
                        "Choose Password",
                        type="password",
                        key="register_password"
                    )

                    confirm_password = st.text_input(
                        "Confirm Password",
                        type="password"
                    )

                    register_clicked = st.form_submit_button(
                        "REGISTER",
                        use_container_width=True
                    )

                    if register_clicked:
                        if new_password != confirm_password:
                            st.error("Passwords do not match.")

                        elif len(new_username.strip()) < 3:
                            st.error("Username must contain at least 3 characters.")

                        elif len(new_password) < 8:
                            st.error("Password must contain at least 8 characters.")

                        else:
                            result = api_request(
                                "POST",
                                "/api/auth/register",
                                json={
                                    "username": new_username,
                                    "password": new_password
                                }
                            )

                            if result:
                                st.success(
                                    "Registration submitted. "
                                    "Wait for administrator approval."
                                )


# ---------------- MAIN APP ----------------
else:

    # Confirm the session is still valid and the account is approved.
    current_user = get_api_data("/api/auth/me")

    if not current_user:
        logout()

    st.session_state.role = current_user["role"]
    st.session_state.username = current_user["username"]

    is_admin = st.session_state.role == "admin"

    with st.sidebar:
        st.markdown("## 💠 OLIST ANALYTICS")
        st.caption("Brazilian E-Commerce Analytics")
        st.divider()

        st.markdown("### Company Information")
        st.write("🇧🇷 Country: Brazil")
        st.write("🏢 Olist E-Commerce Dataset")
        st.write("📍 Curitiba, Paraná")

        st.divider()
        st.markdown("### Navigation")

        pages = [
            "Overview Dashboard",
            "Database Tables",
            *[f"Table: {name}" for name in TABLES],
            "Reports & Export",
        ]

        if is_admin:
            pages += [
                "Data Management",
                "Admin Settings"
            ]

        page = st.radio(
            "Select a page",
            pages,
            label_visibility="collapsed"
        )

        st.divider()

        st.caption(f"Logged in as: {st.session_state.username}")
        st.caption(
            "Administrator" if is_admin else "Approved Viewer"
        )

        if st.button("🚪 Logout", use_container_width=True):
            logout()

    st.markdown(
        "<h1 style='color:#24D5FF;'>Olist E-Commerce Analytics</h1>",
        unsafe_allow_html=True
    )

    # ---------------- DASHBOARD ----------------
    if page == "Overview Dashboard":

        st.subheader("Overview Dashboard")
        st.write("Olist database administration and business data.")

        summary = get_api_data("/api/analytics/summary")

        if summary:
            c1, c2, c3, c4, c5 = st.columns(5)

            c1.metric(
                "Total Revenue",
                f"R$ {summary['total_revenue']:,.2f}"
            )

            c2.metric(
                "Total Orders",
                f"{summary['total_orders']:,}"
            )

            c3.metric(
                "Average Order Value",
                f"R$ {summary['avg_order_value']:,.2f}"
            )

            c4.metric(
                "Average Review Score",
                f"{summary['avg_review_score']:.2f}/5"
            )

            c5.metric(
                "Late Deliveries",
                f"{summary['pct_late_deliveries']:.2f}%"
            )

        st.divider()
        st.markdown("### Business Analytics")

        left, right = st.columns(2)

        with left:
            show_analytics_chart(
                "Monthly Revenue",
                "/api/analytics/revenue-by-month",
                "line",
                ("labels", "months", "month"),
                ("values", "revenue", "total_revenue")
            )

        with right:
            show_analytics_chart(
                "Top Product Categories",
                "/api/analytics/top-categories",
                "bar",
                ("labels", "categories", "category"),
                ("values", "counts", "revenue", "orders")
            )

        left, right = st.columns(2)

        with left:
            show_analytics_chart(
                "Orders by State",
                "/api/analytics/orders-by-state",
                "bar",
                ("labels", "states", "state"),
                ("values", "counts", "orders")
            )

        with right:
            show_analytics_chart(
                "Payment Types",
                "/api/analytics/payment-types",
                "bar",
                ("labels", "payment_types", "payment_type"),
                ("values", "counts", "values")
            )

        show_analytics_chart(
            "Review vs Delivery",
            "/api/analytics/review-vs-delivery",
            "bar",
            ("labels", "delivery_status", "review_scores"),
            ("values", "counts", "values")
        )

        st.info(
            "Use Database Tables in the sidebar to view Olist records."
        )

    # ---------------- DATABASE TABLES ----------------
    elif page == "Database Tables":

        st.subheader("Database Tables")
        st.write("Choose a table from the sidebar to view its records.")

        for label, table_name in TABLES.items():
            st.write(f"• **{label}** — `{table_name}`")

    # ---------------- INDIVIDUAL TABLES ----------------
    elif page.startswith("Table: "):

        label = page.replace("Table: ", "", 1)
        show_table_manager(label, TABLES[label])

    # ---------------- REPORTS ----------------
    elif page == "Reports & Export":

        st.subheader("Reports & Export")

        summary = get_api_data("/api/analytics/summary")

        if summary:
            report = pd.DataFrame(
                list(summary.items()),
                columns=["Metric", "Value"]
            )

            st.dataframe(
                report,
                use_container_width=True,
                hide_index=True
            )

            st.download_button(
                "Download Summary CSV",
                report.to_csv(index=False).encode("utf-8"),
                "olist_summary_report.csv",
                "text/csv"
            )

    # ---------------- DATA MANAGEMENT ----------------
    elif page == "Data Management":

        if not is_admin:
            st.error("Administrator access required.")
            st.stop()

        st.subheader("Data Management")

        st.info(
            "Select a table from the sidebar to add, edit, "
            "or delete individual records."
        )

        st.warning(
            "Bulk CSV-to-MySQL import needs a dedicated backend "
            "import endpoint. This page currently previews CSV files only."
        )

        uploaded = st.file_uploader(
            "Preview a CSV file",
            type=["csv"]
        )

        if uploaded:
            try:
                csv_df = pd.read_csv(uploaded)

                st.caption(f"{len(csv_df):,} rows")

                st.dataframe(
                    csv_df.head(10),
                    use_container_width=True
                )

            except Exception as error:
                st.error(f"Could not read CSV: {error}")

    # ---------------- ADMIN SETTINGS ----------------
    elif page == "Admin Settings":

        if not is_admin:
            st.error("Administrator access required.")
            st.stop()

        st.subheader("Admin Settings")

        st.write("Application: Olist E-Commerce Analytics")
        st.write("Database: ecommerce_analytics")
        st.write("Backend: FastAPI")
        st.write("Frontend: Streamlit")

        st.divider()
        st.markdown("### User Approval Management")

        pending = get_api_data("/api/auth/pending-users")

        if pending is not None:
            users = pending.get("users", [])

            if not users:
                st.success("There are no pending registration requests.")

            else:
                for user in users:
                    username = user["username"]

                    col1, col2, col3 = st.columns([3, 1, 1])

                    with col1:
                        st.write(f"👤 **{username}**")

                    with col2:
                        if st.button(
                            "Approve",
                            key=f"approve_{username}"
                        ):
                            result = api_request(
                                "POST",
                                f"/api/auth/approve/{username}"
                            )

                            if result:
                                st.success(f"{username} approved.")
                                st.rerun()

                    with col3:
                        if st.button(
                            "Reject",
                            key=f"reject_{username}"
                        ):
                            result = api_request(
                                "DELETE",
                                f"/api/auth/reject/{username}"
                            )

                            if result:
                                st.success(f"{username} rejected.")
                                st.rerun()

        st.divider()

        st.info(
            "Independent analytics project using the public "
            "Olist Brazilian e-commerce dataset."
        )
