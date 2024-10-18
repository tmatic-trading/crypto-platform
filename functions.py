import re
import threading
import time
import tkinter as tk
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from random import randint
from typing import Tuple, Union

from dotenv import dotenv_values

import display.bot_menu as bot_menu
import services as service
from api.api import WS, Markets
from api.variables import Variables
from botinit.variables import Variables as robo
from common.data import BotData, Bots, Instrument
from common.variables import Variables as var
from display.functions import info_display
from display.headers import Header
from display.messages import ErrorMessage, Message
from display.option_desk import options_desk
from display.variables import AutoScrollbar
from display.variables import OrderForm as form
from display.variables import SubTreeviewTable, TreeTable, TreeviewTable
from display.variables import Variables as disp


class Function(WS, Variables):
    sql_lock = threading.Lock()

    def calculate(
        self: Markets,
        symbol: tuple,
        price: float,
        qty: float,
        rate: float,
        fund: int,
        execFee: float = None,
    ) -> dict:
        """
        Calculates trade or funding value and commission.

        Parameters
        ----------
        self: Markets
            Market instance.
        symbol: tuple
            Instrument symbol in (symbol, market name) format, e.g.
            ("BTCUSD", "Bybit").
        price: float
            Price of the instrument.
        qty: float
            Quantity of the instrument, negative if sell.
        rate: float
            Comission or funding rate.
        fund: int
            1 - trade, 0 - funding is being calculated.
        execFee: float (optional)
            Some exchanges send the commission and funding already calculated
            in the "execFee" field, so this value will be returned as
            "commission" or "funding" value.

        Returns
        -------
        dict
            "sumreal" - trade value.
            "commiss" - payed commission for trade, negative if maker rebate.
            "funding: - funding value, negative if in favor of the trader.
        """
        instrument = self.Instrument[symbol]
        coef = instrument.valueOfOneContract * instrument.myMultiplier
        if instrument.category in ["inverse", "future reversed"]:
            sumreal = qty / price * fund
            if execFee is not None:
                commiss = execFee
                funding = execFee
            else:
                commiss = abs(qty) / price * rate
                funding = qty / price * rate
        elif instrument.category in ["spot", "spot linear"]:
            sumreal = 0
            if execFee is not None:
                commiss = execFee
            else:
                commiss = abs(qty) * price * rate
            funding = 0
        else:
            sumreal = -qty * price * fund
            if execFee is not None:
                commiss = execFee
                funding = execFee
            else:
                commiss = abs(qty) * price * rate
                funding = qty * price * rate

        return {
            "sumreal": sumreal * coef,
            "commiss": commiss * coef,
            "funding": funding * coef,
        }

    def add_symbol(self: Markets, symb: str, ticker: str, category: str) -> None:
        symbol = (symb, self.name)
        if symbol not in self.Instrument.get_keys():
            qwr = (
                "select * from symbols where SYMBOL ='"
                + symb
                + "' and MARKET = '"
                + self.name
                + "';"
            )
            data = service.select_database(qwr)
            if not data:
                WS.get_instrument(self, ticker=ticker, category=category)
                instrument = self.Instrument[symbol]
                values = [
                    instrument.symbol,
                    instrument.market,
                    instrument.category,
                    instrument.settlCurrency[0],
                    instrument.ticker,
                    instrument.myMultiplier,
                    instrument.multiplier,
                    instrument.tickSize,
                    instrument.price_precision,
                    instrument.minOrderQty,
                    instrument.qtyStep,
                    instrument.precision,
                    instrument.expire,
                    instrument.baseCoin,
                    instrument.quoteCoin,
                    instrument.valueOfOneContract,
                ]
                service.insert_database(values=values, table="symbols")
            else:
                data = data[0]
                instrument = self.Instrument[symbol]
                instrument.symbol = symb
                instrument.market = self.name
                instrument.category = category
                instrument.settlCurrency = (data["CURRENCY"], self.name)
                instrument.ticker = ticker
                instrument.myMultiplier = data["MYMULTIPLIER"]
                instrument.multiplier = data["MULTIPLIER"]
                instrument.tickSize = data["TICKSIZE"]
                instrument.price_precision = data["PRICE_PRECISION"]
                instrument.minOrderQty = data["MINORDERQTY"]
                instrument.qtyStep = data["QTYSTEP"]
                instrument.precision = data["PRECISION"]
                instrument.expire = service.time_converter(time=data["EXPIRE"])
                instrument.baseCoin = data["BASECOIN"]
                instrument.quoteCoin = data["QUOTECOIN"]
                instrument.valueOfOneContract = data["VALUEOFONECONTRACT"]

    def kline_data_filename(self: Markets, symbol: tuple, timefr: str) -> str:
        return "data/" + symbol[0] + "_" + self.name + "_" + str(timefr) + ".txt"

    def save_kline_data(self: Markets, row: dict, symbol: tuple, timefr: int) -> None:
        filename = Function.kline_data_filename(self, symbol=symbol, timefr=timefr)
        zero = (6 - len(str(row["time"]))) * "0"
        data = (
            str(row["date"])
            + ";"
            + str(zero)
            + str(row["time"])
            + ";"
            + str(row["bid"])
            + ";"
            + str(row["ask"])
            + ";"
            + str(row["hi"])
            + ";"
            + str(row["lo"])
            + ";"
        )
        with open(filename, "a") as f:
            f.write(data + "\n")

    def noll(self: Markets, val: str, length: int) -> str:
        r = ""
        for _ in range(length - len(val)):
            r = r + "0"

        return r + val

    def transaction(self: Markets, row: dict, info: str = "") -> None:
        """
        Trades and funding processing
        """

        def handle_trade_or_delivery(row, emi, refer, clientID):
            results = self.Result[row["settlCurrency"]]
            lastQty = row["lastQty"]
            leavesQty = row["leavesQty"]
            if row["side"] == "Sell":
                lastQty = -row["lastQty"]
                leavesQty = -row["leavesQty"]
            calc = Function.calculate(
                self,
                symbol=row["symbol"],
                price=row["lastPx"],
                qty=lastQty,
                rate=row["commission"],
                fund=1,
                execFee=row["execFee"],
            )
            if clientID == "Delivery":
                calc["commiss"] = 0
            instrument = self.Instrument[row["symbol"]]
            instrument.volume += abs(lastQty)
            instrument.sumreal += calc["sumreal"]
            if emi in Bots.keys():
                if row["symbol"] not in Bots[emi].bot_positions:
                    service.fill_bot_position(
                        bot_name=emi,
                        symbol=row["symbol"],
                        instrument=instrument,
                        user_id=Markets[instrument.market].user_id,
                    )
                position = Bots[emi].bot_positions[row["symbol"]]
                if row["category"] != "spot":
                    position["position"] += lastQty
                    position["position"] = round(
                        position["position"],
                        instrument.precision,
                    )
                position["volume"] += abs(lastQty)
                position["commiss"] += calc["commiss"]
                position["sumreal"] += calc["sumreal"]
                position["ltime"] = row["transactTime"]
            results.commission += calc["commiss"]
            results.sumreal += calc["sumreal"]
            values = [
                row["execID"],
                emi,
                refer,
                row["settlCurrency"][0],
                row["symbol"][0],
                instrument.ticker,
                row["category"],
                self.name,
                row["side"],
                lastQty,
                leavesQty,
                row["price"],
                0,
                row["lastPx"],
                calc["sumreal"],
                calc["commiss"],
                clientID,
                row["transactTime"],
                self.user_id,
            ]
            service.insert_database(values=values, table="coins")
            message = {
                "SYMBOL": row["symbol"],
                "MARKET": row["market"],
                "TTIME": row["transactTime"],
                "SIDE": row["side"],
                "TRADE_PRICE": row["lastPx"],
                "QTY": abs(lastQty),
                "EMI": emi,
                "TICKER": instrument.ticker,
                "CATEGORY": instrument.category,
            }
            if not info:
                Function.trades_display(self, table=TreeTable.trades, val=message)
                if emi in Bots.keys():
                    Function.trades_display(
                        self, table=bot_menu.trade_treeTable[emi], val=message
                    )

        var.lock.acquire(True)
        try:
            Function.add_symbol(
                self,
                symb=row["symbol"][0],
                ticker=row["ticker"],
                category=row["category"],
            )
            instrument = self.Instrument[row["symbol"]]
            if "clOrdID" in row:
                if "." not in row["clOrdID"]:
                    del row["clOrdID"]

            # Trade

            if row["execType"] == "Trade":
                if "clOrdID" in row:
                    dot = row["clOrdID"].find(".")
                    if (
                        dot == -1
                    ):  # The transaction was done from the exchange web interface,
                        # the clOrdID field is missing or clOrdID does not have EMI number
                        emi = ""
                        refer = ""
                        if row["clOrdID"] == "":
                            clientID = 0
                        else:
                            try:
                                clientID = int(row["clOrdID"])
                            except Exception:
                                clientID = 0
                    else:
                        emi = row["clOrdID"][dot + 1 :]
                        clientID = row["clOrdID"][:dot]
                        refer = emi
                        symb = emi.split(".")[0]
                        if symb == row["symbol"][0]:
                            refer = ""
                else:
                    emi = ""
                    clientID = 0
                    refer = ""
                if emi not in Bots.keys():
                    emi = ""
                data = service.select_database(  # read_database
                    "select EXECID from coins where EXECID='%s' and account=%s"
                    % (row["execID"], self.user_id),
                )
                if not data:
                    handle_trade_or_delivery(row, emi, refer, clientID)
                Function.orders_processing(self, row=row, info=info)

            # Delivery

            elif row["execType"] == "Delivery":
                results = self.Result[row["settlCurrency"]]
                pos = 0
                if row["side"] == "Sell":
                    lastQty = -row["lastQty"]
                else:
                    lastQty = row["lastQty"]
                for name in Bots.keys():
                    position = Bots[name].bot_positions
                    if (
                        row["symbol"] in position
                        and position[row["symbol"]]["position"] != 0
                    ):
                        qty = position[row["symbol"]]["position"]
                        if qty > 0:
                            row["side"] = "Sell"
                            pos += qty
                        else:
                            row["side"] = "Buy"
                            pos += qty
                        row["lastQty"] = abs(qty)
                        handle_trade_or_delivery(row, name, "", "Delivery")
                diff = -(lastQty + pos)
                if diff != 0:
                    qwr = (
                        "select sum(QTY) as sum from coins where SYMBOL = '"  # d emi
                        + row["symbol"][0]
                        + "' and MARKET = '"
                        + self.name
                        + "' and ACCOUNT = "
                        + str(self.user_id)
                        + " and side <> 'Fund'"
                        + ";"
                    )
                    data = service.select_database(query=qwr)[0]
                    if data["sum"] != diff:
                        message = ErrorMessage.IMPOSSIBLE_DATABASE_POSITION.format(
                            SYMBOL=row["symbol"][0],
                            DELIVERY=diff,
                            MARKET=self.name,
                            POSITION=data["sum"],
                        )
                        _put_message(market=self.name, message=message, warning="error")
                    else:
                        emi = ""
                        if diff > 0:
                            row["side"] = "Sell"
                        else:
                            row["side"] = "Buy"
                        row["lastQty"] = abs(diff)
                        handle_trade_or_delivery(row, emi, "", "Delivery")

            # Funding

            elif row["execType"] == "Funding":
                results = self.Result[row["settlCurrency"]]
                message = {
                    "SYMBOL": row["symbol"],
                    "TTIME": row["transactTime"],
                    "PRICE": row["price"],
                }
                position = 0
                instrument = self.Instrument[row["symbol"]]
                calc = Function.calculate(
                    self,
                    symbol=row["symbol"],
                    price=row["lastPx"],
                    qty=row["lastQty"],
                    rate=row["commission"],
                    fund=0,
                    execFee=row["execFee"],
                )
                message["CATEGORY"] = row["category"]
                message["MARKET"] = self.name
                message["QTY"] = row["lastQty"]
                message["COMMISS"] = calc["funding"]
                message["TICKER"] = instrument.ticker
                values = [
                    row["execID"],
                    "",
                    "",
                    row["settlCurrency"][0],
                    row["symbol"][0],
                    instrument.ticker,
                    row["category"],
                    self.name,
                    "Fund",
                    row["lastQty"],
                    0,
                    row["lastPx"],
                    0,
                    row["price"],
                    calc["sumreal"],
                    calc["funding"],
                    0,
                    row["transactTime"],
                    self.user_id,
                ]
                service.insert_database(values=values, table="coins")
                results.funding += calc["funding"]
                if not info:
                    Function.funding_display(self, message)

            # New order

            elif row["execType"] == "New":
                if (
                    "clOrdID" not in row
                ):  # The order was placed from the exchange web interface
                    emi = service.set_emi(symbol=row["symbol"])
                    clOrdID = service.set_clOrdID(emi=emi)
                    service.fill_order(
                        emi=emi, clOrdID=clOrdID, category=row["category"], value=row
                    )
                    info = "Outside placement:"
                else:
                    info = ""
                Function.orders_processing(self, row=row, info=info)

            # Canceled order

            elif row["execType"] == "Canceled":
                Function.orders_processing(self, row=row)

            # Replaced order

            elif row["execType"] == "Replaced":
                Function.orders_processing(self, row=row)
        finally:
            var.lock.release()

    def orders_processing(self: Markets, row: dict, info: str = "") -> None:
        """
        Orders processing<--transaction()<--(trading_history() or get_exec())

        This function is called from transaction(), which in turn is called
        in two cases:

        1) A new row from the websocket with the corresponding execType is
        received:

        <New>       a new order has been successfully placed.
        <Trade>     the order has been executed, partially or completely.
        <Canceled>  the order has been cancelled.
        <Replaced>  the order has been moved to another price.

        2) A row from trading history (info parameter is "History") is
        received, and since trading history only informs about trades, there
        is only one possible execType:

        <Trade> the order has been executed, partially or completely.

        All orders in var.orders are assigned clOrdID, therefore the task is
        to find the required order and process it according to the execType.
        However, the current row does not necessarily contain clOrdID, so the
        possible scenarios are as follows:

        1) The order was sent via Tmatic.
            Websocket
        clOrdID is always present if the row was received from the websocket
        stream.
            Trading history
        clOrdID is always present for Bitmex and Bybit exchanges. Deribit
        exchange sends clOrdID only for trades for the last 5 days. In case
        of restoring the trading history for an earlier period, then the row
        without clOrdID.

        2) Order was not sent via Tmatic.
        clOrdID is missing. The application searches for order in var.orders
        by orderID. Failure does not always mean an error in case of
        restoring trading history.

        Parameters
        ----------
        self: Markets
            Market instance.
        row: dict
            Information received via web socket stream or downloaded trade
            history.
        info: str
            Possibly "History" in case of trading history or other additional
            information.
        """

        def order_not_found(clOrdID: str) -> None:
            message = (
                "execType "
                + row["execType"]
                + " - order with clOrdID "
                + clOrdID
                + " not found."
            )
            _put_message(market=self.name, message=message, warning="warning")

        if "clOrdID" in row:
            if row["clOrdID"]:
                clOrdID = row["clOrdID"]
                dot = row["clOrdID"].find(".")
                if dot == -1:
                    emi = service.set_emi(symbol=row["symbol"])
                else:
                    emi = row["clOrdID"][dot + 1 :]
            else:
                """Possibly retrieved from Trading history"""
                clOrdID = "Empty"
                emi = "Not_found!"
        else:  # Retrieved from /execution or /execution/tradeHistory. The order was made
            # through the exchange web interface.
            for emi, values in var.orders.items():
                for clOrdID, value in values.items():
                    if value["orderID"] == row["orderID"]:
                        # emi and clOrdID were defined in var.orders
                        break
                else:
                    continue
                break
            else:
                """There is no order with this orderID in the var.orders. The
                order was not sent via Tmatic."""
                clOrdID = "Empty!"
                emi = "Not_found!"
        if "orderID" not in row:
            """Bitmex: orderID is missing when text='Closed to conform to lot
            size'. The last time this happened was on 31.05.2021."""
            row["orderID"] = row["text"]
        price = row["price"]
        info_q = ""
        info_p = ""
        if row["execType"] == "Canceled":
            info_p = price
            info_q = row["orderQty"] - row["cumQty"]
            if emi in var.orders and clOrdID in var.orders[emi]:
                var.queue_order.put(
                    {"action": "delete", "clOrdID": clOrdID, "market": self.name}
                )
                del var.orders[emi][clOrdID]
            else:
                order_not_found(clOrdID=clOrdID)
        else:
            if row["execType"] == "New":
                if "clOrdID" in row and row["clOrdID"]:
                    service.fill_order(
                        emi=emi, clOrdID=clOrdID, category=row["category"], value=row
                    )
                info_p = price
                info_q = row["orderQty"]
            elif row["execType"] == "Trade":
                info_p = row["lastPx"]
                info_q = row["lastQty"]
                if emi in var.orders and clOrdID in var.orders[emi]:
                    precision = self.Instrument[row["symbol"]].precision
                    var.orders[emi][clOrdID]["leavesQty"] -= row["lastQty"]
                    var.orders[emi][clOrdID]["leavesQty"] = round(
                        var.orders[emi][clOrdID]["leavesQty"], precision
                    )
                    if var.orders[emi][clOrdID]["leavesQty"] == 0:
                        del var.orders[emi][clOrdID]
                    var.queue_order.put(
                        {"action": "delete", "clOrdID": clOrdID, "market": self.name}
                    )
                else:
                    if info != "History":
                        order_not_found(clOrdID=clOrdID)
            elif row["execType"] == "Replaced":
                if emi in var.orders and clOrdID in var.orders[emi]:
                    var.orders[emi][clOrdID]["orderID"] = row["orderID"]
                    info_p = price
                    info_q = row["leavesQty"]
                    var.orders[emi][clOrdID]["leavesQty"] = row["leavesQty"]
                    var.queue_order.put(
                        {"action": "delete", "clOrdID": clOrdID, "market": self.name}
                    )
                else:
                    order_not_found(clOrdID=clOrdID)
            if emi in var.orders and clOrdID in var.orders[emi]:
                var.orders[emi][clOrdID]["price"] = price
                var.orders[emi][clOrdID]["transactTime"] = row["transactTime"]
        try:
            t = clOrdID.split(".")
            int(t[0])
            emi = service.set_emi(symbol=t[1:3])
        except ValueError:
            emi = clOrdID
        if info_q:
            info_q = Function.volume(self, qty=info_q, symbol=row["symbol"])
            info_p = Function.format_price(self, number=info_p, symbol=row["symbol"])
            if info != "History":
                message = (
                    row["execType"]
                    + " emi="
                    + emi
                    + ", side="
                    + row["side"]
                    + ", price="
                    + str(info_p)
                    + ", qty="
                    + info_q
                )
                var.queue_info.put(
                    {
                        "market": self.name,
                        "message": message,
                        "time": datetime.now(tz=timezone.utc),
                        "warning": None,
                        "emi": emi,
                    }
                )
            if info:
                info += " - "
            var.logger.info(
                self.name
                + " - "
                + info
                + row["execType"]
                + " - "
                + "side=%s, orderID=%s, clOrdID=%s, price=%s, qty=%s",
                row["side"],
                row["orderID"],
                clOrdID,
                str(info_p),
                info_q,
            )
        if emi in var.orders and clOrdID in var.orders[emi]:
            var.queue_order.put({"action": "put", "order": var.orders[emi][clOrdID]})
            var.orders[emi].move_to_end(clOrdID)
        disp.bot_orders_processing = True

    def trades_display(
        self: Markets, val: dict, table: TreeviewTable, init=False
    ) -> Union[None, list]:
        """
        Update trades widget
        """
        Function.add_symbol(
            self,
            symb=val["SYMBOL"][0],
            ticker=val["TICKER"],
            category=val["CATEGORY"],
        )
        tm = str(val["TTIME"])[2:]
        tm = tm.replace("-", "")
        tm = tm.replace("T", " ")[:15]
        emi = val["EMI"]
        if emi == "":
            emi = var.dash
        row = [
            tm,
            val["SYMBOL"][0],
            val["CATEGORY"],
            val["MARKET"],
            val["SIDE"],
            Function.format_price(
                self,
                number=float(val["TRADE_PRICE"]),
                symbol=val["SYMBOL"],
            ),
            Function.volume(self, qty=val["QTY"], symbol=val["SYMBOL"]),
            emi,
        ]
        if init:
            return row
        table.insert(values=row, market=self.name, configure=val["SIDE"])
        if "No trades" in table.children:
            table.delete(iid="No trades")

    def funding_display(self: Markets, val: dict, init=False) -> Union[None, list]:
        """
        Update funding widget
        """
        Function.add_symbol(
            self,
            symb=val["SYMBOL"][0],
            ticker=val["TICKER"],
            category=val["CATEGORY"],
        )
        tm = str(val["TTIME"])[2:]
        tm = tm.replace("-", "")
        tm = tm.replace("T", " ")[:15]
        row = [
            tm,
            val["SYMBOL"][0],
            val["CATEGORY"],
            val["MARKET"],
            Function.format_price(
                self,
                number=float(val["PRICE"]),
                symbol=val["SYMBOL"],
            ),
            "{:.7f}".format(-val["COMMISS"]),
            Function.volume(self, qty=val["QTY"], symbol=val["SYMBOL"]),
        ]
        if init:
            return row
        configure = "Buy" if val["COMMISS"] <= 0 else "Sell"
        TreeTable.funding.insert(values=row, market=self.name, configure=configure)

    def orders_display(self: Markets, val: dict) -> None:
        """
        Update Orders widget
        """
        symb = val["emi"].split(".")[0]
        if symb == val["symbol"][0]:
            emi = var.dash
        else:
            emi = val["emi"]
        tm = str(val["transactTime"])[2:]
        tm = tm.replace("-", "")
        tm = tm.replace("T", " ")[:15]
        row = [
            tm,
            val["symbol"][0],
            val["category"],
            val["market"],
            val["side"],
            Function.format_price(
                self,
                number=val["price"],
                symbol=val["symbol"],
            ),
            Function.volume(self, qty=val["leavesQty"], symbol=val["symbol"]),
            emi,
        ]
        clOrdID = val["clOrdID"]
        if clOrdID in TreeTable.orders.children:
            TreeTable.orders.delete(iid=clOrdID)
        TreeTable.orders.insert(
            values=row, market=self.name, iid=val["clOrdID"], configure=val["side"]
        )

    def volume(self: Markets, qty: Union[int, float], symbol: tuple) -> str:
        if qty in ["-", "None"]:
            return qty
        if qty == 0:
            qty = "0"
        else:
            instrument = self.Instrument[symbol]
            qty = "{:.{precision}f}".format(qty, precision=instrument.precision)

        return qty

    def format_price(self: Markets, number: Union[float, str], symbol: tuple) -> str:
        if not isinstance(number, str):
            precision = self.Instrument[symbol].price_precision
            number = "{:.{precision}f}".format(number, precision=precision)
            if precision:
                dot = number.find(".")
                if dot == -1:
                    number = number + "."
                n = len(number) - 1 - number.find(".")
                for _ in range(precision - n):
                    number = number + "0"

        return number

    def kline_update_market(self: Markets, utcnow: datetime) -> None:
        """
        Processing timeframes
        """
        for symbol, kline in self.klines.items():
            instrument = self.Instrument[symbol]
            for timefr, values in kline.items():
                timefr_minutes = var.timeframe_human_format[timefr]
                if utcnow > values["time"] + timedelta(minutes=timefr_minutes):
                    Function.save_kline_data(
                        self,
                        row=values["data"][-1],
                        symbol=symbol,
                        timefr=timefr,
                    )
                    next_minute = int(utcnow.minute / timefr_minutes) * timefr_minutes
                    dt_now = utcnow.replace(minute=next_minute, second=0, microsecond=0)
                    values["data"].append(
                        {
                            "date": (utcnow.year - 2000) * 10000
                            + utcnow.month * 100
                            + utcnow.day,
                            "time": utcnow.hour * 10000 + utcnow.minute * 100,
                            "bid": instrument.bids[0][0],
                            "ask": instrument.asks[0][0],
                            "hi": instrument.asks[0][0],
                            "lo": instrument.bids[0][0],
                            "funding": instrument.fundingRate,
                            "datetime": dt_now,
                        }
                    )
                    values["time"] = dt_now

    def refresh_on_screen(self: Markets, utc: datetime) -> None:
        """
        Refresh information on screen
        """
        # adaptive_screen(self)
        if utc.hour != var.refresh_hour:
            service.select_database("select count(*) cou from robots")
            var.refresh_hour = utc.hour
            var.logger.info("Emboldening SQLite")
        current_time = time.gmtime()
        if current_time.tm_sec != disp.last_gmtime_sec:
            # We are here once a second
            asctime = time.asctime(current_time)
            disp.label_time["text"] = (
                "CPU: "
                + str(service.Variables.cpu_usage)
                + "%  MEM: "
                + str(service.Variables.memory_usage)
                + "MB  |  "
                + str(asctime[0 : len(asctime) - 4])
            )
            disp.last_gmtime_sec = current_time.tm_sec
        Function.refresh_tables(self)

    def display_instruments(self: Markets, indx=0):
        tree = TreeTable.instrument
        # d tm = datetime.now()
        for market in var.market_list:
            ws = Markets[market]
            if market == var.current_market:
                for symbol in ws.symbol_list:
                    instrument = ws.Instrument[symbol]
                    compare = [
                        symbol[0],
                        instrument.category,
                        instrument.currentQty,
                        instrument.avgEntryPrice,
                        instrument.unrealisedPnl,
                        instrument.marginCallPrice,
                        instrument.volume24h,
                        instrument.expire,
                        instrument.fundingRate,
                    ]
                    iid = f"{symbol[1]}!{symbol[0]}"
                    if iid in tree.children_hierarchical[market]:
                        if compare != tree.cache[iid]:
                            tree.cache[iid] = compare.copy()
                            tree.update_hierarchical(
                                parent=market,
                                iid=iid,
                                values=Function.form_instrument_line(
                                    self,
                                    compare=compare,
                                    instrument=instrument,
                                    symbol=symbol,
                                ),
                            )
                    else:
                        tree.insert_hierarchical(
                            parent=market,
                            iid=iid,
                            values=Function.form_instrument_line(
                                self,
                                compare=compare,
                                instrument=instrument,
                                symbol=symbol,
                            ),
                            indx=indx,
                            image=disp.image_cancel,
                        )
        if var.rollup_symbol:
            if var.rollup_symbol != "cancel":
                TreeTable.instrument.on_rollup(iid=var.rollup_symbol, setup="child")
                TreeTable.instrument.set_selection(var.rollup_symbol)
                var.rollup_symbol = ""
        # d print("___instrument", datetime.now() - tm)

    def display_account(self: Markets):
        tree = TreeTable.account
        # d tm = datetime.now()
        for market in var.market_list:
            ws = Markets[market]
            for settlCurrency in ws.Account.keys():
                account = ws.Account[settlCurrency]
                compare = [
                    settlCurrency[0],
                    account.walletBalance,
                    account.unrealisedPnl,
                    account.marginBalance,
                    account.orderMargin,
                    account.positionMagrin,
                    account.availableMargin,
                ]
                iid = market + settlCurrency[0]
                if iid in tree.children_hierarchical[market]:
                    if iid not in tree.cache:
                        tree.cache[iid] = []
                    if compare != tree.cache[iid]:
                        tree.cache[iid] = compare.copy()
                        tree.update_hierarchical(
                            parent=market, iid=iid, values=form_result_line(compare)
                        )
                else:
                    tree.insert_hierarchical(
                        parent=market, iid=iid, values=form_result_line(compare)
                    )
        # d print("___account", datetime.now() - tm)

    def display_results(self: Markets):
        tree = TreeTable.results
        # d tm = datetime.now()
        for market in var.market_list:
            ws = Markets[market]
            results = dict()
            for symbol in ws.symbol_list:
                instrument = ws.Instrument[symbol]
                if "spot" not in instrument.category:
                    if instrument.ticker != "option!":
                        if instrument.currentQty != 0:
                            value = Function.close_value(
                                ws, symbol=symbol, pos=instrument.currentQty
                            )
                            currency = instrument.settlCurrency
                            if currency in results:
                                results[currency] += value
                            else:
                                results[currency] = value
            for currency in ws.Result.keys():
                result = ws.Result[currency]
                result.result = 0
                if currency in results:
                    result.result += results[currency]
                compare = [
                    currency[0],
                    result.sumreal + result.result,
                    -result.commission,
                    -result.funding,
                ]
                iid = market + currency[0]
                Function.update_result_line(
                    self,
                    iid=iid,
                    compare=compare,
                    market=market,
                    tree=tree,
                )
            # d print("___result", datetime.now() - tm)

    def display_positions(self: Markets):
        tree = TreeTable.position
        # d tm = datetime.now()
        pos_by_market = {market: [] for market in var.market_list}
        for name in Bots.keys():
            bot = Bots[name]
            for symbol in bot.bot_positions.keys():
                pos_by_market[symbol[1]].append(bot.bot_positions[symbol])
        for market in pos_by_market.keys():
            rest = dict()
            rest_volume = dict()
            rest_sumreal = dict()
            pos = pos_by_market[market]
            notificate = True
            ws = Markets[market]
            for position in pos:
                symbol = (position["symbol"], market)
                if symbol not in rest:
                    rest[symbol] = 0
                    rest_volume[symbol] = 0
                    rest_sumreal[symbol] = 0
                iid = position["emi"] + "!" + position["symbol"]
                if position["position"] == 0:
                    if iid in tree.children_hierarchical[market]:
                        tree.delete_hierarchical(parent=market, iid=iid)
                else:
                    notificate = False
                    pnl = Function.calculate_pnl(
                        ws,
                        symbol=symbol,
                        qty=position["position"],
                        sumreal=position["sumreal"],
                    )
                    rest[symbol] += position["position"]
                    rest_volume[symbol] += position["volume"]
                    rest_sumreal[symbol] += pnl
                    compare = [
                        position["emi"],
                        position["symbol"],
                        position["category"],
                        position["position"],
                        position["volume"],
                        pnl,
                    ]
                    Function.update_position_line(
                        self,
                        iid=iid,
                        compare=compare,
                        columns=[3, 4],
                        symbol=symbol,
                        market=market,
                        tree=tree,
                    )
            for symbol in ws.symbol_list:
                instrument = ws.Instrument[symbol]
                if "spot" not in instrument.category:
                    if instrument.ticker != "option!":
                        pnl = Function.calculate_pnl(
                            ws,
                            symbol=symbol,
                            qty=instrument.currentQty,
                            sumreal=instrument.sumreal,
                        )
                        if symbol in rest:
                            position = instrument.currentQty - rest[symbol]
                            volume = instrument.volume - rest_volume[symbol]
                            pnl = pnl - rest_sumreal[symbol]
                        else:
                            position = instrument.currentQty
                            volume = instrument.volume
                        iid = market + instrument.symbol
                        if position == 0:
                            if iid in tree.children_hierarchical[market]:
                                tree.delete_hierarchical(parent=market, iid=iid)
                        else:
                            notificate = False
                            compare = [
                                var.dash,
                                instrument.symbol,
                                instrument.category,
                                position,
                                volume,
                                pnl,
                            ]
                            Function.update_position_line(
                                self,
                                iid=iid,
                                compare=compare,
                                columns=[3, 4],
                                symbol=symbol,
                                market=market,
                                tree=tree,
                            )
            notification = market + "_notification"
            if notificate:
                if notification not in tree.children_hierarchical[market]:
                    tree.insert_hierarchical(
                        parent=market, iid=notification, text="No positions"
                    )
            else:
                if notification in tree.children_hierarchical[market]:
                    tree.delete_hierarchical(parent=market, iid=notification)
        # d print("___position", datetime.now() - tm)

    def display_robots(self):
        tree = TreeTable.bots
        # d tm = datetime.now()
        for name in Bots.keys():
            bot = Bots[name]
            compare = [
                name,
                bot.timefr,
                bot.state,
                service.bot_error(bot=bot),
                bot.updated,
            ]
            iid = name
            if iid in tree.children:
                if iid not in tree.cache:
                    tree.cache[iid] = []
                if compare != tree.cache[iid]:
                    tree.cache[iid] = compare.copy()
                    tree.update(row=iid, values=compare)
            else:
                tree.insert(iid=iid, values=compare, position="end")
        # d print("___bots", datetime.now() - tm)

    def display_options_desk(self):
        tree = TreeTable.calls
        for num, option in enumerate(options_desk.calls_list):
            if option in options_desk.calls_set:
                instrument = options_desk.ws.Instrument[(option, options_desk.market)]
                compare = [
                    instrument.openInterest,
                    instrument.delta,
                    instrument.bidSize,
                    instrument.bidIv,
                    instrument.bidPrice,
                    instrument.markPrice,
                    instrument.askPrice,
                    instrument.askIv,
                    instrument.askSize,
                ]
            else:
                compare = options_desk.dash
            if compare != tree.cache[num]:
                tree.update(row=num, values=compare)
                tree.cache[num] = compare
        tree = TreeTable.puts
        for num, option in enumerate(options_desk.puts_list):
            if option in options_desk.puts_set:
                instrument = options_desk.ws.Instrument[(option, options_desk.market)]
                compare = [
                    instrument.bidSize,
                    instrument.bidIv,
                    instrument.bidPrice,
                    instrument.markPrice,
                    instrument.askPrice,
                    instrument.askIv,
                    instrument.askSize,
                    instrument.delta,
                    instrument.openInterest,
                ]
            else:
                compare = options_desk.dash
            if compare != tree.cache[num]:
                tree.update(row=num, values=compare)
                tree.cache[num] = compare

    def display_parameters(self, instrument: Instrument):
        if instrument.markPrice != form.cache["markprice"]:
            form.markprice.value["text"] = instrument.markPrice
            form.cache["markprice"] = instrument.markPrice
        if instrument.state != form.cache["state"]:
            if instrument.state == "open":
                form.state.value["text"] = "Open"
            else:
                form.state.value["text"] = instrument.state
            form.cache["state"] = instrument.state
        if "option" in instrument.category:
            if instrument.delta != form.cache["delta"]:
                form.delta.value["text"] = service.number_rounding(
                    number=instrument.delta, precision=6
                )
                form.cache["delta"] = instrument.delta
            if instrument.gamma != form.cache["gamma"]:
                form.gamma.value["text"] = service.number_rounding(
                    number=instrument.gamma, precision=6
                )
                form.cache["delta"] = instrument.gamma
            if instrument.vega != form.cache["vega"]:
                form.vega.value["text"] = service.number_rounding(
                    number=instrument.vega, precision=6
                )
                form.cache["vega"] = instrument.vega
            if instrument.theta != form.cache["theta"]:
                form.theta.value["text"] = service.number_rounding(
                    number=instrument.theta, precision=6
                )
                form.cache["theta"] = instrument.theta
            if instrument.rho != form.cache["rho"]:
                form.rho.value["text"] = service.number_rounding(
                    number=instrument.rho, precision=6
                )
                form.cache["rho"] = instrument.rho

    def refresh_tables(self: Markets) -> None:
        current_notebook_tab = disp.notebook.tab(disp.notebook.select(), "text")
        instrument = self.Instrument[var.symbol]

        # service.count_orders()

        # Refresh instrument table

        Function.display_instruments(self)

        # Refresh orderbook table

        tree = TreeTable.orderbook

        # d tm = datetime.now()

        def display_order_book_values(
            val: list,
            start: int,
            end: int,
            direct: int,
            side: str,
        ) -> None:
            count = 0
            for number in range(start, end, direct):
                if len(val) > count:
                    qty = Function.find_order(self, val[count][0], symbol=var.symbol)
                    if side == "bids":
                        compare = [val[count][0], val[count][1], qty]
                        if compare != tree.cache[number]:
                            tree.cache[number] = compare
                            row = [
                                Function.volume(
                                    self, qty=val[count][1], symbol=var.symbol
                                ),
                                Function.format_price(
                                    self, number=val[count][0], symbol=var.symbol
                                ),
                                "",
                            ]
                            tree.update(row=number, values=row)
                            if qty:
                                TreeTable.orderbook.show_color_cell(
                                    text=Function.volume(
                                        self, qty=qty, symbol=var.symbol
                                    ),
                                    row=number,
                                    column=2,
                                    bg_color=disp.green_color,
                                    fg_color=disp.white_color,
                                )
                            else:
                                TreeTable.orderbook.hide_color_cell(
                                    row=number, column=2
                                )
                    else:
                        compare = [qty, val[count][0], val[count][1]]
                        if compare != tree.cache[number]:
                            tree.cache[number] = compare
                            row = [
                                "",
                                Function.format_price(
                                    self, number=val[count][0], symbol=var.symbol
                                ),
                                Function.volume(
                                    self, qty=val[count][1], symbol=var.symbol
                                ),
                            ]
                            tree.update(row=number, values=row)
                            if qty:
                                TreeTable.orderbook.show_color_cell(
                                    text=Function.volume(
                                        self, qty=qty, symbol=var.symbol
                                    ),
                                    row=number,
                                    column=0,
                                    bg_color=disp.red_color,
                                    fg_color=disp.white_color,
                                )
                            else:
                                TreeTable.orderbook.hide_color_cell(
                                    row=number, column=0
                                )
                else:
                    compare = ["", "", ""]
                    if compare != tree.cache[number]:
                        tree.cache[number] = compare
                        TreeTable.orderbook.hide_color_cell(row=number, column=0)
                        TreeTable.orderbook.hide_color_cell(row=number, column=2)
                        tree.update(row=number, values=compare)
                count += 1

        num = int(disp.num_book / 2)
        display_order_book_values(
            val=instrument.bids,
            start=num,
            end=disp.num_book,
            direct=1,
            side="bids",
        )
        display_order_book_values(
            val=instrument.asks,
            start=num - 1,
            end=-1,
            direct=-1,
            side="asks",
        )
        # d print("___orderbook", datetime.now() - tm)

        # Refresh account table

        if current_notebook_tab == "Account":
            Function.display_account(self)

        # Refresh result table

        elif current_notebook_tab == "Results":
            Function.display_results(self)

        # Refresh position table

        elif current_notebook_tab == "Positions":
            Function.display_positions(self)

        # Refresh bots table

        elif current_notebook_tab == "Bots":
            Function.display_robots(self)

        # Refresh instrument parameters

        Function.display_parameters(self, instrument)

        # Refresh bottom table

        var.display_bottom(self)

        # Refresh market table

        tree = TreeTable.market

        # d tm = datetime.now()
        for num, name in enumerate(var.market_list):
            ws = Markets[name]
            status = str(ws.connect_count) + " " + "ONLINE"
            if not ws.api_is_active:
                status = "RELOADING..."
            compare = service.add_space([ws.name, ws.account_disp, status])
            if compare != tree.cache[name]:
                tree.cache[name] = compare
                tree.update(row=name, values=[compare], text=name)
                configure = "Market" if "ONLINE" in status else "Reload"
                TreeTable.market.paint(row=name, configure=configure)
        # d print("___market", datetime.now() - tm)

        # Refresh options desk

        if options_desk.is_on:
            Function.display_options_desk(self)

        # Refresh bot menu tables

        if disp.refresh_bot_info:
            current_bot_note_tab = disp.bot_note.tab(disp.bot_note.select(), "text")

            # Bot positions table

            if current_bot_note_tab == "Positions":
                # d tm = datetime.now()
                tree = TreeTable.bot_position
                pos_by_market = {market: False for market in var.market_list}
                if disp.bot_name:
                    bot = Bots[disp.bot_name]
                    for symbol, position in bot.bot_positions.items():
                        market = symbol[1]
                        if market not in tree.children:
                            tree.insert_parent(parent=market, configure="Gray")
                        iid = position["emi"] + "!" + position["symbol"]
                        if position["position"] == 0:
                            if iid in tree.children_hierarchical[market]:
                                tree.delete_hierarchical(parent=market, iid=iid)
                        else:
                            pos_by_market[market] = True
                            pnl = Function.calculate_pnl(
                                Markets[position["market"]],
                                symbol=symbol,
                                qty=position["position"],
                                sumreal=position["sumreal"],
                            )
                            compare = [
                                position["symbol"],
                                position["category"],
                                position["position"],
                                position["volume"],
                                pnl,
                            ]
                            Function.update_position_line(
                                self,
                                iid=iid,
                                compare=compare,
                                columns=[2, 3],
                                symbol=symbol,
                                market=market,
                                tree=tree,
                            )
                        for iid in list(tree.children_hierarchical[market]).copy():
                            lst = iid.split("!")
                            if len(lst) == 2:
                                if lst[0] != disp.bot_name:
                                    tree.delete_hierarchical(parent=market, iid=iid)
                    for market in list(tree.children).copy():
                        if market != "notification":
                            if not pos_by_market[market]:
                                tree.delete(iid=market)

                if not tree.children:
                    tree.insert_parent(parent="notification", text="No positions")
                else:
                    if len(tree.children) > 1 and "notification" in tree.children:
                        tree.delete(iid="notification")
                # d print("___bot position", datetime.now() - tm)

            # Bot orders table

            elif current_bot_note_tab == "Orders":
                if disp.bot_orders_processing:
                    bot_menu.refresh_bot_orders()
                    disp.bot_orders_processing = False

            # Bot results table

            elif current_bot_note_tab == "Results":
                tree = TreeTable.bot_results
                result_market = {market: False for market in var.market_list}
                if disp.bot_name:
                    bot = Bots[disp.bot_name]
                    for symbol, value in bot.bot_positions.items():
                        market = value["market"]
                        currency = value["currency"]
                        if market in var.market_list:
                            if not result_market[market]:
                                result_market[market] = dict()
                            pos_value = Function.close_value(
                                ws, symbol=symbol, pos=value["position"]
                            )
                            if currency in result_market[market]:
                                result_market[market][currency]["pnl"] += pos_value
                                result_market[market][currency]["commission"] += value[
                                    "commiss"
                                ]
                            else:
                                result_market[market][currency] = dict()
                                result_market[market][currency]["pnl"] = (
                                    value["sumreal"] + pos_value
                                )
                                result_market[market][currency]["commission"] = value[
                                    "commiss"
                                ]
                lines = set()
                for market, result in result_market.items():
                    if not result:
                        if market in tree.children:
                            tree.delete(iid=market)
                    else:
                        if market not in tree.children:
                            tree.insert_parent(parent=market, configure="Gray")
                        for currency, res in result.items():
                            compare = [
                                currency,
                                res["pnl"],
                                -res["commission"],
                            ]
                            iid = disp.bot_name + "!" + market + "!" + currency
                            lines.add(iid)
                            Function.update_result_line(
                                self,
                                iid=iid,
                                compare=compare,
                                market=market,
                                tree=tree,
                            )
                        for iid in list(tree.children_hierarchical[market]).copy():
                            if iid not in lines:
                                tree.delete_hierarchical(parent=market, iid=iid)
                if not tree.children:
                    tree.insert_parent(parent="notification", text="No results")
                else:
                    if len(tree.children) > 1 and "notification" in tree.children:
                        tree.delete(iid="notification")

    def form_instrument_line(
        self, compare: list, instrument: Instrument, symbol: tuple
    ) -> list:
        compare[2] = Function.volume(self, qty=instrument.currentQty, symbol=symbol)
        compare[3] = Function.format_price(
            self, number=instrument.avgEntryPrice, symbol=symbol
        )
        compare[4] = format_number(number=instrument.unrealisedPnl)
        compare[6] = Function.humanFormat(self, instrument.volume24h, symbol)
        if compare[7] != "Perpetual":
            compare[7] = instrument.expire.strftime("%d%b%y %H:%M")

        return compare

    def update_result_line(
        self, iid: str, compare: list, market: str, tree: TreeviewTable
    ) -> None:
        def form_result_line(compare):
            for num in range(len(compare)):
                compare[num] = format_number(compare[num])

            return compare

        if iid in tree.children_hierarchical[market]:
            if compare != tree.cache[iid]:
                tree.cache[iid] = compare.copy()
                tree.update_hierarchical(
                    parent=market, iid=iid, values=form_result_line(compare)
                )
        else:
            tree.insert_hierarchical(
                parent=market, iid=iid, values=form_result_line(compare)
            )

    def update_position_line(
        self,
        iid: str,
        compare: list,
        columns: list,
        symbol: tuple,
        market: str,
        tree: TreeviewTable,
    ) -> None:
        def form_line(compare):
            for column in columns:
                compare[column] = Function.volume(
                    self,
                    qty=compare[column],
                    symbol=symbol,
                )
            num = columns[1] + 1
            compare[num] = format_number(number=compare[num])
            return compare

        if iid in tree.children_hierarchical[market]:
            if compare != tree.cache[iid]:
                tree.cache[iid] = compare.copy()
                tree.update_hierarchical(
                    parent=market, iid=iid, values=form_line(compare)
                )
        else:
            tree.insert_hierarchical(parent=market, iid=iid, values=form_line(compare))

    def close_value(self: Markets, symbol: tuple, pos: float) -> Union[float, None]:
        """
        Returns the value of the position if it is closed
        """
        instrument = self.Instrument[symbol]
        if pos > 0 and instrument.bids:
            close = instrument.bids[0][0]
        elif pos <= 0 and instrument.asks:
            close = instrument.asks[0][0]
        else:
            return
        calc = Function.calculate(
            self,
            symbol=symbol,
            price=close,
            qty=-pos,
            rate=0,
            fund=1,
        )
        return calc["sumreal"]

    def round_price(self: Markets, symbol: tuple, price: float, rside: int) -> float:
        """
        Round_price() returns rounded price: buy price goes down, sell price
        goes up according to 'tickSize'
        """
        instrument = self.Instrument[symbol]
        coeff = 1 / instrument.tickSize
        result = int(coeff * price) / coeff
        if rside < 0 and result < price:
            result += instrument.tickSize

        return result

    def post_order(
        self: Markets,
        name: str,
        symbol: tuple,
        emi: str,
        side: str,
        price: float,
        qty: int,
    ) -> str:
        """
        This function sends a new order
        """
        price_str = Function.format_price(self, number=price, symbol=symbol)
        clOrdID = ""
        if side == "Sell":
            qty = -qty
        if emi not in Bots.keys():
            emi = service.set_emi(symbol=symbol)
        clOrdID = service.set_clOrdID(emi=emi)
        var.logger.info(
            "Posting symbol="
            + str(symbol)
            + " clOrdID="
            + clOrdID
            + " side="
            + side
            + " price="
            + price_str
            + " qty="
            + str(qty)
        )
        WS.place_limit(
            self, quantity=qty, price=price_str, clOrdID=clOrdID, symbol=symbol
        )

        return clOrdID

    def put_order(
        self: Markets,
        emi: str,
        clOrdID: str,
        price: float,
        qty: int,
    ) -> str:
        """
        Replace orders
        """
        price_str = Function.format_price(
            self, number=price, symbol=var.orders[emi][clOrdID]["symbol"]
        )
        var.logger.info(
            "Putting orderID="
            + var.orders[emi][clOrdID]["orderID"]
            + " clOrdID="
            + clOrdID
            + " price="
            + price_str
            + " qty="
            + str(qty)
        )
        if price != var.orders[emi][clOrdID]["price"]:  # the price alters
            WS.replace_limit(
                self,
                quantity=qty,
                price=price_str,
                orderID=var.orders[emi][clOrdID]["orderID"],
                symbol=var.orders[emi][clOrdID]["symbol"],
            )

        return clOrdID

    def del_order(self: Markets, order: dict, clOrdID: str) -> int:
        """
        Del_order() function cancels orders
        """
        message = "Deleting orderID=" + order["orderID"] + " clOrdID=" + clOrdID
        var.logger.info(message)
        WS.remove_order(self, order=order)

        return self.logNumFatal

    def market_status(self: Markets, status: str, message: str, error=False) -> None:
        row = self.name  # var.market_list.index(self.name)
        if status == "ONLINE":
            line = [
                self.name,
                self.account_disp,
                str(self.connect_count) + " " + status,
            ]
        else:
            line = [self.name, self.account_disp, status]
        values = service.add_space(line)
        TreeTable.market.update(row=row, values=[values])
        if message:
            info_display(market=self.name, message=message)
        if error:
            TreeTable.market.paint(row=row, configure="Reload")
        else:
            TreeTable.market.paint(row=row, configure="Market")
        TreeTable.market.tree.update()

    def humanFormat(self: Markets, volNow: int, symbol: tuple) -> str:
        if volNow == "-":
            return volNow
        if volNow > 1000000000:
            volNow = "{:.2f}".format(round(volNow / 1000000000, 2)) + "B"
        elif volNow > 1000000:
            volNow = "{:.2f}".format(round(volNow / 1000000, 2)) + "M"
        elif volNow > 1000:
            volNow = "{:.2f}".format(round(volNow / 1000, 2)) + "K"
        else:
            volNow = Function.volume(self, qty=volNow, symbol=symbol)

        return volNow

    def find_order(self: Markets, price: float, symbol: str) -> Union[float, str]:
        qty = 0
        for values in var.orders.values():
            for value in values.values():
                if value["price"] == price and value["symbol"] == symbol:
                    qty += value["leavesQty"]
        if not qty:
            qty = ""

        return qty

    def calculate_pnl(
        self: Markets, symbol: tuple, qty: float, sumreal: float
    ) -> Union[float, str]:
        """
        Calculates current position pnl.

        Parameters
        ----------
        symbol: tuple
            Instrument symbol in (symbol, market name) format, e.g.
            ("BTCUSD", "Bybit").
        qty: float
            The quantity of the instrument in this position, negative if sell.
        sumreal:
            Position value.

        Returns
        -------
        float
            PNL value.
        """
        if qty == 0:
            return sumreal

        if symbol in self.symbol_list:
            if qty > 0:
                price = self.Instrument[symbol].bids[0][0]
            else:
                price = self.Instrument[symbol].asks[0][0]
            res = Function.calculate(
                self,
                symbol=symbol,
                price=price,
                qty=-qty,
                rate=0,
                fund=1,
            )
            pnl = sumreal + res["sumreal"]
        else:
            # symbol is not signed, so there is no order book and therefore
            # no position closing price. PNL cannot be calculated.
            pnl = "-"

        return pnl


