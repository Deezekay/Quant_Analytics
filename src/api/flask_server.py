"""
Flask REST API server for crypto analytics.

Provides endpoints for:
- OHLC data retrieval
- Analytics computation
- Data export
"""

import asyncio
import logging
from datetime import datetime, timedelta
from functools import wraps
from typing import Optional

from flask import Flask, jsonify, request, send_file
from flask_cors import CORS
import io
import csv

from ..config import (
    DATABASE_PATH,
    FLASK_DEBUG,
    DEFAULT_SYMBOL_PAIRS,
)
from ..storage.database import DatabaseManager
from ..analytics.engine import AnalyticsEngine

# Initialize Flask app
app = Flask(__name__)
CORS(app)  # Enable CORS for dashboard

logger = logging.getLogger(__name__)


# ============================================================================
# ASYNC-TO-SYNC WRAPPER
# ============================================================================

def async_to_sync(f):
    """
    Decorator to run async functions in Flask routes.
    
    Creates a new event loop, runs the async function, and returns result.
    """
    @wraps(f)
    def wrapper(*args, **kwargs):
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            return loop.run_until_complete(f(*args, **kwargs))
        finally:
            loop.close()
    return wrapper


# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

def serialize_ohlc(bars):
    """Serialize OHLC bars to JSON-compatible format."""
    return [
        {
            "timestamp": bar.timestamp.isoformat(),
            "open": float(bar.open),
            "high": float(bar.high),
            "low": float(bar.low),
            "close": float(bar.close),
            "volume": float(bar.volume),
            "trade_count": bar.trade_count
        }
        for bar in bars
    ]


def serialize_stats(result):
    """Serialize statistics result to JSON."""
    stats = result['stats']
    volume_stats = result['volume_stats']
    
    return {
        "price_stats": {
            "symbol": stats.symbol,
            "interval": stats.interval,
            "window_size": stats.window_size,
            "mean": float(stats.mean),
            "std": float(stats.std),
            "min": float(stats.min),
            "max": float(stats.max),
            "current": float(stats.current),
            "change_pct": float(stats.change_pct),
            "timestamp": stats.timestamp.isoformat()
        },
        "volume_stats": {
            "symbol": volume_stats.symbol,
            "interval": volume_stats.interval,
            "window_size": volume_stats.window_size,
            "mean_volume": float(volume_stats.mean_volume),
            "std_volume": float(volume_stats.std_volume),
            "total_volume": float(volume_stats.total_volume),
            "timestamp": volume_stats.timestamp.isoformat()
        },
        "last_update": result['last_update'].isoformat()
    }


def serialize_pairs(result):
    """Serialize pairs analytics to JSON."""
    reg = result['regression']
    adf = result.get('adf_test')
    corr = result.get('correlation')
    
    data = {
        "regression": {
            "hedge_ratio": float(reg.hedge_ratio),
            "intercept": float(reg.intercept),
            "r_squared": float(reg.r_squared),
            "std_error": float(reg.std_error),
            "timestamp": reg.timestamp.isoformat()
        },
        "spread": {
            "values": [float(x) for x in result['spread'][-100:]],
            "latest": float(result['spread'][-1]) if result['spread'] else None
        },
        "z_score": {
            "values": [float(x) if not str(x) == 'nan' else None for x in result['z_score'][-100:]],
            "latest": float(result['z_score'][-1]) if result['z_score'] and not str(result['z_score'][-1]) == 'nan' else None
        }
    }
    
    if adf:
        data["stationarity"] = {
            "test_statistic": float(adf.test_statistic),
            "p_value": float(adf.p_value),
            "is_stationary": bool(adf.is_stationary),  # Convert numpy bool_ to Python bool
            "critical_values": {k: float(v) for k, v in adf.critical_values.items()},
            "interpretation": adf.interpretation,
            "timestamp": adf.timestamp.isoformat()
        }
    
    if corr:
        data["correlation"] = {
            "current": float(corr.correlation),
            "rolling_window": corr.rolling_window,
            "history": [
                {"timestamp": ts.isoformat(), "value": float(val)}
                for ts, val in corr.correlation_history[-50:]
            ],
            "timestamp": corr.timestamp.isoformat()
        }
    
    data["last_update"] = result['last_update'].isoformat()
    
    return data


# ============================================================================
# API ENDPOINTS
# ============================================================================

@app.route('/api/health', methods=['GET'])
def health_check():
    """Health check endpoint."""
    return jsonify({
        "status": "healthy",
        "service": "Crypto Analytics API",
        "timestamp": datetime.now().isoformat()
    })


