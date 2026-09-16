import os
from datetime import datetime, timezone
import math
import requests
import pandas as pd
import streamlit as st
import plotly.express as px
import plotly.graph_objects as go

st.set_page_config(page_title="Calculadora bursátil", page_icon="📈", layout="wide")

API_BASE = "https://financialmodelingprep.com/stable"


def get_api_key():
    try:
        return st.secrets["FMP_API_KEY"]
    except Exception:
        return os.getenv("FMP_API_KEY", "")


def api_get(endpoint, **params):
    key = get_api_key()
    if not key:
        raise RuntimeError("Falta configurar FMP_API_KEY.")
    params["apikey"] = key
    response = requests.get(f"{API_BASE}/{endpoint}", params=params, timeout=20)
    response.raise_for_status()
    data = response.json()
    if isinstance(data, dict) and (data.get("Error Message") or data.get("error")):
        raise RuntimeError(data.get("Error Message") or data.get("error"))
    return data


def first_item(data):
    return data[0] if isinstance(data, list) and data else (data if isinstance(data, dict) else {})


def safe_num(value):
    try:
        if value is None or value == "":
            return None
        return float(value)
    except Exception:
        return None


def div(a, b):
    a, b = safe_num(a), safe_num(b)
    return None if a is None or b in (None, 0) else a / b


def pct_change(current, previous):
    ratio = div(current, previous)
    return None if ratio is None else ratio - 1


def fmt_money(value, currency=""):
    return "—" if value is None else f"{value:,.2f} {currency}".replace(",", "X").replace(".", ",").replace("X", ".")


def fmt_pct(value):
    return "—" if value is None else f"{value:.1%}".replace(".", ",")


def fmt_mult(value):
    return "—" if value is None else f"{value:.2f}x".replace(".", ",")


def search_companies(query):
    by_symbol = api_get("search-symbol", query=query, limit=10)
    by_name = api_get("search-name", query=query, limit=10)
    unique = {}
    for item in (by_symbol or []) + (by_name or []):
        key = (item.get("symbol"), item.get("exchange"))
        if key[0] and key not in unique:
            unique[key] = item
    return list(unique.values())


def load_company(symbol):
    quote = first_item(api_get("quote", symbol=symbol))
    profile = first_item(api_get("profile", symbol=symbol))
    income = api_get("income-statement", symbol=symbol, period="annual", limit=2)
    balance = api_get("balance-sheet-statement", symbol=symbol, period="annual", limit=2)
    cashflow = api_get("cash-flow-statement", symbol=symbol, period="annual", limit=2)
    ratios = api_get("ratios", symbol=symbol, period="annual", limit=2)
    metrics = api_get("key-metrics", symbol=symbol, period="annual", limit=2)
    return {
        "quote": quote, "profile": profile,
        "income": income or [], "balance": balance or [],
        "cashflow": cashflow or [], "ratios": ratios or [], "metrics": metrics or []
    }


def row(items, n=0):
    return items[n] if isinstance(items, list) and len(items) > n else {}


