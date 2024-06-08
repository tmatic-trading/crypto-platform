import logging
from collections import OrderedDict
from datetime import datetime, timezone

from common.variables import Variables as var


class Variables:
    qwe = 0
    testnet = True
    api_key = ""
    api_secret = ""
    ws_url = ""
    http_url = ""
    symbol_list = list()
    category_list = list()
    currencies = list()
    positions = OrderedDict()
    full_symbol_list = list()
    logger = logging
    logNumFatal = 0
    timeoutOccurred = ""
    depth = var.order_book_depth
    connect_count = 0
    user_id = None
    user = dict()
    message_time = datetime.now(tz=timezone.utc)
    message2000 = ""
    messageStopped = ""
    maxRetryRest = 3
    symbol_category = ""
    currency_divisor = dict()
    filename = ""
    api_is_active = False
