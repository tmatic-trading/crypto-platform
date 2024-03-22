from collections import OrderedDict
from datetime import datetime
from typing import Union

from api.bitmex.agent import Agent as BitmexAgent
from api.bitmex.ws import Bitmex
from api.bybit.agent import Agent as BybitAgent
from api.bybit.ws import Bybit


class WS(Bitmex, Bybit):
    select_ws = {"Bitmex": Bitmex.start, "Bybit": Bybit.start}
    exit_agent = {"Bitmex": BitmexAgent.exit, "Bybit": BybitAgent.exit}
    get_active_instruments_agent = {
        "Bitmex": BitmexAgent.get_active_instruments,
        "Bybit": BybitAgent.get_active_instruments,
    }
    get_user_agent = {"Bitmex": BitmexAgent.get_user, "Bybit": BybitAgent.get_user}
    get_instrument_agent = {
        "Bitmex": BitmexAgent.get_instrument,
        "Bybit": BybitAgent.get_instrument,
    }
    get_position_agent = {
        "Bitmex": BitmexAgent.get_position,
        "Bybit": BybitAgent.get_position,
    }
    trade_bucketed_agent = {
        "Bitmex": BitmexAgent.trade_bucketed,
        "Bybit": BybitAgent.trade_bucketed,
    }
    trading_history_agent = {
        "Bitmex": BitmexAgent.trading_history,
        "Bybit": BybitAgent.trading_history,
    }
    open_orders_agent = {
        "Bitmex": BitmexAgent.open_orders,
        "Bybit": BybitAgent.open_orders,
    }
    get_ticker_agent = {
        "Bitmex": BitmexAgent.get_ticker,
        "Bybit": BybitAgent.get_ticker,
    }
    urgent_announcement_agent = {
        "Bitmex": BitmexAgent.urgent_announcement,
        "Bybit": BybitAgent.urgent_announcement,
    }
    place_limit_agent = {
        "Bitmex": BitmexAgent.place_limit,
        "Bybit": BybitAgent.place_limit,
    }
    replace_limit_agent = {
        "Bitmex": BitmexAgent.replace_limit,
        "Bybit": BybitAgent.replace_limit,
    }
    remove_order_agent = {
        "Bitmex": BitmexAgent.remove_order,
        "Bybit": BybitAgent.remove_order,
    }

    def start_ws(self, name) -> None:
        self.select_ws[name](self)

    def exit(self, name) -> None:
        """
        Closes websocket
        """

        self.exit_agent[name](self)

    def get_active_instruments(self, name) -> OrderedDict:
        """
        Gets all active instruments from the exchange REST API.
        """

        return self.get_active_instruments_agent[name](self)

    def get_user(self, name: str) -> Union[dict, None]:
        """
        Gets account info.
        """

        return self.get_user_agent[name](self)

    def get_instrument(self, name: str, symbol: tuple) -> None:
        """
        Gets a specific instrument by symbol name and category.
        """

        return self.get_instrument_agent[name](self, symbol=symbol)

    def get_position(self, name: str, symbol: tuple) -> None:
        """
        Gets information about an open position for a specific instrument.
        """

        return self.get_position_agent[name](self, symbol=symbol)

    def trade_bucketed(
        self, name: str, symbol: tuple, time: datetime, timeframe: str
    ) -> Union[list, None]:
        """
        Gets timeframe data.
        """

        return self.trade_bucketed_agent[name](
            self, symbol=symbol, time=time, timeframe=timeframe
        )

    def trading_history(self, name: str, histCount: int, time: datetime) -> list:
        """
        Gets all trades and funding from the exchange for the period starting
        from 'time'
        """

        return self.trading_history_agent[name](self, histCount=histCount, time=time)

    def open_orders(self, name: str) -> list:
        """
        Gets open orders.
        """

        return self.open_orders_agent[name](self)

    def get_ticker(self, name: str) -> OrderedDict:
        """
        Returns the best bid/ask price.
        """

        return self.get_ticker_agent[name](self)

    def urgent_announcement(self, name: str) -> list:
        """
        Public announcements of the exchange
        """

        return self.urgent_announcement_agent[name](self)

    def get_funds(self) -> list:
        """
        Cash in the account
        """

        return self.data["margin"].values()

    def market_depth10(self) -> list:
        """
        Gets market depth (orderbook), 10 lines deep.
        """

        return self.data["orderBook10"]

    def place_limit(
        self, name: str, quantity: int, price: float, clOrdID: str, symbol: tuple
    ) -> Union[dict, None]:
        """
        Places a limit order
        """

        return self.place_limit_agent[name](
            self, quantity=quantity, price=price, clOrdID=clOrdID, symbol=symbol
        )

    def replace_limit(
        self, name: str, quantity: int, price: float, orderID: str, symbol: tuple
    ) -> Union[dict, None]:
        """
        Moves a limit order
        """

        return self.replace_limit_agent[name](
            self, quantity=quantity, price=price, orderID=orderID, symbol=symbol
        )

    def remove_order(self, name: str, orderID: str) -> Union[list, None]:
        """
        Deletes an order
        """

        return self.remove_order_agent[name](self, orderID=orderID)
