"""
Unified startup script for the complete crypto analytics platform.

Starts:
1. Main application (WebSocket ingestion + Analytics)
2. Flask REST API server
3. Dash dashboard
4. Opens dashboard in browser

Usage:
    python start_platform.py
"""

import subprocess
import time
import webbrowser
import sys
import os

def main():
    print("=" * 80)
    print("        CRYPTO QUANTITATIVE ANALYTICS PLATFORM - STARTUP")
    print("=" * 80)
    print()
    
    processes = []
    
    try:
        #  Start main application (ingestion + analytics)
        print("📡 [1/3] Starting WebSocket ingestion & analytics engine...")
        main_process = subprocess.Popen(
            [sys.executable, "main.py"],
            cwd=os.getcwd()
        )
        processes.append(("Main App", main_process))
        time.sleep(3)  # Wait for database initialization
        
        # Start Flask API
        print("🌐 [2/3] Starting Flask REST API server...")
        api_process = subprocess.Popen(
            [sys.executable, "run_api.py"],
            cwd=os.getcwd()
        )
        processes.append(("Flask API", api_process))
        time.sleep(2)  # Wait for API to be ready
        
        # Start Dash dashboard
        print("📊 [3/3] Starting Dash dashboard...")
        dashboard_process = subprocess.Popen(
            [sys.executable, "run_dashboard.py"],
            cwd=os.getcwd()
        )
        processes.append(("Dash Dashboard", dashboard_process))
        time.sleep(3)  # Wait for dashboard to start
        
        # Open browser
        print("\n🌍 Opening dashboard in browser...")
        webbrowser.open("http://localhost:8050")
        
        print("\n" + "=" * 80)
        print("✅ PLATFORM RUNNING!")
        print("=" * 80)
        print()
        print("📌 Services:")
        print("   • Data Ingestion:  Running in background")
        print("   • Analytics Engine: Running (updates every 5s)")
        print("   • Flask API:        http://localhost:5000")
        print("   • Dash Dashboard:   http://localhost:8050")
        print()
        print("💡 Tip: Wait 60 seconds for initial data collection before viewing analytics")
        print()
        print("Press Ctrl+C to stop all services")
        print("=" * 80)
        print()
        
        # Wait for main process
        main_process.wait()
        
    except KeyboardInterrupt:
        print("\n\n🛑 Shutting down platform...")
        
        #  Terminate all processes
        for name, process in processes:
            print(f"   Stopping {name}...")
            process.terminate()
        
        # Wait for clean shutdown
        for name, process in processes:
            process.wait()
        
        print("\n✅ Shutdown complete")
        print("=" * 80)
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
        
        # Cleanup on error
        for name, process in processes:
            process.terminate()


if __name__ == "__main__":
    main()
