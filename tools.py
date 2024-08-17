import inspect
import os
import platform
from collections import OrderedDict
from datetime import datetime, timezone
from typing import Union

import functions

import services as service
from api.api import WS, Markets
from common.data import Bots, Instrument, MetaInstrument
from common.variables import Variables as var
from display.messages import ErrorMessage


def name(stack) -> str:
    if ostype == "Windows":
        bot_name = stack[1].filename.split("\\")[-2]
    else:
        bot_name = stack[1].filename.split("/")[-2]

    return bot_name


class Tool(Instrument):
    def __init__(self, instrument: Instrument) -> None:
        self.__dict__ = instrument.__dict__
        self.symbol_tuple = (self.symbol, self.market)

    def close_all(
        self,
        qty: float,
    ) -> None:
        bot_name = name(inspect.stack())
        pass

    def sell(
        self,
        qty: float = None,
        price: float = None,
        move: bool = False,
        cancel: bool = False,
    ) -> Union[str, None]:
        """
        Sets a sell order.

        Parameters
        ----------
        qty: float
            Order quantity. If qty is omitted, then: qty is taken as
            minOrderQty.
        price: float
            Order price. If price is omitted, then price is taken as the
            current first offer in the order book.
        move: bool
            Checks for open buy orders for this bot and if there are any,
            takes the last order and moves it to the new price. If not,
            places a new order.
        cancel: bool
            If True, cancels all buy orders for this bot.

        Returns
        -------
        str | None
            If successful, the clOrdID of this order is returned, otherwise None.
        """
        bot_name = name(inspect.stack())
        bot = Bots[bot_name]
        ws = Markets[self.market]
        res = None
        if not qty:
            qty = self.minOrderQty
        if not price:
            price = self.asks[0][0]
        if price:
            qty = self._control_limits(side="Buy", qty=qty, bot_name=bot_name)
            if qty:
                clOrdID = None
                if move is True:
                    clOrdID = self._get_latest_order(orders=bot.bot_orders, side="Sell")
                if clOrdID is None:
                    new_clOrdID = service.set_clOrdID(emi=bot_name)
                    res = WS.place_limit(
                        ws,
                        quantity=-abs(qty),
                        price=price,
                        clOrdID=new_clOrdID,
                        symbol=self.symbol_tuple,
                    )
                else:
                    order = bot.bot_orders[clOrdID]
                    if order["price"] != price:
                        res = WS.replace_limit(
                            ws,
                            quantity=order["leavesQty"],
                            price=price,
                            orderID=order["orderID"],
                            symbol=order["symbol"],
                        )
        else:
            self._empty_orderbook(qty=qty, price=price)
        if cancel is not None:
            self._remove_orders(orders=bot.bot_orders, side="Buy")

        if res is not None:
            return clOrdID

    def buy(
        self,
        qty: float = None,
        price: float = None,
        move: bool = False,
        cancel: bool = False,
    ) -> Union[str, None]:
        """
        Sets a buy order.

        Parameters
        ----------
        qty: float
            Order quantity. If qty is omitted, then: qty is taken as
            minOrderQty.
        price: float
            Order price. If price is omitted, then price is taken as the
            current first bid in the order book.
        move: bool
            Checks for open buy orders for this bot and if there are any,
            takes the last order and moves it to the new price. If not,
            places a new order.
        cancel: bool
            If True, cancels all buy orders for this bot.

        Returns
        -------
        str | None
            If successful, the clOrdID of this order is returned, otherwise None.
        """
        bot_name = name(inspect.stack())
        bot = Bots[bot_name]
        ws = Markets[self.market]
        res = None
        if not qty:
            qty = self.minOrderQty
        if not price:
            price = self.bids[0][0]
        if price:
            qty = self._control_limits(side="Buy", qty=qty, bot_name=bot_name)
            if qty:
                clOrdID = None
                if move is True:
                    clOrdID = self._get_latest_order(orders=bot.bot_orders, side="Buy")
                if clOrdID is None:
                    new_clOrdID = service.set_clOrdID(emi=bot_name)
                    res = WS.place_limit(
                        ws,
                        quantity=qty,
                        price=price,
                        clOrdID=new_clOrdID,
                        symbol=self.symbol_tuple,
                    )
                else:
                    order = bot.bot_orders[clOrdID]
                    if order["price"] != price:
                        res = WS.replace_limit(
                            ws,
                            quantity=order["leavesQty"],
                            price=price,
                            orderID=order["orderID"],
                            symbol=order["symbol"],
                        )
        else:
            self._empty_orderbook(qty=qty, price=price)
        if cancel is not None:
            self._remove_orders(orders=bot.bot_orders, side="Sell")

        if res is not None:
            return clOrdID

    def EMA(self, period: int) -> float:
        pass

    def add_kline(self) -> list:
        """
        Adds kline (candlestick) data to the instrument.

        This function is called from each bot's strategy.py file. The time
        frame is taken from the bot's parameters. After the bots are
        initialized, the klines list is stored in the kline_set variable
        for each market respectively. While Tmatic is starting or restarting
        a specific market, the kline data is taken from the market's endpoint
        according to the kline_set variable. The initial amount of data
        loaded from the endpoint is equal to CANDLESTICK_NUMBER in
        botinit/variables.py. Then, as the program runs, the data accumulates.

        Returns
        -------
        list
            A list of kline data, where the line with the latest date is
            designated as [-1], the line before the latest is designated
            as [-2], and so on. Each line is a dictionary where:
                "date": int
                    date yymmdd, example 240814
                "time": int
                    time hhmmss, example 143200
                "bid": float
                    first bid price at the beginning of the period
                "ask": float
                    first ask price at the beginning of the period
                "hi": float
                    highest price of the period
                "lo": float
                    lowest price of the period
                "funding": float
                    funding rate for perpetual instruments
                "datetime": datetime
                    date and time in datetime format
        """
        bot_name = name(inspect.stack())
        timefr = Bots[bot_name].timefr
        ws = Markets[self.market]
        ws.kline_set.add((self.symbol, bot_name, Bots[bot_name].timefr))
        functions.append_new_kline(
            ws, symbol=self.symbol_tuple, bot_name=bot_name, timefr=timefr
        )

        return ws.klines[self.symbol_tuple][timefr]["data"]

    def kline(self, period: int = 1) -> dict:
        ws = Markets[self.market]
        print(ws.klines)

    def _control_limits(self, side: str, qty: float, bot_name: str) -> float:
        """
        When an order is submitted, does not allow the bot to exceed the set
        limit for the instrument. Decreases quantity if the limit is exceeded
        or returns 0 if the limit is completely exhausted. If the bot does not
        have a position for this instrument, then such a position will be
        added to the bot, and the limit is set as minOrderQty of the
        instrument.

        Parameters
        ----------
        side: str
            The Sell or Buy side of the order.
        qty: float
            The quantity of the order.
        bot_name: str
            Bot name.
        """
        bot = Bots[bot_name]
        if not self.symbol_tuple in bot.bot_positions:
            bot.bot_positions[self.symbol_tuple] = {
                "emi": bot_name,
                "symbol": self.symbol,
                "category": self.market,
                "market": self.market,
                "ticker": self.ticker,
                "position": 0,
                "volume": 0,
                "sumreal": 0,
                "commiss": 0,
                "ltime": None,
                "pnl": 0,
                "lotSize": self.minOrderQty,
                "currency": self.settlCurrency[0],
                "limits": self.minOrderQty,
            }
            # Checks if this bot has any records in the database on this instrument.
            qwr = (
                "select MARKET, SYMBOL, sum(abs(QTY)) as SUM_QTY, "
                + "sum(SUMREAL) as SUM_SUMREAL, sum(COMMISS) as "
                + "SUM_COMMISS, TTIME from (select * from coins where EMI = '"
                + bot_name
                + "' and SYMBOL = '"
                + self.symbol
                + "' and MARKET = '"
                + self.market
                + "' and ACCOUNT = "
                + str(Markets[self.market].user_id)
                + " and SIDE <> 'Fund' order by ID desc) T;"
            )
            data = service.select_database(qwr)[0]
            if data and data["SUM_QTY"]:
                bot.bot_positions[self.symbol_tuple]["volume"] = float(data["SUM_QTY"])
                bot.bot_positions[self.symbol_tuple]["sumreal"] = float(
                    data["SUM_SUMREAL"]
                )
                bot.bot_positions[self.symbol_tuple]["commiss"] = float(
                    data["SUM_COMMISS"]
                )
        position = bot.bot_positions[self.symbol_tuple]
        if side == "Sell":
            qty = min(max(0, position["position"] + position["limits"]), abs(qty))
        else:
            qty = min(max(0, position["limits"] - position["position"]), abs(qty))

        return round(qty, self.precision)

    def _empty_orderbook(self, qty: float, price: float) -> None:
        """
        Sends a warning message if the order book is empty.
        """
        order = f"Buy qty={qty}, price={price}"
        message = ErrorMessage.EMPTY_ORDERBOOK(ORDER=order, SYMBOL=self.symbol_tuple)
        var.logger.warning(message)
        var.queue_info.put(
            {
                "market": "",
                "message": message,
                "time": datetime.now(tz=timezone.utc),
                "warning": True,
            }
        )

    def _filter_by_side(self, orders: OrderedDict, side: str) -> dict:
        """
        Finds all bot orders on the sell or buy side for a specific instrument.

        Parameters
        ----------
        orders: OrderedDict
            Bot order dictionary, where the key is clOrdID
        side: str
            Buy or Sell

        Returns
        -------
        dict
            Bot orders are filtered by sell or buy side.
        """
        filtered = OrderedDict()
        for clOrdID, value in orders.items():
            if value["side"] == side and value["symbol"] == self.symbol_tuple:
                filtered[clOrdID] = value

        return filtered

    def _remove_orders(self, orders: OrderedDict, side: str) -> None:
        """
        Removes group of given orders by side.

        Parameters
        ----------
        orders: OrderedDict
            Dictionary where key is clOrdID.
        side: str
            Buy or Sell
        """
        orders = self._filter_by_side(orders=orders, side=side)
        for order in orders.values():
            ws = Markets[self.market]
            WS.remove_order(ws, order=order)

    def _get_latest_order(self, orders: OrderedDict, side: str) -> Union[str, None]:
        """
        Finds the last order given side.

        Parameters
        ----------
        orders: OrderedDict
            Dictionary where key is clOrdID.
        side: str
            Buy or Sell

        Returns
        -------
        str | None
            If an order is found, returns clOrdID of that order, otherwise None.
        """
        orders = self._filter_by_side(orders=orders, side=side)
        if orders:
            clOrdID = list(orders)[-1]

            return clOrdID


class MetaTool(type):
    objects = dict()

    def __getitem__(self, item) -> Tool:
        market = self.__qualname__
        instrument = (item, market)
        if instrument not in MetaInstrument.all:
            raise ValueError(f"The instrument {instrument} not found.")
        if instrument not in self.objects:
            self.objects[instrument] = Tool(MetaInstrument.all[instrument])

        return self.objects[instrument]


if platform.system() == "Windows":
    ostype = "Windows"
elif platform.system() == "Darwin":
    ostype = "Mac"
else:
    ostype = "Linux"


class Bitmex(metaclass=MetaTool):
    pass


class Bybit(metaclass=MetaTool):
    pass


class Deribit(metaclass=MetaTool):
    pass


class Bot:
    def __init__(self) -> None:
        bot_name = name(inspect.stack())
        bot = Bots[bot_name]
        self.name = bot.name
        self.bot_positions = bot.bot_positions
        self.timefr = bot.timefr
        self.pnl = bot.pnl
        self.state = bot.state
        self.created = bot.created
        self.updated = bot.updated
        self.error_message = bot.error_message
