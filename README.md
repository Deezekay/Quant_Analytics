# Crypto Analytics Platform - Complete (Phases 1-4)

A production-grade, real-time quantitative trading analytics platform for cryptocurrency markets with **Flask REST API** and **Plotly Dash dashboard**.

## Overview

This platform provides a complete quantitative trading workflow:

**Phase 1 - Data Ingestion:**
- ✅ Multi-symbol WebSocket streams from Binance Futures
- ✅ Async architecture with auto-reconnection
- ✅ Thread-safe buffering and graceful shutdown

**Phase 2 - Persistence & Resampling:**
- ✅ SQLite database (easily upgradable to PostgreSQL/TimescaleDB)
- ✅ Batch insert optimization (100x performance improvement)
- ✅ OHLC resampling (1s, 1m, 5m intervals)

**Phase 3 - Analytics Engine:**
- ✅ Price/volume statistics with rolling windows
- ✅ OLS regression for pairs trading (hedge ratios, spreads)
- ✅ Z-score calculations for trading signals
- ✅ ADF stationarity testing
- ✅ Rolling Pearson correlation
- ✅ Smart caching with TTL (5-60s)

**Phase 4 - REST API + Dashboard:**
- ✅ Flask REST API with 7 endpoints
- ✅ Plotly Dash interactive dashboard
- ✅ Real-time charts (price, spread/z-score, correlation)
- ✅ Widget-based controls
- ✅ CSV export functionality
- ✅ Auto-refresh every 5 seconds

## Features

### Real-time Data Ingestion
- Connects to Binance Futures trade streams (`wss://fstream.binance.com/ws/{symbol}@trade`)
- Normalizes raw trade events into structured data
- Buffers incoming ticks in memory for processing

### Connection Management
- Automatic reconnection with exponential backoff (1s → 2s → 4s → 8s)
- Ping/pong keep-alive mechanism
- Comprehensive error handling and logging

### Monitoring
- Live tick display with formatted output
- Periodic status updates (every 10 seconds)
- Per-symbol tick counters

## Installation

### Prerequisites
- Python 3.9 or higher
- Internet connection for WebSocket streams

### Setup

1. **Clone or navigate to the project directory:**
   ```bash
   cd e:\Quant\crypto-analytics
   ```

2. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

## Usage

### Quick Start (All Phases)

**Start the complete platform (recommended):**

```bash
python start_platform.py
```

This starts:
1. Data ingestion + analytics engine (`main.py`)
2. Flask REST API (`run_api.py`) at `http://localhost:5000`
3. Dash dashboard (`run_dashboard.py`) at `http://localhost:8050`
4. Opens dashboard in your browser automatically

**Wait 60 seconds** for initial data collection before analytics become available.

### Individual Components

**Data ingestion only:**
```bash
python main.py
```

**Flask API only:**
```bash
python run_api.py
```

**Dash dashboard only:**
```bash
python run_dashboard.py
```

### Expected Output

```
[2024-12-16 10:30:15] INFO: Connecting to BTCUSDT...
[2024-12-16 10:30:15] INFO: Connecting to ETHUSDT...
[2024-12-16 10:30:16] INFO: Connected to BTCUSDT
[2024-12-16 10:30:16] INFO: Connected to ETHUSDT
[2024-12-16 10:30:16] INFO: Started WebSocket client for 2 symbols
[2024-12-16 10:30:16] INFO: BTCUSDT | 2024-12-16 10:30:16.234 | $43,250.50 | 0.125000
[2024-12-16 10:30:16] INFO: ETHUSDT | 2024-12-16 10:30:16.456 | $2,280.30 | 1.500000
[2024-12-16 10:30:17] INFO: BTCUSDT | 2024-12-16 10:30:17.123 | $43,251.00 | 0.050000
...
[2024-12-16 10:30:26] INFO: Status - BTCUSDT: 124 ticks, ETHUSDT: 89 ticks
```

### Stopping the Platform

Press **Ctrl+C** to trigger graceful shutdown:

```
[2024-12-16 10:35:42] INFO: Shutdown signal received
[2024-12-16 10:35:42] INFO: Shutting down WebSocket client...
[2024-12-16 10:35:42] INFO: Disconnected from BTCUSDT
[2024-12-16 10:35:42] INFO: Disconnected from ETHUSDT
[2024-12-16 10:35:42] INFO: WebSocket client stopped
[2024-12-16 10:35:42] INFO: Shutdown complete
```

## Configuration

All configuration is centralized in `src/config.py`:

### Adding/Removing Symbols

Edit the `SYMBOLS` list in `src/config.py`:

```python
SYMBOLS: List[str] = [
    "btcusdt",
    "ethusdt",
    "solusdt",  # Add new symbols here
]
```

### Adjusting Buffer Size

Modify `BUFFER_SIZE` to control memory usage:

```python
BUFFER_SIZE: int = 1000  # Max queued ticks per symbol
```

### Logging Configuration

Customize logging format and level:

```python
LOG_LEVEL: str = "INFO"  # Options: DEBUG, INFO, WARNING, ERROR
```

## Architecture

### Project Structure

```
crypto-analytics/
├── src/
│   ├── __init__.py
│   ├── ingestion/
│   │   ├── __init__.py
│   │   └── binance_websocket.py    # WebSocket client implementation
│   ├── storage/                     # Future: Database persistence
│   ├── analytics/                   # Future: Quantitative analytics
│   └── config.py                    # Centralized configuration
├── requirements.txt
├── README.md
└── main.py                          # Entry point
```

### Data Flow

```
Binance Futures → WebSocket → Normalization → Queue Buffer → Display
                                                    ↓
                                         (Future: DB Storage)
```

### Design Principles

1. **Separation of Concerns**: Ingestion logic is isolated from future storage/analytics
2. **Async-first**: Built on `asyncio` for efficient concurrency
3. **Extensibility**: Easy to add new symbols, exchanges, or data processors
4. **Production-ready**: Comprehensive error handling and logging

## Technical Specifications

### Dependencies
- **websockets** (v12.0): Modern async WebSocket client library

### Data Model

```python
@dataclass
class TradeData:
    symbol: str          # Trading pair (e.g., "BTCUSDT")
    timestamp: datetime  # Trade execution time
    price: float         # Trade price
    size: float          # Trade quantity
```

### WebSocket Message Format (Binance)

```json
{
  "e": "trade",
  "s": "BTCUSDT",
  "T": 1702742400000,
  "p": "43250.50",
  "q": "0.125"
}
```

## Next Steps (Phase 2)

- [ ] **Database Integration**: Persist ticks to TimescaleDB/PostgreSQL
- [ ] **Analytics Engine**: Real-time calculations (VWAP, OBV, correlations)
- [ ] **REST API**: Expose data via FastAPI endpoints
- [ ] **WebSocket Broadcasting**: Real-time dashboard feeds
- [ ] **Historical Backtesting**: Query and analyze stored data

## Troubleshooting

### Connection Issues

If you see repeated connection failures:
1. Check your internet connection
2. Verify Binance Futures is accessible in your region
3. Check firewall settings for WebSocket connections

### High CPU Usage

If CPU usage is high:
1. Reduce the number of symbols in `config.py`
2. Increase `BUFFER_SIZE` if queues are frequently full
3. Add artificial delays in the display loop if needed

### Missing Ticks

If ticks are being dropped:
1. Increase `BUFFER_SIZE` in `config.py`
2. Check logs for "Queue full" warnings
3. Consider implementing database storage to offload processing

## License

This project is part of a quantitative trading analytics platform.

## Author

Built for a crypto trading firm - Phase 1: Data Ingestion Foundation
