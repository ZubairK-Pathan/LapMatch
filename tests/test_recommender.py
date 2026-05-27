from unittest.mock import patch

import pandas as pd

from models.recommender import run_lapmatch


@patch("models.recommender.pd.read_csv")
def test_run_lapmatch_empty(mock_read_csv):
    # Test case where no laptops fall under budget
    mock_df = pd.DataFrame(
        {
            "name": ["Premium UltraBook"],
            "price": [150000],
            "Performance_1_to_10": [8.0],
            "Weight_Proxy": [1.2],
            "Battery_Proxy": [8.0],
        }
    )
    mock_read_csv.return_value = mock_df

    # Budget of 50000 is too low to match the 150000 laptop
    result = run_lapmatch(50000, "B", "B", "B")
    assert result.empty


@patch("models.recommender.pd.read_csv")
def test_run_lapmatch_single_match(mock_read_csv):
    # Test case where exactly 1 laptop fits under budget
    mock_df = pd.DataFrame(
        {
            "name": ["Budget Book", "Expensive Book"],
            "price": [40000, 120000],
            "Performance_1_to_10": [4.0, 9.0],
            "Weight_Proxy": [2.2, 1.3],
            "Battery_Proxy": [4.0, 9.0],
        }
    )
    mock_read_csv.return_value = mock_df

    # Only "Budget Book" is <= 50000.
    result = run_lapmatch(50000, "B", "B", "B")
    assert len(result) == 1
    assert result.iloc[0]["name"] == "Budget Book"
    assert result.iloc[0]["Match_Score"] == 1.0


@patch("models.recommender.pd.read_csv")
def test_run_lapmatch_multiple_matches(mock_read_csv):
    # Test case where multiple laptops match and TOPSIS ranking is applied
    mock_df = pd.DataFrame(
        {
            "name": ["Lap A", "Lap B", "Lap C", "Lap D"],
            "price": [40000, 45000, 48000, 50000],
            "Performance_1_to_10": [5.0, 6.0, 7.0, 8.0],
            "Weight_Proxy": [2.0, 1.8, 1.6, 1.4],
            "Battery_Proxy": [4.0, 5.0, 6.0, 7.0],
        }
    )
    mock_read_csv.return_value = mock_df

    # Budget 55000: all match, should return at most 3 sorted by Match_Score
    result = run_lapmatch(55000, "C", "C", "C")
    assert len(result) == 3
    scores = result["Match_Score"].tolist()
    assert scores == sorted(scores, reverse=True)
