import json
import os
import html
from io import BytesIO

import streamlit as st


st.set_page_config(
    page_title="War Room Binder",
    page_icon="📘",
    layout="wide",
    initial_sidebar_state="collapsed",
)

DB_FILE = "runbooks_db.json"


DEFAULT_DATA = [
    {
        "id": "err-crashloop",
        "title": "CrashLoopBackOff",
        "category": "Kubernetes",
        "type": "runbook",
        "status": "active",
        "impact": "high",
        "author": "DevOps",
        "tags": ["kubernetes", "pod"],
        "cause": "Missing environment variables, database connection refused, or OOMKilled.",
        "solution": (
            "kubectl logs -n production -l app=my-app --tail=100 --previous\n"
            "kubectl describe pod -n production -l app=my-app"
        ),
        "verification": [
            "Check pod status and restart count.",
            "Review previous container logs.",
            "Confirm environment variables and resource limits.",
        ],
    },
    {
        "id": "err-502",
        "title": "502 Bad Gateway",
        "category": "Ingress",
        "type": "runbook",
        "status": "active",
        "impact": "high",
        "author": "DevOps",
        "tags": ["ingress", "gateway"],
        "cause": "Backend pod unreachable, service target port mismatch, or failed readiness probe.",
        "solution": (
            "kubectl get pods -n production -l app=my-app\n"
            "kubectl get endpoints my-app-service -n production"
        ),
        "verification": [
            "Confirm backend pods are running.",
            "Check service endpoints.",
            "Verify readiness probes.",
        ],
    },
    {
        "id": "err-db-conn",
        "title": "Database Connection Exhausted",
        "category": "Database",
        "type": "runbook",
        "status": "active",
        "impact": "high",
        "author": "DevOps",
        "tags": ["database", "postgresql"],
        "cause": "Application connection leak or sudden traffic spike without pooler (PgBouncer).",
        "solution": (
            "SELECT count(*), state FROM pg_stat_activity GROUP BY state;\n"
            "SELECT pg_terminate_backend(pid) FROM pg_stat_activity "
            "WHERE state = 'idle';"
        ),
        "verification": [
            "Check active PostgreSQL connections.",
            "Review PgBouncer pool usage.",
            "Confirm application connection count returns to normal.",
        ],
    },
]


# =========================================================
# CSS
# =========================================================

