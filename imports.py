
import hashlib
import re
from datetime import date
import pandas as pd


def br_num(value):
    if value is None:
        return 0.0
    if isinstance(value, (int, float)):
        return float(value)

    txt = str(value).strip()
    if txt in ("", "-", "Indefinido", "None", "nan"):
        return 0.0

    txt = txt.replace("R$", "").replace("%", "").replace(" ", "")
    if "," in txt and "." in txt:
        txt = txt.replace(".", "").replace(",", ".")
    elif "," in txt:
        txt = txt.replace(",", ".")

    try:
        return float(txt)
    except Exception:
        return 0.0


def _find_row(df, text, start=0):
    target = text.lower()
    for i in range(start, len(df)):
        if target in str(df.iloc[i, 0] or "").lower():
            return i
    return None


def _date_base(df):
    for i in range(min(8, len(df))):
        for v in df.iloc[i].tolist():
            m = re.search(r"\b(\d{2}/\d{2}/\d{4})\b", str(v))
            if m:
                return pd.to_datetime(m.group(1), dayfirst=True).date().isoformat()
    return date.today().isoformat()


def parse_position_file(file):
    df = pd.read_excel(file, sheet_name=0, header=None, dtype=object)
    df = df.where(pd.notna(df), None)

    as_of = _date_base(df)
    row_actions = _find_row(df, "Ações")
    row_fiis = _find_row(df, "Fundos Imobiliários")
    row_income = _find_row(df, "Dividendos, proventos e outras distribuições")

    if row_actions is None or row_fiis is None:
        raise ValueError("Não foi possível localizar as seções de Ações e FIIs.")

    positions = []

    # Ações
    for i in range(row_actions + 3, row_fiis):
        ticker = str(df.iloc[i, 0] or "").strip().upper()
        if not re.fullmatch(r"[A-Z]{4}\d{1,2}", ticker):
            continue
        qty = br_num(df.iloc[i, 6])
        if qty <= 0:
            continue
        pm_raw = df.iloc[i, 4]
        undef = str(pm_raw).strip().lower() == "indefinido"
        positions.append({
            "asset_class": "Ação",
            "ticker": ticker,
            "name": ticker,
            "quantity": qty,
            "avg_price": None if undef else br_num(pm_raw),
            "imported_price": br_num(df.iloc[i, 5]),
            "imported_market_value": br_num(df.iloc[i, 1]),
            "avg_price_undefined": undef,
            "source": getattr(file, "name", "PosicaoDetalhada.xlsx"),
        })

    # FIIs
    end_fiis = row_income if row_income is not None else len(df)
    for i in range(row_fiis + 3, end_fiis):
        ticker = str(df.iloc[i, 0] or "").strip().upper()
        if not re.fullmatch(r"[A-Z]{4}\d{1,2}", ticker):
            continue
        qty = br_num(df.iloc[i, 6])
        if qty <= 0:
            continue
        pm_raw = df.iloc[i, 4]
        undef = str(pm_raw).strip().lower() == "indefinido"
        positions.append({
            "asset_class": "FII",
            "ticker": ticker,
            "name": ticker,
            "quantity": qty,
            "avg_price": None if undef else br_num(pm_raw),
            "imported_price": br_num(df.iloc[i, 5]),
            "imported_market_value": br_num(df.iloc[i, 2]),
            "avg_price_undefined": undef,
            "source": getattr(file, "name", "PosicaoDetalhada.xlsx"),
        })

    meta = {
        "declared_portfolio": br_num(df.iloc[3, 0]) if len(df) > 3 else 0,
        "declared_invested": br_num(df.iloc[3, 1]) if len(df) > 3 else 0,
        "available_cash": br_num(df.iloc[3, 2]) if len(df) > 3 else 0,
        "source_file": getattr(file, "name", "PosicaoDetalhada.xlsx"),
    }

    return as_of, positions, meta


def _ticker(product):
    first = str(product or "").upper().split(" - ")[0].strip()
    if re.fullmatch(r"[A-Z0-9]{4,8}", first) and re.search(r"\d", first):
        return first
    return ""


def _fixed_income(product):
    p = str(product or "").upper().strip()
    return any(p.startswith(x) for x in ["CDB -", "LCI -", "LCA -", "CRI -", "CRA -", "DEB -", "TESOURO "])


