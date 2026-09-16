import streamlit as st
import json
import html
import io
from pathlib import Path

# =========================================================
# OPTIONAL PDF DEPENDENCY
# =========================================================

try:
    from xhtml2pdf import pisa
    PDF_AVAILABLE = True
except ImportError:
    PDF_AVAILABLE = False


# =========================================================
# PAGE CONFIG
# =========================================================

st.set_page_config(
    page_title="War Room Binder",
    page_icon="🛠️",
    layout="wide",
    initial_sidebar_state="expanded",
)


# =========================================================
# CSS
# =========================================================

st.markdown(
    """
    <style>
    .stApp {
        background: #f7f8fa;
    }

    [data-testid="stAppViewContainer"] .main .block-container {
        max-width: 1450px;
        padding-top: 2rem;
        padding-bottom: 4rem;
    }

    [data-testid="stSidebar"] {
        background: #ffffff;
        border-right: 1px solid #e5e7eb;
    }

    h1, h2, h3 {
        letter-spacing: -0.02em;
    }

    .hero-title {
        font-size: 2rem;
        font-weight: 750;
        color: #111827;
        margin-bottom: 0.15rem;
    }

    .hero-subtitle {
        color: #6b7280;
        font-size: 0.95rem;
        margin-bottom: 1.5rem;
    }

    .badge {
        display: inline-block;
        padding: 4px 9px;
        border-radius: 999px;
        font-size: 0.72rem;
        font-weight: 700;
        margin-right: 5px;
        margin-bottom: 5px;
        border: 1px solid #e5e7eb;
        background: #f9fafb;
        color: #374151;
    }

    .badge-active {
        background: #ecfdf3;
        color: #067647;
        border-color: #abefc6;
    }

    .badge-high {
        background: #fff1f3;
        color: #c01048;
        border-color: #fda4af;
    }

    .badge-runbook {
        background: #eff6ff;
        color: #175cd3;
        border-color: #bfdbfe;
    }

    .badge-incident {
        background: #fff7ed;
        color: #c2410c;
        border-color: #fed7aa;
    }

    .tag {
        display: inline-block;
        padding: 3px 8px;
        border-radius: 6px;
        font-size: 0.72rem;
        background: #f3f4f6;
        color: #4b5563;
        margin-right: 4px;
        margin-bottom: 4px;
    }

    .muted {
        color: #6b7280;
        font-size: 0.86rem;
    }

    .doc-title {
        font-size: 1.08rem;
        font-weight: 700;
        color: #111827;
        margin: 4px 0 7px 0;
    }

    .doc-description {
        color: #4b5563;
        font-size: 0.88rem;
        line-height: 1.55;
    }

    .section-label {
        color: #6b7280;
        font-size: 0.75rem;
        font-weight: 700;
        text-transform: uppercase;
        letter-spacing: 0.08em;
        margin-bottom: 5px;
    }

    .reading-title {
        font-size: 1.5rem;
        font-weight: 750;
        color: #111827;
        margin: 4px 0 8px 0;
    }

    .reading-description {
        color: #4b5563;
        line-height: 1.6;
        margin-bottom: 1rem;
    }

    .meta-box {
        padding: 12px 14px;
        border-radius: 10px;
        background: #f9fafb;
        border: 1px solid #e5e7eb;
    }

    .meta-label {
        color: #6b7280;
        font-size: 0.72rem;
        text-transform: uppercase;
        font-weight: 700;
        letter-spacing: 0.05em;
    }

    .meta-value {
        color: #111827;
        font-size: 0.9rem;
        font-weight: 600;
        margin-top: 2px;
    }

    div[data-testid="stVerticalBlockBorderWrapper"] {
        border-radius: 14px;
        border-color: #e5e7eb;
        background: #ffffff;
    }

    div[data-testid="stButton"] > button {
        border-radius: 9px;
        font-weight: 600;
    }

    .empty-state {
        text-align: center;
        padding: 60px 20px;
        color: #6b7280;
    }
    </style>
    """,
    unsafe_allow_html=True,
)


# =========================================================
# DATA
# =========================================================

DATA_FILE = Path("war_room_binder.json")

