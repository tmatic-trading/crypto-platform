import inspect
import platform
from collections import OrderedDict
from datetime import datetime, timezone
from typing import Callable, Union

import functions
import services as service
from api.api import WS, Markets
from backtest import functions as backtest
from common.data import BotData, Bots, Instrument, MetaInstrument
from common.variables import Variables as var
from display.bot_menu import bot_manager
from display.messages import ErrorMessage
from display.variables import Variables as disp


def name(stack) -> str:
    if ostype == "Windows":
        bot_name = stack[1].filename.split("\\")[-2]
    else:
        bot_name = stack[1].filename.split("/")[-2]

    return bot_name


class Bot(BotData):
    def __init__(self) -> None:
        bot_name = name(inspect.stack())
        bot = Bots[bot_name]
        self.__dict__ = bot.__dict__

    def remove(self, clOrdID: str = "") -> None:
        """
        Removes the open order by its clOrdID.

        Parameters:
        -----------
        bot: Bot
            An instance of a bot in the Bot class.
        clOrdID: str
            Order ID. Example: "1348642035.Super"
            If this parameter is omitted, all orders for this bot will be
            deleted.
        """
        if var.backtest:
            self._backtest_remove(clOrdID=clOrdID)
            return

        if self.state == "Active" and disp.f9 == "ON":
            ord = var.orders[self.name]
            lst = []
            if not clOrdID:
                for clOrdID in ord:
                    lst.append(clOrdID)
            else:
                lst.append(clOrdID)
            for clOrdID in lst:
                if clOrdID in ord:
                    order = ord[clOrdID]
                    ws = Markets[order["market"]]
                    WS.remove_order(ws, order=ord[clOrdID])
                else:
                    message = "Removing. Order with clOrdID=" + clOrdID + " not found."
                    var.queue_info.put(
                        {
                            "market": "",
                            "message": message,
                            "time": datetime.now(tz=timezone.utc),
                            "warning": "warning",
                            "emi": self.name,
                            "bot_log": True,
                        }
                    )

    def replace(self, clOrdID: str, price: float) -> Union[str, None]:
        """
        Moves an open order to a new price using its clOrdID.

        Parameters
        ----------
        bot: Bot
            An instance of a bot in the Bot class.
        clOrdID: str
            Order ID. Order ID. Example: "1348642035.Super"
        price: float
            New price to reset order to.

        Returns
        -------
        str | None
            On success, clOrdID is returned, otherwise an error type.
        """
        if var.backtest:
            self._backtest_replace(clOrdID=clOrdID, price=price)
            return clOrdID

        if self.state == "Active" and disp.f9 == "ON":
            ord = var.orders[self.name]
            if clOrdID in ord:
                order = ord[clOrdID]
                ws = Markets[order["market"]]
                res = WS.replace_limit(
                    ws,
                    leavesQty=order["leavesQty"],
                    price=price,
                    orderID=order["orderID"],
                    symbol=order["symbol"],
                    orderQty=order["orderQty"],
                    clOrdID=clOrdID,
                )
                if isinstance(res, dict):
                    return clOrdID
            else:
                message = "Replacing. Order with clOrdID=" + clOrdID + " not found."
                var.queue_info.put(
                    {
                        "market": "",
                        "message": message,
                        "time": datetime.now(tz=timezone.utc),
                        "warning": "warning",
                        "emi": self.name,
                        "bot_log": True,
                    }
                )

    def orders(
        self, side: str = "", descend=False, in_list=True
    ) -> Union[OrderedDict, list]:
        """
        Get the bot orders filtered by side.

        Parameters
        ----------
        side: str
            The Sell or Buy side of the order. If this parameter is omitted,
            all orders are returned.
        descend: bool
            If omitted, the data is sorted in ascending order by the value of
            ``transactTime``. If True, descending order is returned.
        in_list: bool
            If True, the data is returned in a list, otherwise an OrderedDict
            is returned where the key is clOrdID.

        Returns
        -------
        OrderedDict | list
            Orders are sorted by ``transactTime`` in the order specified in
            the descend parameter. The OrderedDict key is the clOrdID value.
        """
        ord = var.orders[self.name].values()
        if not in_list:
            filtered = OrderedDict()
            if descend:
                ord = sorted(ord, key=lambda x: x["transactTime"], reverse=True)
            for value in ord:
                if side:
                    if value["side"] == side:
                        filtered[value["clOrdID"]] = value
                else:
                    filtered[value["clOrdID"]] = value
        else:
            filtered = list()
            if descend:
                ord = sorted(ord, key=lambda x: x["transactTime"], reverse=True)
            for value in ord:
                if side:
                    if value["side"] == side:
                        filtered.append(value)
                else:
                    filtered.append(value)

        return filtered

    def _backtest_remove(self, clOrdID: str) -> None:
        del var.orders[self.name][clOrdID]

    def _backtest_replace(self, clOrdID: str, price: float) -> None:
        var.orders[self.name][clOrdID]["price"] = price


