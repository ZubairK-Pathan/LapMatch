import numpy as np
import pandas as pd

from models.topsis import apply_topsis, calculate_weights


def test_calculate_weights():
    # 'A' = 1.0, 'B' = 3.0, 'C' = 5.0. Price = 2.0.
    # For A, A, A: raw weights [2.0, 1.0, 1.0, 1.0], sum = 5.0.
    # Normalized: [0.4, 0.2, 0.2, 0.2]
    w = calculate_weights("A", "A", "A")
    assert np.allclose(w, np.array([0.4, 0.2, 0.2, 0.2]))

    # For C, B, A: raw weights [2.0, 5.0, 3.0, 1.0], sum = 11.0.
    # Normalized: [2/11, 5/11, 3/11, 1/11]
    w2 = calculate_weights("c", "b", "a")
    assert np.allclose(w2, np.array([2 / 11, 5 / 11, 3 / 11, 1 / 11]))


def test_apply_topsis():
    # Columns required for TOPSIS:
    # price_diff (minimize), Performance_1_to_10 (maximize), Weight_Proxy (minimize), Battery_Proxy (maximize)
    data = {
        "name": ["Laptop Best", "Laptop Mid", "Laptop Worst"],
        "price_diff": [10.0, 50.0, 100.0],
        "Performance_1_to_10": [9.0, 6.0, 3.0],
        "Weight_Proxy": [1.2, 2.0, 2.8],
        "Battery_Proxy": [10.0, 6.0, 3.0],
    }
    df = pd.DataFrame(data)
    weights = np.array([0.25, 0.25, 0.25, 0.25])

    result = apply_topsis(df, weights)

    assert "Match_Score" in result.columns
    # The Best laptop has the best scores across all attributes, so it should rank first
    assert result.iloc[0]["name"] == "Laptop Best"
    assert result.iloc[2]["name"] == "Laptop Worst"
    assert all(0.0 <= score <= 1.0 for score in result["Match_Score"])
