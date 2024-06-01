import threading
import time
from datetime import datetime, timedelta, timezone
from time import sleep

import algo.init as algo
import bots.init as bots
import common.init as common
import functions
import services as service
from api.api import WS, Markets
from api.bitmex.ws import Bitmex
from api.bybit.ws import Bybit
from bots.variables import Variables as bot
from common.variables import Variables as var
from display.functions import info_display
from display.variables import TreeTable
from display.variables import Variables as disp
from functions import Function

disp.root.bind("<F3>", lambda event: terminal_reload(event))
disp.root.bind("<F9>", lambda event: trade_state(event))
Bitmex.transaction = Function.transaction
Bybit.transaction = Function.transaction


def setup():
    """
    This function works the first time you start the program or when you
    reboot after pressing F3. Markets are loaded using setup_market() in
    parallel in threads to speed up the loading process.
    """
    clear_params()
    common.setup_database_connecion()
    var.robots_thread_is_active = False
    threads = []
    for name in var.market_list:
        t = threading.Thread(target=setup_market, args=(Markets[name],))
        threads.append(t)
        t.start()
    [thread.join() for thread in threads]
    for name in var.market_list:
        finish_setup(Markets[name])
    merge_orders()
    functions.load_labels()
    var.robots_thread_is_active = True
    thread = threading.Thread(target=robots_thread)
    thread.start()
    disp.label_f9.config(bg=disp.red_color)


def setup_market(ws: Markets):
    """
    Market reboot. During program operation, when accessing endpoints or
    receiving information from websockets, errors may occur due to the loss of
    the Internet connection or errors for other reasons. If the program
    detects such a case, it reboots the market to restore data integrity.

    The download process may take time, because there are a large number
    of calls to endpoints and websocket subscriptions. To speed up, many calls
    are performed in parallel threads, within which parallel threads can also
    be opened. If any download component is not received, the program will
    restart again from the very beginning.

    The download process is done in stages because the order in which the
    information is received matters. Loading sequence:

    1) All active instruments.
    2) All active orders. After receiving orders, it may happen that the order
       is executed even before the websocket comes up. In this case, the
       websocket will not send execution, but the integrity of the information
       will not be lost, because execution of order will be processed at the
       end of loading in the load_trading_history() function.
    3) Simultaneous download:
        1. Subscribe to websockets only for those instruments that are
           specified in the .env files.
        2. Getting the user id.
        3. Obtaining information on account balances.
        4. Obtaining initial information about the positions of signed
           instruments.
    4) Reading active bots from the database.
    5) Simultaneous download:
        1. Receiving klines only for those instruments and timeframes that are
           used by bots.
        2. Trading history.
    """

    def get_timeframes(ws):
        return bots.Init.init_timeframes(ws)

    def get_history(ws):
        common.Init.load_trading_history(ws)

    ws.logNumFatal = -1
    ws.api_is_active = False
    WS.exit(ws)
    while ws.logNumFatal:
        ws.logNumFatal = WS.start_ws(ws)
        if ws.logNumFatal:
            WS.exit(ws)
            sleep(2)
        else:
            common.Init.clear_params(ws)
            ws.logNumFatal = bots.Init.load_robots(ws)
            if not ws.logNumFatal:
                algo.init_algo(ws)
                try:
                    threads = []
                    t = threading.Thread(target=get_timeframes, args=(ws,))
                    threads.append(t)
                    t.start()
                    t = threading.Thread(target=get_history, args=(ws,))
                    threads.append(t)
                    t.start()
                    [thread.join() for thread in threads]
                except Exception:
                    var.logger.error("The kline data or trade history is not loaded.")
                    ws.logNumFatal = -1
                if not ws.setup_frames:
                    var.logger.info(ws.name + " Error during loading timeframes.")
                    WS.exit(ws)
                    ws.logNumFatal = -1
                    sleep(2)
            else:
                var.logger.info("No robots loaded.")


def merge_orders():
    orders_list = list()
    for name in var.market_list:
        orders_list += Markets[name].orders.values()
    orders_list.sort(key=lambda x: x["transactTime"])
    for order in orders_list:
        var.queue_order.put(order)


