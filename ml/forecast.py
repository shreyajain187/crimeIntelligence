"""
Crime-volume forecasting.

Chosen approach: XGBoost regression over lag/rolling/calendar features,
rather than Prophet. Prophet requires a compiled Stan (cmdstan) backend which
is a common source of environment-specific breakage (native compilation,
long first-run downloads) - exactly the kind of unreliability the brief asks
us to avoid ("Use Prophet or XGBoost depending on reliability/environment").
XGBoost has no such runtime dependency and produces comparable short/medium
horizon forecasts for aggregate daily counts.

The model is trained to forecast *daily total incident counts* (optionally
filtered to a district and/or crime_group), using:
  - lag features (t-1, t-7, t-14, t-28)
  - rolling mean/std (7-day, 28-day)
  - calendar features (day of week, month, is_weekend)

Forecast uncertainty is estimated via the residual standard deviation of the
model on a held-out validation tail, giving an approximate (not exact)
uncertainty interval - documented as such rather than presented as a formal
prediction interval.
"""
from dataclasses import dataclass
import numpy as np
import pandas as pd
from sklearn.metrics import mean_absolute_error, mean_squared_error
import xgboost as xgb

LAGS = [1, 7, 14, 28]
ROLLING_WINDOWS = [7, 28]
VALIDATION_DAYS = 60


@dataclass
class ForecastResult:
    history: pd.DataFrame        # date, actual
    forecast: pd.DataFrame       # date, forecast, lower, upper
    mae: float
    rmse: float
    horizon_days: int


def _build_daily_series(df: pd.DataFrame, district: str | None = None,
                         crime_group: str | None = None) -> pd.Series:
    sub = df
    if district:
        sub = sub[sub["district"].astype(str) == district]
    if crime_group:
        sub = sub[sub["crime_group"].astype(str) == crime_group]
    daily = sub.groupby(sub["timestamp"].dt.floor("D")).size()
    full_idx = pd.date_range(daily.index.min(), daily.index.max(), freq="D")
    daily = daily.reindex(full_idx, fill_value=0)
    daily.index.name = "date"
    return daily


def _make_supervised(series: pd.Series) -> pd.DataFrame:
    frame = pd.DataFrame({"y": series})
    for lag in LAGS:
        frame[f"lag_{lag}"] = series.shift(lag)
    for w in ROLLING_WINDOWS:
        frame[f"roll_mean_{w}"] = series.shift(1).rolling(w).mean()
        frame[f"roll_std_{w}"] = series.shift(1).rolling(w).std()
    frame["day_of_week"] = frame.index.dayofweek
    frame["month"] = frame.index.month
    frame["is_weekend"] = frame["day_of_week"].isin([5, 6]).astype(int)
    return frame.dropna()


def train_and_forecast(df: pd.DataFrame, horizon_days: int = 30,
                        district: str | None = None,
                        crime_group: str | None = None) -> ForecastResult:
    series = _build_daily_series(df, district=district, crime_group=crime_group)
    if len(series) < (max(LAGS) + max(ROLLING_WINDOWS) + VALIDATION_DAYS + 30):
        raise ValueError("Not enough historical daily data to forecast reliably for this filter.")

    supervised = _make_supervised(series)
    feature_cols = [c for c in supervised.columns if c != "y"]

    train = supervised.iloc[:-VALIDATION_DAYS]
    valid = supervised.iloc[-VALIDATION_DAYS:]

    model = xgb.XGBRegressor(
        n_estimators=200, max_depth=5, learning_rate=0.1,
        subsample=0.8, colsample_bytree=0.8, n_jobs=1, random_state=42,
    )
    model.fit(train[feature_cols], train["y"])

    valid_pred = model.predict(valid[feature_cols])
    mae = float(mean_absolute_error(valid["y"], valid_pred))
    rmse = float(mean_squared_error(valid["y"], valid_pred) ** 0.5)

    # Refit on the FULL series (including the validation tail) for the
    # actual forward forecast, so the deployed forecast uses all real data.
    model_full = xgb.XGBRegressor(
        n_estimators=200, max_depth=5, learning_rate=0.1,
        subsample=0.8, colsample_bytree=0.8, n_jobs=1, random_state=42,
    )
    model_full.fit(supervised[feature_cols], supervised["y"])

    history_series = series.copy()
    future_dates = pd.date_range(series.index.max() + pd.Timedelta(days=1), periods=horizon_days, freq="D")

    working = history_series.copy()
    preds = []
    for date in future_dates:
        temp = pd.concat([working, pd.Series([np.nan], index=[date])])
        row = {}
        for lag in LAGS:
            row[f"lag_{lag}"] = temp.shift(lag).loc[date]
        for w in ROLLING_WINDOWS:
            row[f"roll_mean_{w}"] = temp.shift(1).rolling(w).mean().loc[date]
            row[f"roll_std_{w}"] = temp.shift(1).rolling(w).std().loc[date]
        row["day_of_week"] = date.dayofweek
        row["month"] = date.month
        row["is_weekend"] = int(date.dayofweek in (5, 6))
        X_row = pd.DataFrame([row])[feature_cols]
        pred = max(0.0, float(model_full.predict(X_row)[0]))
        preds.append(pred)
        working.loc[date] = pred  # feed forward for subsequent lags

    forecast_df = pd.DataFrame({
        "date": future_dates,
        "forecast": preds,
        "lower": [max(0.0, p - 1.96 * rmse) for p in preds],
        "upper": [p + 1.96 * rmse for p in preds],
    })

    history_df = history_series.reset_index()
    history_df.columns = ["date", "actual"]

    return ForecastResult(
        history=history_df, forecast=forecast_df,
        mae=mae, rmse=rmse, horizon_days=horizon_days,
    )
