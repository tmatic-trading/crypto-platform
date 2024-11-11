import threading
from collections import OrderedDict
from datetime import datetime, timezone
from enum import Enum
from typing import Union

import services as service
from api.bitmex.agent import Agent as BitmexAgent
from api.bitmex.ws import Bitmex
from api.bybit.agent import Agent as BybitAgent
from api.bybit.ws import Bybit
from api.deribit.agent import Agent as DeribitAgent
from api.deribit.ws import Deribit
from api.fake import Fake
from common.variables import Variables as var

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
    def start_ws(self: Markets) -> str:
        """
        Loading instruments, orders, user ID, wallet balance, position
        information and initializing websockets.

        Returns
        -------
        str
            On success, "" is returned, otherwise an error type or error message.
        """

        """def start_ws_in_thread():
            try:
                Markets[self.name].start()
            except Exception as exception:
                service.display_exception(exception)"""

        def get_in_thread(method):
            method_name = method.__name__
            try:
                error = method(self)
                if error:
                    success[method_name] = error
                else:
                    success[method_name] = ""  # success

            except Exception as exception:
                service.display_exception(exception)

        def get_instruments(_thread):
            try:
                error = WS.get_active_instruments(self)
                if error:
                    success[_thread] = error
                    return
            except Exception as exception:
                service.display_exception(exception)
                message = self.name + " Instruments not loaded."
                self.logger.error(message)
                error = service.unexpected_error(self)
                success[_thread] = error

        def start_ws_in_thread(_thread):
            try:
                error = Markets[self.name].start_ws()
                if error:
                    success[_thread] = error
            except Exception as exception:
                service.display_exception(exception)
                success[_thread] = "FATAL"

        def setup_streams(_thread):
            error = Markets[self.name].setup_streams()
            if not error:
                success[_thread] = error

        # It starts here.

        threads = []
        success = {}
        success["get_active_instruments"] = ""
        t = threading.Thread(target=get_instruments, args=("get_active_instruments",))
        threads.append(t)
        t.start()
        success["start_ws"] = ""
        t = threading.Thread(target=start_ws_in_thread, args=("start_ws",))
        threads.append(t)
        t.start()

        [thread.join() for thread in threads]

        for method_name, error in success.items():
            if error:
                self.logger.error(
                    self.name + ": error occurred while loading " + method_name
                )
                return error
        try:
            Agents[self.name].value.activate_funding_thread(self)
        except:
            service.display_exception(exception)
            message = self.name + " Error calling activate_funding_thread()."
            self.logger.error(message)
            return message
        try:
            error = WS.open_orders(self)
            if error:
                return error
        except Exception as exception:
            service.display_exception(exception)
            self.logger.error(self.name + " Orders not loaded. Reboot.")
            return service.unexpected_error(self)
        threads = []
        success = {}
        try:
            success["setup_streams"] = "FATAL"
            t = threading.Thread(target=setup_streams, args=("setup_streams",))
            threads.append(t)
            t.start()
            success["get_user"] = "FATAL"
            t = threading.Thread(target=get_in_thread, args=(WS.get_user,))
            threads.append(t)
            t.start()
            success["get_wallet_balance"] = "FATAL"
            t = threading.Thread(target=get_in_thread, args=(WS.get_wallet_balance,))
            threads.append(t)
            t.start()
            success["get_position_info"] = "FATAL"
            t = threading.Thread(target=get_in_thread, args=(WS.get_position_info,))
            threads.append(t)
            t.start()
            [thread.join() for thread in threads]
        except Exception as exception:
            service.display_exception(exception)
            return "FATAL"

        for method_name, error in success.items():
            if error:
                self.logger.error(
                    self.name + ": error occurred while loading " + method_name
                )
                return error
        if self.logNumFatal:
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
        Closes websocket.
        """
        Markets[self.name].exit()

    def get_active_instruments(self: Markets) -> str:
        """
        Gets all active instruments from the exchange. This data stores in
        the self.Instrument[<symbol>].

        Returns
        -------
        str
            On success, "" is returned, otherwise an error type, such as
            FATAL, CANCEL.
        """
        WS._put_message(self, message="Requesting all active instruments.")

        return Agents[self.name].value.get_active_instruments(self)

    def get_user(self: Markets) -> str:
        """
        Gets account info. It turns out user_id, which is the account number.
        It can receive other information. Depends on the specific exchange.

        Returns
        -------
        str
            On success, "" is returned, otherwise an error type, such as
            FATAL, CANCEL.
        """
        WS._put_message(self, message="Requesting user information.")

        return Agents[self.name].value.get_user(self)

    def get_instrument(self: Markets, ticker: str, category: str) -> str:
        """
        Gets a specific instrument by symbol. Fills the
        self.Instrument[<symbol>] array with data.

        Parameters
        ----------
        self: Markets
            Markets class instances such as Bitmex, Bybit, Deribit.
        ticker: str
            The name of the instrument in the classification of a specific
            exchange.
        category:
            The category of the instrument such as linear, inverse etc.

        Returns
        -------
        str
            On success, "" is returned, otherwise an error type, such as
            FATAL, CANCEL.
        """
        message = "Requesting instrument - ticker=" + ticker + ", category=" + category
        WS._put_message(self, message=message)

        return Agents[self.name].value.get_instrument(
            self, ticker=ticker, category=category
        )

    def get_position(self: Markets, symbol: tuple) -> None:
        """
        Gets information about an open position for a specific instrument.
        Currently not in use.
        """

        return Agents[self.name].value.get_position(self, symbol=symbol)

    def trade_bucketed(
        self: Markets, symbol: tuple, time: datetime, timeframe: str
    ) -> Union[list, str]:
        """
        Gets kline data.

        Parameters
        ----------
        self: Markets
            Markets class instances such as Bitmex, Bybit, Deribit.
        symbol: tuple
            Instrument symbol. Example ("BTCUSDT", "Bybit").
        start_time: datetime
            Initial time to download timeframe data.
        timeframe: str
            Time interval.

        Returns
        -------
        str | None
            On success, list is returned, otherwise error type.
        """
        parameters = (
            f"symbol={symbol[0]}" + f", start_time={time}" + f", timeframe={timeframe}"
        )
        message = "Requesting kline data - " + parameters
        WS._put_message(self, message=message)
        data = Agents[self.name].value.trade_bucketed(
            self, symbol=symbol, start_time=time, timeframe=timeframe
        )
        if data:
            message = (
                "Klines - " + parameters + ", received " + str(len(data)) + " records."
            )
            WS._put_message(self, message=message)

        return data

    def trading_history(
        self: Markets, histCount: int, start_time: datetime
    ) -> Union[list, str]:
        """
        Gets trades, funding and delivery from the exchange for the period starting
        from start_time.

        Parameters
        ----------
        self: Markets
            Markets class instances such as Bitmex, Bybit, Deribit.
        histCount: int
            The number of rows of data to retrieve.
        start_time: datetime
            Initial time to download data.

        Returns
        -------
        list
            On success, list is returned, otherwise error type.
        """
        message = "Request for trading history since " + str(start_time)
        WS._put_message(self, message=message)
        res = Agents[self.name].value.trading_history(
            self, histCount=histCount, start_time=start_time
        )
        message = (
            "From the trading history received: " + str(res["length"]) + " records"
        )
        WS._put_message(self, message=message)

        return res

    def open_orders(self: Markets) -> str:
        """
        Gets open orders.

        Returns
        -------
        str
            On success, "" is returned, otherwise an error type.
        """
        var.logger.info(self.name + " - Requesting open orders.")

        return Agents[self.name].value.open_orders(self)

    def place_limit(
        self: Markets, quantity: float, price: float, clOrdID: str, symbol: tuple
    ) -> Union[dict, str]:
        """
        Places a limit order.

        Parameters
        ----------
        self: Markets
            Markets class instances such as Bitmex, Bybit, Deribit.
        quantity: float
            Order quantity.
        price: float
            Order price.
        clOrdID: str
            Unique order identifier, including the bot name.
        symbol: str
            Instrument symbol. Example ("BTCUSDT", "Bybit").

        Returns
        -------
        dict | str
            If successful, a response from the exchange server is returned,
            otherwise - the error type (str).
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
    ) -> Union[dict, str]:
        """
        Moves a limit order.

        Parameters
        ----------
        self: Markets
            Markets class instances such as Bitmex, Bybit, Deribit.
        quantity: float
            Order quantity.
        price: float
            Order price.
        clOrdID: str
            Unique order identifier, including the bot name.
        symbol: str
            Instrument symbol. Example ("BTCUSDT", "Bybit").

        Returns
        -------
        dict | str
            If successful, a response from the exchange server is returned,
            otherwise - the error type (str).
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

    def remove_order(self: Markets, order: dict) -> Union[dict, str]:
        """
        Deletes an order.

        Parameters
        ----------
        self: Markets
            Markets class instances such as Bitmex, Bybit, Deribit.
        order: dict
            Order parameters.

        Returns
        -------
        dict | str
            If successful, a response from the exchange server is returned,
            otherwise - the error type (str).
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

    def get_wallet_balance(self: Markets) -> str:
        """
        Obtain wallet balance, query asset information of each currency, and
        account risk rate information.

        Returns
        -------
        str
            On success, "" is returned, otherwise an error type, such as
            FATAL, CANCEL.
        """
        var.logger.info(self.name + " - Requesting account.")

        return Agents[self.name].value.get_wallet_balance(self)

    def get_position_info(self: Markets) -> dict:
        """
        Get position information.

        Returns
        -------
        str
            On success, "" is returned, otherwise an error type, such as
            FATAL, CANCEL.
        """
        WS._put_message(self, message="Requesting positions.")

        return Agents[self.name].value.get_position_info(self)

    def ping_pong(self: Markets) -> None:
        """
        Check if websocket is working.
        """

        return Markets[self.name].ping_pong()

    def _put_message(self: Markets, message: str) -> None:
        """
        Places an information message into the queue and the logger.
        """
        var.queue_info.put(
            {
                "market": self.name,
                "message": message,
                "time": datetime.now(tz=timezone.utc),
                "warning": None,
            }
        )
        var.logger.info(self.name + " - " + message)
