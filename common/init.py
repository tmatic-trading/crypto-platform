import logging
import os
from collections import OrderedDict
from datetime import datetime

import pymysql
import pymysql.cursors
from dotenv import load_dotenv

#import functions as function
from bots.variables import Variables as bot
from common.variables import Variables as var
from display.variables import Variables as disp
#from ws.init import Variables as ws

load_dotenv()
db = os.getenv("MYSQL_DATABASE")


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
            host=os.getenv("MYSQL_HOST"),
            user=os.getenv("MYSQL_USER"),
            password=os.getenv("MYSQL_PASSWORD"),
            database=os.getenv("MYSQL_DATABASE"),
            charset="utf8mb4",
            cursorclass=pymysql.cursors.DictCursor,
        )
        var.cursor_mysql = var.connect_mysql.cursor()

    except Exception:
        var.logger.error("No connection to mySQL database")
        exit(1)


def load_trading_history() -> None:
    """
    Load trading history (if any)
    """
    tm = datetime.utcnow()
    with open("history.ini", "r") as f:
        lst = list(f)
    if not lst or len(lst) < 1:
        var.logger.error("history.ini error. No data in history.ini")
        exit(1)
    lst = [x.replace("\n", "") for x in lst]
    last_history_time = datetime.strptime(lst[0], "%Y-%m-%d %H:%M:%S")
    if last_history_time > tm:
        var.logger.error(
            "history.ini error. The time in the history.ini file is greater than the current time."
        )
        exit(1)
    history = ws.bitmex.trading_history(histCount=500, time=last_history_time)
    if history == "error":
        var.logger.error("history.ini error")
        exit(1)
    tmp = datetime(2000, 1, 1)
    while history:
        for row in history:
            data = function.read_database(execID=row["execID"], user_id=var.user_id)
            if not data:
                function.transaction(row=row, info=" History ")
        last_history_time = datetime.strptime(
            history[-1]["transactTime"][0:19], "%Y-%m-%dT%H:%M:%S"
        )
        history = ws.bitmex.trading_history(histCount=500, time=last_history_time)
        if last_history_time == tmp:
            break
        tmp = last_history_time
    if ws.bitmex.logNumFatal == 0:
        with open("history.ini", "w") as f:
            f.write(str(last_history_time))


def load_orders() -> None:
    """
    Load Orders (if any)
    """
    myOrders = ws.bitmex.open_orders()
    var.orders = OrderedDict()
    disp.text_orders.delete("1.0", "end")
    disp.text_orders.insert("1.0", " - Orders -\n")
    for val in myOrders:
        if val["leavesQty"] != 0:
            emi = val["symbol"]
            if "clOrdID" not in val:
                # The order was placed from the exchange
                var.last_order += 1
                clOrdID = str(var.last_order) + "." + emi
                function.info_display(
                    "Outside placement: price="
                    + str(val["price"])
                    + " side="
                    + val["side"]
                    + ". Assigned clOrdID="
                    + clOrdID
                )
            else:
                clOrdID = val["clOrdID"]
                s = clOrdID.split(".")
                emi = s[1]
                if emi not in bot.robots:
                    bot.robots[emi] = {
                        "STATUS": "NOT DEFINED",
                        "TIMEFR": None,
                        "EMI": emi,
                        "SYMBOL": val["symbol"],
                        "POS": 0,
                        "VOL": 0,
                        "COMMISS": 0,
                        "SUMREAL": 0,
                        "LTIME": datetime.strptime(
                            val["transactTime"][0:19], "%Y-%m-%dT%H:%M:%S"
                        ),
                        "PNL": 0,
                        "CAPITAL": None,
                    }
                    mes = (
                        "Robot EMI="
                        + emi
                        + ". Adding to 'robots' with STATUS='NOT DEFINED'"
                    )
                    function.info_display(mes)
                    var.logger.info(mes)
            var.orders[clOrdID] = {}
            var.orders[clOrdID]["emi"] = emi
            var.orders[clOrdID]["leavesQty"] = val["leavesQty"]
            var.orders[clOrdID]["transactTime"] = val["transactTime"]
            var.orders[clOrdID]["price"] = val["price"]
            var.orders[clOrdID]["symbol"] = val["symbol"]
            var.orders[clOrdID]["side"] = val["side"]
            var.orders[clOrdID]["orderID"] = val["orderID"]
            var.orders[clOrdID]["oldPrice"] = 0
            function.orders_display(clOrdID=clOrdID)


