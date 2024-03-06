import tkinter as tk

from datetime import datetime

import functions
from api.websockets import Websockets
from common.variables import Variables as var
from display.variables import Variables as disp

disp.root.bind("<F3>", lambda event: terminal_reload(event))
disp.root.bind("<F9>", lambda event: trade_state(event))


def terminal_reload(event) -> None:
    var.robots_thread_is_active = ""
    functions.info_display("Restarting...")
    disp.root.update()
    connect.connection()


def trade_state(event) -> None:
    if disp.f9 == "ON":
        disp.f9 = "OFF"
    elif disp.f9 == "OFF":
        disp.f9 = "ON"
        disp.messageStopped = ""
        ws = Websockets.connect[var.current_exchange]
        ws.logNumFatal = 0
    print(var.current_exchange, disp.f9)


def reconfigure_table(widget: tk.Frame, table: str, action: str, number: int):
    """
    Depending on the exchange, you may need a different number of rows in the
    tables, since, for example, you may be subscribed to a different number of
    instruments. Therefore, the number of rows in tables: "account",
    "position", "robots" must change  dynamically. Calling this function
    changes the number of rows in a particular table.

    Input parameters:

    widget - Tkinter object responsible for the table
    table - the name of the table in the the labels array
    action - "new" - add new lines, "delete" - remove lines
    number - number of lines to add or remove
    """
    row = widget.grid_size()[1]
    if action == "new":
        while number:
            if table == "robots":
                create_robot_grid(widget=widget, table=table, row=row)
            row += 1
            number -= 1
    elif action == "delete":
        row -= 1
        while number:
            for r in widget.grid_slaves(row=row):
                r.grid_forget()
            number -= 1
            row -= 1
            if row == 0:
                break


def create_labels(widget: tk.Frame, table: str, names: list, row: int) -> None:
    """
    Generates labels for a table row.
    """
    lst = []
    cache = []
    if len(disp.labels[table]) <= row:
        for name in names:
            lst.append(tk.Label(widget, text=name, pady=0))
            cache.append(name + str(row))
        disp.labels[table].append(lst)
        disp.labels_cache[table].append(cache)


def create_robot_grid(row: int) -> None:
    create_labels(
        widget=disp.frame_robots, table="robots", names=var.name_robots, row=row
    )
    for column in range(len(var.name_robots)):
        if row > 0:
            disp.labels["robots"][row][column].bind(
                "<Button-1>",
                lambda event, row_position=row: functions.handler_robots(
                    event, row_position
                ),
            )
        disp.labels["robots"][row][column].grid(
            row=row, column=column, sticky="N" + "S" + "W" + "E"
        )
        disp.frame_robots.grid_columnconfigure(column, weight=1)


def create_position_grid(row: int) -> None:
    create_labels(
        widget=disp.frame_positions, table="position", names=var.name_pos, row=row
    )
    for column in range(len(var.name_pos)):
        if row == 0:
            disp.labels["position"][row][column].grid(
                row=row, column=column, sticky="N" + "S" + "W" + "E", padx=1, pady=0
            )
        else:
            disp.labels["position"][row][column].grid(
                row=row, column=column, sticky="N" + "S" + "W" + "E", padx=1, pady=0
            )
            color = "yellow" if row == 1 else disp.bg_color
            disp.labels["position"][row][column]["text"] = ""
            disp.labels["position"][row][column]["bg"] = color
            disp.labels["position"][row][column].bind(
                "<Button-1>",
                lambda event, row_position=row: functions.handler_pos(
                    event, row_position
                ),
            )
        disp.frame_positions.grid_columnconfigure(column, weight=1)


def create_account_grid(row: int):
    create_labels(
        widget=disp.frame_4row_1_2_3col, table="account", names=var.name_acc, row=row
    )
    for column in range(len(var.name_acc)):
        if row == 0:
            disp.labels["account"][row][column].grid(
                row=row, column=column, sticky="N" + "S" + "W" + "E", padx=1, pady=0
            )
        else:
            disp.labels["account"][row][column].grid(
                row=row, column=column, sticky="N" + "S" + "W" + "E", padx=1, pady=0
            )
            disp.labels["account"][row][column]["text"] = ""
            disp.labels["account"][row][column]["bg"] = disp.bg_color
        disp.labels["account"][row][column].grid(row=row, column=column)
        disp.frame_4row_1_2_3col.grid_columnconfigure(column, weight=1)


def create_exchange_grid(row: int):
    create_labels(
        widget=disp.frame_exchange, table="exchange", names=var.name_exchange, row=row
    )
    for column in range(len(var.name_exchange)):
        if row == 0:
            disp.labels["exchange"][row][column].grid(
                row=row, column=column, sticky="N" + "S" + "W" + "E", padx=1, pady=0
            )
        else:
            disp.labels["exchange"][row][column].grid(
                row=row, column=column, sticky="N" + "S" + "W" + "E", padx=1, pady=0
            )
            color = "yellow" if row == 1 else disp.bg_color
            disp.labels["exchange"][row][column]["text"] = ""
            disp.labels["exchange"][row][column]["bg"] = color
            disp.labels["exchange"][row][column].bind(
                "<Button-1>",
                lambda event, row_position=row: functions.handler_exchange(
                    event, row_position
                ),
            )
        disp.frame_exchange.grid_columnconfigure(column, weight=1)


