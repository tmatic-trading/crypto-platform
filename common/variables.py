import logging
import os
import queue
import threading
import time
from collections import OrderedDict
from datetime import datetime, timezone


class ListenLogger(logging.Filter):
    def filter(self, record):
        path = record.pathname.replace(os.path.abspath(os.getcwd()), "")[:-3]
        path = path.replace("/", ".")
        path = path.replace("\\", ".")
        if path[0] == ".":
            path = path[1:]
        record.name = path
        return True


def expire_pattern():
    """
    Represents the expire date pattern required for correct sorting of symbols
    having the type 'DDMMMYY'. Contains expire dates for the next 12 + 1 months.
    """
    month_abbr = {
        "JAN": [31, "A", 1],
        "FEB": [29, "B", 2],
        "MAR": [31, "C", 3],
        "APR": [30, "D", 4],
        "MAY": [31, "E", 5],
        "JUN": [30, "F", 6],
        "JUL": [31, "G", 7],
        "AUG": [31, "H", 8],
        "SEP": [30, "I", 9],
        "OCT": [31, "J", 10],
        "NOV": [30, "K", 11],
        "DEC": [31, "L", 12],
    }
    pattern = {}
    this_year = datetime.now().year
    beg_month = datetime.now().month
    end_month = 12
    year_subt = 2000
    for year in range(this_year, this_year + 2):
        if year != this_year:
            end_month = datetime.now().month
        if year - year_subt > 99:
            year_subt += 100
        year -= year_subt
        if year < 10:
            year_str = "0" + str(year)
        else:
            year_str = str(year)
        for month, values in month_abbr.items():
            if values[2] >= beg_month and values[2] <= end_month:
                beg_month = -1
                for day in range(1, values[0] + 1):
                    pattern_in = str(day) + str(month) + year_str
                    pattern_out = year_str + values[1]
                    if day < 10:
                        pattern[pattern_in] = pattern_out + "0" + str(day)
                        pattern["0" + pattern_in] = pattern_out + "0" + str(day)
                    else:
                        pattern[pattern_in] = pattern_out + str(day)

    return pattern


def setup_logger():
    logger = logging.getLogger()
    logger.setLevel(logging.INFO)
    handler = logging.FileHandler("logfile.log")
    ch = logging.StreamHandler()
    formatter = logging.Formatter(
        "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )
    logging.Formatter.converter = time.gmtime
    ch.setFormatter(formatter)
    handler.setFormatter(formatter)
    logger.addHandler(ch)
    logger.addHandler(handler)
    logger.info("\n\nhello\n")
    filter_logger = ListenLogger()
    logger.addFilter(filter_logger)

    return logger


class Variables:
    env = OrderedDict()
    market_list = list()
    current_market = ""
    symbol = ()
    refresh_rate = 5
    order_book_depth = "orderBook 7"
    db_sqlite = "tmatic.db"
    settings = ".env.Settings"
    subscriptions = ".env.Subscriptions"
    preferences = ".env.Preferences"
    logger: logging = setup_logger()
    connect_sqlite = None
    cursor_sqlite = None
    error_sqlite = None
    last_order = int((time.time() - 1591000000) * 10)
    last_database_time = datetime(1900, 1, 1, 1, 1)
    refresh_hour = datetime.now(tz=timezone.utc).hour
    bot_thread_active = dict()
    queue_info = queue.Queue()
    queue_order = queue.Queue()
    queue_reload = queue.Queue()
    lock = threading.Lock()
    lock_kline_update = threading.Lock()
    lock_display = threading.Lock()
    sql_lock = threading.Lock()
    working_directory: str
    kline_update_active = True
    orders = dict()
    timeframe_human_format = OrderedDict(
        [
            ("1min", 1),
            ("2min", 2),
            ("3min", 3),
            ("5min", 5),
            ("10min", 10),
            ("15min", 15),
            ("20min", 20),
            ("30min", 30),
            ("1h", 60),
            ("2h", 120),
            ("3h", 180),
            ("4h", 240),
            ("6h", 360),
            ("12h", 720),
            ("1D", 1440),
        ]
    )
    default_symbol = {
        "Bitmex": [("XBTUSDT", "Bitmex")],
        "Bybit": [("BTCUSDT", "Bybit")],
        "Deribit": [("BTC-PERPETUAL", "Deribit")],
    }
    platform_name = "Tmatic"
    reloading = False
    subscription_res = dict()
    timeout = 7
    select_time = time.time()
    message_response = ""
    unsubscription = set()
    market_object = dict()
    display_bottom: callable
    _series = "_series"
    selected_option = dict()
    rollup_symbol = "cancel"
    selected_iid = dict()
    backtest = False
    backtest_symbols = list()
    database_real = "real_trade"
    database_test = "test_trade"
    database_table: str
    expired_table = "expired"
    backtest_table = "backtest"
    DASH = "-"
    DASH3 = "---"
    NA = "n/a"
    sort_pattern = expire_pattern()