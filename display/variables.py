import platform
import tkinter as tk
from collections import OrderedDict

from common.variables import Variables as var

if platform.system() == "Windows":
    from ctypes import windll

    windll.shcore.SetProcessDpiAwareness(1)


class Variables:
    root = tk.Tk()
    root.title("COIN DEALER")
    root.geometry("+50+50")  # 1360x850
    num_robots = 15
    bg_color = "gray98"
    title_color = "gray83"
    num_pos = max(5, len(var.symbol_list) + 1)
    num_book = 21  # Must be odd
    num_acc = len(var.currencies) + 1
    frame_state = tk.Frame()
    labels = dict()
    labels_cache = dict()
    label_trading = tk.Label(frame_state, text="  TRADING: ")
    label_f9 = tk.Label(frame_state, text="OFF", fg="white")
    label_state = tk.Label(frame_state, text="  STATE: ")
    label_online = tk.Label(frame_state, fg="white")
    label_time = tk.Label()
    frame_2row_1_2_3col = tk.Frame()
    frame_information = tk.Frame(frame_2row_1_2_3col)
    frame_positions_sub = tk.Frame(frame_2row_1_2_3col)

    canvas_positions = tk.Canvas(frame_positions_sub, height=50, highlightthickness=0)
    v_positions = tk.Scrollbar(frame_positions_sub, orient="vertical")
    v_positions.pack(side="right", fill="y")
    v_positions.config(command=canvas_positions.yview)
    canvas_positions.config(yscrollcommand=v_positions.set)
    canvas_positions.pack(fill="both", expand=True)
    # Frame for position table
    frame_positions = tk.Frame(canvas_positions)
    positions_id = canvas_positions.create_window(
        (0, 0), window=frame_positions, anchor="nw"
    )
    canvas_positions.bind(
        "<Configure>",
        lambda event, id=positions_id, pos=canvas_positions: event_width(
            event, id, pos
        ),
    )
    frame_positions.bind(
        "<Configure>", lambda event, pos=canvas_positions: event_config(event, pos)
    )
    canvas_positions.bind(
        "<Enter>", lambda event, canvas=canvas_positions: on_enter(event, canvas)
    )
    canvas_positions.bind(
        "<Leave>", lambda event, canvas=canvas_positions: on_leave(event, canvas)
    )

    # Frame for trades
    frame_3row_1col = tk.Frame()
    # frame for order book
    frame_3row_3col = tk.Frame(padx=0, pady=2)
    # Frame for orders and funding
    frame_3row_4col = tk.Frame()
    # Frame for the account table
    frame_4row_1_2_3col = tk.Frame()
    frame_5row_1_2_3_4col = tk.Frame()

    canvas_robots = tk.Canvas(frame_5row_1_2_3_4col, height=210, highlightthickness=0)
    v_robots = tk.Scrollbar(frame_5row_1_2_3_4col, orient="vertical")
    v_robots.pack(side="right", fill="y")
    v_robots.config(command=canvas_robots.yview)
    canvas_robots.config(yscrollcommand=v_robots.set)
    canvas_robots.pack(fill="both", expand=True)
    frame_robots = tk.Frame(canvas_robots)
    robots_id = canvas_robots.create_window((0, 0), window=frame_robots, anchor="nw")
    canvas_robots.bind(
        "<Configure>",
        lambda event, id=robots_id, can=canvas_robots: event_width(event, id, can),
    )
    frame_robots.bind(
        "<Configure>", lambda event, can=canvas_robots: event_config(event, can)
    )
    canvas_robots.bind(
        "<Enter>", lambda event, canvas=canvas_robots: on_enter(event, canvas)
    )
    canvas_robots.bind(
        "<Leave>", lambda event, canvas=canvas_robots: on_leave(event, canvas)
    )

    frame_state.grid(row=0, column=0, sticky="W")
    label_state.pack(side="left")
    label_online.pack(side="left")
    label_trading.pack(side="left")
    label_f9.pack(side="left")

    # Place labels and frames into the grid

    label_time.grid(row=0, column=1, sticky="E", columnspan=2)
    frame_2row_1_2_3col.grid(
        row=1, column=0, sticky="N" + "S" + "W" + "E", columnspan=3
    )
    frame_information.grid(row=0, column=0, sticky="N" + "S" + "W" + "E")
    frame_positions_sub.grid(
        row=0, column=1, sticky="N" + "S" + "W" + "E", padx=1, pady=0
    )
    frame_3row_1col.grid(row=2, column=0, sticky="N" + "S" + "W" + "E")
    frame_3row_3col.grid(row=2, column=1, sticky="N" + "S" + "W" + "E")
    frame_3row_4col.grid(row=2, column=2, sticky="N" + "S" + "W" + "E", rowspan=2)
    frame_4row_1_2_3col.grid(
        row=3, column=0, sticky="S" + "W" + "E", columnspan=2, padx=0, pady=0
    )
    frame_5row_1_2_3_4col.grid(
        row=4, column=0, sticky="N" + "S" + "W" + "E", columnspan=3
    )

    # Grid alignment

    root.grid_columnconfigure(0, weight=1)
    root.grid_columnconfigure(1, weight=1)
    root.grid_columnconfigure(2, weight=1)
    frame_2row_1_2_3col.grid_columnconfigure(0, weight=1)
    frame_2row_1_2_3col.grid_columnconfigure(1, weight=1)

    # Information widget

    scroll_info = tk.Scrollbar(frame_information)
    text_info = tk.Text(
        frame_information,
        height=6,
        width=30,
        bg=bg_color,
        highlightthickness=0,
    )
    scroll_info.config(command=text_info.yview)
    text_info.config(yscrollcommand=scroll_info.set)
    scroll_info.pack(side="right", fill="y")
    text_info.pack(side="right", fill="both", expand="yes")

    # Positions widget

    labels["position"] = []
    labels_cache["position"] = []
    for name in var.name_pos:
        lst = []
        cache = []
        for _ in range(num_pos):
            lst.append(tk.Label(frame_positions, text=name))
            cache.append(name)
        labels["position"].append(lst)
        labels_cache["position"].append(cache)

    # Trades widget

    scroll_trades = tk.Scrollbar(frame_3row_1col)
    text_trades = tk.Text(
        frame_3row_1col,
        height=5,
        width=38,
        bg=bg_color,
        highlightthickness=0,
    )
    scroll_trades.config(command=text_trades.yview)
    text_trades.config(yscrollcommand=scroll_trades.set)
    scroll_trades.pack(side="right", fill="y")
    text_trades.pack(side="right", fill="both", expand="yes")

    # Order book table

    labels["orderbook"] = []
    labels_cache["orderbook"] = []
    for name in var.name_book:
        lst = []
        cache = []
        for _ in range(num_book):
            lst.append(tk.Label(frame_3row_3col, text=name, pady=0))
            cache.append(name)
        labels["orderbook"].append(lst)
        labels_cache["orderbook"].append(cache)

    # Orders widget

    frame_orders = tk.Frame(frame_3row_4col)
    frame_orders.pack(fill="both", expand="yes")
    scroll_orders = tk.Scrollbar(frame_orders)
    text_orders = tk.Text(
        frame_orders,
        height=5,
        width=52,
        bg=bg_color,
        cursor="arrow",
        highlightthickness=0,
    )
    scroll_orders.config(command=text_orders.yview)
    text_orders.config(yscrollcommand=scroll_orders.set)
    scroll_orders.pack(side="right", fill="y")
    text_orders.pack(side="right", fill="both", expand="yes")

    # Funding widget

    frame_funding = tk.Frame(frame_3row_4col)
    frame_funding.pack(fill="both", expand="yes")
    scroll_funding = tk.Scrollbar(frame_funding)
    text_funding = tk.Text(
        frame_funding,
        height=5,
        width=52,
        bg=bg_color,
        highlightthickness=0,
    )
    scroll_funding.config(command=text_funding.yview)
    text_funding.config(yscrollcommand=scroll_funding.set)
    scroll_funding.pack(side="right", fill="y")
    text_funding.pack(side="right", fill="both", expand="yes")

    # Account table

    labels["account"] = []
    labels_cache["account"] = []
    for name in var.name_acc:
        lst = []
        cache = []
        for _ in range(num_acc):
            lst.append(tk.Label(frame_4row_1_2_3col, text=name))
            cache.append(name)
        labels["account"].append(lst)
        labels_cache["account"].append(cache)

    # Robots table

    labels["robots"] = []
    labels_cache["robots"] = []

    refresh_var = None
    nfo_display_counter = 0
    f9 = "OFF"
    messageStopped = ""
    robots_window_trigger = "off"
    info_display_counter = 0
    trades_display_counter = 0
    funding_display_counter = 0
    symb_book = ""
    book_window_trigger = "off"
    price_rounding = OrderedDict()
    orders_dict_value = 0
    order_window_trigger = "off"


