import pandas as pd
import numpy as np
from prophet import Prophet
from sklearn.ensemble import RandomForestRegressor
from sklearn.metrics import (
    mean_absolute_error,
    mean_squared_error,
    r2_score
)

# =====================================
# MAPE
# =====================================


def mape(y_true, y_pred):
    y_true = np.array(y_true)
    y_pred = np.array(y_pred)

    mask = y_true != 0

    if mask.sum() == 0:
        return 0

    return np.mean(
        np.abs(
            (y_true[mask] - y_pred[mask]) /
            y_true[mask]
        )
    ) * 100


# =====================================
# Prophet
# =====================================
def train_prophet(df):

    model = Prophet()

    for col in [
        "Is_Weekend",
        "EndOfYear_Promo",
        "On_Promotion"
    ]:
        model.add_regressor(col)

    model.fit(
        df[
            [
                "ds",
                "y",
                "Is_Weekend",
                "EndOfYear_Promo",
                "On_Promotion"
            ]
        ]
    )

    return model


# =====================================
# Random Forest
# =====================================
def train_random_forest(df, prophet_model):

    forecast = prophet_model.predict(
        df[
            [
                "ds",
                "Is_Weekend",
                "EndOfYear_Promo",
                "On_Promotion"
            ]
        ]
    )

    df = df.copy()

    df["prophet_pred"] = forecast["yhat"].values

    df["residual"] = (
        df["y"] -
        df["prophet_pred"]
    )

    feature_cols = [
        "Year",
        "Month",
        "Day",
        "Weekday",
        "Is_Weekend",
        "EndOfYear_Promo",
        "On_Promotion",
        "temperature",
        "price"
    ]

    df = df.dropna(
        subset=feature_cols + ["residual"]
    )

    X = df[feature_cols]
    y = df["residual"]

    rf_model = RandomForestRegressor(
        n_estimators=100,
        random_state=42
    )

    rf_model.fit(X, y)

    return rf_model


# =====================================
# Chargement CSV
# =====================================
CSV_PATH = "data_corrected.csv"

df = pd.read_csv(CSV_PATH)

df["ds"] = pd.to_datetime(df["ds"])

# =====================================
# Valeurs par défaut
# =====================================
if "On_Promotion" not in df.columns:
    df["On_Promotion"] = 0

if "temperature" not in df.columns:
    df["temperature"] = 15

if "price" not in df.columns:
    df["price"] = 3.5

df["On_Promotion"] = df["On_Promotion"].fillna(0)
df["temperature"] = df["temperature"].fillna(15)
df["price"] = df["price"].fillna(3.5)

# =====================================
# Features temporelles
# =====================================
df["Year"] = df["ds"].dt.year
df["Month"] = df["ds"].dt.month
df["Day"] = df["ds"].dt.day
df["Weekday"] = df["ds"].dt.weekday

df["Is_Weekend"] = (
    df["Weekday"]
    .isin([5, 6])
    .astype(int)
)

df["EndOfYear_Promo"] = (
    (
        df["ds"].dt.month == 12
    ) &
    (
        df["ds"].dt.day >= 20
    )
).astype(int)

# =====================================
# Produits
# =====================================
products = df["Product"].unique()

all_results = []

for product in products:

    print("\n" + "=" * 60)
    print("Produit :", product)
    print("=" * 60)

    df_product = (
        df[df["Product"] == product]
        .copy()
        .sort_values("ds")
    )

    # =====================================
    # Train : 2023 + 2024
    # Test : 2025
    # =====================================
    train_df = df_product[
        df_product["ds"] < "2025-01-01"
    ].copy()

    test_df = df_product[
        df_product["ds"] >= "2025-01-01"
    ].copy()

    if len(train_df) == 0:
        print(f"Aucune donnée d'entraînement pour {product}")
        continue

    if len(test_df) == 0:
        print(f"Aucune donnée de test pour {product}")
        continue

    print(
        f"Train : {train_df['ds'].min().date()} -> "
        f"{train_df['ds'].max().date()} "
        f"({len(train_df)} lignes)"
    )

    print(
        f"Test  : {test_df['ds'].min().date()} -> "
        f"{test_df['ds'].max().date()} "
        f"({len(test_df)} lignes)"
    )

    try:

        # =====================
        # Prophet
        # =====================
        prophet_model = train_prophet(
            train_df
        )

        prophet_forecast = prophet_model.predict(
            test_df[
                [
                    "ds",
                    "Is_Weekend",
                    "EndOfYear_Promo",
                    "On_Promotion"
                ]
            ]
        )

        test_df["prophet_pred"] = (
            prophet_forecast["yhat"].values
        )

        # =====================
        # Hybrid
        # =====================
        rf_model = train_random_forest(
            train_df,
            prophet_model
        )

        feature_cols = [
            "Year",
            "Month",
            "Day",
            "Weekday",
            "Is_Weekend",
            "EndOfYear_Promo",
            "On_Promotion",
            "temperature",
            "price"
        ]

        rf_correction = rf_model.predict(
            test_df[feature_cols]
        )

        test_df["hybrid_pred"] = (
            test_df["prophet_pred"] +
            rf_correction
        )

        # =====================
        # Prophet Metrics
        # =====================
        prophet_mae = mean_absolute_error(
            test_df["y"],
            test_df["prophet_pred"]
        )

        prophet_rmse = np.sqrt(
            mean_squared_error(
                test_df["y"],
                test_df["prophet_pred"]
            )
        )

        prophet_r2 = r2_score(
            test_df["y"],
            test_df["prophet_pred"]
        )

        prophet_mape = mape(
            test_df["y"],
            test_df["prophet_pred"]
        )

        # =====================
        # Hybrid Metrics
        # =====================
        hybrid_mae = mean_absolute_error(
            test_df["y"],
            test_df["hybrid_pred"]
        )

        hybrid_rmse = np.sqrt(
            mean_squared_error(
                test_df["y"],
                test_df["hybrid_pred"]
            )
        )

        hybrid_r2 = r2_score(
            test_df["y"],
            test_df["hybrid_pred"]
        )

        hybrid_mape = mape(
            test_df["y"],
            test_df["hybrid_pred"]
        )

        print("\nPROPHET")
        print(f"MAE  : {prophet_mae:.2f}")
        print(f"RMSE : {prophet_rmse:.2f}")
        print(f"MAPE : {prophet_mape:.2f}%")
        print(f"R²   : {prophet_r2:.4f}")

        print("\nHYBRID")
        print(f"MAE  : {hybrid_mae:.2f}")
        print(f"RMSE : {hybrid_rmse:.2f}")
        print(f"MAPE : {hybrid_mape:.2f}%")
        print(f"R²   : {hybrid_r2:.4f}")

        all_results.append({
            "Product": product,
            "Prophet_MAE": prophet_mae,
            "Hybrid_MAE": hybrid_mae,
            "Prophet_RMSE": prophet_rmse,
            "Hybrid_RMSE": hybrid_rmse,
            "Prophet_MAPE": prophet_mape,
            "Hybrid_MAPE": hybrid_mape,
            "Prophet_R2": prophet_r2,
            "Hybrid_R2": hybrid_r2
        })

    except Exception as e:
        print(f"Erreur pour {product} : {e}")

# =====================================
# Résumé final
# =====================================
summary = pd.DataFrame(all_results)

print("\n")
print("=" * 60)
print("RÉSUMÉ GLOBAL")
print("=" * 60)

print(summary)

summary.to_csv(
    "evaluation_results.csv",
    index=False
)

print("\nRésultats enregistrés dans evaluation_results.csv")
