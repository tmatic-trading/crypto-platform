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
        try:
            if usec:
                return datetime.strptime(time[:-1], "%Y-%m-%dT%H:%M:%S.%f")
            else:
                return datetime.strptime(time[:19], "%Y-%m-%dT%H:%M:%S")
        except Exception as e:
            raise e
    else:
        raise TypeError(type(time))


def exceptions_manager(cls):
    for attr in cls.__dict__:
        if callable(getattr(cls, attr)):
            if attr not in ["exit", "Position", "Instrument", "Account"]:
                setattr(cls, attr, exception(getattr(cls, attr)))
    return cls