st.markdown(
    """
    <style>

    .stApp {
        background: #edf6fa;
        color: #10212b;
    }

    .main .block-container {
        max-width: 1500px;
        padding-top: 1.2rem;
        padding-bottom: 3rem;
    }

    header[data-testid="stHeader"] {
        background: transparent;
    }

    footer {
        visibility: hidden;
    }

    .top-header {
        display: flex;
        align-items: center;
        justify-content: space-between;
        padding: 4px 0 14px 0;
        border-bottom: 1px solid #cbdde5;
        margin-bottom: 26px;
    }

    .brand-wrapper {
        display: flex;
        align-items: center;
        gap: 10px;
    }

    .brand-icon {
        width: 34px;
        height: 34px;
        border-radius: 8px;
        background: #18859a;
        color: white;
        display: flex;
        align-items: center;
        justify-content: center;
        font-family: monospace;
        font-size: 10px;
        font-weight: 700;
    }

    .brand-small {
        font-family: monospace;
        font-size: 9px;
        letter-spacing: 2px;
        color: #237187;
        text-transform: uppercase;
    }

    .brand-name {
        font-size: 14px;
        font-weight: 700;
        color: #0b1820;
        margin-top: 2px;
    }

    .page-title {
        font-size: 25px;
        font-weight: 750;
        letter-spacing: -0.7px;
        color: #07151e;
        margin-bottom: 3px;
    }

    .page-subtitle {
        color: #58717d;
        font-size: 12px;
        margin-bottom: 17px;
    }

    .doc-count {
        text-align: right;
        font-family: monospace;
        color: #607d89;
        font-size: 10px;
        margin-top: -35px;
        margin-bottom: 18px;
    }

    .search-panel {
        background: rgba(255,255,255,0.42);
        border: 1px solid #cbdfe7;
        border-radius: 16px;
        padding: 11px;
        margin-bottom: 15px;
    }

    .runbook-card {
        background: rgba(255,255,255,0.55);
        border: 1px solid #cbdfe7;
        border-radius: 15px;
        padding: 14px 15px;
        min-height: 170px;
        margin-bottom: 4px;
        transition: 0.15s ease;
    }

    .runbook-card:hover {
        border-color: #72bfce;
        background: rgba(255,255,255,0.75);
    }

    .card-top {
        display: flex;
        align-items: center;
        justify-content: space-between;
        margin-bottom: 8px;
    }

    .type-badge {
        display: inline-block;
        padding: 3px 8px;
        border-radius: 8px;
        background: #d9eef3;
        color: #18768a;
        font-family: monospace;
        font-size: 8px;
        letter-spacing: 0.5px;
        text-transform: uppercase;
        border: 1px solid #c2e2e9;
    }

    .incident-badge {
        background: #fae8dc;
        color: #c55416;
        border-color: #f1d2c1;
    }

    .infra-badge {
        background: #dceff3;
        color: #17778b;
    }

    .cicd-badge {
        background: #e7e6f2;
        color: #625f91;
    }

    .onboarding-badge {
        background: #e8eedf;
        color: #647d38;
    }

    .status {
        font-family: monospace;
        font-size: 8px;
        color: #66808b;
    }

    .status-dot {
        color: #118749;
        font-size: 11px;
    }

    .resolved-dot {
        color: #c85a13;
    }

    .card-title {
        font-size: 13px;
        font-weight: 700;
        color: #142832;
        margin-bottom: 5px;
    }

    .card-description {
        font-size: 10px;
        line-height: 1.55;
        color: #627a85;
        min-height: 32px;
    }

    .tag {
        display: inline-block;
        background: #e4edf0;
        color: #617984;
        border-radius: 8px;
        padding: 2px 7px;
        margin-right: 4px;
        font-family: monospace;
        font-size: 7px;
    }

    .card-divider {
        border-top: 1px solid #d4e1e5;
        margin: 10px 0 8px 0;
    }

    .card-footer {
        display: flex;
        justify-content: space-between;
        color: #78909a;
        font-family: monospace;
        font-size: 8px;
    }

    .reading-pane {
        background: rgba(255,255,255,0.52);
        border: 1px solid #cbdfe7;
        border-radius: 15px;
        overflow: hidden;
    }

    .reading-header {
        padding: 12px 14px;
        border-bottom: 1px solid #d3e1e5;
        display: flex;
        justify-content: space-between;
        font-family: monospace;
        font-size: 8px;
        color: #66808b;
        letter-spacing: 1px;
        text-transform: uppercase;
    }

    .reading-content {
        padding: 15px;
    }

    .reading-title {
        font-size: 14px;
        font-weight: 750;
        color: #142832;
        margin-bottom: 7px;
    }

    .reading-description {
        color: #607984;
        font-size: 10px;
        line-height: 1.55;
        margin-bottom: 12px;
    }

    .verification-box {
        border: 1px solid #d5e2e6;
        border-radius: 10px;
        background: rgba(255,255,255,0.65);
        padding: 11px;
        margin-top: 10px;
    }

    .verification-title {
        font-family: monospace;
        color: #718a94;
        font-size: 8px;
        letter-spacing: 1px;
        margin-bottom: 8px;
    }

    .verification-item {
        font-size: 9px;
        color: #536d78;
        margin: 7px 0;
        line-height: 1.4;
    }

    .verification-item::before {
        content: "▪";
        color: #18859a;
        margin-right: 7px;
    }

    .command-box {
        background: #0a202b;
        border-radius: 11px;
        padding: 14px;
        color: #d8edf2;
        font-family: monospace;
        font-size: 10px;
        line-height: 1.65;
        white-space: pre-wrap;
        overflow-x: auto;
        margin-top: 10px;
    }

    .mode-card {
        background: rgba(255,255,255,0.5);
        border: 1px solid #cbdfe7;
        border-radius: 16px;
        padding: 12px;
        margin-bottom: 18px;
    }

    .runbook-large {
        background: rgba(255,255,255,0.72);
        border: 1px solid #cbdfe7;
        border-radius: 16px;
        margin-bottom: 16px;
        overflow: hidden;
    }

    .large-header {
        padding: 12px 16px;
        border-bottom: 1px solid #d7e3e7;
        display: flex;
        align-items: center;
        justify-content: space-between;
    }

    .number-circle {
        display: inline-flex;
        width: 20px;
        height: 20px;
        border-radius: 50%;
        background: #0b8249;
        color: white;
        align-items: center;
        justify-content: center;
        font-family: monospace;
        font-size: 8px;
        margin-right: 8px;
    }

    .number-circle-high {
        background: #d05b18;
    }

    .large-title {
        font-size: 12px;
        font-weight: 750;
        color: #10232d;
    }

    .impact {
        font-family: monospace;
        font-size: 8px;
        color: #c75a18;
    }

    .impact-low {
        color: #16804b;
    }

    .large-body {
        display: grid;
        grid-template-columns: 2.2fr 1fr;
    }

    .large-main {
        padding: 15px 18px;
        border-right: 1px solid #d7e3e7;
    }

    .large-verification {
        padding: 15px 18px;
    }

    .large-description {
        color: #486572;
        font-size: 10px;
        line-height: 1.6;
        margin-bottom: 9px;
    }

    .mono-label {
        font-family: monospace;
        color: #718a94;
        font-size: 8px;
        letter-spacing: 1px;
        text-transform: uppercase;
    }

    [data-testid="stSidebar"] {
        background: #f4fafc;
    }

    [data-testid="stSidebar"] .block-container {
        padding-top: 2rem;
    }

    .stButton > button {
        border-radius: 9px;
        border: 1px solid #c8dce3;
        background: #f8fcfd;
        color: #18313d;
        font-size: 10px;
    }

    .stButton > button:hover {
        border-color: #19869b;
        color: #12758a;
    }

    div[data-testid="stDownloadButton"] button {
        border-radius: 9px;
    }

    @media (max-width: 900px) {
        .large-body {
            display: block;
        }

        .large-main {
            border-right: none;
            border-bottom: 1px solid #d7e3e7;
        }
    }

    </style>
    """,
    unsafe_allow_html=True,
)


