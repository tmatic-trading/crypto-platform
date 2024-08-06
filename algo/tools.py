from common.data import MetaInstrument, Instrument
import inspect
import platform


class MetaTool(type):
    objects= dict()
    def __getitem__(self, item) -> Instrument:
        market = self.__qualname__
        instrument = (item, market)
        if instrument not in MetaInstrument.all:
            raise ValueError(f"The instrument {instrument} not found.")
        
        return MetaInstrument.all[instrument]

    def sell(self: Instrument):
        bot_name = get_bot_name(inspect.stack())

    def buy(self: Instrument):
        bot_name = get_bot_name(inspect.stack())
        print(bot_name)

    def EMA(self: Instrument, period):
        print("_____EMA")

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


Instrument.sell = MetaTool.sell
Instrument.buy = MetaTool.buy


class Bitmex(metaclass=MetaTool):
    pass

class Bybit(metaclass=MetaTool):
    pass

class Deribit(metaclass=MetaTool):
    pass


