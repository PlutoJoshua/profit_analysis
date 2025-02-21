import pandas as pd

df = pd.read_csv('../usd.csv', index_col=0)

print(df.head())