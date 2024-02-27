import os
import time
import tkinter as tk
from collections import OrderedDict
from datetime import datetime, timedelta
from random import randint
from typing import Union

from api.api import WS
from api.variables import Variables
from bots.variables import Variables as bot
from common.variables import Variables as var
from display.variables import Variables as disp

from api.websockets import Websockets

# from ws.init import Variables as ws


db = var.env["MYSQL_DATABASE"]


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

    def info_display(self, message: str) -> None:
        t = datetime.utcnow()
        disp.text_info.insert(
            "1.0",
            Function.noll(self, val=str(t.hour), length=2)
            + ":"
            + Function.noll(self, val=str(t.minute), length=2)
            + ":"
            + Function.noll(self, val=str(t.second), length=2)
            + "."
            + Function.noll(self, val=str(int(t.microsecond / 1000)), length=3)
            + " "
            + message
            + "\n",
        )
        disp.info_display_counter += 1
        if disp.info_display_counter > 40:
            disp.text_info.delete("41.0", "end")

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
        time_struct = datetime.strptime(row["transactTime"][:-1], "%Y-%m-%dT%H:%M:%S.%f")

        # Trade

        if row["execType"] == "Trade":
            if "clOrdID" in row:
                dot = row["clOrdID"].find(".")
                if dot == -1:  # The transaction was done from the exchange web interface,
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
                        "SYMBOL": row["symbol"][0],
                        "CATEGORY": row["symbol"][1],
                        "EXCHANGE": self.name,
                        "POS": 0,
                        "VOL": 0,
                        "COMMISS": 0,
                        "SUMREAL": 0,
                        "LTIME": time_struct,
                        "PNL": 0,
                        "CAPITAL": None,
                        "SYMBCAT": row["symbol"]
                    }
                    message = "Robot EMI=" + str(emi) + ". Adding to 'robots' with STATUS=" + status
                    Function.info_display(self, message)
                    var.logger.info(message)
            data = Function.read_database(self, execID=row["execID"], user_id=self.user_id)
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
                    "TTIME": row["transactTime"],
                    "SIDE": side,
                    "TRADE_PRICE": row["lastPx"],
                    "QTY": abs(lastQty),
                    "EMI": emi,
                }
                Function.trades_display(self, message)
                Function.orders_processing(self, row=row, info=info)

        # Funding

        elif row["execType"] == "Funding":
            message = {
                "SYMBOL": row["symbol"],
                "TTIME": row["transactTime"],
                "PRICE": row["price"],
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
            if "clOrdID" not in row:  # The order was placed from the exchange web interface
                var.last_order += 1
                clOrdID = str(var.last_order) + "." + row["symbol"]
                var.orders[clOrdID] = {
                    "leavesQty": row["leavesQty"],
                    "price": row["price"],
                    "symbol": row["symbol"][0],
                    "category": row["symbol"][1],
                    "exchange": self.name,
                    "transactTime": row["transactTime"],
                    "side": row["side"],
                    "emi": row["symbol"],
                    "orderID": row["orderID"],
                    "symbcat": row["symbol"],
                }
                info = "Outside placement: "
            else:
                info = ""
            Function.orders_processing(self, row=row, info=info)
        elif row["execType"] == "Canceled":
            Function.orders_processing(self, row=row)
        elif row["execType"] == "Replaced":
            Function.orders_processing(self, row=row)


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
                del var.orders[clOrdID]
        elif row["leavesQty"] == 0:
            info_p = row["lastPx"]
            info_q = row["lastQty"]
            if clOrdID in var.orders:
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
                        "symbol": row["symbol"][0],
                        "category": row["symbol"][1],
                        "exchange": self.name,
                        "transactTime": str(datetime.utcnow()),
                        "side": row["side"],
                        "emi": _emi,
                        "orderID": row["orderID"],
                        "symbcat": row["symbol"],
                    }
                info_p = price
                info_q = row["orderQty"]
            elif row["execType"] == "Trade":
                info_p = row["lastPx"]
                info_q = row["lastQty"]
            elif row["execType"] == "Replaced":
                var.orders[clOrdID]["leavesQty"] = row["leavesQty"]
                var.orders[clOrdID]["price"] = row["price"]
                var.orders[clOrdID]["transactTime"] = datetime.utcnow()
                var.orders[clOrdID]["orderID"] = row["orderID"]
                info_p = price
                info_q = row["leavesQty"]
            if (
                clOrdID in var.orders
            ):  # var.orders might be empty if we are here from trading_history()
                var.orders[clOrdID]["leavesQty"] = row["leavesQty"]
                var.orders[clOrdID]["price"] = price
        info_q = Function.volume(self, qty=info_q, symbol=row["symbol"])
        info_p = Function.format_price(self, number=info_p, symbol=row["symbol"])
        Function.info_display(
            self, 
            info
            + row["execType"]
            + " "
            + row["side"]
            + ": "
            + clOrdID
            + " price="
            + str(info_p)
            + " qty="
            + info_q
        )
        var.logger.info(
            info + row["execType"] + " %s: orderID=%s clOrdID=%s price=%s qty=%s",
            row["side"],
            row["orderID"],
            clOrdID,
            str(info_p),
            info_q,
        )
        Function.orders_display(self, clOrdID=clOrdID)

    def trades_display(self, value: dict) -> None:
        """
        Update trades widget
        """
        t = str(value["TTIME"])
        time = t[2:4] + t[5:7] + t[8:10] + " " + t[11:19]
        disp.text_trades.insert(
            "2.0",
            time
            + gap(val=str(value["SYMBOL"]), peak=8)
            + gap(
                val=Function.format_price(
                    self, 
                    number=value["TRADE_PRICE"],
                    symbol=value["SYMBOL"],
                ),
                peak=7,
            )
            + gap(val="(" + str(value["EMI"]) + ")", peak=9)
            + " "
            + Function.volume(self, qty=value["QTY"], symbol=value["SYMBOL"])
            + "\n",
        )
        if value["SIDE"] == 1:
            name = "red"
            disp.text_trades.tag_add(name, "2.0", "2.60")
            disp.text_trades.tag_config(name, foreground="red")
        elif value["SIDE"] == 0:
            name = "green"
            disp.text_trades.tag_add(name, "2.0", "2.60")
            disp.text_trades.tag_config(name, foreground="forest green")
        disp.trades_display_counter += 1
        if disp.trades_display_counter > 150:
            disp.text_trades.delete("151.0", "end")

    def funding_display(self, value: dict) -> None:
        """
        Update funding widgwt
        """
        space = ""
        if value["COMMISS"] > 0:
            space = " "
        t = str(value["TTIME"])
        time = t[2:4] + t[5:7] + t[8:10] + " " + t[11:16]
        disp.text_funding.insert(
            "2.0",
            time
            + gap(val=str(value["SYMBOL"]), peak=8)
            + gap(val=str(float(value["PRICE"])), peak=8)
            + gap(val=space + "{:.7f}".format(value["COMMISS"]), peak=10)
            + gap(val="(" + str(value["EMI"]) + ")", peak=9)
            + " "
            + Function.volume(self, qty=value["QTY"], symbol=value["SYMBOL"])
            + "\n",
        )
        disp.funding_display_counter += 1
        if disp.funding_display_counter > 120:
            disp.text_funding.delete("121.0", "end")

    def orders_display(self, clOrdID: str) -> None:
        """
        Update Orders widget
        """
        if clOrdID in var.orders_dict:
            myNum = 0
            for i, myClOrd in enumerate(var.orders_dict):
                if myClOrd == clOrdID:
                    myNum = i
            ordDictPos = abs(myNum + 1 - len(var.orders_dict)) + 1
            disp.text_orders.delete(str(ordDictPos + 1) + ".0", str(ordDictPos + 2) + ".0")
            del var.orders_dict[clOrdID]
        if clOrdID in var.orders:
            emi = var.orders[clOrdID]["emi"]
            var.orders_dict[clOrdID] = {
                "num": disp.orders_dict_value,
                "emi": emi,
            }
            t = str(var.orders[clOrdID]["transactTime"])
            time = t[2:4] + t[5:7] + t[8:10] + " " + t[11:23]
            text_insert = (
                time
                + gap(val=var.orders[clOrdID]["symbol"], peak=8)
                + gap(
                    val=Function.format_price(
                        self,
                        number=var.orders[clOrdID]["price"],
                        symbol=var.orders[clOrdID]["symbol"],
                    ),
                    peak=9,
                )
                + gap(val="(" + var.orders[clOrdID]["emi"] + ")", peak=11)
                + " "
                + Function.volume(
                    self,
                    qty=var.orders[clOrdID]["leavesQty"], symbol=self.robots[emi]["SYMBOL"]
                )
                + "\n"
            )
            disp.text_orders.insert("2.0", text_insert)
            found_name = 0
            if var.orders[clOrdID]["side"] == "Sell":
                name = "red" + str(disp.orders_dict_value)
                # in order to prevent memory leak we use this construction for
                # tag_bind, that activates only once for every string by number
                # and color
                for tag in disp.text_orders.tag_names():
                    if tag == name:
                        found_name = 1
                if found_name == 0:
                    disp.text_orders.tag_bind(
                        name,
                        "<Button-1>",
                        lambda event, y=disp.orders_dict_value: handler_order(event, y),
                    )
                disp.text_orders.tag_add(name, "2.0", "2.60")
                disp.text_orders.tag_config(name, foreground="red")
            elif var.orders[clOrdID]["side"] == "Buy":
                name = "green" + str(disp.orders_dict_value)
                # in order to prevent memory leak we use this construction for
                # tag_bind, that activates only once for every string by number
                # and color
                for tag in disp.text_orders.tag_names():
                    if tag == name:
                        found_name = 1
                if found_name == 0:
                    disp.text_orders.tag_bind(
                        name,
                        "<Button-1>",
                        lambda event, y=disp.orders_dict_value: handler_order(event, y),
                    )
                disp.text_orders.tag_add(name, "2.0", "2.60")
                disp.text_orders.tag_config(name, foreground="forest green")
            disp.orders_dict_value += 1

    def volume(self, qty: int, symbol: str) -> str:
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
                            "date": (utc.year - 2000) * 10000 + utc.month * 100 + utc.day,
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


