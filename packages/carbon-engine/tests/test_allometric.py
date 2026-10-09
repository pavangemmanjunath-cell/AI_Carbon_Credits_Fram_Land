from __future__ import annotations

import math

import pytest

from carbon_engine.equations import chave_2014_agb_kg, chave_2014_no_height_agb_kg
from carbon_engine.errors import ModelInputError


@pytest.mark.parametrize(
    "rho, dbh, height, expected",
    [
        # hand-computed: 0.0673 * (rho * D^2 * H) ** 0.976
        (0.55, 20.0, 10.0, 123.089),
        (0.60, 25.0, 12.0, 247.486),
        (0.80, 15.0, 5.0, 51.446),
    ],
)
def test_chave_2014_with_height_matches_hand_values(rho, dbh, height, expected):
    assert chave_2014_agb_kg(rho, dbh, height) == pytest.approx(expected, abs=0.01)


def test_chave_2014_is_monotonic_in_dbh_and_height():
    base = chave_2014_agb_kg(0.55, 20.0, 10.0)
    assert chave_2014_agb_kg(0.55, 21.0, 10.0) > base
    assert chave_2014_agb_kg(0.55, 20.0, 11.0) > base
    assert chave_2014_agb_kg(0.60, 20.0, 10.0) > base


def test_chave_2014_zero_tree_is_zero_and_bad_inputs_raise():
    assert chave_2014_agb_kg(0.55, 0.0, 10.0) == 0.0
    with pytest.raises(ModelInputError):
        chave_2014_agb_kg(0.0, 20.0, 10.0)
    with pytest.raises(ModelInputError):
        chave_2014_agb_kg(0.55, -1.0, 10.0)


def test_chave_2014_no_height_form():
    # exp(-1.803 - 0.976*E + 0.976*ln(rho) + 2.673*ln(D) - 0.0299*ln(D)^2)
    rho, dbh, e = 0.55, 20.0, 0.1
    ln_d = math.log(dbh)
    expected = math.exp(
        -1.803 - 0.976 * e + 0.976 * math.log(rho) + 2.673 * ln_d - 0.0299 * ln_d**2
    )
    assert chave_2014_no_height_agb_kg(rho, dbh, e) == pytest.approx(expected)
