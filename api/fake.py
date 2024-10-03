from api.variables import Variables
from common.data import MetaAccount, MetaInstrument, MetaResult
from collections import OrderedDict


class Fake(Variables):
    class Account(metaclass=MetaAccount):
        pass

    class Instrument(metaclass=MetaInstrument):
        pass

    class Result(metaclass=MetaResult):
        pass

    def __init__(self):
        self.name = "Fake"
        self.symbol_list = ["BTCUSDT"]
        self.instrument_index = OrderedDict()

    def exit(self):
        pass
