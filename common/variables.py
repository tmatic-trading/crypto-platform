import logging
import os
import queue
import threading
import time
from collections import OrderedDict
from datetime import datetime, timezone

from dotenv import dotenv_values

if not os.path.isfile(".env"):
    print("The .env file does not exist.")
    exit(1)


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
    env = dotenv_values(".env")
    market_list = env["MARKET_LIST"].replace(",", " ").split()
    CATEGORIES = OrderedDict()
    '''CATEGORIES["LINEAR"] = "linear"
    CATEGORIES["INVERSE"] = "inverse"
    CATEGORIES["QUANTO"] = "quanto"
    CATEGORIES["SPOT"] = "spot"
    CATEGORIES["OPTION"] = "option"
    CATEGORIES["FUTURE_LINEAR"] = "future linear"
    CATEGORIES["FUTURE_REVERSED"] = "future reversed"
    CATEGORIES["FUTURE_COMBO_REVERSED"] = "future_combo reversed"
    CATEGORIES["SPOT_LINEAR"] = "spot linear"
    CATEGORIES["OPTION_LINEAR"] = "option linear"
    CATEGORIES["OPTION_REVERSED"] = "option reversed"
    CATEGORIES["OPTION_COMBO_REVERSED"] = "option"'''
    for market_name in market_list:
        env[market_name] = dotenv_values(".env." + market_name)
        symbols = env[market_name]["SYMBOLS"].replace(",", " ").split()
        env[market_name]["SYMBOLS"] = list()
        for symb in symbols:
            env[market_name]["SYMBOLS"].append((symb, market_name))
        """env[market_name]["SYMBOLS"] = list()
        for CATEGORY, category in CATEGORIES.items():
            tmp = CATEGORY + "_SYMBOLS"
            tmp_list = []
            if tmp in env[market_name]:
                tmp_list = env[market_name][tmp].replace(",", " ").split()
            for symbol in tmp_list:
                add_symbol = (symbol, category, market_name)
                if add_symbol not in env[market_name]["SYMBOLS"]:
                    env[market_name]["SYMBOLS"] += [add_symbol]"""
        env[market_name]["CURRENCIES"] = (
            env[market_name]["CURRENCIES"].replace(",", " ").split()
        )
    if env["ORDER_BOOK_DEPTH"] == "orderBook":
        order_book_depth = "orderBook"
    else:
        order_book_depth = "quote"
    current_market = market_list[0]
    symbol = env[current_market]["SYMBOLS"][0]
    name_book = ["QTY", "PRICE", "QTY"]
    name_robots = [
        "EMI",
        "SYMBOL",
        "CATEGORY",
        "CURRENCY",
        "TIMEFR",
        "CAPITAL",
        "STATUS",
        "VOL",
        "PNL",
        "POS",
    ]
    name_instruments = [
        "symbol",
        "state",
        "maxPrice",
        "fundingRate",
        "tickSize",
        "lowPrice",
        "highPrice",
        "volume24h",
        "lotSize",
    ]
    name_instrument = [
        "SYMBOL",
        "CAT",
        "POS",
        "ENTRY",
        "PNL",
        "MCALL",
        "STATE",
        "VOL24h",
        "EXPIRY",
        "FUND",
    ]
    name_account = [
        "MARKET",
        "CURRENCY",
        "WALLET_BAL",
        "UNRLZD_PNL",
        "MARGIN_BAL",
        "ORDER_MARG",
        "POS_MARG",
        "AVAILABLE",
    ]
    name_trade = [
        "TIME",
        "SYMBOL",
        "CAT",
        "MARKET",
        "SIDE",
        "PRICE",
        "QTY",
        "EMI",
    ]
    name_order = [
        "TIME",
        "SYMBOL",
        "CATEGORY",
        "MARKET",
        "SIDE",
        "PRICE",
        "QTY",
        "EMI",
    ]
    name_funding = [
        "TIME",
        "SYMBOL",
        "CATEGORY",
        "MARKET",
        "PRICE",
        "PNL",
        "QTY",
        "EMI",
    ]
    name_market = [
        "MARKET",
    ]
    name_results = [
        "MARKET",
        "CURRENCY",
        "PNL SUM",
        "COMMISSION SUM",
        "FUNDING SUM",
    ]
    name_position = [
        "MARKET",
        "BOT NAME",
        "SYMBOL",
        "CATEGORY",
        "POSITION",
        "VOLUME",
        "PNL",
    ]
    name_bots = [
        "BOT NAME",
        "TIMEFR",
        "STATUS",
        "UPDATED",
    ]
    name_bot_menu = ["AVAILABLE BOTS"]
    name_bot = [
        "BOT NAME",
        "TIMEFR",
        "STATE",
        "UPDATED",
        "CREATED",
    ]
    name_bot_position = [
        "MARKET",
        "SYMBOL",
        "CATEGORY",
        "POSITION",
        "VOLUME",
        "PNL",
    ]
    name_bot_trade = [
        "TIME",
        "SYMBOL",
        "CATEGORY",
        "MARKET",
        "SIDE",
        "PRICE",
        "QTY",
        "BOT NAME",
    ]
    name_bot_order = [
        "TIME",
        "SYMBOL",
        "CATEGORY",
        "MARKET",
        "SIDE",
        "PRICE",
        "QTY",
        "BOT NAME",
    ]
    name_bot_results = [
        "MARKET",
        "CURRENCY",
        "PNL SUM",
        "COMMISSION SUM",
    ]
    logger: logging = setup_logger()
    connect_sqlite = None
    cursor_sqlite = None
    error_sqlite = None
    last_order = int((time.time() - 1591000000) * 10)
    last_database_time = datetime(1900, 1, 1, 1, 1)
    refresh_rate = min(max(100, int(1000 / int(env["REFRESH_RATE"]))), 1000)
    refresh_hour = datetime.now(tz=timezone.utc).hour
    robots_thread_is_active = False
    queue_info = queue.Queue()
    queue_order = queue.Queue()
    queue_reload = queue.Queue()
    lock = threading.Lock()
    lock_market_switch = threading.Lock()
    sql_lock = threading.Lock()
    working_directory: str
