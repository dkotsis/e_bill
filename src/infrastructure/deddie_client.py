# src/infrastructure/deddie_client.py
import requests
from datetime import datetime

class DeddieApiClient:
    def __init__(self, tax_number: str):
        self.tax_number = tax_number
        # Target endpoint extracted from your operational telemetry metrics
        self.api_url = "https://wsmetering.deddie.gr/api/v1/curves" 

    def fetch_consumption_profile(self, supply_number: str, start_date: str, end_date: str) -> list:
        payload = {
            "taxNumber": self.tax_number,
            "supplyNumber": supply_number,
            "fromDate": start_date, # Format: YYYY-MM-DD
            "toDate": end_date,
            "analysisType": "DAILY", # Can be HOURLY if supported by meter type
            "confirmedDataOnly": "True"
        }
        
        try:
            response = requests.post(self.api_url, json=payload, timeout=15)
            if response.status_code == 200:
                data = response.json()
                # Returns the exact array mapped in your VBA loop: c("consumption"), c("meterDate")
                return data.get("curves", []) 
            return []
        except Exception:
            return []