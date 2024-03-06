import platform
import tkinter as tk
from tkinter import ttk
from collections import OrderedDict

from common.variables import Variables as var

if platform.system() == "Windows":
    from ctypes import windll

    windll.shcore.SetProcessDpiAwareness(1)


class Variables:
    root = tk.Tk()
    root.title("Tmatic")
    root.geometry("+50+50")  # 1360x850
    num_robots = 1
    bg_color = "gray98"
    title_color = "gray83"
    num_pos = max(5, var.position_rows + 1)
    num_book = 21  # Must be odd
    num_acc = var.account_rows + 1
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

    # Frame for position table
    frame_positions_sub = tk.Frame(frame_2row_1_2_3col)
    canvas_positions = tk.Canvas(frame_positions_sub, height=50, highlightthickness=0)
    v_positions = tk.Scrollbar(frame_positions_sub, orient="vertical")
    v_positions.pack(side="right", fill="y")
    v_positions.config(command=canvas_positions.yview)
    canvas_positions.config(yscrollcommand=v_positions.set)
    canvas_positions.pack(fill="both", expand=True)
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

    # Frame for the exchange table and the order entry
    frame_3row_1col = tk.Frame()
    frame_exchange_sub = tk.Frame(frame_3row_1col)
    frame_exchange_sub.pack(fill="both", expand=True)
    canvas_exchange = tk.Canvas(frame_exchange_sub, height=210, highlightthickness=0)
    v_exchange = tk.Scrollbar(frame_exchange_sub, orient="vertical")
    v_exchange.pack(side="right", fill="y")
    v_exchange.config(command=canvas_exchange.yview)
    canvas_exchange.config(yscrollcommand=v_exchange.set)
    canvas_exchange.pack(fill="both", expand=True)
    frame_exchange = tk.Frame(canvas_exchange)
    exchange_id = canvas_exchange.create_window(
        (0, 0), window=frame_exchange, anchor="nw"
    )
    canvas_exchange.bind(
        "<Configure>",
        lambda event, id=exchange_id, pos=canvas_exchange: event_width(
            event, id, pos
        ),
    )
    frame_exchange.bind(
        "<Configure>", lambda event, pos=canvas_exchange: event_config(event, pos)
    )
    canvas_exchange.bind(
        "<Enter>", lambda event, canvas=canvas_exchange: on_enter(event, canvas)
    )
    canvas_exchange.bind(
        "<Leave>", lambda event, canvas=canvas_exchange: on_leave(event, canvas)
    )

    # Frame fo the order entry
    frame_entry = tk.Frame(frame_3row_1col)
    frame_entry.pack(fill="both", expand=True)
    label_test = tk.Label(frame_entry, text="Enter orders here")
    label_test.pack()

    # Frame for the order book
    frame_3row_3col = tk.Frame(padx=0, pady=2)

    # Frame for orders and funding
    frame_3row_4col = tk.Frame()

    # Frame for the account table
    frame_4row_1_2_3col = tk.Frame()

    # Frame for the robots table
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

    # Packing service labels

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
    text_info.bind("<Key>", lambda event: text_ignore(event))
    scroll_info.config(command=text_info.yview)
    text_info.config(yscrollcommand=scroll_info.set)
    scroll_info.pack(side="right", fill="y")
    text_info.pack(side="right", fill="both", expand="yes")

    # Positions widget

    labels["position"] = []
    labels_cache["position"] = []

    # Order book table

    labels["orderbook"] = []
    labels_cache["orderbook"] = []    
    for row in range(num_book):
        lst = []
        cache = []
        for name in var.name_book:
            lst.append(tk.Label(frame_3row_3col, text=name, pady=0))
            cache.append(name+str(row))
        labels["orderbook"].append(lst)
        labels_cache["orderbook"].append(cache)

    # Orders widget

    pw_orders_trades = tk.PanedWindow(frame_3row_4col, orient="vertical", sashrelief="raised", bd=0)
    pw_orders_trades.pack(fill="both", expand=True)

    frame_orders = tk.Frame(pw_orders_trades)
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
    text_orders.bind("<Key>", lambda event: text_ignore(event))
    scroll_orders.config(command=text_orders.yview)
    text_orders.config(yscrollcommand=scroll_orders.set)
    scroll_orders.pack(side="right", fill="y")
    text_orders.pack(side="right", fill="both", expand="yes")

    # Trades/Funding widget

    notebook = ttk.Notebook(pw_orders_trades, padding=0)
    style = ttk.Style()
    style.configure("TNotebook", borderwidth=0)
    style.configure("TNotebook.Tab", background=title_color) 
    style.map("TNotebook.Tab", background=[("selected", bg_color)]) 
    notebook.pack(expand=1, fill="both")

    frame_trades = ttk.Frame(notebook)
    frame_trades.pack(fill="both", expand="yes")
    scroll_trades = tk.Scrollbar(frame_trades)
    text_trades = tk.Text(
        frame_trades,
        height=5,
        width=52,
        bg=bg_color,
        highlightthickness=0,
    )
    text_trades.bind("<Key>", lambda event: text_ignore(event))
    scroll_trades.config(command=text_trades.yview)
    text_trades.config(yscrollcommand=scroll_trades.set)
    scroll_trades.pack(side="right", fill="y")
    text_trades.pack(side="right", fill="both", expand="yes")

    frame_funding = tk.Frame(notebook)
    frame_funding.pack(fill="both", expand="yes")
    scroll_funding = tk.Scrollbar(frame_funding)
    text_funding = tk.Text(
        frame_funding,
        height=5,
        width=52,
        bg=bg_color,
        highlightthickness=0,
    )
    text_funding.bind("<Key>", lambda event: text_ignore(event))
    scroll_funding.config(command=text_funding.yview)
    text_funding.config(yscrollcommand=scroll_funding.set)
    scroll_funding.pack(side="right", fill="y")
    text_funding.pack(side="right", fill="both", expand="yes")

    notebook.add(frame_trades, text='Trades')
    notebook.add(frame_funding, text='Funding')
    pw_orders_trades.add(frame_orders)
    pw_orders_trades.add(notebook)
    pw_orders_trades.bind("<Configure>", lambda event: resize_row(event, Variables.pw_orders_trades, 2))

    # Account table

    labels["account"] = []
    labels_cache["account"] = []

    # Robots table

    labels["robots"] = []
    labels_cache["robots"] = []

    # Exchange table
    
    labels["exchange"] = []
    labels_cache["exchange"] = []

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
    var.robots_thread_is_active = ""
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


def text_ignore(event):
    return "break"  # Prevents further handling of the event
def resize_col(event, pw, ratio):
    pw.paneconfig(pw.panes()[0], width=pw.winfo_width() // ratio)
def resize_row(event, pw, ratio):
    pw.paneconfig(pw.panes()[0], height=pw.winfo_height() // ratio)