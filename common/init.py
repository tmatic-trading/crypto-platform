# import logging
import os
import sqlite3
import threading
from collections import OrderedDict
from datetime import datetime, timezone
from sqlite3 import Error

import services as service
from api.api import WS, Markets
from api.init import Variables
from common.variables import Variables as var
from display.functions import info_display
from display.variables import TreeTable
from display.variables import Variables as disp
from functions import Function

db_sqlite = var.env["SQLITE_DATABASE"]
var.working_directory = os.path.abspath(os.getcwd())


class Init(WS, Variables):
    file_lock = threading.Lock()

    def clear_params(self: Markets) -> None:
        self.connect_count += 1
        for emi, values in self.robots.items():
            self.robot_status[emi] = values["STATUS"]
        self.robots = OrderedDict()
        self.frames = dict()
        self.account_disp = "Acc." + str(self.user_id)

    def save_history_file(self: Markets, time: datetime):
        Init.file_lock.acquire(True)
        with open("history.ini", "r") as f:
            lst = list(f)
        saved = ""
        with open("history.ini", "w") as f:
            for row in lst:
                row = row.replace("\n", "")
                res = row.split()
                if res:
                    if res[0] == self.name:
                        row = res[0] + " " + str(time)[:19]
                        if not saved:
                            f.write(row + "\n")
                        saved = "success"
                    else:
                        f.write(row + "\n")
            if not saved:
                row = self.name + " " + str(time)[:19]
                f.write(row + "\n")
        Init.file_lock.release()

    def load_trading_history(self: Markets) -> None:
        """
        This function receives trading history data through tade_history()
        methods in files called agent.py. Each exchange has its own API
        features, so the methods differ significantly from each other.

        Trade_history() reads data in 500-line chunks, starting from the date
        specified in the history.ini file. If trade_history() returned less
        than 500 rows, then this is a signal that the entire trading history
        has been received and this function ends its work. The history.ini
        file records the time of the last transaction.

        If the row with execID already exists in the database, then it is
        skipped, otherwise it is processed in the transaction() in
        functions.py and then written to the database.

        The data obtained from different exchanges have unified values:

        "symbol": tuple             Symbol name. Example: ("BTCUSDT",
                                    "linear", "Bybit")
        "execID": str               Execution ID
        "orderID": str              Order ID
        "lastPx": float             Execution price
        "leavesQty": float          The remaining qty not executed
        "category": str             Instrument type: spot, linear, inverse,
                                    option, quanto
        "transactTime": datetime    Executed timestamp
        "commission": float         Trading fee rate
        "clOrdID": str              User customized order ID
        "price": float              Order price
        "settlCurrency": tuple      Settle coin. Example: ('USDt', 'Bitmex')
        "lastQty": float            Execution qty
        "market": str               Exchange name
        "execType": str             Executed type: Trade, Funding
        "execFee": float            Executed trading fee
        """
        tm = datetime.now(tz=timezone.utc)
        try:
            with open("history.ini", "r") as f:
                lst = list(f)
        except FileNotFoundError:
            var.logger.warning(
                "The history.ini not found. The history.ini file has been created."
            )
            with open("history.ini", "w"):
                pass
            lst = list()
        last_history_time = ""
        for row in lst:
            row = row.replace("\n", "")
            res = row.split()
            if res:
                if res[0] == self.name:
                    _time = " ".join(res[1:])
                    break
        else:
            _time = "2000-01-01 00:0:00"
            var.logger.warning(
                "No time found for "
                + self.name
                + " from history.ini. Assigned time: "
                + _time
            )
        try:
            last_history_time = datetime.strptime(_time, "%Y-%m-%d %H:%M:%S")
        except ValueError:
            _time = "2000-01-01 00:0:00"
            var.logger.warning(
                "Time format for "
                + self.name
                + " from the history.ini is incorrect. Assigned time: "
                + _time
            )
            last_history_time = datetime.strptime(_time, "%Y-%m-%d %H:%M:%S")
        last_history_time = last_history_time.replace(tzinfo=timezone.utc)
        if last_history_time > tm:
            _time = "2000-01-01 00:0:00"
            var.logger.warning(
                "The time in the history.ini file is greater than the current time. Assigned time: "
                + _time
            )
            last_history_time = datetime.strptime(_time, "%Y-%m-%d %H:%M:%S")
            last_history_time = last_history_time.replace(tzinfo=timezone.utc)
        count_val = 500
        history = WS.trading_history(
            self, histCount=count_val, start_time=last_history_time
        )
        if isinstance(history, list):
            while history:
                for row in history:
                    data = service.select_database(  # read_database
                        "select EXECID from coins where EXECID='%s' and account=%s and market='%s'"
                        % (row["execID"], self.user_id, self.name),
                    )
                    if not data:
                        Function.transaction(self, row=row, info=" History ")
                last_history_time = history[-1]["transactTime"]
                if not self.logNumFatal:
                    Init.save_history_file(self, time=last_history_time)
                if len(history) < count_val:
                    return "success"
                history = WS.trading_history(
                    self, histCount=count_val, start_time=last_history_time
                )
                if not isinstance(history, list):
                    self.logNumFatal = "SETUP"
                    return

    def account_balances(self: Markets) -> None:
        """
        Calculates the final trading results for all currencies that were
        involved. The data is taken from the SQLite table "coins".
        Additionally, accrued funding and paid commissions for the entire
        period are calculated.
        """
        data = service.select_database(
            "select SYMBOL, TICKER, CATEGORY from "
            + "coins where ACCOUNT=%s and MARKET='%s' group by SYMBOL, CATEGORY"
            % (self.user_id, self.name),
        )
        if isinstance(data, list):
            symbols = list(map(lambda x: (x["SYMBOL"], self.name), data))
            for row in data:
                Function.add_symbol(
                    self,
                    symbol=row["SYMBOL"],
                    ticker=row["TICKER"],
                    category=row["CATEGORY"],
                )
            if not symbols:
                symbols = [("MUST_NOT_BE_EMPTY", "MUST_NOT_BE_EMPTY")]
            sql = (
                "select DISTINCT(CURRENCY) from coins where MARKET = '"
                + self.name
                + "' AND ACCOUNT = "
                + str(self.user_id)
            )
            data = service.select_database(sql)
            for cur in data:
                currency = cur["CURRENCY"]
                union = ""
                sql = (
                    "select sum(commiss) commiss, sum(sumreal) sumreal, "
                    + "sum(funding) funding from ("
                )
                for symbol in symbols:
                    instrument = self.Instrument[symbol]
                    sql += (
                        union
                        + "select IFNULL(sum(COMMISS),0.0) commiss, "
                        + "IFNULL(sum(SUMREAL),0.0) sumreal, IFNULL((select "
                        + "sum(COMMISS) from "
                        + "coins where SIDE = 'Fund' and ACCOUNT = "
                        + str(self.user_id)
                        + " and MARKET = '"
                        + self.name
                        + "' and CURRENCY = '"
                        + currency
                        + "' and SYMBOL = '"
                        + symbol[0]
                        + "' and CATEGORY = '"
                        + instrument.category
                        + "'),0.0) funding from "
                        + "coins where SIDE <> 'Fund' and ACCOUNT = "
                        + str(self.user_id)
                        + " and MARKET = '"
                        + self.name
                        + "' and CURRENCY = '"
                        + currency
                        + "' and SYMBOL = '"
                        + symbol[0]
                        + "' and CATEGORY = '"
                        + instrument.category
                        + "'"
                    )
                    union = "union "
                sql += ") T"
                data = service.select_database(sql)
                settlCurrency = (currency, self.name)
                self.Result[settlCurrency].commission = float(data[0]["commiss"])
                self.Result[settlCurrency].funding = float(data[0]["funding"])
                self.Result[settlCurrency].sumreal = float(data[0]["sumreal"])
                self.Result[settlCurrency].result = 0
        else:
            var.logger.error("SQL error in account_balances() function")
            self.logNumFatal = "SETUP"

    def load_orders(self: Markets, myOrders: list) -> None:
        """
        All open orders received from the exchange endpoint as a result of an
        HTTP request are taken into account in the orders array. If the
        process of filling the array reveals an order whose emi identifier
        does not belong to any of the bots, such a bot will be created with
        the NOT DEFINED status.
        """
        self.orders = dict()
        for val in reversed(myOrders):
            if val["leavesQty"] != 0:
                emi = val["symbol"][0]
                if "clOrdID" in val:
                    if "." not in val["clOrdID"]:
                        del val["clOrdID"]
                if "clOrdID" not in val:
                    # The order was placed from the exchange web interface
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
                    emi = s[1]
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
                category = self.Instrument[val["symbol"]].category
                self.orders[clOrdID] = {}
                self.orders[clOrdID]["EMI"] = emi
                self.orders[clOrdID]["leavesQty"] = val["leavesQty"]
                self.orders[clOrdID]["transactTime"] = val["transactTime"]
                self.orders[clOrdID]["price"] = val["price"]
                self.orders[clOrdID]["SYMBOL"] = val["symbol"]
                self.orders[clOrdID]["CATEGORY"] = category
                self.orders[clOrdID]["MARKET"] = self.name
                self.orders[clOrdID]["SIDE"] = val["side"]
                self.orders[clOrdID]["orderID"] = val["orderID"]
                self.orders[clOrdID]["clOrdID"] = clOrdID

    def load_database(self: Markets) -> None:
        """
        Download the latest trades and funding data from the database (if any)
        """
        if self.user_id:
            sql = (
                "select ID, EMI, SYMBOL, TICKER, CATEGORY, MARKET, SIDE, QTY,"
                + "PRICE, TTIME, COMMISS from "
                + "coins where SIDE = 'Fund' and ACCOUNT = "
                + str(self.user_id)
                + " and MARKET = '"
                + self.name
                + "' "
                + "order by TTIME desc limit "
                + str(disp.table_limit)
            )
            data = service.select_database(sql)
            rows = list()
            for val in data:
                val["SYMBOL"] = (val["SYMBOL"], self.name)
                row = Function.funding_display(self, val=val, init=True)
                rows.append(row)
            data = TreeTable.funding.append_data(rows=rows, market=self.name)
            indx_pnl = TreeTable.funding.title.index("PNL")
            indx_market = TreeTable.funding.title.index("MARKET")
            for values in data:
                if float(values[indx_pnl]) >= 0:
                    configure = "Buy"
                else:
                    configure = "Sell"
                TreeTable.funding.insert(
                    values=values, market=values[indx_market], configure=configure
                )
            sql = (
                "select ID, EMI, SYMBOL, TICKER, CATEGORY, MARKET, SIDE, ABS(QTY) as QTY,"
                + "TRADE_PRICE, TTIME, COMMISS, SUMREAL from "
                + "coins where SIDE <> 'Fund' and ACCOUNT = "
                + str(self.user_id)
                + " and MARKET = '"
                + self.name
                + "' "
                + "order by TTIME desc limit "
                + str(disp.table_limit)
            )
            data = service.select_database(sql)
            rows = list()
            for val in data:
                val["SYMBOL"] = (val["SYMBOL"], self.name)
                row = Function.trades_display(
                    self, val=val, table=TreeTable.trades, init=True
                )
                rows.append(row)
            data = TreeTable.trades.append_data(rows=rows, market=self.name)
            indx_side = TreeTable.trades.title.index("SIDE")
            indx_market = TreeTable.trades.title.index("MARKET")
            for values in data:
                TreeTable.trades.insert(
                    values=values,
                    market=values[indx_market],
                    configure=values[indx_side],
                )
        else:
            self.logNumFatal = "SETUP"  # Reboot


