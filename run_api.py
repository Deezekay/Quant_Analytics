"""
Run the Flask API server.

Usage:
    python run_api.py
"""

import logging
from src.api.flask_server import app
from src.config import FLASK_HOST, FLASK_PORT, FLASK_DEBUG

if __name__ == '__main__':
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    print(f"🌐 Starting Flask API server on http://{FLASK_HOST}:{FLASK_PORT}")
    print("📖 Available endpoints:")
    print("   GET /api/health - Health check")
    print("   GET /api/symbols - List symbols")
    print("   GET /api/ohlc/<symbol> - Get OHLC data")
    print("   GET /api/stats/<symbol> - Get statistics")
    print("   GET /api/pairs - Get pairs analytics")
    print("   GET /api/export/csv/<x>/<y> - Export CSV")
    print()
    
    app.run(
        host=FLASK_HOST,
        port=FLASK_PORT,
        debug=FLASK_DEBUG
    )