DEFAULT_DATA = [
    {
        "id": "err-crashloop",
        "title": "CrashLoopBackOff",
        "category": "Kubernetes",
        "type": "runbook",
        "status": "active",
        "priority": "high",
        "author": "DevOps",
        "tags": ["kubernetes", "pod"],
        "description": "Pod repeatedly crashes after deployment.",
        "cause": "Missing environment variables, database connection refused, or OOMKilled.",
        "solution": """kubectl get pods -A
kubectl describe pod <pod-name> -n <namespace>
kubectl logs <pod-name> -n <namespace> --previous""",
        "verification": [
            "Pod status changes from CrashLoopBackOff to Running.",
            "Application logs show successful startup.",
            "Readiness and liveness probes become healthy.",
        ],
    },
    {
        "id": "err-502",
        "title": "502 Bad Gateway",
        "category": "Ingress",
        "type": "incident",
        "status": "active",
        "priority": "high",
        "author": "DevOps",
        "tags": ["ingress", "gateway"],
        "description": "Gateway returns HTTP 502 when accessing the application.",
        "cause": "Backend unreachable, incorrect service port, or failed readiness probe.",
        "solution": """kubectl get pods -n <namespace>
kubectl get svc -n <namespace>
kubectl get endpoints -n <namespace>
kubectl describe ingress <ingress-name> -n <namespace>""",
        "verification": [
            "Backend pods are Running and Ready.",
            "Service endpoints contain healthy pod IPs.",
            "Application responds successfully through the ingress.",
        ],
    },
    {
        "id": "err-db-conn",
        "title": "Database Connection Exhausted",
        "category": "Database",
        "type": "runbook",
        "status": "active",
        "priority": "high",
        "author": "DevOps",
        "tags": ["database", "postgresql"],
        "description": "Application cannot establish new database connections.",
        "cause": "Connection leak, traffic spike, or insufficient connection pooling.",
        "solution": """SELECT count(*) FROM pg_stat_activity;

SELECT state, count(*)
FROM pg_stat_activity
GROUP BY state;

SHOW max_connections;""",
        "verification": [
            "Active connections return to a normal range.",
            "Application can establish new database connections.",
            "Connection pool remains stable during normal traffic.",
        ],
    },
]


# =========================================================
# HELPERS
# =========================================================

def load_data():
    if not DATA_FILE.exists():
        return DEFAULT_DATA.copy()

    try:
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)

        if not isinstance(data, list):
            return DEFAULT_DATA.copy()

        return data

    except Exception:
        return DEFAULT_DATA.copy()


def save_data(data):
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


def badge_class(value):
    value = str(value).lower()

    if value == "active":
        return "badge-active"

    if value == "high":
        return "badge-high"

    if value == "runbook":
        return "badge-runbook"

    if value == "incident":
        return "badge-incident"

    return "badge"


def safe(value):
    return html.escape(str(value))


def export_pdf(document):
    if not PDF_AVAILABLE:
        return None

    document_title = safe(document.get("title", "Document"))
    description = safe(document.get("description", ""))
    cause = safe(document.get("cause", ""))
    solution = safe(document.get("solution", ""))

    verification = document.get("verification", [])

    verification_html = "".join(
        f"<li>{safe(item)}</li>" for item in verification
    )

    pdf_html = f"""
    <html>
    <head>
        <meta charset="UTF-8">
        <style>
            body {{
                font-family: Helvetica, Arial, sans-serif;
                font-size: 10pt;
                color: #222;
            }}

            h1 {{
                font-size: 20pt;
                margin-bottom: 8px;
            }}

            h2 {{
                font-size: 13pt;
                margin-top: 20px;
            }}

            p {{
                line-height: 1.5;
            }}

            pre {{
                background: #f2f2f2;
                border: 1px solid #ddd;
                padding: 12px;
                font-size: 8.5pt;
                white-space: pre-wrap;
            }}

            li {{
                margin-bottom: 6px;
            }}
        </style>
    </head>

    <body>
        <h1>{document_title}</h1>

        <p>{description}</p>

        <h2>Cause</h2>
        <p>{cause}</p>

        <h2>Solution</h2>
        <pre>{solution}</pre>

        <h2>Verification</h2>
        <ul>
            {verification_html}
        </ul>
    </body>
    </html>
    """

    output = io.BytesIO()

    result = pisa.CreatePDF(
        src=pdf_html,
        dest=output,
    )

    if result.err:
        return None

    return output.getvalue()


