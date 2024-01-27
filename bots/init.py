from datetime import datetime, timedelta
from typing import Tuple, Union

import functions as function
from bots.variables import Variables as bot
from common.variables import Variables as var


def load_robots(db: str) -> dict:
    """
    This function loads robot settings from the SQL database from the 'robots'
    table. Since all transactions for the current account are saved in the
    database, the function also checks all robots that have open positions,
    but are not in the 'robots' table. Such robots are also loaded. Their
    status is indicated as 'NOT DEFINED'. The program must see orders and
    trades made from the standard exchange web interface, so reserved robot
    names are provided for each instrument that match the symbol of the
    instrument. Using this names, transactions are taken into account and
    financial results are calculated in the database for each instrument
    separately from the financial results of individual robots. The status of
    such robots is 'RESERVED'.
    """
    qwr = "select * from " + db + ".robots where SYMBOL in ("
    for num, symbol in enumerate(var.symbol_list):
        if num == 0:
            c = ""
        else:
            c = ", "
        qwr = qwr + c + "'" + symbol + "'"
    qwr = qwr + ") order by SORT"
    var.cursor_mysql.execute(qwr)
    for robot in var.cursor_mysql.fetchall():
        emi = robot["EMI"]
        bot.robots[emi] = robot
        bot.robots[emi]["STATUS"] = "WORK"

    # Searching for unclosed positions by robots that are not in the 'robots' table

    var.cursor_mysql.execute(
        "select SYMBOL, EMI, POS from (select emi, SYMBOL, \
            sum(CASE WHEN SIDE = 0 THEN QTY WHEN SIDE = 1 THEN \
                -QTY ELSE 0 END) POS from "
        + db
        + ".coins where \
                    account = %s and SIDE <> -1 group by EMI, \
                        SYMBOL) res where POS <> 0",
        var.user_id,
    )
    defuncts = var.cursor_mysql.fetchall()
    for defunct in defuncts:
        for emi in bot.robots:
            if defunct["EMI"] == emi:
                break
        else:
            if defunct["SYMBOL"] in var.symbol_list:
                status = "NOT DEFINED"
            else:
                status = "NOT IN LIST"
            bot.robots[defunct["EMI"]] = {
                "SYMBOL": defunct["SYMBOL"],
                "POS": int(defunct["POS"]),
                "EMI": defunct["EMI"],
                "STATUS": status,
                "TIMEFR": None,
                "CAPITAL": None,
            }

    # Adding RESERVED robots

    for symbol in var.symbol_list:
        var.cursor_mysql.execute(
            "select SYMBOL, EMI, POS from (select emi, SYMBOL, \
                sum(CASE WHEN SIDE = 0 THEN QTY WHEN SIDE = 1 THEN \
                    -QTY ELSE 0 END) POS from "
            + db
            + ".coins where \
                        account = %s and SIDE <> -1 group by EMI, \
                            SYMBOL) res where EMI = %s",
            (var.user_id, symbol),
        )
        reserved = var.cursor_mysql.fetchall()
        if symbol not in bot.robots:
            if not reserved:
                pos = 0
            else:
                pos = int(reserved[0]["POS"])
            if symbol in var.symbol_list or pos != 0:
                bot.robots[symbol] = {
                    "SYMBOL": symbol,
                    "POS": pos,
                    "EMI": symbol,
                    "STATUS": "RESERVED",
                    "TIMEFR": None,
                    "CAPITAL": None,
                }

    # Loading all transactions and calculating financial results for each robot

    for emi in bot.robots:
        function.add_symbol(symbol=bot.robots[emi]["SYMBOL"])
        var.cursor_mysql.execute(
            "SELECT IFNULL(sum(SUMREAL), 0) SUMREAL, IFNULL(sum(QTY), 0) \
                POS, IFNULL(sum(abs(QTY)), 0) VOL, IFNULL(sum(COMMISS), 0) \
                    COMMISS, IFNULL(max(TTIME), '1900-01-01 01:01:01') LTIME \
                        FROM (SELECT SUMREAL, (CASE WHEN SIDE = 0 THEN QTY \
                            WHEN SIDE = 1 THEN -QTY ELSE 0 END) QTY, \
                                COMMISS, TTIME FROM "
            + db
            + ".coins WHERE EMI = %s \
                                    AND ACCOUNT = %s) aa",
            (emi, var.user_id),
        )
        data = var.cursor_mysql.fetchall()
        for row in data:
            for col in row:
                bot.robots[emi][col] = row[col]
                if col == "POS" or col == "VOL":
                    bot.robots[emi][col] = int(bot.robots[emi][col])
                if col == "COMMISS" or col == "SUMREAL":
                    bot.robots[emi][col] = float(bot.robots[emi][col])
                if col == "LTIME":
                    bot.robots[emi][col] = datetime.strptime(
                        str(bot.robots[emi][col]), "%Y-%m-%d %H:%M:%S"
                    )
        bot.robots[emi]["PNL"] = 0
        bot.robots[emi]["FRAME"] = bot.robots[emi]["SYMBOL"] + str(
            bot.robots[emi]["TIMEFR"]
        )
        bot.robots[emi]["lotSize"] = (
            var.instruments[bot.robots[emi]["SYMBOL"]]["lotSize"]
            / var.instruments[bot.robots[emi]["SYMBOL"]]["myMultiplier"]
        )
        if bot.robots[emi]["SYMBOL"] not in bot.full_symbol_list:
            bot.full_symbol_list.append(bot.robots[emi]["SYMBOL"])

    return bot.robots