def form_result_line(compare):
    for num in range(1, 7):
        compare[num] = format_number(compare[num])
    return compare


def delete_instrument_TreeTable(symbol):
    tree = TreeTable.instrument
    tree.delete_hierarchical(parent=symbol[1], iid=symbol[1] + symbol[0])


def handler_order(event) -> None:
    tree = event.widget
    items = tree.selection()
    if items:
        tree.update()
        clOrdID = items[0]
        values = TreeTable.orders.tree.item(clOrdID)["values"]
        indx = TreeTable.orders.title.index("MARKET")
        ws = Markets[values[indx]]
        indx = TreeTable.orders.title.index("BOT")
        emi = str(values[indx])
        if emi == var.dash:
            symbol = (
                values[TreeTable.orders.title.index("SYMBOL")],
                values[TreeTable.orders.title.index("MARKET")],
            )
            emi = service.set_emi(symbol=symbol)

        def on_closing() -> None:
            disp.order_window_trigger = "off"
            order_window.destroy()
            tree.selection_remove(items[0])

        def delete(order: dict, clOrdID: str) -> None:
            try:
                var.orders[emi][clOrdID]
            except KeyError:
                message = "Order " + clOrdID + " does not exist!"
                info_display(market=ws.name, message=message, warning="warning")
                var.logger.info(message)
                return
            if not ws.logNumFatal:
                Function.del_order(ws, order=order, clOrdID=clOrdID)
            else:
                info_display(
                    market=ws.name,
                    message="The operation failed. Websocket closed!",
                    warning="warning",
                )
            on_closing()

        def replace(clOrdID) -> None:
            try:
                var.orders[emi][clOrdID]
            except KeyError:
                message = "Order " + clOrdID + " does not exist!"
                info_display(ws.name, message)
                var.logger.info(message)
                return
            try:
                float(price_replace.get())
            except ValueError:
                info_display(
                    market=ws.name, message="Price must be numeric!", warning="warning"
                )
                return
            if not ws.logNumFatal:
                roundSide = var.orders[emi][clOrdID]["leavesQty"]
                if var.orders[emi][clOrdID]["side"] == "Sell":
                    roundSide = -roundSide
                price = Function.round_price(
                    ws,
                    symbol=var.orders[emi][clOrdID]["symbol"],
                    price=float(price_replace.get()),
                    rside=roundSide,
                )
                if price == var.orders[emi][clOrdID]["price"]:
                    info_display(
                        market=ws.name,
                        message="Price is the same but must be different!",
                        warning="warning",
                    )
                    return
                clOrdID = Function.put_order(
                    ws,
                    emi=emi,
                    clOrdID=clOrdID,
                    price=price,
                    qty=var.orders[emi][clOrdID]["leavesQty"],
                )
            else:
                info_display(
                    market=ws.name,
                    message="The operation failed. Websocket closed!",
                    warning="warning",
                )
            on_closing()

        if disp.order_window_trigger == "off":
            order = var.orders[emi][clOrdID]
            disp.order_window_trigger = "on"
            order_window = tk.Toplevel(disp.root, pady=10, padx=10)
            cx = disp.root.winfo_pointerx()
            cy = disp.root.winfo_pointery()
            order_window.geometry("+{}+{}".format(cx - 200, cy - 50))
            order_window.title("Cancel / Modify order ")
            order_window.protocol("WM_DELETE_WINDOW", on_closing)
            order_window.attributes("-topmost", 1)
            frame_up = tk.Frame(order_window)
            frame_dn = tk.Frame(order_window)
            label1 = tk.Label(frame_up, justify="left")
            order_price = Function.format_price(
                ws,
                number=var.orders[emi][clOrdID]["price"],
                symbol=var.orders[emi][clOrdID]["symbol"],
            )
            label1["text"] = (
                "market\t"
                + var.orders[emi][clOrdID]["symbol"][1]
                + "\nsymbol\t"
                + var.orders[emi][clOrdID]["symbol"][0]
                + "\nside\t"
                + var.orders[emi][clOrdID]["side"]
                + "\nclOrdID\t"
                + clOrdID
                + "\nprice\t"
                + order_price
                + "\nquantity\t"
                + Function.volume(
                    ws,
                    qty=var.orders[emi][clOrdID]["leavesQty"],
                    symbol=var.orders[emi][clOrdID]["symbol"],
                )
            )
            label_price = tk.Label(frame_dn)
            label_price["text"] = "Price "
            label1.pack(side="left")
            button = tk.Button(
                frame_dn,
                text="Delete order",
                command=lambda id=clOrdID: delete(clOrdID=id, order=order),
            )
            price_replace = tk.StringVar(frame_dn, order_price)
            entry_price = tk.Entry(
                frame_dn, width=10, bg=disp.bg_color, textvariable=price_replace
            )
            button_replace = tk.Button(
                frame_dn, text="Replace", command=lambda id=clOrdID: replace(id)
            )
            button.pack(side="right")
            label_price.pack(side="left")
            entry_price.pack(side="left")
            button_replace.pack(side="left")
            frame_up.pack(side="top", fill="x")
            frame_dn.pack(side="top", fill="x")
            change_color(color=disp.title_color, container=order_window)