def finish_setup(ws: Markets):
    common.Init.load_database(ws)
    common.Init.account_balances(ws)
    common.Init.load_orders(ws, ws.setup_orders)
    bots.Init.delete_unused_robot(ws)
    for emi, value in ws.robot_status.items():
        if emi in ws.robots:
            ws.robots[emi]["STATUS"] = value
    ws.api_is_active = True
    ws.message_time = datetime.now(tz=timezone.utc)


def refresh() -> None:
    while not var.queue_info.empty():
        info = var.queue_info.get()
        info_display(
            name=info["market"],
            message=info["message"],
            tm=info["time"],
            warning=info["warning"],
        )
    while not var.queue_order.empty():
        order = var.queue_order.get()
        ws = Markets[order["MARKET"]]
        clOrdID = order["clOrdID"]
        if "delete" in order:
            if clOrdID in TreeTable.orders.children:
                TreeTable.orders.delete(iid=clOrdID)
        else:
            if clOrdID in ws.orders:
                Function.orders_display(ws, val=order)
    for name in var.market_list:
        ws = Markets[name]
        utc = datetime.now(tz=timezone.utc)
        if ws.logNumFatal == 0:
            if utc > ws.message_time + timedelta(seconds=10):
                if ws.message_counter == 0:
                    info_display(ws.name, "No data within 10 sec", warning=True)
                    WS.ping_pong(ws)
                    ws.message_counter = 1000000000
                elif ws.message_counter == 1000000000:
                    ws.logNumFatal = 1001
                else:
                    ws.message_counter = 0
                ws.message_time = utc
        if ws.logNumFatal > 0:
            if ws.logNumFatal > 2000:
                if ws.message2000 == "":
                    ws.message2000 = (
                        "Fatal error=" + str(ws.logNumFatal) + ". Market is frozen"
                    )
                    Function.market_status(
                        ws, status="Error", message=ws.message2000, error=True
                    )
                sleep(1)
            elif ws.logNumFatal >= 1000 or ws.timeoutOccurred != "":  # reload
                Function.market_status(
                    ws, status="RELOADING...", message="Reloading...", error=True
                )
                TreeTable.market.tree.update()
                setup_market(ws=ws)
                finish_setup(ws=ws)
                merge_orders()
                Function.market_status(ws, status="ONLINE", message="", error=False)
            else:
                if ws.logNumFatal > 0 and ws.logNumFatal <= 10:
                    if ws.messageStopped == "":
                        ws.messageStopped = (
                            "Error=" + str(ws.logNumFatal) + ". Trading stopped"
                        )
                        info_display(name, ws.messageStopped)
                    if ws.logNumFatal == 2:
                        info_display(name, "Insufficient available balance!")
                    disp.f9 = "OFF"
                    disp.label_f9.config(bg=disp.red_color)
                    ws.logNumFatal = 0
    Function.refresh_on_screen(Markets[var.current_market], utc=utc)


def clear_params():
    var.symbol = var.env[var.current_market]["SYMBOLS"][0]
    disp.symb_book = ()


def robots_thread() -> None:
    def bot_in_thread():
        # Bots entry point
        bot.robo[robot["emi"]](
            robot=robot["robot"],
            frame=robot["frame"],
            instrument=robot["instrument"],
        )

    while var.robots_thread_is_active:
        utcnow = datetime.now(tz=timezone.utc)
        bot_list = list()
        for market in var.market_list:
            ws = Markets[market]
            if ws.api_is_active:
                if ws.frames:
                    bot_list = Function.robots_entry(ws, bot_list, utc=utcnow)
        threads = []
        for robot in bot_list:
            t = threading.Thread(target=bot_in_thread)
            threads.append(t)
            t.start()
        [thread.join() for thread in threads]
        rest = 1 - time.time() % 1
        time.sleep(rest)


def terminal_reload(event) -> None:
    var.robots_thread_is_active = ""
    functions.info_display("Tmatic", "Restarting...")
    service.close(Markets)
    disp.root.update()
    setup()


def trade_state(event) -> None:
    if disp.f9 == "ON":
        disp.f9 = "OFF"
        disp.label_f9.config(bg=disp.red_color)
    elif disp.f9 == "OFF":
        disp.f9 = "ON"
        disp.label_f9.config(bg=disp.green_color)
        for market in var.market_list:
            Markets[market].logNumFatal = 0
            print(market, disp.f9)
    disp.label_f9["text"] = disp.f9


def on_closing(root, refresh_var):
    root.after_cancel(refresh_var)
    root.destroy()
    service.close(Markets)
    # os.abort()
