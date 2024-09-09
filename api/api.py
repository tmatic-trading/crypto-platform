import threading
from collections import OrderedDict
from datetime import datetime, timezone
from enum import Enum
from typing import Union

from api.bitmex.agent import Agent as BitmexAgent
from api.bitmex.ws import Bitmex
from api.bybit.agent import Agent as BybitAgent
from api.bybit.ws import Bybit
from api.deribit.agent import Agent as DeribitAgent
from api.deribit.ws import Deribit
from api.fake import Fake
from common.variables import Variables as var
from services import display_exception

from .variables import Variables


class MetaMarket(type):
    dictionary = dict()
    names = {"Bitmex": Bitmex, "Bybit": Bybit, "Deribit": Deribit}

    def __getitem__(self, item) -> Union[Bitmex, Bybit, Deribit]:
        if item not in self.dictionary:
            if item != "Fake":
                try:
                    self.dictionary[item] = self.names[item]()
                except ValueError:
                    raise ValueError(f"{item} not found")
            elif item == "Fake":
                self.dictionary[item] = Fake()
            return self.dictionary[item]
        else:
            return self.dictionary[item]


class Markets(Bitmex, Bybit, Deribit, metaclass=MetaMarket):
    pass


class Agents(Enum):
    Bitmex = BitmexAgent
    Bybit = BybitAgent
    Deribit = DeribitAgent


