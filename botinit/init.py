import threading
from collections import OrderedDict
from datetime import datetime, timezone

import functions
import services as service
from api.api import Markets
from botinit.variables import Variables as robo
from common.data import Bots
from common.variables import Variables as var
from display.bot_menu import bot_manager, import_bot_module
from display.messages import ErrorMessage, Message


def add_subscription(subscriptions: set) -> None:
    threads = []
    var.subscription_res = dict()
    for symbol in subscriptions:
        if symbol[1] in var.market_list:
            ws = Markets[symbol[1]]
            ws.positions[symbol] = {"POS": 0}
            var.subscription_res[symbol] = False
            t = threading.Thread(
                target=functions.confirm_subscription,
                args=(
                    symbol[1],
                    symbol[0],
                    var.timeout,
                    True,
                ),
            )
            threads.append(t)
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
        ws = Markets[symbol[1]]
        if res:
            qwr = (
                "select MARKET, SYMBOL, sum(abs(QTY)) as SUM_QTY, "
                + "sum(SUMREAL) as SUM_SUMREAL from "
                + var.database_table
                + " where SYMBOL = '"
                + symbol[0]
                + "' and SIDE <> 'Fund' and market = '"
                + symbol[1]
                + "' and ACCOUNT = "
                + str(ws.user_id)
                + ";"
            )
            data = service.select_database(qwr)
            instrument = ws.Instrument[symbol]
            instrument.volume = round(data[0]["SUM_QTY"], instrument.precision)
            instrument.sumreal = data[0]["SUM_SUMREAL"]


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
        service.init_bot(
            bot=bot,
            name=value["EMI"],
            state=value["STATE"],
            timefr=value["TIMEFR"],
            created=value["DAT"],
            updated=value["UPDATED"],
        )


def load_bots() -> None:
    """
    Loading bots into the Bots class.
    """

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
                + "MARKET, SYMBOL, SIDE, ACCOUNT from "
                + var.database_table
                + " where "
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
    
    var.lock.acquire(True)
    update = True
    update_symbol = dict()
    while update:
        update = False
        qwr = functions.SelectDatabase.QWR.format(DATABASE_TABLE=var.database_table)
        data = service.select_database(qwr)
        subscriptions = set()
        update_symbol = dict()
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
                instrument = ws.Instrument[symbol]
                position = round(value["POS"], instrument.precision)
                if position != 0:
                    name = value["EMI"]
                    update_symbol[symbol] = {"position": position}
                    if name not in Bots.keys():
                        if name != "":
                            qwr = (
                                "select ID, EMI, SYMBOL from %s where side <> 'Fund' and EMI = '%s'"
                                % (var.database_table, name)
                            )
                            data = service.select_database(qwr)
                            for row in data:
                                qwr = "update %s set EMI = '%s' where ID = %s;" % (
                                    var.database_table,
                                    "",
                                    row["ID"],
                                )
                                service.update_database(query=qwr)
                            update = True

    # Adding subscriptions to unclosed positions found in the database (if any).

    for symbol, value in update_symbol.items():
        ws = Markets[symbol[1]]
        instrument = ws.Instrument[symbol]
        if value["position"] != 0:
            if symbol not in ws.symbol_list:
                tm = datetime.now(tz=timezone.utc)
                if (
                    instrument.state == "Open"
                    and isinstance(instrument.expire, datetime)
                    and instrument.expire > tm
                ) or instrument.expire == "Perpetual":
                    subscriptions.add(symbol)
                    message = Message.UNCLOSED_POSITION_FOUND.format(
                        POSITION=functions.Function.volume(
                            ws,
                            value["position"],
                            symbol
                        ),
                        SYMBOL=symbol[0]
                    )
                    _put_message(
                        market="", message=message, warning="warning"
                    )
                else:
                    message = ErrorMessage.IMPOSSIBLE_SUBSCRIPTION.format(
                        SYMBOL=symbol, STATE=instrument.state
                    )
                    _put_message(market="", message=message, warning=True)
    var.lock.release()

    add_subscription(subscriptions=subscriptions)

    # Loading trades and summing up the results for each bot.

    for name in Bots.keys():
        # Open Positions

        qwr = (
            "select * from (select SYMBOL, CATEGORY, MARKET, TICKER, "
            + "ifnull(sum(SUMREAL), 0) SUMREAL, ifnull(sum(case when SIDE = "
            + "'Fund' then 0 else QTY end), 0) POS, ifnull(sum(case when SIDE "
            + "= 'Fund' then 0 else abs(QTY) end), 0) VOL, ifnull(sum(COMMISS)"
            + ", 0) COMMISS, ifnull(max(TTIME), '1900-01-01 01:01:01.000000') "
            + "LTIME from "
            + var.database_table
            + " where EMI = '"
            + name
            + "' group by SYMBOL) T where POS <> 0;"
        )
        var.lock.acquire(True)
        data = service.select_database(qwr)
        bot = Bots[name]
        for value in data:
            symbol = (value["SYMBOL"], value["MARKET"])
            if value["MARKET"] in var.market_list:
                ws = Markets[value["MARKET"]]
                instrument = ws.Instrument[symbol]
                precision = instrument.precision
                bot_pos = round(float(value["POS"]), precision)
                if bot_pos != 0:
                    service.fill_bot_position(
                        bot_name=name,
                        symbol=symbol,
                        instrument=instrument,
                        user_id=ws.user_id,
                        position=bot_pos,
                        volume=round(float(value["VOL"]), precision),
                        sumreal=float(value["SUMREAL"]),
                        commiss=float(value["COMMISS"]),
                        ltime=service.time_converter(time=value["LTIME"], usec=True),
                    )
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

        # Results by currency for closed positions

        qwr = (
            "select * from (select SYMBOL, MARKET, CURRENCY, ifnull(sum(SUMREAL), 0) "
            + "SUMREAL, ifnull(sum(COMMISS), 0) COMMISS, ifnull(sum(case when SIDE = "
            + "'Fund' then 0 else QTY end), 0) POS, ifnull(max(TTIME), "
            + "'1900-01-01 01:01:01.000000') LTIME from "
            + var.database_table
            + " where EMI = '"
            + name
            + "' group by MARKET, SYMBOL) T where POS = 0 group by MARKET, CURRENCY;"
        )
        data = service.select_database(qwr)
        bot.bot_pnl = {}
        for value in data:
            if value["MARKET"] in var.market_list:
                symbol = (value["SYMBOL"], value["MARKET"])
                ws = Markets[value["MARKET"]]
                instrument = ws.Instrument[symbol]
                precision = instrument.precision
                bot_pos = round(float(value["POS"]), precision)
                if bot_pos == 0:
                    if value["MARKET"] not in bot.bot_pnl:
                        bot.bot_pnl[value["MARKET"]] = dict()
                    bot.bot_pnl[value["MARKET"]][value["CURRENCY"]] = dict()
                    bot.bot_pnl[value["MARKET"]][value["CURRENCY"]]["pnl"] = value[
                        "SUMREAL"
                    ]
                    bot.bot_pnl[value["MARKET"]][value["CURRENCY"]][
                        "commission"
                    ] = value["COMMISS"]
                    bot.iter = name
            else:
                message = ErrorMessage.BOT_PNL_CALCULATIONS.format(
                    BOT_NAME=name, MARKET=value["MARKET"]
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


def setup_bots():
    """
    Checks if there is a setup function for a particular bot. If so, runs the
    setup function.
    """
    for bot_name in Bots.keys():
        service.call_bot_function(function=robo.setup_bot[bot_name], bot_name=bot_name)
