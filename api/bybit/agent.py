from .http import Send
from collections import OrderedDict
from typing import Union


class Agent:
    def get_active_instruments(self) -> OrderedDict:
        print("___get_active_instruments")

    def get_user(self) -> Union[dict, None]:
        print("___get_active_instruments")

    def get_instrument(self):
        print("___get_instrument_data")

    def get_position(self):
        print("___get_position")

    def trade_bucketed(self):
        print("___trade_bucketed")

    def trading_history(
            self, histCount: int, time=None) -> Union[list, None]:
        print("___trading_histor")

    def open_orders(self) -> list:
        print("___open_orders")

    def get_ticker(self) -> OrderedDict:
        print("___get_ticker")

    def exit(self):
        print("___exit")