def initial_mysql(account: int) -> None:
    """
    Calculate and load account results from mySQL
    """
    sql = "select distinct(SYMBOL) from " + db + ".coins where ACCOUNT=%s"
    var.cursor_mysql.execute(sql, (account))
    data = var.cursor_mysql.fetchall()
    symbols = list(map(lambda x: x["SYMBOL"], data))
    for symbol in symbols:
        function.add_symbol(symbol)
    for cur in var.currencies:
        symbols = ["no symbols yet"]
        for val in var.instruments.values():
            if val["settlCurrency"] == cur:
                symbols.append(val["symbol"])
        in_p = ", ".join(list(map(lambda x: "%s", symbols)))
        sql = (
            "select IFNULL(sum(COMMISS),0.0) commiss, IFNULL(sum(SUMREAL),0.0) \
                sumreal, IFNULL((select sum(COMMISS) from "
            + db
            + ".coins where SIDE \
                < 0 and ACCOUNT = %s and SYMBOL in ("
            + in_p
            + ")),0.0) funding from "
            + db
            + ".coins where SIDE >= 0 and ACCOUNT \
                    = %s and SYMBOL in ("
            + in_p
            + ")"
        )
        args = [account] + symbols + [account] + symbols
        var.cursor_mysql.execute(sql, args)
        data = var.cursor_mysql.fetchall()
        var.accounts[cur]["COMMISS"] = float(data[0]["commiss"])
        var.accounts[cur]["SUMREAL"] = float(data[0]["sumreal"])
        var.accounts[cur]["FUNDING"] = float(data[0]["funding"])


def initial_display(account: int) -> None:
    """
    Download the latest trades and funding data from the database (if any)
    """
    var.cursor_mysql.execute(
        "select EMI, SYMBOL, SIDE, QTY, PRICE, TTIME, COMMISS from "
        + db
        + ".coins \
            where SIDE=-1 AND account=%s order by id desc limit 121",
        account,
    )
    data = var.cursor_mysql.fetchall()
    disp.funding_display_counter = 0
    disp.text_funding.delete("1.0", "end")
    disp.text_funding.insert("1.0", " - Funding -\n")
    for val in reversed(data):
        function.add_symbol(symbol=val["SYMBOL"])
        function.funding_display(val)

    var.cursor_mysql.execute(
        "select EMI, SYMBOL, SIDE, QTY, TRADE_PRICE, TTIME, COMMISS, SUMREAL \
            from "
        + db
        + ".coins where SIDE<>-1 AND account=%s order by id desc \
                limit 151",
        account,
    )
    data = var.cursor_mysql.fetchall()
    disp.trades_display_counter = 0
    disp.text_trades.delete("1.0", "end")
    disp.text_trades.insert("1.0", " - Trades -\n")
    for val in reversed(data):
        function.add_symbol(symbol=val["SYMBOL"])
        function.trades_display(value=val)

    var.cursor_mysql.execute(
        "select max(TTIME) TTIME from " + db + ".coins where account=%s AND SIDE=-1",
        account,
    )
    data = var.cursor_mysql.fetchall()
    if data[0]["TTIME"]:
        var.last_database_time = datetime.strptime(
            str(data[0]["TTIME"]), "%Y-%m-%d %H:%M:%S"
        )


def initial_ticker_values() -> None:
    for symbol in var.symbol_list:
        var.ticker[symbol]["open_ask"] = var.ticker[symbol]["ask"]
        var.ticker[symbol]["open_bid"] = var.ticker[symbol]["bid"]
        var.ticker[symbol]["fundingRate"] = var.instruments[symbol]["fundingRate"]
