from __future__ import annotations

from datetime import datetime
from html import escape
from typing import Any


def _num(value: Any) -> float:
    try:
        if value is None:
            return 0.0
        return float(value)
    except Exception:
        return 0.0


def _inr(value: Any) -> str:
    return f"₹{_num(value):,.2f}"


def _safe_text(value: Any, default: str = "-") -> str:
    text = "" if value is None else str(value).strip()
    return escape(text) if text else default


def _normalize_label(key: str) -> str:
    return str(key).replace("_", " ").strip().title()


def _dict_rows(source: dict[str, Any]) -> list[tuple[str, float]]:
    rows: list[tuple[str, float]] = []
    for key, val in (source or {}).items():
        if isinstance(val, (int, float)):
            rows.append((_normalize_label(str(key)), _num(val)))
    return rows


def _safe_iso_date(value: Any, fallback: str = "-") -> str:
    if not value:
        return fallback
    try:
        dt = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
        return dt.strftime("%d %b %Y")
    except Exception:
        return _safe_text(value, fallback)


def _first_non_empty(*values: Any, default: str = "-") -> str:
    for v in values:
        if v is None:
            continue
        text = str(v).strip()
        if text:
            return text
    return default


def _section_table(
    title: str,
    rows: list[tuple[str, Any]],
    total_label: str | None = None,
    total_value: Any | None = None,
    col1: str = "Description",
    col2: str = "Amount",
) -> str:
    body = []
    for desc, amount in rows:
        body.append(
            "<tr>"
            f"<td class='desc'>{_safe_text(desc)}</td>"
            f"<td class='amt'>{_inr(amount)}</td>"
            "</tr>"
        )

    if total_label is not None:
        body.append(
            "<tr class='total-row'>"
            f"<td class='desc total'>{_safe_text(total_label)}</td>"
            f"<td class='amt total'>{_inr(total_value)}</td>"
            "</tr>"
        )

    return (
        "<section class='report-section'>"
        f"<h2>{_safe_text(title)}</h2>"
        "<table>"
        f"<thead><tr><th>{_safe_text(col1)}</th><th class='amt'>{_safe_text(col2)}</th></tr></thead>"
        f"<tbody>{''.join(body)}</tbody>"
        "</table>"
        "</section>"
    )


def _build_insights(
    reports: dict[str, Any],
    pl: dict[str, Any],
    cf: dict[str, Any],
    tax: dict[str, Any],
    gst: dict[str, Any],
) -> list[str]:
    insights: list[str] = []

    net_profit = _num(pl.get("net_profit", 0.0))
    margin = _num(pl.get("profit_margin_percent", 0.0))
    operating_exp = _num(pl.get("operating_expenses", 0.0))
    revenue = _num(pl.get("total_revenue", 0.0))
    op_cash = _num((cf.get("operating_activities", {}) or {}).get("net_operating_cash_flow", 0.0))
    tax_liability = _num((tax.get("tax_liability", {}) or {}).get("total_tax_liability", 0.0))
    gst_payable = _num((((gst.get("gstr_3b", {}) or {}).get("section_3_net_payable", {}) or {}).get("net_gst_payable", 0.0)))
    itc_claimed = _num((((gst.get("gstr_3b", {}) or {}).get("section_2_input_tax_credit", {}) or {}).get("itc_claimed", 0.0)))

    if revenue > 0:
        insights.append(f"Revenue for the period is {_inr(revenue)} with operating expenses at {_inr(operating_exp)}.")

    if net_profit >= 0:
        insights.append(f"Net profit stands at {_inr(net_profit)} with margin at {margin:.2f}%.")
    else:
        insights.append(f"Business reported a net loss of {_inr(abs(net_profit))}; cost controls are recommended.")

    if op_cash >= 0:
        insights.append(f"Operating cash flow remains positive at {_inr(op_cash)}, supporting near-term liquidity.")
    else:
        insights.append(f"Operating cash flow is negative at {_inr(abs(op_cash))}, indicating working-capital pressure.")

    insights.append(f"Estimated direct-tax liability is {_inr(tax_liability)} for the reported period.")

    if gst_payable > 0:
        insights.append(f"Net GST payable is {_inr(gst_payable)} after ITC claim of {_inr(itc_claimed)}.")
    else:
        insights.append(f"GST position indicates no net payable; ITC claim considered is {_inr(itc_claimed)}.")

    action_cards = (((reports.get("actions", {}) or {}).get("actions", [])) or [])
    critical = len([x for x in action_cards if str(x.get("priority", "")).lower() == "red"])
    if critical > 0:
        insights.append(f"{critical} critical action item(s) require immediate management review.")

    if len(insights) >= 5:
        return insights[:5]
    if len(insights) < 3:
        insights.extend([
            "Cost allocation trends should be reviewed monthly for variance control.",
            "Ensure statutory filings are aligned with transaction period cut-offs.",
            "Maintain document support for major ledger movements and reconciliations.",
        ])
    return insights[:3]


