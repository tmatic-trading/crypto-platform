import threading
from datetime import datetime, timedelta, timezone
from typing import Tuple, Union

import services as service
from api.api import WS, Markets
from api.init import Variables
from bots.variables import Variables as bot
from common.data import Bot
from common.variables import Variables as var
from display.functions import info_display
from functions import Function


class Init(WS, Variables):
    def load_robots(self: Markets) -> dict:
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
        union = ""
        qwr = "select * from ("
        for symbol in self.symbol_list:
            qwr += (
                union
                + "select * from robots where SYMBOL = '"
                + symbol[0]
                + "' and CATEGORY = '"
                + self.Instrument[symbol].category
                + "' "
            )
            union = "union "
        qwr += ") T where MARKET = '" + self.name + "' order by SORT"
        data = Function.select_database(self, qwr)
        for robot in data:
            emi = robot["EMI"]
            self.robots[emi] = robot
            self.robots[emi]["STATUS"] = "WORK"
            self.robots[emi]["SYMBOL"] = (
                self.robots[emi]["SYMBOL"],
                self.name,
            )

        # Searching for unclosed positions by robots that are not in the 'robots' table

        qwr = (
            "select SYMBOL, CATEGORY, EMI, POS from (select EMI, SYMBOL, CATEGORY, "
            + "sum(QTY) POS from coins where MARKET = '"
            + self.name
            + "' and account = "
            + str(self.user_id)
            + " and SIDE <> 'Fund' group by EMI, SYMBOL, CATEGORY) res where POS <> 0"
        )
        defuncts = Function.select_database(self, qwr)
        for defunct in defuncts:
            symbol = (defunct["SYMBOL"], self.name)
            for emi in self.robots:
                if defunct["EMI"] == emi:
                    break
            else:
                emi = defunct["EMI"]
                if defunct["CATEGORY"] == "spot":
                    status = "RESERVED"
                    emi = symbol[0]
                elif symbol in self.symbol_list:
                    status = "NOT DEFINED"
                else:
                    status = "NOT IN LIST"
                self.robots[emi] = {
                    "SYMBOL": symbol,
                    "CATEGORY": defunct["CATEGORY"],
                    "MARKET": self.name,
                    "POS": defunct["POS"],
                    "EMI": defunct["EMI"],
                    "STATUS": status,
                    "TIMEFR": "None",
                    "CAPITAL": "None",
                }

        # Adding RESERVED robots

        union = ""
        qwr = "select * from ("
        for symbol in self.symbol_list:
            qwr += (
                union
                + "select * from (select EMI, SYMBOL, CATEGORY, ACCOUNT, MARKET, "
                + "sum(QTY) POS from coins where SIDE <> 'Fund' group by EMI, "
                + "SYMBOL, CATEGORY, ACCOUNT, MARKET) res where EMI = '"
                + symbol[0]
                + "' and CATEGORY = '"
                + self.Instrument[symbol].category
                + "' "
            )
            union = "union "
        qwr += (
            ") T where MARKET = '" + self.name + "' and ACCOUNT = " + str(self.user_id)
        )
        reserved = Function.select_database(self, qwr)
        for symbol in self.symbol_list:
            for res in reserved:
                if symbol == (res["SYMBOL"], self.name):
                    pos = reserved[0]["POS"]
                    break
            else:
                pos = 0
            # if pos != 0:
            emi = symbol[0]
            self.robots[emi] = {
                "EMI": emi,
                "SYMBOL": symbol,
                "CATEGORY": self.Instrument[symbol].category,
                "MARKET": self.name,
                "POS": pos,
                "STATUS": "RESERVED",
                "TIMEFR": "None",
                "CAPITAL": "None",
            }

        # Loading all transactions and calculating financial results for each robot

        for emi, robot in self.robots.items():
            instrument = self.Instrument[robot["SYMBOL"]]
            Function.add_symbol(
                self,
                symbol=robot["SYMBOL"][0],
                ticker=instrument.ticker,
                category=instrument.category,
            )
            if isinstance(emi, tuple):
                _emi = emi[0]
            else:
                _emi = emi
            sql = (
                "SELECT IFNULL(sum(SUMREAL), 0) SUMREAL, IFNULL(sum(CASE WHEN "
                + "SIDE = 'Fund' THEN 0 ELSE QTY END), 0) "
                + "POS, IFNULL(sum(CASE WHEN SIDE = 'Fund' THEN 0 ELSE abs(QTY) "
                + "END), 0) VOL, IFNULL(sum(COMMISS), 0) "
                + "COMMISS, IFNULL(max(TTIME), '1900-01-01 01:01:01.000000') LTIME "
                + "FROM (SELECT SUMREAL, SIDE, QTY, COMMISS, TTIME FROM coins WHERE MARKET "
                + "= '%s' AND EMI = '%s' AND ACCOUNT = %s AND CATEGORY = '%s') aa"
                % (self.name, _emi, self.user_id, robot["CATEGORY"])
            )
            data = Function.select_database(self, sql)
            for row in data:
                for col in row:
                    robot[col] = row[col]
                    if col == "POS" or col == "VOL":
                        robot[col] = round(
                            robot[col], self.Instrument[robot["SYMBOL"]].precision
                        )
                    if col == "COMMISS" or col == "SUMREAL":
                        robot[col] = float(robot[col])
                    if col == "LTIME":
                        robot[col] = service.time_converter(time=robot[col], usec=True)
            if robot["CATEGORY"] == "spot":
                robot["PNL"] = "None"
                robot["POS"] = "None"
            else:
                robot["PNL"] = 0
            robot["lotSize"] = self.Instrument[robot["SYMBOL"]].minOrderQty

        return 0

    def download_data(
        self, start_time: datetime, target: datetime, symbol: tuple, timeframe: int
    ) -> Tuple[Union[list, None], Union[datetime, None]]:
        res = list()
        while target > start_time:
            data = WS.trade_bucketed(
                self, symbol=symbol, time=start_time, timeframe=timeframe
            )
            if data:
                last = start_time
                res += data
                message = (
                    self.name
                    + " - loading klines, symbol="
                    + str(symbol)
                    + ", startTime="
                    + str(start_time)
                    + ", received: "
                    + str(len(res))
                    + " records."
                )
                start_time = data[-1]["timestamp"] + timedelta(minutes=timeframe)
                var.logger.info(message)
                if last == start_time or target <= data[-1]["timestamp"]:
                    return res

            else:
                message = (
                    "When downloading trade/bucketed data NoneType was recieved. Reboot"
                )
                var.logger.error(message)
                return None
        self.logNumFatal = ""
        return res

    def load_frames(
        self: Markets,
        symbol: tuple,
        timefr: int,
        frames: dict,
    ) -> Union[dict, None]:
        """
        Loading kline data from the exchange server. Data is recorded
        in files for each timeframe. Every time you reboot the files are
        overwritten.
        """
        self.filename = Function.timeframes_data_filename(
            self, symbol=symbol, timefr=timefr
        )
        with open(self.filename, "w"):
            pass
        target = datetime.now(tz=timezone.utc)
        target = target.replace(second=0, microsecond=0)
        start_time = target - timedelta(
            minutes=bot.CANDLESTICK_NUMBER * timefr - timefr
        )
        delta = timedelta(minutes=target.minute % timefr + (target.hour * 60) % timefr)
        target -= delta

        # Loading timeframe data

        res = Init.download_data(
            self,
            start_time=start_time,
            target=target,
            symbol=symbol,
            timeframe=timefr,
        )
        if not res:
            return None

        # Bitmex bug fix. Bitmex can send data with the next period's
        # timestamp typically for 5m and 60m.
        if target < res[-1]["timestamp"]:
            delta = timedelta(minutes=timefr)
            for r in res:
                r["timestamp"] -= delta

        # The 'frames' array is filled with timeframe data.

        if res[0]["timestamp"] > res[-1]["timestamp"]:
            res.reverse()
        for num, row in enumerate(res):
            tm = row["timestamp"] - timedelta(minutes=timefr)
            frames[symbol][timefr]["data"].append(
                {
                    "date": (tm.year - 2000) * 10000 + tm.month * 100 + tm.day,
                    "time": tm.hour * 10000 + tm.minute * 100,
                    "bid": float(row["open"]),
                    "ask": float(row["open"]),
                    "hi": float(row["high"]),
                    "lo": float(row["low"]),
                    "datetime": tm,
                }
            )
            if num < len(res[:-1]) - 1:
                Function.save_timeframes_data(
                    self,
                    frame=frames[symbol][timefr]["data"][-1],
                )
        frames[symbol][timefr]["time"] = tm

        message = (
            "Downloaded missing data, symbol=" + str(symbol) + " TIMEFR=" + str(timefr)
        )
        var.logger.info(message)

        return frames

    def init_timeframes(self: Markets) -> Union[dict, None]:
        def append_new(frames, symbol, timefr, time):
            frames[symbol][timefr] = {
                "time": time,
                "robots": [],
                "open": 0,
                "data": [],
            }
            frames[symbol][timefr]["robots"].append(emi)

            return frames

        success = []

        def get_in_thread(symbol, timefr, frames, number):
            nonlocal success
            res = Init.load_frames(
                self,
                symbol=symbol,
                timefr=timefr,
                frames=frames,
            )
            if not res:
                message = (
                    str(symbol) + " " + str(timefr) + " min kline data was not loaded!"
                )
                var.logger.error(message)
                return
            success[number] = "success"

        for emi in self.robots:
            # Initialize candlestick timeframe data using 'TIMEFR' fields
            # expressed in minutes.
            if self.robots[emi]["TIMEFR"] != "None":
                time = datetime.now(tz=timezone.utc)
                symbol = self.robots[emi]["SYMBOL"]
                timefr = self.robots[emi]["TIMEFR"]
                try:
                    self.frames[symbol][timefr]["robots"].append(emi)
                except KeyError:
                    try:
                        self.frames = append_new(self.frames, symbol, timefr, time)
                    except KeyError:
                        self.frames[symbol] = dict()
                        self.frames = append_new(self.frames, symbol, timefr, time)
        threads = []
        for symbol, timeframes in self.frames.items():
            for timefr in timeframes.keys():
                success.append(None)
                t = threading.Thread(
                    target=get_in_thread,
                    args=(symbol, timefr, self.frames, len(success) - 1),
                )

                threads.append(t)
                t.start()

        [thread.join() for thread in threads]
        for s in success:
            if not s:
                return

        return "success"

    def delete_unused_robot(self: Markets) -> None:
        """
        Deleting unused robots (if any)
        """
        emi_in_orders = set()
        for val in self.orders.values():
            emi_in_orders.add(val["EMI"])
        for emi in self.robots.copy():
            symbol = tuple(emi.split(".")) + (self.name,)
            if self.robots[emi]["STATUS"] in ("WORK", "OFF"):
                pass
            elif symbol in self.symbol_list:
                self.robots[emi]["STATUS"] = "RESERVED"
            elif self.robots[emi]["POS"] == 0 and emi not in emi_in_orders:
                info_display(self.name, "Robot EMI=" + emi + ". Deleting from 'robots'")
                del self.robots[emi]


