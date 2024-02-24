
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


from functions import Function
from bots.variables import Variables as bot
from common.variables import Variables as var
from display.variables import Variables as disp
from api.websockets import Websockets

from api.variables import Variables



#from API.variables import Variables as API

#from api.api import WS


class Loads(Variables):
    def load_robots(self):
        Loads.clear_params(self)
        bots.Init.load_robots(self)

    def clear_params(self) -> None:
        self.connect_count += 1
        account = self.get_user(self.name)
        if account:
            self.user_id = account["id"]
        else:
            print("A user ID was requested from the exchange but was not received.")
            exit(1)
        for emi, values in self.robots.items():
            self.robot_status[emi] = values["STATUS"]
        self.robots = OrderedDict()
        Function.rounding(self)
        self.frames = dict()

def clear_common_params():
    var.orders = OrderedDict()
    var.orders_dict = OrderedDict()  
    var.current_exchange = var.exchange_list[0]
    var.symbol = var.env[var.current_exchange]["SYMBOLS"][0]
    for values in disp.labels_cache.values():
        for column in values:
            for row in range(len(column)):
                column[row] = ""
        pass



def connection():
    """
    Websocket connection
    """
    clear_common_params()
    common.setup_database_connecion()
    for name, websocket in Websockets.connect.items():
        if name in var.exchange_list:
            while websocket.logNumFatal: 
                websocket.start_ws(name)
                if websocket.logNumFatal:
                    sleep(3)
            Loads.load_robots(websocket)
            if isinstance(bots.Init.init_timeframes(websocket), dict):
                common.Init.load_trading_history(websocket)
                common.Init.account_balances(websocket)


    algo.init_algo()
            #bot_init.load_robots(db=os.getenv("MYSQL_DATABASE"), symbol_list=ws.symbol_list, exchange=name)

    exit(0)


    common_init.setup_database_connecion()
    bot_init.load_robots(db=os.getenv("MYSQL_DATABASE"))



    ws.select["Bitmex"].exit()
    ws.bitmex = None
    while not ws.bitmex:
        var.robots_thread_is_active = ""        
        #ws.bitmex.start_ws("Bitmex")
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
    #var.orders_dict_value = 0
    for emi, values in bot.robots.items():
        bot.robot_status[emi] = values["STATUS"]
    bot.robots = OrderedDict()
    bot.frames = {}
    var.symbol = var.symbol_list[0]
    for values in disp.labels_cache.values():
        for column in values:
            for row in range(len(column)):
                column[row] = ""


def robots_thread() -> None:
    while var.robots_thread_is_active:
        utcnow = datetime.utcnow()
        if bot.frames:
            function.robots_entry(utc=utcnow)
        rest = 1 - time.time() % 1
        time.sleep(rest)