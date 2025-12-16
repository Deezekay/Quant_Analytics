import sqlite3

conn = sqlite3.connect('data/crypto_analytics.db')
c = conn.cursor()

print("Ticks by symbol:")
c.execute('SELECT symbol, COUNT(*) FROM ticks GROUP BY symbol')
for row in c.fetchall():
    print(f'  {row[0]}: {row[1]:,}')

print("\nOHLC bars by interval:")
c.execute('SELECT interval, COUNT(*) FROM ohlc GROUP BY interval')
for row in c.fetchall():
    print(f'  {row[0]}: {row[1]:,}')

print("\nSample 1s OHLC bar:")
c.execute('SELECT * FROM ohl c LIMIT 1')
row = c.fetchone()
if row:
    print(f'  Symbol: {row[0]}')
    print(f'  Interval: {row[1]}')
    print(f'  Time: {row[2]}')
    print(f'  Open: ${row[3]:.2f}, High: ${row[4]:.2f}, Low: ${row[5]:.2f}, Close: ${row[6]:.2f}')
    print(f'  Volume: {row[7]:.6f}, Trades: {row[8]}')

conn.close()
