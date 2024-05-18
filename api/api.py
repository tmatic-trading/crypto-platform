import threading
from collections import OrderedDict
from datetime import datetime, timezone
from enum import Enum
from typing import Union

from api.bitmex.agent import Agent as BitmexAgent
from api.bitmex.ws import Bitmex
from api.bybit.agent import Agent as BybitAgent
from api.bybit.ws import Bybit
from common.variables import Variables as var

from .variables import Variables


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


class Agents(Enum):
    Bitmex = BitmexAgent
    Bybit = BybitAgent


class WS(Variables):
    def start_ws(self: Markets) -> None:
        """
        Websockets init
        """

        def start_ws_in_thread():
            Markets[self.name].start()

        def get_in_thread(method):
            method(self)

        Agents[self.name].value.get_active_instruments(self)
        threads = []
        t = threading.Thread(target=start_ws_in_thread)
        threads.append(t)
        t.start()
        t = threading.Thread(
            target=get_in_thread, args=(Agents[self.name].value.get_user,)
        )
        threads.append(t)
        t.start()
        t = threading.Thread(
            target=get_in_thread, args=(Agents[self.name].value.get_wallet_balance,)
        )
        threads.append(t)
        t.start()
        t = threading.Thread(
            target=get_in_thread, args=(Agents[self.name].value.get_position_info,)
        )
        threads.append(t)
        t.start()
        [thread.join() for thread in threads]
        if self.logNumFatal == 0:
            var.info_queue.put(
                {
                    "market": self.name,
                    "message": "Connected to websocket.",
                    "time": datetime.now(tz=timezone.utc),
                    "warning": False,
                }
            )

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

        return Agents[self.name].value.trading_history(
            self, histCount=histCount, time=time
        )

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

    def remove_order(self: Markets, order: dict) -> Union[list, None]:
        """
        Deletes an order
        """

        return Agents[self.name].value.remove_order(self, order=order)

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
