from datetime import datetime
from typing import Union

from api.bybit.errors import exception


def ticksize_rounding(price: float, ticksize: float) -> float:
    """
    Rounds the price depending on the tickSize value
    """
    arg = 1 / ticksize
    res = round(price * arg, 0) / arg

    return res


def time_converter(
    time: Union[int, float, str, datetime], usec=False
) -> Union[datetime, int]:
    if isinstance(time, int) or isinstance(time, float):
        return datetime.fromtimestamp(time)
    elif isinstance(time, datetime):
        return int(time.timestamp() * 1000)
    elif isinstance(time, str):
        time = time.replace("T", " ")
        time = time.replace("Z", "")
        if usec:
            try:
                return datetime.strptime(time, "%Y-%m-%d %H:%M:%S.%f")
            except:
                return datetime.strptime(time, "%Y-%m-%d %H:%M:%S")
        else:
            return datetime.strptime(time[:19], "%Y-%m-%d %H:%M:%S")
    else:
        raise TypeError(type(time))


def exceptions_manager(cls):
    for attr in cls.__dict__:
        if callable(getattr(cls, attr)):
            if attr not in ["exit", "Position", "Instrument", "Account"]:
                setattr(cls, attr, exception(getattr(cls, attr)))
    return cls


def precision(qty: float) -> int:
    r = str(qty)
    if "e" in r:
        r = r.replace("e", "")
        r = r.replace(".", "")
        r = r.split("-")
        precision = len(r[0]) - 1 + int(r[1])
    elif "." in r:
        r = r.split(".")
        if int(r[1]) == 0:
            precision = 0
        else:
            precision = len(r[1])
    else:
        precision = 0

    return precision
