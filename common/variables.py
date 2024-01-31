import os
import time
from collections import OrderedDict
from datetime import datetime

from dotenv import load_dotenv

from ws.api import Connect_websocket

load_dotenv()

if not os.path.isfile(".env"):
    print("The .env file does not exist.")
    exit(1)


class Variables:
    tm = datetime.utcnow()
    symbol_list = os.getenv("SYMBOLS").replace(",", " ").split()
    currencies = os.getenv("CURRENCIES").replace(",", " ").split()
    name_book = ["    QTY   ", "   PRICE    ", "    QTY    "]
    name_robots = [
        "EMI",
        "SYMB",
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
    name_pos = [
        "SYMB",
        "POS",
        "ENTRY",
        "PNL",
        "MCALL",
        "STATE",
        "VOL24h",
        "EXPIRY",
        "FUND",
    ]
    name_acc = [
        "CURR",
        "MARGINBAL",
        "AVAILABLE",
        "LEVERAGE",
        "RESULT",
        "COMMISS",
        "FUNDING",
        "CONTROL",
    ]
    accounts = dict()
    ticker = OrderedDict()
    positions = OrderedDict()
    instruments = OrderedDict()
    tmp_pos = {y: 0 for y in name_pos}
    tmp_instr = {y: 0 for y in name_instruments}
    for symbol in symbol_list:
        ticker[symbol] = {
            "bid": 0,
            "ask": 0,
            "bidSize": 0,
            "askSize": 0,
            "open_bid": 0,
            "open_ask": 0,
            "hi": 0,
            "lo": 0,
            "time": tm,
        }
        positions[symbol] = tmp_pos.copy()
        instruments[symbol] = tmp_instr.copy()
    symbol = symbol_list[0]
    for cur in currencies:
        accounts[cur] = {y: 0 for y in name_acc}
        accounts[cur]["SUMREAL"] = 0
    ws = Connect_websocket
    connect_count = 0
    logger = None
    connect_mysql = None
    cursor_mysql = None
    orders = OrderedDict()
    user_id = None
    orders_dict = OrderedDict()
    orders_dict_value = 0
    timefrs = {1: "1m", 5: "5m", 60: "1h"}
    currency_divisor = {"XBt": 100000000, "USDt": 1000000, "BMEx": 1000000}
    last_order = int((time.time() - 1591000000) * 10)
    last_database_time = datetime(1900, 1, 1, 1, 1)
    message_time = datetime.utcnow()
    refresh = message_time
    refresh_rate = max(min(10, int(os.getenv("REFRESH_RATE"))), 1)
    refresh_minute = message_time.minute
    refresh_hour = message_time.hour
    message_point = 0
    message2000 = ""
    messageStopped = ""
    if os.getenv("ORDER_BOOK_DEPTH") == "orderBook10":
        order_book_depth = "orderBook10"
    else:
        order_book_depth = "quote"
    thread_is_active = ""