def first_price(prices: list) -> float:
    if prices:
        return prices[0][0]
    else:
        return "None"


def minimum_qty(qnt):
    minOrderQty = form.instrument.minOrderQty
    if qnt < minOrderQty:
        message = (
            "The "
            + str(var.symbol)
            + " quantity must be greater than or equal to "
            + Function.volume(form.ws, qty=minOrderQty, symbol=var.symbol)
        )
        warning_window(message)
        return "error"
    qnt_d = Decimal(str(qnt))
    qtyStep = Decimal(str(form.instrument.qtyStep))
    if qnt_d % qtyStep != 0:
        message = (
            "The "
            + str(var.symbol)
            + " quantity must be multiple to "
            + Function.volume(form.ws, qty=qtyStep, symbol=var.symbol)
        )
        warning_window(message)
        return "error"


def check_order_warning():
    if form.ws.name == "Bitmex" and var.symbol[1] == "spot":
        warning_window("Tmatic does not support spot trading on Bitmex.")
        return False
    if not form.ws.api_is_active:
        if form.ws.name != "Fake":
            info_display(
                market=form.ws.name,
                message=form.ws.name + ": You cannot add new orders during a reboot.\n",
                warning="warning",
            )
            return False

    return True


def callback_sell_limit() -> None:
    for warning in form.warning.values():
        if warning != "":
            warning_window(warning)
            return
    if check_order_warning():
        emi = form.emi_var.get()
        if emi != "Select":
            try:
                qnt = abs(float(form.qty_var.get()))
                price = float(form.price_var.get())
                res = "yes"
            except Exception:
                warning_window("Fields must be numbers!")
                res = "no"
            if res == "yes" and qnt != 0:
                price = Function.round_price(
                    form.ws, symbol=var.symbol, price=price, rside=-qnt
                )
                if minimum_qty(qnt):
                    return
                Function.post_order(
                    form.ws,
                    name=form.ws.name,
                    symbol=var.symbol,
                    emi=emi,
                    side="Sell",
                    price=price,
                    qty=qnt,
                )
        else:
            warning_window("The selection is empty.")