def _key(*values):
    raw = "|".join(str(v).strip() for v in values)
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def parse_b3_movements(file, known_fiis=None):
    known_fiis = {str(x).upper() for x in (known_fiis or [])}
    df = pd.read_excel(file, sheet_name=0, dtype=object)

    required = [
        "Entrada/Saída", "Data", "Movimentação", "Produto",
        "Instituição", "Quantidade", "Preço unitário", "Valor da Operação"
    ]
    missing = [c for c in required if c not in df.columns]
    if missing:
        raise ValueError("Arquivo B3 incompatível. Faltam: " + ", ".join(missing))

    operations, income, fixed = [], [], []

    for _, r in df.iterrows():
        direction = str(r.get("Entrada/Saída") or "").strip()
        movement = str(r.get("Movimentação") or "").strip()
        product = str(r.get("Produto") or "").strip()
        institution = str(r.get("Instituição") or "").strip()
        qty = br_num(r.get("Quantidade"))
        unit_price = br_num(r.get("Preço unitário"))
        value = br_num(r.get("Valor da Operação"))
        dt = pd.to_datetime(r.get("Data"), dayfirst=True, errors="coerce")
        if pd.isna(dt):
            continue
        iso_date = dt.date().isoformat()

        ext = _key(direction, iso_date, movement, product, institution, qty, unit_price, value)

        if _fixed_income(product):
            fixed.append({
                "movement_date": iso_date,
                "direction": direction,
                "movement": movement,
                "product": product,
                "institution": institution,
                "quantity": qty,
                "unit_price": unit_price,
                "operation_value": value,
                "external_key": ext,
                "source": "B3",
            })
            continue

        ticker = _ticker(product)
        if not ticker:
            continue

        asset_class = "FII" if ticker in known_fiis or "FII" in product.upper() else "Ação"
        m = movement.upper()
        d = direction.lower()

        if m in {"DIVIDENDO", "JUROS SOBRE CAPITAL PRÓPRIO", "RENDIMENTO"}:
            income_type = {
                "DIVIDENDO": "Dividendos",
                "JUROS SOBRE CAPITAL PRÓPRIO": "JCP",
                "RENDIMENTO": "Rendimento" if asset_class == "FII" else "Outro rendimento",
            }[m]
            income.append({
                "ticker": ticker,
                "asset_class": asset_class,
                "income_type": income_type,
                "payment_date": iso_date,
                "base_quantity": qty,
                "amount_per_unit": unit_price,
                "gross_amount": value,
                "tax_amount": 0,
                "net_amount": value,
                "status": "Recebido",
                "origin": "B3",
                "external_key": ext,
            })
            continue

        op_type = movement.title()
        if m == "TRANSFERÊNCIA - LIQUIDAÇÃO":
            op_type = "Compra" if d == "credito" else "Venda"
        elif m == "BONIFICAÇÃO EM ATIVOS":
            op_type = "Bonificação"
        elif m == "INCORPORAÇÃO":
            op_type = "Evento societário"

        operations.append({
            "operation_date": iso_date,
            "asset_class": asset_class,
            "ticker": ticker,
            "name": product.split(" - ", 1)[1] if " - " in product else ticker,
            "operation_type": op_type,
            "quantity": qty,
            "unit_price": unit_price,
            "costs": 0,
            "institution": institution,
            "notes": f"B3: {movement} | {direction}",
            "origin": "B3",
            "external_key": ext,
        })

    return operations, income, fixed


def summarize_fixed_income(df):
    cols = [
        "product","institution","type","applications","purchase_sale_out",
        "redemptions_maturities","amortizations","interest_received","estimated_balance"
    ]
    if df is None or df.empty:
        return pd.DataFrame(columns=cols)

    x = df.copy()
    x["operation_value"] = pd.to_numeric(x["operation_value"], errors="coerce").fillna(0.0)

    rows = []
    for _, r in x.iterrows():
        movement = str(r["movement"]).upper().strip()
        direction = str(r["direction"]).lower().strip()
        value = float(r["operation_value"])

        app = out = red = amort = interest = 0.0

        if "PAGAMENTO DE JUROS" in movement:
            interest = value
        elif "AMORTIZA" in movement:
            amort = value
        elif "RESGATE" in movement or "VENCIMENTO" in movement:
            red = value
        elif movement in {"APLICAÇÃO", "APLICACAO", "COMPRA / VENDA"}:
            if direction == "credito":
                app = value
            elif direction == "debito":
                out = value

        p = str(r["product"]).upper()
        ftype = "Outro"
        for prefix, label in [
            ("CDB","CDB"),("LCI","LCI"),("LCA","LCA"),("CRI","CRI"),
            ("CRA","CRA"),("DEB","Debênture"),("TESOURO","Tesouro")
        ]:
            if p.startswith(prefix):
                ftype = label
                break

        rows.append({
            "product": r["product"],
            "institution": r["institution"],
            "type": ftype,
            "applications": app,
            "purchase_sale_out": out,
            "redemptions_maturities": red,
            "amortizations": amort,
            "interest_received": interest,
        })

    out = pd.DataFrame(rows)
    grp = out.groupby(["product","institution","type"], dropna=False).sum().reset_index()
    grp["estimated_balance"] = (
        grp["applications"]
        - grp["purchase_sale_out"]
        - grp["redemptions_maturities"]
        - grp["amortizations"]
    ).clip(lower=0)
    return grp.sort_values("estimated_balance", ascending=False)
