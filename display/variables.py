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
            if (
                self.master in Variables.dlmtr_frames
                and Variables.dlmtr_frames[self.master].winfo_ismapped() == 0
            ):
                Variables.dlmtr_frames[self.master].grid(row=0, column=1, sticky="NSWE")
        else:
            self.grid()
            if (
                self.master in Variables.dlmtr_frames
                and Variables.dlmtr_frames[self.master].winfo_ismapped() == 1
            ):
                Variables.dlmtr_frames[self.master].grid_forget()
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
    # all_height = 1
    state_width = window_width
    last_market = ""
    dlmtr_frames = {}

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
    labels = dict()
    labels_cache = dict()

    # Main frame. Always visible
    frame_left = tk.Frame()
    frame_left.grid(row=0, column=0, sticky="NSWE")
    root.grid_columnconfigure(0, weight=1)

    # Adaptive frame to the right. Always blank; forgotten when the window is narrowed
    frame_right = tk.Frame()
    frame_right.grid(row=0, column=1, sticky="NSWE")
    root.grid_columnconfigure(1, weight=0)
    root.grid_rowconfigure(0, weight=1)

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
        green_color = "#319d30"
        red_color = "#dc6537"
        label_trading.config(bg="gray82")
        title_color = label_trading["background"]
        bg_select_color = "khaki1"
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
    frame_info.grid_columnconfigure(0, weight=1)
    scroll_info = AutoScrollbar(frame_info, orient="vertical")
    scroll_info.config(command=text_info.yview)
    scroll_info.grid(row=0, column=1, sticky="NS")
    text_info.config(yscrollcommand=scroll_info.set)
    frame_info.grid_columnconfigure(1, weight=0)
    frame_info.grid_rowconfigure(0, weight=1)
    # text_info.configure(state="disabled")
    bg_color = text_info["background"]

    # This technical frame contains most frames and widgets
    frame_rest1 = tk.Frame(pw_info_rest)

    pw_info_rest.add(frame_info)
    pw_info_rest.add(frame_rest1)
    pw_info_rest.bind(
        "<Configure>", lambda event: resize_row(event, Variables.pw_info_rest, 9)
    )

    # One or more exchages is put in this frame
    market_frame = tk.Frame(frame_rest1)
    market_frame.grid(row=0, column=0, sticky="NSEW")
    frame_rest1.grid_columnconfigure(0, weight=10)

    # This technical frame contains orderbook, positions, orders, trades, fundings, results, currencies, robots
    frame_rest2 = tk.Frame(frame_rest1)
    frame_rest2.grid(row=0, column=1, sticky="NSEW")
    frame_rest1.grid_columnconfigure(1, weight=500)
    frame_rest1.grid_rowconfigure(0, weight=1)

    # This technical frame contains orderbook, positions, orders, trades, fundings, results
    frame_rest3 = tk.Frame(frame_rest2)
    frame_rest3.grid(row=0, column=0, sticky="NSEW")
    frame_rest2.grid_columnconfigure(0, weight=1)
    frame_rest2.grid_rowconfigure(0, weight=72)

    # Frame for the order book
    orderbook_frame = tk.Frame(frame_rest3)
    orderbook_frame.grid(row=0, column=0, sticky="NSEW")
    frame_rest3.grid_columnconfigure(0, weight=50)
    orderbook_delimiter = tk.Frame(orderbook_frame, width=2)
    dlmtr_frames[orderbook_frame] = orderbook_delimiter

    # This technical frame contains positions, orders, trades, fundings, results
    frame_rest4 = tk.Frame(frame_rest3)
    frame_rest4.grid(row=0, column=1, sticky="NSEW")
    frame_rest3.grid_columnconfigure(1, weight=300)
    frame_rest3.grid_rowconfigure(0, weight=1)

    # Frame for instruments and their positions
    position_frame = tk.Frame(frame_rest4)
    position_frame.grid(row=0, column=0, sticky="NSWE")
    frame_rest4.grid_columnconfigure(0, weight=1)
    frame_rest4.grid_rowconfigure(0, weight=18)

    # Paned window: up - orders, down - trades, fundings, results
    pw_orders_trades = tk.PanedWindow(
        frame_rest4, orient=tk.VERTICAL, sashrelief="raised", bd=0, height=1
    )
    pw_orders_trades.grid(row=1, column=0, sticky="NSWE")
    frame_rest4.grid_rowconfigure(1, weight=82)

    # Orders frame
    frame_orders = tk.Frame(pw_orders_trades)

    # Notebook tabs: Trades / Funding / Results
    if ostype == "Mac":
        notebook = ttk.Notebook(pw_orders_trades, padding=(-9, 0, -9, -9))
    else:
        notebook = ttk.Notebook(pw_orders_trades, padding=0)
    style = ttk.Style()
    line_height = tkinter.font.Font(font='TkDefaultFont').metrics('linespace')
    style.configure("market.Treeview", fieldbackground=title_color, rowheight=line_height*3)
    style.configure("TNotebook", borderwidth=0, background="gray90", tabposition="n")
    style.configure("TNotebook.Tab", background="gray90")
    style.map("TNotebook.Tab", background=[("selected", title_color)])

    # Trades frame
    frame_trades = ttk.Frame(notebook)

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
        "<Configure>", lambda event: resize_row(event, Variables.pw_orders_trades, 2)
    )

    # Paned window: up - currencies (account), down - robots
    pw_account_robo = tk.PanedWindow(
        frame_rest2, orient=tk.VERTICAL, sashrelief="raised", bd=0, height=1
    )
    pw_account_robo.grid(row=1, column=0, sticky="NSWE")
    frame_rest2.grid_rowconfigure(1, weight=28)

    # Frame for currencies (account)
    account_frame = tk.Frame(pw_account_robo)

    # Frame for the robots table
    robots_frame = tk.Frame(pw_account_robo)

    pw_account_robo.add(account_frame)
    pw_account_robo.add(robots_frame)
    pw_account_robo.bind(
        "<Configure>", lambda event: resize_row(event, Variables.pw_account_robo, 2)
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


class GridTable(Variables):
    def __init__(
        self,
        frame: tk.Frame,
        name: str,
        size: int,
        title: list,
        column_width: int = None,
        canvas_height: int = 30,
        title_on: bool = True,
        bind=None,
        color: str = None,
        select: bool = None,
    ) -> None:
        self.name = name
        self.title = title
        self.select = select
        self.bind = bind
        self.color = color
        self.size = size
        self.title_on = title_on
        self.mod = 1
        self.labels[name] = []
        self.labels_cache[name] = []
        if column_width is not None:
            width = len(title) * column_width
        else:
            width = column_width
        if not title_on:
            self.mod = 0
            size -= 1
        my_bg = self.bg_color if name != "market" else self.title_color
        canvas = tk.Canvas(
            frame, highlightthickness=0, height=canvas_height, width=width, bg=my_bg
        )
        canvas.grid(row=0, column=0, sticky="NSEW")
        frame.grid_rowconfigure(0, weight=1)
        frame.grid_columnconfigure(0, weight=1)
        scroll = AutoScrollbar(frame, orient="vertical")
        scroll.config(command=canvas.yview)
        scroll.grid(row=0, column=1, sticky="NS")
        canvas.config(yscrollcommand=scroll.set)
        self.sub = tk.Frame(canvas, bg=my_bg)
        positions_id = canvas.create_window((0, 0), window=self.sub, anchor="nw")
        canvas.bind(
            "<Configure>",
            lambda event, id=positions_id, pos=canvas: event_width(event, id, pos),
        )
        self.sub.bind("<Configure>", lambda event: event_config(event, canvas))
        canvas.bind("<Enter>", lambda event: on_enter(event, canvas, scroll))
        canvas.bind("<Leave>", lambda event: on_leave(event, canvas))
        for row in range(size):
            self.create_grid(row=row)

    def create_grid(self, row: int):
        lst = []
        cache = []
        if len(self.labels[self.name]) <= row:
            for title_name in self.title:
                lst.append(
                    tk.Label(
                        self.sub,
                        text=title_name,
                        pady=0,  # , background=self.title_color
                    )
                )
                cache.append(title_name + str(row))
            self.labels[self.name].append(lst)
            self.labels_cache[self.name].append(cache)
        for column in range(len(self.title)):
            self.labels[self.name][row][column].grid(
                row=row, column=column, sticky="NSWE", padx=0, pady=0
            )
            if row > self.mod - 1:
                if self.select:
                    if row == self.mod:
                        color_bg = self.bg_select_color
                        color_fg = self.fg_select_color
                    else:
                        color_bg = self.color
                        color_fg = self.fg_color
                else:
                    color_bg = self.color
                    color_fg = self.fg_color

                self.labels[self.name][row][column]["text"] = ""
                self.labels[self.name][row][column]["bg"] = color_bg
                self.labels[self.name][row][column]["fg"] = color_fg
                if self.bind:
                    self.labels[self.name][row][column].bind(
                        "<Button-1>",
                        lambda event, row_position=row: self.bind(event, row_position),
                    )
            self.sub.grid_columnconfigure(column, weight=1)

    def reconfigure_table(self, action: str, number: int):
        """
        Depending on the exchange, you may need a different number of rows in the
        tables, since, for example, you may be subscribed to a different number of
        instruments. Therefore, the number of rows in tables: "account",
        "position", "robots" must change  dynamically. Calling this function
        changes the number of rows in a particular table.

        Input parameters:

        action - "new" - add new lines, "hide" - remove lines
        number - number of lines to add or hide
        """
        row = self.sub.grid_size()[1]
        if action == "new":
            while number:
                if row + number > self.size:
                    self.size += 1
                    self.create_grid(row=row)
                else:
                    for num, label in enumerate(self.labels[self.name][row]):
                        label.grid(
                            row=row,
                            column=num,
                            sticky="NSWE",
                            padx=0,
                            pady=0,
                        )
                row += 1
                number -= 1
        elif action == "hide":
            row -= 1
            while number:
                for r in self.sub.grid_slaves(row=row):
                    r.grid_forget()
                number -= 1
                row -= 1
                if row == 0:
                    break

    def color_market(self, state: str, row: int, market: str):
        if state == "error":
            color = self.sell_bg_color
        else:
            if market == var.current_market:
                color = self.bg_select_color
            else:
                color = self.color
        for column in range(len(self.title)):
            self.labels[self.name][row + self.mod][column]["bg"] = color


class Tables:
    position: GridTable
    account: GridTable
    robots: GridTable
    market: GridTable
    orderbook: GridTable
    results: GridTable


class ListBoxTable(Variables):
    """
    The table contains a grid with one row in each column in which a Listbox
    is inserted. The contents of table rows are managed through Listbox tools
    in accordance with the row index.
    """

    def __init__(
        self,
        name: str,
        frame: tk.Frame,
        size: int,
        title: list,
        title_on: bool = True,
        bind=None,
        expand: bool = None,
    ) -> None:
        self.title = title
        self.title_on = title_on
        self.mod = 1
        self.max_rows = 200
        if title_on:
            self.height = 1
        else:
            self.height = 0
            self.mod = 0
        self.active_row = 1
        self.mod = 1
        self.columns = [[] for _ in title]
        self.name = name
        if expand:
            frame.grid_rowconfigure(0, weight=1)
        canvas = tk.Canvas(frame, highlightthickness=0, bg=self.bg_color)
        canvas.grid(row=0, column=0, sticky="NSEW")
        frame.grid_columnconfigure(0, weight=1)
        scroll = AutoScrollbar(frame, orient="vertical")
        scroll.config(command=canvas.yview)
        scroll.grid(row=0, column=1, sticky="NS")
        canvas.config(yscrollcommand=scroll.set)
        self.sub = tk.Frame(canvas, pady=0, bg=self.bg_color)
        id = canvas.create_window((0, 0), window=self.sub, anchor="nw")
        canvas.bind(
            "<Configure>",
            lambda event, id=id, can=canvas: event_width(event, id, can),
        )
        self.sub.bind("<Configure>", lambda event: event_config(event, canvas))
        canvas.bind("<Enter>", lambda event: on_enter(event, canvas, scroll))
        canvas.bind("<Leave>", lambda event: on_leave(event, canvas))
        if self.ostype == "Mac":
            self.item_color = {
                "Buy": {
                    "bg": self.bg_color,
                    "fg": self.green_color,
                    "selectbackground": self.bg_color,
                    "selectforeground": self.green_color,
                },
                "Sell": {
                    "bg": self.bg_color,
                    "fg": self.red_color,
                    "selectbackground": self.bg_color,
                    "selectforeground": self.red_color,
                },
            }
        else:
            self.item_color = {
                "Buy": {
                    "bg": self.buy_bg_color,
                    "fg": self.fg_color,
                    "selectbackground": self.buy_bg_color,
                    "selectforeground": self.fg_color,
                },
                "Sell": {
                    "bg": self.sell_bg_color,
                    "fg": self.fg_color,
                    "selectbackground": self.sell_bg_color,
                    "selectforeground": self.fg_color,
                },
            }
        self.listboxes = list()
        for num, name in enumerate(title):
            value = (
                [
                    name,
                ]
                if title_on
                else [
                    "",
                ]
            )
            vars = tk.Variable(value=value)
            self.listboxes.append(
                tk.Listbox(
                    self.sub,
                    listvariable=vars,
                    bd=0,
                    background=self.bg_color,
                    highlightthickness=0,
                    selectbackground=self.title_color,
                    selectforeground=self.fg_color,
                    activestyle="none",
                    justify="center",
                    height=self.height,
                    width=0,
                )
            )
            if title_on:
                self.listboxes[num].itemconfig(0, bg=self.title_color)
            self.listboxes[num].grid(row=0, padx=0, column=num, sticky="NSWE")
            self.sub.grid_columnconfigure(num, weight=1)
            self.sub.grid_rowconfigure(0, weight=1)
            if bind:
                self.listboxes[num].bind("<<ListboxSelect>>", bind)
            for _ in range(size):
                lst = ["" for _ in range(len(self.title))]
                self.insert(elements=lst, row=1)

    def insert(self, row: int, elements: list) -> None:
        self.height += 1
        for num, listbox in enumerate(self.listboxes):
            listbox.config(height=self.height)
            listbox.insert(row + self.mod, elements[num])
        if self.height > self.max_rows:
            self.delete(row=self.height)

    def delete(self, row: int) -> None:
        self.height -= 1
        for listbox in self.listboxes:
            listbox.config(height=self.height)
            listbox.delete(row + self.mod)

    def clear_all(self) -> None:
        for listbox in self.listboxes:
            listbox.config(height=self.height)
            listbox.delete(self.mod, tk.END)

    def update(self, row: int, elements: list) -> None:
        pass
        """color = self.listboxes[0].itemcget(row + self.mod, "background")
        color_fg = self.listboxes[0].itemcget(row + self.mod, "foreground")
        self.delete(row + self.mod)
        self.insert(row + self.mod, elements)
        self.paint(row + self.mod, color, color_fg)"""

    def paint(self, row: int, side: str) -> None:
        for listbox in self.listboxes:
            listbox.itemconfig(row + self.mod, **self.item_color[side])

    def insert_columns(self, sort=True) -> None:
        """
        Because the Listbox widget is slow to perform insert operations on
        macOS, the initial filling of tables is done column-by-column,
        not row-by-row.
        """
        if sort:
            if self.columns[0]:  # sort by time
                self.columns = list(zip(*self.columns))
                self.columns = list(
                    map(
                        lambda x: x + (datetime.strptime(x[0], "%y%m%d %H:%M:%S"),),
                        self.columns,
                    )
                )
                self.columns.sort(key=lambda x: x[-1], reverse=True)
                self.columns = zip(*self.columns)
                self.columns = list(
                    map(lambda x: list(x[: self.table_limit]), self.columns)
                )[:-1]
        self.height = len(self.columns[0]) + 1
        for num, listbox in enumerate(self.listboxes):
            listbox.delete(self.mod, tk.END)
            listbox.config(height=self.height)
            if self.title_on:
                self.columns[num] = [self.title[num]] + self.columns[num]
            vars = tk.Variable(value=self.columns[num])
            listbox.config(listvariable=vars)
        try:
            col = self.title.index("SIDE")
            name = "SIDE"
        except ValueError:
            col = self.title.index("PNL")
            name = "Funding"
        self.paint_columns(col=col, name=name)

    def paint_columns(self, col: int, name: str) -> None:
        for num, column in enumerate(self.columns):
            for row in range(self.mod, len(column)):
                if name == "Funding":
                    side = "Buy" if float(self.columns[col][row]) > 0 else "Sell"
                else:
                    side = self.columns[col][row]
                self.listboxes[num].itemconfig(row, **self.item_color[side])

    def clear_columns(self, market: str) -> None:
        for num, listbox in enumerate(self.listboxes):
            self.columns[num] = list(listbox.get(self.mod, tk.END))
        col = self.title.index("MARKET")
        col_size = len(self.columns[col])
        for num in range(col_size - 1, -1, -1):
            if self.columns[col][num] == market:
                for column in range(len(self.columns)):
                    self.columns[column].pop(num)
        self.clear_all()


class TreeviewTable(Variables):
    def __init__(
        self, frame: tk.Frame, name: str, title: list, size: int, style="", bind=None
    ) -> None:
        self.title = title
        self.max_rows = 200
        self.name = name
        self.title = title
        self.cache = list()
        columns = [num for num in range(1, len(title) + 1)]
        self.tree = ttk.Treeview(frame, style=style, columns=columns, show="headings")
        for num, name in enumerate(title, start=1):
            self.tree.heading(num, text=name)
            self.tree.column(num, anchor=tk.CENTER, width=10)
        scroll = AutoScrollbar(frame, orient="vertical")
        scroll.config(command=self.tree.yview)
        self.tree.config(yscrollcommand=scroll.set)
        self.tree.grid(row=0, column=0, sticky="NSEW")
        scroll.grid(row=0, column=1, sticky="NS")
        self.children = []
        self.tree.tag_configure("Select", background=self.bg_select_color)
        self.tree.tag_configure("Buy", foreground=self.green_color)
        self.tree.tag_configure("Sell", foreground=self.red_color)
        self.tree.tag_configure("Deselect", background=self.bg_select_color)
        if bind:
            self.tree.bind("<<TreeviewSelect>>", bind)
        self.init(size)


    def init(self, size):
        self.cache = list()
        for _ in range(size):
            self.insert(values=self.title)
            self.cache.append(self.title)

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
        print("Deselect")
        self.tree.item(self.children[row], tags=configure)

    def clear_all(self):
        self.tree.delete(*self.children)
        self.children = self.tree.get_children()


class TreeTables:
    position: TreeviewTable
    robots: TreeviewTable
    account: TreeviewTable
    orderbook: TreeviewTable
    market: TreeviewTable
    results: TreeviewTable


def event_width(event, canvas_id, canvas_event):
    canvas_event.itemconfig(canvas_id, width=event.width)


def event_config(event, canvas_event):
    canvas_event.configure(scrollregion=canvas_event.bbox("all"))


def on_enter(event, canvas, scroll):
    if Variables.ostype == "Linux":
        canvas.bind_all(
            "<Button-4>",
            lambda event: on_mousewheel(event, canvas, scroll),
        )
        canvas.bind_all(
            "<Button-5>",
            lambda event: on_mousewheel(event, canvas, scroll),
        )
    else:
        canvas.bind_all(
            "<MouseWheel>",
            lambda event: on_mousewheel(event, canvas, scroll),
        )


def on_leave(event, canvas):
    if Variables.ostype == "Linux":
        canvas.unbind_all("<Button-4>")
        canvas.unbind_all("<Button-5>")
    else:
        canvas.unbind_all("<MouseWheel>")


def on_mousewheel(event, canvas, scroll):
    slider_position = scroll.get()
    if slider_position != (0.0, 1.0):  # Scrollbar is not full
        if Variables.ostype == "Windows":
            canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")
        elif Variables.ostype == "Mac":
            canvas.yview_scroll(int(-1 * event.delta), "units")
        else:
            if event.num == 4:
                canvas.yview_scroll(-1, "units")
            elif event.num == 5:
                canvas.yview_scroll(1, "units")


def text_ignore(event):
    return "break"  # Prevents further handling of the event


def resize_col(event, pw, ratio):
    pw.paneconfig(pw.panes()[0], width=pw.winfo_width() // ratio)


def resize_row(event, pw, ratio):
    pw.paneconfig(pw.panes()[0], height=pw.winfo_height() // ratio)