def callback_buy_limit() -> None:
    for warning in form.warning.values():
        if warning != "":
            warning_window(warning)
            return
    if check_order_warning():
        emi = form.emi_var.get()
        if form.qty_var.get() and form.price_var.get() and emi and emi != "Select":
            try:
                qnt = abs(float(form.qty_var.get()))
                price = float(form.price_var.get())
                res = "yes"
            except Exception:
                warning_window("Fields must be numbers!")
                res = "no"
            if res == "yes" and qnt != 0:
                price = Function.round_price(
                    form.ws, symbol=var.symbol, price=price, rside=qnt
                )
                if minimum_qty(qnt):
                    return
                Function.post_order(
                    form.ws,
                    name=form.ws.name,
                    symbol=var.symbol,
                    emi=emi,
                    side="Buy",
                    price=price,
                    qty=qnt,
                )
        else:
            warning_window("The selection is empty.")


def update_order_form():
    form.ws = Markets[var.current_market]
    form.instrument = form.ws.Instrument[var.symbol]
    if form.ws.name != "Fake":
        if form.instrument.ticker == "option!":
            if var.symbol not in var.selected_option:
                symb = set_option(
                    ws=form.ws, instrument=form.instrument, symbol=var.symbol
                )
                var.symbol = (symb, form.ws.name)
            else:
                var.symbol = var.selected_option[var.symbol]
            form.instrument = form.ws.Instrument[var.symbol]
        form.option_emi["menu"].delete(0, "end")
        form.entry_price.delete(0, "end")
        form.warning[form.price_name] = "The price entry field is empty."
        options = list()
        for name in Bots.keys():
            options.append(name)
        options.append(var.symbol[0])
        for option in options:
            form.option_emi["menu"].add_command(
                label=option,
                command=lambda v=form.emi_var, optn=option: v.set(optn),
            )
        form.option_emi["menu"].insert_separator(len(options) - 1)
        form.emi_var.set("Select")
        form.entry_quantity.delete(0, "end")
        form.entry_quantity.insert(
            0,
            Function.volume(
                form.ws, qty=form.instrument.minOrderQty, symbol=var.symbol
            ),
        )
        title = service.order_form_title()
        form.title["text"] = title
        form.market.value["text"] = form.instrument.market
        form.category.value["text"] = form.instrument.category
        form.settlcurrency.value["text"] = form.instrument.settlCurrency[0]
        if form.instrument.expire != "Perpetual":
            form.expiry.value["text"] = form.instrument.expire.strftime("%d%b%y %H:%M")
        else:
            form.expiry.value["text"] = "Perpetual"
        form.ticksize.value["text"] = Function.format_price(
            form.ws, number=form.instrument.tickSize, symbol=var.symbol
        )
        if "quanto" in form.instrument.category:
            quote_currency = "Contracts"
        elif (
            "inverse" in form.instrument.category
            or "reversed" in form.instrument.category
            or "_rev" in form.instrument.category
        ):
            quote_currency = form.instrument.quoteCoin
        else:
            quote_currency = form.instrument.baseCoin
        if quote_currency == "Contracts":
            form.qty_currency["text"] = "Cont"
        else:
            form.qty_currency["text"] = quote_currency
        form.minOrderQty.value["text"] = (
            quote_currency
            + " "
            + Function.volume(
                form.ws, qty=form.instrument.minOrderQty, symbol=var.symbol
            )
        )
        form.price_currency["text"] = form.instrument.quoteCoin
        form.markprice.value["text"] = form.instrument.markPrice
        form.cache["markprice"] = form.instrument.markPrice
        if form.instrument.state == "open":
            form.state.value["text"] = "Open"
        else:
            form.state.value["text"] = form.instrument.state
        form.cache["state"] = form.instrument.state
        if form.instrument.makerFee != None:
            form.takerfee.sub.grid(row=8, column=0, sticky="NEWS")
            form.makerfee.sub.grid(row=9, column=0, sticky="NEWS")
            form.takerfee.value["text"] = f"{form.instrument.takerFee*100}%"
            form.makerfee.value["text"] = f"{form.instrument.makerFee*100}%"
        else:
            form.takerfee.sub.grid_forget()
            form.makerfee.sub.grid_forget()
        if "option" in form.instrument.category:
            form.delta.sub.grid(row=10, column=0, sticky="NEWS")
            form.gamma.sub.grid(row=11, column=0, sticky="NEWS")
            form.vega.sub.grid(row=12, column=0, sticky="NEWS")
            form.theta.sub.grid(row=13, column=0, sticky="NEWS")
            form.rho.sub.grid(row=14, column=0, sticky="NEWS")
            form.delta.value["text"] = form.instrument.delta
            form.gamma.value["text"] = form.instrument.gamma
            form.vega.value["text"] = form.instrument.vega
            form.theta.value["text"] = form.instrument.theta
            form.rho.value["text"] = form.instrument.rho
        else:
            form.delta.sub.grid_forget()
            form.gamma.sub.grid_forget()
            form.vega.sub.grid_forget()
            form.theta.sub.grid_forget()
            form.rho.sub.grid_forget()


