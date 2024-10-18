from collections import OrderedDict
from datetime import datetime
from typing import Any, Iterable, Union


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
    """
    Stores data for each instrument.

    Parameters
    -----------
    asks: list
        Asks. The elements are sorted by price in ascending order. There can
        only be one element if the ORDER_BOOK_DEPTH in the .env file is
        defined as ``quote``.
    avgEntryPrice: float
        Average entry price
    baseCoin: str
        Base coin
    bids: list
        Bids. The element is sorted by price in descending order. There can
        only be one element if the ORDER_BOOK_DEPTH in the .env file is
        defined as ``quote``.
    category: str
        Possible categories:
        Bitmex:
            ``inverse``.
            ``quanto``,
            ``linear``,
            ``spot``,
            ``option``,
        Bybit:
            ``inverse``,
            ``linear``,
            ``option``,
            ``spot``,
        Deribt:
            ``future linear``,
            ``future reversed`,
            ``future_combo reversed`,
            ``spot linear``,
            ``option linear``,
            ``option reversed``,
            ``option_combo reversed``,
    confirm_subscription: set
        Confirmation of successful subscription to the instrument (Bybit
        only).
    currentQty: float
        Position size
    expire: datetime
        Expiration time.
    fundingRate: float
        Funding rate.
    makerFee: float
        Taker commission for instrument.
    marginCallPrice: float
        Position margin call or liquidation price.
    market: str
        Exchange name.
    maxOrderQty: float
        Not used
    minOrderQty: float
        Minimum order quantity or lotsize
    multiplier: int
        :::For Bitmex only::: How much is one contract worth? You can see this
        information under the Bitmex Contract Specifications for each
        instrument. For other exchanges it is equal to 1.
    myMultiplier: int
        :::For Bitmex only::: Converts quantity when displayed on screen.
        For other exchanges it is equal to 1.
    openInterest: float
        Open interest size.
    precision: int
        Based on the ``lotSize`` of the instrument. Used to round volumes
        ​​when displayed on the screen.
    price_precision: int
        Based on the ``tickSize`` of the instrument. Used to round prices
        ​​when displayed on the screen.
    qtyStep: float
        The step to increase/reduce order quantity. Also called LotSize.
    quoteCoin: str
        Quote coin.
    settlCurrency: tuple
        Settlement currency of the instrument.
    state: str
        Instrument status. Normally "Open".
    sumreal: float
        Accumulated trading value.
    symbol: str
        A unique value corresponding to the ticker, except in the spot
        category, where the symbol matches "baseCoin/quoteCoin".
    takerFee: float
        Taker commission for instrument.
    ticker: str
        Symbol of the instrument in the exchange classification.
    tickSize: float
        The step to increase/reduce order price.
    unrealisedPnl: float
        Unrealised PnL.
    volume: float
        The total trading volume on a given account.
    volume24h: float
        Volume for 24h
    valueOfOneContract: float
        :::For Bitmex only::: Used when calculating trade value. For other
        exchanges it is equal to 1.
    """

    asks: list
    avgEntryPrice: float = 0
    baseCoin: str
    bids: list
    category: str
    confirm_subscription: set
    currentQty: float = 0
    expire: datetime
    fundingRate: float = 0
    makerFee: float = None
    market: str
    marginCallPrice: float = 0
    maxOrderQty: float
    minOrderQty: float
    multiplier: int
    myMultiplier: int
    precision: int
    price_precision: int
    qtyStep: float
    quoteCoin: str
    settlCurrency: tuple
    sumreal: float = 0
    state: str
    symbol: str
    takerFee: float = None
    ticker: str
    tickSize: float
    unrealisedPnl: float = 0
    volume: float = 0
    volume24h: float = 0
    valueOfOneContract: float

    openInterest: float = "-"
    bidPrice: float = "-"
    bidSize: float = "-"
    bidIv: float = "-"
    askPrice: float = "-"
    askSize: float = "-"
    askIv: float = "-"
    markPrice: float = "-"
    delta: float = "-"
    vega: float = "-"
    theta: float = "-"
    gamma: float = "-"
    rho: float = "-"
    change24h: float = "-"
    markPrice: float = "-"

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
    limits: dict

    def __iter__(self):
        return Ret.iter(self)


class Result:
    commission: float = 0
    funding: float = 0
    sumreal: float = 0
    result: float = 0

    def __iter__(self):
        return Ret.iter(self)


class BotData:
    name: str
    bot_positions: dict = dict()
    bot_orders: OrderedDict
    timefr: str
    timefr_sec: int
    timefr_current: str
    pnl: dict = dict()
    state: str
    created: str
    updated: str
    error_message: str = ""
    log: list

    def __iter__(self):
        return Ret.iter(self)


class MetaInstrument(type):
    # all = dict()
    market = dict()

    def __getitem__(self, item) -> Instrument:
        name = item[1]
        '''if name not in self.market:
            self.market[name] = OrderedDict()
        if item not in self.market[name]:
            self.market[name][item] = Instrument()'''
        return self.market[name][item]




        '''if item not in self.all:
            self.all[item] = Instrument()
            name = item[1]          
            if name not in self.market:
                self.market[name] = OrderedDict()
            self.market[name][item] = self.all[item]
        return self.all[item]'''

    '''def __getitem__(self, item) -> Instrument:
        if item not in self.all:
            self.all[item] = Instrument()
            name = item[1]
            if name not in self.market:
                self.market[name] = OrderedDict()
            self.market[name][item] = self.all[item]
        return self.all[item]'''
    
    def add(self, item) -> Instrument:
        name = item[1]
        if name not in self.market:
            self.market[name] = OrderedDict()
        if item not in self.market[name]:
            self.market[name][item] = Instrument()

        return self.market[name][item]

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

    def keys(self):
        name = self.__qualname__.split(".")[0]
        if name in MetaResult.market:
            for symbol in MetaResult.market[name]:
                yield symbol

    def get_keys(self):
        name = self.__qualname__.split(".")[0]
        if name in MetaResult.market:
            return MetaResult.market[name].keys()


class MetaBot(type):
    all = OrderedDict()

    def __getitem__(self, item) -> BotData:
        if item not in self.all:
            self.all[item] = BotData()
        return self.all[item]

    def items(self) -> Iterable[tuple[str, BotData]]:
        for name, values in MetaBot.all.items():
            yield name, values

    def keys(self):
        return MetaBot.all.keys()

    def remove(self, item):
        del self.all[item]


class Bots(metaclass=MetaBot):
    pass
