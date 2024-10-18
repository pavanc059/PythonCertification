from datetime import datetime, timedelta
from pytz import timezone
t = datetime.now(timezone('US/Eastern')) - timedelta(1)
file_suffix = f"_D{t.year}{t.month:02d}{t.day:02d}.txt"
print(file_suffix)