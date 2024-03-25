from collections import OrderedDict
from typing import Union
from api.variables import Variables
import logging
from .errors import http_exception

from .init import Init


def http_exceptions_manager(cls):
    for attr in cls.__dict__: 
        if callable(getattr(cls, attr)):
            setattr(cls, attr, http_exception(getattr(cls, attr)))
    return cls


@http_exceptions_manager
class Agent(Variables, Init):
    logger = logging.getLogger(__name__)

    def get_active_instruments(self) -> OrderedDict:
        for category in self.category_list:
            print("---category---", category)
            instrument_info = self.session.get_instruments_info(category=category)            
            for instrument in instrument_info["result"]["list"]:
                symbol = (instrument["symbol"], category)
                self.instruments[symbol] = instrument
                if "settleCoin" in instrument:
                    self.instruments[symbol]["settlCurrency"] = instrument["settleCoin"]
                if "deliveryTime" in instrument:
                    self.instruments[symbol]["expiry"] = instrument["deliveryTime"]
                else:
                    self.instruments[symbol]["expiry"] = None
                self.instruments[symbol]["tickSize"] = instrument["priceFilter"]["tickSize"]
                self.instruments[symbol]["lotSize"] = instrument["lotSizeFilter"]["minOrderQty"]
                self.instruments[symbol]["state"] = instrument["status"]
                self.instruments[symbol]["multiplier"] = 1
                self.instruments[symbol]["myMultiplier"] = 1
            '''if category is not "option":
                tickers = self.session.get_tickers(category=category)
                for ticker in tickers["result"]["list"]:
                    symbol = (ticker["symbol"], category)
                    self.instruments[symbol].update(ticker)
                    self.instruments[symbol]["bidPrice"] = ticker["bid1Price"]
                    self.instruments[symbol]["askPrice"] = ticker["ask1Price"]   '''                 

        return self.instruments

    def get_user(self) -> Union[dict, None]:
        print("___get_user")

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

    #del
    '''def exit(self):
        print("___exit")'''

    def urgent_announcement(self):
        print("___urgent_announcement")

    def place_limit(self):
        print("___place_limit")

    def replace_limit(self):
        print("___replace_limit")

    def remove_order(self):
        print("___remove_order")