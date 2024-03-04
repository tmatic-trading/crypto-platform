
import os
import threading
import time
from collections import OrderedDict
from datetime import datetime
from time import sleep

import algo.init as algo
import bots.init as bots
import common.init as common
import display.init as display
import functions


from functions import Function
from bots.variables import Variables as bot
from common.variables import Variables as var
from display.variables import Variables as disp
from api.websockets import Websockets

from api.api import WS


def setup():
    WS.transaction = Function.transaction
    clear_params()
    common.setup_database_connecion()
    var.robots_thread_is_active = ""
    for name, ws in Websockets.connect.items():
        if name in var.exchange_list:
            setup_exchange(ws, name=name)
    common.Init.initial_display(ws)
    display.load_labels()
    algo.init_algo()
    var.robots_thread_is_active = "yes"
    thread = threading.Thread(target=robots_thread)
    thread.start()


def setup_exchange(ws: WS, name: str):
    while ws.logNumFatal:
        ws.start_ws(name)
        if ws.logNumFatal:
            ws.exit(name)
            sleep(2)
        else:
            account = ws.get_user(name)            
            if account:
                ws.user_id = account["id"]
            else:
                raise Exception("A user ID was requested from the \
                                exchange but was not received.")
            common.Init.clear_params(ws)
            if bots.Init.load_robots(ws):
                if isinstance(bots.Init.init_timeframes(ws), dict):
                    common.Init.load_trading_history(ws)
                    common.Init.account_balances(ws)
                    common.Init.load_orders(ws)
                    ws.ticker = ws.get_ticker(name)
                    bots.Init.delete_unused_robot(ws)
                    common.Init.initial_ticker_values(ws)
                    for emi, value in ws.robot_status.items():
                        ws.robots[emi]["STATUS"] = value
                else:
                    print("Error during loading timeframes.")
                    ws.exit(name)
                    ws.logNumFatal = -1
                    sleep(2)
            else:
                var.logger.info("No robots loaded.")


def refresh() -> None:
    for name in var.exchange_list:
        ws = Websockets.connect[name]
        utc = datetime.utcnow()
        if ws.logNumFatal > 2000:
            if ws.message2000 == "":
                ws.message2000 = (
                    "Fatal error=" + str(ws.logNumFatal) + ". Terminal is frozen"
                )
                Function.info_display(ws, ws.message2000)
            sleep(1)
        elif ws.logNumFatal > 1000 or ws.timeoutOccurred != "":  # reload
            setup_exchange(ws=ws, name=name)
        else:
            if ws.logNumFatal > 0 and ws.logNumFatal <= 10:
                if ws.messageStopped == "":
                    ws.messageStopped = (
                        "Error=" + str(ws.logNumFatal) + ". Trading stopped"
                    )
                    Function.info_display(ws, ws.messageStopped)
                    if ws.logNumFatal == 2:
                        Function.info_display(ws, "Insufficient available balance!")
                disp.f9 = "OFF"
            ws.ticker = ws.get_ticker(name=name)            
            '''disp.num_robots -= 1
            #if disp.num_robots != 100:
            #    disp.num_robots = 100
            from datetime import timedelta
            tm = datetime.utcnow()
            if not var.tmm:
                var.tmm = tm
            if tm - var.tmm > timedelta(seconds=1):
            #if not var.tmm:
                print(tm.second, tm.second%5)
                functions.clear_labels_cache()
                display.load_robots()
                var.tmm = tm'''
            Function.refresh_on_screen(ws, utc=utc)

    
def clear_params():
    var.orders = OrderedDict()
    var.orders_dict = OrderedDict()  
    var.current_exchange = var.exchange_list[0]
    var.symbol = var.env[var.current_exchange]["SYMBOLS"][0]
    functions.clear_labels_cache()


def robots_thread() -> None:
    while var.robots_thread_is_active:
        utcnow = datetime.utcnow()        
        for name, ws in Websockets.connect.items():
            if name in var.exchange_list:
                if ws.frames:
                    Function.robots_entry(ws, utc=utcnow)
        rest = 1 - time.time() % 1
        time.sleep(rest)