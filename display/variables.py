import platform
import tkinter as tk
from collections import OrderedDict
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
    root.title("Tmatic")
    root.geometry("+50+50")  # 1360x850

    if platform.system() == "Windows":
        ostype = "Windows"
    elif platform.system() == "Darwin":
        ostype = "Mac"
    else:
        ostype = "Linux"

    num_robots = 1
    num_book = 21  # Must be odd
    col1_book = 0
    symb_book = ()
    frame_state = tk.Frame(padx=10)
    frame_state.grid(row=0, column=0, sticky="W", columnspan=2)
    labels = dict()
    labels_cache = dict()
    label_trading = tk.Label(frame_state, text="  TRADING: ")
    label_trading.pack(side="left")
    label_f9 = tk.Label(frame_state, text="OFF", fg="white")
    label_f9.pack(side="left")
    label_time = tk.Label()
    label_time.grid(row=0, column=2, sticky="E")

    frame_2row_1_2_3col = tk.Frame()
    frame_2row_1_2_3col.grid(
        row=1, column=0, sticky="N" + "S" + "W" + "E", columnspan=3
    )
    frame_information = tk.Frame(frame_2row_1_2_3col)
    frame_information.grid(row=0, column=0, sticky="N" + "S" + "W" + "E")
    position_frame = tk.Frame(frame_2row_1_2_3col)
    position_frame.grid(row=0, column=1, sticky="N" + "S" + "W" + "E")
    frame_2row_1_2_3col.grid_columnconfigure(0, weight=1)
    frame_2row_1_2_3col.grid_columnconfigure(1, weight=1)
    frame_2row_1_2_3col.grid_rowconfigure(0, weight=1)

    # Frame for the exchange table
    frame_3row_1col = tk.Frame()
    frame_3row_1col.grid(row=2, column=0, sticky="N" + "S" + "W" + "E")

    # Frame for the order book
    frame_3row_3col = tk.Frame()
    frame_3row_3col.grid(row=2, column=1, sticky="N" + "S" + "W" + "E", padx=2)
    frame_3row_3col.grid_columnconfigure(0, weight=1)
    frame_3row_3col.grid_rowconfigure(0, weight=1)

    orderbook_frame = tk.Frame(frame_3row_3col, padx=0, pady=0)
    orderbook_frame.grid(row=0, column=0, sticky="N" + "S" + "W" + "E")

    # Frame for orders and funding
    frame_3row_4col = tk.Frame()
    frame_3row_4col.grid(row=2, column=2, sticky="N" + "S" + "W" + "E")

    # Frame for the account table
    frame_4row_1_2_3col = tk.Frame()
    frame_4row_1_2_3col.grid(
        row=3, column=0, sticky="N" + "S" + "W" + "E", columnspan=3, padx=0, pady=0
    )

    # Frame for the robots table
    frame_5row_1_2_3col = tk.Frame()
    frame_5row_1_2_3col.grid(
        row=4, column=0, sticky="N" + "S" + "W" + "E", columnspan=3, padx=0, pady=0
    )

    root.grid_columnconfigure(0, weight=1)
    root.grid_columnconfigure(1, weight=1)
    root.grid_columnconfigure(2, weight=20)
    root.grid_rowconfigure(0, weight=1)
    root.grid_rowconfigure(1, weight=1)
    root.grid_rowconfigure(2, weight=200)
    root.grid_rowconfigure(3, weight=1)
    root.grid_rowconfigure(4, weight=1)

    # Information widget

    if ostype == "Mac":
        text_info = tk.Text(
            frame_information,
            height=6,
            width=30,
            highlightthickness=0,
        )
    else:
        text_info = tk.Text(
            frame_information,
            height=6,
            width=30,
            bg="gray98",
            highlightthickness=0,
        )
    scroll_info = tk.Scrollbar(frame_information)
    text_info.bind("<Key>", lambda event: text_ignore(event))
    scroll_info.config(command=text_info.yview)
    text_info.config(yscrollcommand=scroll_info.set)
    scroll_info.pack(side="right", fill="y")
    text_info.pack(side="right", fill="both", expand="yes")

    # color map

    if ostype == "Mac":
        green_color = "#07b66e"
        red_color = "#f53661"
        title_color = label_trading["background"]
        bg_select_color = "systemSelectedTextBackgroundColor"
    else:
        green_color = "#319d30"
        red_color = "#dc6537"
        label_trading.config(bg="gray83")
        title_color = label_trading["background"]
        bg_select_color = "khaki1"

    bg_color = text_info["background"]
    fg_color = label_trading["foreground"]
    fg_select_color = fg_color

    # Orders widget

    pw_orders_trades = tk.PanedWindow(
        frame_3row_4col, orient=tk.VERTICAL, sashrelief="raised", bd=0
    )
    pw_orders_trades.pack(fill="both", expand=True)

    frame_orders = tk.Frame(pw_orders_trades)
    frame_orders.pack(fill="both", expand="yes")

    # Trades/Funding widget

    if ostype == "Mac":
        notebook = ttk.Notebook(pw_orders_trades, padding=(-9, 0, -9, -9))
    else:
        notebook = ttk.Notebook(pw_orders_trades, padding=0)
    style = ttk.Style()
    style.configure("TNotebook", borderwidth=0, background="gray90")
    style.configure("TNotebook.Tab", background="gray90")
    style.map("TNotebook.Tab", background=[("selected", title_color)])
    notebook.pack(expand=1, fill="both")

    frame_trades = ttk.Frame(notebook)
    frame_trades.pack(fill="both", expand="yes")

    frame_funding = tk.Frame(notebook)
    frame_funding.pack(fill="both", expand="yes")

    notebook.add(frame_trades, text="Trades")
    notebook.add(frame_funding, text="Funding")
    pw_orders_trades.add(frame_orders)
    pw_orders_trades.add(notebook)
    pw_orders_trades.bind(
        "<Configure>", lambda event: resize_row(event, Variables.pw_orders_trades, 2)
    )

    refresh_var = None
    nfo_display_counter = 0
    f9 = "OFF"
    messageStopped = ""
    robots_window_trigger = "off"
    info_display_counter = 0
    symb_book = ""
    book_window_trigger = "off"
    price_rounding = OrderedDict()
    order_window_trigger = "off"
    table_limit = 150


