import logging
from collections import OrderedDict
from datetime import datetime

import pymysql
import pymysql.cursors

import services as service
from api.api import WS, Markets
from api.init import Variables

# from api.websockets import Websockets
from common.variables import Variables as var
from display.functions import info_display
from display.variables import Variables as disp
from functions import Function, funding, orders, trades

db = var.env["MYSQL_DATABASE"]


class Init(WS, Variables):
    def clear_params(self) -> None:
        self.connect_count += 1
        for emi, values in self.robots.items():
            self.robot_status[emi] = values["STATUS"]
        self.robots = OrderedDict()
        Function.rounding(self)
        self.frames = dict()

    def load_trading_history(self: Markets) -> None:
        """
        Load trading history (if any)
        """
        tm = datetime.now()
        with open("history.ini", "r") as f:
            lst = list(f)
        rows = list()
        last_history_time = ""
        for row in lst:
            row = row.replace("\n", "")
            res = row.split()
            if res:
                if res[0] == self.name:
                    time = " ".join(res[1:])
                    last_history_time = datetime.strptime(time, "%Y-%m-%d %H:%M:%S")
                else:
                    rows.append(row)
        if not last_history_time:
            message = self.name + " was not found in the history.ini file."
            var.logger.error(message)
            raise Exception(message)
        if last_history_time > tm:
            message = (
                "history.ini error. The time in the history.ini file is "
                + "greater than the current time."
            )
            var.logger.error(message)
            raise Exception(message)
        count_val = 500
        history = WS.trading_history(self, histCount=count_val, time=last_history_time)
        if history == "error":
            var.logger.error("history.ini error")
            exit(1)
        tmp = datetime(2000, 1, 1)
        """
        A premature exit from the loop is possible due to a small count_val
        value. This will happen in the case of a large number of trades or
        funding with the same time greater than or equal to count_val, when
        the first and last line will have the same transactTime accurate to
        the millisecond.
        """
        while history:
            for row in history:
                data = Function.read_database(
                    self, execID=row["execID"], user_id=self.user_id
                )
                if not data:
                    Function.transaction(self, row=row, info=" History ")
            last_history_time = history[-1]["transactTime"]
            history = WS.trading_history(
                self, histCount=count_val, time=last_history_time
            )
            if last_history_time == tmp:
                break
            tmp = last_history_time
        rows.append(self.name + " " + str(last_history_time)[:19])
        if self.logNumFatal == 0:
            with open("history.ini", "w") as f:
                for row in rows:
                    f.write(row + "\n")

    def account_balances(self: Markets) -> None:
        """
        Calculates the account by currency according to data from the MySQL
        'coins' table.
        """
        sql = (
            "select SYMBOL, CATEGORY from "
            + db
            + ".coins where ACCOUNT=%s and MARKET=%s group by SYMBOL, CATEGORY"
        )
        var.cursor_mysql.execute(sql, (self.user_id, self.name))
        data = var.cursor_mysql.fetchall()
        symbols = list(map(lambda x: (x["SYMBOL"], x["CATEGORY"], self.name), data))
        for symbol in symbols:
            Function.add_symbol(self, symbol=symbol)
        if not symbols:
            symbols = [("MUST_NOT_BE_EMPTY", "MUST_NOT_BE_EMPTY")]
        for currency in self.currencies:
            union = ""
            sql = (
                "select sum(commiss) commiss, sum(sumreal) sumreal, "
                + "sum(funding) funding from ("
            )
            for symbol in symbols:
                sql += (
                    union
                    + "select IFNULL(sum(COMMISS),0.0) commiss, "
                    + "IFNULL(sum(SUMREAL),0.0) sumreal, IFNULL((select "
                    + "sum(COMMISS) from "
                    + db
                    + ".coins where SIDE < 0 and ACCOUNT = "
                    + str(self.user_id)
                    + " and MARKET = '"
                    + self.name
                    + "' and CURRENCY = '"
                    + currency
                    + "' and SYMBOL = '"
                    + symbol[0]
                    + "' and CATEGORY = '"
                    + symbol[1]
                    + "'),0.0) funding from "
                    + db
                    + ".coins where SIDE >= 0 and ACCOUNT = "
                    + str(self.user_id)
                    + " and MARKET = '"
                    + self.name
                    + "' and CURRENCY = '"
                    + currency
                    + "' and SYMBOL = '"
                    + symbol[0]
                    + "' and CATEGORY = '"
                    + symbol[1]
                    + "'"
                )
                union = "union "
            sql += ") T"
            var.cursor_mysql.execute(sql)
            data = var.cursor_mysql.fetchall()
            settlCurrency = (currency, self.name)
            self.Account[settlCurrency].commission = float(data[0]["commiss"])
            self.Account[settlCurrency].funding = float(data[0]["funding"])
            self.Account[settlCurrency].sumreal = float(data[0]["sumreal"])
            self.Account[settlCurrency].result = 0

    def load_orders(self: Markets) -> None:
        """
        Load Orders (if any)
        """
        myOrders = WS.open_orders(self)
        copy = var.orders.copy()
        for clOrdID, order in copy.items():
            if order["MARKET"] == self.name:
                del var.orders[clOrdID]
        for val in reversed(myOrders):
            if val["leavesQty"] != 0:
                emi = ".".join(val["symbol"][:2])
                if "clOrdID" not in val:
                    # The order was placed from the exchange interface
                    var.last_order += 1
                    clOrdID = str(var.last_order) + "." + emi
                    info_display(
                        self.name,
                        "Outside placement: price="
                        + str(val["price"])
                        + " side="
                        + val["side"]
                        + ". Assigned clOrdID="
                        + clOrdID,
                    )
                else:
                    clOrdID = val["clOrdID"]
                    s = clOrdID.split(".")
                    emi = ".".join(s[1:3])
                    if emi not in self.robots:
                        self.robots[emi] = {
                            "STATUS": "NOT DEFINED",
                            "TIMEFR": None,
                            "EMI": emi,
                            "SYMBOL": val["symbol"],
                            "CATEGORY": val["symbol"][1],
                            "MARKET": self.name,
                            "POS": 0,
                            "VOL": 0,
                            "COMMISS": 0,
                            "SUMREAL": 0,
                            "LTIME": val["transactTime"],
                            "PNL": 0,
                            "CAPITAL": None,
                        }
                        message = (
                            "Robot EMI="
                            + emi
                            + ". Adding to 'robots' with STATUS='NOT DEFINED'"
                        )
                        info_display(self.name, message)
                        var.logger.info(message)
                var.orders[clOrdID] = {}
                var.orders[clOrdID]["EMI"] = emi
                var.orders[clOrdID]["leavesQty"] = val["leavesQty"]
                var.orders[clOrdID]["transactTime"] = val["transactTime"]
                var.orders[clOrdID]["price"] = val["price"]
                var.orders[clOrdID]["SYMBOL"] = val["symbol"]
                var.orders[clOrdID]["CATEGORY"] = val["symbol"][1]
                var.orders[clOrdID]["MARKET"] = self.name
                var.orders[clOrdID]["SIDE"] = val["side"]
                var.orders[clOrdID]["orderID"] = val["orderID"]
        for clOrdID, order in var.orders.items():
            order["clOrdID"] = clOrdID
        orders.clear_all()
        values = list(var.orders.values())
        values.sort(key=lambda x: x["transactTime"])
        var.orders = OrderedDict()
        for val in reversed(values):
            var.orders[val["clOrdID"]] = val
        for val in list(var.orders.values()):
            if val["MARKET"] == self.name:
                Function.fill_columns(
                    self, func=Function.orders_display, table=orders, val=val
                )

    def load_database(self: Markets) -> None:
        """
        Download the latest trades and funding data from the database (if any)
        """
        sql = (
            "select ID, EMI, SYMBOL, CATEGORY, MARKET, SIDE, QTY, "
            + "PRICE, TTIME, COMMISS from "
            + db
            + ".coins where SIDE = -1 and ACCOUNT = "
            + str(self.user_id)
            + " and MARKET = '"
            + self.name
            + "' "
            + "order by TTIME desc limit "
            + str(disp.table_limit)
        )
        var.cursor_mysql.execute(sql)
        data = var.cursor_mysql.fetchall()
        for val in data:
            val["SYMBOL"] = (val["SYMBOL"], val["CATEGORY"], self.name)
            val["QTY"] = Function.volume(
                Markets[val["MARKET"]], qty=val["QTY"], symbol=val["SYMBOL"]
            )
            Function.fill_columns(
                self, func=Function.funding_display, table=funding, val=val
            )
        sql = (
            "select ID, EMI, SYMBOL, CATEGORY, MARKET, SIDE, QTY,"
            + "TRADE_PRICE, TTIME, COMMISS, SUMREAL from "
            + db
            + ".coins where SIDE <> -1 and ACCOUNT = "
            + str(self.user_id)
            + " and MARKET = '"
            + self.name
            + "' "
            + "order by TTIME desc limit "
            + str(disp.table_limit)
        )
        var.cursor_mysql.execute(sql)
        data = var.cursor_mysql.fetchall()
        for val in data:
            val["SYMBOL"] = (val["SYMBOL"], val["CATEGORY"], self.name)
            val["QTY"] = Function.volume(
                Markets[val["MARKET"]], qty=val["QTY"], symbol=val["SYMBOL"]
            )
            Function.fill_columns(
                self, func=Function.trades_display, table=trades, val=val
            )


def setup_logger():
    logger = logging.getLogger()
    logger.setLevel(logging.INFO)
    handler = logging.FileHandler("logfile.log")
    ch = logging.StreamHandler()
    formatter = logging.Formatter(
        "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )
    ch.setFormatter(formatter)
    handler.setFormatter(formatter)
    logger.addHandler(ch)
    logger.addHandler(handler)
    logger.info("\n\nhello\n")

    return logger


def setup_database_connecion() -> None:
    try:
        var.connect_mysql = pymysql.connect(
            host=var.env["MYSQL_HOST"],
            user=var.env["MYSQL_USER"],
            password=var.env["MYSQL_PASSWORD"],
            database=var.env["MYSQL_DATABASE"],
            charset="utf8mb4",
            cursorclass=pymysql.cursors.DictCursor,
        )
        var.cursor_mysql = var.connect_mysql.cursor()

    except Exception as error:
        var.logger.error(error)
        raise
