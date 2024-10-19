import threading
from collections import OrderedDict
from datetime import datetime, timezone

import functions
import services as service
from api.api import Markets
from common.data import Bots
from common.variables import Variables as var
from display.bot_menu import import_bot_module
from display.messages import ErrorMessage, Message


def add_subscription(subscriptions: set) -> None:
    threads = []
    var.subscription_res = dict()
    for symbol in subscriptions:
        if symbol[1] in var.market_list:
            ws = Markets[symbol[1]]
            ws.positions[symbol] = {"POS": 0}
            var.subscription_res[symbol] = None
            t = threading.Thread(
                target=functions.confirm_subscription,
                args=(
                    symbol[1],
                    symbol[0],
                    var.timeout,
                    True,
                ),
            )
            t.start()
        else:
            message = (
                "You are trying to subscribe "
                + str(symbol)
                + " but "
                + symbol[1]
                + " is not active. Check the .env.Subscriptions file."
            )
            _put_message(market=ws.name, message=message, warning="warning")
    [thread.join() for thread in threads]
    for symbol, res in var.subscription_res.items():
        if res:
            qwr = (
                "select MARKET, SYMBOL, sum(abs(QTY)) as SUM_QTY from coins where "
                + "SYMBOL = '"
                + symbol[0]
                + "' and SIDE <> 'Fund' and market = '"
                + symbol[1]
                + "' and ACCOUNT = "
                + str(ws.user_id)
                + ";"
            )
            data = service.select_database(qwr)
            ws.Instrument[symbol].volume = data[0]["SUM_QTY"]


def load_bot_parameters():
    qwr = "select * from robots order by DAT;"

    data = service.select_database(qwr)
    for bd in data:
        bd["DAT_datetime"] = datetime.strptime(bd["DAT"], "%Y-%m-%d %H:%M:%S")
    data.sort(key=lambda x: x["DAT_datetime"])
    for value in data:
        if value["EMI"] not in var.orders:
            var.orders[value["EMI"]] = OrderedDict()
        bot = Bots[value["EMI"]]
        bot.name = value["EMI"]
        bot.timefr = value["TIMEFR"]
        bot.timefr_sec = service.timeframe_seconds(value["TIMEFR"])
        bot.timefr_current = value["TIMEFR"]
        bot.created = value["DAT"]
        bot.updated = value["UPDATED"]
        bot.state = value["STATE"]
        bot.bot_positions = dict()
        bot.bot_orders = var.orders[value["EMI"]]
        bot.log = list()


