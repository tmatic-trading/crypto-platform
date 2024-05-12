import threading
import time
import tkinter as tk
from datetime import datetime, timedelta
from decimal import Decimal
from random import randint
from typing import Union

from api.api import WS, Markets
from api.variables import Variables
from bots.variables import Variables as bot
from common.variables import Variables as var
from display.functions import info_display
from display.variables import TreeTable, TreeviewTable
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
        execFee=None,
    ) -> dict:
        """
        Calculate sumreal and commission
        """
        instrument = self.Instrument[symbol]
        coef = abs(
            instrument.multiplier / self.currency_divisor[instrument.settlCurrency[0]]
        )
        if symbol[1] == "inverse":
            sumreal = qty / price * coef * fund
            if execFee:
                commiss = execFee
            else:
                commiss = abs(qty) / price * coef * rate
            funding = qty / price * coef * rate
        elif symbol[1] == "spot":
            sumreal = 0
            if execFee:
                commiss = execFee
            else:
                commiss = abs(qty) * price * coef * rate
            funding = 0
        else:
            sumreal = -qty * price * coef * fund
            if execFee:
                commiss = execFee
            else:
                commiss = abs(qty) * price * coef * rate
            funding = qty * price * coef * rate

        return {"sumreal": sumreal, "commiss": commiss, "funding": funding}

    def add_symbol(self: Markets, symbol: tuple) -> None:
        if symbol not in self.full_symbol_list:
            self.full_symbol_list.append(symbol)
            if symbol not in self.Instrument.get_keys():
                WS.get_instrument(Markets[symbol[2]], symbol=symbol)
            # Function.rounding(self)
        """if symbol not in self.positions:
            WS.get_position(self, symbol=symbol)"""

    def timeframes_data_filename(self: Markets, symbol: tuple, timefr: str) -> str:
        return "data/" + symbol[0] + "_" + symbol[1] + "_" + str(timefr) + ".txt"

    def save_timeframes_data(self: Markets, frame: dict) -> None:
        zero = (6 - len(str(frame["time"]))) * "0"
        data = (
            str(frame["date"])
            + ";"
            + str(zero)
            + str(frame["time"])
            + ";"
            + str(frame["bid"])
            + ";"
            + str(frame["ask"])
            + ";"
            + str(frame["hi"])
            + ";"
            + str(frame["lo"])
            + ";"
        )
        with open(self.filename, "a") as f:
            f.write(data + "\n")

    def noll(self: Markets, val: str, length: int) -> str:
        r = ""
        for _ in range(length - len(val)):
            r = r + "0"

        return r + val

    def select_database(self: Markets, query: str) -> list:
        err_locked = 0
        while True:
            try:
                Function.sql_lock.acquire(True)
                var.cursor_sqlite.execute(query)
                orig = var.cursor_sqlite.fetchall()
                Function.sql_lock.release()
                data = []
                if orig:
                    data = list(map(lambda x: dict(zip(orig[0].keys(), x)), orig))
                return data
            except Exception as e:  # var.error_sqlite
                if "database is locked" not in str(e):
                    var.logger.error("Sqlite Error: " + str(e) + ")")
                    Function.sql_lock.release()
                    break
                else:
                    err_locked += 1
                    var.logger.error(
                        "Sqlite Error: Database is locked (attempt: "
                        + str(err_locked)
                        + ")"
                    )
                    Function.sql_lock.release()

    def insert_database(self: Markets, values: list) -> None:
        err_locked = 0
        while True:
            try:
                Function.sql_lock.acquire(True)
                var.cursor_sqlite.execute(
                    "insert into coins (EXECID,EMI,REFER,CURRENCY,SYMBOL,CATEGORY,MARKET,\
                        SIDE,QTY,QTY_REST,PRICE,THEOR_PRICE,TRADE_PRICE,SUMREAL,COMMISS,\
                            CLORDID,TTIME,ACCOUNT) VALUES (?,?,?,?,?,?,?,?,?,?,\
                                ?,?,?,?,?,?,?,?)",
                    values,
                )
                var.connect_sqlite.commit()
                Function.sql_lock.release()
                break
            except Exception as e:  # var.error_sqlite
                if "database is locked" not in str(e):
                    var.logger.error("Sqlite Error: " + str(e) + " execID=" + values[0])
                    Function.sql_lock.release()
                    break
                else:
                    err_locked += 1
                    var.logger.error(
                        "Sqlite Error: Database is locked (attempt: "
                        + str(err_locked)
                        + ")"
                    )
                    var.connect_sqlite.rollback()
                    Function.sql_lock.release()

    def transaction(self: Markets, row: dict, info: str = "") -> None:
        """
        Trades and funding processing
        """
        Function.add_symbol(self, symbol=row["symbol"])

        # Trade

        if row["execType"] == "Trade":
            results = self.Result[row["settlCurrency"]]
            if "clOrdID" in row:
                dot = row["clOrdID"].find(".")
                if (
                    dot == -1
                ):  # The transaction was done from the exchange web interface,
                    # the clOrdID field is missing or clOrdID does not have EMI number
                    emi = ".".join(row["symbol"][:2])
                    refer = ""
                    if row["clOrdID"] == "":
                        clientID = 0
                    else:
                        clientID = int(row["clOrdID"])
                else:
                    emi = row["clOrdID"][dot + 1 :]
                    clientID = row["clOrdID"][:dot]
                    refer = emi
            else:
                emi = ".".join(row["symbol"][:2])
                clientID = 0
                refer = ""
            if emi not in self.robots:
                emi = ".".join(row["symbol"][:2])
                if emi not in self.robots:
                    if row["symbol"] in self.symbol_list:
                        status = "RESERVED"
                    else:
                        status = "NOT IN LIST"
                    self.robots[emi] = {
                        "STATUS": status,
                        "TIMEFR": None,
                        "EMI": emi,
                        "SYMBOL": row["symbol"],
                        "CATEGORY": row["symbol"][1],
                        "MARKET": self.name,
                        "POS": 0,
                        "VOL": 0,
                        "COMMISS": 0,
                        "SUMREAL": 0,
                        "LTIME": row["transactTime"],
                        "PNL": 0,
                        "CAPITAL": None,
                    }
                    message = (
                        "Robot EMI="
                        + str(emi)
                        + ". Adding to 'robots' with STATUS="
                        + status
                    )
                    if not info:
                        info_display(self.name, message)
                    var.logger.info(message)
            data = Function.select_database(  # read_database
                self,
                "select EXECID from coins where EXECID='%s' and account=%s"
                % (row["execID"], self.user_id),
            )
            if not data:
                lastQty = row["lastQty"]
                leavesQty = row["leavesQty"]
                if row["side"] == "Sell":
                    lastQty = -row["lastQty"]
                    leavesQty = -row["leavesQty"]
                calc = Function.calculate(
                    self,
                    symbol=row["symbol"],
                    price=row["lastPx"],
                    qty=float(lastQty),
                    rate=row["commission"],
                    fund=1,
                    execFee=row["execFee"],
                )
                if row["symbol"][1] != "spot":
                    self.robots[emi]["POS"] += lastQty
                    self.robots[emi]["POS"] = round(
                        self.robots[emi]["POS"],
                        self.Instrument[row["symbol"]].precision,
                    )
                self.robots[emi]["VOL"] += abs(lastQty)
                self.robots[emi]["COMMISS"] += calc["commiss"]
                self.robots[emi]["SUMREAL"] += calc["sumreal"]
                self.robots[emi]["LTIME"] = row["transactTime"]
                results.commission += calc["commiss"]
                results.sumreal += calc["sumreal"]
                values = [
                    row["execID"],
                    emi,
                    refer,
                    row["settlCurrency"][0],
                    row["symbol"][0],
                    row["symbol"][1],
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
                Function.insert_database(self, values=values)
                message = {
                    "SYMBOL": row["symbol"],
                    "MARKET": row["market"],
                    "TTIME": row["transactTime"],
                    "SIDE": row["side"],
                    "TRADE_PRICE": row["lastPx"],
                    "QTY": abs(lastQty),
                    "EMI": emi,
                }
                if info:
                    Function.fill_columns(
                        self, func=Function.trades_display, table=trades, val=message
                    )
                else:
                    Function.trades_display(self, val=message)
                Function.orders_processing(self, row=row, info=info)

        # Funding

        elif row["execType"] == "Funding":
            results = self.Result[row["settlCurrency"]]
            message = {
                "SYMBOL": row["symbol"],
                "TTIME": row["transactTime"],
                "PRICE": row["price"],
            }
            position = 0
            for emi in self.robots:
                if (
                    self.robots[emi]["SYMBOL"] == row["symbol"]
                    and self.robots[emi]["POS"] != 0
                ):
                    position += self.robots[emi]["POS"]
                    calc = Function.calculate(
                        self,
                        symbol=row["symbol"],
                        price=row["price"],
                        qty=float(self.robots[emi]["POS"]),
                        rate=row["commission"],
                        fund=0,
                        execFee=row["execFee"],
                    )
                    message["MARKET"] = self.robots[emi]["MARKET"]
                    message["EMI"] = self.robots[emi]["EMI"]
                    message["QTY"] = self.robots[emi]["POS"]
                    message["COMMISS"] = calc["funding"]
                    values = [
                        row["execID"],
                        self.robots[emi]["EMI"],
                        "",
                        row["settlCurrency"][0],
                        row["symbol"][0],
                        row["symbol"][1],
                        self.name,
                        "Fund",
                        self.robots[emi]["POS"],
                        0,
                        row["price"],
                        0,
                        row["price"],
                        calc["sumreal"],
                        calc["funding"],
                        0,
                        row["transactTime"],
                        self.user_id,
                    ]
                    Function.insert_database(self, values=values)
                    self.robots[emi]["COMMISS"] += calc["funding"]
                    self.robots[emi]["LTIME"] = row["transactTime"]
                    results.funding += calc["funding"]
                    if info:
                        Function.fill_columns(
                            self,
                            func=Function.funding_display,
                            table=funding,
                            val=message,
                        )
                    else:
                        Function.funding_display(self, message)
            diff = row["lastQty"] - position
            if (
                diff != 0
            ):  # robots with open positions have been taken, but some quantity is still left
                calc = Function.calculate(
                    self,
                    symbol=row["symbol"],
                    price=row["price"],
                    qty=float(diff),
                    rate=row["commission"],
                    fund=0,
                    execFee=row["execFee"],
                )
                emi = ".".join(row["symbol"][:2])
                if emi not in self.robots:
                    var.logger.error(
                        "Funding could not appear until the EMI="
                        + emi
                        + " was traded. View your trading history."
                    )
                    exit(1)
                message["MARKET"] = self.robots[emi]["MARKET"]
                message["EMI"] = self.robots[emi]["EMI"]
                message["QTY"] = diff
                message["COMMISS"] = calc["funding"]
                values = [
                    row["execID"],
                    self.robots[emi]["EMI"],
                    "",
                    row["settlCurrency"][0],
                    row["symbol"][0],
                    row["symbol"][1],
                    self.name,
                    "Fund",
                    diff,
                    0,
                    row["price"],
                    0,
                    row["price"],
                    calc["sumreal"],
                    calc["funding"],
                    0,
                    row["transactTime"],
                    self.user_id,
                ]
                Function.insert_database(self, values=values)
                self.robots[emi]["COMMISS"] += calc["funding"]
                self.robots[emi]["LTIME"] = row["transactTime"]
                results.funding += calc["funding"]
                if info:
                    Function.fill_columns(
                        self, func=Function.funding_display, table=funding, val=message
                    )
                else:
                    Function.funding_display(self, message)

        # New order

        elif row["execType"] == "New":
            if (
                "clOrdID" not in row
            ):  # The order was placed from the exchange web interface
                var.last_order += 1
                clOrdID = str(var.last_order) + "." + ".".join(row["symbol"][:2])
                var.orders[clOrdID] = {
                    "leavesQty": row["leavesQty"],
                    "price": row["price"],
                    "SYMBOL": row["symbol"],
                    "CATEGORY": row["symbol"][1],
                    "MARKET": self.name,
                    "transactTime": row["transactTime"],
                    "SIDE": row["side"],
                    "EMI": row["symbol"],
                    "orderID": row["orderID"],
                }
                var.orders.move_to_end(clOrdID, last=False)
                info = "Outside placement: "
            else:
                info = ""
            Function.orders_processing(self, row=row, info=info)
        elif row["execType"] == "Canceled":
            Function.orders_processing(self, row=row)
        elif row["execType"] == "Replaced":
            Function.orders_processing(self, row=row)

    def order_number(self: Markets, clOrdID: str) -> int:
        for number, id in enumerate(var.orders):
            if id == clOrdID:
                return number

    def orders_processing(self: Markets, row: dict, info: str = "") -> None:
        """
        Orders processing <-- transaction()<--( trading_history() or get_exec() )
        """
        if "clOrdID" in row:
            if row["clOrdID"]:
                clOrdID = row["clOrdID"]
            else:
                clOrdID = "Retrieved from Trading history"
        else:  # Retrieved from /execution or /execution/tradeHistory. The order was made
            # through the exchange web interface.
            for clOrdID in var.orders:
                if "orderID" in row:
                    if var.orders[clOrdID]["orderID"] == row["orderID"]:
                        break
            else:
                clOrdID = "Empty clOrdID. The order was not sent via Tmatic."
                print(clOrdID)
        if "orderID" not in row:  # for Bitmex: orderID is missing when text='Closed to
            # conform to lot size', last time 2021-05-31
            row["orderID"] = row["text"]
        price = row["price"]
        if row["execType"] == "Canceled":
            info_p = price
            info_q = row["orderQty"] - row["cumQty"]
            if clOrdID in var.orders:
                TreeTable.orders.delete(row=Function.order_number(self, clOrdID))
                del var.orders[clOrdID]
        elif row["leavesQty"] == 0:
            info_p = row["lastPx"]
            info_q = row["lastQty"]
            if clOrdID in var.orders:
                TreeTable.orders.delete(row=Function.order_number(self, clOrdID))
                del var.orders[clOrdID]
        else:
            if row["execType"] == "New":
                if "clOrdID" in row:
                    dot = row["clOrdID"].find(".")
                    if dot == -1:
                        emi = row["symbol"]
                    else:
                        emi = row["clOrdID"][dot + 1 :]
                    if isinstance(emi, tuple):
                        _emi = emi[0]
                    else:
                        _emi = emi
                    var.orders[clOrdID] = {
                        "leavesQty": row["leavesQty"],
                        "price": row["price"],
                        "SYMBOL": row["symbol"],
                        "CATEGORY": row["symbol"][1],
                        "MARKET": self.name,
                        "transactTime": row["transactTime"],
                        "SIDE": row["side"],
                        "EMI": _emi,
                        "orderID": row["orderID"],
                    }
                    var.orders.move_to_end(clOrdID, last=False)
                info_p = price
                info_q = row["orderQty"]
            elif row["execType"] == "Trade":
                info_p = row["lastPx"]
                info_q = row["lastQty"]
                if clOrdID in var.orders:
                    TreeTable.orders.delete(row=Function.order_number(self, clOrdID))
                    var.orders.move_to_end(clOrdID, last=False)
            elif row["execType"] == "Replaced":
                var.orders[clOrdID]["orderID"] = row["orderID"]
                info_p = price
                info_q = row["leavesQty"]
                TreeTable.orders.delete(row=Function.order_number(self, clOrdID))
                var.orders.move_to_end(clOrdID, last=False)
            if (
                clOrdID in var.orders
            ):  # var.orders might be empty if we are here from trading_history()
                var.orders[clOrdID]["leavesQty"] = row["leavesQty"]
                var.orders[clOrdID]["price"] = price
                var.orders[clOrdID]["transactTime"] = row["transactTime"]
        info_q = Function.volume(self, qty=info_q, symbol=row["symbol"])
        info_p = Function.format_price(self, number=info_p, symbol=row["symbol"])
        try:
            t = clOrdID.split(".")
            int(t[0])
            emi = ".".join(t[1:3])
        except ValueError:
            emi = clOrdID
        if not info:
            info_display(
                self.name,
                info
                + row["execType"]
                + " "
                + row["side"]
                + ": "
                + emi
                + " p="
                + str(info_p)
                + " q="
                + info_q,
            )
        var.logger.info(
            self.name
            + " "
            + info
            + row["execType"]
            + " %s: orderID=%s clOrdID=%s price=%s qty=%s",
            row["side"],
            row["orderID"],
            clOrdID,
            str(info_p),
            info_q,
        )
        if clOrdID in var.orders:
            Function.orders_display(self, val=var.orders[clOrdID])

    def trades_display(self: Markets, val: dict, init=False) -> Union[None, list]:
        """
        Update trades widget
        """
        tm = str(val["TTIME"])[2:]
        tm = tm.replace("-", "")
        tm = tm.replace("T", " ")[:15]
        row = [
            tm,
            val["SYMBOL"][0],
            val["SYMBOL"][1],
            val["MARKET"],
            val["SIDE"],
            Function.format_price(
                self,
                number=float(val["TRADE_PRICE"]),
                symbol=val["SYMBOL"],
            ),
            Function.volume(self, qty=val["QTY"], symbol=val["SYMBOL"]),
            val["EMI"],
        ]
        if init:
            return row
        TreeTable.trades.insert(values=row, configure=val["SIDE"])

    def funding_display(self: Markets, val: dict, init=False) -> Union[None, list]:
        """
        Update funding widget
        """
        tm = str(val["TTIME"])[2:]
        tm = tm.replace("-", "")
        tm = tm.replace("T", " ")[:15]
        row = [
            tm,
            val["SYMBOL"][0],
            val["SYMBOL"][1],
            val["MARKET"],
            Function.format_price(
                self,
                number=float(val["PRICE"]),
                symbol=val["SYMBOL"],
            ),
            "{:.7f}".format(-val["COMMISS"]),
            Function.volume(self, qty=val["QTY"], symbol=val["SYMBOL"]),
            val["EMI"],
        ]
        if init:
            return row
        configure = "Buy" if val["COMMISS"] <= 0 else "Sell"
        TreeTable.funding.insert(values=row, configure=configure)

    def orders_display(self: Markets, val: dict) -> None:
        """
        Update Orders widget
        """
        emi = val["EMI"]
        tm = str(val["transactTime"])[2:]
        tm = tm.replace("-", "")
        tm = tm.replace("T", " ")[:15]
        row = [
            tm,
            val["SYMBOL"][0],
            val["CATEGORY"],
            val["MARKET"],
            val["SIDE"],
            Function.format_price(
                self,
                number=val["price"],
                symbol=val["SYMBOL"],
            ),
            Function.volume(self, qty=val["leavesQty"], symbol=val["SYMBOL"]),
            emi,
        ]
        TreeTable.orders.insert(values=row, configure=val["SIDE"])

    def volume(self: Markets, qty: Union[int, float], symbol: tuple) -> str:
        if qty == "None":
            return qty
        if qty == 0:
            qty = "0"
        else:
            instrument = self.Instrument[symbol]
            qty /= instrument.myMultiplier
            qty = "{:.{precision}f}".format(qty, precision=instrument.precision)

        return qty

    def format_price(self: Markets, number: Union[float, str], symbol: tuple) -> str:
        if not isinstance(number, str):
            precision = self.Instrument[symbol].price_precision
            number = "{:.{precision}f}".format(number, precision=precision)
            dot = number.find(".")
            if dot == -1:
                number = number + "."
            n = len(number) - 1 - number.find(".")
            for _ in range(precision - n):
                number = number + "0"

        return number

    def robots_entry(self: Markets, bot_list: list, utc: datetime) -> None:
        """
        Processing timeframes and entry point into robot algorithms
        """
        for symbol, timeframes in self.frames.items():
            instrument = self.Instrument[symbol]
            for timefr, values in timeframes.items():
                if utc > values["time"] + timedelta(minutes=timefr):
                    for emi in values["robots"]:
                        if (
                            self.robots[emi]["STATUS"] == "WORK"
                            and disp.f9 == "ON"
                            and bot.robo
                        ):
                            bot_list.append(
                                {
                                    "emi": emi,
                                    "robot": self.robots[emi],
                                    "frame": values["data"],
                                    "instrument": instrument,
                                }
                            )
                        Function.save_timeframes_data(
                            self,
                            frame=values["data"][-1],
                        )
                    next_minute = int(utc.minute / timefr) * timefr
                    dt_now = utc.replace(minute=next_minute, second=0, microsecond=0)
                    values["data"].append(
                        {
                            "date": (utc.year - 2000) * 10000
                            + utc.month * 100
                            + utc.day,
                            "time": utc.hour * 10000 + utc.minute * 100,
                            "bid": instrument.bids[0][0],
                            "ask": instrument.asks[0][0],
                            "hi": instrument.asks[0][0],
                            "lo": instrument.bids[0][0],
                            "funding": instrument.fundingRate,
                            "datetime": dt_now,
                        }
                    )
                    values["time"] = dt_now

        return bot_list

    def refresh_on_screen(self: Markets, utc: datetime) -> None:
        """
        Refresh information on screen
        """
        adaptive_screen(self)
        if utc.hour != var.refresh_hour:
            Function.select_database(self, "select count(*) cou from robots")
            var.refresh_hour = utc.hour
            var.logger.info("Emboldening SQLite")

        disp.label_time["text"] = time.asctime(time.gmtime())
        disp.label_f9["text"] = disp.f9
        if disp.f9 == "ON":
            disp.label_f9.config(bg=disp.green_color)
        else:
            disp.label_f9.config(bg=disp.red_color)
        if self.logNumFatal == 0:
            if utc > self.message_time + timedelta(seconds=10):
                if self.message_counter == self.message_point:
                    info_display(self.name, "No data within 10 sec")
                    # disp.label_online["text"] = "NO DATA"
                    # disp.label_online.config(bg="yellow2")
                    WS.urgent_announcement(self)
                self.message_time = utc
                self.message_point = self.message_counter
        tm = datetime.now()
        Function.refresh_tables(self)
        ###print(datetime.now() - tm)

    def refresh_tables(self: Markets) -> None:
        """
        Update tkinter labels in the tables
        """

        # Refresh Positions table

        tree = TreeTable.position

        for num, symbol in enumerate(self.symbol_list):
            instrument = self.Instrument[symbol]
            compare = [
                symbol[0],
                symbol[1],
                instrument.currentQty,
                instrument.avgEntryPrice,
                instrument.unrealisedPnl,
                instrument.marginCallPrice,
                instrument.state,
                instrument.volume24h,
                instrument.expire,
                instrument.fundingRate,
            ]
            if compare != tree.cache[num]:
                tree.cache[num] = compare
                row = [
                    symbol[0],
                    symbol[1],
                    Function.volume(self, qty=instrument.currentQty, symbol=symbol),
                    Function.format_price(
                        self, number=instrument.avgEntryPrice, symbol=symbol
                    ),
                    format_number(number=instrument.unrealisedPnl),
                    instrument.marginCallPrice,
                    instrument.state,
                    Function.humanFormat(self, instrument.volume24h, symbol),
                    instrument.expire,
                    instrument.fundingRate,
                ]
                tree.update(row=num, values=row)

        # Refresh Orderbook table

        tree = TreeTable.orderbook

        def display_order_book_values(
            val: list,
            start: int,
            end: int,
            direct: int,
            side: str,
            col: int,
            color: str,
        ) -> None:
            count = 0
            # col_qty = abs(col - 2)
            for number in range(start, end, direct):
                if len(val) > count:
                    compare = [
                        val[count][0],
                        val[count][1],
                    ]
                    if side == "bids":
                        compare = [val[count][0], val[count][1], ""]
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
                    else:
                        compare = ["", val[count][0], val[count][1]]
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
                else:
                    row = ["", "", ""]
                    tree.cache[number] = row
                    tree.update(row=number, values=row)
                count += 1

        num = int(disp.num_book / 2)
        instrument = self.Instrument[var.symbol]
        if var.order_book_depth == "quote":
            if instrument.asks[0][1]:
                update_label(
                    table="orderbook",
                    column=2,
                    row=num,
                    val=Function.volume(
                        self, qty=instrument.asks[0][1], symbol=var.symbol
                    ),
                )
            else:
                update_label(table="orderbook", column=2, row=num, val="")
            disp.labels["orderbook"][num - mod][2]["fg"] = "black"
            if instrument.bids[0][1]:
                update_label(
                    table="orderbook",
                    column=0,
                    row=num + 1,
                    val=Function.volume(
                        self, qty=instrument.bids[0][1], symbol=var.symbol
                    ),
                )
            else:
                update_label(table="orderbook", column=0, row=num + 1, val="")
            disp.labels["orderbook"][num + 1 - mod][0]["fg"] = "black"
            first_price_sell = instrument.asks[0][0] + (num + mod) * instrument.tickSize
            first_price_buy = instrument.bids[0][0]
            for row in range(1 - mod, disp.num_book - mod):
                if row <= num:
                    price = round(
                        first_price_sell - (row + mod) * instrument.tickSize,
                        instrument.precision,
                    )
                    qty = 0
                    if var.orders:
                        qty = Function.volume(
                            self,
                            qty=find_order(float(price), qty, symbol=var.symbol),
                            symbol=var.symbol,
                        )
                    if instrument.asks[0][0]:
                        price = Function.format_price(
                            self, number=price, symbol=var.symbol
                        )
                    else:
                        price = ""
                    update_label(table="orderbook", column=1, row=row, val=price)
                    if str(qty) != "0":
                        update_label(table="orderbook", column=0, row=row, val=qty)
                        disp.labels["orderbook"][row][0]["bg"] = disp.red_color
                        disp.labels["orderbook"][row][0]["fg"] = "white"
                    else:
                        update_label(table="orderbook", column=0, row=row, val="")
                        disp.labels["orderbook"][row][0]["bg"] = disp.bg_color
                        disp.labels["orderbook"][row][0]["fg"] = "white"
                else:
                    price = round(
                        first_price_buy - (row - num - 1) * instrument.tickSize,
                        instrument.precision,
                    )
                    qty = 0
                    if var.orders:
                        qty = Function.volume(
                            self,
                            qty=find_order(price, qty, symbol=var.symbol),
                            symbol=var.symbol,
                        )
                    if price > 0:
                        price = Function.format_price(
                            self, number=price, symbol=var.symbol
                        )
                    else:
                        price = ""
                    update_label(table="orderbook", column=1, row=row, val=price)
                    if str(qty) != "0":
                        update_label(table="orderbook", column=2, row=row, val=qty)
                        disp.labels["orderbook"][row][2]["bg"] = disp.green_color
                        disp.labels["orderbook"][row][2]["fg"] = "white"
                    else:
                        update_label(table="orderbook", column=2, row=row, val="")
                        disp.labels["orderbook"][row][2]["bg"] = disp.bg_color
                        disp.labels["orderbook"][row][2]["fg"] = disp.fg_color
        else:
            display_order_book_values(
                val=instrument.bids,
                start=num,
                end=disp.num_book,
                direct=1,
                side="bids",
                col=0,
                color=disp.red_color,
            )
            display_order_book_values(
                val=instrument.asks,
                start=num - 1,
                end=-1,
                direct=-1,
                side="asks",
                col=2,
                color=disp.green_color,
            )

        # Refresh Robots table

        tree = TreeTable.robots

        for num, robot in enumerate(self.robots.values()):
            symbol = robot["SYMBOL"]
            if robot["CATEGORY"] != "spot":
                price = Function.close_price(self, symbol=symbol, pos=robot["POS"])
                if price:
                    calc = Function.calculate(
                        self,
                        symbol=symbol,
                        price=price,
                        qty=-float(robot["POS"]),
                        rate=0,
                        fund=1,
                    )
                    robot["PNL"] = robot["SUMREAL"] + calc["sumreal"] - robot["COMMISS"]
                else:
                    robot["PNL"] = robot["SUMREAL"] - robot["COMMISS"]
            compare = [
                robot["EMI"],
                symbol[0],
                symbol[1],
                self.Instrument[symbol].settlCurrency[0],
                robot["TIMEFR"],
                robot["CAPITAL"],
                robot["STATUS"],
                robot["VOL"],
                robot["PNL"],
                robot["POS"],
            ]
            if compare != tree.cache[num]:
                tree.cache[num] = compare
                row = [
                    robot["EMI"],
                    symbol[0],
                    symbol[1],
                    self.Instrument[symbol].settlCurrency[0],
                    robot["TIMEFR"],
                    robot["CAPITAL"],
                    robot["STATUS"],
                    Function.humanFormat(self, robot["VOL"], symbol),
                    format_number(number=robot["PNL"]),
                    Function.volume(
                        self,
                        qty=robot["POS"],
                        symbol=symbol,
                    ),
                ]
                tree.update(row=num, values=row)
            robot["y_position"] = num

        # Refresh Account table

        tree = TreeTable.account

        for num, settlCurrency in enumerate(self.Account.keys()):
            account = self.Account[settlCurrency]
            compare = [
                settlCurrency[0],
                account.walletBalance,
                account.unrealisedPnl,
                account.marginBalance,
                account.orderMargin,
                account.positionMagrin,
                account.availableMargin,
            ]
            if compare != tree.cache[num]:
                tree.cache[num] = compare
                row = [
                    settlCurrency[0],
                    format_number(number=account.walletBalance),
                    format_number(number=account.unrealisedPnl),
                    format_number(number=account.marginBalance),
                    format_number(number=account.orderMargin),
                    format_number(number=account.positionMagrin),
                    format_number(number=account.availableMargin),
                ]
                tree.update(row=num, values=row)

        # Refresh Results table

        tree = TreeTable.results

        results = dict()
        for symbol, position in self.positions.items():
            if symbol[2] == var.current_market:
                if position["POS"] != 0:
                    price = Function.close_price(
                        self, symbol=symbol, pos=position["POS"]
                    )
                    if price:
                        calc = Function.calculate(
                            self,
                            symbol=symbol,
                            price=price,
                            qty=-position["POS"],
                            rate=0,
                            fund=1,
                        )
                        currency = self.Instrument[symbol].settlCurrency
                        if currency in results:
                            results[currency] += calc["sumreal"]
                        else:
                            results[currency] = calc["sumreal"]
        for num, currency in enumerate(self.Result.keys()):  # self.currencies
            result = self.Result[currency]
            result.result = 0
            if currency in results:
                result.result += results[currency]
            compare = [
                currency[0],
                result.sumreal + result.result,
                -result.commission,
                -result.funding,
            ]
            if compare != tree.cache[num]:
                tree.cache[num] = compare
                row = [
                    currency[0],
                    format_number(number=result.sumreal + result.result),
                    format_number(number=-result.commission),
                    format_number(number=-result.funding),
                ]
                tree.update(row=num, values=row)

        # Refresh Market table

        tree = TreeTable.market

        for num, name in enumerate(var.market_list):
            ws = Markets[name]
            status = "ONLINE"
            if ws.logNumFatal != 0:
                if ws.logNumFatal == -1:
                    status = "RELOADING"
            compare = [ws.account_disp + str(ws.connect_count) + " " + status]
            if compare != tree.cache[num]:
                tree.cache[num] = compare
                tree.update(row=num, values=compare)

    def close_price(self: Markets, symbol: tuple, pos: int) -> float:
        instrument = self.Instrument[symbol]
        if pos > 0 and instrument.bids[0]:
            close = instrument.bids[0][0]
        elif pos <= 0 and instrument.asks[0]:
            close = instrument.asks[0][0]
        else:
            close = None

        return close

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
        var.last_order += 1
        clOrdID = str(var.last_order) + "." + emi
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
        clOrdID: str,
        price: float,
        qty: int,
    ) -> str:
        """
        Replace orders
        """
        price_str = Function.format_price(
            self, number=price, symbol=var.orders[clOrdID]["SYMBOL"]
        )
        var.logger.info(
            "Putting orderID="
            + var.orders[clOrdID]["orderID"]
            + " clOrdID="
            + clOrdID
            + " price="
            + price_str
            + " qty="
            + str(qty)
        )
        if price != var.orders[clOrdID]["price"]:  # the price alters
            WS.replace_limit(
                self,
                quantity=qty,
                price=price_str,
                orderID=var.orders[clOrdID]["orderID"],
                symbol=var.orders[clOrdID]["SYMBOL"],
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
        row = var.market_list.index(self.name)
        TreeTable.market.update(row=row, values=self.account_disp + status)
        info_display(self.name, message)
        if error:
            TreeTable.market.paint(row=row, configure="Error")
        disp.root.update()

    def humanFormat(self: Markets, volNow: int, symbol: tuple) -> str:
        if volNow > 1000000000:
            volNow = "{:.2f}".format(round(volNow / 1000000000, 2)) + "B"
        elif volNow > 1000000:
            volNow = "{:.2f}".format(round(volNow / 1000000, 2)) + "M"
        elif volNow > 1000:
            volNow = "{:.2f}".format(round(volNow / 1000, 2)) + "K"
        else:
            volNow = Function.volume(self, qty=volNow, symbol=symbol)

        return volNow


def handler_order(event) -> None:
    row_position = event.widget.curselection()
    if row_position:
        if row_position[0] - orders.mod >= 0:
            for num, clOrdID in enumerate(var.orders):
                if num == row_position[0] - orders.mod:
                    break
            ws = Markets[var.orders[clOrdID]["SYMBOL"][2]]

            def on_closing() -> None:
                disp.order_window_trigger = "off"
                order_window.destroy()

            def delete(order: dict, clOrdID: str) -> None:
                try:
                    var.orders[clOrdID]
                except KeyError:
                    message = "Order " + clOrdID + " does not exist!"
                    info_display(ws.name, message)
                    var.logger.info(message)
                    return
                if ws.logNumFatal == 0:
                    Function.del_order(ws, order=order, clOrdID=clOrdID)
                    # orders.delete(row_position)
                else:
                    info_display(ws.name, "The operation failed. Websocket closed!")
                on_closing()

            def replace(clOrdID) -> None:
                try:
                    var.orders[clOrdID]
                except KeyError:
                    message = "Order " + clOrdID + " does not exist!"
                    info_display(ws.name, message)
                    var.logger.info(message)
                    return
                try:
                    float(price_replace.get())
                except ValueError:
                    info_display(ws.name, "Price must be numeric!")
                    return
                if ws.logNumFatal == 0:
                    roundSide = var.orders[clOrdID]["leavesQty"]
                    if var.orders[clOrdID]["SIDE"] == "Sell":
                        roundSide = -roundSide
                    price = Function.round_price(
                        ws,
                        symbol=var.orders[clOrdID]["SYMBOL"],
                        price=float(price_replace.get()),
                        rside=roundSide,
                    )
                    if price == var.orders[clOrdID]["price"]:
                        info_display(
                            ws.name, "Price is the same but must be different!"
                        )
                        return
                    clOrdID = Function.put_order(
                        ws,
                        clOrdID=clOrdID,
                        price=price,
                        qty=var.orders[clOrdID]["leavesQty"],
                    )
                else:
                    info_display(ws.name, "The operation failed. Websocket closed!")
                on_closing()

            if disp.order_window_trigger == "off":
                order = var.orders[clOrdID]
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
                    number=var.orders[clOrdID]["price"],
                    symbol=var.orders[clOrdID]["SYMBOL"],
                )
                label1["text"] = (
                    "market\t"
                    + var.orders[clOrdID]["SYMBOL"][2]
                    + "\nsymbol\t"
                    + ".".join(var.orders[clOrdID]["SYMBOL"][:2])
                    + "\nside\t"
                    + var.orders[clOrdID]["SIDE"]
                    + "\nclOrdID\t"
                    + clOrdID
                    + "\nprice\t"
                    + order_price
                    + "\nquantity\t"
                    + Function.volume(
                        ws,
                        qty=var.orders[clOrdID]["leavesQty"],
                        symbol=var.orders[clOrdID]["SYMBOL"],
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


def handler_orderbook(event) -> None:
    tree = event.widget
    items = tree.selection()
    if items:
        tree.update()
        time.sleep(0.05)
        tree.selection_remove(items[0])
    disp.handler_orderbook_symbol = var.symbol
    ws = Markets[var.current_market]

    def refresh() -> None:
        nonlocal ws
        book_window.title(var.symbol)
        if disp.handler_orderbook_symbol != var.symbol:
            ws = Markets[var.current_market]
            entry_price_ask.delete(0, "end")
            entry_price_ask.insert(
                0,
                Function.format_price(
                    ws,
                    number=ws.Instrument[var.symbol].asks[0][0],
                    symbol=var.symbol,
                ),
            )
            entry_price_bid.delete(0, "end")
            entry_price_bid.insert(
                0,
                Function.format_price(
                    ws,
                    number=ws.Instrument[var.symbol].bids[0][0],
                    symbol=var.symbol,
                ),
            )
            entry_quantity.delete(0, "end")
            entry_quantity.insert(
                0,
                Function.volume(
                    ws, qty=ws.Instrument[var.symbol].minOrderQty, symbol=var.symbol
                ),
            )
            option_robots["menu"].delete(0, "end")
            options = list()
            for emi in ws.robots:
                if (
                    ws.robots[emi]["SYMBOL"] in ws.symbol_list
                    and ws.robots[emi]["SYMBOL"] == var.symbol
                ):
                    options.append(ws.robots[emi]["EMI"])
            for option in options:
                option_robots["menu"].add_command(
                    label=option, command=lambda v=emi_number, optn=option: v.set(optn)
                )
            emi_number.set("")
            disp.handler_orderbook_symbol = var.symbol
        book_window.after(100, refresh)

    def on_closing() -> None:
        disp.book_window_trigger = "off"
        book_window.after_cancel(refresh_var)
        book_window.destroy()

    def minimum_qty(qnt):
        minOrderQty = ws.Instrument[var.symbol].minOrderQty
        if qnt < minOrderQty:
            message = (
                "The "
                + str(var.symbol)
                + " quantity must be greater than or equal to "
                + Function.volume(ws, qty=minOrderQty, symbol=var.symbol)
            )
            warning_window(message)
            return "error"
        qnt_d = Decimal(str(qnt))
        qtyStep = Decimal(str(ws.Instrument[var.symbol].qtyStep))
        if qnt_d % qtyStep != 0:
            message = (
                "The "
                + str(var.symbol)
                + " quantity must be multiple to "
                + Function.volume(ws, qty=qtyStep, symbol=var.symbol)
            )
            warning_window(message)
            return "error"

    def callback_sell_limit() -> None:
        if quantity.get() and price_ask.get() and emi_number.get():
            try:
                qnt = abs(
                    float(quantity.get()) * ws.Instrument[var.symbol].myMultiplier
                )
                price = float(price_ask.get())
                res = "yes"
            except Exception:
                warning_window("Fields must be numbers!")
                res = "no"
            if res == "yes" and qnt != 0:
                price = Function.round_price(
                    ws, symbol=var.symbol, price=price, rside=-qnt
                )
                if price <= 0:
                    warning_window("The price must be above zero.")
                    return
                if minimum_qty(qnt):
                    return
                Function.post_order(
                    ws,
                    name=ws.name,
                    symbol=var.symbol,
                    emi=emi_number.get(),
                    side="Sell",
                    price=price,
                    qty=qnt,
                )
        else:
            warning_window("Some of the fields are empty!")

    def callback_buy_limit() -> None:
        if quantity.get() and price_bid.get() and emi_number.get():
            try:
                qnt = abs(
                    float(quantity.get()) * ws.Instrument[var.symbol].myMultiplier
                )
                price = float(price_bid.get())
                res = "yes"
            except Exception:
                warning_window("Fields must be numbers!")
                res = "no"
            if res == "yes" and qnt != 0:
                price = Function.round_price(
                    ws, symbol=var.symbol, price=price, rside=qnt
                )
                if price <= 0:
                    warning_window("The price must be above zero.")
                    return
                if minimum_qty(qnt):
                    return
                Function.post_order(
                    ws,
                    name=ws.name,
                    symbol=var.symbol,
                    emi=emi_number.get(),
                    side="Buy",
                    price=price,
                    qty=qnt,
                )
        else:
            warning_window("Some of the fields are empty!")

    if disp.book_window_trigger == "off" and disp.f9 == "OFF":
        disp.book_window_trigger = "on"
        book_window = tk.Toplevel(disp.root, padx=10, pady=20)
        cx = disp.root.winfo_pointerx()
        cy = disp.root.winfo_pointery()
        book_window.geometry("+{}+{}".format(cx + 200, cy))
        book_window.title(var.symbol)
        book_window.protocol("WM_DELETE_WINDOW", on_closing)
        book_window.attributes("-topmost", 1)
        frame_quantity = tk.Frame(book_window)
        frame_market_ask = tk.Frame(book_window)
        frame_market_bid = tk.Frame(book_window)
        frame_robots = tk.Frame(book_window)
        sell_limit = tk.Button(
            book_window, text="Sell Limit", command=callback_sell_limit
        )
        buy_limit = tk.Button(book_window, text="Buy Limit", command=callback_buy_limit)
        quantity = tk.StringVar()
        price_ask = tk.StringVar()
        price_bid = tk.StringVar()
        entry_price_ask = tk.Entry(
            frame_market_ask, width=10, bg=disp.bg_color, textvariable=price_ask
        )
        entry_price_bid = tk.Entry(
            frame_market_bid, width=10, bg=disp.bg_color, textvariable=price_bid
        )
        instrument = ws.Instrument[var.symbol]
        entry_price_ask.insert(
            0,
            Function.format_price(
                ws,
                number=instrument.asks[0][0],
                symbol=var.symbol,
            ),
        )
        entry_price_bid.insert(
            0,
            Function.format_price(
                ws,
                number=instrument.bids[0][0],
                symbol=var.symbol,
            ),
        )
        entry_quantity = tk.Entry(
            frame_quantity, width=9, bg=disp.bg_color, textvariable=quantity
        )
        entry_quantity.insert(
            0,
            Function.volume(ws, qty=instrument.minOrderQty, symbol=var.symbol),
        )
        label_ask = tk.Label(frame_market_ask, text="Price:")
        label_bid = tk.Label(frame_market_bid, text="Price:")
        label_quantity = tk.Label(frame_quantity, text="Quantity:")
        label_robots = tk.Label(frame_robots, text="EMI:")
        emi_number = tk.StringVar()
        options = list()
        for emi in ws.robots:
            if (
                ws.robots[emi]["SYMBOL"] in ws.symbol_list
                and ws.robots[emi]["SYMBOL"] == var.symbol
            ):
                options.append(ws.robots[emi]["EMI"])
        option_robots = tk.OptionMenu(frame_robots, emi_number, *options)
        frame_robots.grid(row=1, column=0, sticky="NSWE", columnspan=2, padx=10, pady=0)
        label_robots.pack(side="left")
        option_robots.pack()
        frame_quantity.grid(
            row=2,
            column=0,
            sticky="NSWE",
            columnspan=2,
            padx=10,
            pady=10,
        )
        label_quantity.pack(side="left")
        entry_quantity.pack()
        frame_market_ask.grid(row=3, column=0, sticky="NSWE")
        frame_market_bid.grid(row=3, column=1, sticky="NSWE")
        label_ask.pack(side="left")
        entry_price_ask.pack()
        label_bid.pack(side="left")
        entry_price_bid.pack()
        sell_limit.grid(row=4, column=0, sticky="NSWE", pady=10)
        buy_limit.grid(row=4, column=1, sticky="NSWE", pady=10)
        change_color(color=disp.title_color, container=book_window)
        refresh_var = book_window.after_idle(refresh)


def format_number(number: Union[float, str]) -> str:
    """
    Rounding a value from 2 to 8 decimal places
    """
    if not isinstance(number, str):
        after_dot = max(2, 9 - max(1, len(str(int(number)))))
        number = "{:.{num}f}".format(number, num=after_dot)
        number = number.rstrip("0")
        number = number.rstrip(".")

    return number


def warning_window(message: str, widget=None, item=None) -> None:
    def on_closing() -> None:
        warn_window.destroy()
        if widget:
            widget.selection_remove(item)

    # disp.robots_window_trigger = "on"
    warn_window = tk.Toplevel(pady=5)
    warn_window.geometry("400x150+{}+{}".format(450 + randint(0, 7) * 15, 300))
    warn_window.title("Warning")
    warn_window.protocol("WM_DELETE_WINDOW", on_closing)
    warn_window.attributes("-topmost", 1)
    tex = tk.Text(warn_window, wrap="word")
    tex.insert("insert", message)
    tex.pack(expand=1)


def handler_position(event) -> None:
    tree = event.widget
    items = tree.selection()
    if items:
        ws = Markets[var.current_market]
        item = items[0]
        children = tree.get_children()
        row_position = children.index(item)
        var.symbol = ws.symbol_list[row_position]


def handler_account(event) -> None:
    tree = event.widget
    items = tree.selection()
    if items:
        tree.update()
        time.sleep(0.05)
        tree.selection_remove(items[0])


def handler_market(event) -> None:
    tree = event.widget
    items = tree.selection()
    if items:
        item = items[0]
        children = tree.get_children()
        row_position = children.index(item)
        shift = var.market_list[row_position]
        if shift != var.current_market:
            var.current_market = shift
            var.symbol = Markets[var.current_market].symbol_list[0]
            clear_tables()


def find_order(price: float, qty: int, symbol: str) -> int:
    for clOrdID in var.orders:
        if (
            var.orders[clOrdID]["price"] == price
            and var.orders[clOrdID]["SYMBOL"] == symbol
        ):
            qty += var.orders[clOrdID]["leavesQty"]

    return qty


def handler_robots(event) -> None:
    emi = None
    ws = Markets[var.current_market]
    tree = event.widget
    items = tree.selection()
    if items:
        item = items[0]
        children = tree.get_children()
        row_position = children.index(item)
        for val in ws.robots:
            if ws.robots[val]["y_position"] == row_position:
                emi = val
                break
        if emi:
            if ws.robots[emi]["STATUS"] not in [
                "NOT IN LIST",
                "NOT DEFINED",
                "RESERVED",
            ]:

                def callback():
                    row = ws.robots[val]["y_position"]
                    if ws.robots[emi]["STATUS"] == "WORK":
                        ws.robots[emi]["STATUS"] = "OFF"
                        TreeTable.robots.paint(row=row, configure="Sell")
                    else:
                        ws.robots[emi]["STATUS"] = "WORK"
                        TreeTable.robots.paint(row=row, configure="Normal")
                    on_closing()

                def on_closing():
                    disp.robots_window_trigger = "off"
                    robot_window.destroy()
                    tree.selection_remove(item)

                if disp.robots_window_trigger == "off":
                    disp.robots_window_trigger = "on"
                    robot_window = tk.Toplevel(disp.root, padx=30, pady=8)
                    cx = disp.root.winfo_pointerx()
                    cy = disp.root.winfo_pointery()
                    robot_window.geometry("250x50+{}+{}".format(cx - 150, cy - 50))
                    robot_window.title("EMI=" + emi)
                    robot_window.protocol("WM_DELETE_WINDOW", on_closing)
                    robot_window.attributes("-topmost", 1)
                    text = emi + " - Disable"
                    if ws.robots[emi]["STATUS"] == "OFF":
                        text = emi + " - Enable"
                    status = tk.Button(robot_window, text=text, command=callback)
                    status.pack()
                    change_color(color=disp.title_color, container=robot_window)
            else:
                warning_window(
                    "You cannot change the " + ws.robots[emi]["STATUS"] + " status.",
                    widget=tree,
                    item=item,
                )


def change_color(color: str, container=None) -> None:
    if "notebook" not in str(container.__dict__):
        container.config(bg=color)
    for child in container.winfo_children():
        if child.winfo_children():
            change_color(color, child)
        elif type(child) is tk.Label:
            child.config(bg=color)
        elif type(child) is tk.Button:
            child.config(bg=color)


def load_labels() -> None:
    ws = Markets[var.current_market]
    '''num = int(disp.num_book / 2)
    mod = Tables.orderbook.mod
    for row in range(disp.num_book + mod - 1):
        for column in range(len(var.name_book)):
            if row > 0:
                if row <= num and column == 2:
                    disp.labels["orderbook"][row][column]["anchor"] = "w"
                if row > num and column == 0:
                    disp.labels["orderbook"][row][column]["anchor"] = "e"'''
    TreeTable.orderbook = TreeviewTable(
        frame=disp.frame_orderbook,
        name="orderbook",
        title=var.name_book,
        size=disp.num_book,
        bind=handler_orderbook,
    )
    TreeTable.position = TreeviewTable(
        frame=disp.frame_position,
        name="position",
        title=var.name_position,
        size=len(ws.symbol_list),
        bind=handler_position,
        hide=["9", "8", "2"],
    )
    TreeTable.robots = TreeviewTable(
        frame=disp.frame_robots,
        name="robots",
        title=var.name_robots,
        size=len(ws.robots),
        bind=handler_robots,
    )
    TreeTable.account = TreeviewTable(
        frame=disp.frame_account,
        name="account",
        title=var.name_account,
        size=len(ws.Account.get_keys()),
        bind=handler_account,
    )
    TreeTable.market = TreeviewTable(
        frame=disp.frame_market,
        name="market",
        title=var.name_market,
        size=len(var.market_list),
        style="market.Treeview",
        bind=handler_market,
    )
    TreeTable.results = TreeviewTable(
        frame=disp.frame_results,
        name="results",
        size=len(ws.Result.get_keys()),
        title=var.name_results,
        bind=handler_account,
    )
    TreeTable.position.set_selection()
    TreeTable.market.set_selection()
    robot_status(ws)


def robot_status(ws: Markets):
    for row, emi in enumerate(ws.robots):
        if ws.robots[emi]["STATUS"] in ["NOT IN LIST", "OFF", "NOT DEFINED"] or (
            ws.robots[emi]["STATUS"] == "RESERVED"
            and ws.robots[emi]["POS"] != 0
            and ws.robots[emi]["CATEGORY"] != "spot"
        ):
            TreeTable.robots.paint(row=row, configure="Sell")
        else:
            TreeTable.robots.paint(row=row, configure="Normal")


def clear_tables():
    ws = Markets[var.current_market]
    TreeTable.position.init(size=len(ws.symbol_list))
    TreeTable.account.init(size=len(ws.Account.get_keys()))
    TreeTable.robots.init(size=len(ws.robots))
    TreeTable.orderbook.init(size=disp.num_book)
    TreeTable.results.init(size=len(ws.Result.get_keys()))
    TreeTable.position.set_selection()
    Function.refresh_tables(ws)
    robot_status(ws)


change_color(color=disp.title_color, container=disp.root)

TreeTable.orders = TreeviewTable(
    frame=disp.frame_orders,
    name="orders",
    size=0,
    title=var.name_order,
    bind=handler_order,
)
TreeTable.trades = TreeviewTable(
    frame=disp.frame_trades,
    name="trades",
    size=0,
    title=var.name_trade,
    bind=handler_account,
)
TreeTable.funding = TreeviewTable(
    frame=disp.frame_funding,
    name="funding",
    size=0,
    title=var.name_funding,
    bind=handler_account,
)


def adaptive_screen(ws: Markets):
    """now_height = disp.frame_rest.winfo_height()
    if now_height != disp.all_height:
        disp.frame_rest.grid_rowconfigure(
            0, minsize=int(disp.frame_rest.winfo_height() / 6)
        )
        disp.frame_rest.grid_rowconfigure(
            1, minsize=int(disp.frame_rest.winfo_height() / 2)
        )
        disp.all_height = now_height"""

    now_width = disp.root.winfo_width()
    if now_width != disp.all_width or var.current_market != disp.last_market:
        ratio = now_width / disp.window_width if now_width > 1 else 1.0
        if now_width > disp.window_width:
            t = disp.platform_name.ljust((now_width - disp.window_width) // 4)
            disp.root.title(t)
        else:
            disp.root.title(disp.platform_name)
        disp.all_width = now_width

        # Hide / show adaptive columns in order to save space in the tables
        if ratio < disp.adaptive_ratio:
            if (
                TreeTable.position.hide_num < 0
                or var.current_market != disp.last_market
            ):
                TreeTable.position.tree.config(displaycolumns=TreeTable.position.column_hide[0])
                TreeTable.position.hide_num = 0
            '''if (
                orders.listboxes[7].winfo_ismapped() == 1
                or var.current_market != disp.last_market
            ):
                orders.listboxes[7].grid_forget()
                orders.sub.grid_columnconfigure(7, weight=0)
            if (
                trades.listboxes[7].winfo_ismapped() == 1
                or var.current_market != disp.last_market
            ):
                trades.listboxes[7].grid_forget()
                trades.sub.grid_columnconfigure(7, weight=0)
            if (
                funding.listboxes[7].winfo_ismapped() == 1
                or var.current_market != disp.last_market
            ):
                funding.listboxes[7].grid_forget()
                funding.sub.grid_columnconfigure(7, weight=0)'''
        if ratio < disp.adaptive_ratio - 0.1:
            if (
                TreeTable.position.hide_num < 1
                or var.current_market != disp.last_market
            ):
                TreeTable.position.tree.config(displaycolumns=TreeTable.position.column_hide[1])
                TreeTable.position.hide_num = 1
            '''if (
                orders.listboxes[2].winfo_ismapped() == 1
                or var.current_market != disp.last_market
            ):
                orders.listboxes[2].grid_forget()
                orders.sub.grid_columnconfigure(2, weight=0)
            if (
                trades.listboxes[2].winfo_ismapped() == 1
                or var.current_market != disp.last_market
            ):
                trades.listboxes[2].grid_forget()
                trades.sub.grid_columnconfigure(2, weight=0)
            if (
                funding.listboxes[2].winfo_ismapped() == 1
                or var.current_market != disp.last_market
            ):
                funding.listboxes[2].grid_forget()
                funding.sub.grid_columnconfigure(2, weight=0)
            if (
                disp.labels["robots"][len(ws.robots)][5].winfo_ismapped() == 1
                or var.current_market != disp.last_market
            ):
                for i in range(len(ws.robots) + 1):
                    disp.labels["robots"][i][5].grid_forget()
                Tables.robots.sub.grid_columnconfigure(5, weight=0)'''
        if ratio < disp.adaptive_ratio - 0.2:
            if (
                TreeTable.position.hide_num < 2
                or var.current_market != disp.last_market
            ):
                TreeTable.position.tree.config(displaycolumns=TreeTable.position.column_hide[2])
                TreeTable.position.hide_num = 2
            '''if (
                orders.listboxes[4].winfo_ismapped() == 1
                or var.current_market != disp.last_market
            ):
                orders.listboxes[4].grid_forget()
                orders.sub.grid_columnconfigure(4, weight=0)
            if (
                trades.listboxes[4].winfo_ismapped() == 1
                or var.current_market != disp.last_market
            ):
                trades.listboxes[4].grid_forget()
                trades.sub.grid_columnconfigure(4, weight=0)
            if (
                funding.listboxes[4].winfo_ismapped() == 1
                or var.current_market != disp.last_market
            ):
                funding.listboxes[4].grid_forget()
                funding.sub.grid_columnconfigure(4, weight=0)
            if (
                disp.labels["robots"][len(ws.robots)][2].winfo_ismapped() == 1
                or var.current_market != disp.last_market
            ):
                for i in range(len(ws.robots) + 1):
                    disp.labels["robots"][i][2].grid_forget()
                Tables.robots.sub.grid_columnconfigure(2, weight=0)'''
        if ratio >= disp.adaptive_ratio:
            if TreeTable.position.hide_num >= 0:
                TreeTable.position.tree.config(displaycolumns=TreeTable.position.tree["columns"])
                TreeTable.position.hide_num = -1
            '''if orders.listboxes[7].winfo_ismapped() == 0:
                orders.listboxes[7].grid(row=0, padx=0, column=7, sticky="NSWE")
                orders.sub.grid_columnconfigure(7, weight=1)
            if trades.listboxes[7].winfo_ismapped() == 0:
                trades.listboxes[7].grid(row=0, padx=0, column=7, sticky="NSWE")
                trades.sub.grid_columnconfigure(7, weight=1)
            if funding.listboxes[7].winfo_ismapped() == 0:
                funding.listboxes[7].grid(row=0, padx=0, column=7, sticky="NSWE")
                funding.sub.grid_columnconfigure(7, weight=1)'''
        elif ratio >= disp.adaptive_ratio - 0.1:
            if TreeTable.position.hide_num >= 1:
                TreeTable.position.tree.config(displaycolumns=TreeTable.position.column_hide[0])
                TreeTable.position.hide_num = 0
            '''if orders.listboxes[2].winfo_ismapped() == 0:
                orders.listboxes[2].grid(row=0, padx=0, column=2, sticky="NSWE")
                orders.sub.grid_columnconfigure(2, weight=1)
            if trades.listboxes[2].winfo_ismapped() == 0:
                trades.listboxes[2].grid(row=0, padx=0, column=2, sticky="NSWE")
                trades.sub.grid_columnconfigure(2, weight=1)
            if funding.listboxes[2].winfo_ismapped() == 0:
                funding.listboxes[2].grid(row=0, padx=0, column=2, sticky="NSWE")
                funding.sub.grid_columnconfigure(2, weight=1)
            if disp.labels["robots"][0][5].winfo_ismapped() == 0:
                for i in range(len(ws.robots) + 1):
                    disp.labels["robots"][i][5].grid(
                        row=i, column=5, sticky="NSWE", padx=0, pady=0
                    )
                Tables.robots.sub.grid_columnconfigure(5, weight=1)'''
        elif ratio >= disp.adaptive_ratio - 0.2:
            if TreeTable.position.hide_num >= 2:
                TreeTable.position.tree.config(displaycolumns=TreeTable.position.column_hide[1])
                TreeTable.position.hide_num = 1
            '''if orders.listboxes[4].winfo_ismapped() == 0:
                orders.listboxes[4].grid(row=0, padx=0, column=4, sticky="NSWE")
                orders.sub.grid_columnconfigure(4, weight=1)
            if trades.listboxes[4].winfo_ismapped() == 0:
                trades.listboxes[4].grid(row=0, padx=0, column=4, sticky="NSWE")
                trades.sub.grid_columnconfigure(4, weight=1)
            if funding.listboxes[4].winfo_ismapped() == 0:
                funding.listboxes[4].grid(row=0, padx=0, column=4, sticky="NSWE")
                funding.sub.grid_columnconfigure(4, weight=1)
            if disp.labels["robots"][0][2].winfo_ismapped() == 0:
                for i in range(len(ws.robots) + 1):
                    disp.labels["robots"][i][2].grid(
                        row=i, column=2, sticky="NSWE", padx=0, pady=0
                    )
                Tables.robots.sub.grid_columnconfigure(2, weight=1)'''
        disp.last_market = var.current_market

        '''# Hide / show right adaptive frame
        if now_width > disp.window_width:
            state_width = disp.window_width
            side_width = now_width - state_width
            disp.frame_right.configure(width=side_width)
            if disp.state_width is None:
                disp.frame_right.grid(row=0, column=1, sticky="NSWE")
                disp.frame_state.configure(width=state_width)
                disp.state_width = state_width
        else:
            state_width = None
            if disp.state_width is not None:
                disp.frame_right.grid_forget()
                disp.frame_state.configure(width=state_width)
                disp.state_width = state_width'''
