from collections import OrderedDict
from datetime import datetime
from typing import Union

from api.bitmex.agent import Agent as BitmexAgent
from api.bitmex.ws import Bitmex
from api.bybit.agent import Agent as BybitAgent
from api.bybit.ws import Bybit
from .variables import Variables
from api.init import Setup

from enum import Enum

class MetaMarket(type):
    dictionary = dict()
    names = {"Bitmex": Bitmex, "Bybit": Bybit}
    def __getitem__(self, item) -> Union[Bitmex, Bybit]:        
        if item not in self.names:
            raise ValueError(f"{item} not found")
        if item not in self.dictionary:
            self.dictionary[item] = self.names[item]()
            return self.dictionary[item]
        else:
            return self.dictionary[item]
        

class Markets(Bitmex, Bybit, metaclass=MetaMarket):
    pass


'''class Markets(Variables, Enum):
    Bitmex =  Bitmex()
    Bybit = Bybit()'''

class Agents(Enum):
    Bitmex = BitmexAgent
    Bybit = BybitAgent


class WS(Variables):
    def start_ws(self: Markets) -> None:
        """
        Websockets init
        """
        Agents[self.name].value.get_active_instruments(self)
        Markets[self.name].start()

    def exit(self: Markets) -> None:
        """
        Closes websocket
        """
        Markets[self.name].exit()

    def get_active_instruments(self: Markets) -> OrderedDict:
        """
        Gets all active instruments from the exchange REST API.
        """

        return Agents[self.name].value.get_active_instruments(self)

    def get_user(self: Markets) -> Union[dict, None]:
        """
        Gets account info.
        """

        return Agents[self.name].value.get_user(self)

    def get_instrument(self: Markets, symbol: tuple) -> None:
        """
        Gets a specific instrument by symbol name and category.
        """

        return Agents[self.name].value.get_instrument(self, symbol=symbol)

    def get_position(self: Markets, symbol: tuple) -> None:
        """
        Gets information about an open position for a specific instrument.
        """

        return Agents[self.name].value.get_position(self, symbol=symbol)

    def trade_bucketed(
        self: Markets, symbol: tuple, time: datetime, timeframe: str
    ) -> Union[list, None]:
        """
        Gets timeframe data.
        """

        return Agents[self.name].value.trade_bucketed(
            self, symbol=symbol, time=time, timeframe=timeframe
        )

    def trading_history(self: Markets, histCount: int, time: datetime) -> list:
        """
        Gets all trades and funding from the exchange for the period starting
        from 'time'
        """

        return Agents[self.name].value.trading_history(self, histCount=histCount, time=time)

    def open_orders(self: Markets) -> list:
        """
        Gets open orders.
        """

        return Agents[self.name].value.open_orders(self)

    def urgent_announcement(self: Markets) -> list:
        """
        Public announcements of the exchange
        """

        return Agents[self.name].value.urgent_announcement(self)

    def get_funds(self: Markets) -> list:
        """
        Cash in the account
        """

        return self.data["margin"]

    '''def market_depth(self: Markets) -> list:
        """
        Gets market depth (orderbook), 10 lines deep.
        """

        return self.data["orderBook"]'''

    def place_limit(
        self: Markets, quantity: int, price: float, clOrdID: str, symbol: tuple
    ) -> Union[dict, None]:
        """
        Places a limit order
        """

        return Agents[self.name].value.place_limit(
            self, quantity=quantity, price=price, clOrdID=clOrdID, symbol=symbol
        )

    def replace_limit(
        self: Markets, quantity: int, price: float, orderID: str, symbol: tuple
    ) -> Union[dict, None]:
        """
        Moves a limit order
        """

        return Agents[self.name].value.replace_limit(
            self, quantity=quantity, price=price, orderID=orderID, symbol=symbol
        )

    def remove_order(self: Markets, orderID: str) -> Union[list, None]:
        """
        Deletes an order
        """

        return Agents[self.name].value.remove_order(self, orderID=orderID)
    
    def get_wallet_balance(self: Markets) -> dict:
        """
        Obtain wallet balance, query asset information of each currency, and 
        account risk rate information.
        """

        return Agents[self.name].value.get_wallet_balance(self)
    
    def get_position_info(self: Markets) -> dict:
        """
        Get Position Info
        """

        return Agents[self.name].value.get_position_info(self)