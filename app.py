from datetime import date, datetime
import pandas as pd
import plotly.express as px
import streamlit as st
from streamlit_autorefresh import st_autorefresh

from auth import init_auth, require_login, sign_out, current_user_id
from db import (
    latest_meta, latest_positions, operations_df, income_df, fixed_income_df,
    goals_df, replace_position_snapshot, upsert_operations, upsert_income,
    upsert_fixed_income_movements, add_operation, add_income, add_goal
)
from imports import parse_position_file, parse_b3_movements, summarize_fixed_income
from market import get_quotes
from portfolio import calculate_positions, enrich_with_quotes
from ui import apply_style, brand, page_header, kpi, money, pct
TECHNICAL_COLUMNS = {
    "id",
    "user_id",
    "external_key",
    "created_at",
}

def display_df(df):
    if df is None or df.empty:
        return pd.DataFrame()

    cols = [
        col for col in df.columns
        if col not in TECHNICAL_COLUMNS
    ]

    return df.loc[:, cols].copy()

st.set_page_config(
    page_title="Painel Patrimonial",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="expanded"
)

apply_style()
init_auth()

if not require_login():
    st.stop()

brand()

user_email = getattr(st.session_state.auth_user, "email", "Usuário")
st.sidebar.caption(user_email)

menu = st.sidebar.radio(
    "Navegação",
    [
        "Dashboard",
        "Ações",
        "FIIs",
        "Renda Fixa",
        "Operações",
        "Proventos",
        "Metas",
        "Importações",
    ]
)

if st.sidebar.button("Sair", use_container_width=True):
    sign_out()
    st.rerun()

st.sidebar.divider()

if st.sidebar.button(
    "🔄 Atualizar cotações agora",
    use_container_width=True
):
    get_quotes.clear()
    st.session_state["manual_quote_refresh"] = (
        datetime.now().strftime("%d/%m/%Y %H:%M:%S")
    )
    st.rerun()

if st.session_state.get("manual_quote_refresh"):
    st.sidebar.caption(
        "Última atualização manual: "
        + st.session_state["manual_quote_refresh"]
    )
else:
    st.sidebar.caption(
        "Cotações atualizam automaticamente a cada 30 min."
    )

# atualização de tela/cotações enquanto aberto
st_autorefresh(interval=30 * 60 * 1000, key="quote_refresh")

base = latest_positions()
ops = operations_df()
inc = income_df()
rfmov = fixed_income_df()
meta = latest_meta()
goals = goals_df()

pos = calculate_positions(base, ops)
tickers = tuple(pos["ticker"].tolist()) if not pos.empty else tuple()

try:
    quotes = get_quotes(tickers)
    quote_error = None
except Exception as e:
    quotes = {}
    quote_error = str(e)

pv = enrich_with_quotes(pos, quotes)

quote_total = len(tickers)
quote_updated = len(quotes)
if quote_total:
    st.sidebar.caption(f"Cotações recebidas: {quote_updated}/{quote_total}")

rf_summary = summarize_fixed_income(rfmov)
rf_balance = float(rf_summary["estimated_balance"].sum()) if not rf_summary.empty else 0.0
rf_interest = float(rf_summary["interest_received"].sum()) if not rf_summary.empty else 0.0

available_cash = float(meta.get("available_cash") or 0)
rv_market = float(pv["market_value"].sum()) if not pv.empty else 0.0
rv_invested = float(pv["invested_value"].sum()) if not pv.empty else 0.0

provisioned = 0.0
received_year = 0.0
if not inc.empty:
    inc["net_amount"] = pd.to_numeric(inc["net_amount"], errors="coerce").fillna(0)
    provisioned = float(
        inc.loc[inc["status"].astype(str).str.lower()=="provisionado","net_amount"].sum()
    )
    pay = pd.to_datetime(inc["payment_date"], errors="coerce")
    received_year = float(
        inc.loc[
            (inc["status"].astype(str).str.lower()=="recebido") &
            (pay.dt.year == date.today().year),
            "net_amount"
        ].sum()
    )

patrimony = rv_market + rf_balance + available_cash + provisioned
invested = rv_invested + rf_balance
result = patrimony - invested
return_pct = ((rv_market-rv_invested)/rv_invested*100) if rv_invested > 0 else 0