def fundamental_table(data):
    q, p = data["quote"], data["profile"]
    inc0, inc1 = row(data["income"], 0), row(data["income"], 1)
    bal0, bal1 = row(data["balance"], 0), row(data["balance"], 1)
    cf0, cf1 = row(data["cashflow"], 0), row(data["cashflow"], 1)
    ra0, ra1 = row(data["ratios"], 0), row(data["ratios"], 1)
    km0, km1 = row(data["metrics"], 0), row(data["metrics"], 1)

    def pick(d, *keys):
        for k in keys:
            if d.get(k) is not None:
                return safe_num(d.get(k))
        return None

    current = {
        "Capitalización bursátil": pick(q, "marketCap") or pick(p, "marketCap"),
        "Valor de empresa (EV)": pick(km0, "enterpriseValue"),
        "PER": pick(q, "pe") or pick(ra0, "priceEarningsRatio"),
        "PEG": pick(ra0, "priceEarningsToGrowthRatio"),
        "Precio / ventas": pick(ra0, "priceToSalesRatio"),
        "Precio / valor contable": pick(ra0, "priceToBookRatio"),
        "EV / EBITDA": pick(km0, "enterpriseValueOverEBITDA"),
        "Ingresos": pick(inc0, "revenue"),
        "EBITDA": pick(inc0, "ebitda"),
        "Beneficio neto": pick(inc0, "netIncome"),
        "BPA / EPS": pick(inc0, "eps", "epsdiluted"),
        "Margen EBITDA": div(pick(inc0, "ebitda"), pick(inc0, "revenue")),
        "Margen neto": pick(ra0, "netProfitMargin") or div(pick(inc0, "netIncome"), pick(inc0, "revenue")),
        "ROE": pick(ra0, "returnOnEquity"),
        "ROA": pick(ra0, "returnOnAssets"),
        "ROIC": pick(ra0, "returnOnCapitalEmployed") or pick(km0, "roic"),
        "Patrimonio neto": pick(bal0, "totalStockholdersEquity", "totalEquity"),
        "Activos totales": pick(bal0, "totalAssets"),
        "Deuda total": pick(bal0, "totalDebt"),
        "Caja y equivalentes": pick(bal0, "cashAndCashEquivalents"),
        "Deuda neta": pick(bal0, "netDebt"),
        "Deuda neta / EBITDA": div(pick(bal0, "netDebt"), pick(inc0, "ebitda")),
        "Ratio corriente": pick(ra0, "currentRatio"),
        "Cobertura de intereses": pick(ra0, "interestCoverage"),
        "Flujo de caja operativo": pick(cf0, "operatingCashFlow", "netCashProvidedByOperatingActivities"),
        "CAPEX": abs(pick(cf0, "capitalExpenditure") or 0),
        "Flujo de caja libre (FCF)": pick(cf0, "freeCashFlow"),
        "Rendimiento FCF": div(pick(cf0, "freeCashFlow"), pick(q, "marketCap")),
        "Dividendo por acción": pick(ra0, "dividendPerShare"),
        "Rentabilidad por dividendo": pick(ra0, "dividendYield"),
        "Payout": pick(ra0, "dividendPayoutRatio"),
    }
    previous = {
        "Capitalización bursátil": None,
        "Valor de empresa (EV)": pick(km1, "enterpriseValue"),
        "PER": pick(ra1, "priceEarningsRatio"),
        "PEG": pick(ra1, "priceEarningsToGrowthRatio"),
        "Precio / ventas": pick(ra1, "priceToSalesRatio"),
        "Precio / valor contable": pick(ra1, "priceToBookRatio"),
        "EV / EBITDA": pick(km1, "enterpriseValueOverEBITDA"),
        "Ingresos": pick(inc1, "revenue"),
        "EBITDA": pick(inc1, "ebitda"),
        "Beneficio neto": pick(inc1, "netIncome"),
        "BPA / EPS": pick(inc1, "eps", "epsdiluted"),
        "Margen EBITDA": div(pick(inc1, "ebitda"), pick(inc1, "revenue")),
        "Margen neto": pick(ra1, "netProfitMargin") or div(pick(inc1, "netIncome"), pick(inc1, "revenue")),
        "ROE": pick(ra1, "returnOnEquity"), "ROA": pick(ra1, "returnOnAssets"),
        "ROIC": pick(ra1, "returnOnCapitalEmployed") or pick(km1, "roic"),
        "Patrimonio neto": pick(bal1, "totalStockholdersEquity", "totalEquity"),
        "Activos totales": pick(bal1, "totalAssets"), "Deuda total": pick(bal1, "totalDebt"),
        "Caja y equivalentes": pick(bal1, "cashAndCashEquivalents"), "Deuda neta": pick(bal1, "netDebt"),
        "Deuda neta / EBITDA": div(pick(bal1, "netDebt"), pick(inc1, "ebitda")),
        "Ratio corriente": pick(ra1, "currentRatio"), "Cobertura de intereses": pick(ra1, "interestCoverage"),
        "Flujo de caja operativo": pick(cf1, "operatingCashFlow", "netCashProvidedByOperatingActivities"),
        "CAPEX": abs(pick(cf1, "capitalExpenditure") or 0), "Flujo de caja libre (FCF)": pick(cf1, "freeCashFlow"),
        "Rendimiento FCF": None, "Dividendo por acción": pick(ra1, "dividendPerShare"),
        "Rentabilidad por dividendo": pick(ra1, "dividendYield"), "Payout": pick(ra1, "dividendPayoutRatio"),
    }
    percent_metrics = {"Margen EBITDA", "Margen neto", "ROE", "ROA", "ROIC", "Rendimiento FCF", "Rentabilidad por dividendo", "Payout"}
    multiple_metrics = {"PER", "PEG", "Precio / ventas", "Precio / valor contable", "EV / EBITDA", "Deuda neta / EBITDA", "Ratio corriente", "Cobertura de intereses"}
    currency_metrics = set(current) - percent_metrics - multiple_metrics
    rows = []
    for metric in current:
        c, old = current[metric], previous.get(metric)
        if metric in percent_metrics:
            fc, fp = fmt_pct(c), fmt_pct(old)
        elif metric in multiple_metrics:
            fc, fp = fmt_mult(c), fmt_mult(old)
        else:
            fc, fp = fmt_money(c), fmt_money(old)
        rows.append({"Indicador": metric, "Actual": fc, "Año anterior": fp, "Variación": fmt_pct(pct_change(c, old))})
    return pd.DataFrame(rows), current, inc0, inc1, bal0, bal1, cf0, cf1

