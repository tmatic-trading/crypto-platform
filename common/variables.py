import logging
import os
import time
from collections import OrderedDict
from datetime import datetime, timezone

from dotenv import dotenv_values

if not os.path.isfile(".env"):
    print("The .env file does not exist.")
    exit(1)


class Variables:
    orders = OrderedDict()
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
                env[market_name]["SYMBOLS"] += [(symbol, category, market_name)]
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
        "WALLET_BAL",
        "UNRLZD_PNL",
        "MARGIN_BAL",
        "ORDER_MARG",
        "POS_MARG",
        "AVAILABLE",
        "PNL",
        "COMMISS",
        "FUNDING",
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
        "CAT",
        "MARKET",
        "SIDE",
        "PRICE",
        "QTY",
        "EMI",
    ]
    name_funding = [
        "TIME",
        "SYMBOL",
        "CAT",
        "MARKET",
        "PRICE",
        "PNL",
        "QTY",
        "EMI",
    ]
    name_market = [
        "MARKET",
    ]
    logger = logging
    connect_sqlite = None
    cursor_sqlite = None
    error_sqlite = None
    currency_divisor = {
        "XBt": 100000000,
        "USDt": 1000000,
        "BMEx": 1000000,
        "USDT": 1,
        "BTC": 1,
    }
    last_order = int((time.time() - 1591000000) * 10)
    last_database_time = datetime(1900, 1, 1, 1, 1)
    refresh_rate = min(max(100, int(1000 / int(env["REFRESH_RATE"]))), 1000)
    refresh_hour = datetime.now(tz=timezone.utc).hour
    robots_thread_is_active = False
