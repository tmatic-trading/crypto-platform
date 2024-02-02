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
from ws.api import Connect
from ws.init import Variables as ws

load_dotenv()


def connection():
    """
    Websocket connection
    """
    if ws.bitmex:
        try:
            ws.bitmex.exit()
        except Exception:
            pass
        ws.bitmex = None
    while not ws.bitmex:
        var.thread_is_active = ""
        ws.bitmex = Connect(
            endpoint=os.getenv("EXCHANGE_API_URL"),
            symbol=var.symbol_list,
            api_key=os.getenv("EXCHANGE_API_KEY"),
            api_secret=os.getenv("EXCHANGE_API_SECRET"),
            info_display=function.info_display,
            order_book_depth=var.order_book_depth,
            instruments=var.instruments,
            format_price = function.format_price,
        )
        if ws.bitmex.logNumFatal == 0:
            common_init.setup_database_connecion()
            clear_params()
            if bot_init.load_robots(db=os.getenv("MYSQL_DATABASE")):
                algo_init.init_algo()
                if isinstance(bot_init.init_timeframes(), dict):
                    common_init.load_trading_history()
                    common_init.initial_mysql(var.user_id)
                    common_init.load_orders()                    
                    common_init.initial_display(var.user_id)
                    var.ticker = ws.bitmex.get_ticker(ticker=var.ticker)
                    var.instruments = ws.bitmex.get_instrument(var.instruments)
                    bot_init.delete_unused_robot()
                    display_init.load_labels()
                    common_init.initial_ticker_values()
                    for emi, value in bot.robot_status.items():
                        bot.robots[emi]["STATUS"] = value
                    var.thread_is_active = "yes"
                    thread = threading.Thread(target=robots_thread)
                    thread.start()
                else:
                    print("Error during loading timeframes.")
                    ws.bitmex.exit()
                    ws.bitmex = None
                    sleep(3)
            else:
                var.logger.info("No robots loaded.")
        else:
            ws.bitmex.exit()
            ws.bitmex = None
            sleep(3)


def refresh() -> None:
    utc = datetime.utcnow()
    if ws.bitmex.logNumFatal > 2000:
        if var.message2000 == "":
            var.message2000 = (
                "Fatal error=" + str(ws.bitmex.logNumFatal) + ". Terminal is frozen"
            )
            function.info_display(var.message2000)
        sleep(1)
    elif ws.bitmex.logNumFatal > 1000 or ws.bitmex.timeoutOccurred != "":  # reload
        connection()
    else:
        if ws.bitmex.logNumFatal > 0 and ws.bitmex.logNumFatal <= 10:
            if var.messageStopped == "":
                var.messageStopped = (
                    "Error=" + str(ws.bitmex.logNumFatal) + ". Trading stopped"
                )
                function.info_display(var.messageStopped)
                if ws.bitmex.logNumFatal == 2:
                    function.info_display("Insufficient available balance!")
            disp.f9 = "OFF"
        var.ticker = ws.bitmex.get_ticker(var.ticker)
        var.instruments = ws.bitmex.get_instrument(instruments=var.instruments)
        while ws.bitmex.get_exec():
            print("+++++++++++++++++", list(ws.bitmex.get_exec().values())[0])
            function.transaction(list(ws.bitmex.get_exec().values())[0])
            ws.bitmex.get_exec().popitem(last=False)
        var.positions = ws.bitmex.get_position(positions=var.positions)
        function.refresh_on_screen(utc=utc)


def clear_params() -> None:
    var.connect_count += 1
    acc = ws.bitmex.get_user()
    if acc:
        var.user_id = acc["id"]
    else:
        print("A user ID was requested from the exchange but was not received.")
        exit(1)
    disp.root.title("Tmatic - Account " + str(var.user_id))
    function.rounding(ws.bitmex.get_instrument(var.instruments))
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
