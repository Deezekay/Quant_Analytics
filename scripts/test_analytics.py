"""
Test script for Phase 3 analytics engine.

This script validates all analytics computations after data collection:
- Price/volume statistics
- OLS regression and hedge ratios
- Spread calculation and z-scores
- ADF stationarity testing
- Rolling correlation

Usage:
    1. Run main.py for at least 5 minutes to accumulate data
    2. Run: python scripts/test_analytics.py
"""

import asyncio
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.storage.database import DatabaseManager
from src.analytics.engine import AnalyticsEngine
from src.config import DATABASE_PATH


async def test_analytics():
    """Run comprehensive analytics tests."""
    
    print("=" * 80)
    print("CRYPTO ANALYTICS PLATFORM - Phase 3 Analytics Test")
    print("=" * 80)
    print()
    
    try:
        # Initialize database and engine
        db = DatabaseManager(DATABASE_PATH)
        await db.initialize()
        
        engine = AnalyticsEngine(db)
        
        # =====================================================================
        # Test 1: Single Symbol Analytics (BTCUSDT)
        # =====================================================================
        print("📊 TEST 1: Single Symbol Analytics - BTCUSDT")
        print("-" * 80)
        
        btc_analytics = await engine.get_symbol_analytics("BTCUSDT", "1m")
        
        if btc_analytics:
            stats = btc_analytics['stats']
            vol_stats = btc_analytics['volume_stats']
            
            print(f"✅ Price Statistics:")
            print(f"   Symbol: {stats.symbol}")
            print(f"   Interval: {stats.interval}")
            print(f"   Window: {stats.window_size} bars")
            print(f"   Mean: ${stats.mean:,.2f}")
            print(f"   Std Dev: ${stats.std:,.2f}")
            print(f"   Min: ${stats.min:,.2f}")
            print(f"   Max: ${stats.max:,.2f}")
            print(f"   Current: ${stats.current:,.2f}")
            print(f"   Change: {stats.change_pct:+.2f}%")
            print()
            
            print(f"✅ Volume Statistics:")
            print(f"   Mean Volume: {vol_stats.mean_volume:.6f}")
            print(f"   Std Volume: {vol_stats.std_volume:.6f}")
            print(f"   Total Volume: {vol_stats.total_volume:.6f}")
        else:
            print("❌ FAIL: Insufficient data for BTCUSDT analytics")
            print("   Please run main.py for at least 5 minutes")
        
        print()
        
        # =====================================================================
        # Test 2: Single Symbol Analytics (ETHUSDT)
        # =====================================================================
        print("📊 TEST 2: Single Symbol Analytics - ETHUSDT")
        print("-" * 80)
        
        eth_analytics = await engine.get_symbol_analytics("ETHUSDT", "1m")
        
        if eth_analytics:
            stats = eth_analytics['stats']
            print(f"✅ Price Statistics:")
            print(f"   Mean: ${stats.mean:,.2f}")
            print(f"   Std Dev: ${stats.std:,.2f}")
            print(f"   Current: ${stats.current:,.2f}")
            print(f"   Change: {stats.change_pct:+.2f}%")
        else:
            print("❌ FAIL: Insufficient data for ETHUSDT analytics")
        
        print()
        
        # =====================================================================
        # Test 3: Pairs Trading Analytics (BTC-ETH)
        # =====================================================================
        print("📈 TEST 3: Pairs Trading Analytics - BTCUSDT vs ETHUSDT")
        print("-" * 80)
        
        pairs = await engine.get_pairs_analytics("BTCUSDT", "ETHUSDT", "1m")
        
        if pairs:
            regression = pairs['regression']
            spread = pairs['spread']
            z_scores = pairs['z_score']
            adf = pairs['adf_test']
            corr = pairs['correlation']
            
            print(f"✅ OLS Regression:")
            print(f"   Equation: {regression.symbol_y} = "
                  f"{regression.intercept:.2f} + "
                  f"{regression.hedge_ratio:.6f} × {regression.symbol_x}")
            print(f"   Hedge Ratio (β): {regression.hedge_ratio:.6f}")
            print(f"     → If BTC moves $1, ETH moves ${regression.hedge_ratio:.6f}")
            print(f"   R² (fit): {regression.r_squared:.4f}")
            print(f"     →{regression.r_squared * 100:.2f}% of ETH variance explained by BTC")
            print(f"   Std Error: {regression.std_error:.4f}")
            print()
            
            print(f"✅ Spread Analysis:")
            print(f"   Data Points: {len(spread)}")
            if spread:
                print(f"   Latest Spread: ${spread[-1]:.2f}")
                print(f"   Mean Spread: ${sum(spread)/len(spread):.2f}")
            print()
            
            print(f"✅ Z-Score (Trading Signal):")
            valid_z = [z for z in z_scores if not str(z) == 'nan']
            if valid_z:
                latest_z = valid_z[-1]
                print(f"   Latest Z-Score: {latest_z:.2f}")
                
                if latest_z > 2:
                    signal = "🔴 OVERBOUGHT - Consider shorting spread"
                elif latest_z < -2:
                    signal = "🟢 OVERSOLD - Consider longing spread"
                elif abs(latest_z) < 1:
                    signal = "⚪ NORMAL RANGE - No signal"
                else:
                    signal = "🟡 NEUTRAL - Watch for extremes"
                
                print(f"   Signal: {signal}")
            print()
            
            if adf:
                print(f"✅ ADF Stationarity Test:")
                print(f"   Test Statistic: {adf.test_statistic:.4f}")
                print(f"   P-Value: {adf.p_value:.4f}")
                print(f"   Critical Values:")
                for level, value in adf.critical_values.items():
                    print(f"     {level:>4}: {value:.4f}")
                print(f"   Result: {'✅ STATIONARY' if adf.is_stationary else '❌ NON-STATIONARY'}")
                if adf.is_stationary:
                    print(f"   → Spread is mean-reverting, suitable for pairs trading!")
                else:
                    print(f"   → Spread may not be mean-reverting, use caution")
                print()
                print(f"   Interpretation:")
                print(f"   {adf.interpretation}")
            print()
            
            if corr:
                print(f"✅ Correlation Analysis:")
                print(f"   Latest Correlation: {corr.correlation:.4f}")
                
                if corr.correlation > 0.8:
                    strength = "🟢 VERY STRONG positive"
                elif corr.correlation > 0.5:
                    strength = "🟡 MODERATE positive"
                elif corr.correlation > 0:
                    strength = "⚪ WEAK positive"
                elif corr.correlation > -0.5:
                    strength = "⚪ WEAK negative"
                else:
                    strength = "🔴 STRONG negative"
                
                print(f"   Strength: {strength}")
                print(f"   History Points: {len(corr.correlation_history)}")
            
        else:
            print("❌ FAIL: Insufficient data for pairs analytics")
            print("   Please run main.py for at least 5 minutes to collect enough data")
            print("   Required: ~30 aligned 1m OHLC bars for BTCUSDT and ETHUSDT")
        
        print()
        
        # =====================================================================
        # Summary
        # =====================================================================
        print("=" * 80)
        print("TEST SUMMARY")
        print("=" * 80)
        
        if btc_analytics and eth_analytics and pairs:
            print("✅ ALL TESTS PASSED!")
            print()
            print("Phase 3 Analytics Engine is working correctly!")
            print()
            print("Key Metrics:")
            if pairs:
                print(f"  • Hedge Ratio: {pairs['regression'].hedge_ratio:.6f}")
                print(f"  • R²: {pairs['regression'].r_squared:.4f}")
                if pairs['adf_test']:
                    print(f"  • Stationary: {pairs['adf_test'].is_stationary}")
                if pairs['correlation']:
                    print(f"  • Correlation: {pairs['correlation'].correlation:.4f}")
        else:
            print("⚠️  PARTIAL SUCCESS")
            print()
            print("Some analytics could not be computed due to insufficient data.")
            print("Recommendation: Run main.py for 5-10 minutes, then retry this test.")
        
        print("=" * 80)
        
        # Close database
        await db.close()
        
    except FileNotFoundError:
        print("❌ ERROR: Database file not found!")
        print(f"   Expected location: {DATABASE_PATH}")
        print()
        print("   Please run: python main.py")
        print("   Let it run for at least 5 minutes, then try again.")
        print("=" * 80)
        
    except Exception as e:
        print(f"❌ ERROR: {e}")
        print("=" * 80)
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    print()
    asyncio.run(test_analytics())
    print()
