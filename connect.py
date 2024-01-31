import os
import time
from collections import OrderedDict
from datetime import datetime
from time import sleep
import threading

from dotenv import load_dotenv

import algo.init as algo_init
import bots.init as bot_init
import common.init as common_init
import display.init as display_init
import functions as function
from bots.variables import Variables as bot
from common.variables import Variables as var
from display.variables import Variables as disp
from ws.api import Connect_websocket

load_dotenv()


def connection():
    """
    Websocket connection
    """
    if var.ws:
        try:
            var.ws.exit()
        except Exception:
            pass
        var.ws = None
    while not var.ws:
        var.thread_is_active = ""
        var.ws = Connect_websocket(
            endpoint=os.getenv("EXCHANGE_API_URL"),
            symbol=var.symbol_list,
            api_key=os.getenv("EXCHANGE_API_KEY"),
            api_secret=os.getenv("EXCHANGE_API_SECRET"),
            info_display=function.info_display,
            order_book_depth=var.order_book_depth,
            instruments=var.instruments,
            format_price = function.format_price,
        )
        if var.ws.logNumFatal == 0:
            common_init.setup_database_connecion()
            clear_params()
            if bot_init.load_robots(db=os.getenv("MYSQL_DATABASE")):
                algo_init.init_algo()
                if isinstance(bot_init.init_timeframes(), dict):
                    common_init.load_trading_history()
                    common_init.initial_mysql(var.user_id)
                    common_init.load_orders()                    
                    common_init.initial_display(var.user_id)
                    var.ticker = var.ws.get_ticker(ticker=var.ticker)
                    var.instruments = var.ws.get_instrument(var.instruments)
                    bot_init.delete_unused_robot()
                    display_init.load_labels()
                    common_init.initial_hi_lo_ticker_values()
                    for emi, value in bot.robot_status.items():
                        bot.robots[emi]["STATUS"] = value
                    for emi in bot.robots:
                        bot.robot_pos[emi] = 0
                    var.thread_is_active = "yes"
                    thread = threading.Thread(target=robots_thread)
                    thread.start()
                else:
                    print("Error during loading timeframes.")
                    var.ws.exit()
                    var.ws = None
                    sleep(3)
            else:
                var.logger.info("No robots loaded.")
        else:
            var.ws.exit()
            var.ws = None
            sleep(3)

    return var.ws


def refresh() -> None:
    utc = datetime.utcnow()
    if var.ws.logNumFatal > 2000:
        if var.message2000 == "":
            var.message2000 = (
                "Fatal error=" + str(var.ws.logNumFatal) + ". Terminal is frozen"
            )
            function.info_display(var.message2000)
        sleep(1)
    elif var.ws.logNumFatal > 1000 or var.ws.timeoutOccurred != "":  # reload
        var.ws = connection()
    else:
        if var.ws.logNumFatal > 0 and var.ws.logNumFatal <= 10:
            if var.messageStopped == "":
                var.messageStopped = (
                    "Error=" + str(var.ws.logNumFatal) + ". Trading stopped"
                )
                function.info_display(var.messageStopped)
                if var.ws.logNumFatal == 2:
                    function.info_display("Insufficient available balance!")
            disp.f9 = "OFF"
        var.ticker = var.ws.get_ticker(var.ticker)
        var.instruments = var.ws.get_instrument(instruments=var.instruments)
        function.ticker_hi_lo_minute_price(utc=utc)
        while var.ws.get_exec():
            function.transaction(list(var.ws.get_exec().values())[0])
            var.ws.get_exec().popitem(last=False)
        var.positions = var.ws.get_position(positions=var.positions)
        if utc > var.refresh:
            function.refresh_on_screen(utc=utc, rate=var.refresh_rate)


def clear_params() -> None:
    var.connect_count += 1
    acc = var.ws.get_user()
    if acc:
        var.user_id = acc["id"]
    else:
        print("A user ID was requested from the exchange but was not received.")
        exit(1)
    disp.root.title("Tmatic - Account " + str(var.user_id))
    function.rounding(var.ws.get_instrument(var.instruments))
    var.orders = OrderedDict()
    var.orders_dict = OrderedDict()
    var.orders_dict_value = 0
    for emi, values in bot.robots.items():
        bot.robot_status[emi] = values["STATUS"]
    bot.robots = OrderedDict()
    bot.frames = {}
    bot.framing = {}


def robots_thread() -> None:
    while var.thread_is_active:
        utcnow = datetime.utcnow()
        if bot.frames:
            function.robots_entry(utc=utcnow)
        rest = 1-time.time()%1
        time.sleep(rest)