# =========================================================
# DATA
# =========================================================

def normalize_runbook(r):
    r.setdefault("type", "runbook")
    r.setdefault("status", "active")
    r.setdefault("impact", "medium")
    r.setdefault("author", "DevOps")
    r.setdefault("tags", [])
    r.setdefault("cause", "")
    r.setdefault("solution", "")

    if not isinstance(r["tags"], list):
        r["tags"] = [str(r["tags"])]

    r.setdefault(
        "verification",
        [
            "Review the service status.",
            "Confirm the remediation was successful.",
        ],
    )

    return r


def save_data(data):
    with open(DB_FILE, "w", encoding="utf-8") as f:
        json.dump(
            data,
            f,
            indent=2,
            ensure_ascii=False,
        )


def load_data():
    if not os.path.exists(DB_FILE):
        data = [
            normalize_runbook(x)
            for x in DEFAULT_DATA
        ]
        save_data(data)
        return data

    try:
        with open(DB_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)

        if not isinstance(data, list):
            raise ValueError("Invalid database format")

        return [
            normalize_runbook(x)
            for x in data
        ]

    except (
        json.JSONDecodeError,
        OSError,
        ValueError,
    ):
        return [
            normalize_runbook(x)
            for x in DEFAULT_DATA
        ]


runbooks = load_data()


