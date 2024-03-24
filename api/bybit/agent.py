from collections import OrderedDict
from typing import Union
from api.variables import Variables
import logging
from .errors import exceptions_manager

from .init import Init


def http_exceptions_manager(cls):
    for attr in cls.__dict__: 
        if callable(getattr(cls, attr)):
            setattr(cls, attr, exceptions_manager(getattr(cls, attr)))
    return cls


@http_exceptions_manager
class Agent(Variables, Init):
    logger = logging.getLogger(__name__)

    def get_active_instruments(self) -> OrderedDict: 
        result = self.session.get_instruments_info(category="linear")["result"]["list"]

    def get_user(self) -> Union[dict, None]:
        print("___get_active_instruments")

    def get_instrument(self):
        print("___get_instrument_data")

    def get_position(self):
        print("___get_position")

    def trade_bucketed(self):
        print("___trade_bucketed")

    def trading_history(self):
        print("___trading_histor")

    def open_orders(self) -> list:
        print("___open_orders")

    def get_ticker(self) -> OrderedDict:
        print("___get_ticker")

    def exit(self):
        print("___exit")

    def urgent_announcement(self):
        print("___urgent_announcement")

    def place_limit(self):
        print("___place_limit")

    def replace_limit(self):
        print("___replace_limit")

    def remove_order(self):
        print("___remove_order")