# =========================================================
# SESSION STATE
# =========================================================

if "documents" not in st.session_state:
    st.session_state.documents = load_data()

if "selected_id" not in st.session_state:
    st.session_state.selected_id = None

if "mode" not in st.session_state:
    st.session_state.mode = "Knowledge Base"


# =========================================================
# SIDEBAR
# =========================================================

with st.sidebar:

    st.markdown("## 🛠️ War Room Binder")
    st.caption("Arsip dokumentasi tim DevOps")

    st.divider()

    mode = st.radio(
        "Workspace",
        ["Knowledge Base", "Runbook Mode"],
        index=(
            0
            if st.session_state.mode == "Knowledge Base"
            else 1
        ),
    )

    st.session_state.mode = mode

    st.divider()

    st.markdown("### Add Documentation")

    with st.form("add_document_form", clear_on_submit=True):

        new_title = st.text_input(
            "Title",
            placeholder="e.g. Redis Connection Error",
        )

        new_category = st.text_input(
            "Category",
            placeholder="Database",
        )

        new_type = st.selectbox(
            "Type",
            ["runbook", "incident"],
        )

        new_priority = st.selectbox(
            "Priority",
            ["high", "medium", "low"],
        )

        new_description = st.text_area(
            "Description",
            placeholder="Short explanation...",
        )

        new_cause = st.text_area(
            "Cause",
            placeholder="Possible root causes...",
        )

        new_solution = st.text_area(
            "Solution / Commands",
            placeholder="kubectl ...",
            height=140,
        )

        new_verification = st.text_area(
            "Verification",
            placeholder="One verification step per line",
        )

        submitted = st.form_submit_button(
            "Add Document",
            use_container_width=True,
        )

        if submitted:

            if not new_title.strip():
                st.error("Title wajib diisi.")

            else:
                new_doc = {
                    "id": (
                        new_title.lower()
                        .strip()
                        .replace(" ", "-")
                        .replace("/", "-")
                    ),
                    "title": new_title.strip(),
                    "category": new_category.strip() or "General",
                    "type": new_type,
                    "status": "active",
                    "priority": new_priority,
                    "author": "DevOps",
                    "tags": [],
                    "description": new_description.strip(),
                    "cause": new_cause.strip(),
                    "solution": new_solution.strip(),
                    "verification": [
                        item.strip()
                        for item in new_verification.splitlines()
                        if item.strip()
                    ],
                }

                st.session_state.documents.append(new_doc)
                save_data(st.session_state.documents)

                st.success("Dokumentasi berhasil ditambahkan.")
                st.rerun()

    st.divider()

    st.caption(
        f"{len(st.session_state.documents)} dokumentasi tersimpan"
    )


# =========================================================
# HEADER
# =========================================================

st.markdown(
    '<div class="hero-title">War Room Binder</div>',
    unsafe_allow_html=True,
)

st.markdown(
    '<div class="hero-subtitle">Arsip dokumentasi dan operational knowledge tim DevOps</div>',
    unsafe_allow_html=True,
)


# =========================================================
# KNOWLEDGE BASE
# =========================================================