def load_bots() -> None:
    """
    Loading bots into the Bots class.
    """
    load_bot_parameters()

    # Loading volumes for subscribed instruments

    if var.market_list:
        union = ""
        sql = ""
        for market in var.market_list:
            ws = Markets[market]
            sql += union
            qwr = (
                "select MARKET, SYMBOL, sum(QTY) as SUM_QTY, sum(SUMREAL) as "
                + "SUM_SUMREAL from (select abs(QTY) as QTY, SUMREAL, "
                + "MARKET, SYMBOL, SIDE, ACCOUNT from coins where "
            )
            _or = ""
            lst = ws.symbol_list.copy()
            if not lst:
                lst = [("MUST_NOT_BE_EMPTY", "MUST_NOT_BE_EMPTY")]
            for symbol in lst:
                qwr += _or
                qwr += "SYMBOL = '" + symbol[0] + "'"
                _or = " or "
            qwr += (
                ") T where SIDE <> 'Fund' and MARKET = '"
                + ws.name
                + "' and ACCOUNT = "
                + str(ws.user_id)
                + " group by SYMBOL, MARKET"
            )
            sql += qwr
            union = " union "
        sql += ";"
        var.lock.acquire(True)
        data = service.select_database(sql)
        for value in data:
            ws = Markets[value["MARKET"]]
            symbol = (value["SYMBOL"], value["MARKET"])
            instrument = ws.Instrument[symbol]
            precision = instrument.precision
            instrument.volume = round(float(value["SUM_QTY"]), precision)
            instrument.sumreal = float(value["SUM_SUMREAL"])
        var.lock.release()

    # Search for unclosed positions. If an unclosed position belongs to a bot
    # that is not in the "robots" table, EMI becomes "". If the SYMBOL of the
    # unclosed position is not subscribed, it is added to the subscription.
    qwr = (
        "select SYMBOL, TICKER, CATEGORY, EMI, POS, PNL, MARKET, TTIME from (select "
        + "EMI, SYMBOL, TICKER, CATEGORY, sum(QTY) POS, sum(SUMREAL) PNL, MARKET, "
        + "TTIME from coins where SIDE <> 'Fund' group by EMI, SYMBOL, "
        + "MARKET) res where POS <> 0 order by SYMBOL desc;"
    )
    var.lock.acquire(True)
    data = service.select_database(qwr)
    subscriptions = set()
    for value in data:
        if value["MARKET"] in var.market_list:
            ws = Markets[value["MARKET"]]
            functions.Function.add_symbol(
                ws,
                symb=value["SYMBOL"],
                ticker=value["TICKER"],
                category=value["CATEGORY"],
            )
            symbol = (value["SYMBOL"], ws.name)
            if symbol not in ws.symbol_list:
                if ws.Instrument[symbol].state == "Open":
                    subscriptions.add(symbol)
                    message = Message.SUBSCRIPTION_ADDED.format(SYMBOL=symbol[0])
                    var.logger.info(message)
                else:
                    message = ErrorMessage.IMPOSSIBLE_SUBSCRIPTION.format(
                        SYMBOL=symbol[0], STATE=ws.Instrument[symbol].state
                    )
                    _put_message(market="", message=message, warning="error")
            name = value["EMI"]
            if name not in Bots.keys():
                if value["SYMBOL"] != name and name != "":
                    qwr = (
                        "select ID, EMI, SYMBOL from coins where side <> 'Fund' and EMI = '%s'"
                        % (name)
                    )
                    data = service.select_database(qwr)
                    print("    ")
                    print(data)
                    for row in data:
                        qwr = "update coins set EMI = '%s' where ID = %s;" % (
                            "",
                            row["ID"],
                        )
                        service.update_database(query=qwr)
    var.lock.release()

    add_subscription(subscriptions=subscriptions)

    # Loading trades and summing up the results for each bot.

    for name in Bots.keys():
        qwr = (
            "select * from (select SYMBOL, CATEGORY, MARKET, TICKER, "
            + "ifnull(sum(SUMREAL), 0) SUMREAL, ifnull(sum(case when SIDE = "
            + "'Fund' then 0 else QTY end), 0) POS, ifnull(sum(case when SIDE "
            + "= 'Fund' then 0 else abs(QTY) end), 0) VOL, ifnull(sum(COMMISS)"
            + ", 0) COMMISS, ifnull(max(TTIME), '1900-01-01 01:01:01.000000') "
            + "LTIME from coins where EMI = '"
            + name
            + "' group by SYMBOL) T;"
        )
        var.lock.acquire(True)
        data = service.select_database(qwr)
        for value in data:
            symbol = (value["SYMBOL"], value["MARKET"])
            if value["MARKET"] in var.market_list:
                ws = Markets[value["MARKET"]]
                instrument = ws.Instrument[symbol]
                bot = Bots[name]
                precision = instrument.precision
                bot.bot_positions[symbol] = {
                    "emi": name,
                    "symbol": value["SYMBOL"],
                    "category": value["CATEGORY"],
                    "market": value["MARKET"],
                    "ticker": value["TICKER"],
                    "position": round(float(value["POS"]), precision),
                    "volume": round(float(value["VOL"]), precision),
                    "sumreal": float(value["SUMREAL"]),
                    "commiss": float(value["COMMISS"]),
                    "ltime": service.time_converter(time=value["LTIME"], usec=True),
                    "pnl": 0,
                    "lotSize": instrument.minOrderQty,
                    "currency": instrument.settlCurrency[0],
                    "limits": instrument.minOrderQty,
                }
                if instrument.category == "spot":
                    bot.bot_positions[symbol]["pnl"] = "-"
                    bot.bot_positions[symbol]["position"] = "-"
            elif value["POS"] != 0:
                message = (
                    name
                    + " bot has open position on "
                    + str(symbol)
                    + ", but "
                    + value["MARKET"]
                    + " is not enabled. Position on "
                    + str(symbol)
                    + " ignored. Add "
                    + value["MARKET"]
                    + " to the .env.Settings file."
                )
                _put_message(market="", message=message, warning="warning")
        var.lock.release()

    # Importing the strategy.py bot files

    for bot_name in Bots.keys():
        import_bot_module(bot_name=bot_name)


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
