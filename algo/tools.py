import inspect
import platform

from api.api import Markets
from common.data import Bots, Instrument, MetaInstrument


def name(stack) -> str:
    if ostype == "Windows":
        bot_name = stack[1].filename.split("\\")[-2]
    else:
        bot_name = stack[1].filename.split("/")[-2]

    return bot_name


class Tool(Instrument):
    def __init__(self, instrument: Instrument) -> None:
        self.__dict__ = instrument.__dict__.copy()
        self.instrument = instrument
        self.market = self.instrument.market
        self.bot_name = ""

    def close_all(self):
        bot_name = name(inspect.stack())
        pass

    def sell(self):
        bot_name = name(inspect.stack())

    def buy(self):
        bot_name = name(inspect.stack())

    def EMA(self, period: int):
        pass

    def add_kline(self):
        bot_name = name(inspect.stack())
        Bots[bot_name].timefr
        ws = Markets[self.market]
        ws.kline_list.append(
            {
                "symbol": self.instrument.symbol,
                "bot_name": bot_name,
                "timefr": Bots[bot_name].timefr,
            }
        )


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
