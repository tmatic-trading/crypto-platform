import tkinter as tk

import connect
import functions as function
from bots.variables import Variables as bot
from common.variables import Variables as var
from display.variables import Variables as disp
from ws.init import Variables as ws
from datetime import datetime

disp.root.bind("<F3>", lambda event: terminal_reload(event))
disp.root.bind("<F9>", lambda event: trade_state(event))


def terminal_reload(event) -> None:
    var.thread_is_active = ""
    function.info_display("Restarting...")
    disp.root.update()
    connect.connection()


def trade_state(event) -> None:
    if disp.f9 == "ON":
        disp.f9 = "OFF"
    elif disp.f9 == "OFF":
        disp.f9 = "ON"
        disp.messageStopped = ""
        ws.bitmex.logNumFatal = 0
    print(disp.f9)


def load_labels() -> None:
    # Robots table

    rows = max(disp.num_robots, len(bot.robots) + 1)
    for name in var.name_robots:
        lst = []
        cache = []
        for _ in range(rows):
            lst.append(tk.Label(disp.frame_robots, text=name, pady=0))
            cache.append(name)
        disp.labels["robots"].append(lst)
        disp.labels_cache["robots"].append(cache)
    for row in range(rows):
        for column in range(len(var.name_robots)):
            if row > 0:
                disp.labels["robots"][column][row]["text"] = ""
                disp.labels["robots"][column][row].bind(
                    "<Button-1>",
                    lambda event, row_position=row: function.handler_robots(
                        event, row_position
                    ),
                )
            disp.labels["robots"][column][row].grid(
                row=row, column=column, sticky="N" + "S" + "W" + "E"
            )
            disp.frame_robots.grid_columnconfigure(column, weight=1)
    for row, emi in enumerate(bot.robots):
        if bot.robots[emi]["STATUS"] in ["NOT IN LIST", "OFF", "NOT DEFINED"] or (
            bot.robots[emi]["STATUS"] == "RESERVED" and bot.robots[emi]["POS"] != 0
        ):
            disp.labels["robots"][5][row + 1]["fg"] = "red"
        else:
            disp.labels["robots"][5][row + 1]["fg"] = "#212121"
    function.change_color(color=disp.title_color, container=disp.root)

    # Positions widget

    for row in range(disp.num_pos):
        for column in range(len(var.name_pos)):
            if row == 0:
                disp.labels["position"][column][row].grid(
                    row=row, column=column, sticky="N" + "S" + "W" + "E", padx=1, pady=0
                )
            else:
                disp.labels["position"][column][row].grid(
                    row=row, column=column, sticky="N" + "S" + "W" + "E", padx=1, pady=0
                )
                color = "yellow" if row == 1 else disp.bg_color
                disp.labels["position"][column][row]["text"] = ""
                disp.labels["position"][column][row]["bg"] = color
                disp.labels["position"][column][row].bind(
                    "<Button-1>",
                    lambda event, row_position=row: function.handler_pos(
                        event, row_position
                    ),
                )
            disp.frame_positions.grid_columnconfigure(column, weight=1)

    # Order book table

    num = int(disp.num_book / 2)
    for row in range(disp.num_book):
        for column in range(len(var.name_book)):
            if row == 0:
                disp.labels["orderbook"][column][row].grid(
                    row=row, column=column, sticky="N" + "S" + "W" + "E", padx=1
                )
            else:
                if (row <= num and column == 0) or (row > num and column == 2):
                    disp.labels["orderbook"][column][row]["fg"] = disp.bg_color
                if row <= num and column == 2:
                    disp.labels["orderbook"][column][row]["anchor"] = "w"
                if row > num and column == 0:
                    disp.labels["orderbook"][column][row]["anchor"] = "e"
                disp.labels["orderbook"][column][row].grid(
                    row=row, column=column, sticky="N" + "S" + "W" + "E", padx=1
                )
                disp.labels["orderbook"][column][row]["text"] = ""
                disp.labels["orderbook"][column][row]["bg"] = disp.bg_color
                disp.labels["orderbook"][column][row]["height"] = 1
                disp.labels["orderbook"][column][row].bind(
                    "<Button-1>",
                    lambda row_position=row: function.handler_book(row_position),
                )
            disp.labels["orderbook"][column][row].grid(row=row, column=column)
            disp.frame_3row_3col.grid_columnconfigure(column, weight=1)

    # Account table

    for row in range(disp.num_acc):
        for column in range(len(var.name_acc)):
            if row == 0:
                disp.labels["account"][column][row].grid(
                    row=row, column=column, sticky="N" + "S" + "W" + "E", padx=1, pady=0
                )
            else:
                disp.labels["account"][column][row].grid(
                    row=row, column=column, sticky="N" + "S" + "W" + "E", padx=1, pady=0
                )
                disp.labels["account"][column][row]["text"] = ""
                disp.labels["account"][column][row]["bg"] = disp.bg_color
            disp.labels["account"][column][row].grid(row=row, column=column)
            disp.frame_4row_1_2_3col.grid_columnconfigure(column, weight=1)


def noll(val: str, length: int) -> str:
    r = ""
    for _ in range(length - len(val)):
        r = r + "0"

    return r + val


def info_display(name: str, message: str) -> None:
    t = datetime.utcnow()
    disp.text_info.insert(
        "1.0",
        noll(str(t.hour), 2)
        + ":"
        + noll(str(t.minute), 2)
        + ":"
        + noll(str(t.second), 2)
        + "."
        + noll(str(int(t.microsecond / 1000)), 3)
        + " "
        + message
        + "\n",
    )
    disp.info_display_counter += 1
    if disp.info_display_counter > 40:
        disp.text_info.delete("41.0", "end")