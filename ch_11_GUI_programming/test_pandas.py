import polars as pl
 
(transactions
 .group_by("CUST_ID")
 .agg(pl.col("AMOUNT").sum())
 .sort(by="AMOUNT", descending=True)
 .head()
 .collect(engine="gpu"))