# =========================================================
# SESSION STATE
# =========================================================

if "selected_id" not in st.session_state:
    st.session_state.selected_id = (
        runbooks[0]["id"]
        if runbooks
        else None
    )

if "mode" not in st.session_state:
    st.session_state.mode = "Knowledge Base"

if "kb_filter" not in st.session_state:
    st.session_state.kb_filter = "All"

if "impact_filter" not in st.session_state:
    st.session_state.impact_filter = "standard"


# =========================================================
# HELPERS
# =========================================================

def get_type_class(runbook_type):
    value = str(runbook_type).lower()

    if "incident" in value:
        return "incident-badge"

    if "infra" in value:
        return "infra-badge"

    if "ci" in value:
        return "cicd-badge"

    if "onboard" in value:
        return "onboarding-badge"

    return ""


def get_type_label(runbook):
    value = str(
        runbook.get("type", "runbook")
    ).lower()

    mapping = {
        "runbook": "RUNBOOK",
        "incident": "INCIDENT",
        "infra": "INFRA",
        "ci/cd": "CI/CD",
        "cicd": "CI/CD",
        "onboarding": "ONBOARDING",
    }

    return mapping.get(
        value,
        value.upper(),
    )


def status_html(runbook):
    status = str(
        runbook.get("status", "active")
    ).lower()

    if status == "resolved":
        return (
            '<span class="status-dot resolved-dot">'
            "●"
            "</span> resolved"
        )

    return (
        '<span class="status-dot">●</span> active'
    )


def tags_html(runbook):
    tags = runbook.get("tags", [])

    if not tags:
        return ""

    return "".join(
        f'<span class="tag">'
        f'{html.escape(str(tag))}'
        f"</span>"
        for tag in tags[:4]
    )


def card_html(runbook):
    type_label = get_type_label(runbook)

    type_class = get_type_class(
        runbook.get("type", "runbook")
    )

    return f"""
    <div class="runbook-card">

        <div class="card-top">
            <span class="type-badge {type_class}">
                {html.escape(type_label)}
            </span>

            <span class="status">
                {status_html(runbook)}
            </span>
        </div>

        <div class="card-title">
            {html.escape(
                str(runbook.get("title", ""))
            )}
        </div>

        <div class="card-description">
            {html.escape(
                str(runbook.get("cause", ""))
            )}
        </div>

        <div style="margin-top: 8px;">
            {tags_html(runbook)}
        </div>

        <div class="card-divider"></div>

        <div class="card-footer">
            <span>
                {html.escape(
                    str(
                        runbook.get(
                            "author",
                            "DevOps"
                        )
                    )
                )}
            </span>

            <span>
                {html.escape(
                    str(
                        runbook.get(
                            "id",
                            ""
                        )
                    )
                )}
            </span>
        </div>

    </div>
    """


# =========================================================
# PDF
# =========================================================