def setup_database_connecion() -> None:
    try:
        var.connect_sqlite = sqlite3.connect(db_sqlite, check_same_thread=False)
        var.connect_sqlite.row_factory = sqlite3.Row
        var.cursor_sqlite = var.connect_sqlite.cursor()
        var.error_sqlite = Error

        sql_create_robots = """
        CREATE TABLE IF NOT EXISTS robots (
        EMI varchar(20) DEFAULT NULL UNIQUE,
        SYMBOL varchar(20) DEFAULT 'nemo',
        TICKER varchar(20) DEFAULT 'nemo',
        CATEGORY varchar(10) DEFAULT 'nemo',
        MARKET varchar(20) DEFAULT 'nemo',
        SORT tinyint DEFAULT 0,
        DAT timestamp NULL DEFAULT CURRENT_TIMESTAMP,
        TIMEFR tinyint DEFAULT 0,
        CAPITAL int DEFAULT 0,
        MARGIN int DEFAULT 0,
        STATE varchar(10) DEFAULT 'Suspended',
        UPDATED timestamp NULL DEFAULT CURRENT_TIMESTAMP)"""

        sql_create_coins = """
        CREATE TABLE IF NOT EXISTS coins (
        ID INTEGER PRIMARY KEY AUTOINCREMENT,
        EXECID varchar(45) DEFAULT NULL,
        EMI varchar(25) DEFAULT NULL,
        REFER varchar(20) DEFAULT NULL,
        MARKET varchar(20) DEFAULT NULL,
        CURRENCY varchar(10) DEFAULT NULL,
        SYMBOL varchar(20) DEFAULT NULL,
        TICKER varchar(20) DEFAULT NULL,
        CATEGORY varchar(10) DEFAULT NULL,
        SIDE varchar(4) DEFAULT NULL,
        QTY decimal(20,8) DEFAULT NULL,
        QTY_REST decimal(20,8) DEFAULT NULL,
        PRICE decimal(20,8) DEFAULT NULL,
        THEOR_PRICE decimal(20,8) DEFAULT NULL,
        TRADE_PRICE decimal(20,8) DEFAULT NULL,
        SUMREAL decimal(30,12) DEFAULT NULL,
        COMMISS decimal(30,16) DEFAULT 0.0000000000000000,
        TTIME datetime DEFAULT NULL,
        DAT timestamp NULL DEFAULT CURRENT_TIMESTAMP,
        CLORDID int DEFAULT 0,
        ACCOUNT int DEFAULT 0)"""

        var.cursor_sqlite.execute(sql_create_robots)
        var.cursor_sqlite.execute(sql_create_coins)
        var.cursor_sqlite.execute(
            "CREATE UNIQUE INDEX IF NOT EXISTS ID_UNIQUE ON coins (ID)"
        )
        var.cursor_sqlite.execute(
            "CREATE INDEX IF NOT EXISTS EXECID_ix ON coins (EXECID)"
        )
        var.cursor_sqlite.execute(
            "CREATE INDEX IF NOT EXISTS EMI_QTY_ix ON coins (EMI, QTY)"
        )
        var.cursor_sqlite.execute("CREATE INDEX IF NOT EXISTS SIDE_ix ON coins (SIDE)")
        var.connect_sqlite.commit()

    except Exception as error:
        var.logger.error(error)
        raise