def handler_orderbook(event) -> None:
    tree = event.widget
    items = tree.selection()
    if items:
        tree.update()
        tree.selection_remove(items[0])
        try:
            price = float(tree.item(items[0])["values"][1])
            form.entry_price.delete(0, "end")
            form.entry_price.insert(
                0,
                Function.format_price(
                    form.ws,
                    number=price,
                    symbol=var.symbol,
                ),
            )
        except Exception:
            pass


def format_number(number: Union[float, str]) -> str:
    """
    Rounding a value from 2 to 8 decimal places.
    """
    if not isinstance(number, str):
        after_dot = max(2, 9 - max(1, len(str(int(number)))))
        number = "{:.{num}f}".format(number, num=after_dot)
        number = number.rstrip("0")
        number = number.rstrip(".")

    return number


def set_option(ws: Markets, instrument: Instrument, symbol: tuple):
    series = ws.instrument_index[instrument.category][instrument.settlCurrency[0]][
        symbol[0]
    ]
    if series["CALLS"]:
        symb = series["CALLS"][0]
    elif series["PUTS"]:
        symb = series["PUTS"][0]
    var.selected_option[symbol] = (symb, ws.name)

    return symb


def handler_instrument(event) -> None:
    tree = event.widget
    items = tree.selection()
    if items:
        lst = items[0].split("!")
        market = tree.parent(items[0])
        if len(lst) > 1:
            symb = lst[1]
            if market:
                create = False
                symbol = (symb, market)
                _symb = symb
                ws = Markets[market]
                instrument = ws.Instrument[symbol]
                if var.symbol != symbol:
                    if (
                        "option" in instrument.category
                        and "combo" not in instrument.category
                    ):
                        if symbol in var.selected_option:
                            symbol = var.selected_option[symbol]
                            if var.symbol == symbol:  # Opens the options
                                # desk only on the second click
                                create = True
                            if var.rollup_symbol == "cancel":
                                create = False
                                var.rollup_symbol = ""
                            var.symbol = symbol
                        else:
                            symb = set_option(
                                ws=ws, instrument=instrument, symbol=symbol
                            )
                            symbol = (symb, market)
                            var.symbol = symbol
                            # create = False
                    else:
                        var.symbol = symbol
                    update_order_form()
                    TreeTable.orderbook.clear_color_cell()
                else:
                    var.rollup_symbol = ""
                if time.time() - var.select_time > 0.2:
                    if symbol not in var.unsubscription:
                        bbox = tree.bbox(items[0], "#0")
                        if bbox:
                            width, y = bbox[2], bbox[1]
                            x_pos = tree.winfo_pointerx() - tree.winfo_rootx()
                            y_pos = tree.winfo_pointery() - tree.winfo_rooty()
                            if 1 < x_pos - width < 13:
                                if 5 < y_pos - y < 16:
                                    create = False
                                    t = threading.Thread(
                                        target=confirm_unsubscribe, args=(market, _symb)
                                    )
                                    t.start()
                            if var.message_response:
                                warning_window(var.message_response)
                                var.message_response = ""
                if create:
                    if (
                        "option" in instrument.category
                        and "combo" not in instrument.category
                    ):
                        options_desk.create(
                            instrument=instrument, update=update_order_form
                        )
                        disp.root.update()
                        height = (
                            options_desk.label.winfo_height()
                            + options_desk.calls_headers.winfo_height()
                            + TreeTable.calls.tree.winfo_height()
                        )
                        if height > int(disp.window_height * 0.8):
                            height = int(disp.window_height * 0.8)
                        options_desk.desk.geometry(
                            "{}x{}".format(disp.window_width, height)
                        )
            var.selected_iid[market] = items[0]
        else:
            market = items[0]
            var.current_market = market
            if market in var.selected_iid:
                iid = var.selected_iid[market]
            else:
                iid = market
            TreeTable.instrument.on_rollup(iid=iid, setup="child")