def handler_robots(y_pos):
    print(y_pos)


def on_closing(root, refresh_var):
    var.thread_is_active = ""
    root.after_cancel(refresh_var)
    root.destroy()


def event_width(event, canvas_id, canvas_event):
    canvas_event.itemconfig(canvas_id, width=event.width)


def event_config(event, canvas_event):
    canvas_event.configure(scrollregion=canvas_event.bbox("all"))


def on_enter(event, canvas_event):
    if platform.system() == "Linux":
        canvas_event.bind_all(
            "<Button-4>",
            lambda event, canvas=canvas_event: robots_on_mousewheel(event, canvas),
        )
        canvas_event.bind_all(
            "<Button-5>",
            lambda event, canvas=canvas_event: robots_on_mousewheel(event, canvas),
        )
    else:
        canvas_event.bind_all(
            "<MouseWheel>",
            lambda event, canvas=canvas_event: robots_on_mousewheel(event, canvas),
        )


def on_leave(event, canvas_event):
    if platform.system() == "Linux":
        canvas_event.unbind_all("<Button-4>")
        canvas_event.unbind_all("<Button-5>")
    else:
        canvas_event.unbind_all("<MouseWheel>")


def robots_on_mousewheel(event, canvas_event):
    if platform.system() == "Windows":
        canvas_event.yview_scroll(int(-1 * (event.delta / 120)), "units")
    elif platform.system() == "Darwin":
        canvas_event.yview_scroll(int(-1 * event.delta), "units")
    else:
        if event.num == 4:
            canvas_event.yview_scroll(-1, "units")
        elif event.num == 5:
            canvas_event.yview_scroll(1, "units")
