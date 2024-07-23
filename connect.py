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
from api.deribit.ws import Deribit
from bots.variables import Variables as bot
from common.variables import Variables as var
from display.functions import info_display
from display.variables import TreeTable
from display.variables import Variables as disp
from functions import Function
from display.robots_menu import buttons_menu

disp.root.bind("<F3>", lambda event: terminal_reload(event))
disp.root.bind("<F9>", lambda event: trade_state(event))
Bitmex.transaction = Function.transaction
Bybit.transaction = Function.transaction
Deribit.transaction = Function.transaction
disp.label_f9.config(bg=disp.red_color)


def setup(reload=False):
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
        t = threading.Thread(target=setup_market, args=(Markets[name], reload))
        threads.append(t)
        t.start()
    [thread.join() for thread in threads]
    for name in var.market_list:
        finish_setup(Markets[name])
    merge_orders()
    bots.load_bots()
    buttons_menu.create_bots_menu()
    buttons_menu.show_bot()
    functions.init_tables()
    var.robots_thread_is_active = True
    thread = threading.Thread(target=robots_thread)
    thread.start()


def setup_market(ws: Markets, reload=False):
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

    def get_timeframes(ws, success, num):
        if bots.Init.init_timeframes(ws):
            success[num] = "success"

    def get_history(ws, success, num):
        if common.Init.load_trading_history(ws):
            success[num] = "success"

    ws.logNumFatal = "SETUP"
    ws.api_is_active = False
    if reload:
        WS.exit(ws)
        sleep(3)
    while ws.logNumFatal:
        var.queue_order.put({"action": "clear", "market": ws.name})
        ws.logNumFatal = WS.start_ws(ws)
        if ws.logNumFatal:
            WS.exit(ws)
            sleep(2)
        else:
            common.Init.clear_params(ws)
            ws.logNumFatal = bots.Init.load_robots(ws)
            if not ws.logNumFatal:
                algo.init_algo(ws)
                threads, success = [], []
                success.append(None)
                t = threading.Thread(
                    target=get_timeframes,
                    args=(ws, success, len(success) - 1),
                )
                threads.append(t)
                t.start()
                success.append(None)
                t = threading.Thread(
                    target=get_history,
                    args=(ws, success, len(success) - 1),
                )
                threads.append(t)
                t.start()
                [thread.join() for thread in threads]
                for s in success:
                    if not s:
                        var.logger.error(
                            ws.name + ": The kline data or trade history is not loaded."
                        )
                        ws.logNumFatal = "SETUP"
            else:
                var.logger.info("No robots loaded.")
                sleep(2)
        if ws.logNumFatal:
            var.logger.info("\n\n")
            var.logger.info(
                "Something went wrong. "
                + ws.name
                + " is not loading. See logFile.log. Reboot.\n\n"
            )
            WS.exit(ws)
            sleep(3)


def merge_orders():
    orders_list = list()
    for name in var.market_list:
        orders_list += Markets[name].orders.values()
    orders_list.sort(key=lambda x: x["transactTime"])
    for order in orders_list:
        var.queue_order.put({"action": "put", "order": order})


def finish_setup(ws: Markets):
    """
    This part of the setup does not interact with HTTP, so there is no need to
    load data from different threads to speed up the program and this function
    is executed from the main loop. Moreover, the function uses
    load_database() to fill data into the Treeview tables, which, according to
    Tkinter capabilities, is only possible from the main loop.
    """
    common.Init.load_database(ws)
    common.Init.account_balances(ws)
    common.Init.load_orders(ws, ws.setup_orders)
    bots.Init.delete_unused_robot(ws)
    for emi, value in ws.robot_status.items():
        if emi in ws.robots:
            ws.robots[emi]["STATUS"] = value
    ws.message_time = datetime.now(tz=timezone.utc)
    ws.api_is_active = True


def reload_market(ws: Markets):
    ws.api_is_active = False
    Function.market_status(
        ws, status="RELOADING...", message="Reloading...", error=True
    )
    TreeTable.market.tree.update()
    setup_market(ws=ws, reload=True)
    var.queue_reload.put(ws)


def refresh() -> None:
    while not var.queue_reload.empty():
        ws = var.queue_reload.get()
        finish_setup(ws=ws)
        merge_orders()
        Function.market_status(ws, status="ONLINE", message="", error=False)
        functions.clear_tables()
    while not var.queue_info.empty():
        info = var.queue_info.get()
        info_display(
            name=info["market"],
            message=info["message"],
            tm=info["time"],
            warning=info["warning"],
        )
    while not var.queue_order.empty():
        """
        The queue thread-safely displays current orders that can be queued:
        1. From the websockets of the markets.
        2. When retrieving current orders from the endpoints when loading or
           reloading the market.
        3. When processing the trading history data.

        Possible queue jobs:
        1.     "action": "put"
           Display a row with the new order in the table. If an order with the
           same clOrdID already exists, then first remove it from the table
           and print the order on the first line.
        2.     "action": "delete"
           Delete order by clOrdID.
        3.     "action": "clear"
           Before reloading the market, delete all orders of a particular
           market from the table, because the reboot process will update
           information about current orders, so possibly canceled orders
           during the reloading will be removed.
        """
        job = var.queue_order.get()
        if job["action"] == "delete":
            clOrdID = job["clOrdID"]
            if clOrdID in TreeTable.orders.children:
                TreeTable.orders.delete(iid=clOrdID)
        elif job["action"] == "put":
            order = job["order"]
            clOrdID = order["clOrdID"]
            ws = Markets[order["MARKET"]]
            if clOrdID in ws.orders:
                Function.orders_display(ws, val=order)
        elif job["action"] == "clear":
            TreeTable.orders.clear_all(market=job["market"])

    for name in var.market_list:
        ws = Markets[name]
        utc = datetime.now(tz=timezone.utc)
        if not ws.logNumFatal:
            if ws.api_is_active:
                if utc > ws.message_time + timedelta(seconds=10):
                    if not WS.ping_pong(ws):
                        info_display(
                            ws.name,
                            "The websocket does not respond within 10 sec. Reboot",
                            warning=True,
                        )
                        ws.logNumFatal = "FATAL"  # reboot
                    ws.message_time = utc
        elif ws.logNumFatal == "BLOCK":
            if ws.message2000 == "":
                ws.message2000 = "Fatal error. Trading stopped"
                Function.market_status(
                    ws, status="Error", message=ws.message2000, error=True
                )
            sleep(1)
        elif ws.logNumFatal == "FATAL":  # reboot
            if ws.api_is_active:
                t = threading.Thread(target=reload_market, args=(ws,))
                t.start()
    var.lock_market_switch.acquire(True)
    ws = Markets[var.current_market]
    if ws.api_is_active:
        Function.refresh_on_screen(Markets[var.current_market], utc=utc)
    var.lock_market_switch.release()


def clear_params():
    var.symbol = var.env[var.current_market]["SYMBOLS"][0]


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
    functions.clear_tables()


def trade_state(event) -> None:
    if disp.f9 == "ON":
        disp.f9 = "OFF"
        disp.label_f9.config(bg=disp.red_color)
    elif disp.f9 == "OFF":
        disp.f9 = "ON"
        disp.label_f9.config(bg=disp.green_color)
        for market in var.market_list:
            Markets[market].logNumFatal = ""
            print(market, disp.f9)
    disp.label_f9["text"] = disp.f9


def on_closing(root, refresh_var):
    root.after_cancel(refresh_var)
    root.destroy()
    service.close(Markets)
    # os.abort()