def handler_account(event) -> None:
    tree = event.widget
    items = tree.selection()
    if items:
        tree.update()
        time.sleep(0.05)
        tree.selection_remove(items[0])


def confirm_subscription(market: str, symb: str, timeout=None, init=False) -> None:
    """
    Called when using the Instruments menu or while initial loading if an
    instrument is not subscribed, but unclosed positions are found for it.
    Adds an instrument to a websocket subscription of a specific exchange.
    After receiving confirmation from the exchange, writes the symbol to the
    .env.Subscriptions file.

    Parameters
    ----------
    market: str
        Exchange name.
    symb: str
        Instrument symbol.
    timeout: int
        Subscription confirmation timeout in seconds.
    init: bool
        Prevents writing a symbol to the .env.Subscriptions file on
        initialization and detects symbols that are not subscribed but have
        unclosed positions.
    """
    ws = Markets[market]
    symbol = (symb, market)
    message = Message.SUBSCRIPTION_WAITING.format(SYMBOL=symb, MARKET=market)
    _put_message(market=market, message=message)
    res = ws.subscribe_symbol(symbol=symbol)
    if not res:
        message = Message.SUBSCRIPTION_ADDED.format(SYMBOL=symb)
        _put_message(market=market, message=message)
        ws.symbol_list = [symbol] + ws.symbol_list
        if not init:
            var.env[market]["SYMBOLS"] = [symbol] + var.env[market]["SYMBOLS"]
            value = ", ".join(map(lambda x: x[0], var.env[market]["SYMBOLS"]))
            service.set_dotenv(
                dotenv_path=var.subscriptions,
                key=service.define_symbol_key(market=market),
                value=value,
            )
            var.current_market = ws.name
            var.rollup_symbol = f"{ws.name}!{symb}"
    else:
        message = ErrorMessage.FAILED_SUBSCRIPTION.format(SYMBOL=symb)
        _put_message(market=market, message=message, warning="error")
        ws.logNumFatal = "FATAL"


def confirm_unsubscribe(market: str, symb: str) -> None:
    """
    Removes an instrument from a websocket subscription for a specific
    exchange. After receiving confirmation from the exchange, removes the
    symbol from the .env.Subscriptions file.
    """
    ws = Markets[market]
    if len(ws.symbol_list) == 1:
        var.message_response = ErrorMessage.UNSUBSCRIPTION_WARNING
        return
    symbol = (symb, market)
    if symbol in var.selected_option:
        del var.selected_option[symbol]
    message = Message.UNSUBSCRIPTION_WAITING.format(SYMBOL=symb, MARKET=market)
    _put_message(market=market, message=message)
    var.unsubscription.add(symbol)
    res = ws.unsubscribe_symbol(symbol)
    if not res:
        message = Message.UNSUBSCRIBED.format(SYMBOL=symb)
        _put_message(market=market, message=message)
        ws.symbol_list.remove(symbol)
        var.symbol = ws.symbol_list[0]
        if symbol in var.env[market]["SYMBOLS"]:
            var.env[market]["SYMBOLS"].remove(symbol)
        dotenv_data = dotenv_values(var.subscriptions)
        key = service.define_symbol_key(market=market)
        data = dotenv_data[key].replace(" ", "")
        data = data.split(",")
        for item in ["", symb]:
            while item in data:
                data.remove(item)
        data = ",".join(data)
        service.set_dotenv(var.subscriptions, key=key, value=data)
        tree = TreeTable.instrument
        tree.delete_hierarchical(parent=market, iid=f"{market}!{symb}")
        var.select_time = time.time()
        var.rollup_symbol = "cancel"
        TreeTable.instrument.set_selection(
            index=f"{var.current_market}!{var.symbol[0]}"
        )
        var.current_market = market
        update_order_form()
    else:
        message = ErrorMessage.FAILED_UNSUBSCRIPTION.format(SYMBOL=symb)
        _put_message(market=market, message=message, warning="error")
        ws.logNumFatal = "FATAL"
    var.unsubscription.remove(symbol)