def load_bots():
    """
    Loading bots into the new Bot class is under development.
    """

    qwr = "select * from robots order by SORT;"

    data = Function.select_database("self", qwr)
    for value in data:
        name = value["EMI"]
        bot = Bot[name]
        bot.name = value["EMI"]
        bot.market = value["MARKET"]
        bot.timefr = value["TIMEFR"]
        bot.created = value["DAT"]
        bot.status = "ON"

    # Subscribe to instruments for which bots have open positions

    # Searching for unclosed positions by robots that are not in the 'robots' table

    qwr = (
        "select SYMBOL, CATEGORY, EMI, POS, PNL, MARKET, TTIME from (select "
        + "EMI, SYMBOL, CATEGORY, sum(QTY) POS, sum(SUMREAL) PNL, MARKET, "
        + "TTIME from coins where SIDE <> 'Fund' group by EMI, SYMBOL, "
        + "MARKET) res where POS <> 0;"
    )
    data = Function.select_database("self", qwr)
    for value in data:
        name = value["EMI"]
        print("-----")
        print(value)
        if name not in Bot.keys():
            bot = Bot[name]
            symbol = (value["SYMBOL"], value["MARKET"])
            bot.name = value["EMI"]
            bot.position[symbol] = value["POS"]
            bot.pnl[symbol] = value["PNL"]
            bot.status = "NOT DEFINED"

    """for name, bot in Bot.items():
        for value in bot:
            print(value.name, value.value)"""
