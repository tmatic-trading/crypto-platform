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
    symbol = ""
    refresh_rate = 5
    order_book_depth = "orderBook"
    db_sqlite = "tmatic.db"
    settings = ".env.Settings"
    subscriptions = ".env.Subscriptions"
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
    reloading = False
    subscription_res = dict()
    timeout = 7
    select_time = time.time()
    message_response = ""
    unsubscription = set()
    market_object = dict()
    display_bottom: callable
    _series = "_series"
