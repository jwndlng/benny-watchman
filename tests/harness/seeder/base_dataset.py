"""Abstract base class for dataset loaders."""

from abc import ABC, abstractmethod


class BaseDataset(ABC):
    @abstractmethod
    def load(self, db_path: str) -> None:
        """Populate the SQLite database at db_path with data."""