def del_order(clOrdID: str) -> int:
    """
    Del_order() function cancels orders
    """
    mes = "Deleting orderID=" + var.orders[clOrdID]["orderID"] + " clOrdID=" + clOrdID
    var.logger.info(mes)
    ws.bitmex.remove_order(orderID=var.orders[clOrdID]["orderID"])

    return ws.bitmex.logNumFatal


def put_order(
    clOrdID: str,
    price: float,
    qty: int,
) -> str:
    """
    Replace orders
    """
    info_p = format_price(number=price, symbol=var.orders[clOrdID]["symbol"])
    var.logger.info(
        "Putting orderID="
        + var.orders[clOrdID]["orderID"]
        + " clOrdID="
        + clOrdID
        + " price="
        + info_p
        + " qty="
        + str(qty)
    )
    if price != var.orders[clOrdID]["price"]:  # the price alters
        ws.bitmex.replace_limit(
            quantity=qty,
            price=price,
            orderID=var.orders[clOrdID]["orderID"],
            symbol=var.orders[clOrdID]["symbol"],
        )

    return clOrdID


def post_order(
    symbol: str,
    emi: str,
    side: str,
    price: float,
    qty: int,
) -> str:
    """
    This function sends a new order
    """
    info_p = format_price(number=price, symbol=symbol)
    var.logger.info("Posting side=" + side + " price=" + info_p + " qty=" + str(qty))
    clOrdID = ""
    if side == "Sell":
        qty = -qty
    var.last_order += 1
    clOrdID = str(var.last_order) + "." + emi
    ws.bitmex.place_limit(quantity=qty, price=price, clOrdID=clOrdID, symbol=symbol)

    return clOrdID