def generate_financial_statement_html(payload: dict[str, Any]) -> str:
    """Render a strict CA-style financial report HTML from report JSON payload."""
    reports = payload.get("reports", {}) if isinstance(payload, dict) else {}
    fs = reports.get("financial_statements", {}) if isinstance(reports, dict) else {}
    pl = fs.get("profit_and_loss", {}) if isinstance(fs, dict) else {}
    bs = fs.get("balance_sheet", {}) if isinstance(bs := fs, dict) else {}
    cf = fs.get("cash_flow_statement", {}) if isinstance(fs, dict) else {}
    tax = reports.get("income_tax", {}) if isinstance(reports, dict) else {}
    gst = reports.get("gst_report", {}) if isinstance(reports, dict) else {}

    user_id = _safe_text(payload.get("user_id", "-"))
    generated_at = payload.get("generated_at") or datetime.now().isoformat()
    period = _first_non_empty(
        payload.get("reporting_period"),
        pl.get("reporting_period") if isinstance(pl, dict) else None,
        default=datetime.now().strftime("%b %Y"),
    )
    client_name = _first_non_empty(
        payload.get("client_name"),
        payload.get("business_name"),
        payload.get("name"),
        f"Client {user_id}",
    )

    client_rows = [
        ("Client Name", client_name),
        ("Client ID", user_id),
        ("Reporting Period", period),
        ("Generated Date", _safe_iso_date(generated_at, datetime.now().strftime("%d %b %Y"))),
        ("Report Status", _safe_text(payload.get("status", "ok"))),
    ]

    income_rows = _dict_rows((pl.get("revenue") if isinstance(pl.get("revenue"), dict) else {}))
    if not income_rows:
        income_rows = [
            ("Total Revenue", pl.get("total_revenue", 0.0)),
            ("Other Income", pl.get("other_income", 0.0)),
        ]
    total_income = sum(_num(v) for _, v in income_rows)

    expense_breakdown = pl.get("expense_breakdown", {}) if isinstance(pl, dict) else {}
    expense_rows = _dict_rows(expense_breakdown if isinstance(expense_breakdown, dict) else {})
    if not expense_rows:
        expense_rows = [
            ("Operating Expenses", pl.get("operating_expenses", 0.0)),
            ("Personal Expenses", pl.get("personal_expenses", 0.0)),
        ]
    total_expenses = sum(_num(v) for _, v in expense_rows)

    gross_profit = _num(pl.get("gross_profit", total_income - total_expenses))
    net_itc = _num(pl.get("net_itc", 0.0))
    net_profit = _num(pl.get("net_profit", gross_profit + net_itc))

    assets_rows = _dict_rows((bs.get("assets") if isinstance(bs, dict) else {}) or {})
    liabilities_rows = _dict_rows((bs.get("liabilities") if isinstance(bs, dict) else {}) or {})
    equity_rows = _dict_rows((bs.get("equity") if isinstance(bs, dict) else {}) or {})
    liabilities_equity_rows = liabilities_rows + equity_rows

    op_rows = _dict_rows((cf.get("operating_activities") if isinstance(cf, dict) else {}) or {})
    inv_rows = _dict_rows((cf.get("investing_activities") if isinstance(cf, dict) else {}) or {})
    fin_rows = _dict_rows((cf.get("financing_activities") if isinstance(cf, dict) else {}) or {})

    taxable_income = _num(((tax.get("taxable_income_summary", {}) or {}).get("taxable_income", 0.0)))
    estimated_tax = _num(((tax.get("tax_liability", {}) or {}).get("total_tax_liability", 0.0)))
    gst_summary = ((gst.get("gstr_3b", {}) or {}).get("section_3_net_payable", {}) or {})
    gst_payable = _num(gst_summary.get("net_gst_payable", 0.0))
    gst_refund = _num(gst_summary.get("net_refund_available", 0.0))

    insights = _build_insights(reports, pl, cf, tax, gst)

    notes: list[str] = []
    for section_notes in [
        pl.get("notes", []),
        bs.get("notes", []),
        cf.get("notes", []),
        tax.get("tax_planning_advice", []),
    ]:
        if isinstance(section_notes, list):
            notes.extend([_safe_text(x) for x in section_notes if _safe_text(x) != "-"])
    if not notes:
        notes = [
            "Figures are generated from available structured transaction data and should be reviewed before filing."
        ]

    remarks_html = "".join(f"<li>{_safe_text(n)}</li>" for n in notes[:8])
    insight_html = "".join(f"<li>{_safe_text(i)}</li>" for i in insights)

    client_html = (
        "<section class='report-section'>"
        "<h2>Client Details</h2>"
        "<table>"
        "<thead><tr><th>Description</th><th>Value</th></tr></thead>"
        "<tbody>"
        + "".join(
            "<tr>"
            f"<td class='desc'>{_safe_text(k)}</td>"
            f"<td class='value'>{_safe_text(v)}</td>"
            "</tr>"
            for k, v in client_rows
        )
        + "</tbody></table></section>"
    )

    max_rows = max(len(assets_rows), len(liabilities_equity_rows), 1)
    balance_rows_html = []
    for i in range(max_rows):
        a_desc, a_amt = assets_rows[i] if i < len(assets_rows) else ("", "")
        l_desc, l_amt = liabilities_equity_rows[i] if i < len(liabilities_equity_rows) else ("", "")
        balance_rows_html.append(
            "<tr>"
            f"<td class='desc'>{_safe_text(a_desc, '')}</td>"
            f"<td class='amt'>{_inr(a_amt) if a_desc else ''}</td>"
            f"<td class='desc'>{_safe_text(l_desc, '')}</td>"
            f"<td class='amt'>{_inr(l_amt) if l_desc else ''}</td>"
            "</tr>"
        )

    balance_html = (
      "<section class='report-section'>"
        "<h2>Balance Sheet</h2>"
        "<table class='balance-table'>"
        "<thead>"
        "<tr>"
        "<th class='desc'>Assets</th><th class='amt'>Amount</th>"
        "<th class='desc'>Liabilities & Equity</th><th class='amt'>Amount</th>"
        "</tr>"
        "</thead>"
        f"<tbody>{''.join(balance_rows_html)}</tbody>"
        "</table>"
        "<table class='mt8'>"
        "<tbody>"
        f"<tr class='total-row'><td class='desc total'>Total Assets</td><td class='amt total'>{_inr(sum(_num(v) for _, v in assets_rows))}</td></tr>"
        f"<tr class='total-row'><td class='desc total'>Total Liabilities & Equity</td><td class='amt total'>{_inr(sum(_num(v) for _, v in liabilities_equity_rows))}</td></tr>"
        "</tbody>"
        "</table>"
        "</section>"
    )

    cover_page = (
        "<section class='report-section cover-page'>"
        "<h1>Comprehensive Financial Report</h1>"
        "<div class='cover-box'>"
        f"<div><span>Client Name:</span><b>{_safe_text(client_name)}</b></div>"
        f"<div><span>Reporting Period:</span><b>{_safe_text(period)}</b></div>"
        f"<div><span>Generated Date:</span><b>{_safe_iso_date(generated_at, datetime.now().strftime('%d %b %Y'))}</b></div>"
        "</div>"
        "</section>"
    )

    pnl_net_calc = (
      "<section class='report-section'>"
        "<h2>Net Profit Calculation</h2>"
        "<table>"
        "<thead><tr><th>Description</th><th class='amt'>Amount</th></tr></thead>"
        "<tbody>"
        f"<tr><td class='desc'>Total Income</td><td class='amt'>{_inr(total_income)}</td></tr>"
        f"<tr><td class='desc'>Total Expense</td><td class='amt'>{_inr(total_expenses)}</td></tr>"
        f"<tr><td class='desc'>Gross Profit</td><td class='amt'>{_inr(gross_profit)}</td></tr>"
        f"<tr><td class='desc'>Net ITC Adjustment</td><td class='amt'>{_inr(net_itc)}</td></tr>"
        f"<tr class='total-row'><td class='desc total'>Net Profit</td><td class='amt total'>{_inr(net_profit)}</td></tr>"
        "</tbody>"
        "</table>"
        "</section>"
    )

    cash_flow_html = (
      "<section class='report-section'>"
        "<h2>Cash Flow Statement</h2>"
        "<div class='flow-grid'>"
        f"{_section_table('Operating Activities', op_rows or [('Net Operating Cash Flow', _num((cf.get('operating_activities', {}) or {}).get('net_operating_cash_flow', 0.0)))])}"
        f"{_section_table('Investing Activities', inv_rows or [('Net Investing Cash Flow', _num((cf.get('investing_activities', {}) or {}).get('net_investing_cash_flow', 0.0)))])}"
        f"{_section_table('Financing Activities', fin_rows or [('Net Financing Cash Flow', _num((cf.get('financing_activities', {}) or {}).get('net_financing_cash_flow', 0.0)))])}"
        "</div>"
        "<table class='mt8'>"
        "<tbody>"
        f"<tr class='total-row'><td class='desc total'>Net Change in Cash</td><td class='amt total'>{_inr((cf.get('net_change_in_cash', 0.0) if isinstance(cf, dict) else 0.0))}</td></tr>"
        "</tbody>"
        "</table>"
        "</section>"
    )

    tax_html = (
      "<section class='report-section'>"
        "<h2>Tax Summary</h2>"
        "<table>"
        "<thead><tr><th>Description</th><th class='amt'>Amount</th></tr></thead>"
        "<tbody>"
        f"<tr><td class='desc'>Taxable Income</td><td class='amt'>{_inr(taxable_income)}</td></tr>"
        f"<tr><td class='desc'>Estimated Tax</td><td class='amt'>{_inr(estimated_tax)}</td></tr>"
        f"<tr><td class='desc'>GST Payable</td><td class='amt'>{_inr(gst_payable)}</td></tr>"
        f"<tr><td class='desc'>GST Refund Available</td><td class='amt'>{_inr(gst_refund)}</td></tr>"
        "</tbody>"
        "</table>"
        "</section>"
    )

    declaration_html = (
      "<section class='report-section'>"
        "<h2>Declaration</h2>"
        "<div class='notes'>"
        "This report has been generated from the provided records and system-derived financial computations."
        " Figures are subject to supporting documentation and statutory review."
        "</div>"
        "<table class='mt8'>"
        "<tbody>"
        "<tr><td class='desc'>Generated by Pocket CA</td><td class='amt'></td></tr>"
        "<tr><td class='desc'>Authorized Signature</td><td class='amt'>____________________</td></tr>"
        "</tbody>"
        "</table>"
        "</section>"
    )

    html = f"""<!DOCTYPE html>
<html lang=\"en\">
<head>
  <meta charset=\"UTF-8\" />
  <meta name=\"viewport\" content=\"width=device-width, initial-scale=1.0\" />
  <title>Comprehensive Financial Report</title>
  <style>
    @page {{
      size: A4;
      margin: 22mm;
    }}
    body {{
      font-family: "Times New Roman", Georgia, serif;
      color: #111;
      margin: 0;
      padding: 0;
      background: #fff;
      font-size: 12px;
      line-height: 1.4;
    }}
    .page {{
      width: 100%;
      box-sizing: border-box;
      padding-bottom: 28px;
    }}
    h1 {{
      margin: 0;
      font-size: 22px;
      text-align: center;
      letter-spacing: 0.2px;
    }}
    .report-section {{
      margin-bottom: 16px;
      page-break-inside: avoid;
    }}
    h2 {{
      font-size: 14px;
      margin: 0 0 10px 0;
      border-left: 3px solid #444;
      padding-left: 8px;
      font-weight: 700;
    }}
    .cover-page {{
      min-height: 160mm;
      display: flex;
      flex-direction: column;
      justify-content: flex-start;
      border: 1px solid #8e8e8e;
      padding: 28mm 12mm 18mm 12mm;
      page-break-after: always;
      background: #fff;
    }}
    .cover-page h1 {{
      font-size: 28px;
      margin-bottom: 18px;
      text-align: center;
    }}
    .cover-box div {{
      display: flex;
      justify-content: space-between;
      border-bottom: 1px solid #c8c8c8;
      padding: 8px 2px;
      font-size: 13px;
    }}
    .cover-box span {{ color: #444; }}
    table {{
      width: 100%;
      border-collapse: collapse;
      table-layout: fixed;
      margin-top: 4px;
    }}
    th, td {{
      border: 1px solid #8e8e8e;
      padding: 7px 8px;
      vertical-align: middle;
    }}
    thead th {{
      background: #efefef;
      font-weight: 700;
      text-align: left;
    }}
    .desc {{
      text-align: left;
      width: 70%;
      word-break: break-word;
    }}
    .value {{
      text-align: right;
    }}
    .amt {{
      text-align: right;
      width: 30%;
      white-space: nowrap;
    }}
    .balance-table .desc {{ width: 36%; }}
    .balance-table .amt {{ width: 14%; }}
    .total-row td {{
      background: #f8f8f8;
    }}
    .total {{
      font-weight: 700;
    }}
    .notes {{
      border: 1px solid #8e8e8e;
      padding: 8px 12px;
    }}
    .notes ul {{
      margin: 0;
      padding-left: 18px;
    }}
    .notes li {{
      margin: 4px 0;
    }}
    .flow-grid {{
      display: grid;
      grid-template-columns: 1fr;
      gap: 10px;
    }}
    .mt8 {{ margin-top: 8px; }}
    .footer {{
      position: fixed;
      left: 0;
      right: 0;
      bottom: 0;
      font-size: 10px;
      color: #4d4d4d;
      border-top: 1px solid #aaa;
      padding: 6px 14mm 0 14mm;
      display: flex;
      justify-content: space-between;
      align-items: center;
      background: #fff;
    }}
    .page-no::after {{
      content: counter(page);
    }}
  </style>
</head>
<body>
  <div class=\"page\">
    {cover_page}
    {client_html}
    <section class=\"report-section\"><h2>Profit &amp; Loss Statement</h2></section>
    {_section_table("Income Table", income_rows, "Total Income", total_income, "Particulars", "Amount")}
    {_section_table("Expense Table", expense_rows, "Total Expense", total_expenses, "Particulars", "Amount")}
    {pnl_net_calc}
    {balance_html}
    {cash_flow_html}
    {tax_html}

    <section class=\"report-section\">
      <h2>AI Financial Insights</h2>
      <div class=\"notes\">
        <ul>{insight_html}</ul>
      </div>
    </section>

    <section class=\"report-section\">
      <h2>Notes to Accounts</h2>
      <div class=\"notes\">
        <ul>{remarks_html}</ul>
      </div>
    </section>

    {declaration_html}
  </div>

  <div class=\"footer\">
    <span>Generated by Pocket CA</span>
    <span>Page <span class=\"page-no\"></span></span>
  </div>
</body>
</html>"""

    return html
