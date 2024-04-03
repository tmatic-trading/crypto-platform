from datetime import datetime
from typing import Union
from api.bybit.errors import exception
from api.variables import Variables


def ticksize_rounding(price: float, ticksize: float) -> float:
    """
    Rounds the price depending on the tickSize value
    """
    arg = 1 / ticksize
    res = round(price * arg, 0) / arg

    return res


def time_converter(time: Union[int, float, str, datetime], usec=False) -> Union[datetime, int]:
    if isinstance(time, int) or isinstance(time, float):
        return datetime.fromtimestamp(time)
    elif isinstance(time, datetime):
        return int(time.timestamp())
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
            if attr not in ["exit", "Position", "Instrument"]:
                setattr(cls, attr, exception(getattr(cls, attr)))
    return cls


def fill_ticker(self: Variables, depth: str, data: dict):
    if depth in data:
        for symbol, val in data[depth].items():
            if depth == "quote":
                if "bidPrice" in val:
                    self.ticker[symbol]["bid"] = float(val["bidPrice"])
                    self.ticker[symbol]["bidSize"] = float(val["bidSize"])
                if "askPrice" in val:
                    self.ticker[symbol]["ask"] = float(val["askPrice"])
                    self.ticker[symbol]["askSize"] = float(val["askSize"])
            else:
                if val["bids"]:
                    self.ticker[symbol]["bid"] = float(val["bids"][0][0])
                    self.ticker[symbol]["bidSize"] = float(val["bids"][0][1])
                if val["asks"]:
                    self.ticker[symbol]["ask"] = float(val["asks"][0][0])
                    self.ticker[symbol]["askSize"] = float(val["asks"][0][1])

    return self.ticker