def ticksize_rounding(price: float, ticksize: float) -> float:
    """
    Rounds the price depending on the tickSize value
    """
    arg = 1 / ticksize
    res = round(price * arg, 0) / arg

    return res


def refresh_on_screen(utc: datetime) -> None:
    """
    Refresh information on screen
    """
    # Only to embolden MySQL in order to avoid 'MySQL server has gone away' error
    if utc.hour != var.refresh_hour:
        var.cursor_mysql.execute("select count(*) from " + db + ".robots")
        var.cursor_mysql.fetchall()
        var.refresh_hour = utc.hour
        var.logger.info("Emboldening MySQL")

    disp.label_time["text"] = "(" + str(var.connect_count) + ")  " + time.ctime()
    disp.label_f9["text"] = str(disp.f9)
    if disp.f9 == "ON":
        disp.label_f9.config(bg="green3")
    else:
        disp.label_f9.config(bg="orange red")
    if ws.bitmex.logNumFatal == 0:
        if utc > var.message_time + timedelta(seconds=10):
            if ws.bitmex.message_counter == var.message_point:
                info_display("No data within 10 sec")
                disp.label_online["text"] = "NO DATA"
                disp.label_online.config(bg="yellow2")
                ws.bitmex.urgent_announcement()
            var.message_time = utc
            var.message_point = ws.bitmex.message_counter
    if ws.bitmex.message_counter != var.message_point:
        disp.label_online["text"] = "ONLINE"
        disp.label_online.config(bg="green3")
    if ws.bitmex.logNumFatal != 0:
        disp.label_online["text"] = "error " + str(ws.bitmex.logNumFatal)
        disp.label_online.config(bg="orange red")
    refresh_tables()