def load_labels() -> None:
    
    # Robots table

    ws = Websockets.connect[var.current_exchange]
    rows = max(disp.num_robots, len(ws.robots) + 1)
    for row in range(rows):
        create_robot_grid(row=row)
    for row, emi in enumerate(ws.robots):
        if ws.robots[emi]["STATUS"] in ["NOT IN LIST", "OFF", "NOT DEFINED"] or (
            ws.robots[emi]["STATUS"] == "RESERVED" and ws.robots[emi]["POS"] != 0
        ):
            disp.labels["robots"][row + 1][5]["fg"] = "red"
        else:
            disp.labels["robots"][row + 1][5]["fg"] = "#212121"

    functions.change_color(color=disp.title_color, container=disp.root)

    # Positions table

    for row in range(disp.num_pos):
        create_position_grid(row=row)

    # Order book table

    num = int(disp.num_book / 2)
    for row in range(disp.num_book):
        for column in range(len(var.name_book)):
            if row == 0:
                disp.labels["orderbook"][row][column].grid(
                    row=row, column=column, sticky="N" + "S" + "W" + "E", padx=1
                )
            else:
                if (row <= num and column == 0) or (row > num and column == 2):
                    disp.labels["orderbook"][row][column]["fg"] = disp.bg_color
                if row <= num and column == 2:
                    disp.labels["orderbook"][row][column]["anchor"] = "w"
                if row > num and column == 0:
                    disp.labels["orderbook"][row][column]["anchor"] = "e"
                disp.labels["orderbook"][row][column].grid(
                    row=row, column=column, sticky="N" + "S" + "W" + "E", padx=1
                )
                disp.labels["orderbook"][row][column]["text"] = ""
                disp.labels["orderbook"][row][column]["bg"] = disp.bg_color
                disp.labels["orderbook"][row][column]["height"] = 1
                disp.labels["orderbook"][row][column].bind(
                    "<Button-1>",
                    lambda row_position=row: functions.handler_orderbook(row_position),
                )
            disp.labels["orderbook"][row][column].grid(row=row, column=column)
            disp.orderbook.grid_columnconfigure(column, weight=1)

    # Account table

    for row in range(disp.num_acc):
        create_account_grid(row=row)

    # Exchange table

    for row in range(len(var.exchange_list)+1):
        create_exchange_grid(row=row)


"""def load_robots():

    # Robots table

    print(disp.num_robots)
    rows = 0
    for ws in Websockets.connect.values():
        rows += len(ws.robots)
    rows = max(disp.num_robots, rows + 1)
    print(rows)
    disp.labels["robots"][3][3]["text"] = "LLLL"
    if not disp.frame_robots.grid_slaves(row=2):
        print("+++++++++++++++")
        for column in range(len(var.name_robots)):
            disp.labels["robots"][3][3].grid(
                    row=2, column=column, sticky="N" + "S" + "W" + "E"
              )
    else:
    #if  disp.frame_robots.grid_slaves(row=2):
        for r in disp.frame_robots.grid_slaves(row=2):
            r.grid_forget()
    print(disp.frame_robots.grid_slaves(row=2))
    tm = datetime.utcnow()
    #disp.frame_robots.pack_forget()
    for name in var.name_robots:
        lst = []
        cache = []
        for _ in range(rows):
            lst.append(tk.Label(disp.frame_robots, text="name", pady=0))
            cache.append("name")
        #print(lst)
        #print(" ")
        disp.labels["robots"].append(lst)
        disp.labels_cache["robots"].append(cache)

    for row in range(rows):
        for column in range(len(var.name_robots)):
            if row > 0:
                disp.labels["robots"][column][row]["text"] = ""
                disp.labels["robots"][column][row].bind(
                    "<Button-1>",
                    lambda event, row_position=row: functions.handler_robots(
                        event, row_position
                    ),
                )
            disp.labels["robots"][column][row].grid(
                row=row, column=column, sticky="N" + "S" + "W" + "E"
            )
            #disp.frame_robots.grid_columnconfigure(column, weight=1)
    for ws in Websockets.connect.values():
        for row, emi in enumerate(ws.robots):
            if ws.robots[emi]["STATUS"] in ["NOT IN LIST", "OFF", "NOT DEFINED"] or (
                ws.robots[emi]["STATUS"] == "RESERVED" and ws.robots[emi]["POS"] != 0
            ):
                disp.labels["robots"][5][row + 1]["fg"] = "red"
            else:
                disp.labels["robots"][5][row + 1]["fg"] = "#212121"
    print(datetime.utcnow() - tm)"""