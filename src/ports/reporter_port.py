from abc import ABC, abstractmethod
from typing import List
from src.domain.model.bill import Bill

class ReporterPort(ABC):
    @abstractmethod
    def log(self, message: str, level: str = "info"): pass
    @abstractmethod
    def report_file_summary(self, filename: str, bills: List[Bill], anomalies: List): pass
    @abstractmethod
    def report_final_summary(self, stats: dict): pass