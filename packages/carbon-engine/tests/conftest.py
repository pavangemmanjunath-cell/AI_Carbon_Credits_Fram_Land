from __future__ import annotations

import pytest

from carbon_engine import ParameterStore, TreeBiomassModel


@pytest.fixture(scope="session")
def store() -> ParameterStore:
    return ParameterStore()


@pytest.fixture(scope="session")
def model(store: ParameterStore) -> TreeBiomassModel:
    return TreeBiomassModel(store)
