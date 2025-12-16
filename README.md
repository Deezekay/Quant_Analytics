# Quant Analytics Platform

Professional-grade cryptocurrency pairs trading analytics platform with real-time WebSocket data ingestion, log-returns regression, and statistical validation.

---

## 🎯 Project Context

This platform provides **quantitative analysis tools for crypto pairs trading**, specifically designed for statistical arbitrage strategies. It addresses the core challenge in pairs trading: **identifying mean-reverting relationships between correlated assets in real-time**.

### **Business Problem**
- Manual monitoring of crypto pairs is inefficient and error-prone
- Raw price regression yields misleading hedge ratios due to scale mismatch
- Traders need instant alerts when spreads deviate beyond statistical thresholds
- Real-time data processing is critical for high-frequency trading decisions

### **Solution**
A complete end-to-end analytics platform that:
1. Ingests live tick data from Binance WebSocket
2. Computes **log-returns-based regression** for scale-invariant metrics
3. Validates stationarity using **Augmented Dickey-Fuller (ADF) tests**
4. Alerts traders when Z-scores exceed configurable thresholds
5. Provides professional-grade visualizations via an interactive dashboard

---

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    QUANT ANALYTICS PLATFORM                  │
└─────────────────────────────────────────────────────────────┘
                              │
        ┌─────────────────────┼─────────────────────┐
        │                     │                     │
   ┌────▼────┐          ┌────▼────┐          ┌────▼────┐
   │ INGESTION│          │ANALYTICS│          │   UI    │
   │  Layer   │          │ Engine  │          │Dashboard│
   └────┬────┘          └────┬────┘          └────┬────┘
        │                     │                     │
   WebSocket ───► SQLite ───► Regression ───► Dash/Plotly
   (Binance)      (OHLC)      Stats/ADF       (Alerts)
```

### **Components**

#### **1. Data Ingestion (`src/ingestion/`)**
- **WebSocket Client**: Connects to Binance for BTC/ETH tick data
- **Real-time Aggregation**: Converts ticks → 1s/1m/5m OHLC bars
- **SQLite Storage**: Persistent storage with `ticks` and `ohlc` tables

#### **2. Analytics Engine (`src/analytics/`)**
- **Regression (`regression.py`)**: Log-returns OLS with sanity gates (|β| < 3, R² > 0.3)
- **Stationarity (`stationarity.py`)**: ADF test on return spreads
- **Correlation (`correlation.py`)**: Rolling correlation tracking
- **Statistics (`statistics.py`)**: Z-score computation for spread monitoring

#### **3. REST API (`src/api/`)**
- **Flask Server**: Exposes `/api/pairs`, `/api/stats`, `/api/health`
- **JSON Endpoints**: Serves regression results, Z-scores, ADF tests
- **OHLC Upload**: CSV import for historical data

#### **4. Dashboard (`src/dashboard/`)**
- **Dash/Plotly UI**: Interactive charts (Price, Spread, Correlation, Heatmap)
- **Compact Stats Cards**: 4 horizontal badges (Price Stats, Regression, Stationarity, Alerts)
- **Live Status Banner**: Displays timestamp, timeframe, window settings
- **Alert System**: Visual + audio notifications for Z-score thresholds

---

## 📊 Workflow

```
1. START PLATFORM
   └─► python start_platform.py

2. DATA INGESTION (Auto)
   ├─► Connect to Binance WebSocket
   ├─► Stream BTC/ETH ticks
   ├─► Aggregate to OHLC (1s, 1m, 5m)
   └─► Store in SQLite

3. ANALYTICS COMPUTATION (Auto, every update)
   ├─► Fetch aligned OHLC data
   ├─► Compute log returns: r_t = log(P_t) - log(P_{t-1})
   ├─► OLS Regression: r_ETH = α + β·r_BTC + ε
   ├─► Sanity Gates:
   │   ├─► |β| must be < 3.0
   │   ├─► R² must be > 0.3
   │   └─► σ(β) must be < |β|
   ├─► Spread: s_t = r_ETH - β·r_BTC
   ├─► Z-Score: z = (s_t - μ) / σ
   └─► ADF Test on spread (stationarity check)

4. DASHBOARD VISUALIZATION (Auto-refresh every 5s)
   ├─► Fetch /api/pairs?symbol_x=BTCUSDT&symbol_y=ETHUSDT
   ├─► Render compact stats cards
   ├─► Plot charts (Price, Spread, Correlation)
   └─► Trigger alerts if |Z| > threshold

5. USER INTERACTION
   ├─► Adjust timeframe (1s, 1m, 5m)
   ├─► Change rolling window (10-500 periods)
   ├─► Set Z-score threshold (default: 2.0)
   └─► Export data to CSV
```

---

## 🚀 Quick Start

### **Prerequisites**
- Python 3.8+
- Internet connection (for Binance WebSocket)

### **Installation**
```bash
# Clone repository
git clone https://github.com/Deezekay/Quant_Analytics.git
cd Quant_Analytics

# Install dependencies
pip install -r requirements.txt
```

### **Run Platform**
```bash
# Single command to start all services
python start_platform.py
```

This launches:
- **WebSocket Ingestion** (port 8765)
- **Flask API** (port 5000)
- **Dash Dashboard** (port 8050)

### **Access Dashboard**
Open browser: `http://localhost:8050`

---

## 📁 Project Structure

