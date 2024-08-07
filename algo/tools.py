import inspect
import platform

from api.api import Markets
from common.data import Instrument, MetaInstrument


def insert_bot_name(func):
    def inner(self):
        self.bot_name = get_bot_name(inspect.stack())
        func(self)

    return inner


class Tool(Instrument):
    def __init__(self, instrument: Instrument) -> None:
        self.__dict__ = instrument.__dict__.copy()
        self.instrument = instrument
        self.market = self.instrument.market
        self.bot_name = ""

    @insert_bot_name
    def close_all(self):
        pass

    @insert_bot_name
    def sell(self):
        pass

    @insert_bot_name
    def buy(self):
        pass

    def EMA(self, period: int):
        pass
    
    @insert_bot_name
    def add_kline(self):
        ws = Markets[self.market]
        ws.kline_list.append(self.instrument.symbol)


class MetaTool(type):
    objects = dict()

    def __getitem__(self, item) -> Tool:
        market = self.__qualname__
        instrument = (item, market)
        if instrument not in MetaInstrument.all:
            raise ValueError(f"The instrument {instrument} not found.")
        if instrument not in self.objects:
            self.objects[instrument] = Tool(MetaInstrument.all[instrument])

        return self.objects[instrument]


def get_bot_name(stack) -> str:
    if ostype == "Windows":
        bot_name = stack[1].filename.split("\\")[-2]
    else:
        bot_name = stack[1].filename.split("/")[-2]

    return bot_name


if platform.system() == "Windows":
    ostype = "Windows"
elif platform.system() == "Darwin":
    ostype = "Mac"
else:
    ostype = "Linux"


class Bitmex(metaclass=MetaTool):
    pass


class Bybit(metaclass=MetaTool):
    pass


class Deribit(metaclass=MetaTool):
    pass
