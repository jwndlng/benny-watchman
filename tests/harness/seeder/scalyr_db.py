"""Scalyr dataset loader — stub, not yet implemented."""

from tests.harness.seeder.base_dataset import BaseDataset


class ScalyrDataset(BaseDataset):
    def __init__(self, data_path: str) -> None:
        self._data_path = data_path

    def load(self, db_path: str) -> None:
        raise NotImplementedError(
            "Scalyr loader not yet implemented. "
            "Place Scalyr log files in tests/harness/data/scalyr/ and implement this loader."
        )