@app.route('/api/ohlc/<symbol>', methods=['GET'])
def get_ohlc(symbol):
    """
    Get OHLC bars for a symbol.
    
    Query params:
    - interval: Bar interval (1s, 1m, 5m) [default: 1m]
    - limit: Max bars to return [default: 500]
    """
    interval = request.args.get('interval', '1m')
    limit = int(request.args.get('limit', 500))
    
    @async_to_sync
    async def fetch():
        db = DatabaseManager(DATABASE_PATH)
        await db.initialize()
        
        end = datetime.now()
        start = end - timedelta(hours=24)
        
        bars = await db.get_ohlc(symbol, interval, start, end, limit=limit)
        await db.close()
        
        return bars
    
    bars = fetch()
    
    if not bars:
        return jsonify({"error": f"No data available for {symbol}"}), 404
    
    return jsonify({
        "symbol": symbol,
        "interval": interval,
        "count": len(bars),
        "bars": serialize_ohlc(bars)
    })


@app.route('/api/stats/<symbol>', methods=['GET'])
def get_statistics(symbol):
    """
    Get price/volume statistics for a symbol.
    
    Query params:
    - interval: Bar interval [default: 1m]
    - window: Rolling window size [default: 60]
    - force_refresh: Bypass cache [default: false]
    """
    interval = request.args.get('interval', '1m')
    window = int(request.args.get('window', 60))
    force_refresh = request.args.get('force_refresh', 'false').lower() == 'true'
    
    @async_to_sync
    async def fetch():
        db = DatabaseManager(DATABASE_PATH)
        await db.initialize()
        engine = AnalyticsEngine(db)
        
        result = await engine.get_symbol_analytics(symbol, interval, force_refresh)
        await db.close()
        
        return result
    
    result = fetch()
    
    if not result:
        return jsonify({"error": f"Insufficient data for {symbol}"}), 404
    
    return jsonify(serialize_stats(result))


@app.route('/api/pairs', methods=['GET'])
def get_pairs_analytics():
    """
    Get complete pairs trading analytics.
    
    Query params:
    - symbol_x: First symbol (required)
    - symbol_y: Second symbol (required)
    - interval: Bar interval [default: 1m]
    - window: Rolling window [default: 60]
    - force_refresh: Bypass cache [default: false]
    """
    symbol_x = request.args.get('symbol_x')
    symbol_y = request.args.get('symbol_y')
    
    if not symbol_x or not symbol_y:
        return jsonify({"error": "symbol_x and symbol_y are required"}), 400
    
    interval = request.args.get('interval', '1m')
    window = int(request.args.get('window', 60))
    force_refresh = request.args.get('force_refresh', 'false').lower() == 'true'
    
    @async_to_sync
    async def fetch():
        db = DatabaseManager(DATABASE_PATH)
        await db.initialize()
        engine = AnalyticsEngine(db)
        
        result = await engine.get_pairs_analytics(
            symbol_x, symbol_y, interval, force_refresh
        )
        await db.close()
        
        return result
    
    result = fetch()
    
    if not result:
        return jsonify({"error": "Insufficient data for pairs analysis"}), 404
    
    return jsonify({
        "symbol_x": symbol_x,
        "symbol_y": symbol_y,
        "interval": interval,
        "window": window,
        **serialize_pairs(result)
    })


@app.route('/api/symbols', methods=['GET'])
def get_symbols():
    """Get list of available symbols."""
    from ..config import SYMBOLS
    
    return jsonify({
        "symbols": SYMBOLS,
        "pairs": [[x, y] for x, y in DEFAULT_SYMBOL_PAIRS]
    })




