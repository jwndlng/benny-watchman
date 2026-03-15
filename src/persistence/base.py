"""Abstract persistence backend interface."""

from abc import ABC, abstractmethod
from src.schemas.investigation import Investigation


class PersistenceBackend(ABC):
    @abstractmethod
    def save(self, investigation: Investigation) -> None:
        pass

    @abstractmethod
    def get(self, investigation_id: str) -> Investigation | None:
        pass

    @abstractmethod
    def list(self) -> list[Investigation]:
        pass
