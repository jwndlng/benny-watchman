"""Abstract persistence backend interface."""

from abc import ABC, abstractmethod
from src.schemas.incident_report import IncidentReport


class PersistenceBackend(ABC):

    @abstractmethod
    def save(self, report: IncidentReport) -> None:
        pass

    @abstractmethod
    def get(self, alert_id: str) -> IncidentReport | None:
        pass

    @abstractmethod
    def list(self) -> list[IncidentReport]:
        pass