def handler_order(event, order_number: int) -> None:
    for clOrdID in var.orders_dict:
        if var.orders_dict[clOrdID]["num"] == order_number:
            break

    def on_closing() -> None:
        disp.order_window_trigger = "off"
        order_window.destroy()

    def delete() -> None:
        try:
            var.orders[clOrdID]
        except KeyError:
            mes = "Order " + clOrdID + " does not exist!"
            info_display(mes)
            var.logger.info(mes)
            return
        if ws.bitmex.logNumFatal == 0:
            del_order(clOrdID=clOrdID)
        else:
            info_display("The operation failed. Websocket closed!")
        on_closing()

    def replace() -> None:
        for clOrdID in var.orders_dict:
            if var.orders_dict[clOrdID]["num"] == order_number:
                break
        try:
            var.orders[clOrdID]
        except KeyError:
            mes = "Order " + clOrdID + " does not exist!"
            info_display(mes)
            var.logger.info(mes)
            return
        try:
            float(price_replace.get())
        except KeyError:
            info_display("Price must be numeric!")
            return
        if ws.bitmex.logNumFatal == 0:
            roundSide = var.orders[clOrdID]["leavesQty"]
            if var.orders[clOrdID]["side"] == "Sell":
                roundSide = -roundSide
            price = round_price(
                symbol=var.orders[clOrdID]["symbol"],
                price=float(price_replace.get()),
                rside=roundSide,
            )
            if price == var.orders[clOrdID]["price"]:
                info_display("Price is the same but must be different!")
                return
            clOrdID = put_order(
                clOrdID=clOrdID,
                price=price,
                qty=var.orders[clOrdID]["leavesQty"],
            )
        else:
            info_display("The operation failed. Websocket closed!")
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
            + str(order_number)
            + "\nsymbol\t"
            + var.orders[clOrdID]["symbol"]
            + "\nside\t"
            + var.orders[clOrdID]["side"]
            + "\nclOrdID\t"
            + clOrdID
            + "\nprice\t"
            + format_price(
                number=var.orders[clOrdID]["price"],
                symbol=var.orders[clOrdID]["symbol"],
            )
            + "\nquantity\t"
            + str(var.orders[clOrdID]["leavesQty"])
        )
        label_price = tk.Label(frame_dn)
        label_price["text"] = "Price "
        label1.pack(side="left")
        button = tk.Button(frame_dn, text="Delete order", command=delete)
        price_replace = tk.StringVar()
        entry_price = tk.Entry(
            frame_dn, width=10, bg="white", textvariable=price_replace
        )
        button_replace = tk.Button(frame_dn, text="Replace", command=replace)
        button.pack(side="right")
        label_price.pack(side="left")
        entry_price.pack(side="left")
        button_replace.pack(side="left")
        frame_up.pack(side="top", fill="x")
        frame_dn.pack(side="top", fill="x")
        change_color(color=disp.title_color, container=order_window)