def generate_pdf(runbooks):
    from xhtml2pdf import pisa

    cards_html = ""

    for r in runbooks:

        cause = html.escape(
            str(r.get("cause", ""))
        )

        solution = html.escape(
            str(r.get("solution", ""))
        )

        cards_html += f"""
        <div style="
            background-color:#ffffff;
            border:1px solid #d5e1e5;
            padding:12px;
            margin-bottom:12px;
        ">

            <div style="
                font-size:11pt;
                font-weight:bold;
                color:#0f172a;
                margin-bottom:5px;
            ">
                [{html.escape(
                    get_type_label(r)
                )}]
                {html.escape(
                    str(r.get("id", ""))
                )}
                -
                {html.escape(
                    str(r.get("title", ""))
                )}
            </div>

            <div style="margin-bottom:7px;">
                <strong>Root Cause:</strong>
                {cause}
            </div>

            <div style="
                background-color:#0f2029;
                color:#f8fafc;
                padding:10px;
                font-family:monospace;
                white-space:pre-wrap;
            ">
                {solution}
            </div>

        </div>
        """

    html_content = f"""
    <!DOCTYPE html>
    <html>

    <head>
        <meta charset="UTF-8">

        <style>

            @page {{
                size: A4;
                margin: 12mm;
            }}

            body {{
                font-family: Helvetica, Arial, sans-serif;
                font-size: 9pt;
                color: #1e293b;
            }}

            h1 {{
                color: #0f172a;
                border-bottom: 2px solid #cbd5e1;
                padding-bottom: 6px;
                font-size: 16pt;
            }}

            .meta {{
                color: #64748b;
                font-size: 8pt;
                margin-bottom: 16px;
            }}

        </style>
    </head>

    <body>

        <h1>
            DevOps Operations Manual
        </h1>

        <div class="meta">
            Internal Infrastructure &
            Incident Resolution Guides
        </div>

        {cards_html}

    </body>
    </html>
    """

    output = BytesIO()

    result = pisa.CreatePDF(
        html_content,
        dest=output,
    )

    if result.err:
        raise RuntimeError(
            "PDF generation gagal."
        )

    return output.getvalue()


# =========================================================
# HEADER
# =========================================================

st.markdown(
    """
    <div class="top-header">

        <div class="brand-wrapper">

            <div class="brand-icon">
                OPS
            </div>

            <div>

                <div class="brand-small">
                    Documentation Archive
                </div>

                <div class="brand-name">
                    War Room Binder
                </div>

            </div>

        </div>

    </div>
    """,
    unsafe_allow_html=True,
)


# =========================================================
# MODE SWITCH
# =========================================================

mode_col1, mode_col2, mode_spacer = st.columns(
    [1, 1, 4]
)

with mode_col1:

    if st.button(
        "Knowledge Base",
        use_container_width=True,
    ):
        st.session_state.mode = (
            "Knowledge Base"
        )
        st.rerun()


with mode_col2:

    if st.button(
        "Runbook Mode",
        use_container_width=True,
    ):
        st.session_state.mode = (
            "Runbook Mode"
        )
        st.rerun()


st.markdown(
    "<br>",
    unsafe_allow_html=True,
)


# =========================================================
# SIDEBAR
# =========================================================

with st.sidebar:

    st.markdown("### Operations")

    st.caption(
        "Internal documentation and infrastructure runbooks."
    )

    st.markdown("---")

    st.markdown("### Add Runbook")

    with st.form(
        "add_runbook_form",
        clear_on_submit=True,
    ):

        new_id = st.text_input(
            "ID",
            placeholder="err-pod-oom",
        )

        new_title = st.text_input(
            "Title",
            placeholder="Pod OOMKilled Exception",
        )

        new_type = st.selectbox(
            "Type",
            [
                "runbook",
                "incident",
                "infra",
                "ci/cd",
                "onboarding",
            ],
        )

        new_category = st.text_input(
            "Category",
            placeholder="Kubernetes",
        )

        new_status = st.selectbox(
            "Status",
            [
                "active",
                "resolved",
            ],
        )

        new_impact = st.selectbox(
            "Impact",
            [
                "low",
                "medium",
                "high",
            ],
        )

        new_author = st.text_input(
            "Author",
            value="DevOps",
        )

        new_tags = st.text_input(
            "Tags",
            placeholder=(
                "kubernetes, pod, production"
            ),
        )

        new_cause = st.text_area(
            "Description / Root Cause"
        )

        new_solution = st.text_area(
            "Commands / Solution"
        )

        new_verification = st.text_area(
            "Verification Steps",
            placeholder=(
                "Check pod status\n"
                "Review logs\n"
                "Verify service health"
            ),
        )

        submit_btn = st.form_submit_button(
            "Save Entry",
            use_container_width=True,
        )

        if submit_btn:

            if (
                not new_id.strip()
                or not new_title.strip()
                or not new_category.strip()
            ):

                st.error(
                    "ID, Title, dan Category wajib diisi."
                )

            elif any(
                item.get("id")
                == new_id.strip()
                for item in runbooks
            ):

                st.error(
                    "ID tersebut sudah digunakan."
                )

            else:

                verification = [
                    x.strip()
                    for x in new_verification.splitlines()
                    if x.strip()
                ]

                tags = [
                    x.strip()
                    for x in new_tags.split(",")
                    if x.strip()
                ]

                new_entry = {
                    "id": new_id.strip(),
                    "title": new_title.strip(),
                    "category": new_category.strip(),
                    "type": new_type,
                    "status": new_status,
                    "impact": new_impact,
                    "author": (
                        new_author.strip()
                        or "DevOps"
                    ),
                    "tags": tags,
                    "cause": new_cause.strip(),
                    "solution": new_solution.strip(),
                    "verification": verification,
                }

                runbooks.append(new_entry)

                save_data(runbooks)

                st.session_state.selected_id = (
                    new_entry["id"]
                )

                st.success(
                    "Runbook saved."
                )

                st.rerun()

    st.markdown("---")

    st.markdown("### Export")

    if st.button(
        "Generate PDF Report",
        use_container_width=True,
    ):

        try:

            pdf_bytes = generate_pdf(
                runbooks
            )

            st.download_button(
                "Download PDF",
                data=pdf_bytes,
                file_name="devops_runbooks.pdf",
                mime="application/pdf",
                use_container_width=True,
            )

        except ImportError:

            st.error(
                "xhtml2pdf belum terinstall. "
                "Jalankan: pip install xhtml2pdf"
            )

        except Exception as exc:

            st.error(
                f"PDF generation gagal: {exc}"
            )