@app.route('/api/upload/ohlc', methods=['POST'])
def upload_ohlc():
    """
    Upload historical OHLC data from CSV file.
    
    Expected CSV format:
    timestamp,symbol,interval,open,high,low,close,volume,trade_count
    2024-12-16T10:00:00,BTCUSDT,1m,86000.0,86100.0,85900.0,86050.0,100.5,1500
    """
    try:
        # Check if file was uploaded
        if 'file' not in request.files:
            return jsonify({"error": "No file provided"}), 400
        
        file = request.files['file']
        
        if file.filename == '':
            return jsonify({"error": "No file selected"}), 400
        
        if not file.filename.endswith('.csv'):
            return jsonify({"error": "Only CSV files are supported"}), 400
        
        # Read CSV content
        content = file.read().decode('utf-8')
        lines = content.strip().split('\n')
        
        if len(lines) < 2:
            return jsonify({"error": "CSV file is empty"}), 400
        
        # Parse header
        header = lines[0].strip().split(',')
        required_fields = ['timestamp', 'symbol', 'interval', 'open', 'high', 'low', 'close', 'volume']
        
        if not all(field in header for field in required_fields):
            return jsonify({"error": f"CSV must contain fields: {', '.join(required_fields)}"}), 400
        
        # Parse data rows
        from ..analytics.models import OHLCData
        ohlc_bars = []
        
        for line_num, line in enumerate(lines[1:], start=2):
            try:
                values = line.strip().split(',')
                if len(values) < len(required_fields):
                    continue
                
                row = dict(zip(header, values))
                
                # Parse timestamp
                timestamp = datetime.fromisoformat(row['timestamp'].replace('Z', '+00:00'))
                
                # Create OHLC object
                ohlc = OHLCData(
                    timestamp=timestamp,
                    symbol=row['symbol'],
                    interval=row['interval'],
                    open=float(row['open']),
                    high=float(row['high']),
                    low=float(row['low']),
                    close=float(row['close']),
                    volume=float(row['volume']),
                    trade_count=int(row.get('trade_count', 0))
                )
                ohlc_bars.append(ohlc)
                
            except Exception as e:
                logger.warning(f"Skipping line {line_num}: {e}")
                continue
        
        if not ohlc_bars:
            return jsonify({"error": "No valid OHLC data found in file"}), 400
        
        # Insert into database
        @async_to_sync
        async def insert_data():
            db = DatabaseManager(DATABASE_PATH)
            await db.initialize()
            
            inserted = 0
            for bar in ohlc_bars:
                await db.insert_ohlc(bar)
                inserted += 1
            
            await db.close()
            return inserted
        
        inserted_count = insert_data()
        
        # Get summary
        symbols = list(set(bar.symbol for bar in ohlc_bars))
        intervals = list(set(bar.interval for bar in ohlc_bars))
        
        return jsonify({
            "success": True,
            "message": f"Successfully uploaded {inserted_count} OHLC bars",
            "summary": {
                "total_bars": inserted_count,
                "symbols": symbols,
                "intervals": intervals,
                "time_range": {
                    "start": ohlc_bars[0].timestamp.isoformat() if ohlc_bars else None,
                    "end": ohlc_bars[-1].timestamp.isoformat() if ohlc_bars else None
                }
            }
        })
        
    except Exception as e:
        logger.error(f"Upload error: {e}")
        return jsonify({"error": f"Upload failed: {str(e)}"}), 500


@app.route('/api/export/csv/<symbol_x>/<symbol_y>', methods=['GET'])
def export_analytics_csv(symbol_x, symbol_y):
    """
    Export pairs analytics as CSV.
    
    Query params:
    - interval: Bar interval [default: 1m]
    """
    interval = request.args.get('interval', '1m')
    
    @async_to_sync
    async def fetch():
        db = DatabaseManager(DATABASE_PATH)
        await db.initialize()
        engine = AnalyticsEngine(db)
        
        result = await engine.get_pairs_analytics(symbol_x, symbol_y, interval, force_refresh=True)
        await db.close()
        
        return result
    
    result = fetch()
    
    if not result:
        return jsonify({"error": "No data to export"}), 404
    
    # Create CSV
    output = io.StringIO()
    writer = csv.writer(output)
    
    # Headers
    writer.writerow([
        'index', 'spread', 'z_score', 'hedge_ratio', 'r_squared', 
        'is_stationary', 'correlation'
    ])
    
    # Data rows
    reg = result['regression']
    adf = result.get('adf_test')
    corr = result.get('correlation')
    
    for i, (spread, zscore) in enumerate(zip(result['spread'], result['z_score'])):
        writer.writerow([
            i,
            float(spread),
            float(zscore) if not str(zscore) == 'nan' else '',
            float(reg.hedge_ratio),
            float(reg.r_squared),
            bool(adf.is_stationary) if adf else '',
            float(corr.correlation) if corr else ''
        ])
    
    # Prepare file
    output.seek(0)
    mem_file = io.BytesIO()
    mem_file.write(output.getvalue().encode('utf-8'))
    mem_file.seek(0)
    
    filename = f"analytics_{symbol_x}_{symbol_y}_{interval}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
    
    return send_file(
        mem_file,
        mimetype='text/csv',
        as_attachment=True,
        download_name=filename
    )


@app.errorhandler(404)
def not_found(error):
    """404 error handler."""
    return jsonify({"error": "Endpoint not found"}), 404


@app.errorhandler(500)
def internal_error(error):
    """500 error handler."""
    logger.error(f"Internal error: {error}")
    return jsonify({"error": "Internal server error"}), 500


if __name__ == '__main__':
    from ..config import FLASK_HOST, FLASK_PORT
    
    logging.basicConfig(level=logging.INFO)
    logger.info(f"Starting Flask API on {FLASK_HOST}:{FLASK_PORT}")
    
    app.run(
        host=FLASK_HOST,
        port=FLASK_PORT,
        debug=FLASK_DEBUG
    )
