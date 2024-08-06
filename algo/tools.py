import inspect
import platform

from api.api import Markets
from common.data import Instrument, MetaInstrument


class Tool(Instrument):
    def __init__(self, instrument) -> None:
        self.__dict__ = instrument.__dict__.copy()
        self.instrument = instrument

    def close_all(self):
        bot_name = get_bot_name(inspect.stack())

    def sell(self):
        bot_name = get_bot_name(inspect.stack())

    def buy(self):
        bot_name = get_bot_name(inspect.stack())

    def EMA(self, period):
        pass

    def add_kline(self):
        ws = Markets[self.market]
        ws.kline_list.append(self.symbol)


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