def handler_subscription(event) -> None:
    """
    Opens a websocket subscription for an instrument selected in the
    Instruments menu.

    Parameters
    ----------
    market: str
        Market names such as Bitmex, Bybit.
    symbol: str
        Instrument symbol.
    """
    market = TreeTable.market.active_row
    symb = TreeTable.i_list.active_row
    if market:
        ws = Markets[market]
        symbol = (symb, market)
        if symbol not in ws.symbol_list:
            t = threading.Thread(target=confirm_subscription, args=(market, symb))
            t.start()
        else:
            var.symbol = symbol
            var.current_market = market
            TreeTable.instrument.on_rollup(iid=f"{market}!{symb}", setup="child")
        TreeTable.market.del_sub(TreeTable.market)
        TreeTable.i_list.clear_all()


def handler_bot(event) -> None:
    """
    Handles the event when the bot table is clicked.
    """
    tree = event.widget
    iid = tree.selection()
    if iid:
        iid = tree.selection()[0]
        disp.on_bot_menu("None")
        bot_menu.bot_manager.show(iid)


def warning_window(
    message: str, widget=None, item=None, width=400, height=150, title="Warning"
) -> None:
    def on_closing() -> None:
        warn_window.destroy()
        if widget:
            widget.selection_remove(item)

    warn_window = tk.Toplevel()
    warn_window.geometry(
        "{}x{}+{}+{}".format(
            width,
            height,
            str(disp.screen_width // 2 - width // 2 - randint(0, 7) * 15),
            str(disp.screen_height // 2 - height // 2),
        )
    )
    warn_window.title(title)
    warn_window.protocol("WM_DELETE_WINDOW", on_closing)
    warn_window.attributes("-topmost", 1)
    text = tk.Text(warn_window, wrap="word")
    scroll = AutoScrollbar(warn_window, orient="vertical")
    scroll.config(command=text.yview)
    text.config(yscrollcommand=scroll.set)
    text.insert("insert", message)
    text.grid(row=0, column=0, sticky="NSEW")
    scroll.grid(row=0, column=1, sticky="NS")
    warn_window.grid_columnconfigure(0, weight=1)
    warn_window.grid_rowconfigure(0, weight=1)


def change_color(color: str, container=None) -> None:
    line = container.__dict__.copy()
    if "children" in line:
        del line["children"]
    if "_last_child_ids" in line:
        del line["_last_child_ids"]
    line = str(line)
    if "notebook" not in line and "treeview" not in line:
        container.config(bg=color)
    for child in container.winfo_children():
        if child.winfo_children():
            change_color(color, child)
        elif type(child) is tk.Label:
            child.config(bg=color)
        elif type(child) is tk.Button:
            child.config(bg=color)


def init_bot_treetable_trades():
    for bot_name in Bots.keys():
        bot_menu.init_bot_trades(bot_name)


def clear_tables():
    current_market = var.current_market
    symbol = var.symbol
    var.lock_display.acquire(True)
    TreeTable.instrument.lines = var.market_list
    TreeTable.instrument.init()
    TreeTable.market.lst = var.market_list
    TreeTable.market.init()
    TreeTable.account.lines = var.market_list
    TreeTable.account.init()
    TreeTable.results.lines = var.market_list
    TreeTable.results.init()
    TreeTable.position.lines = var.market_list
    TreeTable.position.init()
    TreeTable.orderbook.set_size(disp.num_book)
    TreeTable.orderbook.init()
    TreeTable.bot_menu.init()
    if "Fake" not in var.market_list:
        for market in var.market_list:
            ws = Markets[market]
            var.current_market = market
            Function.display_instruments(ws, "end")
        if current_market in var.market_list:
            var.current_market = current_market
            ws = Markets[var.current_market]
            if symbol in ws.symbol_list:
                var.symbol = symbol
            else:
                var.symbol = ws.symbol_list[0]
        else:
            var.current_market = var.market_list[0]
            ws = Markets[var.current_market]
            var.symbol = ws.symbol_list[0]
        if ws.name in var.selected_iid:
            iid = var.selected_iid[ws.name]
        else:
            iid = ws.name
        TreeTable.instrument.on_rollup(iid=iid, setup="child")
        update_order_form()
    var.lock_display.release()


def target_time(timeframe_sec):
    now = datetime.now(tz=timezone.utc).timestamp()
    target_tm = now + (timeframe_sec - now % timeframe_sec)

    return target_tm


def bot_in_thread(bot_name: str, target_tm: float, bot: BotData):
    """
    Bot entry point
    """
    while var.bot_thread_active[bot_name]:
        tm = time.time()
        if tm > target_tm:
            target_tm = target_time(bot.timefr_sec)
            bot.timefr_current = bot.timefr
            if disp.f9 == "ON":
                if bot.state == "Active":
                    if not bot.error_message:
                        if callable(robo.run[bot_name]):
                            # Calls strategy function in the strategy.py file
                            robo.run[bot_name]()
        time.sleep(1 - time.time() % 1)


def activate_bot_thread(bot_name: str) -> None:
    var.bot_thread_active[bot_name] = True
    bot = Bots[bot_name]
    target_tm = target_time(bot.timefr_sec)
    t = threading.Thread(
        target=bot_in_thread,
        args=(
            bot_name,
            target_tm,
            bot,
        ),
    )
    t.start()


def download_kline_data(
    self: Markets, start_time: datetime, target: datetime, symbol: tuple, timeframe: int
) -> Tuple[Union[list, None], Union[datetime, None]]:
    res = list()
    while target > start_time:
        data = WS.trade_bucketed(
            self, symbol=symbol, time=start_time, timeframe=timeframe
        )
        if isinstance(data, list):
            last = start_time
            res += data
            start_time = data[-1]["timestamp"] + timedelta(minutes=timeframe)
            if last == start_time or target <= data[-1]["timestamp"]:
                return res

        else:
            message = "When downloading trade/bucketed data, list was recieved. Reboot."
            var.logger.error(message)
            return service.unexpected_error(self)

    return res


def kline_update():
    while var.kline_update_active:
        utcnow = datetime.now(tz=timezone.utc)
        var.lock_kline_update.acquire(True)
        for market in var.market_list:
            ws = Markets[market]
            if ws.api_is_active:
                Function.kline_update_market(ws, utcnow=utcnow)
        var.lock_kline_update.release()
        rest = 1 - time.time() % 1
        time.sleep(rest)


def merge_klines(data: list, timefr_minutes: int, prev: int):
    op = 0
    hi = 0
    lo = 0
    cl = 0
    res = list()
    prev, fl = None, "append"
    for el in data:
        m = el["timestamp"]
        delta = timedelta(
            minutes=timefr_minutes
            - m.minute % timefr_minutes
            - (m.hour * 60) % timefr_minutes
        )
        next_t = el["timestamp"] + delta
        if prev != next_t:
            if op != 0:
                res.append(
                    {
                        "timestamp": timestamp,
                        "symbol": symbol,
                        "open": op,
                        "high": hi,
                        "low": lo,
                        "close": cl,
                    }
                )
            timestamp = el["timestamp"]
            op = el["open"]
            hi = el["high"]
            lo = el["low"]
            cl = el["close"]
            symbol = el["symbol"]
            fl = "append"
        else:
            if el["high"] > hi:
                hi = el["high"]
            if el["low"] < lo:
                lo = el["low"]
            cl = el["close"]
            fl = ""
        prev = next_t
    if fl == "":
        res.append(
            {
                "timestamp": timestamp,
                "symbol": symbol,
                "open": op,
                "high": hi,
                "low": lo,
                "close": cl,
            }
        )

    return res


def load_klines(
    self: Markets,
    symbol: tuple,
    timefr: str,
    klines: dict,
) -> Union[dict, None]:
    """
    Loading kline data from the exchange server. Data is recorded
    in files for each timeframe. Every time you reboot the files are
    overwritten.
    """
    filename = Function.kline_data_filename(self, symbol=symbol, timefr=timefr)
    with open(filename, "w") as f:
        f.write("date;time;open bid;open ask;hi;lo;" + "\n")
    target = datetime.now(tz=timezone.utc)
    target = target.replace(second=0, microsecond=0)
    timefr_minutes = var.timeframe_human_format[timefr]
    prev = 1
    for tf_min in reversed(self.timefrs.keys()):
        if tf_min == timefr_minutes:
            prev = tf_min
            break
        elif tf_min < timefr_minutes:
            if timefr_minutes % tf_min == 0:
                prev = tf_min
                break
    factor = int(timefr_minutes / prev)
    timefr_minutes = prev
    start_time = target - timedelta(
        minutes=robo.CANDLESTICK_NUMBER * timefr_minutes * factor - timefr_minutes
    )
    delta = timedelta(
        minutes=target.minute % timefr_minutes + (target.hour * 60) % timefr_minutes
    )
    target -= delta

    # Loading timeframe data

    res = download_kline_data(
        self,
        start_time=start_time,
        target=target,
        symbol=symbol,
        timeframe=timefr_minutes,
    )

    if not res:
        message = str(symbol) + " " + str(timefr) + " kline data was not loaded!"
        var.logger.error(message)
        return None

    # Bitmex bug fix. Bitmex can send data with the next period's
    # timestamp typically for 5m and 60m.
    if target < res[-1]["timestamp"]:
        delta = timedelta(minutes=timefr_minutes)
        for r in res:
            r["timestamp"] -= delta

    # The 'klines' array is filled with timeframe data.
    if res[0]["timestamp"] > res[-1]["timestamp"]:
        res.reverse()

    if factor > 1:
        res = merge_klines(data=res, timefr_minutes=timefr_minutes, prev=prev)

    klines[symbol][timefr]["data"] = []
    for num, row in enumerate(res):
        tm = row["timestamp"] - timedelta(minutes=timefr_minutes)
        klines[symbol][timefr]["data"].append(
            {
                "date": (tm.year - 2000) * 10000 + tm.month * 100 + tm.day,
                "time": tm.hour * 10000 + tm.minute * 100,
                "bid": float(row["open"]),
                "ask": float(row["open"]),
                "hi": float(row["high"]),
                "lo": float(row["low"]),
                "datetime": tm,
            }
        )
        if num < len(res) - 1:
            Function.save_kline_data(
                self,
                row=klines[symbol][timefr]["data"][-1],
                symbol=symbol,
                timefr=timefr,
            )
    klines[symbol][timefr]["time"] = tm

    return klines


def add_new_kline(self: Markets, symbol: tuple, bot_name: str, timefr: int) -> None:
    """
    Adds a new kline to the dictionary klines for the given exchange. If the
    given timefr already exists in the dictionary klines[symbol], then only
    adds bot_name to the set "robots", otherwise first creates a new timefr
    element. If the given symbol does not exist in the dictionary klines,
    then first adds the symbol to klines, then adds timefr to klines[symbol],
    and finally adds bot_name to the set "robots" in klines[symbol][timefr].
    """
    time = datetime.now(tz=timezone.utc)

    def append_new():
        self.klines[symbol][timefr] = {
            "time": time,
            "robots": set(),
            "open": 0,
            "data": [],
        }
        self.klines[symbol][timefr]["robots"].add(bot_name)

    try:
        self.klines[symbol][timefr]["robots"].add(bot_name)
    except KeyError:
        try:
            append_new()
        except KeyError:
            self.klines[symbol] = dict()
            append_new()


def init_market_klines(
    self: Markets,
) -> Union[dict, None]:
    """
    Downloads kline data from the endpoint of the specific exchange.
    """
    success = []

    def get_in_thread(symbol: tuple, timefr: str, klines: dict, number: int):
        nonlocal success
        res = load_klines(
            self,
            symbol=symbol,
            timefr=timefr,
            klines=klines,
        )
        if not res:
            return

        success[number] = "success"

    threads = []

    for symbol, timeframes in self.klines.items():
        for timefr in timeframes.keys():
            success.append(None)
            t = threading.Thread(
                target=get_in_thread,
                args=(symbol, timefr, self.klines, len(success) - 1),
            )

            threads.append(t)
            t.start()

    [thread.join() for thread in threads]
    for s in success:
        if not s:
            return

    return "success"


def init_bot_klines(bot_name: str) -> None:
    """
    Downloads kline data from exchange endpoints for a given bot. This
    happens when a specific bot's strategy.py file is updated.
    """
    success = []

    def get_in_thread(
        ws: Markets, symbol: tuple, timefr: str, klines: dict, number: int
    ):
        nonlocal success
        res = load_klines(
            ws,
            symbol=symbol,
            timefr=timefr,
            klines=klines,
        )
        if not res:
            return
        success[number] = "success"

    kline_to_download = list()
    for market in var.market_list:
        ws = Markets[market]
        for symbol, timeframes in ws.klines.items():
            for timefr, value in timeframes.items():
                if bot_name in value["robots"]:
                    if not value["data"]:
                        itm = {
                            "symbol": symbol,
                            "bot_name": bot_name,
                            "timefr": timefr,
                            "market": market,
                        }
                        kline_to_download.append(itm)
        """for item in ws.klin_set:
            if item[1] == bot_name:
                symbol = (item[0], market)
                if not ws.klines[symbol][item[2]]["data"]:
                    itm = {
                        "symbol": item[0],
                        "bot_name": item[1],
                        "timefr": item[2],
                        "market": market,
                    }
                    kline_to_download.append(itm)"""
    while kline_to_download:
        success = []
        threads = []
        for num, kline in enumerate(kline_to_download):
            success.append(None)
            ws = Markets[kline["market"]]
            t = threading.Thread(
                target=get_in_thread,
                args=(ws, kline["symbol"], kline["timefr"], ws.klines, num),
            )
            threads.append(t)
            t.start()
        [thread.join() for thread in threads]
        for num in range(len(success) - 1, -1, -1):
            if success[num]:
                kline_to_download.pop(num)
            else:
                message = (
                    kline_to_download[num]["market"]
                    + " "
                    + kline_to_download[num]["symbol"]
                    + " "
                    + kline_to_download[num]["timefr"]
                    + " kline is not loaded."
                )
                var.logger.error(message)
                time.sleep(2)


def remove_bot_klines(bot_name: str) -> None:
    """
    Removes the bot's subscription to kline data when deleting the bot in the
    Bot menu.
    """
    for market in var.market_list:
        ws = Markets[market]
        ws.klines
        for symbol, timeframes in ws.klines.items():
            copy = timeframes.copy()
            for timefr, value in copy.items():
                if bot_name in value["robots"]:
                    ws.klines[symbol][timefr]["robots"].remove(bot_name)
                    if not ws.klines[symbol][timefr]["robots"]:
                        var.lock_kline_update.acquire(True)
                        del ws.klines[symbol][timefr]
                        if not ws.klines:
                            del ws.klines[symbol]
                        var.lock_kline_update.release()


def setup_klines():
    """
    Initializing kline data on boot or reboot <f3>
    """

    def get_klines(ws: Markets, success):
        if init_market_klines(ws):
            success[ws.name] = "success"

    market_list = var.market_list.copy()
    while market_list:
        threads = []
        success = {market: None for market in market_list}
        for market in market_list:
            ws = Markets[market]
            success[market] = None
            t = threading.Thread(
                target=get_klines,
                args=(ws, success),
            )
            threads.append(t)
            t.start()
        [thread.join() for thread in threads]
        for market, value in success.items():
            if not value:
                var.logger.error(market + ": Klines are not loaded.")
                time.sleep(2)
            else:
                indx = market_list.index(market)
                market_list.pop(indx)


def _put_message(market: str, message: str, warning=None) -> None:
    """
    Places an information message into the queue and the logger.
    """
    var.queue_info.put(
        {
            "market": market,
            "message": message,
            "time": datetime.now(tz=timezone.utc),
            "warning": warning,
        }
    )
    if not warning:
        var.logger.info(market + " - " + message)
    elif warning == "warning":
        var.logger.warning(market + " - " + message)
    else:
        var.logger.error(market + " - " + message)


def clear_klines():
    """
    Erase all kline data.
    """
    for market in var.market_list:
        Markets[market].klines = dict()


TreeTable.orderbook = TreeviewTable(
    frame=disp.frame_orderbook,
    name="orderbook",
    title=Header.name_book,
    size=disp.num_book,
    style="orderbook.Treeview",
    bind=handler_orderbook,
    multicolor=True,
    autoscroll=True,
)
TreeTable.instrument = TreeviewTable(
    frame=disp.frame_instrument,
    name="instrument",
    title=Header.name_instrument,
    bind=handler_instrument,
    hierarchy=True,
    lines=var.market_list,
    hide=["7", "8", "9"],
)
TreeTable.account = TreeviewTable(
    frame=disp.frame_account,
    name="account",
    title=Header.name_account,
    bind=handler_account,
    hierarchy=True,
    lines=var.market_list,
    hide=["3", "5", "6"],
)
TreeTable.i_list = SubTreeviewTable(
    frame=disp.frame_i_list,
    name="list",
    size=0,
    style="menu.Treeview",
    title=["Instrument"],
    bind=handler_subscription,
)
TreeTable.i_currency = SubTreeviewTable(
    frame=disp.frame_i_currency,
    name="currency",
    size=0,
    style="menu.Treeview",
    title=["Currency"],
    subtable=TreeTable.i_list,
)
TreeTable.i_category = SubTreeviewTable(
    frame=disp.frame_i_category,
    name="category",
    size=0,
    style="menu.Treeview",
    title=["Category"],
    subtable=TreeTable.i_currency,
)
TreeTable.market = SubTreeviewTable(
    frame=disp.frame_market,
    name="market",
    title=Header.name_market,
    size=var.market_list,
    style="market.Treeview",
    autoscroll=True,
    subtable=TreeTable.i_category,
    selectmode="none",
)
TreeTable.results = TreeviewTable(
    frame=disp.frame_results,
    name="results",
    title=Header.name_results,
    hierarchy=True,
    lines=var.market_list,
)
TreeTable.position = TreeviewTable(
    frame=disp.frame_positions,
    name="position",
    title=Header.name_position,
    hierarchy=True,
    lines=var.market_list,
)
TreeTable.bots = TreeviewTable(
    frame=disp.frame_bots,
    name="bots",
    title=Header.name_bots,
    bind=handler_bot,
    hierarchy=False,
)
TreeTable.bot_menu = TreeviewTable(
    frame=bot_menu.menu_frame,
    name="bot_menu",
    title=Header.name_bot_menu,
    style="bots.Treeview",
    bind=bot_menu.handler_bot_menu,
    autoscroll=True,
    hierarchy=True,
    rollup=True,
)
TreeTable.bot_info = TreeviewTable(
    frame=disp.frame_bot_parameters,
    name="bot_info",
    title=Header.name_bot,
    bind=bot_menu.handler_bot_info,
    size=1,
    autoscroll=True,
)
TreeTable.bot_position = TreeviewTable(
    frame=disp.bot_positions,
    name="bot_position",
    title=Header.name_bot_position,
    autoscroll=True,
    hierarchy=True,
    lines=var.market_list,
)
TreeTable.bot_results = TreeviewTable(
    frame=disp.bot_results,
    name="bot_results",
    title=Header.name_bot_results,
    autoscroll=True,
    hierarchy=True,
)

TreeTable.orders = TreeviewTable(
    frame=disp.frame_orders,
    name="orders",
    size=0,
    title=Header.name_order,
    bind=handler_order,
    hide=["8", "3", "5"],
)
TreeTable.trades = TreeviewTable(
    frame=disp.frame_trades,
    name="trades",
    size=0,
    title=Header.name_trade,
    bind=handler_account,
    hide=["8", "3", "5"],
)
TreeTable.funding = TreeviewTable(
    frame=disp.frame_funding,
    name="funding",
    size=0,
    title=Header.name_funding,
    bind=handler_account,
    hide=["3", "5"],
)
TreeTable.bot_orders = TreeviewTable(
    frame=disp.bot_orders,
    name="bot_orders",
    size=0,
    title=Header.name_bot_order,
    bind=handler_order,
    hide=["8", "3", "5"],
)


def do_nothing(*args, **kwargs):
    pass


disp.notebook_frames["Orders"] = {"frame": disp.frame_orders, "method": do_nothing}
disp.notebook_frames["Positions"] = {
    "frame": disp.frame_positions,
    "method": Function.display_positions,
}
disp.notebook_frames["Trades"] = {"frame": disp.frame_trades, "method": do_nothing}
disp.notebook_frames["Funding"] = {"frame": disp.frame_funding, "method": do_nothing}
disp.notebook_frames["Account"] = {
    "frame": disp.frame_account,
    "method": Function.display_account,
}
disp.notebook_frames["Results"] = {
    "frame": disp.frame_results,
    "method": Function.display_results,
}
disp.notebook_frames["Bots"] = {
    "frame": disp.frame_bots,
    "method": Function.display_robots,
}

for name, values in disp.notebook_frames.items():
    if name != "Bots":
        disp.notebook.add(values["frame"], text=name)
    else:
        var.display_bottom = values["method"]


def form_trace(item, index, mode, str_var: tk.StringVar, widget: tk.Entry) -> None:
    """
    Formats the price and quantity on an order form according to the
    precision of the values ​​in the specified instrument.
    """
    ws = Markets[var.current_market]
    instrument = ws.Instrument[var.symbol]
    if item == form.price_name:
        precision = instrument.price_precision
        step = instrument.tickSize
    elif item == form.qty_name:
        precision = instrument.precision
        step = instrument.qtyStep
    number = re.sub("[^\d\.]", "", str_var.get())
    number = number.split(".")
    if len(number) > 1:
        number[1] = number[1][:precision]
    number = ".".join(number[:2])
    if len(number) > 1 and number[0] == ".":
        number = "0" + number
    if number != "":
        num = Decimal(str(number)) / Decimal(str(step))
        if int(num) != float(num) or float(num) == 0:
            widget.config(foreground=disp.red_color)
            form.warning[item] = f"Incorrect {item}."
        else:
            widget.config(foreground=disp.fg_color)
            form.warning[item] = ""
    else:
        form.warning[item] = f"The {item} entry field is empty."
    cursor = widget.index(tk.INSERT)
    widget.delete(0, tk.END)
    widget.insert(0, number)
    widget.icursor(cursor)


form.sell_limit.configure(command=callback_sell_limit)
form.buy_limit.configure(command=callback_buy_limit)
form.price_var.trace_add(
    "write",
    lambda *trace: form_trace(*trace, form.price_var, form.entry_price),
)
form.qty_var.trace_add(
    "write",
    lambda *trace: form_trace(*trace, form.qty_var, form.entry_quantity),
)

# change_color(color=disp.title_color, container=disp.root)
