from collections import OrderedDict
from typing import Union
#from api.variables import Variables
import logging
from .errors import http_exception

from datetime import datetime
import services as service

from .ws import Bybit


def http_exceptions_manager(cls):
    for attr in cls.__dict__: 
        if callable(getattr(cls, attr)):
            setattr(cls, attr, http_exception(getattr(cls, attr)))
    return cls


@http_exceptions_manager
class Agent(Bybit):
    logger = logging.getLogger(__name__)

    def get_active_instruments(self) -> OrderedDict:
        for category in self.category_list:
            print("---category---", category)
            instrument_info = self.session.get_instruments_info(category=category)      
            for instrument in instrument_info["result"]["list"]:
                Agent.fill_instrument(self, instrument=instrument, category=category)
        for symbol in self.symbol_list:
            if symbol not in self.instruments:
                Agent.logger.error(
                    "Unknown symbol: "
                    + str(symbol)
                    + ". Check the SYMBOLS in the .env.Bitmex file. Perhaps "
                    + "such symbol does not exist"
                )
                Bybit.exit()
                exit(1)
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
        result = self.session.get_uid_wallet_type()
        self.user = result
        id = find_value_by_key(data=result, key="uid")
        if id:
            self.user_id = id
        else:
            self.logNumFatal = 10001
            message = (
                "A user ID was requested from the exchange but was not "
                + "received."
            )
            Agent.logger.error(message)
       

    def get_instrument(self, symbol: tuple) -> None:
        print("___get_instrument_data")
        instrument_info = self.session.get_instruments_info(symbol=symbol[0], category=symbol[1])
        Agent.fill_instrument(self, instrument=instrument_info["result"]["list"][0], category=symbol[1])
 

    def get_position(self):
        print("___get_position")

    def trade_bucketed(self):
        print("___trade_bucketed")

    def trading_history(self, histCount: int, time: datetime):
        time = service(time)
        histCount = min(100, histCount)
        for category in self.category_list:
            self.session.get_executions(category=category, limit=histCount)

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

    def fill_instrument(self, instrument: dict, category: str):
        symbol = (instrument["symbol"], category)
        self.instruments[symbol] = instrument
        if "settleCoin" in instrument:
            self.instruments[symbol]["settlCurrency"] = instrument["settleCoin"]
        if "deliveryTime" in instrument:
            self.instruments[symbol]["expiry"] = instrument["deliveryTime"]
        else:
            self.instruments[symbol]["expiry"] = None
        self.instruments[symbol]["tickSize"] = instrument["priceFilter"]["tickSize"]
        self.instruments[symbol]["lotSize"] = float(instrument["lotSizeFilter"]["minOrderQty"])
        self.instruments[symbol]["state"] = instrument["status"]
        self.instruments[symbol]["multiplier"] = 1
        self.instruments[symbol]["myMultiplier"] = 1



def find_value_by_key(data: dict, key: str) -> Union[str, None]:
    for k, val in data.items():
        if k == key:
            return val
        elif isinstance(val, dict):
            res = find_value_by_key(val, key)
            if res:
                return res
        elif isinstance(val, list):
            for item in val:
                if isinstance(item, dict):
                    res = find_value_by_key(item, key)
                    if res:
                        return res