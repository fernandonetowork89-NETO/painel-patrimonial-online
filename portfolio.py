
import pandas as pd


def calculate_positions(base_df, operations_df):
    positions = {}

    if base_df is not None and not base_df.empty:
        for _, r in base_df.iterrows():
            key = (str(r["asset_class"]), str(r["ticker"]).upper())
            qty = float(r["quantity"] or 0)
            avg = None if bool(r.get("avg_price_undefined", False)) else r.get("avg_price")
            cost = qty * float(avg or 0)
            positions[key] = {
                "asset_class": key[0],
                "ticker": key[1],
                "name": r.get("name") or key[1],
                "quantity": qty,
                "cost": cost,
                "avg_price_undefined": bool(r.get("avg_price_undefined", False)),
                "as_of": str(r.get("as_of") or ""),
                "fallback_price": float(r.get("imported_price") or 0),
            }

    if operations_df is None or operations_df.empty:
        operations_df = pd.DataFrame()

    for _, r in operations_df.iterrows():
        key = (str(r["asset_class"]), str(r["ticker"]).upper())
        if key not in positions:
            positions[key] = {
                "asset_class": key[0],
                "ticker": key[1],
                "name": r.get("name") or key[1],
                "quantity": 0.0,
                "cost": 0.0,
                "avg_price_undefined": False,
                "as_of": "",
                "fallback_price": 0.0,
            }

        p = positions[key]
        op_date = pd.to_datetime(r["operation_date"], errors="coerce")
        base_date = pd.to_datetime(p["as_of"], errors="coerce")

        if pd.notna(base_date) and pd.notna(op_date) and op_date <= base_date:
            continue

        typ = str(r["operation_type"]).lower().strip()
        qty = float(r.get("quantity") or 0)
        price = float(r.get("unit_price") or 0)
        costs = float(r.get("costs") or 0)

        if typ in {"compra", "subscrição", "subscricao"}:
            p["quantity"] += qty
            p["cost"] += qty * price + costs
        elif typ in {"bonificação", "bonificacao"}:
            p["quantity"] += qty
        elif typ == "venda":
            if p["quantity"] > 0:
                avg = p["cost"] / p["quantity"] if p["quantity"] else 0
                sold = min(qty, p["quantity"])
                p["cost"] -= avg * sold
                p["quantity"] -= sold

        positions[key] = p

    rows = []
    for p in positions.values():
        if p["quantity"] <= 0:
            continue
        avg = p["cost"] / p["quantity"] if p["quantity"] else 0
        rows.append({
            **p,
            "avg_price": avg,
            "invested_value": p["cost"],
        })

    return pd.DataFrame(rows)


def enrich_with_quotes(pos_df, quotes):
    if pos_df is None or pos_df.empty:
        return pd.DataFrame()

    out = pos_df.copy()

    def price(row):
        q = quotes.get(row["ticker"], {})
        return float(q.get("price") or row.get("fallback_price") or 0)

    def change(row):
        return float(quotes.get(row["ticker"], {}).get("change_pct") or 0)

    out["market_price"] = out.apply(price, axis=1)
    out["change_pct"] = out.apply(change, axis=1)
    out["market_value"] = out["quantity"] * out["market_price"]
    out["result"] = out["market_value"] - out["invested_value"]
    out["return_pct"] = out.apply(
        lambda r: (r["result"] / r["invested_value"] * 100) if r["invested_value"] > 0 else 0,
        axis=1
    )
    return out
