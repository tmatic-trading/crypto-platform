from collections import OrderedDict
from datetime import datetime
from typing import Union

from api.bitmex.agent import Agent as BitmexAgent
from api.bitmex.ws import Bitmex
from api.bybit.agent import Agent as BybitAgent
from api.bybit.ws import Bybit
from .variables import Variables

from enum import Enum


class Markets(Variables, Enum):
    Bitmex =  Bitmex()
    Bybit = Bybit()
    

class Agents(Enum):
    Bitmex = BitmexAgent
    Bybit = BybitAgent


class WS(Variables):

    def start_ws(ws: Markets) -> None:
        """
        Websockets init
        """

        Markets[ws.name].value.start()

    def exit(ws: Markets) -> None:
        """
        Closes websocket
        """

        Markets[ws.name].value.exit()

    def get_active_instruments(ws: Markets) -> OrderedDict:
        """
        Gets all active instruments from the exchange REST API.
        """

        return Agents[ws.name].value.get_active_instruments(ws)

    def get_user(ws: Markets) -> Union[dict, None]:
        """
        Gets account info.
        """

        return Agents[ws.name].value.get_user(ws)

    def get_instrument(ws: Markets, symbol: tuple) -> None:
        """
        Gets a specific instrument by symbol name and category.
        """

        return Agents[ws.name].value.get_instrument(ws, symbol=symbol)

    def get_position(ws: Markets, symbol: tuple) -> None:
        """
        Gets information about an open position for a specific instrument.
        """

        return Agents[ws.name].value.get_position(ws, symbol=symbol)

    def trade_bucketed(
        ws: Markets, symbol: tuple, time: datetime, timeframe: str
    ) -> Union[list, None]:
        """
        Gets timeframe data.
        """

        return Agents[ws.name].value.trade_bucketed(
            ws, symbol=symbol, time=time, timeframe=timeframe
        )

    def trading_history(ws: Markets, histCount: int, time: datetime) -> list:
        """
        Gets all trades and funding from the exchange for the period starting
        from 'time'
        """

        return Agents[ws.name].value.trading_history(ws, histCount=histCount, time=time)

    def open_orders(ws: Markets) -> list:
        """
        Gets open orders.
        """

        return Agents[ws.name].value.open_orders(ws)

    def get_ticker(ws: Markets) -> OrderedDict:
        """
        Returns the best bid/ask price.
        """

        return Agents[ws.name].value.get_ticker(ws)

    def urgent_announcement(ws: Markets) -> list:
        """
        Public announcements of the exchange
        """

        return Agents[ws.name].value.urgent_announcement(ws)

    def get_funds(ws: Markets) -> list:
        """
        Cash in the account
        """

        return ws.data["margin"].values()

    def market_depth10(ws: Markets) -> list:
        """
        Gets market depth (orderbook), 10 lines deep.
        """

        return ws.data["orderBook10"]

    def place_limit(
        ws: Markets, quantity: int, price: float, clOrdID: str, symbol: tuple
    ) -> Union[dict, None]:
        """
        Places a limit order
        """

        return Agents[ws.name].value.place_limit(
            ws, quantity=quantity, price=price, clOrdID=clOrdID, symbol=symbol
        )

    def replace_limit(
        ws, quantity: int, price: float, orderID: str, symbol: tuple
    ) -> Union[dict, None]:
        """
        Moves a limit order
        """

        return Agents[ws.name].value.replace_limit(
            ws, quantity=quantity, price=price, orderID=orderID, symbol=symbol
        )

    def remove_order(ws: Markets, orderID: str) -> Union[list, None]:
        """
        Deletes an order
        """

        return Agents[ws.name].value.remove_order(ws, orderID=orderID)
