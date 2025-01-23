import threading
from datetime import datetime, timezone
from typing import Callable, Union

import services as service
from api.setup import Agents, Markets
from common.variables import Variables as var

from .variables import Variables


class WS(Variables):
    def connect_market(self: Markets) -> str:
        """
        Loading instruments, orders, user ID, wallet balance, position
        information and initializing websockets.

        Returns
        -------
        str
            On success, "" is returned, otherwise an error type or error message.
        """
        def get_in_thread(method: Callable):
            """
            On success, "" is returned, otherwise an error type.
            """
            method_name = method.__name__
            try:
                error = method(self)
                if error:
                    success[method_name] = error
            except Exception as exception:
                mes = service.display_exception(exception, display=False)
                WS._put_message(self, message=mes, warning=True)
                self.logNumFatal = "CANCEL"
                success[method_name] = self.logNumFatal

        # It starts here.

        threads = []
        success = {}

        success["get_active_instruments"] = ""
        t = threading.Thread(target=get_in_thread, args=(WS.get_active_instruments,))
        threads.append(t)
        t.start()

        success["start_ws"] = ""
        t = threading.Thread(target=get_in_thread, args=(WS.start_ws,))
        threads.append(t)
        t.start()

        [thread.join() for thread in threads]

        for method_name, error in success.items():
            if error:
                self.logger.error(
                    self.name + ": error occurred while loading " + method_name
                )
                return service.unexpected_error(self)

        success["open_orders"] = ""
        t = threading.Thread(target=get_in_thread, args=(WS.open_orders,))
        t.start()
        t.join()
        if success["open_orders"]:
            self.logger.error(
                self.name + ": error occurred while loading open_orders."
            )
            return service.unexpected_error(self)

        threads = []
        success = {}

        success["activate_funding_thread"] = ""
        t = threading.Thread(target=get_in_thread, args=(WS.activate_funding_thread,))
        t.start()
        success["setup_streams"] = ""
        t = threading.Thread(target=get_in_thread, args=(WS.setup_streams,))
        threads.append(t)
        t.start()
        success["get_user"] = ""
        t = threading.Thread(target=get_in_thread, args=(WS.get_user,))
        threads.append(t)
        t.start()
        success["get_wallet_balance"] = ""
        t = threading.Thread(target=get_in_thread, args=(WS.get_wallet_balance,))
        threads.append(t)
        t.start()
        success["get_position_info"] = ""
        t = threading.Thread(target=get_in_thread, args=(WS.get_position_info,))
        threads.append(t)
        t.start()

        [thread.join() for thread in threads]

        for method_name, error in success.items():
            if error:
                self.logger.error(
                    self.name + ": error occurred while loading " + method_name
                )
                return service.unexpected_error(self)
            
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
    
    def start_ws(self: Markets) -> str:
        """
        Launching a websocket.

        Returns
        -------
        str
            On success, "" is returned, otherwise an error type, such as
            FATAL, CANCEL.
        """
        WS._put_message(self, message="Connecting to websocket.")

        return Markets[self.name].start_ws()    

    def setup_streams(self: Markets) -> str:
        """
        Initial websocket subscriptions, heartbeat, etc.

        Returns
        -------
        str
            On success, "" is returned, otherwise an error type, such as
            FATAL, CANCEL.
        """
        WS._put_message(self, message="Establishing subscriptions via web sockets.")

        return Markets[self.name].setup_streams()
    
    def activate_funding_thread(self: Markets) -> str:
        """
        Only for Deribit, which does not provide funding and delivery 
        information via websocket.

        Returns
        -------
        str
            On success, "" is returned.
        """

        return Agents[self.name].value.activate_funding_thread(self)

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
        WS._put_message(self, message="Requesting open orders.")

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
        message = (
            self.name
            + " - Sending a new order - "
            + "symbol="
            + symbol[0]
            + ", clOrdID="
            + clOrdID
            + ", price="
            + str(price)
            + ", qty="
            + str(quantity)
        )

        WS._put_message(self, message=message, info=False)

        return Agents[self.name].value.place_limit(
            self, quantity=quantity, price=price, clOrdID=clOrdID, symbol=symbol
        )

    def replace_limit(
        self: Markets,
        leavesQty: float,
        price: float,
        orderID: str,
        symbol: tuple,
        orderQty: float,
        clOrdID: str,
    ) -> Union[dict, str]:
        """
        Moves a limit order.

        Parameters
        ----------
        self: Markets
            Markets class instances such as Bitmex, Bybit, Deribit.
        leavesQty: float
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
        message = (
            self.name
            + " - Replace order - "
            + "symbol="
            + symbol[0]
            + ", orderID="
            + orderID
            + ", clOrdID="
            + clOrdID
            + ", price="
            + str(price)
            + ", qty="
            + str(leavesQty)
        )

        WS._put_message(self, message=message, info=False)

        return Agents[self.name].value.replace_limit(
            self,
            leavesQty=leavesQty,
            price=price,
            orderID=orderID,
            symbol=symbol,
            orderQty=orderQty,
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
        message = (
            self.name
            + " - Cancel order - "
            + "symbol="
            + order["symbol"][0]
            + ", orderID="
            + order["orderID"]
            + ", clOrdID="
            + order["clOrdID"]
            + ", price="
            + str(order["price"])
            + ", qty="
            + str(order["orderQty"])
        )

        WS._put_message(self, message=message, info=False)

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
        WS._put_message(self, message="Requesting account.")

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

    def _put_message(self: Markets, message: str, warning=None, info=True) -> None:
        """
        Places an information message into the queue and the logger.
        """
        if info:
            var.queue_info.put(
                {
                    "market": self.name,
                    "message": message,
                    "time": datetime.now(tz=timezone.utc),
                    "warning": warning,
                }
            )
        if warning is None:
            self.logger.info(self.name + " - " + message)
        else:
            self.logger.error(self.name + " - " + message)