st.title("📈 Calculadora de rentabilidad y análisis fundamental")
st.caption("Herramienta informativa. Las cotizaciones pueden llevar retraso. No constituye asesoramiento financiero.")

if not get_api_key():
    st.warning("Para usar la aplicación debes configurar una clave de Financial Modeling Prep como FMP_API_KEY. Consulta la pestaña Ayuda.")

buscar, ayuda = st.tabs(["Buscador y análisis", "Ayuda"])
with buscar:
    query = st.text_input("Nombre de la empresa o ticker", placeholder="Ej.: Microsoft o MSFT")
    if st.button("Buscar empresa", type="primary", disabled=not query.strip()):
        try:
            with st.spinner("Buscando empresas..."):
                st.session_state["matches"] = search_companies(query.strip())
        except Exception as exc:
            st.error(f"No se pudo realizar la búsqueda: {exc}")

    matches = st.session_state.get("matches", [])
    if matches:
        labels = [f"{x.get('symbol')} | {x.get('name')} | {x.get('exchangeFullName') or x.get('exchange')} | {x.get('currency','')}" for x in matches]
        chosen = st.selectbox("Selecciona la empresa y el mercado correctos", range(len(labels)), format_func=lambda i: labels[i])
        symbol = matches[chosen].get("symbol")
        if st.button("Actualizar cotización y fundamentales"):
            try:
                with st.spinner("Descargando los datos más recientes disponibles..."):
                    st.session_state["company_data"] = load_company(symbol)
                    st.session_state["updated_at"] = datetime.now(timezone.utc).astimezone()
            except Exception as exc:
                st.error(f"No se pudieron recuperar los datos: {exc}")

    data = st.session_state.get("company_data")
    if data:
        q, p = data["quote"], data["profile"]
        currency = q.get("currency") or p.get("currency") or ""
        price = safe_num(q.get("price"))
        change_pct = safe_num(q.get("changesPercentage"))
        updated = st.session_state.get("updated_at")
        st.subheader(f"{q.get('name') or p.get('companyName') or ''} ({q.get('symbol') or p.get('symbol') or ''})")
        st.caption(f"Mercado: {q.get('exchange') or p.get('exchange') or '—'} | Moneda: {currency or '—'} | Consulta: {updated.strftime('%d/%m/%Y %H:%M:%S') if updated else '—'}")
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Cotización", fmt_money(price, currency))
        c2.metric("Variación diaria", fmt_pct(change_pct/100 if change_pct is not None else None))
        c3.metric("Máximo 52 semanas", fmt_money(safe_num(q.get("yearHigh")), currency))
        c4.metric("Mínimo 52 semanas", fmt_money(safe_num(q.get("yearLow")), currency))

        st.divider()
        st.subheader("Calculadora de la operación")
        a,b,c,d = st.columns(4)
        capital_total = a.number_input("Capital total", min_value=0.0, value=10000.0, step=100.0)
        capital_operacion = b.number_input("Capital destinado", min_value=0.0, value=2000.0, step=100.0)
        riesgo_pct = c.number_input("Riesgo máximo (%)", min_value=0.0, value=1.0, step=0.1) / 100
        precio_entrada = d.number_input("Precio de entrada", min_value=0.0, value=float(price or 0), step=0.01)
        e,f,g = st.columns(3)
        precio_salida = e.number_input("Precio de salida / objetivo", min_value=0.0, value=float(price or 0), step=0.01)
        stop_manual = f.checkbox("Introducir stop loss manualmente")
        acciones = math.floor(capital_operacion / precio_entrada) if precio_entrada > 0 else 0
        riesgo_eur = capital_total * riesgo_pct
        stop_auto = max(0, precio_entrada - riesgo_eur / acciones) if acciones else 0
        stop_loss = g.number_input("Stop loss", min_value=0.0, value=float(stop_auto), step=0.01, disabled=not stop_manual)
        if not stop_manual:
            stop_loss = stop_auto
        invertido = acciones * precio_entrada
        peso = invertido / capital_total if capital_total else 0
        perdida = max(0, acciones * (precio_entrada - stop_loss))
        ganancia = acciones * (precio_salida - precio_entrada)
        rent_inv = ganancia / invertido if invertido else 0
        rent_total = ganancia / capital_total if capital_total else 0
        r1,r2,r3,r4 = st.columns(4)
        r1.metric("Acciones", f"{acciones:,}".replace(",", "."))
        r2.metric("Importe invertido", fmt_money(invertido, currency))
        r3.metric("Capital utilizado", fmt_pct(peso))
        r4.metric("¿Supera el 20%?", "SÍ" if peso > .20 else "NO")
        r5,r6,r7,r8 = st.columns(4)
        r5.metric("Pérdida hasta stop", fmt_money(perdida, currency))
        r6.metric("Ganancia estimada", fmt_money(ganancia, currency))
        r7.metric("Rentabilidad invertido", fmt_pct(rent_inv))
        r8.metric("Rentabilidad capital", fmt_pct(rent_total))

        st.divider()
        st.subheader("Análisis fundamental")
        df, fundamentals, inc0, inc1, bal0, bal1, cf0, cf1 = fundamental_table(data)
        st.dataframe(df, use_container_width=True, hide_index=True)

        st.subheader("Evolución anual")
        chart_df = pd.DataFrame({
            "Indicador": ["Ingresos", "EBITDA", "Beneficio neto", "FCF"] * 2,
            "Periodo": [str(inc1.get("calendarYear") or inc1.get("date") or "Anterior")]*4 + [str(inc0.get("calendarYear") or inc0.get("date") or "Actual")]*4,
            "Importe": [safe_num(inc1.get("revenue")) or 0, safe_num(inc1.get("ebitda")) or 0, safe_num(inc1.get("netIncome")) or 0, safe_num(cf1.get("freeCashFlow")) or 0,
                        safe_num(inc0.get("revenue")) or 0, safe_num(inc0.get("ebitda")) or 0, safe_num(inc0.get("netIncome")) or 0, safe_num(cf0.get("freeCashFlow")) or 0]
        })
        fig = px.bar(chart_df, x="Indicador", y="Importe", color="Periodo", barmode="group", title="Resultados fundamentales")
        st.plotly_chart(fig, use_container_width=True)

        output = df.to_csv(index=False).encode("utf-8-sig")
        st.download_button("Descargar fundamentales en CSV", output, file_name=f"fundamentales_{q.get('symbol','empresa')}.csv", mime="text/csv")

with ayuda:
    st.markdown("""
### Configuración en tres pasos
1. Crea una cuenta y consigue una clave API en Financial Modeling Prep.
2. En Streamlit Community Cloud, abre **App settings > Secrets**.
3. Añade la clave así:

```toml
FMP_API_KEY = "TU_CLAVE_AQUI"
```

La clave nunca debe escribirse directamente en `app.py` ni compartirse dentro del archivo.

### Avisos
- La disponibilidad, retraso y cobertura dependen del proveedor y del plan contratado.
- Algunos ratios pueden no estar disponibles para todas las empresas, fondos, ETF o mercados.
- Confirma siempre la empresa, el ticker, el mercado, la moneda y el ejercicio fiscal.
- La herramienta es informativa y no constituye asesoramiento financiero.
""")
