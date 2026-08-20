import pandas as pd

def score_trust(df: pd.DataFrame) -> pd.DataFrame:
    df = df.sort_values("date").copy()
    df["roc"] = df["water_level_m"].diff().abs()
    roc_mean = df["roc"].mean()
    roc_std = df["roc"].std() + 1e-6
    roc_z = (df["roc"] - roc_mean) / roc_std
    df["trust_score"] = (100 - (roc_z.clip(lower=0) * 15)).clip(0, 100)
    df["trust_score"] = df["trust_score"].fillna(90)
    df["status"] = pd.cut(
        df["trust_score"],
        bins=[-1, 40, 70, 101],
        labels=["PROBABLE SENSOR FAULT", "SUSPICIOUS", "TRUSTED"]
    ).astype(str)
    return df