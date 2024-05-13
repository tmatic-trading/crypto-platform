import platform
import tkinter as tk
import tkinter.font
from datetime import datetime
from tkinter import ttk

from common.variables import Variables as var

if platform.system() == "Windows":
    from ctypes import windll

    windll.shcore.SetProcessDpiAwareness(1)


class AutoScrollbar(tk.Scrollbar):
    def set(self, low, high):
        if float(low) <= 0.0 and float(high) >= 1.0:
            self.tk.call("grid", "remove", self)
        else:
            self.grid()
        tk.Scrollbar.set(self, low, high)


class Variables:
    root = tk.Tk()
    platform_name = "Tmatic"
    root.title(platform_name)
    screen_width = root.winfo_screenwidth()
    screen_height = root.winfo_screenheight()
    if screen_width > 1440:
        window_ratio = 0.7
        adaptive_ratio = 0.85
    elif screen_width > 1366:
        window_ratio = 0.72
        adaptive_ratio = 0.9
    elif screen_width > 1280:
        window_ratio = 0.75
        adaptive_ratio = 0.95
    elif screen_width > 1024:
        window_ratio = 0.8
        adaptive_ratio = 0.97
    else:
        window_ratio = 1
        adaptive_ratio = 1
    window_width = int(screen_width * window_ratio)
    window_height = int(screen_height * 0.7)
    root.geometry("{}x{}".format(window_width, window_height))
    all_width = window_width
    state_width = window_width
    last_market = ""

    if platform.system() == "Windows":
        ostype = "Windows"
    elif platform.system() == "Darwin":
        ostype = "Mac"
    else:
        ostype = "Linux"

    num_robots = 1
    num_book = 20  # Must be even
    col1_book = 0
    symb_book = ()

    pw_main = tk.PanedWindow(
        root, orient=tk.HORIZONTAL, sashrelief="raised", bd=0, sashwidth=0
    )
    pw_main.pack(fill="both", expand="yes")

    # Adaptive frame to the left, always visible
    frame_left = tk.Frame()
    frame_left.pack(fill="both", expand="yes")

    # Frame to the right, always blank
    frame_right = tk.Frame()
    frame_right.pack(fill="both", expand="yes")

    # Top state frame: trading on/off, time
    frame_state = tk.Frame(frame_left)
    frame_state.grid(row=0, column=0, sticky="NSWE")
    frame_left.grid_columnconfigure(0, weight=1)
    frame_left.grid_rowconfigure(0, weight=0)
    label_trading = tk.Label(frame_state, text=" TRADING: ")
    label_trading.pack(side="left")
    label_f9 = tk.Label(
        frame_state, width=3, text="OFF", fg="white", bg="red", anchor="c"
    )
    label_f9.pack(side="left")

    # Color map
    if ostype == "Mac":
        green_color = "#07b66e"
        red_color = "#f53661"
        title_color = label_trading["background"]
        bg_select_color = "systemSelectedTextBackgroundColor"
        fg_color = label_trading["foreground"]
    else:
        green_color = "#07b66e"
        red_color = "#f53661"
        label_trading.config(bg="gray82")
        title_color = label_trading["background"]
        bg_select_color = "#b3d7ff"
        sell_bg_color = "#feede0"
        buy_bg_color = "#e3f3cf"
        fg_color = "black"
    fg_select_color = fg_color

    label_time = tk.Label(frame_state, anchor="e", foreground=fg_color)
    label_time.pack(side="right")

    # Paned window: up - information field, down - the rest interface
    pw_info_rest = tk.PanedWindow(
        frame_left, orient=tk.VERTICAL, sashrelief="raised", bd=0
    )
    pw_info_rest.grid(row=1, column=0, sticky="NSEW")
    frame_left.grid_rowconfigure(1, weight=1)

    # Information field
    frame_info = tk.Frame(pw_info_rest)
    frame_info.pack(fill="both", expand="yes")

    # Information widget
    if ostype == "Mac":
        text_info = tk.Text(
            frame_info,
            highlightthickness=0,
        )
    else:
        text_info = tk.Text(
            frame_info,
            bg="gray98",
            highlightthickness=0,
        )
    text_info.grid(row=0, column=0, sticky="NSEW")
    scroll_info = AutoScrollbar(frame_info, orient="vertical")
    scroll_info.config(command=text_info.yview)
    scroll_info.grid(row=0, column=1, sticky="NS")
    text_info.config(yscrollcommand=scroll_info.set)
    frame_info.grid_columnconfigure(0, weight=1)
    frame_info.grid_columnconfigure(1, weight=0)
    frame_info.grid_rowconfigure(0, weight=1)
    # text_info.configure(state="disabled")
    bg_color = text_info["background"]

    # This technical PanedWindow contains most frames and widgets
    pw_rest1 = tk.PanedWindow(
        pw_info_rest, orient=tk.HORIZONTAL, sashrelief="raised", bd=0, sashwidth=0
    )
    pw_rest1.pack(fill="both", expand="yes")

    # One or more exchages is put in this frame
    frame_market = tk.Frame(pw_rest1)

    # This technical PanedWindow contains orderbook, positions, orders, trades, fundings, results, currencies, robots
    pw_rest2 = tk.PanedWindow(
        pw_rest1,
        orient=tk.VERTICAL,
        sashrelief="raised",
        bd=0,
        sashwidth=0,
        height=1,
    )
    pw_rest2.pack(fill="both", expand="yes")

    # This technical PanedWindow contains orderbook, positions, orders, trades, fundings, results
    pw_rest3 = tk.PanedWindow(
        pw_rest2, orient=tk.HORIZONTAL, sashrelief="raised", bd=0, sashwidth=0
    )
    pw_rest3.pack(fill="both", expand="yes")

    # Frame for the order book
    frame_orderbook = tk.Frame(pw_rest3)

    # This technical PanedWindow contains positions, orders, trades, fundings, results
    pw_rest4 = tk.PanedWindow(
        pw_rest3,
        orient=tk.VERTICAL,
        sashrelief="raised",
        bd=0,
        sashwidth=0,
        height=1,
    )
    pw_rest4.pack(fill="both", expand="yes")

    # Frame for instruments and their positions
    frame_position = tk.Frame(pw_rest4)

    # Paned window: up - orders, down - trades, fundings, results
    pw_orders_trades = tk.PanedWindow(
        pw_rest4, orient=tk.VERTICAL, sashrelief="raised", bd=0, height=1
    )
    pw_orders_trades.pack(fill="both", expand="yes")

    # Frame for active orders
    frame_orders = tk.Frame(pw_orders_trades)

    # Notebook tabs: Trades / Funding / Results
    if ostype == "Mac":
        notebook = ttk.Notebook(pw_orders_trades, padding=(-9, 0, -9, -9))
    else:
        notebook = ttk.Notebook(pw_orders_trades, padding=0)
    style = ttk.Style()
    line_height = tkinter.font.Font(font="TkDefaultFont").metrics("linespace")
    # style.configure("Treeview.Heading", background=title_color)
    if ostype != "Mac":
        style.map(
            "Treeview",
            background=[("selected", "#b3d7ff")],
            foreground=[("selected", fg_color)],
        )
    style.configure(
        "market.Treeview",
        fieldbackground=title_color,
        background=title_color,
        rowheight=line_height * 3,
    )

    style.configure("TNotebook", borderwidth=0, background="gray92", tabposition="n")
    style.configure("TNotebook.Tab", background="gray92")
    # style.map("TNotebook.Tab", background=[("selected", title_color)])

    # Trades frame
    frame_trades = tk.Frame(notebook)

    # Funding frame
    frame_funding = tk.Frame(notebook)

    # Results frame
    frame_results = tk.Frame(notebook)

    notebook.add(frame_trades, text="Trades")
    notebook.add(frame_funding, text="Funding")
    notebook.add(frame_results, text="Results")
    pw_orders_trades.add(frame_orders)
    pw_orders_trades.add(notebook)
    pw_orders_trades.bind(
        "<Configure>", lambda event: resize_height(event, Variables.pw_orders_trades, 2)
    )

    # Paned window: up - currencies (account), down - robots
    pw_account_robo = tk.PanedWindow(
        pw_rest2, orient=tk.VERTICAL, sashrelief="raised", bd=0, height=1
    )
    pw_account_robo.pack(fill="both", expand="yes")

    # Frame for currencies (account)
    frame_account = tk.Frame(pw_account_robo)

    # Frame for the robots table
    frame_robots = tk.Frame(pw_account_robo)

    pw_account_robo.add(frame_account)
    pw_account_robo.add(frame_robots)
    pw_account_robo.bind(
        "<Configure>", lambda event: resize_height(event, Variables.pw_account_robo, 2)
    )

    pw_rest4.add(frame_position)
    pw_rest4.add(pw_orders_trades)
    pw_rest4.bind(
        "<Configure>", lambda event: resize_height(event, Variables.pw_rest4, 5)
    )

    pw_rest3.add(frame_orderbook)
    pw_rest3.add(pw_rest4)
    pw_rest3.bind(
        "<Configure>", lambda event: resize_width(event, Variables.pw_rest3, Variables.window_width // 4.25, 3)
    )

    pw_rest2.add(pw_rest3)
    pw_rest2.add(pw_account_robo)
    pw_rest2.bind(
        "<Configure>", lambda event: resize_height(event, Variables.pw_rest2, 1.4)
    )

    pw_rest1.add(frame_market)
    pw_rest1.add(pw_rest2)
    pw_rest1.bind(
        "<Configure>", lambda event: resize_width(event, Variables.pw_rest1, Variables.window_width // 9, 6)
    )

    pw_info_rest.add(frame_info)
    pw_info_rest.add(pw_rest1)
    pw_info_rest.bind(
        "<Configure>", lambda event: resize_height(event, Variables.pw_info_rest, 9)
    )

    pw_main.add(frame_left)
    pw_main.add(frame_right)
    pw_main.bind(
        "<Configure>", lambda event: resize_width(event, Variables.pw_main, Variables.window_width, 1)
    )

    refresh_var = None
    nfo_display_counter = 0
    f9 = "OFF"
    robots_window_trigger = "off"
    info_display_counter = 0
    handler_orderbook_symbol = tuple()
    book_window_trigger = "off"
    order_window_trigger = "off"
    table_limit = 150


class TreeviewTable(Variables):
    def __init__(
        self, frame: tk.Frame, name: str, title: list, size: int, style="", bind=None, hide=[]
    ) -> None:
        self.title = title
        self.max_rows = 200
        self.name = name
        self.title = title
        self.cache = list()
        self.bind = bind
        columns = [num for num in range(1, len(title) + 1)]
        frame.grid_columnconfigure(0, weight=1)
        frame.grid_rowconfigure(0, weight=1)
        self.tree = ttk.Treeview(frame, style=style, columns=columns, show="headings")
        for num, name in enumerate(title, start=1):
            self.tree.heading(num, text=name)
            self.tree.column(num, anchor=tk.CENTER, width=50)
        scroll = AutoScrollbar(frame, orient="vertical")
        scroll.config(command=self.tree.yview)
        self.tree.config(yscrollcommand=scroll.set)
        self.tree.grid(row=0, column=0, sticky="NSEW")
        scroll.grid(row=0, column=1, sticky="NS")
        self.children = list()
        self.tree.tag_configure("Select", background=self.bg_select_color)
        self.tree.tag_configure("Buy", foreground=self.green_color)
        self.tree.tag_configure("Sell", foreground=self.red_color)
        self.tree.tag_configure("Deselect", background=self.bg_color)
        self.tree.tag_configure("Normal", foreground=self.fg_color)
        self.tree.tag_configure("Error", background=self.red_color, foreground="white")
        self.tree.tag_configure(
            "Market", background=self.title_color, foreground=self.fg_color
        )
        if bind:
            self.tree.bind("<<TreeviewSelect>>", bind)
        self.init(size=size)
        self.column_hide = []
        self.hide_num = -1
        hide_begin = list(self.tree["columns"])
        for num, id_col in enumerate(hide, start=0):
            self.column_hide.append(hide_begin)
            self.column_hide[num].remove(id_col)
            hide_begin = list(self.column_hide[num])
            self.column_hide[num] = tuple(hide_begin)

    def init(self, size):
        self.clear_all()
        self.cache = list()
        blank = ["" for _ in self.title]
        for _ in range(size):
            self.insert(values=blank)
            self.cache.append(blank)

    def insert(self, values: list, configure="") -> None:
        self.tree.insert("", 0, values=values, tags=configure)
        self.children = self.tree.get_children()
        if len(self.children) > self.max_rows:
            self.delete(row=len(self.children) - 1)

    def delete(self, row: int) -> None:
        self.tree.delete(self.children[row])
        self.children = self.tree.get_children()

    def update(self, row: int, values: list) -> None:
        self.tree.item(self.children[row], values=values)

    def paint(self, row: int, configure: str) -> None:
        self.tree.item(self.children[row], tags=configure)

    def clear_all(self):
        self.tree.delete(*self.children)
        self.children = self.tree.get_children()

    def append_data(self, rows: list, market: str) -> list:
        data = list()
        if self.children:
            child = self.children[0]
            for child in self.children:
                values = self.tree.item(child)["values"]
                if values[3] != market:
                    data.append(values)
        data += rows
        self.clear_all()
        data = list(
            map(lambda x: x + [datetime.strptime(x[0], "%y%m%d %H:%M:%S")], data)
        )
        data.sort(key=lambda x: x[-1])
        data = list(map(lambda x: x[:-1], data))

        return data[: self.max_rows]

    def set_selection(self):
        self.tree.selection_add(self.children[0])
        # self.tree.selection_clear


class TreeTable:
    position: TreeviewTable
    robots: TreeviewTable
    account: TreeviewTable
    orderbook: TreeviewTable
    market: TreeviewTable
    results: TreeviewTable
    trades: TreeviewTable
    funding: TreeviewTable
    orders: TreeviewTable


def text_ignore(event):
    return "break"  # Prevents further handling of the event


def resize_col(event, pw, ratio):
    pw.paneconfig(pw.panes()[0], width=pw.winfo_width() // ratio)


def resize_height(event, pw, ratio):
    pw.paneconfig(pw.panes()[0], height=pw.winfo_height() // ratio)

def resize_width(event, pw, start_width, min_ratio):
    ratio = pw.winfo_width() / start_width
    if ratio < min_ratio:
        my_width = pw.winfo_width() // min_ratio
    else:
        my_width = start_width
    pw.paneconfig(pw.panes()[0], width=my_width)