def download_data(
    time: datetime, target: datetime, symbol: str, timeframe: str
) -> Tuple[Union[list, None], Union[datetime, None]]:
    res = list()
    while target > time:
        data = var.ws.trade_bucketed(symbol=symbol, time=time, timeframe=timeframe)
        if data:
            last = time
            time = datetime.strptime(
                str(data[-1]["timestamp"][:19]), "%Y-%m-%dT%H:%M:%S"
            )
            if last == time:
                return res, time
            res += data
            print(
                "----> downloaded trade/bucketed, time: "
                + str(time)
                + ", rows downloaded:",
                len(res),
            )
        else:
            message = (
                "When downloading trade/bucketed data NoneType was recieved "
                + str(data)
            )
            var.logger.error(message)
            return None, None
    var.ws.logNumFatal = 0

    return res, time


def load_frames(
    robot: dict, frames: dict, framing: dict, timeframe: str
) -> Union[dict, None]:
    """
    Loading usual candlestick data from the exchange server. Data is recorded
    in files for each algorithm. Every time you reboot the files are
    overwritten.
    """
    filename = "data/" + timeframe + "_EMI" + robot["EMI"] + ".txt"
    with open(filename, "w"):
        pass
    target = datetime.utcnow()
    time = target - timedelta(days=bot.missing_days_number)
    delta = timedelta(minutes=robot["TIMEFR"] - target.minute % robot["TIMEFR"])
    target += delta
    target = target.replace(second=0, microsecond=0)

    # Loading timeframe data

    res, time = download_data(
        time=time,
        target=target,
        symbol=framing[timeframe]["symbol"],
        timeframe=var.timefrs[robot["TIMEFR"]],
    )
    if not res:
        return None

    # The 'frames' array is filled with timeframe data.

    for num, row in enumerate(res):
        utc = datetime.strptime(
            row["timestamp"][0:19], "%Y-%m-%dT%H:%M:%S"
        ) - timedelta(minutes=robot["TIMEFR"])
        frames[timeframe].append(
            {
                "date": (utc.year - 2000) * 10000 + utc.month * 100 + utc.day,
                "time": utc.hour * 10000 + utc.minute * 100,
                "bid": float(row["open"]),
                "ask": float(row["open"]),
                "hi": float(row["high"]),
                "lo": float(row["low"]),
                "funding": 0,
                "datetime": utc,
            }
        )
        if num < len(res[:-1]) - 1:
            function.save_timeframes_data(
                emi=robot["EMI"],
                timeframe=timeframe,
                frame=frames[timeframe][-1],
            )
    framing[timeframe]["time"] = utc

    message = "Downloaded missing data from the exchange for " + timeframe
    var.logger.info(message)
    function.info_display(message)

    return frames


def init_timeframes() -> Union[dict, None]:
    for emi in bot.robots:
        # Initialize candlestick timeframe data using 'TIMEFR' fields 
        # expressed in minutes.
        if bot.robots[emi]["TIMEFR"]:
            time = datetime.utcnow()
            try:
                bot.frames[bot.robots[emi]["FRAME"]]
                bot.framing[bot.robots[emi]["FRAME"]]["robots"].append(emi)
            except KeyError:
                bot.frames[bot.robots[emi]["FRAME"]] = []
                bot.framing[bot.robots[emi]["FRAME"]] = {
                    "symbol": bot.robots[emi]["SYMBOL"],
                    "timefr": bot.robots[emi]["TIMEFR"],
                    "time": time,
                    "robots": [],
                    "open": 0,
                    "trigger": 0,
                }
                bot.framing[bot.robots[emi]["FRAME"]]["robots"].append(emi)
                for num, symbol in enumerate(var.symbol_list):
                    if symbol == bot.framing[bot.robots[emi]["FRAME"]]["symbol"]:
                        bot.framing[bot.robots[emi]["FRAME"]]["SYMBOL"] = num
                        break
                res = load_frames(
                    robot=bot.robots[emi],
                    frames=bot.frames,
                    framing=bot.framing,
                    timeframe=bot.robots[emi]["FRAME"],
                )
                if not res:
                    message = (
                        "The emi " + emi + " candle timeframe data was not loaded!"
                    )
                    var.logger.error(message)
                    return None

    return bot.frames


def delete_unused_robot() -> None:
    """
    Deleting unused robots (if any)
    """
    emi_in_orders = set()
    for val in var.orders.values():
        emi_in_orders.add(val["emi"])
    for emi in bot.robots.copy():
        if bot.robots[emi]["STATUS"] in ("WORK", "OFF"):
            pass
        elif emi in var.symbol_list:
            bot.robots[emi]["STATUS"] = "RESERVED"
        elif bot.robots[emi]["POS"] == 0 and emi not in emi_in_orders:
            function.info_display("Robot EMI=" + emi + ". Deleting from 'robots'")
            del bot.robots[emi]