if st.session_state.mode == "Knowledge Base":

    top_left, top_right = st.columns([3, 1])

    with top_left:
        search = st.text_input(
            "Search documentation",
            placeholder="Search title, category, description, tag...",
            label_visibility="collapsed",
        )

    with top_right:
        filter_type = st.selectbox(
            "Filter",
            ["All", "Runbook", "Incident"],
            label_visibility="collapsed",
        )

    documents = st.session_state.documents

    filtered = []

    for document in documents:

        query = search.lower().strip()

        searchable = " ".join(
            [
                str(document.get("title", "")),
                str(document.get("category", "")),
                str(document.get("description", "")),
                str(document.get("cause", "")),
                " ".join(document.get("tags", [])),
            ]
        ).lower()

        matches_search = not query or query in searchable

        matches_type = (
            filter_type == "All"
            or document.get("type", "").lower()
            == filter_type.lower()
        )

        if matches_search and matches_type:
            filtered.append(document)

    st.markdown(
        f'<div class="muted">{len(filtered)} documentation ditemukan</div>',
        unsafe_allow_html=True,
    )

    st.write("")

    if not filtered:

        st.markdown(
            """
            <div class="empty-state">
                <h3>Documentation tidak ditemukan</h3>
                <p>Coba ubah keyword atau filter.</p>
            </div>
            """,
            unsafe_allow_html=True,
        )

    else:

        for index, document in enumerate(filtered):

            with st.container(border=True):

                col_content, col_action = st.columns(
                    [5, 1],
                    vertical_alignment="center",
                )

                with col_content:

                    type_value = document.get("type", "runbook")
                    status_value = document.get("status", "active")
                    priority_value = document.get("priority", "medium")

                    st.markdown(
                        f"""
                        <span class="badge {badge_class(type_value)}">
                            {safe(type_value.upper())}
                        </span>
                        <span class="badge {badge_class(status_value)}">
                            {safe(status_value.upper())}
                        </span>
                        <span class="badge {badge_class(priority_value)}">
                            {safe(priority_value.upper())}
                        </span>
                        """,
                        unsafe_allow_html=True,
                    )

                    st.markdown(
                        f'<div class="doc-title">{safe(document.get("title", ""))}</div>',
                        unsafe_allow_html=True,
                    )

                    st.markdown(
                        f'<div class="doc-description">{safe(document.get("description", ""))}</div>',
                        unsafe_allow_html=True,
                    )

                    st.write("")

                    tags = document.get("tags", [])

                    if tags:

                        tags_html = "".join(
                            f'<span class="tag">#{safe(tag)}</span>'
                            for tag in tags
                        )

                        st.markdown(
                            tags_html,
                            unsafe_allow_html=True,
                        )

                    st.caption(
                        f'{document.get("author", "DevOps")}  ·  {document.get("id", "")}'
                    )

                with col_action:

                    if st.button(
                        "Open",
                        key=f"open_{document.get('id')}_{index}",
                        use_container_width=True,
                    ):
                        st.session_state.selected_id = document.get("id")
                        st.rerun()


    # =====================================================
    # READING PANE
    # =====================================================

    selected = None

    if st.session_state.selected_id:

        for document in st.session_state.documents:

            if document.get("id") == st.session_state.selected_id:
                selected = document
                break

    if selected:

        st.divider()

        with st.container(border=True):

            head_left, head_right = st.columns(
                [5, 1],
                vertical_alignment="center",
            )

            with head_left:

                st.markdown(
                    f'<div class="section-label">{safe(selected.get("category", "General"))}</div>',
                    unsafe_allow_html=True,
                )

                st.markdown(
                    f'<div class="reading-title">{safe(selected.get("title", ""))}</div>',
                    unsafe_allow_html=True,
                )

                st.markdown(
                    f'<div class="reading-description">{safe(selected.get("description", ""))}</div>',
                    unsafe_allow_html=True,
                )

            with head_right:

                pdf_data = export_pdf(selected)

                if pdf_data:

                    st.download_button(
                        "Export PDF",
                        data=pdf_data,
                        file_name=(
                            selected.get("id", "document")
                            + ".pdf"
                        ),
                        mime="application/pdf",
                        use_container_width=True,
                    )

                else:

                    st.caption(
                        "PDF export unavailable"
                    )

            st.divider()

            meta1, meta2, meta3, meta4 = st.columns(4)

            with meta1:
                st.markdown(
                    f"""
                    <div class="meta-box">
                        <div class="meta-label">Type</div>
                        <div class="meta-value">
                            {safe(selected.get("type", ""))}
                        </div>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )

            with meta2:
                st.markdown(
                    f"""
                    <div class="meta-box">
                        <div class="meta-label">Priority</div>
                        <div class="meta-value">
                            {safe(selected.get("priority", ""))}
                        </div>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )

            with meta3:
                st.markdown(
                    f"""
                    <div class="meta-box">
                        <div class="meta-label">Status</div>
                        <div class="meta-value">
                            {safe(selected.get("status", ""))}
                        </div>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )

            with meta4:
                st.markdown(
                    f"""
                    <div class="meta-box">
                        <div class="meta-label">Owner</div>
                        <div class="meta-value">
                            {safe(selected.get("author", ""))}
                        </div>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )

            st.write("")

            st.markdown("### Cause")

            st.write(
                selected.get(
                    "cause",
                    "No cause documented.",
                )
            )

            st.markdown("### Solution")

            solution = selected.get("solution", "")

            st.code(
                solution,
                language="bash",
            )

            st.markdown("### Verification")

            verification = selected.get(
                "verification",
                [],
            )

            for step in verification:
                st.checkbox(
                    step,
                    key=f"verify_{selected.get('id')}_{hash(step)}",
                )

            st.write("")

            close_col, delete_col = st.columns(2)

            with close_col:

                if st.button(
                    "Close Document",
                    key=f"close_{selected.get('id')}",
                    use_container_width=True,
                ):
                    st.session_state.selected_id = None
                    st.rerun()

            with delete_col:

                if st.button(
                    "Delete Document",
                    key=f"delete_{selected.get('id')}",
                    use_container_width=True,
                ):

                    st.session_state.documents = [
                        doc
                        for doc in st.session_state.documents
                        if doc.get("id")
                        != selected.get("id")
                    ]

                    save_data(
                        st.session_state.documents
                    )

                    st.session_state.selected_id = None
                    st.rerun()


