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

    def close_all(self) -> None:
        bot_name = name(inspect.stack())
        pass

    def sell(self) -> None:
        bot_name = name(inspect.stack())

    def buy(self) -> None:
        bot_name = name(inspect.stack())

    def EMA(self, period: int) -> float:
        pass

    def add_kline(self) -> None:
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

    def kline(self, period: int = -1) -> dict:
        ws = Markets[self.market]
        print("___________________", ws.name)
        print(ws.klines)


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


class Bot:
    def __init__(self) -> None:
        bot_name = name(inspect.stack())
        bot = Bots[bot_name]
        self.name = bot.name
        self.position = bot.position
        self.timefr = bot.timefr
        self.pnl = bot.pnl
        self.state = bot.state
        self.created = bot.created
        self.updated = bot.updated
        self.error_message = bot.error_message
