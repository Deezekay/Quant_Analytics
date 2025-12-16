"""
Run the Dash dashboard.

Usage:
    python run_dashboard.py
"""

import logging
from src.dashboard.app import app
from src.config import DASH_HOST, DASH_PORT, DASH_DEBUG

if __name__ == '__main__':
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    print(f"📊 Starting Dash dashboard on http://{DASH_HOST}:{DASH_PORT}")
    print("🎯 Features:")
    print("   • Interactive price charts")
    print("   • Spread & Z-score analysis")
    print("   • Rolling correlation")
    print("   • Real-time alerts")
    print("   • CSV export")
    print()
    
    app.run_server(
        host=DASH_HOST,
        port=DASH_PORT,
        debug=DASH_DEBUG
    )
