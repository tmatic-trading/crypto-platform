import os
import platform
import time
import tkinter as tk
import traceback
from collections import OrderedDict
from datetime import datetime, timezone
from typing import Union

from dotenv import dotenv_values, set_key

from common.data import BotData, Bots, Instrument
from common.variables import Variables as var
from display.messages import ErrorMessage, Message

if platform.system() == "Windows":
    import ctypes
    import ctypes.wintypes

    PROCESS_QUERY_INFORMATION = 0x0400
    PROCESS_VM_READ = 0x0010
    pid = os.getpid()  # Current process PID

    class PROCESS_MEMORY_COUNTERS(ctypes.Structure):
        _fields_ = [
            ("cb", ctypes.wintypes.DWORD),
            ("PageFaultCount", ctypes.wintypes.DWORD),
            ("PeakWorkingSetSize", ctypes.wintypes.ctypes.c_size_t),
            ("WorkingSetSize", ctypes.wintypes.ctypes.c_size_t),
            ("QuotaPeakPagedPoolUsage", ctypes.wintypes.ctypes.c_size_t),
            ("QuotaPagedPoolUsage", ctypes.wintypes.ctypes.c_size_t),
            ("QuotaPeakNonPagedPoolUsage", ctypes.wintypes.ctypes.c_size_t),
            ("QuotaNonPagedPoolUsage", ctypes.wintypes.ctypes.c_size_t),
            ("PagefileUsage", ctypes.wintypes.ctypes.c_size_t),
            ("PeakPagefileUsage", ctypes.wintypes.ctypes.c_size_t),
        ]

    counters = PROCESS_MEMORY_COUNTERS()
    process_handle = ctypes.windll.kernel32.OpenProcess(
        PROCESS_QUERY_INFORMATION | PROCESS_VM_READ, False, pid
    )

    def get_memory_usage():
        """Get the memory usage of the current process (Windows)"""
        ctypes.windll.psapi.GetProcessMemoryInfo(
            process_handle, ctypes.byref(counters), ctypes.sizeof(counters)
        )
        # Return memory usage in bytes (WorkingSetSize = physical memory
        # currently used by the process)
        return counters.WorkingSetSize / (1024**2)  # Convert bytes to MB

else:
    # Unix-like OS (Darwin is macOS)
    import resource

    def get_memory_usage():
        """Get the memory usage of the current process (Unix)"""
        usage = resource.getrusage(resource.RUSAGE_SELF)
        if platform.system() == "Darwin":
            return usage.ru_maxrss / 1048576  # Convert B to MB
        else:
            return usage.ru_maxrss / 1024  # Convert KB to MB


class Variables:
    cpu_count = 1  # os.cpu_count()
    start_time = 0
    cpu_start = 0
    cpu_usage = 0
    memory_usage = 0
    usage_count = 0


def get_usage():
    per_second = int(1000 / var.refresh_rate)
    if Variables.usage_count >= per_second:
        # Comes here 1 time every second
        current_time = time.time()
        current_cpu = os.times()
        if Variables.start_time != 0:
            # Calculate elapsed real and user times
            elapsed_real_time = current_time - Variables.start_time
            elapsed_user_time = current_cpu.user - Variables.cpu_start.user
            elapsed_sys_time = current_cpu.system - Variables.cpu_start.system
            # Calculate CPU usage percentage
            Variables.cpu_usage = int(
                round(
                    ((elapsed_user_time + elapsed_sys_time) / elapsed_real_time)
                    * 100
                    / Variables.cpu_count,
                    0,
                )
            )
            # Calculate memory usage in MB
            Variables.memory_usage = int(round(get_memory_usage(), 0))
            # print(f"s={current_time}, f={time.time()}, e={time.time() - current_time}")
        Variables.start_time = current_time
        Variables.cpu_start = current_cpu
        Variables.usage_count = 0
    Variables.usage_count += 1


