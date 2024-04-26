from collections import OrderedDict
from datetime import datetime
from typing import Any, Union


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
    asks: list
    avgEntryPrice: float
    bids: list
    category: str
    currentQty: float
    expire: Union[str, datetime]
    fundingRate: float
    marginCallPrice: Union[str, float]
    maxOrderQty: float
    minOrderQty: float
    multiplier: int
    myMultiplier: int
    precision: int
    price_precision: int
    qtyStep: float
    settlCurrency: str
    state: str
    symbol: str
    tickSize: Union[str, float]
    unrealisedPnl: Union[str, float]
    volume24h: float

    def __iter__(self):
        return Ret.iter(self)


class Account:
    account: Union[str, float]
    availableMargin: float = 0
    marginBalance: float = 0
    orderMargin: float = 0
    positionMagrin: float = 0
    settlCurrency: str
    unrealisedPnl: float = 0
    walletBalance: float = 0

    def __iter__(self):
        return Ret.iter(self)
    
class Result:
    commission: float = 0
    funding: float = 0
    sumreal: float = 0
    result: float = 0

    def __iter__(self):
        return Ret.iter(self)


class MetaInstrument(type):
    all = dict()
    market = dict()

    def __getitem__(self, item) -> Instrument:
        if item not in self.all:
            self.all[item] = Instrument()
            name = item[2]
            if name not in self.market:
                self.market[name] = OrderedDict()
            self.market[name][item] = self.all[item]
            return self.all[item]
        else:
            return self.all[item]

    def keys(self):
        name = self.__qualname__.split(".")[0]
        if name in MetaInstrument.market:
            for symbol in MetaInstrument.market[name]:
                yield symbol

    def get_keys(self):
        name = self.__qualname__.split(".")[0]
        if name in MetaInstrument.market:
            return MetaInstrument.market[name].keys()


class MetaAccount(type):
    all = dict()
    market = dict()

    def __getitem__(self, item) -> Account:
        if item not in self.all:
            self.all[item] = Account()
            name = item[1]
            if name not in self.market:
                self.market[name] = OrderedDict()
            self.market[name][item] = self.all[item]
            return self.all[item]
        else:
            return self.all[item]

    def keys(self):
        name = self.__qualname__.split(".")[0]
        if name in MetaAccount.market:
            for symbol in MetaAccount.market[name]:
                yield symbol

    def get_keys(self):
        name = self.__qualname__.split(".")[0]
        if name in MetaAccount.market:
            return MetaAccount.market[name].keys()
        

class MetaResult(type):
    all = dict()
    market = dict()

    def __getitem__(self, item) -> Result:
        if item not in self.all:
            self.all[item] = Result()
            name = item[1]
            if name not in self.market:
                self.market[name] = OrderedDict()
            self.market[name][item] = self.all[item]
            return self.all[item]
        else:
            return self.all[item]

    def keys(self):
        name = self.__qualname__.split(".")[0]
        if name in MetaResult.market:
            for symbol in MetaResult.market[name]:
                yield symbol

    def get_keys(self):
        name = self.__qualname__.split(".")[0]
        if name in MetaResult.market:
            return MetaResult.market[name].keys()