# =========================================================
# RUNBOOK MODE
# =========================================================

else:

    st.markdown("## ⚡ Runbook Mode")

    st.caption(
        "Operational commands dan verification checklist untuk troubleshooting."
    )

    search_runbook = st.text_input(
        "Search runbook",
        placeholder="Search runbook...",
        label_visibility="collapsed",
    )

    runbook_priority = st.radio(
        "Priority",
        ["All", "High", "Medium", "Low"],
        horizontal=True,
    )

    runbooks = [
        document
        for document in st.session_state.documents
        if document.get("type") == "runbook"
    ]

    if search_runbook:

        query = search_runbook.lower()

        runbooks = [
            document
            for document in runbooks
            if query in (
                document.get("title", "")
                + " "
                + document.get("description", "")
                + " "
                + document.get("category", "")
            ).lower()
        ]

    if runbook_priority != "All":

        runbooks = [
            document
            for document in runbooks
            if document.get("priority", "").lower()
            == runbook_priority.lower()
        ]

    st.write("")

    if not runbooks:

        st.info("Belum ada runbook yang sesuai.")

    else:

        for index, runbook in enumerate(runbooks):

            with st.container(border=True):

                left, right = st.columns(
                    [5, 1],
                    vertical_alignment="center",
                )

                with left:

                    st.markdown(
                        f"""
                        <span class="badge badge-runbook">
                            RUNBOOK
                        </span>

                        <span class="badge {badge_class(runbook.get("priority", "medium"))}">
                            {safe(runbook.get("priority", "medium").upper())}
                        </span>

                        <div class="doc-title">
                            {safe(runbook.get("title", ""))}
                        </div>

                        <div class="doc-description">
                            {safe(runbook.get("description", ""))}
                        </div>
                        """,
                        unsafe_allow_html=True,
                    )

                with right:

                    if st.button(
                        "Delete",
                        key=f"runbook_delete_{runbook.get('id')}_{index}",
                        use_container_width=True,
                    ):

                        st.session_state.documents = [
                            doc
                            for doc in st.session_state.documents
                            if doc.get("id")
                            != runbook.get("id")
                        ]

                        save_data(
                            st.session_state.documents
                        )

                        st.rerun()

                st.divider()

                st.markdown("**Cause**")

                st.write(
                    runbook.get(
                        "cause",
                        "No cause documented.",
                    )
                )

                st.markdown("**Commands / Solution**")

                language = "sql" if (
                    "SELECT" in runbook.get(
                        "solution",
                        "",
                    ).upper()
                ) else "bash"

                st.code(
                    runbook.get(
                        "solution",
                        "",
                    ),
                    language=language,
                )

                st.markdown("**Verification**")

                verification = runbook.get(
                    "verification",
                    [],
                )

                for step_index, step in enumerate(
                    verification
                ):

                    st.checkbox(
                        step,
                        key=(
                            f"runbook_verify_"
                            f"{runbook.get('id')}_"
                            f"{step_index}"
                        ),
                    )