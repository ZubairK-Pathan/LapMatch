from pathlib import Path

import pandas as pd

from models.topsis import apply_topsis, calculate_weights

DATA_PATH = Path(__file__).resolve().parent.parent / "data" / "lapmatch_clean_data.csv"
LAPTOPS_DF = pd.read_csv(DATA_PATH)

def run_lapmatch(budget: float, q_perf: str, q_port: str, q_batt: str, flex: float = 0.3) -> pd.DataFrame:
    df = LAPTOPS_DF.copy()

    lower_bound = budget * (1 - flex)

    df_filtered = df[(df["price"] >= lower_bound) & (df["price"] <= budget)].copy()

    if len(df_filtered) == 0:
        df_filtered = df[df["price"] <= budget].copy()

    if len(df_filtered) == 0:
        return pd.DataFrame()

    df_filtered["price_diff"] = abs(df_filtered["price"] - budget)

    # if only 1 laptop is found, we don't need TOPSIS distance.
    if len(df_filtered) == 1:
        df_filtered["Match_Score"] = 1.0
        return df_filtered.head(1)

    weights = calculate_weights(q_perf, q_port, q_batt)
    ranked = apply_topsis(df_filtered, weights)

    return ranked.head(3)


if __name__ == "__main__":
    result = run_lapmatch(120000, "B", "B", "B")

    print(result[["name", "price", "Match_Score"]])