# ============================================================
# DASHBOARD
# ============================================================
if menu == "Dashboard":
    page_header("Dashboard patrimonial", "Visão consolidada da sua carteira.")

    if quote_error:
        st.warning("Algumas cotações não puderam ser atualizadas. O sistema usou preços importados quando disponíveis.")

    c1,c2,c3,c4 = st.columns(4)
    with c1: kpi("Patrimônio total", money(patrimony), "Mercado + renda fixa + disponível")
    with c2: kpi("Valor investido", money(invested), "Custo consolidado")
    with c3: kpi("Ganho / perda", money(result), "Resultado consolidado", "pos" if result>=0 else "neg")
    with c4: kpi("Rentabilidade", pct(return_pct), "Sobre ações e FIIs", "pos" if return_pct>=0 else "neg")

    c1,c2,c3,c4 = st.columns(4)
    with c1: kpi("Ações + FIIs", money(rv_market), "Valor atual de mercado")
    with c2: kpi("Renda fixa", money(rf_balance), "Saldo estimado por movimentações")
    with c3: kpi("Saldo disponível", money(available_cash), "Última posição importada")
    with c4: kpi("Ativos", str(len(pv)), "Ações e FIIs")

    c1,c2,c3 = st.columns(3)
    with c1: kpi("Proventos provisionados", money(provisioned), "Ainda não recebidos")
    with c2: kpi("Proventos recebidos no ano", money(received_year), "Ações e FIIs")
    with c3: kpi("Juros de renda fixa", money(rf_interest), "Histórico B3")

    st.divider()

    col1,col2 = st.columns([1.15,1])
    with col1:
        dist = []
        if not pv.empty:
            for klass,val in pv.groupby("asset_class")["market_value"].sum().items():
                dist.append({"Classe":klass,"Valor":float(val)})
        if rf_balance>0: dist.append({"Classe":"Renda Fixa","Valor":rf_balance})
        if available_cash>0: dist.append({"Classe":"Disponível","Valor":available_cash})

        if dist:
            fig = px.pie(pd.DataFrame(dist), names="Classe", values="Valor", hole=.62)
            fig.update_traces(textinfo="percent+label")
            fig.update_layout(height=360,margin=dict(l=10,r=10,t=10,b=10),showlegend=False)
            st.plotly_chart(fig,use_container_width=True)

    with col2:
        comp = pd.DataFrame({
            "Categoria":["Investido","Valor atual"],
            "Valor":[invested, rv_market+rf_balance]
        })
        fig = px.bar(comp,x="Categoria",y="Valor",text="Valor")
        fig.update_traces(texttemplate="R$ %{text:,.0f}",textposition="outside")
        fig.update_layout(height=360,margin=dict(l=10,r=10,t=10,b=10),xaxis_title=None,yaxis_title=None)
        st.plotly_chart(fig,use_container_width=True)

    if not pv.empty:
        st.subheader("Maiores posições")
        top = pv.sort_values("market_value").tail(12)
        fig = px.bar(top,x="market_value",y="ticker",orientation="h",hover_data=["asset_class","quantity","return_pct"])
        fig.update_layout(height=460,xaxis_title=None,yaxis_title=None)
        st.plotly_chart(fig,use_container_width=True)


# ============================================================
# AÇÕES / FIIs
# ============================================================
elif menu in ("Ações","FIIs"):
    klass = "Ação" if menu=="Ações" else "FII"
    page_header(menu, "Posição atual, operações e proventos por ativo.")
    df = pv[pv["asset_class"]==klass].sort_values("market_value",ascending=False) if not pv.empty else pd.DataFrame()

    if df.empty:
        st.info("Nenhum ativo desta classe na carteira.")
    else:
        for _,r in df.iterrows():
            with st.expander(f"{r['ticker']} — {r.get('name') or r['ticker']}"):
                c1,c2,c3,c4 = st.columns(4)
                c1.metric("Quantidade", f"{r['quantity']:,.2f}")
                c2.metric("Preço médio", "Indefinido" if r.get("avg_price_undefined") else money(r["avg_price"]))
                c3.metric("Cotação", money(r["market_price"]))
                c4.metric("Valor atual", money(r["market_value"]))

                c1,c2,c3 = st.columns(3)
                c1.metric("Investido", money(r["invested_value"]))
                c2.metric("Resultado", money(r["result"]))
                c3.metric("Rentabilidade", pct(r["return_pct"]))

                tabs = st.tabs(["Operações","Proventos","Mercado"])
                with tabs[0]:
                    h = ops[(ops["ticker"]==r["ticker"]) & (ops["asset_class"]==klass)] if not ops.empty else pd.DataFrame()
                    st.dataframe(
                        display_df(h),
                        use_container_width=True,
                        hide_index=True
                    )
                with tabs[1]:
                    h = inc[inc["ticker"]==r["ticker"]] if not inc.empty else pd.DataFrame()
                    st.dataframe(
                        display_df(h),
                        use_container_width=True,
                        hide_index=True
                    )
                with tabs[2]:
                    q = quotes.get(r["ticker"],{})
                    st.metric("Variação do dia", pct(q.get("change_pct",0)))
                    st.caption(f"Última atualização da fonte: {q.get('updated_at','não disponível')}")