# =========================================================
# KNOWLEDGE BASE MODE
# =========================================================

if st.session_state.mode == "Knowledge Base":

    st.markdown(
        '<div class="page-title">'
        "Knowledge Base"
        "</div>",
        unsafe_allow_html=True,
    )

    st.markdown(
        '<div class="page-subtitle">'
        "Semua runbook, incident, infra, CI/CD, "
        "dan onboarding dalam satu binder."
        "</div>",
        unsafe_allow_html=True,
    )

    st.markdown(
        f'<div class="doc-count">'
        f"{len(runbooks)} docs"
        "</div>",
        unsafe_allow_html=True,
    )

    st.markdown(
        '<div class="search-panel">',
        unsafe_allow_html=True,
    )

    search_query = st.text_input(
        "Search",
        placeholder=(
            "⌕  Search runbooks, incidents, "
            "infra guides..."
        ),
        label_visibility="collapsed",
    )

    st.markdown(
        "</div>",
        unsafe_allow_html=True,
    )

    filter_col1, filter_col2, filter_col3, \
    filter_col4, filter_col5, filter_col6 = st.columns(
        [1, 1, 1, 1, 1, 1]
    )

    filters = [
        ("All", filter_col1),
        ("runbook", filter_col2),
        ("incident", filter_col3),
        ("infra", filter_col4),
        ("ci/cd", filter_col5),
        ("onboarding", filter_col6),
    ]

    for filter_name, column in filters:

        with column:

            label = (
                filter_name.upper()
                if filter_name != "All"
                else "ALL"
            )

            if st.button(
                label,
                use_container_width=True,
                key=f"filter_{filter_name}",
            ):

                st.session_state.kb_filter = (
                    filter_name
                )

                st.rerun()

    query = search_query.lower().strip()

    active_filter = (
        st.session_state.kb_filter.lower()
    )

    filtered_runbooks = []

    for r in runbooks:

        matches_search = (
            not query
            or query in str(
                r.get("id", "")
            ).lower()
            or query in str(
                r.get("title", "")
            ).lower()
            or query in str(
                r.get("cause", "")
            ).lower()
            or query in str(
                r.get("category", "")
            ).lower()
            or any(
                query in str(tag).lower()
                for tag in r.get("tags", [])
            )
        )

        matches_filter = (
            active_filter == "all"
            or str(
                r.get("type", "runbook")
            ).lower()
            == active_filter
        )

        if matches_search and matches_filter:
            filtered_runbooks.append(r)

    selected = None

    if filtered_runbooks:

        selected = next(
            (
                r
                for r in filtered_runbooks
                if r.get("id")
                == st.session_state.selected_id
            ),
            None,
        )

        if selected is None:

            selected = filtered_runbooks[0]

            st.session_state.selected_id = (
                selected.get("id")
            )

    left_col, right_col = st.columns(
        [2.2, 1],
        gap="medium",
    )

    with left_col:

        if not filtered_runbooks:

            st.info(
                "No documentation matches "
                "the current filter."
            )

        else:

            for idx, runbook in enumerate(
                filtered_runbooks
            ):

                st.markdown(
                    card_html(runbook),
                    unsafe_allow_html=True,
                )

                if st.button(
                    "Open document",
                    key=(
                        f"open_kb_"
                        f"{runbook.get('id')}_"
                        f"{idx}"
                    ),
                    use_container_width=True,
                ):

                    st.session_state.selected_id = (
                        runbook.get("id")
                    )

                    st.rerun()

    with right_col:

        if selected:

            verification_html = "".join(
                f"""
                <div class="verification-item">
                    {html.escape(str(step))}
                </div>
                """
                for step in selected.get(
                    "verification",
                    [],
                )
            )

            st.markdown(
                f"""
                <div class="reading-pane">

                    <div class="reading-header">

                        <span>
                            Reading Pane
                        </span>

                        <span>
                            {html.escape(
                                get_type_label(selected)
                            )}
                        </span>

                    </div>

                    <div class="reading-content">

                        <div class="reading-title">
                            {html.escape(
                                str(
                                    selected.get(
                                        "title",
                                        ""
                                    )
                                )
                            )}
                        </div>

                        <div class="reading-description">

                            <strong>ID:</strong>
                            {html.escape(
                                str(
                                    selected.get(
                                        "id",
                                        ""
                                    )
                                )
                            )}

                            <br><br>

                            {html.escape(
                                str(
                                    selected.get(
                                        "cause",
                                        ""
                                    )
                                )
                            )}

                        </div>

                        <div>
                            {tags_html(selected)}
                        </div>

                        <div class="verification-box">

                            <div class="verification-title">
                                VERIFICATION STEPS
                            </div>

                            {verification_html}

                        </div>

                    </div>

                </div>
                """,
                unsafe_allow_html=True,
            )

            if st.button(
                "Open Full Document",
                key=(
                    f"full_"
                    f"{selected.get('id')}"
                ),
                use_container_width=True,
            ):

                st.session_state.mode = (
                    "Runbook Mode"
                )

                st.session_state.selected_id = (
                    selected.get("id")
                )

                st.rerun()


