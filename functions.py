import time
import tkinter as tk
from collections import OrderedDict
from datetime import datetime, timedelta
from random import randint
from typing import Union

from api.api import WS
from api.variables import Variables
from api.websockets import Websockets
from bots.variables import Variables as bot
from common.variables import Variables as var
from display.functions import info_display
#from display.init import Tables as table
#from display.init import trades, funding, orders
from display.variables import Variables as disp
from display.variables import GridTable, ListBoxTable

db = var.env["MYSQL_DATABASE"]


class Tables:
    position: GridTable
    account: GridTable
    robots: GridTable
    exchange: GridTable
    orderbook: GridTable


class Function(WS, Variables):
    def calculate(
        self, symbol: tuple, price: float, qty: float, rate: int, fund: int
    ) -> dict:
        """
        Calculate sumreal and commission
        """
        coef = abs(
            self.instruments[symbol]["multiplier"]
            / var.currency_divisor[self.instruments[symbol]["settlCurrency"]]
        )
        if self.instruments[symbol]["isInverse"]:
            sumreal = qty / price * coef * fund
            commiss = abs(qty) / price * coef * rate
            funding = qty / price * coef * rate
        else:
            sumreal = -qty * price * coef * fund
            commiss = abs(qty) * price * coef * rate
            funding = qty * price * coef * rate

        return {"sumreal": sumreal, "commiss": commiss, "funding": funding}

    def add_symbol(self, symbol: tuple) -> None:
        if symbol not in self.full_symbol_list:
            self.full_symbol_list.append(symbol)
            if symbol not in self.instruments:
                self.get_instrument(name=self.name, symbol=symbol)
            Function.rounding(self)
        if symbol not in self.positions:
            self.get_position(name=self.name, symbol=symbol)

    def rounding(self) -> None:
        if self.name not in disp.price_rounding:
            disp.price_rounding[self.name] = OrderedDict()
        for symbol, instrument in self.instruments.items():
            tickSize = str(instrument["tickSize"])
            if tickSize.find(".") > 0:
                disp.price_rounding[self.name][symbol] = (
                    len(tickSize) - 1 - tickSize.find(".")
                )
            elif tickSize.find("e-") > 0:
                disp.price_rounding[self.name][symbol] = int(
                    tickSize[tickSize.find("e-") + 2 :]
                )
            else:
                disp.price_rounding[self.name][symbol] = 0

    def timeframes_data_filename(self, emi: str, symbol: tuple, timefr: str) -> str:
        return "data/" + symbol[0] + symbol[1] + str(timefr) + "_EMI" + emi + ".txt"

    def save_timeframes_data(self, frame: dict) -> None:
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

    def noll(self, val: str, length: int) -> str:
        r = ""
        for _ in range(length - len(val)):
            r = r + "0"

        return r + val

    def read_database(self, execID: str, user_id: int) -> list:
        """
        Load a row by execID from the database
        """
        var.cursor_mysql.execute(
            "select EXECID from " + db + ".coins where EXECID=%s and account=%s",
            (execID, user_id),
        )
        data = var.cursor_mysql.fetchall()

        return data

    def insert_database(self, values: list) -> None:
        """
        Insert row into database
        """
        var.cursor_mysql.execute(
            "insert into "
            + db
            + ".coins (EXECID,EMI,REFER,CURRENCY,SYMBOL,CATEGORY,EXCHANGE,\
                SIDE,QTY,QTY_REST,PRICE,THEOR_PRICE,TRADE_PRICE,SUMREAL,COMMISS,\
                    CLORDID,TTIME,ACCOUNT) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,\
                        %s,%s,%s,%s,%s,%s,%s,%s)",
            values,
        )
        var.connect_mysql.commit()

    def transaction(self, row: dict, info: str = "") -> None:
        """
        Trades and funding processing
        """
        Function.add_symbol(self, symbol=row["symbol"])
        time_struct = datetime.strptime(
            row["transactTime"][:-1], "%Y-%m-%dT%H:%M:%S.%f"
        )

        # Trade

        if row["execType"] == "Trade":
            if "clOrdID" in row:
                dot = row["clOrdID"].find(".")
                if (
                    dot == -1
                ):  # The transaction was done from the exchange web interface,
                    # the clOrdID field is missing or clOrdID does not have EMI number
                    emi = ".".join(row["symbol"])
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
                emi = ".".join(row["symbol"])
                clientID = 0
                refer = ""
            if emi not in self.robots:
                emi = ".".join(row["symbol"])
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
                        "EXCHANGE": self.name,
                        "POS": 0,
                        "VOL": 0,
                        "COMMISS": 0,
                        "SUMREAL": 0,
                        "LTIME": time_struct,
                        "PNL": 0,
                        "CAPITAL": None,
                    }
                    message = (
                        "Robot EMI="
                        + str(emi)
                        + ". Adding to 'robots' with STATUS="
                        + status
                    )
                    info_display(self.name, message)
                    var.logger.info(message)
            data = Function.read_database(
                self, execID=row["execID"], user_id=self.user_id
            )
            if not data:
                side = 0
                lastQty = row["lastQty"]
                if row["side"] == "Sell":
                    lastQty = -row["lastQty"]
                    side = 1
                calc = Function.calculate(
                    self,
                    symbol=row["symbol"],
                    price=row["lastPx"],
                    qty=float(lastQty),
                    rate=row["commission"],
                    fund=1,
                )
                self.robots[emi]["POS"] += lastQty
                self.robots[emi]["VOL"] += abs(lastQty)
                self.robots[emi]["COMMISS"] += calc["commiss"]
                self.robots[emi]["SUMREAL"] += calc["sumreal"]
                self.robots[emi]["LTIME"] = time_struct
                self.accounts[row["settlCurrency"]]["COMMISS"] += calc["commiss"]
                self.accounts[row["settlCurrency"]]["SUMREAL"] += calc["sumreal"]
                values = [
                    row["execID"],
                    emi,
                    refer,
                    row["settlCurrency"],
                    row["symbol"][0],
                    row["symbol"][1],
                    self.name,
                    side,
                    abs(lastQty),
                    row["leavesQty"],
                    row["price"],
                    0,
                    row["lastPx"],
                    calc["sumreal"],
                    calc["commiss"],
                    clientID,
                    time_struct,
                    self.user_id,
                ]
                Function.insert_database(self, values=values)
                message = {
                    "SYMBOL": row["symbol"],
                    "CATEGORY": row["symbol"][1], 
                    "EXCHANGE": row["exchange"], 
                    "TTIME": row["transactTime"],
                    "SIDE": side,
                    "TRADE_PRICE": row["lastPx"],
                    "QTY": abs(lastQty),
                    "EMI": emi,
                }
                Function.trades_display(self, val=message)
                Function.orders_processing(self, row=row, info=info)

        # Funding

        elif row["execType"] == "Funding":
            message = {
                "SYMBOL": row["symbol"],
                "TTIME": row["transactTime"],
                "PRICE": row["price"],
                "CATEGORY": row["CATEGORY"], 
            }
            position = 0
            true_position = row["lastQty"]
            true_funding = row["commission"]
            if row["foreignNotional"] > 0:
                true_position = -true_position
                true_funding = -true_funding
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
                        rate=true_funding,
                        fund=0,
                    )
                    message["EXCHANGE"] = self.robots[emi]["EXCHANGE"]
                    message["EMI"] = self.robots[emi]["EMI"]
                    message["QTY"] = self.robots[emi]["POS"]
                    message["COMMISS"] = calc["funding"]
                    values = [
                        row["execID"],
                        self.robots[emi]["EMI"],
                        "",
                        row["settlCurrency"],
                        row["symbol"][0],
                        row["symbol"][1],
                        self.name,
                        -1,
                        self.robots[emi]["POS"],
                        0,
                        row["price"],
                        0,
                        row["price"],
                        calc["sumreal"],
                        calc["funding"],
                        0,
                        time_struct,
                        self.user_id,
                    ]
                    Function.insert_database(self, values=values)
                    self.robots[emi]["COMMISS"] += calc["funding"]
                    self.robots[emi]["LTIME"] = time_struct
                    self.accounts[row["settlCurrency"]]["FUNDING"] += calc["funding"]
                    Function.funding_display(self, message)
            diff = true_position - position
            if (
                diff != 0
            ):  # robots with open positions have been taken, but some quantity is still left
                calc = Function.calculate(
                    self,
                    symbol=row["symbol"],
                    price=row["price"],
                    qty=float(diff),
                    rate=true_funding,
                    fund=0,
                )
                emi = ".".join(row["symbol"])
                if emi not in self.robots:
                    var.logger.error(
                        "Funding could not appear until the EMI="
                        + emi
                        + " was traded. View your trading history."
                    )
                    exit(1)
                message["EXCHANGE"] = self.robots[emi]["EXCHANGE"]
                message["EMI"] = self.robots[emi]["EMI"]
                message["QTY"] = diff
                message["COMMISS"] = calc["funding"]
                values = [
                    row["execID"],
                    self.robots[emi]["EMI"],
                    "",
                    row["settlCurrency"],
                    row["symbol"][0],
                    row["symbol"][1],
                    self.name,
                    -1,
                    diff,
                    0,
                    row["price"],
                    0,
                    row["price"],
                    calc["sumreal"],
                    calc["funding"],
                    0,
                    time_struct,
                    self.user_id,
                ]
                Function.insert_database(self, values=values)
                self.robots[emi]["COMMISS"] += calc["funding"]
                self.robots[emi]["LTIME"] = time_struct
                self.accounts[row["settlCurrency"]]["FUNDING"] += calc["funding"]
                Function.funding_display(self, message)

        # New order

        elif row["execType"] == "New":
            if (
                "clOrdID" not in row
            ):  # The order was placed from the exchange web interface
                var.last_order += 1
                clOrdID = str(var.last_order) + "." + row["symbol"]
                var.orders[clOrdID] = {
                    "leavesQty": row["leavesQty"],
                    "price": row["price"],
                    "symbol": row["symbol"],
                    "category": row["symbol"][1],
                    "exchange": self.name,
                    "transactTime": row["transactTime"],
                    "side": row["side"],
                    "emi": row["symbol"],
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

    def order_number(self, clOrdID: str) -> int:
        for number, id in enumerate(var.orders):
            if id == clOrdID:
                return number

    def orders_processing(self, row: dict, info: str = "") -> None:
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
                if var.orders[clOrdID]["orderID"] == row["orderID"]:
                    break
            else:
                clOrdID = "Empty clOrdID. The order was not sent via Tmatic."
                print(clOrdID)
        if "orderID" not in row:  # orderID is missing when text='Closed to
            # conform to lot size', last time 2021-05-31
            row["orderID"] = row["text"]
        price = row["price"]
        if row["execType"] == "Canceled":
            info_p = price
            info_q = row["orderQty"] - row["cumQty"]
            if clOrdID in var.orders:
                orders.delete(row=Function.order_number(self, clOrdID))
                del var.orders[clOrdID]
        elif row["leavesQty"] == 0:
            info_p = row["lastPx"]
            info_q = row["lastQty"]
            if clOrdID in var.orders:
                orders.delete(row=Function.order_number(self, clOrdID))
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
                        "symbol": row["symbol"],
                        "category": row["symbol"][1],
                        "exchange": self.name,
                        "transactTime": str(datetime.utcnow()),
                        "side": row["side"],
                        "emi": _emi,
                        "orderID": row["orderID"],
                    }
                    var.orders.move_to_end(clOrdID, last=False)
                info_p = price
                info_q = row["orderQty"]
            elif row["execType"] == "Trade":
                info_p = row["lastPx"]
                info_q = row["lastQty"]
                if clOrdID in var.orders:
                    orders.delete(row=Function.order_number(self, clOrdID))
            elif row["execType"] == "Replaced":
                var.orders[clOrdID]["leavesQty"] = row["leavesQty"]
                var.orders[clOrdID]["price"] = row["price"]
                var.orders[clOrdID]["transactTime"] = datetime.utcnow()
                var.orders[clOrdID]["orderID"] = row["orderID"]
                info_p = price
                info_q = row["leavesQty"]
                print("----------number------------")
                print(Function.order_number(self, clOrdID), clOrdID)
                orders.delete(row=Function.order_number(self, clOrdID))
                var.orders.move_to_end(clOrdID, last=False)
            if (
                clOrdID in var.orders
            ):  # var.orders might be empty if we are here from trading_history()
                var.orders[clOrdID]["leavesQty"] = row["leavesQty"]
                var.orders[clOrdID]["price"] = price
        info_q = Function.volume(self, qty=info_q, symbol=row["symbol"])
        info_p = Function.format_price(self, number=info_p, symbol=row["symbol"])
        try:
            t = clOrdID.split(".")
            int(t[0])
            emi = ".".join(t[1:])
        except ValueError:
            emi = clOrdID
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
            info + row["execType"] + " %s: orderID=%s clOrdID=%s price=%s qty=%s",
            row["side"],
            row["orderID"],
            clOrdID,
            str(info_p),
            info_q,
        )
        Function.orders_display(self, clOrdID=clOrdID, execType=row["execType"])

    def trades_display(self, val: dict) -> None:
        """
        Update trades widget
        """       
        val["TTIME"] = str(val["TTIME"])[2:]
        val["TTIME"] = val["TTIME"].replace("-", "")
        val["TTIME"] = val["TTIME"].replace("T", " ")[:15]
        if val["SIDE"] == 0:
            val["SIDE"] = "Buy"
        else:
            val["SIDE"] = "Sell"
        elements = [
            val["TTIME"],
            val["SYMBOL"][0],
            val["CATEGORY"],
            val["EXCHANGE"], 
            val["SIDE"],
            Function.format_price(
                self,
                number=float(val["TRADE_PRICE"]),
                symbol=val["SYMBOL"],
            ),
            val["QTY"],
            val["EMI"],
        ]
        trades.insert(row=0, elements=elements)
        if val["SIDE"] == "Buy":
            trades.paint(row=0, color=disp.buy_color)
        else:
            trades.paint(row=0, color=disp.sell_color)

    def funding_display(self, val: dict) -> None:
        """
        Update funding widgwt
        """
        val["TTIME"] = str(val["TTIME"])[2:]
        val["TTIME"] = val["TTIME"].replace("-", "")
        val["TTIME"] = val["TTIME"].replace("T", " ")[:15]
        elements = [
            val["TTIME"],
            val["SYMBOL"][0],
            val["CATEGORY"],
            val["EXCHANGE"], 
            Function.format_price(
                self,
                number=float(val["PRICE"]),
                symbol=val["SYMBOL"],
            ),
            "{:.7f}".format(val["COMMISS"]),
            val["QTY"], 
            val["EMI"],
        ]
        funding.insert(row=0, elements=elements)

    def orders_display(self, clOrdID: str, execType: str) -> None:
        """
        Update Orders widget
        """
        if clOrdID in var.orders:
            emi = var.orders[clOrdID]["emi"]
            tm = str(var.orders[clOrdID]["transactTime"])[2:]
            tm = tm.replace("-", "")
            tm = tm.replace("T", " ")[:15]
            elements = [
                tm, 
                var.orders[clOrdID]["symbol"][0],
                var.orders[clOrdID]["category"], 
                var.orders[clOrdID]["exchange"], 
                var.orders[clOrdID]["side"],
                Function.format_price(
                        self,
                        number=var.orders[clOrdID]["price"],
                        symbol=var.orders[clOrdID]["symbol"],
                    ),
                var.orders[clOrdID]["leavesQty"], 
                emi,
            ]
            orders.insert(row=0, elements=elements)
            if var.orders[clOrdID]["side"] == "Buy":
                orders.paint(row=0, color=disp.buy_color)
            else:
                orders.paint(row=0, color=disp.sell_color)

        print("---------orders---------")
        print(var.orders.keys(), sep = "\n")


    def volume(self, qty: int, symbol: tuple) -> str:
        if qty == 0:
            qty = "0"
        else:
            qty /= self.instruments[symbol]["myMultiplier"]
            num = len(str(self.instruments[symbol]["myMultiplier"])) - len(
                str(self.instruments[symbol]["lotSize"])
            )
            if num > 0:
                qty = "{:.{precision}f}".format(qty, precision=num)
            else:
                qty = "{:.{precision}f}".format(qty, precision=0)

        return qty

    def format_price(self, number: float, symbol: tuple) -> str:
        rounding = disp.price_rounding[self.name][symbol]
        number = "{:.{precision}f}".format(number, precision=rounding)
        dot = number.find(".")
        if dot == -1:
            number = number + "."
        n = len(number) - 1 - number.find(".")
        for _ in range(rounding - n):
            number = number + "0"

        return number

    def robots_entry(self, utc: datetime) -> None:
        """
        Processing timeframes and entry point into robot algorithms
        """
        self.ticker = self.get_ticker(self.name)
        for symbol, timeframes in self.frames.items():
            for timefr, values in timeframes.items():
                if utc > values["time"] + timedelta(minutes=timefr):
                    for emi in values["robots"]:
                        if (
                            self.robots[emi]["STATUS"] == "WORK"
                            and disp.f9 == "ON"
                            and bot.robo
                        ):
                            # Robots entry point
                            bot.robo[emi](
                                robot=self.robots[emi],
                                frame=values["data"],
                                ticker=self.ticker[symbol],
                                instrument=self.instruments[symbol],
                            )
                        Function.save_timeframes_data(
                            self,
                            frame=values["data"][-1],
                        )
                    next_minute = int(utc.minute / timefr) * timefr
                    dt_now = datetime(
                        utc.year, utc.month, utc.day, utc.hour, next_minute, 0, 0
                    )
                    values["data"].append(
                        {
                            "date": (utc.year - 2000) * 10000
                            + utc.month * 100
                            + utc.day,
                            "time": utc.hour * 10000 + utc.minute * 100,
                            "bid": self.ticker[symbol]["bid"],
                            "ask": self.ticker[symbol]["ask"],
                            "hi": self.ticker[symbol]["ask"],
                            "lo": self.ticker[symbol]["bid"],
                            "funding": self.ticker[symbol]["fundingRate"],
                            "datetime": dt_now,
                        }
                    )
                    values["time"] = dt_now

    def refresh_on_screen(self, utc: datetime) -> None:
        """
        Refresh information on screen
        """
        # Only to embolden MySQL in order to avoid 'MySQL server has gone away' error
        if utc.hour != var.refresh_hour:
            var.cursor_mysql.execute("select count(*) from " + db + ".robots")
            var.cursor_mysql.fetchall()
            var.refresh_hour = utc.hour
            var.logger.info("Emboldening MySQL")

        disp.label_time["text"] = "(" + str(self.connect_count) + ")  " + time.ctime()
        disp.label_f9["text"] = str(disp.f9)
        if disp.f9 == "ON":
            disp.label_f9.config(bg=disp.dark_green_color)
        else:
            disp.label_f9.config(bg=disp.dark_red_color)
        if self.logNumFatal == 0:
            if utc > self.message_time + timedelta(seconds=10):
                if self.message_counter == self.message_point:
                    info_display(self.name, "No data within 10 sec")
                    # disp.label_online["text"] = "NO DATA"
                    # disp.label_online.config(bg="yellow2")
                    self.urgent_announcement(self.name)
                self.message_time = utc
                self.message_point = self.message_counter
        """if self.message_counter != self.message_point:
            disp.label_online["text"] = "ONLINE"
            disp.label_online.config(bg="green3")
        if self.logNumFatal != 0:
            disp.label_online["text"] = "error " + str(self.logNumFatal)
            disp.label_online.config(bg="orange red")"""
        Function.refresh_tables(self)

    def refresh_tables(self) -> None:
        """
        Update tkinter labels in the tables
        """

        # Get funds

        funds = self.get_funds()
        for currency in self.accounts:
            for fund in funds:
                if currency == fund["currency"]:
                    self.accounts[currency]["ACCOUNT"] = fund["account"]
                    self.accounts[currency]["MARGINBAL"] = (
                        float(fund["marginBalance"]) / var.currency_divisor[currency]
                    )
                    self.accounts[currency]["AVAILABLE"] = (
                        float(fund["availableMargin"]) / var.currency_divisor[currency]
                    )
                    if "marginLeverage" in fund:
                        self.accounts[currency]["LEVERAGE"] = fund["marginLeverage"]
                    else:
                        self.accounts[currency]["LEVERAGE"] = 0
                    self.accounts[currency]["RESULT"] = self.accounts[currency][
                        "SUMREAL"
                    ]
                    break
            else:
                message = "Currency " + str(currency) + " not found."
                var.logger.error(message)
                exit(1)

        # Refresh Positions table

        mod = Tables.position.mod
        for num, symbol in enumerate(self.symbol_list):
            self.positions[symbol]["STATE"] = self.instruments[symbol]["state"]
            self.positions[symbol]["VOL24h"] = self.instruments[symbol]["volume24h"]
            self.positions[symbol]["FUND"] = round(
                self.instruments[symbol]["fundingRate"] * 100, 6
            )
            update_label(table="position", column=0, row=num + mod, val=symbol[0])
            update_label(table="position", column=1, row=num + mod, val=symbol[1])
            if self.positions[symbol]["POS"]:
                pos = Function.volume(
                    self, qty=self.positions[symbol]["POS"], symbol=symbol
                )
            else:
                pos = "0"
            update_label(table="position", column=2, row=num + mod, val=pos)
            update_label(
                table="position",
                column=3,
                row=num + mod,
                val=(
                    Function.format_price(
                        self,
                        number=self.positions[symbol]["ENTRY"],
                        symbol=symbol,
                    )
                    if self.positions[symbol]["ENTRY"] is not None
                    else 0
                ),
            )
            update_label(
                table="position",
                column=4,
                row=num + mod,
                val=(
                    self.positions[symbol]["PNL"]
                    if self.positions[symbol]["PNL"] is not None
                    else 0
                ),
            )
            update_label(
                table="position",
                column=5,
                row=num + mod,
                val=(
                    str(self.positions[symbol]["MCALL"]).replace("100000000", "inf")
                    if self.positions[symbol]["MCALL"] is not None
                    else 0
                ),
            )
            update_label(
                table="position",
                column=6,
                row=num + mod,
                val=self.positions[symbol]["STATE"],
            )
            update_label(
                table="position",
                column=7,
                row=num + mod,
                val=humanFormat(self.positions[symbol]["VOL24h"]),
            )
            if isinstance(self.instruments[symbol]["expiry"], datetime):
                tm = self.instruments[symbol]["expiry"].strftime("%y%m%d %Hh")
            else:
                tm = self.instruments[symbol]["expiry"]
            update_label(table="position", column=8, row=num + mod, val=tm)
            update_label(
                table="position",
                column=9,
                row=num + mod,
                val=self.positions[symbol]["FUND"],
            )

        # Refresh Orderbook table

        def display_order_book_values(
            val: dict, start: int, end: int, direct: int, side: str
        ) -> None:
            count = 0
            if side == "asks":
                col = 2
                color = disp.sell_color_dark
            else:
                col = 0
                color = disp.buy_color
            col_qty = abs(col - 2)
            for row in range(start, end, direct):
                vlm = ""
                price = ""
                qty = 0
                if len(val[side]) > count:
                    price = Function.format_price(
                        self, number=val[side][count][0], symbol=var.symbol
                    )
                    vlm = Function.volume(
                        self, qty=val[side][count][1], symbol=var.symbol
                    )
                    if var.orders:
                        qty = Function.volume(
                            self,
                            qty=find_order(float(price), qty, symbol=var.symbol),
                            symbol=var.symbol,
                        )
                if str(qty) != "0":
                    update_label(table="orderbook", column=col_qty, row=row, val=qty)
                    disp.labels["orderbook"][row][col_qty]["bg"] = color
                else:
                    update_label(table="orderbook", column=col_qty, row=row, val="")
                    disp.labels["orderbook"][row][col_qty]["bg"] = disp.bg_color
                update_label(table="orderbook", column=col, row=row, val=vlm)
                update_label(table="orderbook", column=1, row=row, val=price)
                count += 1

        mod = 1 - Tables.orderbook.mod
        num = int(disp.num_book / 2) - mod
        if var.order_book_depth == "quote":
            if self.ticker[var.symbol]["askSize"]:
                update_label(
                    table="orderbook",
                    column=2,
                    row=num,
                    val=Function.volume(
                        self, qty=self.ticker[var.symbol]["askSize"], symbol=var.symbol
                    ),
                )
            else:
                update_label(table="orderbook", column=2, row=num, val="")
            if self.ticker[var.symbol]["bidSize"]:
                update_label(
                    table="orderbook",
                    column=0,
                    row=num + 1,
                    val=Function.volume(
                        self, qty=self.ticker[var.symbol]["bidSize"], symbol=var.symbol
                    ),
                )
            else:
                update_label(table="orderbook", column=0, row=num + mod, val="")
            disp.labels["orderbook"][0][num + 1]["fg"] = "black"
            first_price_sell = (
                self.ticker[var.symbol]["ask"]
                + (num - 1) * self.instruments[var.symbol]["tickSize"]
            )
            first_price_buy = self.ticker[var.symbol]["bid"]
            for row in range(disp.num_book - 1):
                if row < num:
                    price = round(
                        first_price_sell
                        - row * self.instruments[var.symbol]["tickSize"],
                        disp.price_rounding[self.name][var.symbol],
                    )
                    qty = 0
                    if var.orders:
                        qty = Function.volume(
                            self,
                            qty=find_order(float(price), qty, symbol=var.symbol),
                            symbol=var.symbol,
                        )
                    if self.ticker[var.symbol]["ask"]:
                        price = Function.format_price(
                            self, number=price, symbol=var.symbol
                        )
                    else:
                        price = ""
                    update_label(table="orderbook", column=1, row=row + mod, val=price)
                    if str(qty) != "0":
                        update_label(table="orderbook", column=0, row=row + mod, val=qty)
                        disp.label_book[0][row + 1]["bg"] = "orange red"
                    else:
                        update_label(table="orderbook", column=0, row=row + mod, val="")
                        disp.labels["orderbook"][0][row + 1]["bg"] = disp.bg_color
                else:
                    price = round(
                        first_price_buy
                        - (row - num) * self.instruments[var.symbol]["tickSize"],
                        disp.price_rounding[self.name][var.symbol],
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
                    update_label(table="orderbook", column=1, row=row + mod, val=price)
                    if str(qty) != "0":
                        update_label(table="orderbook", column=2, row=row + mod, val=qty)
                        disp.labels["orderbook"][2][row + 1]["bg"] = "green2"
                    else:
                        update_label(table="orderbook", column=2, row=row + mod, val="")
                        disp.labels["orderbook"][2][row + 1]["bg"] = disp.bg_color
        else:
            val = self.market_depth10()[var.symbol]
            display_order_book_values(
                val=val, start=num + 1, end=disp.num_book - mod, direct=1, side="bids"
            )
            display_order_book_values(val=val, start=num, end=0 - mod, direct=-1, side="asks")

        # Update Robots table

        mod = Tables.robots.mod
        for num, emi in enumerate(self.robots):
            symbol = self.robots[emi]["SYMBOL"]
            price = Function.close_price(
                self, symbol=symbol, pos=self.robots[emi]["POS"]
            )
            if price:
                calc = Function.calculate(
                    self,
                    symbol=symbol,
                    price=price,
                    qty=-float(self.robots[emi]["POS"]),
                    rate=0,
                    fund=1,
                )
                self.robots[emi]["PNL"] = (
                    self.robots[emi]["SUMREAL"]
                    + calc["sumreal"]
                    - self.robots[emi]["COMMISS"]
                )
            symbol = self.robots[emi]["SYMBOL"]
            update_label(table="robots", column=0, row=num + mod, val=emi)
            update_label(table="robots", column=1, row=num + mod, val=symbol[0])
            update_label(table="robots", column=2, row=num + mod, val=symbol[1])
            update_label(
                table="robots",
                column=3,
                row=num + mod,
                val=self.instruments[symbol]["settlCurrency"],
            )
            update_label(
                table="robots", column=4, row=num + mod, val=self.robots[emi]["TIMEFR"]
            )
            update_label(
                table="robots", column=5, row=num + mod, val=self.robots[emi]["CAPITAL"]
            )
            update_label(
                table="robots", column=6, row=num + mod, val=self.robots[emi]["STATUS"]
            )
            update_label(
                table="robots",
                column=7,
                row=num + mod,
                val=humanFormat(self.robots[emi]["VOL"]),
            )
            update_label(
                table="robots",
                column=8,
                row=num + mod,
                val="{:.8f}".format(self.robots[emi]["PNL"]),
            )
            val = Function.volume(
                self,
                qty=self.robots[emi]["POS"],
                symbol=symbol,
            )
            if disp.labels_cache["robots"][num + mod][9] != val:
                if self.robots[emi]["STATUS"] == "RESERVED":
                    if self.robots[emi]["POS"] != 0:
                        disp.labels["robots"][num + mod][6]["fg"] = disp.dark_red_color
                    else:
                        disp.labels["robots"][num + mod][6]["fg"] = disp.fg_color
            update_label(
                table="robots",
                column=9,
                row=num + mod,
                val=val,
            )
            self.robots[emi]["y_position"] = num + mod

        # Refresh Account table

        mod = Tables.account.mod
        for symbol, position in self.positions.items():
            if position["POS"] != 0:
                calc = Function.calculate(
                    self,
                    symbol=symbol,
                    price=Function.close_price(
                        self, symbol=symbol, pos=position["POS"]
                    ),
                    qty=-position["POS"],
                    rate=0,
                    fund=1,
                )
                settlCurrency = self.instruments[symbol]["settlCurrency"]
                if settlCurrency in self.accounts:
                    self.accounts[settlCurrency]["RESULT"] += calc["sumreal"]
                else:
                    var.logger.error(
                        settlCurrency
                        + " not found. See the CURRENCIES variable in the .env file."
                    )
                    exit(1)
        for num, cur in enumerate(self.currencies):
            update_label(table="account", column=0, row=num + mod, val=cur)
            update_label(
                table="account",
                column=1,
                row=num + mod,
                val=format_number(number=self.accounts[cur]["MARGINBAL"]),
            )
            update_label(
                table="account",
                column=2,
                row=num + mod,
                val=format_number(number=self.accounts[cur]["AVAILABLE"]),
            )
            update_label(
                table="account",
                column=3,
                row=num + mod,
                val="{:.3f}".format(self.accounts[cur]["LEVERAGE"]),
            )
            update_label(
                table="account",
                column=4,
                row=num + mod,
                val=format_number(number=self.accounts[cur]["RESULT"]),
            )
            update_label(
                table="account",
                column=5,
                row=num + mod,
                val=format_number(number=-self.accounts[cur]["COMMISS"]),
            )
            update_label(
                table="account",
                column=6,
                row=num + mod,
                val=format_number(number=-self.accounts[cur]["FUNDING"]),
            )
            number = (
                self.accounts[cur]["MARGINBAL"]
                - self.accounts[cur]["RESULT"]
                + self.accounts[cur]["COMMISS"]
                + self.accounts[cur]["FUNDING"]
            )
            update_label(
                table="account", column=7, row=num + mod, val=format_number(number=number)
            )

        # Refresh Exchange table

        mod = Tables.exchange.mod
        for row, name in enumerate(var.exchange_list):
            ws = Websockets.connect[name]
            message = "ONLINE"
            if ws.logNumFatal != 0:
                message = "error " + str(ws.logNumFatal)
            update_label(
                table="exchange",
                column=0,
                row=row + mod,
                val=name + "\nAcc." + str(ws.user_id) + "\n" + message,
            )

    def close_price(self, symbol: tuple, pos: int) -> float:
        if symbol in self.ticker:
            close = (
                self.ticker[symbol]["bid"] if pos > 0 else self.ticker[symbol]["ask"]
            )
        else:
            close = (
                self.instruments[symbol]["bidPrice"]
                if pos > 0
                else self.instruments[symbol]["askPrice"]
            )

        return close

    def round_price(self, symbol: tuple, price: float, rside: int) -> float:
        """
        Round_price() returns rounded price: buy price goes down, sell price
        goes up according to 'tickSize'
        """
        coeff = 1 / self.instruments[symbol]["tickSize"]
        result = int(coeff * price) / coeff
        if rside < 0 and result < price:
            result += self.instruments[symbol]["tickSize"]

        return result

    def post_order(
        self,
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
        var.logger.info(
            "Posting side=" + side + " price=" + price_str + " qty=" + str(qty)
        )
        clOrdID = ""
        if side == "Sell":
            qty = -qty
        var.last_order += 1
        clOrdID = str(var.last_order) + "." + emi
        self.place_limit(
            name=name, quantity=qty, price=price_str, clOrdID=clOrdID, symbol=symbol
        )

        return clOrdID

    def put_order(
        self,
        clOrdID: str,
        price: float,
        qty: int,
    ) -> str:
        """
        Replace orders
        """
        price_str = Function.format_price(
            self, number=price, symbol=var.orders[clOrdID]["symbol"]
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
            self.replace_limit(
                name=self.name,
                quantity=qty,
                price=price_str,
                orderID=var.orders[clOrdID]["orderID"],
                symbol=var.orders[clOrdID]["symbol"],
            )

        return clOrdID

    def del_order(self, clOrdID: str) -> int:
        """
        Del_order() function cancels orders
        """
        message = (
            "Deleting orderID=" + var.orders[clOrdID]["orderID"] + " clOrdID=" + clOrdID
        )
        var.logger.info(message)
        self.remove_order(name=self.name, orderID=var.orders[clOrdID]["orderID"])

        return self.logNumFatal


def ticksize_rounding(price: float, ticksize: float) -> float:
    """
    Rounds the price depending on the tickSize value
    """
    arg = 1 / ticksize
    res = round(price * arg, 0) / arg

    return res


def handler_order(event) -> None:
    row_position = event.widget.curselection()
    if row_position:
        ws = Websockets.connect[var.current_exchange]
        for num, clOrdID in enumerate(var.orders):            
            if num == row_position[0] - orders.mod:
                break

        def on_closing() -> None:
            disp.order_window_trigger = "off"
            order_window.destroy()

        def delete(clOrdID) -> None:
            try:
                var.orders[clOrdID]
            except KeyError:
                message = "Order " + clOrdID + " does not exist!"
                info_display(ws.name, message)
                var.logger.info(message)
                return
            if ws.logNumFatal == 0:
                Function.del_order(ws, clOrdID=clOrdID)
                #orders.delete(row_position)
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
            except KeyError:
                info_display(ws.name, "Price must be numeric!")
                return
            if ws.logNumFatal == 0:
                roundSide = var.orders[clOrdID]["leavesQty"]
                if var.orders[clOrdID]["side"] == "Sell":
                    roundSide = -roundSide
                price = Function.round_price(
                    ws,
                    symbol=var.orders[clOrdID]["symbol"],
                    price=float(price_replace.get()),
                    rside=roundSide,
                )
                if price == var.orders[clOrdID]["price"]:
                    info_display(ws.name, "Price is the same but must be different!")
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
            disp.order_window_trigger = "on"
            order_window = tk.Toplevel(disp.root, pady=10, padx=10)
            cx = disp.root.winfo_pointerx()
            cy = disp.root.winfo_pointery()
            order_window.geometry("+{}+{}".format(cx - 200, cy - 50))
            order_window.title("Delete order ")
            order_window.protocol("WM_DELETE_WINDOW", on_closing)
            order_window.attributes("-topmost", 1)
            frame_up = tk.Frame(order_window)
            frame_dn = tk.Frame(order_window)
            label1 = tk.Label(frame_up, justify="left")
            label1["text"] = (
                "number\t"
                + str(row_position)
                + "\nsymbol\t"
                + ".".join(var.orders[clOrdID]["symbol"])
                + "\nside\t"
                + var.orders[clOrdID]["side"]
                + "\nclOrdID\t"
                + clOrdID
                + "\nprice\t"
                + Function.format_price(
                    ws,
                    number=var.orders[clOrdID]["price"],
                    symbol=var.orders[clOrdID]["symbol"],
                )
                + "\nquantity\t"
                + str(var.orders[clOrdID]["leavesQty"])
            )
            label_price = tk.Label(frame_dn)
            label_price["text"] = "Price "
            label1.pack(side="left")
            button = tk.Button(frame_dn, text="Delete order", command=lambda id=clOrdID: delete(id))
            price_replace = tk.StringVar()
            entry_price = tk.Entry(
                frame_dn, width=10, bg="white", textvariable=price_replace
            )
            button_replace = tk.Button(frame_dn, text="Replace", command=lambda id=clOrdID: replace(id))
            button.pack(side="right")
            label_price.pack(side="left")
            entry_price.pack(side="left")
            button_replace.pack(side="left")
            frame_up.pack(side="top", fill="x")
            frame_dn.pack(side="top", fill="x")
            change_color(color=disp.title_color, container=order_window)


def handler_orderbook(event, row_position: int) -> None:
    disp.symb_book = var.symbol
    ws = Websockets.connect[var.current_exchange]

    def refresh() -> None:
        book_window.title(var.symbol)
        if disp.symb_book != var.symbol:
            entry_price_ask.delete(0, "end")
            entry_price_ask.insert(
                0,
                Function.format_price(
                    ws,
                    number=ws.ticker[var.symbol]["ask"],
                    symbol=var.symbol,
                ),
            )
            entry_price_bid.delete(0, "end")
            entry_price_bid.insert(
                0,
                Function.format_price(
                    ws,
                    number=ws.ticker[var.symbol]["bid"],
                    symbol=var.symbol,
                ),
            )
            entry_quantity.delete(0, "end")
            entry_quantity.insert(
                0,
                Function.volume(
                    ws, qty=ws.instruments[var.symbol]["lotSize"], symbol=var.symbol
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
            disp.symb_book = var.symbol
        book_window.after(500, refresh)

    def on_closing() -> None:
        disp.book_window_trigger = "off"
        book_window.after_cancel(refresh_var)
        book_window.destroy()

    def callback_sell_limit() -> None:
        if quantity.get() and price_ask.get() and emi_number.get():
            try:
                qnt = abs(
                    int(
                        float(quantity.get())
                        * ws.instruments[var.symbol]["myMultiplier"]
                    )
                )
                price = float(price_ask.get())
                res = "yes"
            except Exception:
                info_display(
                    ws.name,
                    "Fields must be numbers! quantity: int or float, price: float",
                )
                res = "no"
            if res == "yes" and qnt != 0:
                price = Function.round_price(
                    ws, symbol=var.symbol, price=price, rside=-qnt
                )
                if price <= 0:
                    message = "The price must be above zero."
                    info_display(ws.name, message)
                    warning_window(message)
                    return
                if qnt % ws.instruments[var.symbol]["lotSize"] != 0:
                    message = (
                        "The "
                        + str(var.symbol)
                        + " quantity must be multiple to "
                        + str(ws.instruments[var.symbol]["lotSize"])
                    )
                    info_display(ws.name, message)
                    warning_window(message)
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
            info_display(ws.name, "Some of the fields are empty!")

    def callback_buy_limit() -> None:
        if quantity.get() and price_bid.get() and emi_number.get():
            try:
                qnt = abs(
                    int(
                        float(quantity.get())
                        * ws.instruments[var.symbol]["myMultiplier"]
                    )
                )
                price = float(price_bid.get())
                res = "yes"
            except Exception:
                info_display(
                    ws.name,
                    "Fields must be numbers! quantity: int or float, price: float",
                )
                res = "no"
            if res == "yes" and qnt != 0:
                price = Function.round_price(
                    ws, symbol=var.symbol, price=price, rside=qnt
                )
                if price <= 0:
                    message = "The price must be above zero."
                    info_display(ws.name, message)
                    warning_window(message)
                    return
                if qnt % ws.instruments[var.symbol]["lotSize"] != 0:
                    message = (
                        "The "
                        + str(var.symbol)
                        + " quantity must be multiple to "
                        + str(ws.instruments[var.symbol]["lotSize"])
                    )
                    info_display(ws.name, message)
                    warning_window(message)
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
            info_display(ws.name, "Some of the fields are empty!")

    if disp.book_window_trigger == "off" and disp.f9 == "OFF":
        disp.book_window_trigger = "on"
        book_window = tk.Toplevel(disp.root, padx=10, pady=20)
        cx = disp.root.winfo_pointerx()
        cy = disp.root.winfo_pointery()
        book_window.geometry("+{}+{}".format(cx - 200, cy - 250))
        book_window.title(var.symbol)
        book_window.protocol("WM_DELETE_WINDOW", on_closing)
        book_window.attributes("-topmost", 1)
        frame_quantity = tk.Frame(book_window)
        frame_market_ask = tk.Frame(book_window)
        frame_market_bid = tk.Frame(book_window)
        frame_robots = tk.Frame(book_window)
        sell_market = tk.Button(
            book_window, text="Sell Market", command=callback_sell_limit
        )
        buy_market = tk.Button(
            book_window, text="Buy Market", command=callback_buy_limit
        )
        sell_limit = tk.Button(
            book_window, text="Sell Limit", command=callback_sell_limit
        )
        buy_limit = tk.Button(book_window, text="Buy Limit", command=callback_buy_limit)
        quantity = tk.StringVar()
        price_ask = tk.StringVar()
        price_bid = tk.StringVar()
        entry_price_ask = tk.Entry(
            frame_market_ask, width=10, bg="white", textvariable=price_ask
        )
        entry_price_bid = tk.Entry(
            frame_market_bid, width=10, bg="white", textvariable=price_bid
        )
        entry_price_ask.insert(
            0,
            Function.format_price(
                ws,
                number=ws.ticker[var.symbol]["ask"],
                symbol=var.symbol,
            ),
        )
        entry_price_bid.insert(
            0,
            Function.format_price(
                ws,
                number=ws.ticker[var.symbol]["bid"],
                symbol=var.symbol,
            ),
        )
        entry_quantity = tk.Entry(
            frame_quantity, width=6, bg="white", textvariable=quantity
        )
        entry_quantity.insert(
            0,
            Function.volume(
                ws, qty=ws.instruments[var.symbol]["lotSize"], symbol=var.symbol
            ),
        )
        label_ask = tk.Label(frame_market_ask, text="Price:")
        label_bid = tk.Label(frame_market_bid, text="Price:")
        label_quantity = tk.Label(frame_quantity, text="Quantity:")
        sell_market.grid(row=0, column=0, sticky="N" + "S" + "W" + "E", pady=10)
        buy_market.grid(row=0, column=1, sticky="N" + "S" + "W" + "E", pady=10)
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
        frame_robots.grid(
            row=1, column=0, sticky="N" + "S" + "W" + "E", columnspan=2, padx=10, pady=0
        )
        label_robots.pack(side="left")
        option_robots.pack()
        frame_quantity.grid(
            row=2,
            column=0,
            sticky="N" + "S" + "W" + "E",
            columnspan=2,
            padx=10,
            pady=10,
        )
        label_quantity.pack(side="left")
        entry_quantity.pack()
        frame_market_ask.grid(row=3, column=0, sticky="N" + "S" + "W" + "E")
        frame_market_bid.grid(row=3, column=1, sticky="N" + "S" + "W" + "E")
        label_ask.pack(side="left")
        entry_price_ask.pack()
        label_bid.pack(side="left")
        entry_price_bid.pack()
        sell_limit.grid(row=4, column=0, sticky="N" + "S" + "W" + "E", pady=10)
        buy_limit.grid(row=4, column=1, sticky="N" + "S" + "W" + "E", pady=10)
        change_color(color=disp.title_color, container=book_window)
        refresh_var = book_window.after_idle(refresh)


def update_label(
    table: str, column: int, row: int, val: Union[str, int, float]
) -> None:
    if disp.labels_cache[table][row][column] != val:
        disp.labels_cache[table][row][column] = val
        disp.labels[table][row][column]["text"] = val


def format_number(number: float) -> str:
    """
    Rounding a value from 3 to 6 decimal places
    """
    number = 0 if round(number, 7) == 0 else number
    len_int = len(str(int(number)))
    after_dot = max(3, 9 - max(3, len_int))

    return "{:.{num}f}".format(number, num=after_dot)


def gap(val: str, peak: int) -> str:
    """
    Generate spaces for scroll widgets
    """
    res = " " + val
    for _ in range(peak - len(val)):
        res = " " + res

    return res


def warning_window(message: str) -> None:
    def on_closing() -> None:
        warn_window.destroy()

    disp.robots_window_trigger = "on"
    warn_window = tk.Toplevel(pady=5)
    warn_window.geometry("400x150+{}+{}".format(450 + randint(0, 7) * 15, 300))
    warn_window.title("Warning")
    warn_window.protocol("WM_DELETE_WINDOW", on_closing)
    warn_window.attributes("-topmost", 1)
    tex = tk.Text(warn_window, wrap="word")
    tex.insert("insert", message)
    tex.pack(expand=1)


def handler_pos(event, row_position: int) -> None:
    ws = Websockets.connect[var.current_exchange]
    if row_position > len(ws.symbol_list):
        row_position = len(ws.symbol_list)
    var.symbol = ws.symbol_list[row_position - 1]
    mod = Tables.position.mod
    for num in range(len(ws.symbol_list)):
        for column in range(len(var.name_position)):
            if num + mod == row_position:
                disp.labels["position"][num + mod][column]["bg"] = disp.yellow_color
            else:
                if num + mod >= 0:
                    disp.labels["position"][num + mod][column]["bg"] = disp.bg_color


def handler_exchange(event, row_position: int) -> None:
    ws = Websockets.connect[var.current_exchange]
    if row_position > len(var.exchange_list):
        row_position = len(var.exchange_list)
    var.current_exchange = var.exchange_list[row_position - 1]
    for row in enumerate(var.exchange_list):
        for column in range(len(var.name_exchange)):
            if row[0] + 1 == row_position:
                disp.labels["exchange"][row[0] + 1][column]["bg"] = "yellow"
            else:
                if row[0] + 1 > 0:
                    disp.labels["exchange"][row[0] + 1][column]["bg"] = disp.bg_color


def humanFormat(volNow: int) -> str:
    if volNow > 1000000000:
        volNow = "{:.2f}".format(round(volNow / 1000000000, 2)) + "B"
    elif volNow > 1000000:
        volNow = "{:.2f}".format(round(volNow / 1000000, 2)) + "M"
    elif volNow > 1000:
        volNow = "{:.2f}".format(round(volNow / 1000, 2)) + "K"

    return volNow


def find_order(price: float, qty: int, symbol: str) -> int:
    for clOrdID in var.orders:
        if (
            var.orders[clOrdID]["price"] == price
            and var.orders[clOrdID]["symbol"] == symbol
        ):
            qty += var.orders[clOrdID]["leavesQty"]

    return qty


def handler_robots(event, row_position: int) -> None:
    emi = None
    ws = Websockets.connect[var.current_exchange]
    for val in ws.robots:
        if ws.robots[val]["y_position"] == row_position:
            emi = val
            break
    if emi:
        if ws.robots[emi]["STATUS"] not in ["NOT IN LIST", "NOT DEFINED", "RESERVED"]:

            def callback():
                row = ws.robots[val]["y_position"]
                if ws.robots[emi]["STATUS"] == "WORK":
                    ws.robots[emi]["STATUS"] = "OFF"
                    disp.labels["robots"][5][row]["fg"] = "red"
                else:
                    ws.robots[emi]["STATUS"] = "WORK"
                    disp.labels["robots"][5][row]["fg"] = "#212121"
                on_closing()

            def on_closing():
                disp.robots_window_trigger = "off"
                robot_window.destroy()

            if disp.robots_window_trigger == "off":
                disp.robots_window_trigger = "on"
                robot_window = tk.Toplevel(disp.root, padx=30, pady=8)
                cx = disp.root.winfo_pointerx()
                cy = disp.root.winfo_pointery()
                robot_window.geometry("+{}+{}".format(cx - 90, cy - 10))
                robot_window.title("EMI=" + emi)
                robot_window.protocol("WM_DELETE_WINDOW", on_closing)
                robot_window.attributes("-topmost", 1)
                text = emi + " - Disable"
                if ws.robots[emi]["STATUS"] == "OFF":
                    text = emi + " - Enable"
                status = tk.Button(robot_window, text=text, command=callback)
                status.pack()
                change_color(color=disp.title_color, container=robot_window)


def clear_labels_cache():
    # disp.labels["robots"] = []
    disp.labels_cache["robots"] = []
    for values in disp.labels_cache.values():
        for column in values:
            for row in range(len(column)):
                column[row] = ""


def change_color(color: str, container=None) -> None:
    if "notebook" not in str(container):
        container.config(bg=color)
    for child in container.winfo_children():
        if child.winfo_children():
            change_color(color, child)
        elif type(child) is tk.Label:
            child.config(bg=color)
        elif type(child) is tk.Button:
            child.config(bg=color)


def load_labels() -> None:
    ws = Websockets.connect[var.current_exchange]
    Tables.position = GridTable(
        frame=disp.position_frame,
        name="position",
        size=max(5, var.position_rows + 1),
        title=var.name_position,
        column_width = 40, 
        canvas_height=65,
        bind=handler_pos,
        color=disp.bg_color,
        select=True,
    )
    Tables.account = GridTable(
        frame=disp.frame_4row_1_2_3col,
        name="account",
        size=var.account_rows + 1,
        title=var.name_account,
        canvas_height=60,
        color=disp.bg_color,
    )
    Tables.robots = GridTable(
        frame=disp.frame_5row_1_2_3col,
        name="robots",
        size=max(disp.num_robots, len(ws.robots) + 1),
        title=var.name_robots,
        canvas_height=150,
        bind=handler_robots,
        color=disp.title_color,
    )
    Tables.exchange = GridTable(
        frame=disp.frame_3row_1col,
        name="exchange",
        size=2,
        title=var.name_exchange,
        title_on=False,
        color=disp.title_color,
        select=True,
    )
    mod = Tables.robots.mod
    for row, emi in enumerate(ws.robots):
        if ws.robots[emi]["STATUS"] in ["NOT IN LIST", "OFF", "NOT DEFINED"] or (
            ws.robots[emi]["STATUS"] == "RESERVED" and ws.robots[emi]["POS"] != 0
        ):
            disp.labels["robots"][row + mod][6]["fg"] = "red"
        else:
            disp.labels["robots"][row + mod][6]["fg"] = "#212121"
    Tables.orderbook = GridTable(
        frame=disp.orderbook_frame,
        name="orderbook",
        size=disp.num_book,
        title=var.name_book,
        canvas_height=440,
        bind=handler_orderbook,
        color=disp.bg_color,
    )
    num = int(disp.num_book / 2)
    mod = Tables.orderbook.mod
    for row in range(disp.num_book + mod - 1):
        for column in range(len(var.name_book)):
            if row > 0:
                if row <= num and column == 2:
                    disp.labels["orderbook"][row][column]["anchor"] = "w"
                if row > num and column == 0:
                    disp.labels["orderbook"][row][column]["anchor"] = "e"

change_color(color=disp.title_color, container=disp.root)

trades = ListBoxTable(
    frame=disp.frame_trades, title=var.name_trade, size=0, expand=True
)
funding = ListBoxTable(
    frame=disp.frame_funding, title=var.name_funding, size=0, expand=True
)
orders = ListBoxTable(
    frame=disp.frame_orders,
    title=var.name_trade,
    bind=handler_order,
    size=0,
    expand=True,
)



