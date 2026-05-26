from abc import ABC, abstractmethod
from typing import List
from src.domain.model.bill import Bill

class ParserPort(ABC):
    @abstractmethod
    def parse(self, file_path: str) -> List[Bill]: pass