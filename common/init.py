import os
import sqlite3
import threading
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

var.working_directory = os.path.abspath(os.getcwd())


class Init(WS, Variables):
    file_lock = threading.Lock()

    def clear_params(self: Markets) -> None:
        self.connect_count += 1
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
        his_data = history["data"]
        if isinstance(his_data, list):
            if his_data:
                while his_data:
                    for row in his_data:
                        data = service.select_database(  # read_database
                            "select EXECID from %s where EXECID='%s' and account=%s and market='%s'"
                            % (
                                var.database_table,
                                row["execID"],
                                self.user_id,
                                self.name,
                            ),
                        )
                        if not data:
                            Function.transaction(self, row=row, info="History")
                    last_history_time = his_data[-1]["transactTime"]
                    if not self.logNumFatal:
                        Init.save_history_file(self, time=last_history_time)
                    if history["length"] < count_val:
                        return "success"
                    history = WS.trading_history(
                        self, histCount=count_val, start_time=last_history_time
                    )
                    his_data = history["data"]
                    if not isinstance(his_data, list):
                        return service.unexpected_error(self)
        else:
            return service.unexpected_error(self)
        message = self.name + ": Empty trading history."
        var.logger.warning(message)
        var.queue_info.put(
            {
                "market": self.name,
                "message": message,
                "time": datetime.now(tz=timezone.utc),
                "warning": "warning",
            }
        )

        return "empty"

    def account_balances(self: Markets) -> None:
        """
        Calculates the final trading results for all currencies that were
        involved. The data is taken from the SQLite table. Additionally,
        accrued funding and paid commissions for the entire period are
        calculated.
        """
        data = service.select_database(
            "select SYMBOL, TICKER, CATEGORY from "
            + "%s where ACCOUNT=%s and MARKET='%s' group by SYMBOL, CATEGORY"
            % (var.database_table, self.user_id, self.name),
        )
        if isinstance(data, list):
            symbols = list(map(lambda x: (x["SYMBOL"], self.name), data))
            for row in data:
                Function.add_symbol(
                    self,
                    symb=row["SYMBOL"],
                    ticker=row["TICKER"],
                    category=row["CATEGORY"],
                )
            if not symbols:
                symbols = [("MUST_NOT_BE_EMPTY", "MUST_NOT_BE_EMPTY")]
            sql = (
                "select DISTINCT(CURRENCY) from "
                + var.database_table
                + " where MARKET = '"
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
                        + var.database_table
                        + " where SIDE = 'Fund' and ACCOUNT = "
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
                        + var.database_table
                        + " where SIDE <> 'Fund' and ACCOUNT = "
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

    def clear_orders_by_market(self: Markets):
        """
        Clears the var.orders dictionary of entries for a specific market
        when the market is restarted.
        """
        orders_copy = var.orders.copy()
        for emi, orders in orders_copy.items():
            emi_orders_copy = orders.copy()
            for clOrdID, order in emi_orders_copy.items():
                if order["market"] == self.name:
                    del var.orders[emi][clOrdID]

    def load_orders(self: Markets, myOrders: list) -> None:
        """
        All open orders received from the exchange endpoint as a result of an
        HTTP request are taken into account in the orders array.
        """
        myOrders.sort(key=lambda x: x["transactTime"], reverse=True)
        for val in reversed(myOrders):
            if val["leavesQty"] != 0:
                cl_id, emi = service.get_clOrdID(row=val)
                if cl_id == 0:
                    cl_id = service.set_clOrdID()
                    info_display(
                        self.name,
                        "Outside placement: price="
                        + str(val["price"])
                        + " side="
                        + val["side"]
                        + ". Assigned clOrdID="
                        + cl_id,
                    )
                if emi == "":
                    emi = service.set_emi(symbol=val["symbol"])
                else:
                    cl_id = val["clOrdID"]
                category = self.Instrument[val["symbol"]].category
                service.fill_order(
                    emi=emi, clOrdID=cl_id, category=category, value=val
                )

    def load_database(self: Markets) -> None:
        """
        Download the latest trades and funding data from the database (if any)
        """
        if self.user_id:
            sql = (
                "select ID, EMI, SYMBOL, TICKER, CATEGORY, MARKET, SIDE, QTY,"
                + "PRICE, TTIME, COMMISS from "
                + var.database_table
                + " where SIDE = 'Fund' and ACCOUNT = "
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
                + var.database_table
                + " where SIDE <> 'Fund' and ACCOUNT = "
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
        var.connect_sqlite = sqlite3.connect(var.db_sqlite, check_same_thread=False)
        var.connect_sqlite.row_factory = sqlite3.Row
        var.cursor_sqlite = var.connect_sqlite.cursor()
        var.error_sqlite = Error

        sql_create_robots = """
        CREATE TABLE IF NOT EXISTS robots (
        EMI varchar(20) DEFAULT NULL UNIQUE,
        SORT tinyint DEFAULT 0,
        DAT timestamp NULL DEFAULT CURRENT_TIMESTAMP,
        TIMEFR varchar(5) DEFAULT '5min',
        STATE varchar(10) DEFAULT 'Suspended',
        UPDATED timestamp NULL DEFAULT CURRENT_TIMESTAMP)"""

        sql_create = """
        CREATE TABLE IF NOT EXISTS %s (
        ID INTEGER PRIMARY KEY AUTOINCREMENT,
        SYMBOL varchar(40) DEFAULT NULL,
        MARKET varchar(20) DEFAULT NULL,
        CURRENCY varchar(10) DEFAULT NULL,
        TICKER varchar(40) DEFAULT NULL,
        CATEGORY varchar(20) DEFAULT NULL,
        MYMULTIPLIER int DEFAULT 1,
        MULTIPLIER int DEFAULT 1,
        TICKSIZE decimal(10,12) DEFAULT NULL,
        PRICE_PRECISION int DEFAULT NULL,
        MINORDERQTY decimal(10,12) DEFAULT NULL,
        QTYSTEP decimal(10,12) DEFAULT NULL,
        PRECISION int  DEFAULT NULL,
        EXPIRE datetime DEFAULT NULL,
        BASECOIN varchar(10) DEFAULT NULL,
        QUOTECOIN varchar(10) DEFAULT NULL,
        VALUEOFONECONTRACT decimal(10,12) DEFAULT NULL,
        TAKERFEE decimal(1,12) DEFAULT 0.000000000000,
        MAKERFEE decimal(1,12) DEFAULT 0.000000000000,
        DAT timestamp NULL DEFAULT CURRENT_TIMESTAMP)"""

        sql_create_expired = sql_create % var.expired_table
        sql_create_backtest = sql_create % "backtest"

        var.cursor_sqlite.execute(sql_create_robots)
        var.cursor_sqlite.execute(sql_create_expired)
        var.cursor_sqlite.execute(sql_create_backtest)
        create_table_for_trades(var.database_real)
        create_table_for_trades(var.database_test)
        var.cursor_sqlite.execute(
            "CREATE INDEX IF NOT EXISTS %s_MARKET_SYMBOL ON %s (MARKET, SYMBOL)"
            % (var.expired_table, var.expired_table)
        )
        var.cursor_sqlite.execute(
            "CREATE INDEX IF NOT EXISTS %s_MARKET_SYMBOL ON %s (MARKET, SYMBOL)"
            % (var.backtest_table, var.backtest_table)
        )
        var.connect_sqlite.commit()

    except Exception as error:
        var.logger.error(error)
        raise

def create_table_for_trades(table_name):
    try:
        sql_create_trade = ("""
        CREATE TABLE IF NOT EXISTS %s (
        ID INTEGER PRIMARY KEY AUTOINCREMENT,
        EXECID varchar(45) DEFAULT NULL,
        EMI varchar(20) DEFAULT NULL,
        REFER varchar(20) DEFAULT NULL,
        MARKET varchar(20) DEFAULT NULL,
        CURRENCY varchar(10) DEFAULT NULL,
        SYMBOL varchar(40) DEFAULT NULL,
        TICKER varchar(40) DEFAULT NULL,
        CATEGORY varchar(20) DEFAULT NULL,
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
            % table_name
        )
        var.cursor_sqlite.execute(sql_create_trade)
        var.cursor_sqlite.execute(
            "CREATE UNIQUE INDEX IF NOT EXISTS %s_ID ON %s (ID)"
            % (table_name, table_name)
        )
        var.cursor_sqlite.execute(
            "CREATE INDEX IF NOT EXISTS %s_EXECID ON %s (EXECID)"
            % (table_name, table_name)
        )
        var.cursor_sqlite.execute(
            "CREATE INDEX IF NOT EXISTS %s_EMI_QTY ON %s (EMI, QTY)"
            % (table_name, table_name)
        )
        var.cursor_sqlite.execute(
            "CREATE INDEX IF NOT EXISTS %s_SIDE ON %s (SIDE)"
            % (table_name, table_name)
        )
    except Exception as error:
        var.logger.error(error)
        raise