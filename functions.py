import threading
import time
import tkinter as tk
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from random import randint
from typing import Union

import services as service
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
        Calculates trade value and commission
        """
        coef = self.Instrument[symbol].valueOfOneContract
        if symbol[1] == "inverse":
            sumreal = qty / price * coef * fund
            if execFee is not None:
                commiss = execFee
                funding = execFee
            else:
                commiss = abs(qty) / price * coef * rate
                funding = qty / price * coef * rate
        elif symbol[1] == "spot":
            sumreal = 0
            if execFee is not None:
                commiss = execFee
            else:
                commiss = abs(qty) * price * coef * rate
            funding = 0
        else:
            sumreal = -qty * price * coef * fund
            if execFee is not None:
                commiss = execFee
                funding = execFee
            else:
                commiss = abs(qty) * price * coef * rate
                funding = qty * price * coef * rate

        return {"sumreal": sumreal, "commiss": commiss, "funding": funding}

    def add_symbol(self: Markets, symbol: tuple) -> None:
        # if symbol not in self.full_symbol_list:
        #    self.full_symbol_list.append(symbol)
        if symbol not in self.Instrument.get_keys():
            WS.get_instrument(self, symbol=symbol)
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
                    print("_____query:", query)
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
        var.lock.acquire(True)
        try:
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
                            try:
                                clientID = int(row["clOrdID"])
                            except Exception:
                                clientID = 0
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
                            var.queue_info.put(
                                {
                                    "market": self.name,
                                    "message": message,
                                    "time": datetime.now(tz=timezone.utc),
                                    "warning": False,
                                }
                            )
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
                    if not info:
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
                            price=row["lastPx"],
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
                            row["lastPx"],
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
                        if not info:
                            Function.funding_display(self, message)
                diff = row["lastQty"] - position
                if (
                    diff != 0
                ):  # robots with open positions have been taken, but some quantity is still left
                    calc = Function.calculate(
                        self,
                        symbol=row["symbol"],
                        price=row["lastPx"],
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
                        row["lastPx"],
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
                    if not info:
                        Function.funding_display(self, message)

            # New order

            elif row["execType"] == "New":
                if (
                    "clOrdID" not in row
                ):  # The order was placed from the exchange web interface
                    var.last_order += 1
                    clOrdID = str(var.last_order) + "." + ".".join(row["symbol"][:2])
                    self.orders[clOrdID] = {
                        "leavesQty": row["leavesQty"],
                        "price": row["price"],
                        "SYMBOL": row["symbol"],
                        "CATEGORY": row["symbol"][1],
                        "MARKET": self.name,
                        "transactTime": row["transactTime"],
                        "SIDE": row["side"],
                        "EMI": row["symbol"],
                        "orderID": row["orderID"],
                        "clOrdID": clOrdID,
                    }
                    info = "Outside placement: "
                else:
                    info = ""
                Function.orders_processing(self, row=row, info=info)
            elif row["execType"] == "Canceled":
                Function.orders_processing(self, row=row)
            elif row["execType"] == "Replaced":
                Function.orders_processing(self, row=row)
        finally:
            var.lock.release()

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
            for clOrdID in self.orders:
                if "orderID" in row:
                    if self.orders[clOrdID]["orderID"] == row["orderID"]:
                        break
            else:
                clOrdID = "Empty clOrdID. The order was not sent via Tmatic."
                print(clOrdID)
        if "orderID" not in row:  # for Bitmex: orderID is missing when text='Closed to
            # conform to lot size', last time 2021-05-31
            row["orderID"] = row["text"]
        price = row["price"]
        info_q = ""
        info_p = ""
        if row["execType"] == "Canceled":
            info_p = price
            info_q = row["orderQty"] - row["cumQty"]
            if clOrdID in self.orders:
                var.queue_order.put(
                    {"action": "delete", "clOrdID": clOrdID, "market": self.name}
                )
                del self.orders[clOrdID]
                Function.not_defined_robot_color(self, clOrdID=clOrdID)
            else:
                var.logger.warning(
                    self.name
                    + ": execType "
                    + row["execType"]
                    + " - order with clOrdID "
                    + clOrdID
                    + " not found."
                )
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
                    self.orders[clOrdID] = {
                        "leavesQty": row["leavesQty"],
                        "price": row["price"],
                        "SYMBOL": row["symbol"],
                        "CATEGORY": row["symbol"][1],
                        "MARKET": self.name,
                        "transactTime": row["transactTime"],
                        "SIDE": row["side"],
                        "EMI": _emi,
                        "orderID": row["orderID"],
                        "clOrdID": clOrdID,
                    }
                    Function.not_defined_robot_color(self, emi=_emi)
                info_p = price
                info_q = row["orderQty"]
            elif row["execType"] == "Trade":
                info_p = row["lastPx"]
                info_q = row["lastQty"]
                if clOrdID in self.orders:
                    precision = self.Instrument[row["symbol"]].precision
                    if row["side"] == "Sell":
                        self.orders[clOrdID]["leavesQty"] -= row["lastQty"]
                    else:
                        self.orders[clOrdID]["leavesQty"] += row["lastQty"]
                    self.orders[clOrdID]["leavesQty"] = round(
                        self.orders[clOrdID]["leavesQty"], precision
                    )
                    if self.orders[clOrdID]["leavesQty"] == 0:
                        del self.orders[clOrdID]
                        Function.not_defined_robot_color(self, clOrdID=clOrdID)
                    var.queue_order.put(
                        {"action": "delete", "clOrdID": clOrdID, "market": self.name}
                    )
                else:
                    if not info:
                        var.logger.warning(
                            self.name
                            + ": execType "
                            + row["execType"]
                            + " - order with clOrdID "
                            + clOrdID
                            + " not found."
                        )
            elif row["execType"] == "Replaced":
                if clOrdID in self.orders:
                    self.orders[clOrdID]["orderID"] = row["orderID"]
                    info_p = price
                    info_q = row["leavesQty"]
                    self.orders[clOrdID]["leavesQty"] = row["leavesQty"]
                    var.queue_order.put(
                        {"action": "delete", "clOrdID": clOrdID, "market": self.name}
                    )
                else:
                    var.logger.warning(
                        self.name
                        + ": execType "
                        + row["execType"]
                        + " - order with clOrdID "
                        + clOrdID
                        + " not found."
                    )
            if clOrdID in self.orders:
                # self.orders[clOrdID]["leavesQty"] = row["leavesQty"]
                self.orders[clOrdID]["price"] = price
                self.orders[clOrdID]["transactTime"] = row["transactTime"]
        try:
            t = clOrdID.split(".")
            int(t[0])
            emi = ".".join(t[1:3])
        except ValueError:
            emi = clOrdID
        if info_q:
            info_q = Function.volume(self, qty=info_q, symbol=row["symbol"])
            info_p = Function.format_price(self, number=info_p, symbol=row["symbol"])
            if not info:
                message = (
                    row["execType"]
                    + " "
                    + row["side"]
                    + ": "
                    + emi
                    + " p="
                    + str(info_p)
                    + " q="
                    + info_q
                )
                var.queue_info.put(
                    {
                        "market": self.name,
                        "message": message,
                        "time": datetime.now(tz=timezone.utc),
                        "warning": False,
                    }
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
        if clOrdID in self.orders:
            var.queue_order.put({"action": "put", "order": self.orders[clOrdID]})

        """elif row["leavesQty"] == 0:
            info_p = row["lastPx"]
            info_q = row["lastQty"]
            if clOrdID in self.orders:
                if not info:
                    var.queue_order.put(
                        {"action": "delete", "clOrdID": clOrdID, "market": self.name}
                    )
                del self.orders[clOrdID]
                Function.not_defined_robot_color(self, clOrdID=clOrdID)
            else:
                if not info:
                    var.logger.warning(
                        self.name
                        + ": execType "
                        + row["execType"]
                        + " - order with clOrdID "
                        + clOrdID
                        + " not found."
                    )"""

    def trades_display(self: Markets, val: dict, init=False) -> Union[None, list]:
        """
        Update trades widget
        """
        Function.add_symbol(self, symbol=val["SYMBOL"])
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
        TreeTable.trades.insert(values=row, market=self.name, configure=val["SIDE"])

    def funding_display(self: Markets, val: dict, init=False) -> Union[None, list]:
        """
        Update funding widget
        """
        Function.add_symbol(self, symbol=val["SYMBOL"])
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
        TreeTable.funding.insert(values=row, market=self.name, configure=configure)

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
        clOrdID = val["clOrdID"]
        if clOrdID in TreeTable.orders.children:
            TreeTable.orders.delete(iid=clOrdID)
        TreeTable.orders.insert(
            values=row, market=self.name, iid=val["clOrdID"], configure=val["SIDE"]
        )

    def volume(self: Markets, qty: Union[int, float], symbol: tuple) -> str:
        if qty in ["", "None"]:
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
        # adaptive_screen(self)
        if utc.hour != var.refresh_hour:
            Function.select_database(self, "select count(*) cou from robots")
            var.refresh_hour = utc.hour
            var.logger.info("Emboldening SQLite")
        disp.label_time["text"] = time.asctime(time.gmtime())
        Function.refresh_tables(self)

    def refresh_tables(self: Markets) -> None:
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
        instrument = self.Instrument[var.symbol]
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
            robot["y_position"] = num
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
                if robot["STATUS"] in ["RESERVED", "NOT IN LIST"]:
                    if robot["POS"] in [0, "None"]:
                        tree.paint(row=num, configure="Normal")
                    else:
                        tree.paint(row=num, configure="Red")
                elif robot["STATUS"] == "NOT DEFINED":
                    Function.not_defined_robot_color(self, emi=robot["EMI"])

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
            status = str(ws.connect_count) + " " + "ONLINE"
            if not ws.api_is_active:
                status = "RELOADING..."
            compare = service.add_space([ws.name, ws.account_disp, status])
            if compare != tree.cache[num]:
                tree.cache[num] = compare
                tree.update(row=num, values=[compare])
                configure = "Market" if "ONLINE" in status else "Reload"
                TreeTable.market.paint(
                    row=var.market_list.index(ws.name), configure=configure
                )

    def close_price(self: Markets, symbol: tuple, pos: float) -> Union[float, None]:
        instrument = self.Instrument[symbol]
        if pos > 0 and instrument.bids:
            close = instrument.bids[0][0]
        elif pos <= 0 and instrument.asks:
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
            self, number=price, symbol=self.orders[clOrdID]["SYMBOL"]
        )
        var.logger.info(
            "Putting orderID="
            + self.orders[clOrdID]["orderID"]
            + " clOrdID="
            + clOrdID
            + " price="
            + price_str
            + " qty="
            + str(qty)
        )
        if price != self.orders[clOrdID]["price"]:  # the price alters
            WS.replace_limit(
                self,
                quantity=qty,
                price=price_str,
                orderID=self.orders[clOrdID]["orderID"],
                symbol=self.orders[clOrdID]["SYMBOL"],
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
            info_display(self.name, message)
        if error:
            TreeTable.market.paint(row=row, configure="Reload")
        else:
            TreeTable.market.paint(row=row, configure="Market")
        TreeTable.market.tree.update()

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

    def find_order(self: Markets, price: float, symbol: str) -> Union[float, str]:
        qty = 0
        for clOrdID in self.orders:
            if (
                self.orders[clOrdID]["price"] == price
                and self.orders[clOrdID]["SYMBOL"] == symbol
            ):
                qty += self.orders[clOrdID]["leavesQty"]
        if not qty:
            qty = ""

        return qty

    def not_defined_robot_color(self: Markets, emi=None, clOrdID=None) -> None:
        """
        A robot has NOT DEFINED status if it is not listed in the robots
        SQLite table, but has an open position or an active order. In this
        case, it appears on the screen in red.
        """
        if self.name == var.current_market:
            if clOrdID:
                dot = clOrdID.find(".")
                if dot != -1:
                    emi = clOrdID[dot + 1 :]
            for num, robot in enumerate(self.robots.values()):
                if emi == robot["EMI"]:
                    if var.current_market == robot["MARKET"]:
                        if robot["STATUS"] == "NOT DEFINED":
                            if hasattr(TreeTable, "robots"):
                                tree = TreeTable.robots
                                for clOrdID in self.orders:
                                    if emi in clOrdID:
                                        tree.paint(row=num, configure="Red")
                                        break
                                else:
                                    if self.robots[emi]["POS"] == 0:
                                        tree.paint(row=num, configure="Normal")
                                    else:
                                        tree.paint(row=num, configure="Red")
                    break


def handler_order(event) -> None:
    tree = event.widget
    items = tree.selection()
    if items:
        tree.update()
        clOrdID = items[0]
        indx = TreeTable.orders.title.index("MARKET")
        ws = Markets[TreeTable.orders.tree.item(clOrdID)["values"][indx]]

        def on_closing() -> None:
            disp.order_window_trigger = "off"
            order_window.destroy()
            tree.selection_remove(items[0])

        def delete(order: dict, clOrdID: str) -> None:
            try:
                ws.orders[clOrdID]
            except KeyError:
                message = "Order " + clOrdID + " does not exist!"
                info_display(ws.name, message)
                var.logger.info(message)
                return
            if not ws.logNumFatal:
                Function.del_order(ws, order=order, clOrdID=clOrdID)
            else:
                info_display(ws.name, "The operation failed. Websocket closed!")
            on_closing()

        def replace(clOrdID) -> None:
            try:
                ws.orders[clOrdID]
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
            if not ws.logNumFatal:
                roundSide = ws.orders[clOrdID]["leavesQty"]
                if ws.orders[clOrdID]["SIDE"] == "Sell":
                    roundSide = -roundSide
                price = Function.round_price(
                    ws,
                    symbol=ws.orders[clOrdID]["SYMBOL"],
                    price=float(price_replace.get()),
                    rside=roundSide,
                )
                if price == ws.orders[clOrdID]["price"]:
                    info_display(ws.name, "Price is the same but must be different!")
                    return
                clOrdID = Function.put_order(
                    ws,
                    clOrdID=clOrdID,
                    price=price,
                    qty=ws.orders[clOrdID]["leavesQty"],
                )
            else:
                info_display(ws.name, "The operation failed. Websocket closed!")
            on_closing()

        if disp.order_window_trigger == "off":
            order = ws.orders[clOrdID]
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
                number=ws.orders[clOrdID]["price"],
                symbol=ws.orders[clOrdID]["SYMBOL"],
            )
            label1["text"] = (
                "market\t"
                + ws.orders[clOrdID]["SYMBOL"][2]
                + "\nsymbol\t"
                + ".".join(ws.orders[clOrdID]["SYMBOL"][:2])
                + "\nside\t"
                + ws.orders[clOrdID]["SIDE"]
                + "\nclOrdID\t"
                + clOrdID
                + "\nprice\t"
                + order_price
                + "\nquantity\t"
                + Function.volume(
                    ws,
                    qty=ws.orders[clOrdID]["leavesQty"],
                    symbol=ws.orders[clOrdID]["SYMBOL"],
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
        tree.selection_remove(items[0])
    ws = Markets[var.current_market]
    if ws.name == "Bitmex" and var.symbol[1] == "spot":
        warning_window("Tmatic does not support spot trading on Bitmex.")
        return
    if not ws.api_is_active:
        info_display(
            name=ws.name,
            message=ws.name + ": You cannot add new orders during a reboot.",
            warning=True,
        )
        return
    disp.handler_orderbook_symbol = var.symbol

    def first_price(prices: list) -> float:
        if prices:
            return prices[0][0]
        else:
            return "None"

    def refresh() -> None:
        while disp.refresh_handler_orderbook:
            try:
                book_window.title(var.symbol)
            except Exception:
                pass
            if disp.handler_orderbook_symbol != var.symbol:
                ws = Markets[var.current_market]
                entry_price_ask.delete(0, "end")
                entry_price_ask.insert(
                    0,
                    Function.format_price(
                        ws,
                        number=first_price(ws.Instrument[var.symbol].asks),
                        symbol=var.symbol,
                    ),
                )
                entry_price_bid.delete(0, "end")
                entry_price_bid.insert(
                    0,
                    Function.format_price(
                        ws,
                        number=first_price(ws.Instrument[var.symbol].bids),
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
                        label=option,
                        command=lambda v=emi_number, optn=option: v.set(optn),
                    )
                emi_number.set("")
                disp.handler_orderbook_symbol = var.symbol
            time.sleep(0.1)

    def on_closing() -> None:
        disp.book_window_trigger = "off"
        disp.refresh_handler_orderbook = False
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
                number=first_price(instrument.asks),
                symbol=var.symbol,
            ),
        )
        entry_price_bid.insert(
            0,
            Function.format_price(
                ws,
                number=first_price(instrument.bids),
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
        disp.refresh_handler_orderbook = True
        t = threading.Thread(target=refresh)
        t.start()


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
    TreeTable.orderbook.clear_color_cell()
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
            if Markets[var.current_market].api_is_active:
                TreeTable.market.paint(
                    row=var.market_list.index(shift), configure="Market"
                )
            else:
                TreeTable.market.paint(
                    row=var.market_list.index(shift), configure="Reload"
                )
            ws = Markets[var.current_market]
            var.symbol = ws.symbol_list[0]
            clear_tables()


def handler_robots(event) -> None:
    emi = None
    ws = Markets[var.current_market]
    tree = event.widget
    items = tree.selection()
    if items:
        item = items[0]
        if not ws.api_is_active:
            info_display(
                name=ws.name,
                message=ws.name
                + ": You cannot change the bot's status during a reboot.",
                warning=True,
            )
            tree.selection_remove(item)
            return
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
                        TreeTable.robots.paint(row=row, configure="Red")
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


def init_tables() -> None:
    ws = Markets[var.current_market]
    TreeTable.orderbook = TreeviewTable(
        frame=disp.frame_orderbook,
        name="orderbook",
        title=var.name_book,
        size=disp.num_book,
        bind=handler_orderbook,
        multicolor=True,
        autoscroll=True,
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
        hide=["6", "3"],
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
        autoscroll=True,
    )
    TreeTable.results = TreeviewTable(
        frame=disp.frame_results,
        name="results",
        size=len(ws.Result.get_keys()),
        title=var.name_results,
        bind=handler_account,
    )
    TreeTable.position.set_selection()
    indx = var.market_list.index(var.current_market)
    TreeTable.market.set_selection(index=indx)
    robot_status(ws)


TreeTable.orders = TreeviewTable(
    frame=disp.frame_orders,
    name="orders",
    size=0,
    title=var.name_order,
    bind=handler_order,
    hide=["8", "3", "5"],
)
TreeTable.trades = TreeviewTable(
    frame=disp.frame_trades,
    name="trades",
    size=0,
    title=var.name_trade,
    bind=handler_account,
    hide=["8", "3", "5"],
)
TreeTable.funding = TreeviewTable(
    frame=disp.frame_funding,
    name="funding",
    size=0,
    title=var.name_funding,
    bind=handler_account,
    hide=["8", "3", "5"],
)


def robot_status(ws: Markets):
    for row, emi in enumerate(ws.robots):
        if ws.robots[emi]["STATUS"] in ["NOT IN LIST", "OFF", "NOT DEFINED"] or (
            ws.robots[emi]["STATUS"] == "RESERVED"
            and ws.robots[emi]["POS"] != 0
            and ws.robots[emi]["CATEGORY"] != "spot"
        ):
            TreeTable.robots.paint(row=row, configure="Red")
        else:
            TreeTable.robots.paint(row=row, configure="Normal")


def clear_tables():
    var.lock_market_switch.acquire(True)
    ws = Markets[var.current_market]
    TreeTable.position.init(size=len(ws.symbol_list))
    TreeTable.account.init(size=len(ws.Account.get_keys()))
    TreeTable.robots.init(size=len(ws.robots))
    TreeTable.orderbook.init(size=disp.num_book)
    TreeTable.results.init(size=len(ws.Result.get_keys()))
    TreeTable.position.set_selection()
    robot_status(ws)
    var.lock_market_switch.release()


change_color(color=disp.title_color, container=disp.root)
