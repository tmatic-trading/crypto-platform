from datetime import datetime, timedelta
from typing import Tuple, Union

# from ws.init import Variables as ws
from api.api import WS
# import functions as function
from api.init import Variables
from bots.variables import Variables as bot
from common.variables import Variables as var
from functions import Function
from display.functions import info_display


class Init(WS, Variables):
    def load_robots(self) -> dict:
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
        db = var.env["MYSQL_DATABASE"]
        union = ""
        qwr = "select * from ("
        for symbol in self.symbol_list:
            qwr += (
                union
                + "select * from "
                + db
                + ".robots where SYMBOL = '"
                + symbol[0]
                + "' and CATEGORY = '"
                + symbol[1]
                + "' "
            )
            union = "union "
        qwr += ") T where MARKET = '" + self.name + "' order by SORT"
        var.cursor_mysql.execute(qwr)
        for robot in var.cursor_mysql.fetchall():
            emi = robot["EMI"]
            self.robots[emi] = robot
            self.robots[emi]["STATUS"] = "WORK"
            self.robots[emi]["SYMBOL"] = (
                self.robots[emi]["SYMBOL"],
                self.robots[emi]["CATEGORY"],
            )

        # Searching for unclosed positions by robots that are not in the 'robots' table
        qwr = (
            "select SYMBOL, CATEGORY, EMI, POS from (select EMI, SYMBOL, CATEGORY, \
                sum(CASE WHEN SIDE = 0 THEN QTY WHEN SIDE = 1 THEN \
                    -QTY ELSE 0 END) POS from "
            + db
            + ".coins where MARKET = '"
            + self.name
            + "' and \
                        account = "
            + str(self.user_id)
            + " and SIDE <> -1 group by EMI, \
                            SYMBOL, CATEGORY) res where POS <> 0"
        )
        var.cursor_mysql.execute(qwr)
        defuncts = var.cursor_mysql.fetchall()
        for defunct in defuncts:
            symbol = (defunct["SYMBOL"], defunct["CATEGORY"])
            for emi in self.robots:
                if defunct["EMI"] == emi:
                    break
            else:
                if symbol in self.symbol_list:
                    status = "NOT DEFINED"
                else:
                    status = "NOT IN LIST"
                emi = ".".join(symbol)
                self.robots[emi] = {
                    "SYMBOL": symbol,
                    "CATEGORY": defunct["CATEGORY"],
                    "MARKET": self.name,
                    "POS": int(defunct["POS"]),
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
                + "select * from (select EMI, SYMBOL, CATEGORY, ACCOUNT, MARKET, \
            sum(CASE WHEN SIDE = 0 THEN QTY WHEN SIDE = 1 THEN \
            -QTY ELSE 0 END) POS from "
                + db
                + ".coins where SIDE <> -1 group by EMI, SYMBOL, CATEGORY, \
            ACCOUNT, MARKET) res where EMI = '"
                + symbol[0]
                + "' and CATEGORY = '"
                + symbol[1]
                + "' "
            )
            union = "union "
        qwr += (
            ") T where MARKET = '"
            + self.name
            + "' and ACCOUNT = "
            + str(self.user_id)
        )
        var.cursor_mysql.execute(qwr)
        reserved = var.cursor_mysql.fetchall()
        for symbol in self.symbol_list:
            for res in reserved:
                if symbol == (res["SYMBOL"], res["CATEGORY"]):
                    pos = int(reserved[0]["POS"])
                    break
            else:
                pos = 0
            if symbol in self.symbol_list or pos != 0:
                emi = ".".join(symbol)
                self.robots[emi] = {
                    "EMI": emi,
                    "SYMBOL": symbol,
                    "CATEGORY": symbol[1],
                    "MARKET": self.name,
                    "POS": pos,
                    "STATUS": "RESERVED",
                    "TIMEFR": "None",
                    "CAPITAL": "None",
                }

        # Loading all transactions and calculating financial results for each robot
        for emi, val in self.robots.items():
            Function.add_symbol(self, symbol=self.robots[emi]["SYMBOL"])
            if isinstance(emi, tuple):
                _emi = emi[0]
            else:
                _emi = emi
            var.cursor_mysql.execute(
                "SELECT IFNULL(sum(SUMREAL), 0) SUMREAL, IFNULL(sum(QTY), 0) \
                    POS, IFNULL(sum(abs(QTY)), 0) VOL, IFNULL(sum(COMMISS), 0) \
                        COMMISS, IFNULL(max(TTIME), '1900-01-01 01:01:01') LTIME \
                            FROM (SELECT SUMREAL, (CASE WHEN SIDE = 0 THEN QTY \
                                WHEN SIDE = 1 THEN -QTY ELSE 0 END) QTY, \
                                    COMMISS, TTIME FROM "
                + db
                + ".coins WHERE EMI = %s AND ACCOUNT = %s AND CATEGORY = %s) aa",
                (_emi, self.user_id, val["CATEGORY"]),
            )
            data = var.cursor_mysql.fetchall()
            for row in data:
                for col in row:
                    self.robots[emi][col] = row[col]
                    if col == "POS" or col == "VOL":
                        self.robots[emi][col] = int(self.robots[emi][col])
                    if col == "COMMISS" or col == "SUMREAL":
                        self.robots[emi][col] = float(self.robots[emi][col])
                    if col == "LTIME":
                        self.robots[emi][col] = datetime.strptime(
                            str(self.robots[emi][col]), "%Y-%m-%d %H:%M:%S"
                        )
            self.robots[emi]["PNL"] = 0
            self.robots[emi]["lotSize"] = (
                self.instruments[self.robots[emi]["SYMBOL"]]["lotSize"]
                / self.instruments[self.robots[emi]["SYMBOL"]]["myMultiplier"]
            )
            if self.robots[emi]["SYMBOL"] not in self.full_symbol_list:
                self.full_symbol_list.append(self.robots[emi]["SYMBOL"])

        return self.robots

    def download_data(
        self, time: datetime, target: datetime, symbol: tuple, timeframe: str
    ) -> Tuple[Union[list, None], Union[datetime, None]]:
        res = list()
        while target > time:
            data = self.trade_bucketed(
                name=self.name, symbol=symbol, time=time, timeframe=timeframe
            )
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
        self.logNumFatal = 0

        return res, time

    def load_frames(
        self,
        robot: dict,
        frames: dict,
    ) -> Union[dict, None]:
        """
        Loading usual candlestick data from the exchange server. Data is recorded
        in files for each algorithm. Every time you reboot the files are
        overwritten.
        """
        self.filename = Function.timeframes_data_filename(
            self, emi=robot["EMI"], symbol=robot["SYMBOL"], timefr=robot["TIMEFR"]
        )
        with open(self.filename, "w"):
            pass
        target = datetime.utcnow()
        time = target - timedelta(days=bot.missing_days_number)
        delta = timedelta(minutes=robot["TIMEFR"] - target.minute % robot["TIMEFR"])
        target += delta
        target = target.replace(second=0, microsecond=0)

        # Loading timeframe data

        res, time = Init.download_data(
            self,
            time=time,
            target=target,
            symbol=robot["SYMBOL"],
            timeframe=var.timefrs[robot["TIMEFR"]],
        )
        if not res:
            return None

        # The 'frames' array is filled with timeframe data.

        f = datetime.strptime(res[0]["timestamp"][0:19], "%Y-%m-%dT%H:%M:%S")
        l = datetime.strptime(res[-1]["timestamp"][0:19], "%Y-%m-%dT%H:%M:%S")
        if f > l:
            res.reverse()
        for num, row in enumerate(res):
            tm = datetime.strptime(
                row["timestamp"][0:19], "%Y-%m-%dT%H:%M:%S"
            ) - timedelta(minutes=robot["TIMEFR"])
            frames[robot["SYMBOL"]][robot["TIMEFR"]]["data"].append(
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
                    frame=frames[robot["SYMBOL"]][robot["TIMEFR"]]["data"][-1],
                )
        frames[robot["SYMBOL"]][robot["TIMEFR"]]["time"] = tm

        message = (
            "Downloaded missing data, symbol="
            + str(robot["SYMBOL"])
            + " TIMEFR="
            + str(robot["TIMEFR"])
        )
        var.logger.info(message)
        info_display(self.name, message)

        return frames

    def init_timeframes(self) -> Union[dict, None]:
        for emi in self.robots:
            # Initialize candlestick timeframe data using 'TIMEFR' fields
            # expressed in minutes.
            if self.robots[emi]["TIMEFR"] != "None":
                time = datetime.utcnow()
                symbol = self.robots[emi]["SYMBOL"]
                timefr = self.robots[emi]["TIMEFR"]
                try:
                    self.frames[symbol]
                except KeyError:
                    self.frames[symbol] = dict()
                    try:
                        self.frames[symbol][timefr]
                    except KeyError:
                        self.frames[symbol][timefr] = {
                            "time": time,
                            "robots": [],
                            "open": 0,
                            "data": [],
                        }
                        self.frames[symbol][timefr]["robots"].append(emi)
                        res = Init.load_frames(
                            self,
                            robot=self.robots[emi],
                            frames=self.frames,
                        )
                        if not res:
                            message = (
                                "The emi "
                                + emi
                                + " candle timeframe data was not loaded!"
                            )
                            var.logger.error(message)
                            return None

        return self.frames

    def delete_unused_robot(self) -> None:
        """
        Deleting unused robots (if any)
        """
        emi_in_orders = set()
        for val in var.orders.values():
            emi_in_orders.add(val["emi"])
        for emi in self.robots.copy():
            symbol = tuple(emi.split("."))
            if self.robots[emi]["STATUS"] in ("WORK", "OFF"):
                pass
            elif symbol in self.symbol_list:
                self.robots[emi]["STATUS"] = "RESERVED"
            elif self.robots[emi]["POS"] == 0 and emi not in emi_in_orders:
                info_display(self.name, "Robot EMI=" + emi + ". Deleting from 'robots'")
                del self.robots[emi]
