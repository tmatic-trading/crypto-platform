import logging
from collections import OrderedDict
from datetime import datetime, timezone

import requests


class Variables:
    name: str
    qwe = 0
    testnet = True
    api_key = ""
    api_secret = ""
    ws_url = ""
    http_url = ""
    symbol_list = list()
    category_list = list()
    positions = OrderedDict()
    logger = logging
    logNumFatal = ""
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
    session: requests.Session