```
crypto-analytics/
├── src/
│   ├── analytics/
│   │   ├── regression.py      # Log-returns OLS with sanity gates
│   │   ├── stationarity.py    # ADF test implementation
│   │   ├── correlation.py     # Rolling correlation
│   │   ├── statistics.py      # Z-score computation
│   │   ├── resampler.py       # OHLC aggregation
│   │   └── engine.py          # Orchestrates all analytics
│   ├── api/
│   │   └── flask_server.py    # REST API endpoints
│   ├── dashboard/
│   │   └── app.py             # Dash UI (compact layout)
│   ├── ingestion/
│   │   └── binance_websocket.py  # Live data stream
│   └── storage/
│       └── database.py        # SQLite ORM
├── scripts/
│   ├── check_db.py            # Database verification
│   ├── test_analytics.py      # Analytics testing
│   └── validate_db.py         # Data validation
├── start_platform.py          # Main entry point
├── schema.sql                 # Database schema
├── requirements.txt           # Python dependencies
└── README.md                  # This file
```

---

## 🔬 Key Features

### **1. Log-Returns Regression (Industry Standard)**
- **Why Log Returns?** Scale-invariant, numerically stable, additive
- **Formula**: `r_t = log(P_t) - log(P_{t-1})`
- **Interpretation**: β = 1.12 means "ETH returns 1.12% when BTC returns 1%"

### **2. Professional Sanity Gates**
Regression results are **suppressed** if:
- `|β| > 3.0` → Unrealistic leverage (data misalignment)
- `R² < 0.3` → Weak relationship (not suitable for pairs trading)
- `σ(β) > |β|` → Unstable estimate (high uncertainty)

### **3. Real-Time Alerts**
- **Trigger**: When `|Z-score| > threshold` (default: 2.0)
- **Interpretation**: Spread has deviated >2 standard deviations
- **Action**: Mean reversion trade opportunity

### **4. Compact Dashboard UI**
- **4 Horizontal Stats Cards**: Price Stats, Regression, Stationarity, Alerts
- **Minimal vertical space**: ~70px total (vs 180px before)
- **Charts prioritized**: Occupy 75% of viewport
- **Z-Score input**: Inline (60px wide)

---

## 📈 Expected Results

After 60 seconds of data collection:
- **β (Beta)**: 0.8 to 1.2 (BTC-ETH return sensitivity)
- **R²**: 0.5 to 0.8 (strong explanatory power)
- **Intercept (α)**: ~0 (near zero for returns)
- **ADF p-value**: < 0.05 (spread is stationary at 95% confidence)

---

## 🛠️ Configuration

Edit `src/config.py`:
```python
# API Settings
FLASK_HOST = 'localhost'
FLASK_PORT = 5000

# Dashboard Settings
DASH_HOST = 'localhost'
DASH_PORT = 8050
DASHBOARD_UPDATE_INTERVAL = 5000  # 5 seconds

# Analytics Settings
DEFAULT_TRADING_PAIR_X = 'BTCUSDT'
DEFAULT_TRADING_PAIR_Y = 'ETHUSDT'
DEFAULT_ROLLING_WINDOW = 60
ZSCORE_THRESHOLD = 2.0

# Database
DATABASE_PATH = 'data/crypto_analytics.db'
```

---

## 🧪 Testing

```bash
# Test database setup
python scripts/check_db.py

# Test analytics engine
python scripts/test_analytics.py

# Validate data quality
python scripts/validate_db.py
```

---

## 📊 API Endpoints

### **GET /api/pairs**
```bash
curl "http://localhost:5000/api/pairs?symbol_x=BTCUSDT&symbol_y=ETHUSDT&interval=1m&window=60"
```

Returns:
- `regression`: {hedge_ratio, r_squared, intercept, std_error}
- `z_score`: {latest, values, mean, std}
- `stationarity`: {is_stationary, p_value, test_statistic}
- `correlation`: Rolling correlation values

### **GET /api/stats/{symbol}**
```bash
curl "http://localhost:5000/api/stats/BTCUSDT"
```

Returns basic price statistics.

### **POST /api/upload/ohlc**
Upload CSV with historical OHLC data.

---

## 🎯 Use Cases

1. **Pairs Trading Desks**: Real-time spread monitoring
2. **Quant Researchers**: Statistical validation of trading relationships
3. **Hedge Funds**: Risk-neutral arbitrage signal generation
4. **Crypto Traders**: Automated mean-reversion alerts

---

## ⚠️ Important Notes

- **Database Excluded**: The `data/` folder is gitignored (721MB database)
- **Fresh Data**: Clone creates empty DB, platform auto-populates from Binance
- **Internet Required**: WebSocket needs live connection
- **Single Command**: `python start_platform.py` runs everything

---

## Screenshots

<img width="1896" height="980" alt="image" src="https://github.com/user-attachments/assets/227b9398-f510-44f3-930e-6f5c24098c4c" />

<img width="1367" height="610" alt="image" src="https://github.com/user-attachments/assets/ce1fc7a7-7533-40f7-bc8b-f641406cc476" />



## 📜 License

MIT License - Free to use, modify, and distribute.

---

## 👨‍💻 Author

**Deezekay**  
GitHub: [@Deezekay](https://github.com/Deezekay)

---

## 🙏 Acknowledgments

- **Binance**: Live WebSocket data
- **Plotly/Dash**: Interactive visualizations
- **SciPy/Statsmodels**: Statistical analysis

---

**Built with professional quant standards. Ready for production use.** 🚀
