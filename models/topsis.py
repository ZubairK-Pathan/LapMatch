import numpy as np
import pandas as pd


def calculate_weights(q_perf: str, q_port: str, q_batt: str) -> np.ndarray:
    """
    Normalizes the user's categorical intent (A, B, C) into a mathematical weight array.
    Price is heavily weighted (2.0) by default to strictly respect budgets.
    """
    intent_map = {"A": 1.0, "B": 3.0, "C": 5.0}

    perf_w = intent_map.get(q_perf.upper(), 1.0)
    port_w = intent_map.get(q_port.upper(), 1.0)
    batt_w = intent_map.get(q_batt.upper(), 1.0)

    price_w = 2.0

    raw_weights = np.array([price_w, perf_w, port_w, batt_w])

    return raw_weights / np.sum(raw_weights)


def apply_topsis(df: pd.DataFrame, weights: np.ndarray) -> pd.DataFrame:
    """
    Executes the Technique for Order of Preference by Similarity to Ideal Solution (TOPSIS)
    against the filtered dataframe to rank the optimal laptops.
    """
    criteria_cols = [
        "price_diff",  # minimize
        "Performance_1_to_10",  # maximize
        "Weight_Proxy",  # minimize
        "Battery_Proxy",  # maximize
    ]

    df_clean = df.dropna(subset=criteria_cols).copy()
    matrix = df_clean[criteria_cols].values.astype(float)

    # Step 1: Normalize Matrix (Added 1e-9 epsilon for numerical stability to prevent division by zero)
    norm_matrix = matrix / (np.sqrt((matrix**2).sum(axis=0)) + 1e-9)

    # Step 2: Apply Weights
    weighted_matrix = norm_matrix * weights

    # Step 3: Determine Ideal Solutions (Best / Worst capabilities)
    ideal_best = np.array(
        [
            np.min(weighted_matrix[:, 0]),  # price_diff (min)
            np.max(weighted_matrix[:, 1]),  # performance (max)
            np.min(weighted_matrix[:, 2]),  # weight (min)
            np.max(weighted_matrix[:, 3]),  # battery (max)
        ]
    )

    ideal_worst = np.array(
        [
            np.max(weighted_matrix[:, 0]),
            np.min(weighted_matrix[:, 1]),
            np.max(weighted_matrix[:, 2]),
            np.min(weighted_matrix[:, 3]),
        ]
    )

    # Step 4: Calculate Euclidean distances from the ideal solutions
    dist_best = np.sqrt(((weighted_matrix - ideal_best) ** 2).sum(axis=1))
    dist_worst = np.sqrt(((weighted_matrix - ideal_worst) ** 2).sum(axis=1))

    # Step 5: Compute the Relative Closeness / Match Score
    topsis_scores = dist_worst / (dist_best + dist_worst + 1e-9)

    result_df = df_clean.copy()
    result_df["Match_Score"] = topsis_scores

    return result_df.sort_values(by="Match_Score", ascending=False)