def ticksize_rounding(price: float, ticksize: float) -> float:
    """
    Rounds the price depending on the tickSize value.
    """
    arg = 1 / ticksize
    res = round(price * arg, 0) / arg

    return res


def number_rounding(number: float, precision: int) -> str:
    """
    Rounds a number to the specified precision.
    """
    if not isinstance(number, float):
        return number
    number = "{:.{precision}f}".format(number, precision=precision)
    for num, char in enumerate(reversed(number)):
        if char != "0":
            break
    number = number[: len(number) - num]
    if number[-1] == ".":
        number = number[:-1]

    return number


def time_converter(
    time: Union[int, float, str, datetime], usec=False
) -> Union[datetime, int]:
    """
    The datetime always corresponds to utc time, the timestamp always
    corresponds to local time.
    int, float      -> datetime (utc)
    datetime utc    -> Unix timestamp (local time)
    str utc         -> datetime (utc)
    """
    if isinstance(time, int) or isinstance(time, float):
        return datetime.fromtimestamp(time, tz=timezone.utc)
    elif isinstance(time, datetime):
        return int(time.timestamp() * 1000)
    elif isinstance(time, str):
        time = time.replace("T", " ")
        time = time.replace("Z", "")
        f = time.find("+")
        if f > 0:
            time = time[:f]
        if usec:
            try:
                dt = datetime.strptime(time, "%Y-%m-%d %H:%M:%S.%f")
            except Exception:
                dt = datetime.strptime(time, "%Y-%m-%d %H:%M:%S")
        else:
            dt = datetime.strptime(time[:19], "%Y-%m-%d %H:%M:%S")
        dt = dt.replace(tzinfo=timezone.utc)
        return dt

    else:
        raise TypeError(type(time))


def precision(number: float) -> int:
    r = str(number)
    if "e" in r:
        r = r.replace("e", "")
        r = r.replace(".", "")
        r = r.split("-")
        precision = len(r[0]) - 1 + int(r[1])
    elif "." in r:
        r = r.split(".")
        if int(r[1]) == 0:
            precision = 0
        else:
            precision = len(r[1])
    else:
        precision = 0

    return precision


def add_space(line: list) -> str:
    n = max(map(lambda x: len(x), line))
    lst = list()
    for l in line:
        lst.append((n - len(l)) * " " + l)

    return "\n".join(lst)


def close(markets):
    for bot_name in var.bot_thread_active:
        var.bot_thread_active[bot_name] = False
    for name in var.market_list:
        ws = markets[name]
        ws.exit()


def display_exception(exception) -> str:
    formated = "".join(
        traceback.format_exception(type(exception), exception, exception.__traceback__)
    )
    print(formated)

    return formated


def select_database(query: str) -> list:
    err_locked = 0
    while True:
        try:
            var.sql_lock.acquire(True)
            var.cursor_sqlite.execute(query)
            orig = var.cursor_sqlite.fetchall()
            var.sql_lock.release()
            data = []
            if orig:
                data = list(map(lambda x: dict(zip(orig[0].keys(), x)), orig))
            return data
        except Exception as e:  # var.error_sqlite
            if "database is locked" not in str(e):
                print("_____query:", query)
                var.logger.error("Sqlite Error: " + str(e) + ")")
                var.sql_lock.release()
                break
            else:
                err_locked += 1
                var.logger.error(
                    "Sqlite Error: Database is locked (attempt: "
                    + str(err_locked)
                    + ")"
                )
                var.sql_lock.release()


