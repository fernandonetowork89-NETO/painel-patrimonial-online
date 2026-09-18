
from datetime import date
import pandas as pd
import streamlit as st
from auth import current_user_id


def sb():
    return st.session_state.sb


def uid():
    user_id = current_user_id()
    if not user_id:
        raise RuntimeError("Usuário não autenticado.")
    return user_id


def select_df(table, order_by=None, desc=False):
    q = sb().table(table).select("*")
    if order_by:
        q = q.order(order_by, desc=desc)
    data = q.execute().data or []
    return pd.DataFrame(data)


def latest_meta():
    df = select_df("portfolio_meta", "as_of", True)
    return df.iloc[0].to_dict() if not df.empty else {}


def latest_positions():
    meta = latest_meta()
    if not meta:
        return pd.DataFrame()

    as_of = meta["as_of"]
    data = (
        sb().table("positions_base")
        .select("*")
        .eq("as_of", as_of)
        .execute()
        .data or []
    )
    return pd.DataFrame(data)


def operations_df():
    return select_df("operations", "operation_date", True)


def income_df():
    return select_df("income", "payment_date", True)


def fixed_income_df():
    return select_df("fixed_income_movements", "movement_date", True)


def goals_df():
    return select_df("goals", "created_at", True)


def replace_position_snapshot(as_of, positions, meta):
    user_id = uid()

    sb().table("positions_base").delete().eq("as_of", as_of).execute()
    sb().table("portfolio_meta").delete().eq("as_of", as_of).execute()

    rows = []
    for p in positions:
        row = dict(p)
        row["user_id"] = user_id
        row["as_of"] = as_of
        rows.append(row)

    if rows:
        sb().table("positions_base").insert(rows).execute()

    meta_row = dict(meta)
    meta_row["user_id"] = user_id
    meta_row["as_of"] = as_of
    sb().table("portfolio_meta").insert(meta_row).execute()


def _upsert(table, rows):
    if not rows:
        return 0
    user_id = uid()
    payload = []
    for row in rows:
        r = dict(row)
        r["user_id"] = user_id
        payload.append(r)

    # Atualiza registro já existente quando external_key coincidir.
    sb().table(table).upsert(
        payload,
        on_conflict="user_id,external_key",
        ignore_duplicates=False
    ).execute()
    return len(payload)


def upsert_operations(rows):
    return _upsert("operations", rows)


def upsert_income(rows):
    return _upsert("income", rows)


def upsert_fixed_income_movements(rows):
    return _upsert("fixed_income_movements", rows)


def add_operation(row):
    r = dict(row)
    r["user_id"] = uid()
    sb().table("operations").insert(r).execute()


def add_income(row):
    r = dict(row)
    r["user_id"] = uid()
    sb().table("income").insert(r).execute()


def add_goal(row):
    r = dict(row)
    r["user_id"] = uid()
    sb().table("goals").insert(r).execute()
