
import streamlit as st


CSS = """
<style>
:root{
  --bg:#f7f8fb; --card:#ffffff; --border:rgba(15,23,42,.08);
  --text:#0f172a; --muted:#64748b; --accent:#5b5bf7;
}
.stApp{
  background:
    radial-gradient(circle at 84% -10%, rgba(91,91,247,.10), transparent 28%),
    linear-gradient(180deg,#f8fafc 0%,#fff 42%);
}
.block-container{max-width:1480px;padding-top:1.2rem;padding-bottom:2.4rem}
section[data-testid="stSidebar"]{
  background:linear-gradient(180deg,#fff,#f8fafc);
  border-right:1px solid rgba(15,23,42,.07);
}
.app-brand{display:flex;align-items:center;gap:10px;margin-bottom:15px}
.brand-icon{
  width:40px;height:40px;border-radius:12px;background:linear-gradient(135deg,#111827,#5b5bf7);
  display:flex;align-items:center;justify-content:center;color:#fff;font-weight:900;
  box-shadow:0 9px 24px rgba(91,91,247,.20)
}
.brand-title{font-weight:800;color:#0f172a;line-height:1.05}
.brand-sub{color:#64748b;font-size:.72rem;margin-top:3px}
.page-title{font-weight:850;font-size:2.05rem;color:#0f172a;letter-spacing:-.035em;line-height:1.05}
.page-sub{color:#64748b;margin-top:.35rem;margin-bottom:1.2rem}
.kpi{
  background:rgba(255,255,255,.96);border:1px solid var(--border);border-radius:18px;
  padding:17px;min-height:116px;box-shadow:0 8px 28px rgba(15,23,42,.055);
  transition:.18s ease
}
.kpi:hover{transform:translateY(-2px);box-shadow:0 14px 34px rgba(15,23,42,.08)}
.kpi-label{font-size:.74rem;font-weight:700;color:#64748b;text-transform:uppercase;letter-spacing:.055em}
.kpi-value{font-size:1.58rem;font-weight:850;color:#0f172a;margin-top:9px;letter-spacing:-.025em}
.kpi-note{font-size:.74rem;color:#94a3b8;margin-top:8px}
.pos{color:#059669}.neg{color:#dc2626}
.login-wrap{text-align:center;margin:7vh auto 1.4rem auto;max-width:520px}
.login-brand{
  width:58px;height:58px;border-radius:18px;background:linear-gradient(135deg,#111827,#5b5bf7);
  color:white;display:flex;align-items:center;justify-content:center;font-weight:900;font-size:1.4rem;
  margin:0 auto 14px auto;box-shadow:0 14px 36px rgba(91,91,247,.20)
}
.login-wrap h1{margin:0;color:#0f172a;letter-spacing:-.03em}
.login-wrap p{color:#64748b}
div[data-testid="stDataFrame"],div[data-testid="stForm"],div[data-testid="stExpander"]{
  border:1px solid rgba(15,23,42,.08);border-radius:16px;overflow:hidden;
  box-shadow:0 7px 24px rgba(15,23,42,.04)
}
.stButton>button,.stDownloadButton>button{border-radius:12px;min-height:42px;font-weight:700}
</style>
"""


def apply_style():
    st.markdown(CSS, unsafe_allow_html=True)


def brand():
    st.sidebar.markdown(
        """
        <div class="app-brand">
          <div class="brand-icon">P</div>
          <div>
            <div class="brand-title">Painel Patrimonial</div>
            <div class="brand-sub">Carteira multiusuário</div>
          </div>
        </div>
        """,
        unsafe_allow_html=True
    )


def page_header(title, subtitle=""):
    st.markdown(f'<div class="page-title">{title}</div>', unsafe_allow_html=True)
    if subtitle:
        st.markdown(f'<div class="page-sub">{subtitle}</div>', unsafe_allow_html=True)


def money(v):
    try:
        v=float(v)
    except Exception:
        v=0
    return f"R$ {v:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")


def pct(v):
    try:
        v=float(v)
    except Exception:
        v=0
    return f"{v:,.2f}%".replace(",", "X").replace(".", ",").replace("X", ".")


def kpi(label, value, note="", tone=""):
    cls = " pos" if tone=="pos" else " neg" if tone=="neg" else ""
    st.markdown(
        f"""
        <div class="kpi">
          <div class="kpi-label">{label}</div>
          <div class="kpi-value{cls}">{value}</div>
          <div class="kpi-note">{note}</div>
        </div>
        """,
        unsafe_allow_html=True
    )
