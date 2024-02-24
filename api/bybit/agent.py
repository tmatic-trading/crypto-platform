from .http import Send
from collections import OrderedDict
from typing import Union


class Agent:
    def get_active_instruments(self) -> OrderedDict:
        print("---get_active_instruments---")

    def get_user(self) -> Union[dict, None]:
        print("---get_active_instruments---")

    def get_instrument(self):
        print("---get_instrument_data---")

    def get_position(self):
        print("---get_position---")

    def trade_bucketed(self):
        print("---trade_bucketed---")

    def trading_history(
            self, histCount: int, time=None) -> Union[list, None]:
        print("---trading_histor---")