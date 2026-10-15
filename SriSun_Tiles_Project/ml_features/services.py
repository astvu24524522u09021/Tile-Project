from pathlib import Path

import joblib
import pandas as pd
from django.db.models import IntegerField, OuterRef, Subquery, Sum, Value
from django.db.models.functions import Coalesce
from sklearn.ensemble import RandomForestRegressor
from sklearn.metrics import mean_squared_error, r2_score
from sklearn.model_selection import train_test_split

from inventory.models import InventoryStock, StockTransaction
from tiles.models import Tile

MODEL_PATH = Path(__file__).resolve().parent / 'models' / 'demand_model.joblib'
FEATURE_COLUMNS = ['current_stock', 'price', 'incoming_qty', 'outgoing_qty']
_CACHED_MODEL = None
_CACHED_MODEL_MTIME_NS = None


def load_saved_model():
    global _CACHED_MODEL, _CACHED_MODEL_MTIME_NS

    try:
        model_mtime_ns = MODEL_PATH.stat().st_mtime_ns
    except OSError:
        return None

    if _CACHED_MODEL is None or model_mtime_ns != _CACHED_MODEL_MTIME_NS:
        try:
            model = joblib.load(MODEL_PATH)
        except Exception:
            return None
        _CACHED_MODEL = model
        _CACHED_MODEL_MTIME_NS = model_mtime_ns
    return _CACHED_MODEL


def _build_dataset():
    stock_totals = InventoryStock.objects.filter(tile_id=OuterRef('pk')).order_by().values('tile_id').annotate(
        total=Sum('quantity'),
    ).values('total')
    incoming_totals = StockTransaction.objects.filter(
        tile_id=OuterRef('pk'),
        transaction_type__in=['ADD', 'TRANSFER_IN'],
    ).order_by().values('tile_id').annotate(total=Sum('quantity')).values('total')
    outgoing_totals = StockTransaction.objects.filter(
        tile_id=OuterRef('pk'),
        transaction_type__in=['REMOVE', 'TRANSFER_OUT'],
    ).order_by().values('tile_id').annotate(total=Sum('quantity')).values('total')

    rows = Tile.objects.order_by('model_id').annotate(
        current_stock=Coalesce(Subquery(stock_totals, output_field=IntegerField()), Value(0)),
        incoming_qty=Coalesce(Subquery(incoming_totals, output_field=IntegerField()), Value(0)),
        outgoing_qty=Coalesce(Subquery(outgoing_totals, output_field=IntegerField()), Value(0)),
    ).values(
        'id', 'model_id', 'name', 'current_stock', 'price', 'incoming_qty', 'outgoing_qty',
    )
    dataset = pd.DataFrame.from_records(rows)
    if dataset.empty:
        return pd.DataFrame(columns=[
            'tile_id', 'model_id', 'name', 'current_stock', 'price',
            'incoming_qty', 'outgoing_qty', 'demand_score',
        ])

    dataset = dataset.rename(columns={'id': 'tile_id'})
    dataset['demand_score'] = dataset['incoming_qty'] + dataset['outgoing_qty'].clip(lower=0)
    return dataset


def train_and_save_model():
    global _CACHED_MODEL, _CACHED_MODEL_MTIME_NS

    df = _build_dataset()
    if df.empty or len(df) < 2:
        return {
            'status': 'not enough data',
            'message': 'Not enough inventory data is available to train the model yet.',
            'predictions': [],
            'metrics': {'mse': None, 'r2': None},
        }

    target = 'demand_score'
    X = df[FEATURE_COLUMNS]
    y = df[target]

    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.25, random_state=42)
    model = RandomForestRegressor(n_estimators=200, random_state=42)
    model.fit(X_train, y_train)
    predictions = model.predict(X_test)

    mse = mean_squared_error(y_test, predictions)
    r2 = r2_score(y_test, predictions)

    MODEL_PATH.parent.mkdir(parents=True, exist_ok=True)
    joblib.dump(model, MODEL_PATH)
    _CACHED_MODEL = model
    _CACHED_MODEL_MTIME_NS = MODEL_PATH.stat().st_mtime_ns

    summary = []
    for _, row in df.iterrows():
        current = row['current_stock']
        price = row['price']
        incoming = row['incoming_qty']
        outgoing = row['outgoing_qty']
        prediction_row = pd.DataFrame(
            [[current, price, incoming, outgoing]],
            columns=FEATURE_COLUMNS,
        )
        pred = model.predict(prediction_row)[0]
        summary.append({
            'model_id': row['model_id'],
            'current_stock': int(current),
            'incoming_qty': int(incoming),
            'outgoing_qty': int(outgoing),
            'predicted_demand': round(float(pred), 2),
        })

    summary.sort(key=lambda x: x['predicted_demand'], reverse=True)
    return {
        'status': 'trained',
        'message': 'Demand forecasting model has been trained successfully.',
        'predictions': summary[:10],
        'metrics': {'mse': round(float(mse), 2), 'r2': round(float(r2), 4)},
    }


def predict_tile_demand(tile):
    model = load_saved_model()
    if model is None:
        train_and_save_model()
        model = load_saved_model()
    if model is None:
        return {'model_id': tile.model_id, 'predicted_demand': 0}
    df = _build_dataset()
    row = df[df['model_id'] == tile.model_id]
    if row.empty:
        return {'model_id': tile.model_id, 'predicted_demand': 0}

    feature_row = row.iloc[0]
    prediction_row = pd.DataFrame(
        [[feature_row['current_stock'], float(tile.price), feature_row['incoming_qty'], feature_row['outgoing_qty']]],
        columns=FEATURE_COLUMNS,
    )
    prediction = model.predict(prediction_row)[0]
    return {
        'model_id': tile.model_id,
        'tile_name': tile.name,
        'current_stock': int(feature_row['current_stock']),
        'predicted_demand': round(float(prediction), 2),
    }


def get_prediction_summary():
    model = load_saved_model()
    if model is None:
        return train_and_save_model()

    df = _build_dataset()
    if df.empty:
        return {'status': 'not enough data', 'message': 'No data available for prediction.', 'predictions': [], 'metrics': {'mse': None, 'r2': None}}

    df['predicted_demand'] = model.predict(df[FEATURE_COLUMNS])
    top_predictions = df.nlargest(10, 'predicted_demand')
    predictions = [
        {
            'model_id': row.model_id,
            'tile_name': row.name,
            'current_stock': int(row.current_stock),
            'predicted_demand': round(float(row.predicted_demand), 2),
        }
        for row in top_predictions.itertuples(index=False)
    ]
    return {
        'status': 'ready',
        'message': 'Forecast data loaded successfully.',
        'predictions': predictions[:10],
        'metrics': {'mse': None, 'r2': None},
    }


def get_model_status():
    if load_saved_model() is None:
        return {
            'status': 'unavailable',
            'message': 'No saved demand forecasting model is available.',
            'metrics': {'mse': None, 'r2': None},
        }
    return {
        'status': 'ready',
        'message': 'The saved demand forecasting model is ready.',
        'metrics': {'mse': None, 'r2': None},
    }
