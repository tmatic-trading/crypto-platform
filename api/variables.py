import logging
from collections import OrderedDict
from datetime import datetime

#import functions as function
from common.variables import Variables as var
import requests



class Variables:
    name = ""
    qwe = 0
    testnet = True
    api_key = ""
    api_secret = ""
    ws_url = ""
    http_url = ""
    symbol_list = list()
    currencies = list()
    accounts = dict()
    ticker = OrderedDict()
    positions = OrderedDict()
    instruments = OrderedDict()
    data = dict()
    full_symbol_list = list()
    logger = logging
    logNumFatal = 401
    depth = var.order_book_depth
    message_counter = 0
    connect_count = 0
    user_id = None
    message_time = datetime.utcnow()
    message2000 = ""
    messageStopped = ""
    maxRetryRest = (3)
    symbol_category = ""
    currency_divisor = dict()

    # Bots data
    robots = OrderedDict()
    frames = dict()
    robot_status = dict()
    
    # Prepare HTTPS session
    session = requests.Session()
    session.headers.update({"user-agent": "Tmatic"})
    session.headers.update({"content-type": "application/json"})
    session.headers.update({"accept": "application/json"})

    '''# HTTP functions
    get_active_instruments = None
    get_user = None
    get_instrument_data = None
    get_position_data = None'''

    # Exchange functions
    transaction = None
    format_price = None
    add_symbol = None

