from collections import OrderedDict
from datetime import datetime
from typing import Any, Iterable, Union

from common.variables import Variables as var


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
    avgEntryPrice: [float, str]
        Average entry price.
    baseCoin: str
        Base coin.
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
            ``future_linear``,
            ``future_reversed`,
            ``future_combo_reversed`,
            ``spot_linear``,
            ``option_linear``,
            ``option_reversed``,
            ``option_combo_reversed``,
    confirm_subscription: set
        Confirmation of successful subscription to the instrument (Bybit
        only).
    currentQty: float
        Position size
    expire: datetime
        Expiration time.
    fundingRate: float
        Funding rate.
    isInverse: bool
        Indicates that the nature of the contract is ``inverse`` or
        ``reversed`` in the case of Deribit.
    makerFee: float
        Maker's commission for instrument.
    marginCallPrice: [float, str]
        Position margin call or liquidation price.
    market: str
        Exchange name.
    markPrice: float
        Defines mark price for the instrument.
    maxOrderQty: float
        Not used
    minOrderQty: float
        Minimum order quantity or lotsize.
    multiplier: int
        :::For Bitmex only::: How much is one contract worth. You can see this
        information under the Bitmex Contract Specifications for each
        instrument. For other exchanges it is equal to 1.
    myMultiplier: int
        :::For Bitmex only::: Converts quantity when displayed on screen.
        For other exchanges it is equal to 1.
    openInterest: float
        Open interest size.
    optionStrike: str
        :::For options only::: The strike value
    optionType: str
        :::For options only::: Option type. CALL, PUT
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
        Taker's commission for instrument.
    ticker: str
        Symbol of the instrument in the exchange classification.
    tickSize: float
        The step to increase/reduce order price.
    unrealisedPnl: [float, str]
        Unrealised PnL.
    volume: float
        The total trading volume on a given account.
    volume24h: float
        Volume for 24h
    valueOfOneContract: float
        :::For Bitmex only::: Used when calculating trade value. For other
        exchanges it is equal to 1.
    """

    asks: list = []
    avgEntryPrice: float = var.DASH
    baseCoin: str
    bids: list = []
    category: str
    confirm_subscription: set
    currentQty: float = 0
    expire: datetime
    fundingRate: float = 0
    isInverse: bool
    makerFee: float = None
    market: str
    markPrice: float = var.DASH
    marginCallPrice: float = var.DASH
    maxOrderQty: float
    minOrderQty: float
    multiplier: int
    myMultiplier: int
    optionStrike: str
    optionType: str
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
    unrealisedPnl: float = var.DASH
    volume: float = 0
    volume24h: float = 0
    valueOfOneContract: float

    openInterest: float = var.DASH
    bidPrice: float = var.DASH
    bidSize: float = var.DASH
    bidIv: float = var.DASH
    askPrice: float = var.DASH
    askSize: float = var.DASH
    askIv: float = var.DASH
    delta: float = var.DASH
    vega: float = var.DASH
    theta: float = var.DASH
    gamma: float = var.DASH
    rho: float = var.DASH

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
    timefr: str
    timefr_sec: int
    timefr_current: str
    bot_pnl: dict
    state: str
    created: str
    updated: str
    error_message: str = ""
    log: list
    backtest_data: dict
    iter: int = 0
    strategy_log: str
    multitrade: str = ""
    block: bool = False

    def __iter__(self):
        return Ret.iter(self)


class MetaInstrument(type):
    market = dict()

    def __getitem__(self, item) -> Instrument:
        name = item[1]

        return self.market[name][item]

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