def insert_database(values: list, table: str) -> None:
    err_locked = 0
    while True:
        try:
            var.sql_lock.acquire(True)
            if table == "coins":
                var.cursor_sqlite.execute(
                    "insert into coins (EXECID,EMI,REFER,CURRENCY,SYMBOL,"
                    + "TICKER,CATEGORY,MARKET,SIDE,QTY,QTY_REST,PRICE,"
                    + "THEOR_PRICE,TRADE_PRICE,SUMREAL,COMMISS,CLORDID,TTIME,"
                    + "ACCOUNT) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                    values,
                )
            elif table == "robots":
                var.cursor_sqlite.execute(
                    "insert into robots (EMI,STATE,TIMEFR) VALUES (?,?,?)",
                    values,
                )
            elif table == "symbols":
                var.cursor_sqlite.execute(
                    "insert into symbols (SYMBOL,MARKET,CATEGORY,CURRENCY,"
                    + "TICKER,MYMULTIPLIER,MULTIPLIER,TICKSIZE,"
                    + "PRICE_PRECISION,MINORDERQTY,QTYSTEP,PRECISION,EXPIRE,"
                    + "BASECOIN,QUOTECOIN,VALUEOFONECONTRACT) VALUES (?,?,?,"
                    + "?,?,?,?,?,?,?,?,?,?,?,?,?)",
                    values,
                )
            else:
                return "Sqlite Error: Unknown database table."
            var.connect_sqlite.commit()
            var.sql_lock.release()
            return None
        except Exception as ex:  # var.error_sqlite
            if "database is locked" not in str(ex):
                err_str = f"Sqlite Error: {str(ex)} for: {values[0]}"
                var.logger.error(err_str)
                var.sql_lock.release()
                return err_str
            else:
                err_locked += 1
                var.logger.error(
                    "Sqlite Error: Database is locked (attempt: "
                    + str(err_locked)
                    + ")"
                )
                var.connect_sqlite.rollback()
                var.sql_lock.release()


def update_database(query: list) -> Union[str, None]:
    err_locked = 0
    while True:
        try:
            var.sql_lock.acquire(True)
            var.cursor_sqlite.execute(query)
            var.connect_sqlite.commit()
            var.sql_lock.release()
            return None
        except Exception as e:  # var.error_sqlite
            if "database is locked" not in str(e):
                err_str = f"Sqlite Error: {str(e)}"
                var.logger.error(err_str)
                var.sql_lock.release()
                return err_str
            else:
                err_locked += 1
                var.logger.error(
                    "Sqlite Error: Database is locked (attempt: "
                    + str(err_locked)
                    + ")"
                )
                var.connect_sqlite.rollback()
                var.sql_lock.release()


def set_clOrdID(emi: str) -> str:
    var.last_order += 1
    clOrdID = f"{var.last_order}.{emi}"

    return clOrdID


def fill_order(emi: str, clOrdID: str, category: str, value: dict) -> None:
    if emi not in var.orders:
        var.orders[emi] = OrderedDict()
    var.orders[emi][clOrdID] = dict()
    var.orders[emi][clOrdID]["emi"] = emi
    var.orders[emi][clOrdID]["leavesQty"] = value["leavesQty"]
    var.orders[emi][clOrdID]["transactTime"] = value["transactTime"]
    var.orders[emi][clOrdID]["price"] = value["price"]
    var.orders[emi][clOrdID]["symbol"] = value["symbol"]
    var.orders[emi][clOrdID]["category"] = category
    var.orders[emi][clOrdID]["market"] = value["symbol"][1]
    var.orders[emi][clOrdID]["side"] = value["side"]
    var.orders[emi][clOrdID]["orderID"] = value["orderID"]
    var.orders[emi][clOrdID]["clOrdID"] = clOrdID


