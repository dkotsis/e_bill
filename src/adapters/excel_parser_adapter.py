# src/adapters/excel_parser_adapter.py
from typing import List
from src.ports.parser_port import ParserPort
from src.domain.model.bill import Bill
from src.parsers_excel import extract_invoices
from datetime import datetime


class ExcelParserAdapter(ParserPort):
    def parse(self, file_path: str) -> List[Bill]:
        raw_bills = extract_invoices(file_path)
        domain_bills = []

        # print(f"DEBUG PARSER: Loaded {len(raw_bills)} raw bills from {file_path}")

        for i, old in enumerate(raw_bills):
            p_start = getattr(old, 'period_start', None)
            p_end = getattr(old, 'period_end', None)

            # print(f"DEBUG RAW BILL {i}: period_start={p_start} ({type(p_start)}), period_end={p_end} ({type(p_end)})")

            # Aggressive date fixing
            if isinstance(p_start, str):
                for fmt in ("%d/%m/%Y", "%Y-%m-%d", "%d-%m-%Y"):
                    try:
                        p_start = datetime.strptime(p_start, fmt)
                        break
                    except:
                        continue
            if isinstance(p_end, str):
                for fmt in ("%d/%m/%Y", "%Y-%m-%d", "%d-%m-%Y"):
                    try:
                        p_end = datetime.strptime(p_end, fmt)
                        break
                    except:
                        continue

            domain_bill = Bill(
                supply_number=str(getattr(old, 'supply_number', "")),
                provider=str(getattr(old, 'provider', "")),
                bill_number=str(getattr(old, 'bill_number', "")),
                issue_date=getattr(old, 'issue_date', None),
                period_start=p_start,
                period_end=p_end,
                consumption=float(getattr(old, 'consumption', 0.0)),
                compet_charge=float(getattr(old, 'compet_charge', 0.0)),
                regul_charge=float(getattr(old, 'regul_charge', 0.0)),
                bill_type=str(getattr(old, 'bill_type', "")),
                bill_hash=str(getattr(old, 'bill_hash', "")),
            )

            domain_bills.append(domain_bill)

        return domain_bills