def handler_book(row_position: int) -> None:
    disp.symb_book = var.symbol

    def refresh() -> None:
        book_window.title(var.symbol)
        if disp.symb_book != var.symbol:
            entry_price_ask.delete(0, "end")
            entry_price_ask.insert(
                0,
                format_price(
                    number=var.ticker[var.symbol]["ask"],
                    symbol=var.symbol,
                ),
            )
            entry_price_bid.delete(0, "end")
            entry_price_bid.insert(
                0,
                format_price(
                    number=var.ticker[var.symbol]["bid"],
                    symbol=var.symbol,
                ),
            )
            entry_quantity.delete(0, "end")
            entry_quantity.insert(
                0, volume(qty=var.instruments[var.symbol]["lotSize"], symbol=var.symbol)
            )
            option_robots["menu"].delete(0, "end")
            options = list()
            for emi in bot.robots:
                if (
                    bot.robots[emi]["SYMBOL"] in var.symbol_list
                    and bot.robots[emi]["SYMBOL"] == var.symbol
                ):
                    options.append(bot.robots[emi]["EMI"])
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
                        * var.instruments[var.symbol]["myMultiplier"]
                    )
                )
                price = float(price_ask.get())
                res = "yes"
            except Exception:
                info_display(
                    "Fields must be numbers! quantity: int or float, price: float"
                )
                res = "no"
            if res == "yes" and qnt != 0:
                price = round_price(symbol=var.symbol, price=price, rside=-qnt)
                if price <= 0:
                    mes = "The price must be above zero."
                    info_display(mes)
                    warning_window(mes)
                    return
                if qnt % var.instruments[var.symbol]["lotSize"] != 0:
                    mes = (
                        "The "
                        + str(var.symbol)
                        + " quantity must be multiple to "
                        + str(var.instruments[var.symbol]["lotSize"])
                    )
                    info_display(mes)
                    warning_window(mes)
                    return
                post_order(
                    symbol=var.symbol,
                    emi=emi_number.get(),
                    side="Sell",
                    price=price,
                    qty=qnt,
                )
        else:
            info_display("Some of the fields are empty!")

    def callback_buy_limit() -> None:
        if quantity.get() and price_bid.get() and emi_number.get():
            try:
                qnt = abs(
                    int(
                        float(quantity.get())
                        * var.instruments[var.symbol]["myMultiplier"]
                    )
                )
                price = float(price_bid.get())
                res = "yes"
            except Exception:
                info_display(
                    "Fields must be numbers! quantity: int or float, price: float"
                )
                res = "no"
            if res == "yes" and qnt != 0:
                price = round_price(symbol=var.symbol, price=price, rside=qnt)
                if price <= 0:
                    mes = "The price must be above zero."
                    info_display(mes)
                    warning_window(mes)
                    return
                if qnt % var.instruments[var.symbol]["lotSize"] != 0:
                    mes = (
                        "The "
                        + str(var.symbol)
                        + " quantity must be multiple to "
                        + str(var.instruments[var.symbol]["lotSize"])
                    )
                    info_display(mes)
                    warning_window(mes)
                    return
                post_order(
                    symbol=var.symbol,
                    emi=emi_number.get(),
                    side="Buy",
                    price=price,
                    qty=qnt,
                )
        else:
            info_display("Some of the fields are empty!")

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
            format_price(
                number=var.ticker[var.symbol]["ask"],
                symbol=var.symbol,
            ),
        )
        entry_price_bid.insert(
            0,
            format_price(
                number=var.ticker[var.symbol]["bid"],
                symbol=var.symbol,
            ),
        )
        entry_quantity = tk.Entry(
            frame_quantity, width=6, bg="white", textvariable=quantity
        )
        entry_quantity.insert(
            0, volume(qty=var.instruments[var.symbol]["lotSize"], symbol=var.symbol)
        )
        label_ask = tk.Label(frame_market_ask, text="Price:")
        label_bid = tk.Label(frame_market_bid, text="Price:")
        label_quantity = tk.Label(frame_quantity, text="Quantity:")
        sell_market.grid(row=0, column=0, sticky="N" + "S" + "W" + "E", pady=10)
        buy_market.grid(row=0, column=1, sticky="N" + "S" + "W" + "E", pady=10)
        label_robots = tk.Label(frame_robots, text="EMI:")
        emi_number = tk.StringVar()
        options = list()
        for emi in bot.robots:
            if (
                bot.robots[emi]["SYMBOL"] in var.symbol_list
                and bot.robots[emi]["SYMBOL"] == var.symbol
            ):
                options.append(bot.robots[emi]["EMI"])
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


def close_price(symbol: str, pos: int) -> float:
    if symbol in var.ticker:
        close = var.ticker[symbol]["bid"] if pos > 0 else var.ticker[symbol]["ask"]
    else:
        close = (
            var.instruments[symbol]["bidPrice"]
            if pos > 0
            else var.instruments[symbol]["askPrice"]
        )

    return close


