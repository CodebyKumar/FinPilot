from __future__ import annotations

from copy import deepcopy
import re
from typing import Any

ITR1_REPORT_NAME = "ITR-1"

ITR1_TEMPLATE_SCHEMA: dict[str, Any] = {
    "PART_A_GENERAL_INFORMATION": {
        "A1": "PAN",
        "A2": "First Name",
        "A2a": "Middle Name",
        "A3": "Last Name",
        "A4": "Date of Birth",
        "A5": "Aadhaar Number",
        "A6a": "Primary Mobile Number",
        "A6b": "Secondary Mobile Number",
        "A7a": "Primary Email ID",
        "A7b": "Secondary Email ID",
        "ADDRESS_PRIMARY": {
            "A8a": "Flat/Door/Block No.",
            "A9a": "Premises/Building/Village",
            "A10a": "Road/Street/Post Office",
            "A11a": "Town/City/District",
            "A12a": "State",
            "A13a": "Country",
            "A14a": "PIN Code",
        },
        "ADDRESS_SECONDARY": {
            "A8b": "Flat/Door/Block No.",
            "A9b": "Premises/Building/Village",
            "A10b": "Road/Street/Post Office",
            "A11b": "Town/City/District",
            "A12b": "State",
            "A13b": "Country",
            "A14b": "PIN Code",
        },
        "A15": "Filed under section",
        "A16": "Filed in response to notice u/s",
        "A17": "Nature of employment",
        "A18": "Receipt No. & Date (Original Return)",
        "A19": "DIN & Date of Notice/Order",
        "A20": "Opting out of new tax regime (115BAC)",
        "A21": {
            "general": "Filing under seventh proviso",
            "i": "Foreign travel expenditure",
            "ii": "Electricity expenditure",
            "iii": "Other prescribed conditions",
        },
        "A22": {
            "general": "Representative assessee",
            "name": "Representative Name",
            "email": "Representative Email",
            "contact": "Representative Contact Number",
        },
    },
    "PART_B_GROSS_TOTAL_INCOME": {
        "B1": {
            "ia": "Salary u/s 17(1)",
            "ib": "Perquisites u/s 17(2)",
            "ic": "Profit in lieu of salary u/s 17(3)",
            "ii": "Exempt allowances u/s 10",
            "iii": "Net Salary",
            "iva": "Standard Deduction",
            "ivb": "Entertainment Allowance",
            "ivc": "Professional Tax",
            "total": "Income from Salary",
        },
        "B2": {
            "property_details": {
                "address": "Property Address",
                "co_owned": "Is Co-owned",
                "share": "Ownership %",
                "co_owner_name": "Co-owner Name",
                "co_owner_pan": "Co-owner PAN/Aadhaar",
                "tenant_name": "Tenant Name",
                "tenant_pan": "Tenant PAN/Aadhaar",
            },
            "1a": "Gross Rent",
            "1b": "Unrealized Rent",
            "1c": "Municipal Tax",
            "1d": "Total Deductions",
            "1e": "Annual Value",
            "1f": "Share of Annual Value",
            "1g": "30% Deduction",
            "1h": "Interest on Loan",
            "1i": "Total Deduction",
            "1j": "Arrears Rent",
            "1k": "Income from Property",
            "total": "Income from House Property",
        },
        "B3": "Income from Other Sources",
        "B4": "Gross Total Income",
    },
    "PART_C_DEDUCTIONS": {
        "80C": "Investments",
        "80CCC": "Pension Fund",
        "80CCD1": "NPS Contribution",
        "80CCD1B": "Additional NPS",
        "80CCD2": "Employer NPS",
        "80CCH": "Agniveer Fund",
        "80D": "Medical Insurance",
        "80DD": "Disability Dependent",
        "80DDB": "Specified Disease",
        "80E": "Education Loan Interest",
        "80EE": "Home Loan Interest",
        "80EEA": "Affordable Housing",
        "80EEB": "Electric Vehicle Loan",
        "80G": "Donations",
        "80GG": "Rent Paid",
        "80GGA": "Scientific Research Donation",
        "80GGC": "Political Donation",
        "80TTA": "Savings Interest",
        "80TTB": "Senior Citizen Interest",
        "80U": "Disability",
        "other": "Other Deductions",
        "C1": "Total Deductions",
        "C2": "Total Income",
        "C3": {
            "LTCG_112A": "Long Term Capital Gains details",
        },
    },
    "PART_D_TAX_COMPUTATION": {
        "D1": "Tax on Total Income",
        "D2": "Rebate u/s 87A",
        "D3": "Tax after Rebate",
        "D4": "Cess",
        "D5": "Total Tax",
        "D6": "Relief u/s 89",
        "D7": "Interest 234A",
        "D8": "Interest 234B",
        "D9": "Interest 234C",
        "D10": "Fee 234F",
        "D10a": "Revised Return Fee",
        "D11": "Total Tax Liability",
        "D12": "Taxes Paid",
        "D13": "Amount Payable",
        "D14": "Refund",
    },
    "PART_E_OTHER_INFORMATION": {
        "bank_details": {
            "IFS": "IFSC Code",
            "bank_name": "Bank Name",
            "account_number": "Account Number",
            "account_type": "Account Type",
            "refund_flag": "Selected for Refund",
        },
    },
    "SCHEDULE_IT": {
        "BSR": "Bank Code",
        "date": "Date of Deposit",
        "challan_no": "Challan Number",
        "tax_paid": "Tax Paid",
    },
    "SCHEDULE_TDS": {
        "TAN": "Deductor TAN",
        "name": "Deductor Name",
        "section": "Section",
        "amount": "Amount Paid",
        "year": "Year",
        "tax": "Tax Deducted",
        "credit": "Credit Claimed",
    },
    "VERIFICATION": {
        "name": "Declarant Name",
        "capacity": "Filing Capacity",
        "date": "Date",
        "signature": "Signature",
        "trp_id": "TRP ID",
        "trp_name": "TRP Name",
    },
}

