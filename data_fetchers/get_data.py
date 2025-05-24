import yfinance as yf
import pandas as pd

# Download S&P 500 data from 1975 to today
ticker = '^GSPC'
data = yf.download(ticker, start='1982-04-20')

# Keep only Open and Close columns
data = data[['Open', 'Close']]

# Save to CSV
data.to_csv('sp500_open_close_1982_2025.csv')

print("CSV saved successfully.")