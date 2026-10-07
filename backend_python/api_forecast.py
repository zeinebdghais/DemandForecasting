import pandas as pd
from flask import Flask, request, jsonify
from datetime import datetime, timedelta
import io
from flask_cors import CORS
from prophet import Prophet
from sklearn.ensemble import RandomForestRegressor
from waitress import serve

app = Flask(__name__)
CORS(app)


def train_prophet(df):
    model = Prophet()
    for col in ["Is_Weekend", "EndOfYear_Promo", "On_Promotion"]:
        if col in df.columns:
            model.add_regressor(col)

    model.fit(df[["ds", "y", "Is_Weekend", "EndOfYear_Promo", "On_Promotion"]])
    return model


def train_random_forest(df, prophet_model):

    forecast = prophet_model.predict(
        df[["ds", "Is_Weekend", "EndOfYear_Promo", "On_Promotion"]]
    )
    df["prophet_pred"] = forecast["yhat"].values

    df["residual"] = df["y"] - df["prophet_pred"]

    feature_cols = ["Year", "Month", "Day", "Weekday", "Is_Weekend",
                    "EndOfYear_Promo", "On_Promotion", "temperature", "price"]

    X = df[feature_cols]
    y = df["residual"]

    rf_model = RandomForestRegressor(n_estimators=100, random_state=42)
    rf_model.fit(X, y)

    return rf_model


@app.route("/predict", methods=["POST"])
def predict():
    try:
        data = request.get_json()
        csv_content = data.get("csv_data")
        start_date_str = data.get("start_date")
        end_date_str = data.get("end_date")
        selected_products = data.get("products")

        if not csv_content:
            return jsonify({"error": "csv_data is required"}), 400
        if not start_date_str or not end_date_str:
            return jsonify({"error": "start_date and end_date are required"}), 400

        df = pd.read_csv(io.StringIO(csv_content))

        if not {"ds", "y", "Product"}.issubset(df.columns):
            return jsonify({"error": "CSV must contain 'Product', 'ds', and 'y' columns"}), 400

        df["ds"] = pd.to_datetime(df["ds"])
        products = df["Product"].unique()

        if selected_products:
            products = [p for p in products if p in selected_products]

        start_date = datetime.strptime(start_date_str, "%Y-%m-%d")
        end_date = datetime.strptime(end_date_str, "%Y-%m-%d")
        if start_date > end_date:
            return jsonify({"error": "start_date cannot be after end_date"}), 400

        all_results = {}

        for product in products:
            df_product = df[df["Product"] == product].copy()
            if df_product.empty:
                continue

            df_product["Year"] = df_product["ds"].dt.year
            df_product["Month"] = df_product["ds"].dt.month
            df_product["Day"] = df_product["ds"].dt.day
            df_product["Weekday"] = df_product["ds"].dt.weekday
            df_product["Is_Weekend"] = df_product["Weekday"].apply(
                lambda x: 1 if x in [5, 6] else 0)
            df_product["EndOfYear_Promo"] = df_product["ds"].apply(
                lambda x: 1 if (x.month == 12 and x.day >= 20) else 0)
            df_product["On_Promotion"] = df_product.get("On_Promotion", 0)
            df_product["temperature"] = df_product.get("temperature", 15)
            df_product["price"] = df_product.get("price", 3.5)

            prophet_model = train_prophet(df_product)
            rf_model = train_random_forest(df_product, prophet_model)

            results = []
            current_date = start_date
            while current_date <= end_date:
                same_day = df_product[
                    (df_product["Month"] == current_date.month) &
                    (df_product["Day"] == current_date.day)
                ]

                if not same_day.empty:
                    ref_row = same_day.iloc[-1]
                    features = {
                        "Year": current_date.year,
                        "Month": current_date.month,
                        "Day": current_date.day,
                        "Weekday": current_date.weekday(),
                        "Is_Weekend": 1 if current_date.weekday() in [5, 6] else 0,
                        "EndOfYear_Promo": 1 if (current_date.month == 12 and current_date.day >= 20) else 0,
                        "On_Promotion": ref_row["On_Promotion"],
                        "temperature": ref_row["temperature"],
                        "price": ref_row["price"]
                    }
                else:
                    
                    features = {
                        "Year": current_date.year,
                        "Month": current_date.month,
                        "Day": current_date.day,
                        "Weekday": current_date.weekday(),
                        "Is_Weekend": 1 if current_date.weekday() in [5, 6] else 0,
                        "EndOfYear_Promo": 1 if (current_date.month == 12 and current_date.day >= 20) else 0,
                        "On_Promotion": df_product["On_Promotion"].mean(),
                        "temperature": df_product["temperature"].mean(),
                        "price": df_product["price"].mean()
                    }

                future_df = pd.DataFrame({
                    "ds": [current_date],
                    "Is_Weekend": [features["Is_Weekend"]],
                    "EndOfYear_Promo": [features["EndOfYear_Promo"]],
                    "On_Promotion": [features["On_Promotion"]]
                })
                prophet_pred = prophet_model.predict(future_df)["yhat"].iloc[0]

                rf_correction = rf_model.predict(pd.DataFrame([features]))[0]

                final_pred = prophet_pred + rf_correction

                results.append({
                    "ds": current_date.strftime("%Y-%m-%d"),
                    "Prophet_Pred": round(float(prophet_pred), 2),
                    "RF_Correction": round(float(rf_correction), 2),
                    "Final_Hybrid": round(int(final_pred))
                })

                current_date += timedelta(days=1)

            all_results[product] = results

        return jsonify(all_results)

    except Exception as e:
        return jsonify({"error": str(e)}), 500


if __name__ == "__main__":
    serve(app, host="0.0.0.0", port=5000)
