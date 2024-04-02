from typing import Any, Union
from datetime import datetime


class Ret:
    name: str
    value: Any

    def iter(self):
        for attr in dir(self):
            if not attr.startswith("__"):
                Ret.name = attr
                Ret.value = getattr(self, attr)
                yield Ret


class Instrument:
    askPrice: Union[str, float]
    bidPrice: Union[str, float]
    category: str
    expire: str
    fundingRate: Union[str, float]
    minOrderQty: Union[str, float]
    multiplier: int
    myMultiplier: int
    precision: int
    settlCurrency: str
    state: str
    symbol: str 
    tickSize: Union[str, float]
    volume24h: Union[str, float]   

    def __iter__(self):
        return Ret.iter(self)
    

class Position:
    avgEntryPrice: Union[str, float]
    category: str
    currentQty: Union[str, float]
    expire: str
    fundingRate: Union[str, float]
    marginCallPrice: Union[str, float]
    state: str
    symbol: str
    unrealisedPnl: Union[str, float]
    volume24h: Union[str, float] 

    def __iter__(self):
        return Ret.iter(self)
    

class Meta(type):
    dictionary = dict()
    names = {
        "Instrument": Instrument,
        "Position": Position,        
    }
    def __getitem__(self, item) -> Union[Position, Instrument]:
        key = item + (self,)
        if key not in self.dictionary:
            self.dictionary[key] = self.names[self.__name__]()
            return self.dictionary[key]
        else:
            return self.dictionary[key]