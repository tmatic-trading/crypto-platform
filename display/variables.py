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

    '''# Packing service labels

    frame_state.grid(row=0, column=0, sticky="W")
    label_state.pack(side="left")
    label_online.pack(side="left")
    label_trading.pack(side="left")
    label_f9.pack(side="left")'''

    # Create labels, frames, tables and the grid

    label_time = tk.Label()
    label_time.grid(row=0, column=0, sticky="E")
    frame_row1 = tk.Frame(root, borderwidth=1, bg=bg_color, height=70)
    frame_row1.grid(row=1, column=0, sticky="N" + "S" + "W" + "E")
    pw_1row = tk.PanedWindow(frame_row1, orient="horizontal", sashrelief="raised", bd=0)
    pw_1row.pack(fill="both", expand=True)

    # Information widget

    text_info = tk.Text(pw_1row, cursor="arrow", bg=bg_color, highlightthickness=0,)
    text_info.bind("<Key>", lambda event: text_ignore(event))
    scroll_info = tk.Scrollbar(text_info)
    scroll_info.config(command=text_info.yview)
    text_info.config(yscrollcommand=scroll_info.set)
    scroll_info.pack(side="right", fill="y")
    text_info.pack(side="left", fill="both", expand=True)

    # Positions widget

    frame_positions_sub = tk.Frame(pw_1row, cursor="arrow", bg=bg_color, highlightthickness=0,) # frame_2row_1_2_3col
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

    # Positions table

    labels["position"] = []
    labels_cache["position"] = []

    pw_1row.add(text_info)
    pw_1row.add(frame_positions_sub)
    pw_1row.bind("<Configure>", lambda event: resize_col(event, pw_1row, 2))

    frame_row2 = tk.Frame(root, borderwidth=1, bg=bg_color)
    frame_row2.grid(row=2, column=0, sticky="N" + "S" + "W" + "E")
    pw_2row = tk.PanedWindow(frame_row2, orient="vertical", sashrelief="raised", bd=0)
    pw_2row.pack(fill="both", expand=True)

    main_frame = tk.Frame(pw_2row, cursor="arrow", bg=bg_color, highlightthickness=0,)
    main_frame.pack(side="left", fill="both", expand=True)

    main_col0 = tk.Frame(main_frame, borderwidth=0)
    main_col0.grid(row=0, column=0, sticky="N" + "S" + "W" + "E")

    main_col0_row0 = tk.Frame(main_col0, borderwidth=0)
    main_col0_row0.grid(row=0, column=0, sticky="N" + "S" + "W" + "E")
    main_col0_row0_col0 = tk.Frame(main_col0_row0, borderwidth=0)
    main_col0_row0_col0.grid(row=0, column=0, sticky="N" + "S" + "W" + "E")

    pw_orders_trades = tk.PanedWindow(main_col0_row0_col0, orient="vertical", sashrelief="raised", bd=0)
    pw_orders_trades.pack(fill="both", expand=True)

    # Orders widget

    text_orders = tk.Text(pw_orders_trades, cursor="arrow", highlightthickness=0,)
    text_orders.bind("<Key>", lambda event: text_ignore(event))
    scroll_orders = tk.Scrollbar(text_orders)
    scroll_orders.config(command=text_orders.yview)
    text_orders.config(yscrollcommand=scroll_orders.set)
    scroll_orders.pack(side="right", fill="y")
    text_orders.pack(side="left", fill="both", expand=True)

    notebook = ttk.Notebook(pw_orders_trades)
    style = ttk.Style()
    style.configure("TNotebook", background=title_color, borderwidth=0)
    style.configure("TNotebook.Tab", background=title_color, borderwidth=1) 
    style.map("TNotebook.Tab", background=[("selected", bg_color)])

    # Trades widget

    text_trades = tk.Text(notebook, cursor="arrow", highlightthickness=0,)
    text_trades.bind("<Key>", lambda event: text_ignore(event))
    scroll_trades = tk.Scrollbar(text_trades)
    scroll_trades.config(command=text_trades.yview)
    text_trades.config(yscrollcommand=scroll_trades.set)
    scroll_trades.pack(side="right", fill="y")
    text_trades.pack(side="left", fill="both", expand=True)
    notebook.add(text_trades, text='Trades')

    # Funding widget

    text_funding = tk.Text(notebook, cursor="arrow", highlightthickness=0,)
    text_funding.bind("<Key>", lambda event: text_ignore(event))
    scroll_funding = tk.Scrollbar(text_funding)
    scroll_funding.config(command=text_funding.yview)
    text_funding.config(yscrollcommand=scroll_funding.set)
    scroll_funding.pack(side="right", fill="y")
    text_funding.pack(side="left", fill="both", expand=True)
    notebook.add(text_funding, text='Funding')

    notebook.pack(expand=1, fill="both")
    pw_orders_trades.add(text_orders)
    pw_orders_trades.add(notebook)
    pw_orders_trades.bind("<Configure>", lambda event: resize_row(event, pw_orders_trades, 2))

    # Orderbook widget

    main_col0_row0_col1 = tk.Frame(main_col0_row0, borderwidth=0, bg="green", padx=0, pady=2)
    main_col0_row0_col1.grid(row=0, column=1, sticky="N" + "S" + "W" + "E")
    main_col0_row0.grid_columnconfigure(0, weight=1)
    main_col0_row0.grid_columnconfigure(1, minsize=400)
    main_col0_row0.grid_rowconfigure(0, weight=1)
    main_col0_row0_col1.grid_columnconfigure(1, weight=1)

    # Orderbook table

    labels["orderbook"] = []
    labels_cache["orderbook"] = []
    for row in range(num_book):
        lst = []
        cache = []
        for name in var.name_book:
            lst.append(tk.Label(main_col0_row0_col1, text=name, pady=0)) # frame_3row_3col
            cache.append(name+str(row))
        labels["orderbook"].append(lst)
        labels_cache["orderbook"].append(cache)

    # Account widget
        
    main_col0_row1 = tk.Frame(main_col0, borderwidth=0, bg="red") # frame_4row_1_2_3col
    main_col0_row1.grid(row=1, column=0, sticky="N" + "S" + "W" + "E")
    main_col0.grid_columnconfigure(0, weight=1)
    main_col0.grid_rowconfigure(0, minsize=400)
    main_col0.grid_rowconfigure(1, weight=1)

    # Account table

    labels["account"] = []
    labels_cache["account"] = []

    # Exchange widget

    main_col1 = tk.Frame(main_frame, borderwidth=1, bg="blue") # frame_3row_1col
    main_col1.grid(row=0, column=1, sticky="N" + "S" + "W" + "E")

    frame_exchange_sub = tk.Frame(main_col1)
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

    '''# Frame fo the order entry
    frame_entry = tk.Frame(main_frame)
    frame_entry.pack(fill="both", expand=True)
    label_test = tk.Label(frame_entry, text="Enter orders here")
    label_test.pack()'''

    main_frame.grid_columnconfigure(0, weight=1)
    main_frame.grid_columnconfigure(1, minsize=350)
    main_frame.grid_rowconfigure(0, weight=1)

    # Robots widget

    robo_frame = tk.Frame(pw_2row, cursor="arrow", bg=bg_color, highlightthickness=0,) # frame_5row_1_2_3_4col
    canvas_robots = tk.Canvas(robo_frame, height=210, highlightthickness=0)
    v_robots = tk.Scrollbar(robo_frame, orient="vertical")
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
 
    # Robots table

    labels["robots"] = []
    labels_cache["robots"] = []

    pw_2row.add(main_frame)
    pw_2row.add(robo_frame)
    pw_2row.bind("<Configure>", lambda event: resize_row(event, pw_2row, 1.35))

    root.grid_columnconfigure(0, weight=1)
    root.grid_rowconfigure(1, weight=1)
    root.grid_rowconfigure(2, minsize=630)



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