# =========================================================
# RUNBOOK MODE
# =========================================================

else:

    st.markdown(
        '<div class="page-title">'
        "Active Runbooks"
        "</div>",
        unsafe_allow_html=True,
    )

    st.markdown(
        '<div class="page-subtitle">'
        "Verified procedures with direct command "
        "execution blocks."
        "</div>",
        unsafe_allow_html=True,
    )

    st.markdown(
        '<div class="mode-card">',
        unsafe_allow_html=True,
    )

    command_query = st.text_input(
        "Command Search",
        placeholder=(
            "⌕  Filter commands by service, "
            "action, or environment..."
        ),
        label_visibility="collapsed",
    )

    st.markdown(
        "</div>",
        unsafe_allow_html=True,
    )

    mode_col1, mode_col2, mode_col3 = st.columns(
        [1, 1, 4]
    )

    with mode_col1:

        if st.button(
            "Standard",
            use_container_width=True,
        ):

            st.session_state.impact_filter = (
                "standard"
            )

            st.rerun()

    with mode_col2:

        if st.button(
            "Critical Only",
            use_container_width=True,
        ):

            st.session_state.impact_filter = (
                "critical"
            )

            st.rerun()

    query = command_query.lower().strip()

    runbook_results = []

    for r in runbooks:

        if (
            str(
                r.get(
                    "type",
                    "runbook"
                )
            ).lower()
            != "runbook"
        ):
            continue

        search_text = " ".join(
            [
                str(r.get("id", "")),
                str(r.get("title", "")),
                str(r.get("cause", "")),
                str(r.get("solution", "")),
                str(r.get("category", "")),
                " ".join(
                    str(x)
                    for x in r.get(
                        "tags",
                        []
                    )
                ),
            ]
        ).lower()

        matches_query = (
            not query
            or query in search_text
        )

        matches_impact = (
            st.session_state.impact_filter
            == "standard"
            or str(
                r.get(
                    "impact",
                    "medium"
                )
            ).lower()
            == "high"
        )

        if matches_query and matches_impact:
            runbook_results.append(r)

    if not runbook_results:

        st.info(
            "No active runbooks match "
            "the current filter."
        )

    else:

        for idx, r in enumerate(
            runbook_results,
            start=1,
        ):

            impact = str(
                r.get(
                    "impact",
                    "medium"
                )
            ).lower()

            circle_class = (
                "number-circle-high"
                if impact == "high"
                else ""
            )

            impact_class = (
                ""
                if impact == "high"
                else "impact-low"
            )

            verification_html = "".join(
                f"""
                <div class="verification-item">
                    {html.escape(str(step))}
                </div>
                """
                for step in r.get(
                    "verification",
                    []
                )
            )

            st.markdown(
                f"""
                <div class="runbook-large">

                    <div class="large-header">

                        <div>

                            <span class="number-circle {circle_class}">
                                {idx:02d}
                            </span>

                            <span class="large-title">
                                {html.escape(
                                    str(
                                        r.get(
                                            "title",
                                            ""
                                        )
                                    )
                                )}
                            </span>

                        </div>

                        <div>

                            <span class="impact {impact_class}">
                                impact:
                                {html.escape(impact)}
                            </span>

                        </div>

                    </div>

                    <div class="large-body">

                        <div class="large-main">

                            <div class="large-description">
                                {html.escape(
                                    str(
                                        r.get(
                                            "cause",
                                            ""
                                        )
                                    )
                                )}
                            </div>

                            <div class="mono-label">
                                Remediation Commands
                            </div>

                            <div class="command-box">
{html.escape(
    str(
        r.get(
            "solution",
            ""
        )
    )
)}
                            </div>

                        </div>

                        <div class="large-verification">

                            <div class="mono-label">
                                Verification Steps
                            </div>

                            <div style="margin-top: 8px;">
                                {verification_html}
                            </div>

                        </div>

                    </div>

                </div>
                """,
                unsafe_allow_html=True,
            )

            action_col1, action_col2, action_col3 = (
                st.columns([4, 1, 1])
            )

            with action_col3:

                if st.button(
                    "Delete",
                    key=(
                        f"delete_"
                        f"{r.get('id')}_"
                        f"{idx}"
                    ),
                ):

                    runbooks = [
                        item
                        for item in runbooks
                        if item.get("id")
                        != r.get("id")
                    ]

                    save_data(runbooks)

                    if (
                        st.session_state.selected_id
                        == r.get("id")
                    ):
                        st.session_state.selected_id = (
                            runbooks[0]["id"]
                            if runbooks
                            else None
                        )

                    st.rerun()


# =========================================================
# FOOTER
# =========================================================

st.markdown(
    """
    <div style="
        text-align:center;
        margin-top:35px;
        color:#78909a;
        font-family:monospace;
        font-size:8px;
        letter-spacing:1px;
    ">
        WAR ROOM BINDER · DEVOPS DOCUMENTATION ARCHIVE
    </div>
    """,
    unsafe_allow_html=True,
)