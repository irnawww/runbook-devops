import json
import os
import streamlit as st
from xhtml2pdf import pisa

# Page Configuration - Clean Dev Portal Theme
st.set_page_config(
    page_title="DevOps Knowledge Base",
    layout="wide",
    initial_sidebar_state="expanded",
)

DB_FILE = "runbooks_db.json"

DEFAULT_DATA = [
    {
        "id": "err-crashloop",
        "title": "CrashLoopBackOff",
        "category": "Kubernetes",
        "cause": "Missing environment variables, database connection refused, or OOMKilled.",
        "solution": (
            "kubectl logs -n production -l app=my-app --tail=100"
            " --previous\nkubectl describe pod -n production -l app=my-app"
        ),
    },
    {
        "id": "err-502",
        "title": "502 Bad Gateway",
        "category": "Ingress",
        "cause": (
            "Backend pod unreachable, service target port mismatch, or failed"
            " readiness probe."
        ),
        "solution": (
            "kubectl get pods -n production -l app=my-app\nkubectl get"
            " endpoints my-app-service -n production"
        ),
    },
    {
        "id": "err-db-conn",
        "title": "Database Connection Exhausted",
        "category": "Database",
        "cause": (
            "Application connection leak or sudden traffic spike without pooler"
            " (PgBouncer)."
        ),
        "solution": (
            "SELECT count(*), state FROM pg_stat_activity GROUP BY"
            " state;\nSELECT pg_terminate_backend(pid) FROM pg_stat_activity"
            " WHERE state = 'idle';"
        ),
    },
]


def load_data():
  if not os.path.exists(DB_FILE):
    with open(DB_FILE, "w", encoding="utf-8") as f:
      json.dump(DEFAULT_DATA, f, indent=2)
    return DEFAULT_DATA
  with open(DB_FILE, "r", encoding="utf-8") as f:
    return json.load(f)


def save_data(data):
  with open(DB_FILE, "w", encoding="utf-8") as f:
    json.dump(data, f, indent=2)


def generate_pdf(runbooks, app_name="DevOps Operations Manual"):
  cards_html = ""
  for r in runbooks:
    cards_html += f"""
        <div style="background-color: #ffffff; border: 1px solid #e2e8f0; border-radius: 4px; padding: 12px; margin-bottom: 12px;">
            <div style="font-size: 11pt; font-weight: bold; color: #0f172a; margin-bottom: 4px;">
                [{r['category']}] {r['id']} - {r['title']}
            </div>
            <div style="margin-bottom: 6px; color: #334155;"><strong>Root Cause:</strong> {r['cause']}</div>
            <div style="background-color: #0f172a; color: #f8fafc; font-family: monospace; padding: 10px; border-radius: 4px; font-size: 8.5pt; white-space: pre-wrap;">{r['solution']}</div>
        </div>
        """

  html_content = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="UTF-8">
        <style>
            @page {{ size: A4; margin: 12mm; }}
            body {{ font-family: Helvetica, Arial, sans-serif; font-size: 9pt; color: #1e293b; background-color: #f8fafc; }}
            h1 {{ color: #0f172a; border-bottom: 2px solid #cbd5e1; padding-bottom: 6px; font-size: 16pt; }}
            .meta {{ color: #64748b; font-size: 8pt; margin-bottom: 16px; }}
        </style>
    </head>
    <body>
        <h1>{app_name}</h1>
        <div class="meta">Internal Infrastructure & Incident Resolution Guides</div>
        {cards_html}
    </body>
    </html>
    """

  pdf_filename = "devops_runbook_export.pdf"
  with open(pdf_filename, "wb") as pdf_file:
    pisa.CreatePDF(html_content, dest=pdf_file)
  return pdf_filename


# Load Data
runbooks = load_data()

# Header Section
st.title("DevOps Knowledge Base")
st.caption("Internal repository for infrastructure runbooks and incident resolution protocols.")
st.markdown("---")

# Sidebar - Operations & Forms
st.sidebar.subheader("Navigation & Tools")

# Filter / Search
search_query = st.sidebar.text_input("Search (ID, Tag, Keyword):", placeholder="e.g. crashloop, ingress, db")

# Category Setup
existing_categories = sorted(list(set([r["category"] for r in runbooks if "category" in r])))
default_categories = ["Kubernetes", "Database", "Ingress", "CI/CD", "Monitoring", "Cloud"]
all_categories = sorted(list(set(existing_categories + default_categories)))
category_options = all_categories + ["+ Add Custom Category..."]

st.sidebar.markdown("---")
st.sidebar.subheader("Entry Management")

# Form Add Runbook
with st.sidebar.form("add_runbook_form", clear_on_submit=True):
    new_id = st.text_input("ID Tag", placeholder="err-pod-oom")
    new_title = st.text_input("Incident Title", placeholder="Pod OOMKilled Exception")
    
    selected_cat = st.selectbox("Category", category_options)
    custom_cat = st.text_input("Custom Category Name", placeholder="Specify if custom option selected")
    
    new_cause = st.text_area("Root Cause / Description")
    new_sol = st.text_area("Remediation Commands / Solution")
    
    submit_btn = st.form_submit_button("Save Entry")

    if submit_btn:
        final_category = custom_cat.strip() if selected_cat == "+ Add Custom Category..." else selected_cat

        if new_id and new_title and final_category:
            new_entry = {
                "id": new_id,
                "title": new_title,
                "category": final_category,
                "cause": new_cause,
                "solution": new_sol,
            }
            runbooks.append(new_entry)
            save_data(runbooks)
            st.sidebar.success("Entry successfully saved.")
            st.rerun()
        else:
            st.sidebar.error("ID, Title, and Category fields are required.")

# Sidebar Export
st.sidebar.markdown("---")
if st.sidebar.button("Generate PDF Report"):
    pdf_file = generate_pdf(runbooks)
    with open(pdf_file, "rb") as f:
        st.sidebar.download_button(
            "Download Export (.pdf)", f, file_name="devops_runbooks.pdf", mime="application/pdf"
        )

# Main Workspace Content
filtered_runbooks = [
    r for r in runbooks
    if search_query.lower() in r["id"].lower()
    or search_query.lower() in r["title"].lower()
    or search_query.lower() in r["cause"].lower()
    or search_query.lower() in r["category"].lower()
]

# Quick Metrics Bar
col_m1, col_m2, col_m3 = st.columns(3)
col_m1.metric("Total Active Runbooks", len(runbooks))
col_m2.metric("Filtered Results", len(filtered_runbooks))
col_m3.metric("Total Categories", len(existing_categories))

st.markdown("---")

if not filtered_runbooks:
    st.info("No runbook entries match the current filter criteria.")

# List Runbooks
for idx, r in enumerate(filtered_runbooks):
    expander_title = f"[{r['category'].upper()}]  {r['id']} — {r['title']}"
    
    with st.expander(expander_title, expanded=True):
        st.markdown(f"**Root Cause Analysis:** {r['cause']}")
        st.markdown("**Remediation Steps:**")
        st.code(r["solution"], language="bash")

        col_action, col_del = st.columns([0.88, 0.12])
        with col_del:
            if st.button("Delete", key=f"del_{r['id']}_{idx}"):
                runbooks = [item for item in runbooks if item["id"] != r["id"]]
                save_data(runbooks)
                st.rerun()