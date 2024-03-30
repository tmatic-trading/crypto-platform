import logging
import os
import time
from collections import OrderedDict
from datetime import datetime

from dotenv import dotenv_values

if not os.path.isfile(".env"):
    print("The .env file does not exist.")
    exit(1)


class Variables:
    orders = OrderedDict()
    position_rows = 0
    account_rows = 0
    env = dotenv_values(".env")
    market_list = env["MARKET_LIST"].replace(",", " ").split()
    CATEGORIES = OrderedDict()
    CATEGORIES["LINEAR"] = "linear"
    CATEGORIES["INVERSE"] = "inverse"
    CATEGORIES["QUANTO"] = "quanto"
    CATEGORIES["SPOT"] = "spot"
    CATEGORIES["OPTION"] = "option"
    for market_name in market_list:
        env[market_name] = dotenv_values(".env." + market_name)
        env[market_name]["SYMBOLS"] = list()
        for CATEGORY, category in CATEGORIES.items():
            tmp = CATEGORY + "_SYMBOLS"
            if tmp in env[market_name]:
                tmp_list = env[market_name][tmp].replace(",", " ").split()
            for symbol in tmp_list:
                env[market_name]["SYMBOLS"] += [(symbol, category)]
        env[market_name]["CURRENCIES"] = (
            env[market_name]["CURRENCIES"].replace(",", " ").split()
        )
        position_rows += len(env[market_name]["SYMBOLS"])
        account_rows += len(env[market_name]["CURRENCIES"])
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
    name_position = [
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
        "CURR",
        "MARGINBAL",
        "AVAILABLE",
        "LEVERAGE",
        "RESULT",
        "COMMISS",
        "FUNDING",
        "CONTROL",
    ]
    name_trade = [
        "TIME",
        "SYMBOL",
        "CAT",
        "EXCH",
        "SIDE",
        "PRICE",
        "QTY",
        "EMI",
    ]
    name_funding = [
        "TIME",
        "SYMBOL",
        "CAT",
        "EXCH",
        "PRICE",
        "PNL",
        "QTY",
        "EMI",
    ]
    name_market = [
        "MARKET",
    ]
    logger = logging
    connect_mysql = None
    cursor_mysql = None
    timefrs = {1: "1m", 5: "5m", 60: "1h"}
    currency_divisor = {"XBt": 100000000, "USDt": 1000000, "BMEx": 1000000, "USDT": 1}
    last_order = int((time.time() - 1591000000) * 10)
    last_database_time = datetime(1900, 1, 1, 1, 1)
    refresh_rate = min(max(100, int(1000 / int(env["REFRESH_RATE"]))), 1000)
    refresh_hour = datetime.utcnow().hour
    robots_thread_is_active = False