def fill_bot_position(
    bot_name: str, symbol: tuple, instrument: Instrument, user_id: int
) -> None:
    bot = Bots[bot_name]
    bot.bot_positions[symbol] = {
        "emi": bot_name,
        "symbol": instrument.symbol,
        "category": instrument.market,
        "market": instrument.market,
        "ticker": instrument.ticker,
        "position": 0,
        "volume": 0,
        "sumreal": 0,
        "commiss": 0,
        "ltime": None,
        "pnl": 0,
        "lotSize": instrument.minOrderQty,
        "currency": instrument.settlCurrency[0],
        "limits": instrument.minOrderQty,
    }
    # Checks if this bot has any records in the database on this instrument.
    if not var.backtest:
        qwr = (
            "select MARKET, SYMBOL, sum(abs(QTY)) as SUM_QTY, "
            + "sum(SUMREAL) as SUM_SUMREAL, sum(COMMISS) as "
            + "SUM_COMMISS, TTIME from (select * from coins where EMI = '"
            + bot_name
            + "' and SYMBOL = '"
            + instrument.symbol
            + "' and MARKET = '"
            + instrument.market
            + "' and ACCOUNT = "
            + str(user_id)
            + " and SIDE <> 'Fund' order by ID desc) T;"
        )
        data = select_database(qwr)[0]
        if data and data["SUM_QTY"]:
            bot.bot_positions[symbol]["volume"] = float(data["SUM_QTY"])
            bot.bot_positions[symbol]["sumreal"] = float(data["SUM_SUMREAL"])
            bot.bot_positions[symbol]["commiss"] = float(data["SUM_COMMISS"])


def timeframe_seconds(timefr: str) -> int:
    """
    Converts a time interval in a string to seconds.
    """
    timefr_minutes = var.timeframe_human_format[timefr]

    return timefr_minutes * 60


def bot_error(bot: BotData) -> str:
    if not bot.error_message:
        error = "-"
    else:
        error = bot.error_message["error_type"]

    return error


def kline_hi_lo_values(ws, symbol: tuple, instrument: Instrument) -> None:
    """
    Updates the high and low values of kline data when websocket updates the
    order book.

    Parameters
    ----------
    ws: Markets
        Bitmex, Bybit, Deribit
    symbol: tuple
        Instrument symbol in (symbol, market name) format, e.g.
        ("BTCUSD", "Bybit").
    instrument: Instrument
        The Instrument instance for this symbol.
    """
    if symbol in ws.klines:
        for timeframe in ws.klines[symbol].values():
            if timeframe["data"]:
                ask = instrument.asks[0][0]
                bid = instrument.bids[0][0]
                if ask > timeframe["data"][-1]["hi"]:
                    timeframe["data"][-1]["hi"] = ask
                if bid < timeframe["data"][-1]["lo"]:
                    timeframe["data"][-1]["lo"] = bid


def count_orders():
    """Temporarily created function for debugging"""
    count = 0
    for values in var.orders.values():
        for _ in values.keys():
            count += 1
    # print("___________________orders", count)


def noll(val: str, length: int) -> str:
    r = ""
    for _ in range(length - len(val)):
        r = r + "0"

    return r + val


def format_message(market: str, message: str, tm=None) -> str:
    """
    Formats the message in the required format.
    """
    if market:
        market += ": "
    if not tm:
        tm = datetime.now(tz=timezone.utc)
    text = (
        noll(str(tm.hour), 2)
        + ":"
        + noll(str(tm.minute), 2)
        + ":"
        + noll(str(tm.second), 2)
        + "."
        + noll(str(int(tm.microsecond / 1000)), 3)
        + "  "
        + market
        + message
        + "\n"
    )
    if isinstance(text, tuple):
        text = text[0]

    return text


def wrap(frame: tk.Frame, padx):
    for child in frame.winfo_children():
        if type(child) is tk.Label:
            child.config(wraplength=frame.winfo_width() - padx * 2)


def cancel_market(market: str) -> None:
    """
    Removes an exchange from the boot process if an error like "Host name is
    invalid" occurs.
    """
    if market in var.market_list:
        var.market_list.remove(market)