# ============================================================
# RENDA FIXA
# ============================================================
elif menu == "Renda Fixa":
    page_header("Renda Fixa", "Saldo estimado, aplicações, resgates, amortizações e juros.")

    c1,c2,c3,c4 = st.columns(4)
    applications = float(rf_summary["applications"].sum()) if not rf_summary.empty else 0
    out = float((rf_summary["purchase_sale_out"]+rf_summary["redemptions_maturities"]+rf_summary["amortizations"]).sum()) if not rf_summary.empty else 0
    with c1:kpi("Saldo estimado",money(rf_balance),"Principal estimado ainda aplicado")
    with c2:kpi("Aplicações históricas",money(applications),"Créditos identificados")
    with c3:kpi("Saídas de principal",money(out),"Resgates, vencimentos e amortizações")
    with c4:kpi("Juros recebidos",money(rf_interest),"Rendimentos identificados")

    st.caption("O saldo é estimado pelas movimentações da B3; não é marcação a mercado nem valor atualizado oficial.")

    if not rf_summary.empty:
        c1,c2 = st.columns([1.2,1])
        with c1:
            chart = rf_summary[rf_summary["estimated_balance"]>0].head(15)
            if not chart.empty:
                fig=px.bar(chart.sort_values("estimated_balance"),x="estimated_balance",y="product",orientation="h",hover_data=["institution","type","interest_received"])
                fig.update_layout(height=max(360,36*len(chart)),xaxis_title=None,yaxis_title=None)
                st.plotly_chart(fig,use_container_width=True)
        with c2:
            typ=rf_summary.groupby("type")["estimated_balance"].sum().reset_index()
            typ=typ[typ["estimated_balance"]>0]
            if not typ.empty:
                fig=px.pie(typ,names="type",values="estimated_balance",hole=.58)
                fig.update_layout(height=360,showlegend=False)
                st.plotly_chart(fig,use_container_width=True)

        st.dataframe(
            rf_summary,
            use_container_width=True,
            hide_index=True
        )
    else:
        st.info("Importe o histórico da B3 para montar a renda fixa.")


# ============================================================
# OPERAÇÕES
# ============================================================
elif menu == "Operações":
    page_header("Operações","Cadastre apenas movimentações que não estejam no arquivo B3.")
    with st.form("operation_form",clear_on_submit=True):
        c1,c2=st.columns(2)
        with c1:
            dt=st.date_input("Data",value=date.today())
            klass=st.selectbox("Classe",["Ação","FII"])
            ticker=st.text_input("Ticker").upper().strip()
            typ=st.selectbox("Tipo",["Compra","Venda","Bonificação","Subscrição","Outro"])
        with c2:
            qty=st.number_input("Quantidade",min_value=0.0,step=1.0)
            price=st.number_input("Preço unitário",min_value=0.0,step=0.01)
            costs=st.number_input("Custos",min_value=0.0,step=0.01)
            institution=st.text_input("Corretora / instituição")
        notes=st.text_area("Observações")
        if st.form_submit_button("Registrar operação",use_container_width=True):
            add_operation({
                "operation_date":dt.isoformat(),"asset_class":klass,"ticker":ticker,
                "name":ticker,"operation_type":typ,"quantity":qty,"unit_price":price,
                "costs":costs,"institution":institution,"notes":notes,"origin":"Manual"
            })
            st.success("Operação registrada.")
            st.rerun()
    st.dataframe(
        display_df(ops),
        use_container_width=True,
        hide_index=True
    )


