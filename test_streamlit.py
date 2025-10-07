import yfinance as yf
df = yf.download("^NSEI", period="5d", interval="5m", progress=False)
print("DF shape:", df.shape)
print(df.head())