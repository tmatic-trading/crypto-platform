import logging
from collections import OrderedDict
from datetime import datetime

#from functions import Function
from common.variables import Variables as var



class Variables():
    #name = ""
    qwe = 0
    testnet = True
    api_key = ""
    api_secret = ""
    ws_url = ""
    http_url = ""
    symbol_list = list()
    category_list = list()
    currencies = list()
    accounts = dict()
    ticker = OrderedDict()
    positions = OrderedDict()
    instruments = OrderedDict()
    data = dict()
    full_symbol_list = list()
    logger = logging
    logNumFatal = -1
    timeoutOccurred = ""
    depth = var.order_book_depth
    message_counter = 0
    message_point = 0
    connect_count = 0
    user_id = None
    user = dict()
    message_time = datetime.utcnow()
    message2000 = ""
    messageStopped = ""
    maxRetryRest = (3)
    symbol_category = ""
    currency_divisor = dict()
    filename = ""
    api_is_active = False

    # Bots data
    robots = OrderedDict()
    frames = dict()
    robot_status = dict()






