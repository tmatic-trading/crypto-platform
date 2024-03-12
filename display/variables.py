import platform
import tkinter as tk
from collections import OrderedDict
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
    num_robots = 1
    bg_color = "gray98"
    title_color = "gray83"
    num_book = 21  # Must be odd
    frame_state = tk.Frame()
    frame_state.grid(row=0, column=0, sticky="W")
    labels = dict()
    labels_cache = dict()
    label_trading = tk.Label(frame_state, text="  TRADING: ")
    label_trading.pack(side="left")
    label_f9 = tk.Label(frame_state, text="OFF", fg="white")
    label_f9.pack(side="left")
    label_time = tk.Label()
    label_time.grid(row=0, column=1, sticky="E", columnspan=2)

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
    frame_3row_3col.grid(row=2, column=1, sticky="N" + "S" + "W" + "E")
    frame_3row_3col.grid_columnconfigure(0, weight=1)
    frame_3row_3col.grid_rowconfigure(0, weight=1)

    # frame_3row_3col.grid_rowconfigure(1, weight=200)
    orderbook_frame = tk.Frame(frame_3row_3col, padx=2, pady=0)
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
    root.grid_columnconfigure(2, weight=10)
    root.grid_rowconfigure(0, weight=1)
    root.grid_rowconfigure(1, weight=1)
    root.grid_rowconfigure(2, weight=200)
    root.grid_rowconfigure(3, weight=1)
    root.grid_rowconfigure(4, weight=1)

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

    # Orders widget

    pw_orders_trades = tk.PanedWindow(
        frame_3row_4col, orient="vertical", sashrelief="raised", bd=0
    )
    pw_orders_trades.pack(fill="both", expand=True)

    frame_orders = tk.Frame(pw_orders_trades)
    frame_orders.pack(fill="both", expand="yes")

    # Trades/Funding widget

    notebook = ttk.Notebook(pw_orders_trades, padding=0)
    style = ttk.Style()
    style.configure("TNotebook", borderwidth=0)
    style.configure("TNotebook.Tab", background=title_color)
    style.map("TNotebook.Tab", background=[("selected", bg_color)])
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
    trades_display_counter = 0
    funding_display_counter = 0
    symb_book = ""
    book_window_trigger = "off"
    price_rounding = OrderedDict()
    order_window_trigger = "off"


class GridTable(Variables):
    def __init__(
        self,
        frame: tk.Frame,
        name: str,
        size: int,
        title: list,
        title_on: bool = True, 
        canvas_height: int = None,
        bind = None,
        color: str = None,
        select: bool = None,
    ) -> None:
        self.color = color
        self.title_on = title_on
        self.mod = 1
        self.labels[name] = []
        self.labels_cache[name] = []
        width = len(title) * 70
        if not title_on:
            self.mod = 0
            size -= 1
        my_bg = self.bg_color if name != "robots" and name != "exchange" else self.title_color
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
        sub = tk.Frame(canvas, bg=self.bg_color)
        positions_id = canvas.create_window((0, 0), window=sub, anchor="nw")
        canvas.bind(
            "<Configure>",
            lambda event, id=positions_id, pos=canvas: event_width(event, id, pos),
        )
        sub.bind("<Configure>", lambda event: event_config(event, canvas))
        canvas.bind("<Enter>", lambda event: on_enter(event, canvas, scroll))
        canvas.bind("<Leave>", lambda event: on_leave(event, canvas))
        for row in range(size):
            lst = []
            cache = []
            if len(self.labels[name]) <= row:
                for title_name in title:
                    lst.append(tk.Label(sub, text=title_name, pady=0))
                    cache.append(title_name + str(row))
                self.labels[name].append(lst)
                self.labels_cache[name].append(cache)
            for column in range(len(title)):
                self.labels[name][row][column].grid(
                    row=row, column=column, sticky="N" + "S" + "W" + "E", padx=0, pady=0
                )
                if row > self.mod - 1:
                    if select:
                        color = "yellow" if row == self.mod else self.color
                    else:
                        color = self.color
                    self.labels[name][row][column]["text"] = ""
                    self.labels[name][row][column]["bg"] = color
                    if bind:
                        self.labels[name][row][column].bind(
                            "<Button-1>",
                            lambda event, row_position=row: bind(event, row_position),
                        )
                sub.grid_columnconfigure(column, weight=1)

    def reconfigure_table(self, widget: tk.Frame, table: str, action: str, number: int):
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
                    pass
                    # create_robot_grid(widget=widget, table=table, row=row)
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


class ListBoxTable(Variables):
    """
    The table contains a grid with one row in each column in which a Listbox
    is inserted. The contents of table rows are managed through Listbox tools
    in accordance with the row index.
    """

    def __init__(
        self, frame: tk.Frame, size: int, title: list, title_on: bool = True, bind=None, expand: bool = None
    ) -> None:
        self.title = title
        self.title_on = title_on
        self.mod = 1
        if title_on:
            self.height = 1
        else:
            self.height = 0
            self.mod = 0
        self.active_row = 1
        self.mod = 1
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
        self.listboxes = []
        for column, name in enumerate(title):
            value = [name,] if title_on else ["",]        
            vars = tk.Variable(value=value)
            self.listboxes.append(
                tk.Listbox(
                    self.sub,
                    listvariable=vars,
                    bd=0,
                    background=self.bg_color,
                    highlightthickness=0,
                    selectbackground=self.bg_color,
                    selectforeground="Black",
                    activestyle="none",
                    justify="center",
                    height=self.height,
                    width=0,
                    # selectmode=tk.SINGLE,
                )
            )
            if title_on:
                self.listboxes[column].itemconfig(0, bg=self.title_color)
            self.listboxes[column].grid(
                row=0, padx=0, column=column, sticky="N" + "S" + "W" + "E"
            )
            self.sub.grid_columnconfigure(column, weight=1)
            self.sub.grid_rowconfigure(0, weight=1)
            if bind:
                self.listboxes[column].bind("<<ListboxSelect>>", bind)
            for _ in range(size):
                lst = ["" for _ in range(len(self.title))]
                self.insert(elements=lst, row=1)

    def insert(self, row: int, elements: list) -> None:
        if not self.title_on:
            row -= 1
        self.height += 1
        for column, listbox in enumerate(self.listboxes):
            listbox.config(height=self.height)
            listbox.insert(row, elements[column])

    def delete(self, row: int) -> None:
        if not self.title_on:
            row -= 1
        self.height -= 1
        for listbox in self.listboxes:
            listbox.config(height=self.height)
            listbox.delete(row)

    def update(self, row: int, elements: list) -> None:
        if not self.title_on:
            row -= 1        
        color = self.listboxes[0].itemcget(row, "background")
        self.delete(row)
        self.insert(row, elements)
        self.paint(row, color)

    def paint(self, row: int, color: str) -> None:
        if not self.title_on:
            row -= 1
        for listbox in self.listboxes:
            listbox.itemconfig(row, bg=color)


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


def on_enter(event, canvas, scroll):
    if platform.system() == "Linux":
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
    if platform.system() == "Linux":
        canvas.unbind_all("<Button-4>")
        canvas.unbind_all("<Button-5>")
    else:
        canvas.unbind_all("<MouseWheel>")


def on_mousewheel(event, canvas, scroll):
    slider_position = scroll.get()
    if slider_position != (0.0, 1.0): # Scrollbar is not full
        if platform.system() == "Windows":
            canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")
        elif platform.system() == "Darwin":
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