def check_symbol_list(symbols: list, market: str, symbol_list: list) -> list:
    """
    Checks if the symbols in the symbol_list of a given market are valid for
    further websocket subscription. Removes misspelled or expired symbols
    from the symbol_list. If symbol_list is empty after removal, adds a
    default symbol.

    Parameters
    ----------
    symbols: list
        List of symbols of all available active instruments, which is
        received from the exchange.
    market: str
        Exchange name.
    symbol_list: list
        Symbols for subscription.

    Returns
    -------
    list
        Corrected symbol_list.
    """

    def put_default(symbol_list: list):
        if not symbol_list:
            default = var.default_symbol[market]
            symbol_list = var.default_symbol[market]
            message = Message.DEFAULT_SYMBOL_ADDED.format(
                SYMBOL=default[0], MARKET=market
            )
            var.queue_info.put(
                {
                    "market": market,
                    "message": message,
                    "time": datetime.now(tz=timezone.utc),
                    "warning": "warning",
                }
            )
            var.logger.info(message)

        return symbol_list

    if symbols:
        for symbol in symbol_list.copy():
            if symbol not in symbols:
                message = ErrorMessage.UNKNOWN_SYMBOL.format(
                    SYMBOL=symbol[0], MARKET=market
                )
                var.queue_info.put(
                    {
                        "market": market,
                        "message": message,
                        "time": datetime.now(tz=timezone.utc),
                        "warning": "error",
                    }
                )
                var.logger.error(message)
                symbol_list.remove(symbol)
        symbol_list = put_default(symbol_list=symbol_list)
    else:
        symbol_list = put_default(symbol_list=symbol_list)

    return symbol_list


def unexpected_error(ws) -> str:
    """
    if the http request produces an error, or if it is correct but the data
    received does not match the expected data, and this error is assumed to
    be FATAL.
    """
    if not ws.logNumFatal:
        ws.logNumFatal = "FATAL"

    return ws.logNumFatal


def fill_instrument_index(index: OrderedDict, instrument: Instrument, ws) -> dict:
    """
    Adds an instrument to the instrument_index dictionary.

    Parameters
    ----------
    index: dict
        The instrument_index is used for the Instrument Menu. It ranks
        instruments by category, currency.
    instrument: Instrument
        An Instrument instance, which belongs to a particular exchange.
    ws: Markets
        Bitmex, Bybit or Deribit object.

    Returns
    -------
    dict
        The instrument_index dictionary.

    """
    category = instrument.category
    if "spot" in category:
        currency = instrument.baseCoin
    else:
        currency = instrument.settlCurrency[0]
    if category not in index:
        index[category] = OrderedDict()
    if currency not in index[category]:
        index[category][currency] = OrderedDict()
    symb = instrument.symbol
    if "option" in category and "combo" not in category:
        parts = symb.split("-")
        option_series = "-".join(parts[:2]) + var._series
        if option_series not in index[category][currency]:
            index[category][currency][option_series] = OrderedDict()
            index[category][currency][option_series]["CALLS"] = list()
            index[category][currency][option_series]["PUTS"] = list()
            index[category][currency][option_series]["sort"] = option_series
        if parts[-1] == "C":
            index[category][currency][option_series]["CALLS"].append(symb)
        else:
            index[category][currency][option_series]["PUTS"].append(symb)

        # Add a series of options.

        symbol = (option_series, instrument.market)
        series: Instrument = ws.Instrument.add(symbol)
        series.market = instrument.market
        series.symbol = option_series
        series.ticker = "option!"
        series.category = instrument.category
        series.settlCurrency = instrument.settlCurrency
        series.quoteCoin = instrument.quoteCoin
        series.currentQty = "-"
        series.avgEntryPrice = "-"
        series.unrealisedPnl = "-"
        series.marginCallPrice = "-"
        series.state = instrument.state
        series.volume24h = "-"
        series.expire = instrument.expire
        series.fundingRate = "-"
        series.baseCoin = instrument.baseCoin
        series.precision = instrument.precision
        series.asks = [["-", "-"]]
        series.bids = [["-", "-"]]
        series.price_precision = 1
    else:
        if symb not in index[category][currency]:
            index[category][currency][symb] = {"sort": symb}

    return index


def define_symbol_key(market: str):
    return f"{market}_SYMBOLS"


def set_dotenv(dotenv_path: str, key: str, value: str):
    """
    Updates dotenv file.
    """
    set_key(
        dotenv_path=dotenv_path,
        key_to_set=key,
        value_to_set=value,
    )


