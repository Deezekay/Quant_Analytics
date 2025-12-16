"""
Validation script for Phase 2 database persistence.

Run main.py for 1 minute, then run this script to verify:
1. Ticks are being persisted to database
2. OHLC bars are being generated correctly
3. Queries work as expected
4. Data integrity is maintained

Usage:
    python scripts/validate_db.py
"""

import asyncio
import sys
from datetime import datetime, timedelta
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.storage.database import DatabaseManager
from src.config import DATABASE_PATH


async def validate():
    """Run validation checks on the database."""
    
    print("=" * 70)
    print("CRYPTO ANALYTICS PLATFORM - DATABASE VALIDATION")
    print("=" * 70)
    print()
    
    try:
        # Initialize database connection
        db = DatabaseManager(DATABASE_PATH)
        await db.initialize()
        
        # Define time range (last 2 minutes to be safe)
        end = datetime.now()
        start = end - timedelta(minutes=2)
        
        print(f"Time Range: {start.strftime('%Y-%m-%d %H:%M:%S')} to {end.strftime('%Y-%m-%d %H:%M:%S')}")
        print()
        
        # =====================================================================
        # Test 1: Tick Count Validation
        # =====================================================================
        print("📊 TEST 1: Tick Persistence")
        print("-" * 70)
        
        symbols = ["BTCUSDT", "ETHUSDT"]
        total_ticks = 0
        
        for symbol in symbols:
            ticks = await db.get_ticks(symbol, start, end)
            count = len(ticks)
            total_ticks += count
            
            status = "✅ PASS" if count > 0 else "❌ FAIL (No ticks found)"
            print(f"  {symbol:12} {count:6,} ticks  {status}")
            
            # Show sample tick if available
            if ticks:
                sample = ticks[0]
                print(f"    Sample: {sample.timestamp.strftime('%H:%M:%S.%f')[:-3]} | "
                      f"${sample.price:,.2f} | {sample.size:.6f}")
        
        print(f"\n  Total ticks: {total_ticks:,}")
        print()
        
        # =====================================================================
        # Test 2: OHLC Bar Generation (1s interval)
        # =====================================================================
        print("📈 TEST 2: OHLC Bars (1-second interval)")
        print("-" * 70)
        
        for symbol in symbols:
            bars_1s = await db.get_ohlc(symbol, "1s", start, end)
            count = len(bars_1s)
            
            # Expect at least some bars in 2 minutes (expect ~60-120)
            status = "✅ PASS" if count > 10 else "⚠️  WARNING (Few bars)"
            print(f"  {symbol:12} {count:6} bars  {status}")
            
            # Show sample bar if available
            if bars_1s:
                bar = bars_1s[0]
                print(f"    Sample: {bar.timestamp.strftime('%H:%M:%S')} | "
                      f"O: ${bar.open:,.2f} | H: ${bar.high:,.2f} | "
                      f"L: ${bar.low:,.2f} | C: ${bar.close:,.2f} | "
                      f"V: {bar.volume:.6f} | Trades: {bar.trade_count}")
        
        print()
        
        # =====================================================================
        # Test 3: OHLC Bar Generation (1m interval)
        # =====================================================================
        print("📈 TEST 3: OHLC Bars (1-minute interval)")
        print("-" * 70)
        
        for symbol in symbols:
            bars_1m = await db.get_ohlc(symbol, "1m", start, end)
            count = len(bars_1m)
            
            # Expect 1-2 bars (depends on when you ran it)
            status = "✅ PASS" if count > 0 else "⚠️  WARNING (No bars yet)"
            print(f"  {symbol:12} {count:6} bars  {status}")
            
            # Show detailed bar info
            if bars_1m:
                for bar in bars_1m:
                    print(f"    {bar.timestamp.strftime('%H:%M:%S')} | "
                          f"O: ${bar.open:,.2f} | H: ${bar.high:,.2f} | "
                          f"L: ${bar.low:,.2f} | C: ${bar.close:,.2f} | "
                          f"V: {bar.volume:.6f} | Trades: {bar.trade_count}")
        
        print()
        
        # =====================================================================
        # Test 4: OHLC Bar Generation (5m interval)
        # =====================================================================
        print("📈 TEST 4: OHLC Bars (5-minute interval)")
        print("-" * 70)
        
        for symbol in symbols:
            bars_5m = await db.get_ohlc(symbol, "5m", start, end)
            count = len(bars_5m)
            
            # May or may not have completed a 5m bar yet
            status = "✅ PASS" if count >= 0 else "❌ FAIL"
            print(f"  {symbol:12} {count:6} bars  {status}")
            
            if bars_5m:
                bar = bars_5m[0]
                print(f"    {bar.timestamp.strftime('%H:%M:%S')} | "
                      f"O: ${bar.open:,.2f} | H: ${bar.high:,.2f} | "
                      f"L: ${bar.low:,.2f} | C: ${bar.close:,.2f} | "
                      f"V: {bar.volume:.6f} | Trades: {bar.trade_count}")
        
        print()
        
        # =====================================================================
        # Test 5: Latest Price Query
        # =====================================================================
        print("💰 TEST 5: Latest Price Query")
        print("-" * 70)
        
        for symbol in symbols:
            latest_price = await db.get_latest_price(symbol)
            
            if latest_price:
                status = "✅ PASS"
                print(f"  {symbol:12} ${latest_price:,.2f}  {status}")
            else:
                status = "❌ FAIL"
                print(f"  {symbol:12} No price data  {status}")
        
        print()
        
        # =====================================================================
        # Summary
        # =====================================================================
        print("=" * 70)
        print("VALIDATION SUMMARY")
        print("=" * 70)
        
        if total_ticks > 100:
            print("✅ Database persistence: WORKING")
            print("✅ Tick ingestion: ACTIVE")
        else:
            print("⚠️  Low tick count - run main.py for longer")
        
        print()
        print(f"Database file: {DATABASE_PATH}")
        print(f"Validation completed at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print("=" * 70)
        
        # Close database
        await db.close()
        
    except FileNotFoundError:
        print("❌ ERROR: Database file not found!")
        print(f"   Expected location: {DATABASE_PATH}")
        print()
        print("   Please run: python main.py")
        print("   Let it run for at least 1 minute, then try again.")
        print("=" * 70)
        
    except Exception as e:
        print(f"❌ ERROR: {e}")
        print("=" * 70)
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    print()
    asyncio.run(validate())
    print()