class Tool(Instrument):
    def __init__(self, instrument: Instrument) -> None:
        self.__dict__ = instrument.__dict__
        self.symbol_tuple = (self.symbol, self.market)
        self.instrument = instrument
        if var.backtest:
            var.backtest_symbols.append(self.symbol_tuple)

    def close_all(
        self,
        bot: Bot,
        qty: float,
    ) -> None:
        pass

    def _place(
        self,
        price: float,
        qty: float,
        side: str,
        move: bool,
        bot: BotData,
        cancel: bool,
    ):
        res = None
        if price:
            price = service.ticksize_rounding(price=price, ticksize=self.tickSize)
            qty = self._control_limits(side=side, qty=qty, bot_name=bot.name)
            if qty != 0:
                ws = Markets[self.market]
                clOrdID = None
                if move is True:
                    clOrdID = self._get_latest_order(
                        orders=var.orders[bot.name], side=side
                    )
                if clOrdID is None:
                    clOrdID = service.set_clOrdID(emi=bot.name)
                    if side == "Sell":
                        qty = -qty
                    res = WS.place_limit(
                        ws,
                        quantity=qty,
                        price=price,
                        clOrdID=clOrdID,
                        symbol=self.symbol_tuple,
                    )
                else:
                    order = var.orders[bot.name][clOrdID]
                    if order["price"] != price:
                        res = WS.replace_limit(
                            ws,
                            leavesQty=order["leavesQty"],
                            price=price,
                            orderID=order["orderID"],
                            symbol=order["symbol"],
                            orderQty=order["orderQty"],
                            clOrdID=clOrdID,
                        )
        else:
            self._empty_orderbook(qty=qty, price=price, bot_name=bot.name)
        if cancel:
            if side == "Sell":
                self._remove_orders(orders=var.orders[bot.name], side="Buy")
            elif side == "Buy":
                self._remove_orders(orders=var.orders[bot.name], side="Sell")

        if isinstance(res, dict):
            return clOrdID

    def sell(
        self,
        bot: Bot,
        qty: float = None,
        price: float = None,
        move: bool = False,
        cancel: bool = False,
    ) -> Union[str, None]:
        """
        Sets a sell order.

        Parameters
        ----------
        bot: Bot
            An instance of a bot in the Bot class.
        qty: float
            Order quantity. If qty is omitted, then: qty is taken as
            minOrderQty.
        price: float
            Order price. If price is omitted, then price is taken as the
            current first offer in the order book.
        move: bool
            Checks for open sell orders for the current instrument for this
            bot and if there are any, takes the last order and moves it to
            the new price. If not, places a new order.
        cancel: bool
            If True, cancels all buy orders for the current instrument for
            this bot.

        Returns
        -------
        str | None
            If successful, the clOrdID of this order is returned, otherwise
            None.
        """
        if not qty:
            qty = self.minOrderQty

        if var.backtest:
            return self._backtest_place(
                bot=bot, qty=qty, side="Sell", price=price, move=move, cancel=cancel
            )

        if bot.state == "Active" and disp.f9 == "ON":
            if not price:
                try:
                    price = self.asks[0][0]
                except IndexError:
                    self._empty_orderbook(qty=qty, price=price, bot_name=bot.name)
                    return

            return self._place(
                price=price, qty=qty, side="Sell", move=move, bot=bot, cancel=cancel
            )

    def buy(
        self,
        bot: Bot,
        qty: float = None,
        price: float = None,
        move: bool = False,
        cancel: bool = False,
    ) -> Union[str, None]:
        """
        Sets a buy order.

        Parameters
        ----------
        bot: Bot
            An instance of a bot in the Bot class.
        qty: float
            Order quantity. If qty is omitted, then: qty is taken as
            minOrderQty.
        price: float
            Order price. If price is omitted, then price is taken as the
            current first bid in the order book.
        move: bool
            Checks for open buy orders for the current instrument for this
            bot and if there are any, takes the last order and moves it to
            the new price. If not, places a new order.
        cancel: bool
            If True, cancels all buy orders for the current instrument for
            this bot.

        Returns
        -------
        str | None
            If successful, the clOrdID of this order is returned, otherwise
            None.
        """

        if not qty:
            qty = self.minOrderQty

        if var.backtest:
            return self._backtest_place(
                bot=bot, qty=qty, side="Buy", price=price, move=move, cancel=cancel
            )

        if bot.state == "Active" and disp.f9 == "ON":
            if not price:
                try:
                    price = self.bids[0][0]
                except IndexError:
                    self._empty_orderbook(qty=qty, price=price, bot_name=bot.name)
                    return

            return self._place(
                price=price, qty=qty, side="Buy", move=move, bot=bot, cancel=cancel
            )

    def EMA(self, period: int) -> float:
        pass

    def add_kline(self, timefr: str = "") -> Callable:
        """
        Adds kline (candlestick) data to the instrument for the time interval
        specified in the bot parameters.

        This function is called from each bot's strategy.py file. The time
        frame is taken from the bot's parameters. After the bots are
        initialized, the kline data is stored in the klines dictionary for
        each market respectively. While Tmatic is starting or restarting
        a specific market, the kline data is taken from the market's endpoint
        according to the klines dictionary. The initial amount of data
        loaded from the endpoint is equal to CANDLESTICK_NUMBER in
        botinit/variables.py. Then, as the program runs, the data accumulates.

        Parameters
        ----------
        timefr: str
            Possible values: "1min", "2min", "3min", "5min", "10min",
            "15min", "20min", "30min", "1h", "2h", "3h", "4h", "6h", "12h",
            "1D". If omited, the time frame is specified in the bot
            parameters.

        Returns
        -------
        Callable
            A callable method that returns the kline data of the specified
            instrument. If argumens to this method are omitted, all klines are
            returned. The line with the latest date is designated as -1, the
            line before the latest is designated -2, and so on. Each line is
            a dictionary where:
                "date": int
                    date yymmdd, example 240814
                "time": int
                    time hhmmss, example 143200
                "open_bid": float
                    first bid price at the beginning of the period
                "open_ask": float
                    first ask price at the beginning of the period
                "bid": float
                    current first bid price
                "ask": float
                    current first ask price
                "hi": float
                    highest price of the period
                "lo": float
                    lowest price of the period
                "funding": float
                    funding rate for perpetual instruments
                "datetime": datetime
                    date and time in datetime format

        Examples
        --------
        kl = Bybit["BTCUSD"].add_kline()

        kl(-1)
        Return type: dict
            Returns latest kline data.
        """
        bot_name = name(inspect.stack())
        bot = Bots[bot_name]
        if self.state not in ["Open", "open"]:
            bot_path = bot_manager.get_bot_path(bot_name)
            message = ErrorMessage.BOT_KLINE_ERROR.format(
                BOT_NAME=bot_name,
                INSTRUMENT=self.symbol_tuple,
                STATUS=self.state,
                EXPIRE=self.expire,
                FILE=bot_path,
            )
            bot.error_message = {
                "error_type": "invalid_instrument",
                "message": message,
            }
            var.queue_info.put(
                {
                    "market": "",
                    "message": message,
                    "time": datetime.now(tz=timezone.utc),
                    "warning": True,
                }
            )
            var.logger.error(message)
            return
        if timefr == "":
            timefr = bot.timefr
        ws = Markets[self.market]
        functions.add_new_kline(
            ws, symbol=self.symbol_tuple, bot_name=bot_name, timefr=timefr
        )

        return lambda *args: self._kline(timefr, bot_name, *args)

    def set_limit(self, bot: Bot, limit: float) -> None:
        """
        Limits bot position for the specified instrument.

        Parameters
        ----------
        bot: Bot
            An instance of a bot in the Bot class.
        limit: float
            The limit of positions the bot is allowed to trade on this
            instrument. If this parameter is less than the instrument's
            minOrderQty, it becomes minOrderQty.
        """
        if limit < self.instrument.minOrderQty:
            limit = self.instrument.minOrderQty
        position = self._get_position(bot_name=bot.name)
        position["limits"] = limit

    def limit(self, bot: Bot) -> float:
        """
        Get bot position limit for the instrument.

        Parameters
        ----------
        bot: Bot
            An instance of a bot in the Bot class.

        Returns
        -------
        float
            Bot position limit for the instrument.
        """
        position = self._get_position(bot_name=bot.name)

        return position["limits"]

    def position(self, bot: Bot) -> float:
        """
        Get the bot position for the instrument.

        Parameters
        ----------
        bot: Bot
            An instance of a bot in the Bot class.

        Returns
        -------
        float
            The bot position value for the instrument.
        """
        position = self._get_position(bot_name=bot.name)

        return position["position"]

    def orders(
        self, bot: Bot, side: str = None, descend: bool = False, in_list=True
    ) -> Union[OrderedDict, list]:
        """
        Get the bot orders for the given instrument filtered by instrument
        and side.

        Parameters
        ----------
        bot: Bot
            An instance of a bot in the Bot class.
        side: str
            The Sell or Buy side of the order. If the parameter is omitted,
            both sides are returned.
        descend: bool
            If omitted, the data is sorted in ascending order by the value of
            ``transactTime``. If True, descending order is returned.
        in_list: bool
            If True, the data is returned in a list, otherwise an OrderedDict
            is returned where the key is clOrdID.

        Returns
        -------
        OrderedDict | list
            Orders are sorted by ``transactTime`` in the order specified in
            the descend parameter. The OrderedDict key is the clOrdID value.
        """
        filtered = self._filter_by_side(
            orders=var.orders[bot.name], side=side, descend=descend, in_list=in_list
        )

        return filtered

    def _kline(self, timefr, bot_name, *args) -> dict:
        """
        Returns kline (candlestick) data.

        Parameters
        ----------
        args parameter: int
            The line with the latest date is designated as -1, the
            line before the latest is designated -2, and so on. If args is
            empty, all kline are returned in the "data" key.

        Returns
        -------
        dict
            Kline data. For more information, see add_kline().
        """
        if not var.backtest:
            ws = Markets[self.market]
            if not args:
                values = {"data": ws.klines[self.symbol_tuple][timefr]["data"]}
            else:
                values = ws.klines[self.symbol_tuple][timefr]["data"][args[0]]
            try:
                values["bid"] = self.instrument.bids[0][0]
            except IndexError as exception:
                message = {
                    "error_type": exception.__class__.__name__,
                    "message": ErrorMessage.EMPTY_ORDERBOOK_DATA.format(
                        SIDE="bid", SYMBOL=self.symbol_tuple
                    ),
                }
                Bots[bot_name].error_message = message
                values["bid"] = 0
            try:
                values["ask"] = self.instrument.asks[0][0]
            except IndexError as exception:
                message = {
                    "error_type": exception.__class__.__name__,
                    "message": ErrorMessage.EMPTY_ORDERBOOK_DATA.format(
                        SIDE="ask", SYMBOL=self.symbol_tuple
                    ),
                }
                Bots[bot_name].error_message = message
                values["ask"] = 0

            return values

        else:
            bot = Bots[bot_name]
            if not args:
                values = bot.backtest_data[self.symbol_tuple]
            else:
                values = bot.backtest_data[self.symbol_tuple][bot.iter + args[0]]
            values["bid"] = bot.backtest_data[self.symbol_tuple][
                bot.iter + args[0] + 2
            ]["open_bid"]
            values["ask"] = bot.backtest_data[self.symbol_tuple][
                bot.iter + args[0] + 2
            ]["open_ask"]

            return values

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
        position = self._get_position(bot_name=bot_name)
        if side == "Sell":
            qty = min(max(0, position["position"] + position["limits"]), abs(qty))
        else:
            qty = min(max(0, position["limits"] - position["position"]), abs(qty))
        qty = round(qty, self.precision)
        if not var.backtest and qty == 0:
            message = (
                side
                + " order rejected. "
                + "Position has reached the limit for ("
                + position["symbol"]
                + ", "
                + position["market"]
                + "), limit "
                + str(position["limits"])
                + ", current position "
                + str(position["position"])
                + ". "
            )
            var.queue_info.put(
                {
                    "market": "",
                    "message": message,
                    "time": datetime.now(tz=timezone.utc),
                    "warning": "warning",
                    "emi": bot_name,
                    "bot_log": True,
                }
            )

        return qty

    def _empty_orderbook(self, qty: float, price: float, bot_name: str) -> None:
        """
        Sends a warning message if the order book is empty.
        """
        order = f"qty={qty}, price={price}"
        message = ErrorMessage.EMPTY_ORDERBOOK(ORDER=order, SYMBOL=self.symbol_tuple)
        var.logger.warning(message)
        var.queue_info.put(
            {
                "market": "",
                "message": message,
                "time": datetime.now(tz=timezone.utc),
                "warning": "warning",
                "emi": bot_name,
            }
        )

    def _filter_by_side(
        self,
        orders: OrderedDict,
        side: str = None,
        descend: bool = False,
        in_list: bool = True,
    ) -> Union[OrderedDict, list]:
        """
        Finds all bot orders on the sell or buy side for a specific instrument.

        Parameters
        ----------
        orders: OrderedDict
            Bot order dictionary, where the key is clOrdID
        side: str
            Buy or Sell
        descend: bool
            If omitted, the data is sorted in ascending order by the value of
            ``transactTime``. If True, descending order is returned.
        in_list: bool
            If True, the data is returned in a list, otherwise an OrderedDict
            is returned where the key is clOrdID.

        Returns
        -------
        OrderedDict | list
            Orders are sorted by ``transactTime`` in the order specified in
            the descend parameter. The OrderedDict key is the clOrdID value.
        """
        ord = orders.values()
        if not in_list:
            filtered = OrderedDict()
            if descend:
                ord = sorted(ord, key=lambda x: x["transactTime"], reverse=True)
            for value in ord:
                if value["symbol"] == self.symbol_tuple:
                    if side:
                        if value["side"] == side:
                            filtered[value["clOrdID"]] = value
                    else:
                        filtered[value["clOrdID"]] = value
        else:
            filtered = list()
            if descend:
                ord = sorted(ord, key=lambda x: x["transactTime"], reverse=True)
            for value in ord:
                if value["symbol"] == self.symbol_tuple:
                    if side:
                        if value["side"] == side:
                            filtered.append(value)
                    else:
                        filtered.append(value)

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
        ws = Markets[self.market]
        for order in orders:
            WS.remove_order(ws, order=order)

    def _get_latest_order(self, orders: OrderedDict, side: str) -> Union[str, None]:
        """
        Finds the last order on a given side.

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
            return orders[0]["clOrdID"]

    def _get_position(self, bot_name: str) -> dict:
        """
        Returns the bot's position values.

        Parameters
        ----------
        bot_name: str
            Bot name.

        Returns
        -------
        dict
            All bot's position values: "emi", "symbol", "category", "limits",
            "ticker", "position", "volume", "sumreal", "commiss", "ltime",
            "pnl", "lotSize", "currency", "limits".
        """
        bot = Bots[bot_name]
        if self.symbol_tuple not in bot.bot_positions:
            service.fill_bot_position(
                bot_name=bot_name,
                symbol=self.symbol_tuple,
                instrument=self.instrument,
                user_id=Markets[self.market].user_id,
            )

        return bot.bot_positions[self.symbol_tuple]

    def _backtest_place(
        self,
        bot: Bot,
        qty: float,
        side: str,
        price: Union[float, None],
        move: bool,
        cancel: bool,
    ) -> Union[str, None]:
        qty = self._control_limits(side=side, qty=qty, bot_name=bot.name)
        clOrdID = None
        if qty != 0:
            price = service.ticksize_rounding(price=price, ticksize=self.tickSize)
            if move is True:
                clOrdID = self._get_latest_order(orders=var.orders[bot.name], side=side)
            data = bot.backtest_data[self.symbol_tuple]
            if side == "Sell":
                compare_2 = data[bot.iter + 1]["open_bid"]
                if not price:
                    price = data[bot.iter + 1]["open_ask"]
                else:
                    if price < compare_2:
                        price = compare_2
                compare_1 = price
            else:
                compare_1 = data[bot.iter + 1]["open_ask"]
                if not price:
                    price = data[bot.iter + 1]["open_bid"]
                else:
                    if price > compare_1:
                        price = compare_1
                compare_2 = price
            ttime = int(str(data[bot.iter]["date"]) + str(data[bot.iter]["time"]))
            if compare_1 <= compare_2:
                clOrdID = backtest._trade(
                    instrument=self,
                    bot=bot,
                    side=side,
                    qty=qty,
                    price=price,
                    ttime=ttime,
                    clOrdID=clOrdID,
                )
            else:
                if not clOrdID:
                    clOrdID = service.set_clOrdID(emi=bot.name)
                    value = {
                        "leavesQty": qty,
                        "transactTime": ttime,
                        "price": price,
                        "symbol": self.symbol_tuple,
                        "side": side,
                        "orderID": "Not used",
                    }
                    service.fill_order(
                        emi=bot.name,
                        clOrdID=clOrdID,
                        category=self.instrument.category,
                        value=value,
                    )
                else:
                    var.orders[bot.name][clOrdID]["price"] = price
        if cancel:
            if side == "Sell":
                orders = self._filter_by_side(
                    orders=var.orders[bot.name], side="Buy", in_list=False
                )
            else:
                orders = self._filter_by_side(
                    orders=var.orders[bot.name], side="Sell", in_list=False
                )
            for clOrdID in orders:
                del var.orders[bot.name][clOrdID]

        return clOrdID


class MetaTool(type):
    objects = dict()

    def __getitem__(self, item) -> Tool:
        market = self.__qualname__
        symbol = (item, market)
        ws = Markets[market]
        if var.backtest:  # backtest is runnig
            if Markets[market].Instrument.get_keys() is None:
                backtest.get_instrument(ws, symbol)
            if symbol not in MetaInstrument.market[market]:
                backtest.get_instrument(ws, symbol)
        if symbol not in MetaInstrument.market[market]:
            raise ValueError(f"The instrument {symbol} not found.")
        if symbol not in self.objects:
            expire = MetaInstrument.market[market][symbol].expire
            if isinstance(expire, datetime):
                if datetime.now(tz=timezone.utc) > expire:
                    bot_name = name(inspect.stack())
                    bot = Bots[bot_name]
                    bot_path = bot_manager.get_bot_path(bot_name)
                    message = ErrorMessage.BOT_INSTRUMENT_EXPIRED.format(
                        INSTRUMENT=symbol,
                        FILE=bot_path,
                    )
                    bot.error_message = {
                        "error_type": "expired_instrument",
                        "message": message,
                    }
                    var.queue_info.put(
                        {
                            "market": "",
                            "message": message,
                            "time": datetime.now(tz=timezone.utc),
                            "warning": True,
                        }
                    )
                    var.logger.error(message)
            self.objects[symbol] = Tool(MetaInstrument.market[market][symbol])

        return self.objects[symbol]


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