class WS(Variables):
    def start_ws(self: Markets) -> None:
        """
        Loading instruments, orders, user ID, wallet balance, position
        information and initializing websockets.
        """

        def start_ws_in_thread():
            try:
                Markets[self.name].start()
            except Exception as exception:
                display_exception(exception)
                # self.logNumFatal = "SETUP"

        def get_in_thread(method):
            try:
                method(self)
            except Exception as exception:
                display_exception(exception)
                # self.logNumFatal = "SETUP"

        try:
            if WS.get_active_instruments(self):
                return self.logNumFatal
        except Exception as exception:
            display_exception(exception)
            self.logger.error(self.name + " Instruments not loaded. Reboot.")
            return self.logNumFatal
        try:
            Agents[self.name].value.activate_funding_thread(self)
        except:
            display_exception(exception)
            self.logger.error(self.name + " Error calling activate_funding_thread().")
            return self.logNumFatal
        self.logNumFatal = ""
        try:
            if WS.open_orders(self):
                return self.logNumFatal
        except Exception as exception:
            display_exception(exception)
            self.logger.error(self.name + " Orders not loaded. Reboot.")
            return self.logNumFatal
        try:
            threads = []
            t = threading.Thread(target=start_ws_in_thread)
            threads.append(t)
            t.start()
            t = threading.Thread(target=get_in_thread, args=(WS.get_user,))
            threads.append(t)
            t.start()
            t = threading.Thread(target=get_in_thread, args=(WS.get_wallet_balance,))
            threads.append(t)
            t.start()
            t = threading.Thread(target=get_in_thread, args=(WS.get_position_info,))
            threads.append(t)
            t.start()
            [thread.join() for thread in threads]
        except Exception as exception:
            display_exception(exception)
            # self.logNumFatal = "SETUP"
        if self.logNumFatal:
            if self.logNumFatal == "FATAL":
                self.logger.error(
                    self.name
                    + ": The websocket is not running, or the user "
                    + "information, wallet balance or position information "
                    + "is not loaded. Reboot."
                )
            return self.logNumFatal
        var.queue_info.put(
            {
                "market": self.name,
                "message": "Connected to websocket.",
                "time": datetime.now(tz=timezone.utc),
                "warning": None,
            }
        )

        return ""

    def exit(self: Markets) -> None:
        """
        Closes websocket
        """
        Markets[self.name].exit()

    def get_active_instruments(self: Markets) -> int:
        """
        Gets all active instruments from the exchange REST API.
        """
        var.logger.info(self.name + " - Requesting all active instruments.")

        return Agents[self.name].value.get_active_instruments(self)

    def get_user(self: Markets) -> Union[dict, None]:
        """
        Gets account info.
        """
        var.logger.info(self.name + " - Requesting user information.")

        return Agents[self.name].value.get_user(self)

    def get_instrument(self: Markets, ticker: str, category: str) -> None:
        """
        Gets a specific instrument by symbol name and category.
        """
        var.logger.info(
            self.name
            + " - Requesting instrument - ticker="
            + ticker
            + ", category="
            + category
        )

        return Agents[self.name].value.get_instrument(
            self, ticker=ticker, category=category
        )

    def get_position(self: Markets, symbol: tuple) -> None:
        """
        Gets information about an open position for a specific instrument.
        """

        return Agents[self.name].value.get_position(self, symbol=symbol)

    def trade_bucketed(
        self: Markets, symbol: tuple, time: datetime, timeframe: str
    ) -> Union[list, None]:
        """
        Gets kline data.
        """
        parameters = (
            f"symbol={symbol[0]}" + f", start_time={time}" + f", timeframe={timeframe}"
        )
        var.logger.info(self.name + " - Requesting kline data - " + parameters)
        data = Agents[self.name].value.trade_bucketed(
            self, symbol=symbol, start_time=time, timeframe=timeframe
        )
        if data:
            var.logger.info(
                self.name
                + " - Klines - "
                + parameters
                + f", received {len(data)} records."
            )

        return data

    def trading_history(self: Markets, histCount: int, start_time: datetime) -> list:
        """
        Gets all trades and funding from the exchange for the period starting
        from 'time'
        """
        var.logger.info(
            self.name + " - Requesting trading history - start_time=" + str(start_time)
        )

        return Agents[self.name].value.trading_history(
            self, histCount=histCount, start_time=start_time
        )

    def open_orders(self: Markets) -> list:
        """
        Gets open orders.
        """
        var.logger.info(self.name + " - Requesting open orders.")

        return Agents[self.name].value.open_orders(self)

    def place_limit(
        self: Markets, quantity: float, price: float, clOrdID: str, symbol: tuple
    ) -> Union[dict, None]:
        """
        Places a limit order
        """
        var.logger.info(
            self.name
            + " - Order - New - "
            + "symbol="
            + symbol[0]
            + ", qty="
            + str(quantity)
            + ", price="
            + str(price)
            + ", clOrdID="
            + clOrdID
        )

        return Agents[self.name].value.place_limit(
            self, quantity=quantity, price=price, clOrdID=clOrdID, symbol=symbol
        )

    def replace_limit(
        self: Markets, quantity: float, price: float, orderID: str, symbol: tuple
    ) -> Union[dict, None]:
        """
        Moves a limit order
        """
        var.logger.info(
            self.name
            + " - Order - Replace - "
            + "symbol="
            + symbol[0]
            + ", qty="
            + str(quantity)
            + ", price="
            + str(price)
            + ", orderID="
            + orderID
        )

        return Agents[self.name].value.replace_limit(
            self, quantity=quantity, price=price, orderID=orderID, symbol=symbol
        )

    def remove_order(self: Markets, order: dict) -> Union[list, None]:
        """
        Deletes an order
        """
        var.logger.info(
            self.name
            + " - Order - Cancel - "
            + "symbol="
            + order["symbol"][0]
            + ", orderID="
            + order["orderID"]
        )

        return Agents[self.name].value.remove_order(self, order=order)

    def get_wallet_balance(self: Markets) -> dict:
        """
        Obtain wallet balance, query asset information of each currency, and
        account risk rate information.
        """
        var.logger.info(self.name + " - Requesting account.")

        return Agents[self.name].value.get_wallet_balance(self)

    def get_position_info(self: Markets) -> dict:
        """
        Get position information.
        """
        var.logger.info(self.name + " - Requesting positions.")

        return Agents[self.name].value.get_position_info(self)

    def ping_pong(self: Markets) -> None:
        """
        Check if websocket is working
        """

        return Markets[self.name].ping_pong()
