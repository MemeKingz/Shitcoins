import time
from datetime import datetime


def datetime_from_utc_to_local(utc_datetime: datetime):
    now_timestamp = time.time()
    offset = datetime.fromtimestamp(now_timestamp) - datetime.utcfromtimestamp(now_timestamp)
    return utc_datetime + offset