_FIELD_CODE_PATTERN = re.compile(r"^(?:[A-Z]{1,6}\d+[A-Za-z0-9]*|[A-Z]{2,6}|80[A-Z0-9]+|\d{1,3}[A-Za-z]{0,5}\d*[A-Za-z0-9]*)$")


def _looks_like_short_code(value: str) -> bool:
    return bool(_FIELD_CODE_PATTERN.match(value))


def flatten_itr1_template(schema: dict[str, Any] | None = None) -> list[dict[str, Any]]:
    template = schema or ITR1_TEMPLATE_SCHEMA
    fields: list[dict[str, Any]] = []
    used_ids: dict[str, int] = {}

    def allocate_field_id(path: list[str], key: str) -> str:
        candidate = key if _looks_like_short_code(key) else ".".join(path + [key])
        seen = used_ids.get(candidate, 0)
        used_ids[candidate] = seen + 1
        if seen == 0:
            return candidate
        return f"{candidate}.{seen + 1}"

    def walk(node: Any, path: list[str], section: str) -> None:
        if not isinstance(node, dict):
            return

        for key, value in node.items():
            if isinstance(value, dict):
                walk(value, path + [key], section)
                continue

            if not isinstance(value, str):
                continue

            field_id = allocate_field_id(path, key)
            fields.append(
                {
                    "field_id": field_id,
                    "field_name": value,
                    "value": None,
                    "status": "pending",
                    "source": "template",
                    "section": section,
                    "path": ".".join(path + [key]),
                    "required": True,
                    "prompt": f"Please provide {value}",
                }
            )

    for section, content in template.items():
        if isinstance(content, dict):
            walk(content, [section], section)

    return fields


def itr1_template_fields() -> list[dict[str, Any]]:
    return deepcopy(flatten_itr1_template())