class GridTable(Variables):
    def __init__(
        self,
        frame: tk.Frame,
        name: str,
        size: int,
        title: list,
        column_width: int = 70,
        title_on: bool = True,
        canvas_height: int = None,
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
        width = len(title) * column_width
        if not title_on:
            self.mod = 0
            size -= 1
        my_bg = (
            self.bg_color if name != "robots" and name != "market" else self.title_color
        )
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
                row=row, column=column, sticky="N" + "S" + "W" + "E", padx=0, pady=0
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
                            sticky="N" + "S" + "W" + "E",
                            padx=0,
                            pady=0,
                        )
                    # self.sub.config(bg=self.bg_color)
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


class ListBoxTable(Variables):
    """
    The table contains a grid with one row in each column in which a Listbox
    is inserted. The contents of table rows are managed through Listbox tools
    in accordance with the row index.
    """

    def __init__(
        self,
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
        if expand:
            frame.grid_rowconfigure(0, weight=1)
        canvas = tk.Canvas(frame, highlightthickness=0, bg=self.bg_color)
        canvas.grid(row=0, column=0, sticky="NSEW")
        frame.grid_columnconfigure(0, weight=1)
        scroll = AutoScrollbar(frame, orient="vertical")
        scroll.config(command=canvas.yview)
        scroll.grid(row=0, column=1, sticky="NS")
        canvas.config(yscrollcommand=scroll.set)
        sub = tk.Frame(canvas, pady=0, bg=self.bg_color)
        id = canvas.create_window((0, 0), window=sub, anchor="nw")
        canvas.bind(
            "<Configure>",
            lambda event, id=id, can=canvas: event_width(event, id, can),
        )
        sub.bind("<Configure>", lambda event: event_config(event, canvas))
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
                    "bg": "#e3f3cf",
                    "fg": self.fg_color,
                    "selectbackground": "#e3f3cf",
                    "selectforeground": self.fg_color,
                },
                "Sell": {
                    "bg": "#feede0",
                    "fg": self.fg_color,
                    "selectbackground": "#feede0",
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
                    sub,
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
            self.listboxes[num].grid(
                row=0, padx=0, column=num, sticky="N" + "S" + "W" + "E"
            )
            sub.grid_columnconfigure(num, weight=1)
            sub.grid_rowconfigure(0, weight=1)
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

    def clear_columns(self, name: str) -> None:
        for num, listbox in enumerate(self.listboxes):
            self.columns[num] = list(listbox.get(self.mod, tk.END))
        col = self.title.index("EXCH")
        col_size = len(self.columns[col])
        for num in range(col_size - 1, -1, -1):
            if self.columns[col][num] == name:
                for column in range(len(self.columns)):
                    self.columns[column].pop(num)
        self.clear_all()


def on_closing(root, refresh_var):
    var.robots_thread_is_active = ""
    root.after_cancel(refresh_var)
    root.destroy()


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