def sort_instrument_index(index: OrderedDict) -> OrderedDict:
    """
    Categories and currencies are sorted by name, instruments by the `sort`
    parameter, options are additionally sorted by ascending strike price.
    """
    res = OrderedDict(sorted(index.items(), key=lambda x: x[0]))
    for category, values_category in index.items():
        res[category] = OrderedDict(sorted(values_category.items(), key=lambda x: x[0]))
        for currency, values_currency in res[category].items():
            res[category][currency] = OrderedDict(
                sorted(values_currency.items(), key=lambda x: x[1]["sort"])
            )
            for series, values in res[category][currency].items():
                for key, value in values.items():
                    if key in ["CALLS", "PUTS"]:
                        try:
                            value.sort(
                                key=lambda x: float(x.split("-")[-2].replace("d", "."))
                            )
                        except Exception:
                            try:
                                value.sort(
                                    key=lambda x: float(x.split("-")[-1].split("_")[0])
                                )
                            except Exception:
                                value.sort()
                        res[category][currency][series][key] = value

    return res


def select_option_strikes(index: dict, instrument: Instrument) -> list:
    """
    Extracts all strikes from a series of options.
    """
    series = index[instrument.category][instrument.settlCurrency[0]][instrument.symbol]

    return series["CALLS"] + series["PUTS"]


def load_preferences(root, width, height):
    """
    Load the last remembered params to be used for the terminal appearance
    """
    if not os.path.isfile(var.preferences):
        set_dotenv(
            dotenv_path=var.preferences,
            key="ROOT_WIDTH",
            value=str(width),
        )
        set_dotenv(
            dotenv_path=var.preferences,
            key="ROOT_HEIGHT",
            value=str(height),
        )
        set_dotenv(
            dotenv_path=var.preferences,
            key="ROOT_X_POS",
            value=str(root.winfo_x()),
        )
        set_dotenv(
            dotenv_path=var.preferences,
            key="ROOT_Y_POS",
            value=str(root.winfo_y()),
        )
    return dotenv_values(var.preferences)


def order_form_title():
    if len(var.symbol[0]) > 22:
        return var.symbol[0][:22] + "\n" + var.symbol[0][22:]
    else:
        return var.symbol[0]


def set_emi(symbol: tuple) -> str:
    return ".".join(symbol)


def add_symbol_database(instrument: Instrument, table: str) -> None:
    values = [
        instrument.symbol,
        instrument.market,
        instrument.category,
        instrument.settlCurrency[0],
        instrument.ticker,
        instrument.myMultiplier,
        instrument.multiplier,
        instrument.tickSize,
        instrument.price_precision,
        instrument.minOrderQty,
        instrument.qtyStep,
        instrument.precision,
        instrument.expire,
        instrument.baseCoin,
        instrument.quoteCoin,
        instrument.valueOfOneContract,
    ]
    insert_database(values=values, table=table)


def set_symbol(instrument: Instrument, data: dict) -> None:
    instrument.symbol = data["SYMBOL"]
    instrument.market = data["MARKET"]
    instrument.category = data["CATEGORY"]
    instrument.settlCurrency = (data["CURRENCY"], data["MARKET"])
    instrument.ticker = data["TICKER"]
    instrument.myMultiplier = data["MYMULTIPLIER"]
    instrument.multiplier = data["MULTIPLIER"]
    instrument.tickSize = data["TICKSIZE"]
    instrument.price_precision = data["PRICE_PRECISION"]
    instrument.minOrderQty = data["MINORDERQTY"]
    instrument.qtyStep = data["QTYSTEP"]
    instrument.precision = data["PRECISION"]
    instrument.expire = time_converter(time=data["EXPIRE"])
    instrument.baseCoin = data["BASECOIN"]
    instrument.quoteCoin = data["QUOTECOIN"]
    instrument.valueOfOneContract = data["VALUEOFONECONTRACT"]