def update_label(
    table: str, column: int, row: int, val: Union[str, int, float]
) -> None:
    if disp.labels_cache[table][column][row] != val:
        disp.labels_cache[table][column][row] = val
        disp.labels[table][column][row]["text"] = val


def refresh_tables() -> None:
    """
    Update tkinter labels in the tables
    """

    # Get funds

    funds = ws.bitmex.get_funds()
    for cur in var.accounts:
        for fund in funds:
            if cur == fund["currency"]:
                var.accounts[cur]["ACCOUNT"] = fund["account"]
                var.accounts[cur]["MARGINBAL"] = (
                    float(fund["marginBalance"]) / var.currency_divisor[cur]
                )
                var.accounts[cur]["AVAILABLE"] = (
                    float(fund["availableMargin"]) / var.currency_divisor[cur]
                )
                var.accounts[cur]["LEVERAGE"] = fund["marginLeverage"]
                var.accounts[cur]["RESULT"] = var.accounts[cur]["SUMREAL"]
                break
        else:
            mes = "Currency " + str(cur) + " not found."
            var.logger.error(mes)
            exit(1)

    # Refresh Positions table

    for num, symbol in enumerate(var.symbol_list):
        var.positions[symbol]["STATE"] = var.instruments[symbol]["state"]
        var.positions[symbol]["VOL24h"] = var.instruments[symbol]["volume24h"]
        var.positions[symbol]["FUND"] = round(
            var.instruments[symbol]["fundingRate"] * 100, 6
        )
        update_label(table="position", column=0, row=num + 1, val=symbol)
        if var.positions[symbol]["POS"]:
            pos = volume(qty=var.positions[symbol]["POS"], symbol=symbol)
        else:
            pos = "0"
        update_label(table="position", column=1, row=num + 1, val=pos)
        update_label(
            table="position",
            column=2,
            row=num + 1,
            val=(
                format_price(
                    number=var.positions[symbol]["ENTRY"],
                    symbol=symbol,
                )
                if var.positions[symbol]["ENTRY"] is not None
                else 0
            ),
        )
        update_label(
            table="position",
            column=3,
            row=num + 1,
            val=(
                var.positions[symbol]["PNL"]
                if var.positions[symbol]["PNL"] is not None
                else 0
            ),
        )
        update_label(
            table="position",
            column=4,
            row=num + 1,
            val=(
                str(var.positions[symbol]["MCALL"]).replace("100000000", "inf")
                if var.positions[symbol]["MCALL"] is not None
                else 0
            ),
        )
        update_label(
            table="position", column=5, row=num + 1, val=var.positions[symbol]["STATE"]
        )
        update_label(
            table="position",
            column=6,
            row=num + 1,
            val=humanFormat(var.positions[symbol]["VOL24h"]),
        )
        if isinstance(var.instruments[symbol]["expiry"], datetime):
            tm = var.instruments[symbol]["expiry"].strftime("%y%m%d %Hh")
        else:
            tm = var.instruments[symbol]["expiry"]
        update_label(table="position", column=7, row=num + 1, val=tm)
        update_label(
            table="position", column=8, row=num + 1, val=var.positions[symbol]["FUND"]
        )

    # Refresh Orderbook table

    def display_order_book_values(
        val: dict, start: int, end: int, direct: int, side: str
    ) -> None:
        count = 0
        if side == "asks":
            col = 2
            color = "orange red"
        else:
            col = 0
            color = "green2"
        col_qty = abs(col - 2)
        for row in range(start, end, direct):
            vlm = ""
            price = ""
            qty = 0
            if len(val[side]) > count:
                price = format_price(number=val[side][count][0], symbol=var.symbol)
                vlm = volume(qty=val[side][count][1], symbol=var.symbol)
                if var.orders:
                    qty = volume(
                        qty=find_order(float(price), qty, symbol=var.symbol),
                        symbol=var.symbol,
                    )
            if str(qty) != "0":
                update_label(table="orderbook", column=col_qty, row=row, val=qty)
                disp.labels["orderbook"][col_qty][row]["bg"] = color
            else:
                update_label(table="orderbook", column=col_qty, row=row, val="")
                disp.labels["orderbook"][col_qty][row]["bg"] = disp.bg_color
            update_label(table="orderbook", column=col, row=row, val=vlm)
            update_label(table="orderbook", column=1, row=row, val=price)
            count += 1

    num = int(disp.num_book / 2)
    if var.order_book_depth == "quote":
        if var.ticker[var.symbol]["askSize"]:
            update_label(
                table="orderbook",
                column=2,
                row=num,
                val=volume(qty=var.ticker[var.symbol]["askSize"], symbol=var.symbol),
            )
        else:
            update_label(table="orderbook", column=2, row=num, val="")
        if var.ticker[var.symbol]["bidSize"]:
            update_label(
                table="orderbook",
                column=0,
                row=num + 1,
                val=volume(qty=var.ticker[var.symbol]["bidSize"], symbol=var.symbol),
            )
        else:
            update_label(table="orderbook", column=0, row=num + 1, val="")
        disp.labels["orderbook"][0][num + 1]["fg"] = "black"
        first_price_sell = (
            var.ticker[var.symbol]["ask"]
            + (num - 1) * var.instruments[var.symbol]["tickSize"]
        )
        first_price_buy = var.ticker[var.symbol]["bid"]
        for row in range(disp.num_book - 1):
            if row < num:
                price = round(
                    first_price_sell - row * var.instruments[var.symbol]["tickSize"],
                    disp.price_rounding[var.symbol],
                )
                qty = 0
                if var.orders:
                    qty = volume(
                        qty=find_order(float(price), qty, symbol=var.symbol),
                        symbol=var.symbol,
                    )
                if var.ticker[var.symbol]["ask"]:
                    price = format_price(number=price, symbol=var.symbol)
                else:
                    price = ""
                update_label(table="orderbook", column=1, row=row + 1, val=price)
                if str(qty) != "0":
                    update_label(table="orderbook", column=0, row=row + 1, val=qty)
                    disp.label_book[0][row + 1]["bg"] = "orange red"
                else:
                    update_label(table="orderbook", column=0, row=row + 1, val="")
                    disp.labels["orderbook"][0][row + 1]["bg"] = disp.bg_color
            else:
                price = round(
                    first_price_buy
                    - (row - num) * var.instruments[var.symbol]["tickSize"],
                    disp.price_rounding[var.symbol],
                )
                qty = 0
                if var.orders:
                    qty = volume(
                        qty=find_order(price, qty, symbol=var.symbol), symbol=var.symbol
                    )
                if price > 0:
                    price = format_price(number=price, symbol=var.symbol)
                else:
                    price = ""
                update_label(table="orderbook", column=1, row=row + 1, val=price)
                if str(qty) != "0":
                    update_label(table="orderbook", column=2, row=row + 1, val=qty)
                    disp.labels["orderbook"][2][row + 1]["bg"] = "green2"
                else:
                    update_label(table="orderbook", column=2, row=row + 1, val="")
                    disp.labels["orderbook"][2][row + 1]["bg"] = disp.bg_color
    else:
        val = ws.bitmex.market_depth10()[(("symbol", var.symbol),)]
        display_order_book_values(
            val=val, start=num + 1, end=disp.num_book, direct=1, side="bids"
        )
        display_order_book_values(val=val, start=num, end=0, direct=-1, side="asks")

    # Update Robots table

    for num, emi in enumerate(bot.robots):
        symbol = bot.robots[emi]["SYMBOL"]
        price = close_price(symbol=symbol, pos=bot.robots[emi]["POS"])
        if price:
            calc = calculate(
                symbol=symbol,
                price=price,
                qty=-float(bot.robots[emi]["POS"]),
                rate=0,
                fund=1,
            )
            bot.robots[emi]["PNL"] = (
                bot.robots[emi]["SUMREAL"]
                + calc["sumreal"]
                - bot.robots[emi]["COMMISS"]
            )
        symbol = bot.robots[emi]["SYMBOL"]
        update_label(table="robots", column=0, row=num + 1, val=emi)
        update_label(table="robots", column=1, row=num + 1, val=symbol)
        update_label(
            table="robots",
            column=2,
            row=num + 1,
            val=var.instruments[symbol]["settlCurrency"],
        )
        update_label(
            table="robots", column=3, row=num + 1, val=bot.robots[emi]["TIMEFR"]
        )
        update_label(
            table="robots", column=4, row=num + 1, val=bot.robots[emi]["CAPITAL"]
        )
        update_label(
            table="robots", column=5, row=num + 1, val=bot.robots[emi]["STATUS"]
        )
        update_label(
            table="robots",
            column=6,
            row=num + 1,
            val=humanFormat(bot.robots[emi]["VOL"]),
        )
        update_label(
            table="robots",
            column=7,
            row=num + 1,
            val="{:.8f}".format(bot.robots[emi]["PNL"]),
        )
        val = volume(
            qty=bot.robots[emi]["POS"],
            symbol=symbol,
        )
        if disp.labels_cache["robots"][8][num + 1] != val:
            if bot.robots[emi]["STATUS"] == "RESERVED":
                if bot.robots[emi]["POS"] != 0:
                    disp.labels["robots"][5][num + 1]["fg"] = "red"
                else:
                    disp.labels["robots"][5][num + 1]["fg"] = "#212121"
        update_label(
            table="robots",
            column=8,
            row=num + 1,
            val=val,
        )
        bot.robots[emi]["y_position"] = num + 1

    # Refresh Account table

    for symbol, position in var.positions.items():
        if position["POS"] != 0:
            calc = calculate(
                symbol=symbol,
                price=close_price(symbol=symbol, pos=position["POS"]),
                qty=-position["POS"],
                rate=0,
                fund=1,
            )
            settlCurrency = var.instruments[symbol]["settlCurrency"]
            if settlCurrency in var.accounts:
                var.accounts[settlCurrency]["RESULT"] += calc["sumreal"]
            else:
                var.logger.error(
                    settlCurrency
                    + " not found. See the CURRENCIES variable in the .env file."
                )
                exit(1)
    for num, cur in enumerate(var.currencies):
        update_label(table="account", column=0, row=num + 1, val=cur)
        update_label(
            table="account",
            column=1,
            row=num + 1,
            val=format_number(number=var.accounts[cur]["MARGINBAL"]),
        )
        update_label(
            table="account",
            column=2,
            row=num + 1,
            val=format_number(number=var.accounts[cur]["AVAILABLE"]),
        )
        update_label(
            table="account",
            column=3,
            row=num + 1,
            val="{:.3f}".format(var.accounts[cur]["LEVERAGE"]),
        )
        update_label(
            table="account",
            column=4,
            row=num + 1,
            val=format_number(number=var.accounts[cur]["RESULT"]),
        )
        update_label(
            table="account",
            column=5,
            row=num + 1,
            val=format_number(number=-var.accounts[cur]["COMMISS"]),
        )
        update_label(
            table="account",
            column=6,
            row=num + 1,
            val=format_number(number=-var.accounts[cur]["FUNDING"]),
        )
        number = (
            var.accounts[cur]["MARGINBAL"]
            - var.accounts[cur]["RESULT"]
            + var.accounts[cur]["COMMISS"]
            + var.accounts[cur]["FUNDING"]
        )
        update_label(
            table="account", column=7, row=num + 1, val=format_number(number=number)
        )


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


def round_price(symbol: str, price: float, rside: int) -> float:
    """
    Round_price() returns rounded price: buy price goes down, sell price
    goes up according to 'tickSize'
    """
    coeff = 1 / var.instruments[symbol]["tickSize"]
    result = int(coeff * price) / coeff
    if rside < 0 and result < price:
        result += var.instruments[symbol]["tickSize"]

    return result


def handler_pos(event, row_position: int) -> None:
    if row_position > len(var.symbol_list):
        row_position = len(var.symbol_list)
    var.symbol = var.symbol_list[row_position - 1]
    for row in enumerate(var.symbol_list):
        for column in enumerate(disp.labels["position"]):
            if row[0] + 1 == row_position:
                disp.labels["position"][column[0]][row[0] + 1]["bg"] = "yellow"
            else:
                if row[0] + 1 > 0:
                    disp.labels["position"][column[0]][row[0] + 1]["bg"] = disp.bg_color


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
    for ws in Websockets.connect.values():
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


def change_color(color: str, container=None) -> None:
    container.config(bg=color)
    for child in container.winfo_children():
        if child.winfo_children():
            change_color(color, child)
        elif type(child) is tk.Label:
            child.config(bg=color)
        elif type(child) is tk.Button:
            child.config(bg=color)