# ============================================================
# PROVENTOS
# ============================================================
elif menu == "Proventos":
    page_header("Proventos","Dividendos, JCP, rendimentos e valores provisionados.")
    st.dataframe(
        display_df(inc),
        use_container_width=True,
        hide_index=True
    )


# ============================================================
# METAS
# ============================================================
elif menu == "Metas":
    page_header("Metas patrimoniais","Simulações matemáticas, não previsões de mercado.")

    with st.form("goal_form",clear_on_submit=True):
        c1,c2=st.columns(2)
        with c1:
            name=st.text_input("Nome da meta")
            target=st.number_input("Valor objetivo",min_value=0.0,step=1000.0)
            target_date=st.date_input("Data objetivo",value=date.today())
        with c2:
            contribution=st.number_input("Aporte mensal",min_value=0.0,step=100.0)
            assumed=st.number_input("Rentabilidade anual hipotética (%)",min_value=0.0,value=8.0,step=.5)
        if st.form_submit_button("Salvar meta",use_container_width=True):
            add_goal({
                "name":name,"target_value":target,"target_date":target_date.isoformat(),
                "monthly_contribution":contribution,"assumed_annual_return":assumed
            })
            st.success("Meta salva.")
            st.rerun()

    if not goals.empty:
        for _,g in goals.iterrows():
            target=float(g["target_value"])
            progress=min(patrimony/target,1) if target>0 else 0
            st.subheader(g["name"])
            c1,c2=st.columns(2)
            c1.metric("Atual",money(patrimony))
            c2.metric("Objetivo",money(target))
            st.progress(progress)


# ============================================================
# IMPORTAÇÕES
# ============================================================
elif menu == "Importações":
    page_header("Importações","Carregue posição atual e histórico B3 sem misturar os dois conceitos.")

    tab1,tab2=st.tabs(["Posição Detalhada","Movimentações B3"])

    with tab1:
        f=st.file_uploader("Arquivo de Posição Detalhada",type=["xlsx","xls"],key="posfile")
        if f:
            try:
                as_of, positions, pmeta = parse_position_file(f)
                prev=pd.DataFrame(positions)
                st.success(f"{len(prev)} ativos identificados. Data-base: {as_of}")
                st.dataframe(prev,use_container_width=True,hide_index=True)
                confirm=st.checkbox("Conferi a posição e desejo gravá-la.",key="confirm_pos")
                if st.button("Confirmar posição",disabled=not confirm,use_container_width=True):
                    replace_position_snapshot(as_of,positions,pmeta)
                    st.success("Posição-base atualizada.")
                    st.rerun()
            except Exception as e:
                st.error(f"Erro na posição: {e}")

    with tab2:
        f=st.file_uploader("Arquivo de Movimentações da B3",type=["xlsx","xls"],key="b3file")
        if f:
            try:
                fiis=set(base.loc[base["asset_class"]=="FII","ticker"].astype(str)) if not base.empty else set()
                op_rows, income_rows, fixed_rows = parse_b3_movements(f,fiis)
                st.success(
                    f"{len(op_rows)} operações/eventos • "
                    f"{len(income_rows)} proventos • "
                    f"{len(fixed_rows)} movimentações de renda fixa"
                )
                tabs=st.tabs(["Operações/Eventos","Proventos","Renda Fixa"])
                with tabs[0]: st.dataframe(pd.DataFrame(op_rows),use_container_width=True,hide_index=True)
                with tabs[1]: st.dataframe(pd.DataFrame(income_rows),use_container_width=True,hide_index=True)
                with tabs[2]: st.dataframe(pd.DataFrame(fixed_rows),use_container_width=True,hide_index=True)

                confirm=st.checkbox("Conferi a prévia e desejo importar.",key="confirm_b3")
                if st.button("Confirmar importação B3",disabled=not confirm,use_container_width=True):
                    upsert_operations(op_rows)
                    upsert_income(income_rows)
                    upsert_fixed_income_movements(fixed_rows)
                    st.success("Histórico B3 importado. Registros repetidos são ignorados.")
                    st.rerun()
            except Exception as e:
                st.error(f"Erro no arquivo B3: {e}")
