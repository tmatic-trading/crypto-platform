import platform
import tkinter as tk
import tkinter.font
import webbrowser
from datetime import datetime
from tkinter import ttk
from typing import Callable, Union

import services as service
from api.api import Markets
from common.data import Instrument
from common.variables import Variables as var

if platform.system() == "Windows":
    from ctypes import windll

    windll.shcore.SetProcessDpiAwareness(1)


class AutoScrollbar(tk.Scrollbar):
    def resize_init(self, on_scroll_resize):
        self.on_scroll_resize = on_scroll_resize

    def set(self, low, high):
        if float(low) <= 0.0 and float(high) >= 1.0:
            self.tk.call("grid", "remove", self)
            if hasattr(self, "trim_columns"):
                if self.trim_columns:
                    self.trim_columns.grid_forget()
        else:
            if hasattr(self, "on_scroll_resize"):
                self.on_scroll_resize()
            self.grid()
            if hasattr(self, "trim_columns"):
                if self.trim_columns:
                    self.trim_columns.grid(row=0, column=3)
        tk.Scrollbar.set(self, low, high)


def on_canvas_enter(event, canvas, scroll, ostype):
    if ostype == "Linux":
        canvas.bind_all(
            "<Button-4>",
            lambda event: on_canvas_mousewheel(event, canvas, scroll, ostype),
        )
        canvas.bind_all(
            "<Button-5>",
            lambda event: on_canvas_mousewheel(event, canvas, scroll, ostype),
        )
    else:
        canvas.bind_all(
            "<MouseWheel>",
            lambda event: on_canvas_mousewheel(event, canvas, scroll, ostype),
        )


def on_canvas_leave(event, canvas, ostype):
    if ostype == "Linux":
        canvas.unbind_all("<Button-4>")
        canvas.unbind_all("<Button-5>")
    else:
        canvas.unbind_all("<MouseWheel>")


def on_canvas_mousewheel(event, canvas, scroll, ostype):
    slider_position = scroll.get()
    if slider_position != (0.0, 1.0):  # Scrollbar is not full
        if ostype == "Windows":
            canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")
        elif ostype == "Mac":
            canvas.yview_scroll(int(-1 * event.delta), "units")
        else:
            if event.num == 4:
                canvas.yview_scroll(-1, "units")
            elif event.num == 5:
                canvas.yview_scroll(1, "units")


class ScrollFrame(tk.Frame):
    def __init__(self, parent: tk.Frame, bg: str, bd: int, trim=None):
        super().__init__(parent)
        canvas = tk.Canvas(parent, highlightthickness=0, bg=bg, bd=bd)
        canvas.grid(row=0, column=0, sticky="NSEW")
        parent.grid_columnconfigure(0, weight=1)
        parent.grid_rowconfigure(0, weight=1)
        scroll = AutoScrollbar(parent, orient="vertical")
        scroll.trim_columns = trim
        scroll.config(command=canvas.yview)
        scroll.grid(row=0, column=1, sticky="NS")
        canvas.config(yscrollcommand=scroll.set)
        page = tk.Frame(canvas, bg=bg, bd=0)
        id = canvas.create_window((0, 0), window=page, anchor="nw")
        canvas.bind(
            "<Configure>",
            lambda event, id=id, can=canvas: event_width(event, id, can, bd),
        )
        page.bind(
            "<Configure>",
            lambda event: event_config(event, canvas, page, 5),
        )
        canvas.bind(
            "<Enter>",
            lambda event: on_canvas_enter(event, canvas, scroll, Variables.ostype),
        )
        canvas.bind(
            "<Leave>", lambda event: on_canvas_leave(event, canvas, Variables.ostype)
        )
        self.__dict__ = page.__dict__

        def event_config(event, canvas_event: tk.Canvas, frame: tk.Frame, padx: int):
            canvas_event.configure(scrollregion=canvas_event.bbox("all"))
            service.wrap(frame=frame, padx=padx)

        def event_width(event, canvas_id, canvas_event: tk.Canvas, bd):
            canvas_event.itemconfig(canvas_id, width=event.width - bd * 2)


class CustomButton(tk.Frame):
    def __init__(
        self, root, master, text, bg, fg, command=None, menu_items=None, **kwargs
    ):
        super().__init__(master, **kwargs)
        self.label = tk.Label(self, text=text, bg=bg, fg=fg)
        self.label.pack(fill="both")
        self.root = root
        # self.config(bg=bg)
        self.name = text
        self.bg = bg
        self.fg = fg
        self.command = command
        self.menu_items = menu_items
        self.state = None

        # Initialize the menu
        self.menu = tk.Menu(self, tearoff=0)
        if menu_items:
            for item in menu_items:
                if item == "<F3> Reload All":
                    self.menu.add_separator()
                self.menu.add_command(
                    label=item, command=lambda value=item: self.on_command(value)
                )

        # Tracks if the menu is posted or not as there is no direct built-in
        # method to check if the tk.Menu widget is currently posted (visible)
        # or not.
        self.menu_posted = False

        self.label.bind("<ButtonPress-1>", self.on_press)
        root.bind("<Button>", self.check_click_outside)
        root.bind("<Escape>", self.on_escape)
        root.bind("<FocusOut>", self.on_escape)
        self.label.bind("<Enter>", self.on_enter)
        self.label.bind("<Leave>", self.on_leave)

    def hide_menu(self):
        self.menu.unpost()
        self.menu_posted = False

    def on_escape(self, event):
        """
        This function triggers the unpost() method
        since not every OS or Python version makes it by
        default after ESC press
        """
        if self.menu_posted:
            self.hide_menu()

    def check_click_outside(self, event):
        """
        This function triggers the unpost() method
        since not every OS or Python version makes it by
        default after a mouse-click outside the button
        """
        mouse_x = self.winfo_pointerx()
        mouse_y = self.winfo_pointery()
        # Get the button bounds
        menu_x1, menu_y1, menu_x2, menu_y2 = (
            self.label.winfo_rootx(),
            self.label.winfo_rooty(),
            self.label.winfo_rootx() + self.label.winfo_width(),
            self.label.winfo_rooty() + self.label.winfo_height(),
        )
        # Check if the click is outside the button
        if not (menu_x1 <= mouse_x <= menu_x2 and menu_y1 <= mouse_y <= menu_y2):
            if self.menu_posted:
                self.hide_menu()
        else:
            if Variables.ostype == "Mac":
                self.menu_posted = False

    def on_command(self, value):
        self.menu_posted = False
        self.command(value)

    def on_enter(self, event):
        if self.state != "Disabled":
            self.label.config(bg=Variables.bg_active)

    def on_leave(self, event):
        self.label.config(bg=self.bg, fg=self.fg)

    def on_press(self, event):
        if self.menu_items:
            if self.menu_posted:
                self.hide_menu()
            else:
                # Get the coordinates of the button relative to the root window
                x = self.winfo_rootx()
                y = self.winfo_rooty() + self.winfo_height()
                # Show the menu at the bottom-left corner of the button
                self.menu.post(x, y)
                self.menu_posted = True
        else:
            if self.state != "Disabled":
                self.command(self.name)


class Variables:
    root = tk.Tk()
    root.bind("<F7>", lambda event: Variables.on_bot_menu(event))
    root.bind("<F8>", lambda event: Variables.on_settings())
    root.bind("<F9>", lambda event: on_trade_state(event))
    root.title(var.platform_name)
    screen_width = root.winfo_screenwidth()
    screen_height = root.winfo_screenheight()
    if screen_width > 1440:
        window_ratio = 0.75
        adaptive_ratio = 0.9
    elif screen_width > 1366:
        window_ratio = 0.77
        adaptive_ratio = 0.93
    elif screen_width > 1280:
        window_ratio = 0.8
        adaptive_ratio = 0.95
    elif screen_width > 1024:
        window_ratio = 0.85
        adaptive_ratio = 0.97
    else:
        window_ratio = 1
        adaptive_ratio = 1
    window_width = int(screen_width * window_ratio)
    window_height = int(screen_height * 0.8)
    root.geometry("{}x{}".format(window_width, window_height))
    all_width = window_width
    left_width = window_width
    pw_ratios = {}
    text_line_limit = 300

    if platform.system() == "Windows":
        ostype = "Windows"
        slash = "\\"
    elif platform.system() == "Darwin":
        ostype = "Mac"
        slash = "/"
    else:
        ostype = "Linux"
        slash = "/"

    num_robots = 1
    num_book = 14  # Must be even
    col1_book = 0

    pw_main = tk.PanedWindow(
        root, orient=tk.HORIZONTAL, sashrelief="raised", bd=0, sashwidth=0
    )
    pw_main.pack(fill="both", expand="yes")

    # Adaptive frame to the left, always visible
    frame_left = tk.Frame()
    frame_left.pack(fill="both", expand="yes")
    root.bind("<Configure>", lambda event: root_dimensions(event))

    # Frame to the right, always blank
    frame_right = tk.Frame()
    frame_right.pack(fill="both", expand="yes")

    # Top state frame: trading on/off, time
    frame_state = tk.Frame(frame_left)
    frame_state.grid(row=0, column=0, sticky="NSWE")
    frame_left.grid_columnconfigure(0, weight=1)
    frame_left.grid_rowconfigure(0, weight=0)

    label_trading = tk.Label(frame_state, text="  TRADING: ")

    # Color map and styles
    fg_color = label_trading["foreground"]
    fg_select_color = fg_color
    bg_changed = "gold"
    green_color = "#07b66e"
    red_color = "#f53661"
    white_color = "#FFFFFF"
    black_color = "#000000"
    gray_color = "#777777"
    warning_color = "#11a0e1"  # "#36adf5"  # "#7e9cbd"
    light_gray_color = "gray92"

    line_height = tkinter.font.Font(font="TkDefaultFont").metrics("linespace")
    symbol_width = tkinter.font.Font().measure("01234567890.") / 12
    symbol_height = tkinter.font.nametofont("TkDefaultFont").actual()["size"]
    button_height = 20
    style = ttk.Style()
    disabled_fg = style.lookup("TEntry", "foreground", ("disabled",))
    current_font = tkinter.font.nametofont(tk.Label().cget("font"))
    bold_font = current_font.copy()
    bold_font.config(weight="bold")

    # Paned window: up - information field, down - the rest interface
    pw_info_rest = tk.PanedWindow(
        frame_left, orient=tk.VERTICAL, sashrelief="raised", bd=0
    )

    # Information field
    frame_info = tk.Frame(pw_info_rest)
    frame_info.pack(fill="both", expand="yes")

    menu_frame = tk.Frame(pw_info_rest)
    menu_frame.pack(fill="both", expand="yes")

    # This technical PanedWindow contains most frames and widgets
    pw_rest1 = tk.PanedWindow(
        menu_frame, orient=tk.HORIZONTAL, sashrelief="raised", bd=0, sashwidth=0
    )
    # pw_rest1.pack(fill="both", expand="yes")

    # This technical PanedWindow contains orderbook, instruments, positions,
    # orders, trades, fundings, results, account, bots
    pw_rest2 = tk.PanedWindow(
        pw_rest1,
        orient=tk.HORIZONTAL,
        sashrelief="raised",
        bd=0,
        sashwidth=0,
        height=1,
    )
    pw_rest2.pack(fill="both", expand="yes")

    # This technical PanedWindow contains instruments, positions, orders,
    # trades, fundings, results, account, bots
    pw_rest3 = tk.PanedWindow(pw_rest2, orient=tk.VERTICAL, sashrelief="raised", bd=0)
    pw_rest3.pack(fill="both", expand="yes")

    # Frame for instruments and their positions
    frame_instrument = tk.Frame(pw_rest3)

    # This technical PanedWindow contains positions, orders, trades, fundings,
    # results, account, bots
    pw_rest4 = tk.PanedWindow(pw_rest3, orient=tk.VERTICAL, sashrelief="raised", bd=0)
    pw_rest4.pack(fill="both", expand="yes")

    style.configure("free.TEntry", foreground=fg_color)
    style.configure("used.TEntry", foreground=red_color)
    # bg_combobox = style.lookup('TCombobox', 'fieldbackground')
    style.map(
        "changed.TCombobox",
        selectbackground=[("readonly", "")],
        selectforeground=[("readonly", fg_color)],
        fieldbackground=[("readonly", bg_changed)],
    )
    style.map(
        "default.TCombobox",
        selectbackground=[("readonly", "")],
        selectforeground=[("readonly", fg_color)],
    )

    if platform.system() == "Darwin":
        # ostype = "Mac"
        bg_color = frame_state["background"]
        title_color = bg_color
        light_gray_color = tk.Text()["background"]
        book_color = title_color
        bg_select_color = "systemSelectedTextBackgroundColor"
        bg_active = bg_select_color
    else:
        style.theme_use("default")
        frame_state.configure(bg="grey82")
        bg_color = "white"
        book_color = light_gray_color
        # if platform.system() == "Windows":
        #     ostype = "Windows"
        # else:
        #     ostype = "Linux"
        style.map(
            "Treeview",
            background=[("selected", "#b3d7ff")],
            foreground=[("selected", fg_color)],
        )
        style.map(
            "menu.Treeview",
            background=[("selected", "invalid", "#b3d7ff")],
        )
        style.map(
            "bots.Treeview",
            background=[("selected", "#b3d7ff")],
        )
        title_color = frame_state["background"]
        label_trading.config(bg=title_color)
        bg_select_color = "#b3d7ff"
        bg_active = bg_select_color
        sell_bg_color = "#feede0"
        buy_bg_color = "#e3f3cf"
        frame_right.configure(background=title_color)
    style.configure(
        "Treeview",
        foreground=fg_color,
    )
    style.layout(
        "Treeview.Item",
        [
            (
                "Treeitem.padding",
                {
                    "sticky": "nswe",
                    "children": [
                        ("Treeitem.indicator", {"side": "left", "sticky": ""}),
                        ("Treeitem.image", {"sticky": "e"}),
                        ("Treeitem.text", {"sticky": "nswe"}),
                    ],
                },
            )
        ],
    )
    # style.configure("Treeview.Item", padding=(0, 0, 0, 0))
    style.configure(
        "market.Treeview",
        fieldbackground=title_color,
        background=title_color,
        rowheight=line_height * 3,
    )
    style.configure(
        "orderbook.Treeview",
        fieldbackground=book_color,
        background=book_color,
        # highlightthickness=0,
        borderwidth=0,
    )
    style.configure(
        "menu.Treeview",
        fieldbackground=title_color,
        background=title_color,
    )
    style.configure(
        "bots.Treeview",
        fieldbackground=title_color,
        background=title_color,
    )
    style.configure(
        "option.Treeview",
        rowheight=int(line_height * 1.5),
    )
    style.configure("Treeview.Heading", foreground=fg_color)
    style.configure(
        "TNotebook", borderwidth=0, background=light_gray_color, tabposition="n"
    )
    style.configure("TNotebook.Tab", background=light_gray_color)
    fg_disabled = tk.Entry()["disabledforeground"]
    bg_disabled = title_color  # tk.Entry()["disabledbackground"]
    fg_normal = tk.Entry()["foreground"]

    # frame_state.config(background=title_color)
    # label_trading.config(background=title_color)

    # Menu widget
    """menu_button = tk.Menubutton(
        frame_state, text=" MENU ", relief=tk.FLAT, padx=0, pady=0, bg=title_color
    )"""

    def on_menu_select(value):
        if value == "<F7> Bot Menu":
            Variables.on_bot_menu("None")
        elif value[:4] == "<F9>":
            on_trade_state("none")
        elif value == "<F3> Reload All":
            on_f3_reload()
        elif value == "<F8> Settings":
            Variables.on_settings()
        elif value == "- Update instruments":
            var.queue_info.put({"update"})

    menu_button = CustomButton(
        root,
        frame_state,
        " MENU ",
        title_color,
        fg_color,
        command=on_menu_select,
        menu_items=[
            "<F9> Trading ON",
            "<F8> Settings",
            "<F7> Bot Menu",
            "- Update instruments",
            "<F3> Reload All",
        ],  # , "Settings", "About"],
    )
    menu_button.pack(side="left", padx=4)

    menu_delimiter = tk.Label(frame_state, text="|", bg=title_color)
    menu_delimiter.pack(side="left", padx=0)

    label_trading.pack(side="left")
    label_f9 = tk.Label(
        frame_state, width=3, text="OFF", fg=white_color, bg=red_color, anchor="c"
    )
    label_f9.pack(side="left")

    label_time = tk.Label(frame_state, anchor="e", foreground=fg_color, bg=title_color)
    label_time.pack(side="right")
    last_gmtime_sec = 0

    pw_info_rest.grid(row=1, column=0, sticky="NSEW")
    frame_left.grid_rowconfigure(1, weight=1)

    # Information widget
    if ostype == "Mac":
        text_info = tk.Text(
            frame_info,
            highlightthickness=0,
            wrap=tk.WORD,
        )
    else:
        text_info = tk.Text(
            frame_info,
            bg=bg_color,
            highlightthickness=0,
            wrap=tk.WORD,
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

    # Intended to display the main area of the terminal or the minor pages
    # (bots info, settings)
    menu_robots = tk.Frame(menu_frame)

    # Settings page
    settings = tk.Frame(menu_frame)

    # One or more exchages is put in this frame
    frame_market = tk.Frame(pw_rest1)

    if ostype == "Mac":
        frame_symbol = tk.Frame(pw_rest2, bg=book_color, border=0)
    else:
        frame_symbol = tk.Frame(pw_rest2, bg=book_color, border=1, relief="sunken")

    frame_symbol_nested = ScrollFrame(frame_symbol, bg=book_color, bd=0)

    # Frame for the order book
    frame_orderbook = tk.Frame(frame_symbol_nested)
    frame_orderbook.pack(fill="both")

    # Frame for the new order form
    if ostype == "Mac":
        frame_order_form = tk.Frame(
            frame_symbol_nested, bg=book_color, border=1, relief="sunken"
        )
    else:
        frame_order_form = tk.Frame(frame_symbol_nested, bg=book_color, border=0)
    frame_order_form.pack(fill="both", expand=True)

    notebook_frames = {}

    pw_ratios[pw_info_rest] = {"ratio": 9, "name": "INFO_FRAME_RATIO"}
    pw_ratios[pw_rest3] = {"ratio": 4, "name": "SYMBOL_FRAME_RATIO"}
    pw_ratios[pw_rest4] = {"ratio": 2, "name": "NOTE_FRAME_RATIO"}

    # Frame for active orders
    frame_orders = tk.Frame()

    # Positions frame
    frame_positions = tk.Frame()

    # Trades frame
    frame_trades = tk.Frame()

    # Funding frame
    frame_funding = tk.Frame()

    # Account frame
    frame_account = tk.Frame()

    # Financial results by currencies
    frame_results = tk.Frame()

    # Bots frame
    frame_bots = tk.Frame()

    # Notebook tabs: Orders | Positions | Trades | Funding | Account | Results
    if ostype == "Mac":
        notebook = ttk.Notebook(pw_rest4, padding=(-9, 0, -9, -9))
    else:
        notebook = ttk.Notebook(pw_rest4, padding=0)
    notebook.bind(
        "<<NotebookTabChanged>>",
        lambda event: service.set_dotenv(
            dotenv_path=var.preferences,
            key="MAIN_TAB_SELECTED",
            value=str(Variables.notebook.index("current")),
        ),
    )

    pw_rest4.add(notebook)
    pw_rest4.add(frame_bots)
    pw_rest4.bind(
        "<Configure>",
        lambda event: Variables.resize_height(
            event, Variables.pw_rest4, Variables.pw_ratios[Variables.pw_rest4]["ratio"]
        ),
    )
    pw_rest4.bind(
        "<ButtonRelease-1>",
        lambda event: Variables.on_sash_move(event, Variables.pw_rest4),
    )

    pw_rest3.add(frame_instrument)
    pw_rest3.add(pw_rest4)
    pw_rest3.bind(
        "<Configure>",
        lambda event: Variables.resize_height(
            event, Variables.pw_rest3, Variables.pw_ratios[Variables.pw_rest3]["ratio"]
        ),
    )
    pw_rest3.bind(
        "<ButtonRelease-1>",
        lambda event: Variables.on_sash_move(event, Variables.pw_rest3),
    )

    pw_rest2.add(frame_symbol)
    pw_rest2.add(pw_rest3)
    pw_rest2.bind(
        "<Configure>",
        lambda event: Variables.resize_width(
            event, Variables.pw_rest2, Variables.window_width // 5.5, 4.5
        ),
    )

    pw_rest1.add(frame_market)
    pw_rest1.add(pw_rest2)
    pw_rest1.bind(
        "<Configure>",
        lambda event: Variables.resize_width(
            event, Variables.pw_rest1, Variables.window_width // 9.5, 6
        ),
    )

    pw_info_rest.add(frame_info)
    pw_info_rest.add(menu_frame)
    pw_info_rest.bind(
        "<Configure>",
        lambda event: Variables.resize_height(
            event,
            Variables.pw_info_rest,
            Variables.pw_ratios[Variables.pw_info_rest]["ratio"],
        ),
    )
    pw_info_rest.bind(
        "<ButtonRelease-1>",
        lambda event: Variables.on_sash_move(event, Variables.pw_info_rest),
    )

    pw_main.add(frame_left)
    pw_main.add(frame_right)
    pw_main.bind(
        "<Configure>",
        lambda event: Variables.resize_width(
            event, Variables.pw_main, Variables.window_width, 1
        ),
    )

    refresh_var = None
    nfo_display_counter = 0
    f9 = "OFF"
    f3 = False
    robots_window_trigger = "off"
    info_display_counter = 0
    handler_orderbook_symbol = tuple()
    book_window_trigger = "off"
    order_window_trigger = "off"
    table_limit = 200
    refresh_handler_orderbook = False
    refresh_bot_info = False
    bot_name = None
    bot_trades = dict()
    bot_orders_processing = False
    bot_event_prev = ""
    bot_menu_option = ""
    image_cancel = tk.PhotoImage(file="display/unsubscribe.png")
    empty_image = tk.PhotoImage(file="display/empty.png")

    # Bot menu widgets

    pw_menu_robots = tk.PanedWindow(
        menu_robots,
        orient=tk.HORIZONTAL,
        bd=0,
        sashwidth=0,
        height=1,
    )
    pw_menu_robots.pack(fill="both", expand="yes")
    info_frame = tk.Frame(pw_menu_robots, bg=bg_color)
    frame_bot_parameters = tk.Frame(info_frame)
    frame_bot_parameters.pack(fill="both", anchor="n")
    frame_bot_info = tk.Frame(info_frame)
    frame_bot_info.pack(fill="both", expand=True, anchor="n")
    pw_bot_info = tk.PanedWindow(
        frame_bot_info,
        orient=tk.VERTICAL,
        sashrelief="raised",
        bd=0,
    )
    pw_ratios[pw_bot_info] = {"ratio": 3, "name": "BOT_MENU_RATIO"}
    if ostype == "Mac":
        bot_note = ttk.Notebook(pw_bot_info, padding=(-9, 0, -9, -9))
    else:
        bot_note = ttk.Notebook(pw_bot_info, padding=0)
    bot_note.bind(
        "<<NotebookTabChanged>>",
        lambda event: service.set_dotenv(
            dotenv_path=var.preferences,
            key="BOT_TAB_SELECTED",
            value=str(Variables.bot_note.index("current")),
        ),
    )
    frame_strategy = tk.Frame(pw_bot_info)
    frame_strategy.pack(fill="both", expand="yes")
    bot_positions = tk.Frame(bot_note, bg=bg_color)
    bot_orders = tk.Frame(bot_note, bg=bg_color)
    bot_trades = tk.Frame(bot_note, bg=bg_color)
    bot_results = tk.Frame(bot_note, bg=bg_color)
    bot_log = tk.Frame(bot_note, bg=bg_color)
    bot_note.add(bot_positions, text="Positions")
    bot_note.add(bot_orders, text="Orders")
    bot_note.add(bot_trades, text="Trades")
    bot_note.add(bot_results, text="Results")
    bot_note.add(bot_log, text="Log")

    # Bot log widget
    if ostype == "Mac":
        text_bot_log = tk.Text(
            bot_log,
            highlightthickness=0,
            wrap=tk.WORD,
        )
    else:
        text_bot_log = tk.Text(
            bot_log,
            bg=bg_color,
            highlightthickness=0,
            wrap=tk.WORD,
        )
    text_bot_log.grid(row=0, column=0, sticky="NSEW")
    scroll_info = AutoScrollbar(bot_log, orient="vertical")
    scroll_info.config(command=text_bot_log.yview)
    scroll_info.grid(row=0, column=1, sticky="NS")
    text_bot_log.config(yscrollcommand=scroll_info.set)
    bot_log.grid_columnconfigure(0, weight=1)
    bot_log.grid_columnconfigure(1, weight=0)
    bot_log.grid_rowconfigure(0, weight=1)

    # Settings widgets

    s_title = tk.Frame(settings, bg=light_gray_color)
    s_title.pack(fill="both", side="top")
    s_top_line = tk.Frame(settings, bg=title_color)
    s_top_line.pack(fill="both")
    label_title = tk.Label(
        s_title,
        text="SETTINGS",
        bg=light_gray_color,
        font=("", symbol_height + 1, "bold"),
    )
    label_title.pack()

    s_main = tk.Frame(settings, bg=bg_color)
    s_main.pack(fill="both", expand=True)
    s_pw_main = tk.PanedWindow(
        s_main,
        orient=tk.HORIZONTAL,
        bd=0,
        sashwidth=0,
        height=1,
    )
    s_pw_main.pack(fill="both", expand="yes")
    s_left = tk.Frame(s_pw_main, padx=5, pady=5, bg=bg_color)
    s_right = tk.Frame(s_pw_main, bg=bg_color)
    s_pw_main.add(s_left)
    s_pw_main.add(s_right)
    v_line = tk.Frame(s_right, bg=light_gray_color)
    v_line.pack(fill="both", side="left")
    s_set = tk.Frame(s_right, padx=0, pady=0, bg=bg_color)
    s_set.pack(fill="both", expand=True)
    settings_page = ScrollFrame(s_set, bg=bg_color, bd=5)
    frame_tips = ScrollFrame(s_left, bg=light_gray_color, bd=5)
    s_label = tk.Label(frame_tips, text="Tips", bg=light_gray_color)
    s_label.config(font=("", symbol_height, "bold"))
    s_label.pack(anchor="nw")
    tips = tk.Label(
        frame_tips,
        text="",
        bg=light_gray_color,
        justify=tk.LEFT,
    )
    tips.pack(anchor="nw")
    s_pw_main.bind(
        "<Configure>",
        lambda event: Variables.resize_width(
            event, Variables.s_pw_main, Variables.window_width // 3.8, 3.8
        ),
    )

    # Instruments menu widgets

    frame_i_category = tk.Frame(
        root,
        highlightbackground=bg_select_color,
        highlightcolor=bg_select_color,
        highlightthickness=1,
    )
    frame_i_currency = tk.Frame(
        root,
        highlightbackground=bg_select_color,
        highlightcolor=bg_select_color,
        highlightthickness=1,
    )
    frame_i_list = tk.Frame(
        root,
        highlightbackground=bg_select_color,
        highlightcolor=bg_select_color,
        highlightthickness=1,
    )

    def resize_width(event, pw, start_width, min_ratio):
        ratio = pw.winfo_width() / start_width
        if ratio < min_ratio:
            my_width = pw.winfo_width() // min_ratio
        else:
            my_width = start_width
        pw.paneconfig(pw.panes()[0], width=my_width)

    def resize_height(event, pw, ratio):
        pw.paneconfig(pw.panes()[0], height=pw.winfo_height() // ratio)

    def on_sash_move(event, pw):
        panes = pw.winfo_children()
        Variables.pw_ratios[pw]["ratio"] = pw.winfo_height() / panes[0].winfo_height()
        if Variables.pw_ratios[pw]["ratio"] < 1.02:
            Variables.pw_ratios[pw]["ratio"] = 1.02
        service.set_dotenv(
            dotenv_path=var.preferences,
            key=Variables.pw_ratios[pw]["name"],
            value=str(round(Variables.pw_ratios[pw]["ratio"], 2)),
        )

    def on_bot_menu(event) -> None:
        Variables.pw_rest1.pack_forget()
        Variables.settings.pack_forget()
        Variables.menu_robots.pack(fill="both", expand="yes")

    def on_settings() -> None:
        Variables.pw_rest1.pack_forget()
        Variables.menu_robots.pack_forget()
        Variables.settings.pack(fill="both", expand="yes")

    def on_main(event="") -> None:
        Variables.settings.pack_forget()
        Variables.menu_robots.pack_forget()
        Variables.pw_rest1.pack(fill="both", expand="yes")

    # Change appearance according the last remembered parameters
    pref_params = service.load_preferences(root, window_width, window_height)
    root.geometry(
        "{}x{}+{}+{}".format(
            pref_params["ROOT_WIDTH"],
            pref_params["ROOT_HEIGHT"],
            pref_params["ROOT_X_POS"],
            pref_params["ROOT_Y_POS"],
        )
    )
    for pw, value in pw_ratios.items():
        if value["name"] in pref_params:
            pw_ratios[pw]["ratio"] = float(pref_params[value["name"]])


def on_trade_state(event) -> None:
    if Variables.f9 == "ON":
        Variables.menu_button.menu.entryconfigure(
            0, label="<F9> Trading " + Variables.f9
        )
        Variables.f9 = "OFF"
        Variables.label_f9.config(bg=Variables.red_color)
    elif Variables.f9 == "OFF":
        Variables.menu_button.menu.entryconfigure(
            0, label="<F9> Trading " + Variables.f9
        )
        Variables.f9 = "ON"
        Variables.label_f9.config(bg=Variables.green_color)
        for market in var.market_list:
            Markets[market].logNumFatal = ""
    Variables.label_f9["text"] = Variables.f9


def on_f3_reload() -> None:
    Variables.menu_robots.pack_forget()
    Variables.settings.pack_forget()
    Variables.pw_rest1.pack(fill="both", expand="yes")
    Variables.f3 = True


class TreeviewTable(Variables):
    def __init__(
        self,
        frame: tk.Frame,
        name: str,
        title: list,
        size: Union[int, list] = 0,
        style="",
        bind=None,
        hide=[],
        multicolor=False,
        autoscroll=False,
        hierarchy=False,
        lines=[],
        rollup=False,
        hover=True,
        selectmode="browse",
        cancel_scroll=False,
        headings=True,
        bold=False,
    ) -> None:
        self.frame: tk.Frame = frame
        self.bold = bold
        self.title = title
        self.max_rows = 200
        self.name = name
        self.title = title
        self.cache = list()
        self.bind = bind
        self.set_size(size)
        self.count = 0
        self.hierarchy = hierarchy
        self.lines = lines
        self.rollup = rollup
        self.active_row = 0
        self.hide = hide
        self.multicolor = multicolor
        frame.grid_columnconfigure(0, weight=1)
        frame.grid_rowconfigure(0, weight=1)
        if hierarchy:
            show = "tree headings"
            length = len(title)
        else:
            if headings:
                show = "headings"
            else:
                show = ""
            length = len(title) + 1
        columns = [num for num in range(1, length)]
        self.tree = ttk.Treeview(
            frame,
            style=style,
            columns=columns,
            show=show,
            selectmode=selectmode,
            height=self.size,
        )
        for num, name in enumerate(title, start=1):
            if hierarchy:
                if num == 1:
                    num = "#0"
                else:
                    num -= 1
            self.tree.heading(num, text=name)
            self.tree.column(num, anchor=tk.CENTER, width=50)
        if not cancel_scroll:
            if autoscroll:
                self.scroll = AutoScrollbar(frame, orient="vertical")
            else:
                self.scroll = tk.Scrollbar(frame, orient="vertical")
            self.scroll.config(command=self.tree.yview)
            self.tree.config(yscrollcommand=self.scroll.set)
            self.scroll.grid(row=0, column=1, sticky="NS")
        self.tree.grid(row=0, column=0, sticky="NSEW")
        self.children = list()
        self.children_hierarchical = dict()
        self.tree.tag_configure("Select", background=self.bg_select_color)
        self.tree.tag_configure("Buy", foreground=self.green_color)
        self.tree.tag_configure("Sell", foreground=self.red_color)
        self.tree.tag_configure("White", background=self.bg_color)
        self.tree.tag_configure("Normal", foreground=self.fg_color)
        self.tree.tag_configure("Reload", foreground=self.red_color)
        self.tree.tag_configure("Red", foreground=self.red_color)
        if self.ostype != "Mac":
            self.tree.tag_configure("Gray", background="gray90")
        else:
            self.tree.tag_configure("Gray", background=self.title_color)
            self.frame.config(borderwidth=1, relief="sunken")
        """self.tree.tag_configure(
            "Market", background=self.title_color, foreground=self.fg_color
        )"""
        self.tree.tag_configure("highlight", background=self.bg_select_color)
        self.tree.tag_configure("Bold", font=("", self.symbol_height, "bold"))
        if hover:
            self.tree.bind("<Motion>", self.on_hover)
            self.tree.bind("<Leave>", self.on_leave)
        if bind:
            self.tree.bind("<<TreeviewSelect>>", bind)
        self.iid_count = 0
        self.init()
        if self.hide:
            self.column_hide = []
            self.hide_num = 0
            hide_begin = list(self.tree["columns"])
            self.column_hide.append(tuple(hide_begin))
            for num, id_col in enumerate(self.hide, start=1):
                self.column_hide.append(hide_begin)
                self.column_hide[num].remove(id_col)
                hide_begin = list(self.column_hide[num])
                self.column_hide[num] = tuple(hide_begin)
        if self.multicolor:
            self.setup_color_cell()
            self.tree.bind("<Configure>", self.on_window_resize)
            self.scroll.resize_init(self.on_scroll_resize)
            self.tree.bind("<B1-Motion>", self.on_window_resize)
            # self.tree.update()

    def set_size(self, size):
        if isinstance(size, int):
            self.lst = [num for num in range(size)]
            self.size = size
        else:
            self.lst = size
            self.size = len(size)

    def init(self):
        self.clear_all()
        self.cache = dict()
        if self.hierarchy:
            self.init_hierarchical()
        else:
            blank = ["" for _ in self.title]
            self.tree.config(height=len(self.lst))
            for item in self.lst:
                if self.bold:
                    self.tree.insert("", tk.END, iid=item, values=blank, tags="Bold")
                else:
                    self.tree.insert("", tk.END, iid=item, values=blank)
                self.cache[item] = blank
            self.children = self.tree.get_children()

    def init_hierarchical(self):
        self.tree.column("#0", anchor=tk.W)
        if len(self.title) > 1:
            self.tree.column("1", anchor=tk.W)
        for line in self.lines:
            self.tree.insert("", tk.END, text=line, iid=line, open=True, tags="Gray")
            self.cache[line] = line
            self.children_hierarchical[line] = self.tree.get_children(line)
        self.children = self.tree.get_children()

    def insert(self, values: list, market="", iid="", configure="", position=0) -> None:
        if not iid:
            self.iid_count += 1
            iid = self.iid_count
        self.tree.insert(
            "", position, iid=iid, values=values, tags=configure, text=market
        )
        self.children = self.tree.get_children()
        if len(self.children) > self.max_rows:
            self.delete()

    def insert_parent(self, parent: str, configure="", text="") -> None:
        if not text:
            text = parent
        self.tree.insert("", tk.END, text=text, iid=parent, open=True, tags=configure)
        self.children = self.tree.get_children()
        self.children_hierarchical[parent] = self.tree.get_children(parent)

    def insert_hierarchical(
        self,
        parent: str,
        iid: str,
        values=[],
        configure="",
        text="",
        indx="end",
        image="",
    ):
        self.tree.insert(
            parent, indx, iid=iid, values=values, tags=configure, text=text, image=image
        )
        self.children_hierarchical[parent] = self.tree.get_children(parent)
        self.children = self.tree.get_children()
        self.cache[iid] = values

    def delete(self, iid="") -> None:
        if not iid:
            iid = self.children[len(self.children) - 1]
        self.tree.delete(iid)
        self.children = self.tree.get_children()
        if iid in self.children_hierarchical:
            del self.children_hierarchical[iid]

    def delete_hierarchical(self, parent: str, iid="") -> None:
        self.tree.delete(iid)
        self.children_hierarchical[parent] = self.tree.get_children(parent)
        del self.cache[iid]

    def update(self, row: int, values: list, text="") -> None:
        self.tree.item(row, values=values, text=text)

    def update_hierarchical(self, parent: str, iid: str, values: list) -> None:
        self.tree.item(iid, values=values)

    def paint(self, row: Union[int, str], configure: str) -> None:
        row = str(row)
        self.tree.item(row, tags=configure)
        """if self.tree.selection():
            selected = self.tree.selection()[0]
        if self.name == "market":
            if configure == "Reload" and row == selected:
                self.style.map(
                    "market.Treeview",
                    foreground=[("selected", self.red_color)],
                )
            else:
                self.style.map(
                    "market.Treeview",
                    foreground=[("selected", self.fg_color)],
                )"""

    def clear_all(self, market=None):
        if not market:
            if self.hierarchy:
                for line in self.lst:
                    self.tree.delete(*self.children_hierarchical[line])
                    self.children_hierarchical[line] = self.tree.get_children(line)
            self.tree.delete(*self.children)
        else:
            for child in self.children:
                line = self.tree.item(child)
                if line["text"] == market:
                    self.delete(iid=child)
        self.children = self.tree.get_children()

    def append_data(self, rows: list, market: str) -> list:
        data = list()
        if self.children:
            for child in self.children:
                line = self.tree.item(child)
                if line["text"] != market:
                    data.append(line["values"])
        data += rows
        self.clear_all()
        data = list(
            map(lambda x: x + [datetime.strptime(x[0], "%y%m%d %H:%M:%S")], data)
        )
        data.sort(key=lambda x: x[-1], reverse=True)
        data = list(map(lambda x: x[:-1], data))

        return reversed(data[: self.max_rows])

    def set_selection(self, index=0):
        self.tree.selection_set(index)

    def setup_color_cell(self):
        self._canvas = list()
        for _ in range(20):
            lst = list()
            for num in range(len(self.title)):
                lst.append(tk.Canvas(self.tree, borderwidth=0, highlightthickness=0))
                lst[num].text = lst[num].create_text(
                    10, self.line_height / 2, anchor="w"
                )
                lst[num].up = False
            self._canvas.append(lst)

    def show_color_cell(
        self,
        text: str,
        row: int,
        column: int,
        bg_color: str,
        fg_color: str,
    ):
        canvas = self._canvas[row][column]
        s_length = self.symbol_width * len(text)
        canvas.config(background=bg_color)
        canvas.itemconfigure(canvas.text, text=text, fill=fg_color)
        canvas.txt = text
        bbox = self.tree.bbox(self.children[row], column + 1)
        if bbox:
            x, y, width, height = bbox
            canvas.configure(width=width, height=height)
            canvas.coords(canvas.text, (max(0, (width - s_length)) / 2, height / 2))
            canvas.place(x=x, y=y)
            canvas.up = True
        else:
            canvas.up = "hidden"

    def resize_color_cell(self, bbox: tuple, row: int, column: int):
        x, y, width, height = bbox
        canvas = self._canvas[row][column]
        s_length = self.symbol_width * len(canvas.txt)
        canvas.configure(width=width, height=height)
        canvas.coords(canvas.text, (max(0, (width - s_length)) / 2, height / 2))
        canvas.place(x=x, y=y)

    def hide_color_cell(self, row: int, column: int):
        canvas = self._canvas[row][column]
        canvas.configure(width=0, height=0)
        canvas.place(x=0, y=0)
        canvas.up = False

    def clear_color_cell(self):
        for row in range(self.size):
            for column in range(len(self.title)):
                self.hide_color_cell(row, column)

    def on_window_resize(self, event):
        if self.children:
            for row in range(self.size):
                canvas_list = self._canvas[row]
                self.count += 1
                for column, canvas in enumerate(canvas_list):
                    bbox = self.tree.bbox(self.children[row], column + 1)
                    if bbox:
                        if canvas.up is True:
                            self.resize_color_cell(bbox, row, column)
                        elif canvas.up == "hidden":
                            x, y, width, height = bbox
                            canvas.configure(width=width, height=height)
                            s_length = self.symbol_width * len(canvas.txt)
                            canvas.coords(
                                canvas.text,
                                (max(0, (width - s_length)) / 2, height / 2),
                            )
                            canvas.place(x=x, y=y)
                            canvas.up = True
                    else:
                        if canvas.up is True:
                            self.hide_color_cell(row=row, column=column)
                            canvas.up = "hidden"

    def on_scroll_resize(self):
        self.on_window_resize("scroll")

    def on_rollup(self, iid=None, setup="parent"):
        parent = iid.split("!")[0]
        for child in self.children:
            if child != parent:
                self.tree.item(child, open=False)
        if parent in self.children:
            self.tree.item(parent, open=True)
        if setup == "parent":
            self.tree.selection_set(iid)
        else:
            if self.children_hierarchical:
                if iid == parent:
                    iid = self.children_hierarchical[parent][0]
                elif iid not in self.children_hierarchical[parent]:
                    iid = self.children_hierarchical[parent][0]
                self.tree.selection_set(iid)

    def on_hover(self, event):
        widget = event.widget
        item = widget.identify_row(event.y)
        if self.active_row != item:
            widget.tk.call(widget, "tag", "remove", "highlight")
            widget.tk.call(widget, "tag", "add", "highlight", item)
        self.active_row = item

    def on_leave(self, event):
        widget = event.widget
        widget.tk.call(widget, "tag", "remove", "highlight")


class SubTreeviewTable(TreeviewTable):
    def __init__(self, subtable=False, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.subtable: TreeviewTable = subtable
        self.frame.bind("<Leave>", self.on_leave_frame)

    def on_hover(self, event):
        item = self.tree.identify_row(event.y)
        self.del_sub(self.subtable)
        if self.active_row != item:
            self.active_row = item
            self.tree.tk.call(self.tree, "tag", "remove", "highlight")
            if item:
                self.tree.tk.call(self.tree, "tag", "add", "highlight", item)
                if self.subtable and TreeTable.market.active_row:
                    self.display_subtable(item=item)
            else:
                self.del_sub(self)

    def display_subtable(self, item: str):
        ws = Markets[TreeTable.market.active_row]
        if self.name == "market":
            lst = ws.instrument_index.keys()
            x_pos = self.frame_market.winfo_width()
        elif self.name == "category":
            lst = ws.instrument_index[TreeTable.i_category.active_row].keys()
            x_pos = (
                self.frame_market.winfo_width() + self.frame_i_category.winfo_width()
            )
        elif self.name == "currency":
            lst = ws.instrument_index[TreeTable.i_category.active_row][
                TreeTable.i_currency.active_row
            ]
            x_pos = (
                self.frame_market.winfo_width()
                + self.frame_i_category.winfo_width()
                + self.frame_i_currency.winfo_width()
            )
        y_pos = (
            self.tree.winfo_rooty()
            - self.root.winfo_rooty()
            + self.tree.bbox(item=item)[1]
            + self.tree.bbox(item=item)[3] // 2
        )
        self.subtable.clear_all()
        for item in reversed(lst):
            self.subtable.insert(values=[item], iid=item)
        self.subtable.tree.column("1", width=200)
        rows = len(self.subtable.tree.get_children())
        if rows > 20:
            rows = 20
            self.subtable.scroll.grid(row=0, column=1, sticky="NS")
        else:
            self.subtable.scroll.grid_forget()
        height = TreeTable.market.tree.bbox(TreeTable.market.tree.get_children()[0])[1]
        y_pos -= height * (rows + 1) // 2
        y_pos = max(y_pos, 0)
        self.subtable.tree.config(height=rows)
        self.subtable.frame.place(x=x_pos, y=y_pos)

    def on_leave(self, event):
        height = self.tree.winfo_height()
        x, y = self.root.winfo_pointerxy()
        pos_y = self.tree.winfo_rooty()
        if y < pos_y or y >= pos_y + height:
            self.del_sub(TreeTable.market)
            TreeTable.market.tree.tk.call(
                TreeTable.market.tree, "tag", "remove", "highlight"
            )

    def on_leave_frame(self, event):
        x, y = self.root.winfo_pointerxy()
        if not self.subtable:
            if x >= self.frame.winfo_width() + self.frame.winfo_rootx():
                self.del_sub(TreeTable.market)
                TreeTable.market.tree.tk.call(
                    TreeTable.market.tree, "tag", "remove", "highlight"
                )

    def del_sub(self, widget):
        """
        Deletes all nested tables cascadingly, starting with the subtable of
        this table.
        """
        if widget:
            if widget.subtable:
                widget.subtable.frame.place(x=-1000, y=-1000)
                widget.active_row = ""
                self.del_sub(widget.subtable)


class TreeTable:
    instrument: TreeviewTable
    account: TreeviewTable
    orderbook: TreeviewTable
    market: SubTreeviewTable
    results: TreeviewTable
    trades: TreeviewTable
    funding: TreeviewTable
    orders: TreeviewTable
    position: TreeviewTable
    bots: TreeviewTable
    bot_menu: TreeviewTable
    bot_info: TreeviewTable
    bot_position: TreeviewTable
    bot_orders: TreeviewTable
    bot_results: TreeviewTable
    i_category: SubTreeviewTable
    i_currency: SubTreeviewTable
    i_list: SubTreeviewTable
    calls: TreeviewTable
    strikes: TreeviewTable
    puts: TreeviewTable


class ClickLabel(tk.Label):
    """
    Creates a custom tkinter clickable label that either calls a method or
    opens a web page using the link parameter.
    """

    def __init__(
        self, parent: tk.Frame, link: str = None, method: Callable = None, **kwags
    ):
        super().__init__(parent, **kwags)
        self.config(cursor="hand2", fg="blue", bg=Variables.light_gray_color)
        if link:
            self.bind("<Button-1>", lambda e: on_label_click(link))
        else:
            self.bind("<Button-1>", method)
        self.pack(anchor="nw")


def on_label_click(url):
    webbrowser.open_new(url)


def text_ignore(event):
    return "break"  # Prevents further handling of the event


def resize_col(event, pw, ratio):
    pw.paneconfig(pw.panes()[0], width=pw.winfo_width() // ratio)


def trim_col_width(tview: TreeviewTable, cols: list):
    """
    Aligns the width of columns when a column is hidden.

    Parameters
    ----------
    tview: TreeviewTable
        TreeviewTable object.
    cols:
        List of columns to align.
    plus:
        If the table is hierarchical, then alignment is performed taking into
        account the first column #0.
    """
    if tview.hierarchy is True:
        plus = 1
    else:
        plus = 0
    width_all = tview.tree.winfo_width()
    if tview.tree == TreeTable.instrument.tree:
        ratio_1 = 1.85  # the ratio of the column "1" to the normal columns
        ratio_2 = 1.35  # the ratio of the column "2" to the normal columns
        width = int(width_all / (ratio_1 + ratio_2 + len(cols) + plus - 2))
        width_1 = int(width * ratio_1)
        width_2 = int(width * ratio_2)
    else:
        width = width_all // (len(cols) + plus)
        width_1 = width
        width_2 = width
    if plus != 0:
        tview.tree.column("#0", width=width)
    for col in cols:
        if col == "1":
            tview.tree.column(col, width=width_1)
        elif col == "2":
            tview.tree.column(col, width=width_2)
        else:
            tview.tree.column(col, width=width)


def root_dimensions(event):
    """
    Hide / show adaptive columns in order to save space in the tables
    """
    if var.market_list:
        # if hasattr(TreeTable, "instrument"):
        ratio = (
            Variables.frame_left.winfo_width() / Variables.left_width
            if Variables.left_width > 1
            else 1.0
        )
        if ratio < Variables.adaptive_ratio - 0.2:
            if TreeTable.instrument.hide_num != 3:
                TreeTable.instrument.tree.config(
                    displaycolumns=TreeTable.instrument.column_hide[3]
                )
                TreeTable.instrument.hide_num = 3
                trim_col_width(
                    TreeTable.instrument, TreeTable.instrument.column_hide[3]
                )
            if TreeTable.orders.hide_num != 3:
                TreeTable.orders.tree.config(
                    displaycolumns=TreeTable.orders.column_hide[3]
                )
                TreeTable.orders.hide_num = 3
                trim_col_width(TreeTable.orders, TreeTable.orders.column_hide[3])
            if TreeTable.trades.hide_num != 3:
                TreeTable.trades.tree.config(
                    displaycolumns=TreeTable.trades.column_hide[3]
                )
                TreeTable.trades.hide_num = 3
                trim_col_width(TreeTable.trades, TreeTable.trades.column_hide[3])
            if TreeTable.account.hide_num != 3:
                TreeTable.account.tree.config(
                    displaycolumns=TreeTable.account.column_hide[3]
                )
                TreeTable.account.hide_num = 3
                trim_col_width(TreeTable.account, TreeTable.account.column_hide[3])
        elif ratio < Variables.adaptive_ratio - 0.1:
            if TreeTable.instrument.hide_num != 2:
                TreeTable.instrument.tree.config(
                    displaycolumns=TreeTable.instrument.column_hide[2]
                )
                TreeTable.instrument.hide_num = 2
                trim_col_width(
                    TreeTable.instrument, TreeTable.instrument.column_hide[2]
                )
            if TreeTable.orders.hide_num != 2:
                TreeTable.orders.tree.config(
                    displaycolumns=TreeTable.orders.column_hide[2]
                )
                TreeTable.orders.hide_num = 2
                trim_col_width(TreeTable.orders, TreeTable.orders.column_hide[2])
            if TreeTable.trades.hide_num != 2:
                TreeTable.trades.tree.config(
                    displaycolumns=TreeTable.trades.column_hide[2]
                )
                TreeTable.trades.hide_num = 2
                trim_col_width(TreeTable.trades, TreeTable.trades.column_hide[2])
            if TreeTable.funding.hide_num != 2:
                TreeTable.funding.tree.config(
                    displaycolumns=TreeTable.funding.column_hide[2]
                )
                TreeTable.funding.hide_num = 2
                trim_col_width(TreeTable.funding, TreeTable.funding.column_hide[2])
            if TreeTable.account.hide_num != 2:
                TreeTable.account.tree.config(
                    displaycolumns=TreeTable.account.column_hide[2]
                )
                TreeTable.account.hide_num = 2
                trim_col_width(TreeTable.account, TreeTable.account.column_hide[2])
        elif ratio < Variables.adaptive_ratio:
            if TreeTable.instrument.hide_num != 1:
                TreeTable.instrument.tree.config(
                    displaycolumns=TreeTable.instrument.column_hide[1]
                )
                TreeTable.instrument.hide_num = 1
                trim_col_width(
                    TreeTable.instrument, TreeTable.instrument.column_hide[1]
                )
            if TreeTable.orders.hide_num != 1:
                TreeTable.orders.tree.config(
                    displaycolumns=TreeTable.orders.column_hide[1]
                )
                TreeTable.orders.hide_num = 1
                trim_col_width(TreeTable.orders, TreeTable.orders.column_hide[1])
            if TreeTable.trades.hide_num != 1:
                TreeTable.trades.tree.config(
                    displaycolumns=TreeTable.trades.column_hide[1]
                )
                TreeTable.trades.hide_num = 1
                trim_col_width(TreeTable.trades, TreeTable.trades.column_hide[1])
            if TreeTable.funding.hide_num != 1:
                TreeTable.funding.tree.config(
                    displaycolumns=TreeTable.funding.column_hide[1]
                )
                TreeTable.funding.hide_num = 1
                trim_col_width(TreeTable.funding, TreeTable.funding.column_hide[1])
            if TreeTable.account.hide_num != 1:
                TreeTable.account.tree.config(
                    displaycolumns=TreeTable.account.column_hide[1]
                )
                TreeTable.account.hide_num = 1
                trim_col_width(TreeTable.account, TreeTable.account.column_hide[1])
        elif ratio > Variables.adaptive_ratio:
            if TreeTable.instrument.hide_num != 0:
                TreeTable.instrument.tree.config(
                    displaycolumns=TreeTable.instrument.column_hide[0]
                )
                TreeTable.instrument.hide_num = 0
                trim_col_width(
                    TreeTable.instrument, TreeTable.instrument.column_hide[0]
                )
            if TreeTable.orders.hide_num != 0:
                TreeTable.orders.tree.config(
                    displaycolumns=TreeTable.orders.column_hide[0]
                )
                TreeTable.orders.hide_num = 0
                trim_col_width(TreeTable.orders, TreeTable.orders.column_hide[0])
            if TreeTable.trades.hide_num != 0:
                TreeTable.trades.tree.config(
                    displaycolumns=TreeTable.trades.column_hide[0]
                )
                TreeTable.trades.hide_num = 0
                trim_col_width(TreeTable.trades, TreeTable.trades.column_hide[0])
            if TreeTable.funding.hide_num != 0:
                TreeTable.funding.tree.config(
                    displaycolumns=TreeTable.funding.column_hide[0]
                )
                TreeTable.funding.hide_num = 0
                trim_col_width(TreeTable.funding, TreeTable.funding.column_hide[0])
            if TreeTable.account.hide_num != 0:
                TreeTable.account.tree.config(
                    displaycolumns=TreeTable.account.column_hide[0]
                )
                TreeTable.account.hide_num = 0
                trim_col_width(TreeTable.account, TreeTable.account.column_hide[0])

        # Save the root window dimensions and position
        now_width = Variables.root.winfo_width()
        now_height = Variables.root.winfo_height()
        now_x = Variables.root.winfo_x()
        now_y = Variables.root.winfo_y()
        if now_width != Variables.pref_params["ROOT_WIDTH"]:
            service.set_dotenv(
                dotenv_path=var.preferences,
                key="ROOT_WIDTH",
                value=str(now_width),
            )
            Variables.pref_params["ROOT_WIDTH"] = now_width
        if now_height != Variables.pref_params["ROOT_HEIGHT"]:
            service.set_dotenv(
                dotenv_path=var.preferences,
                key="ROOT_HEIGHT",
                value=str(now_height),
            )
            Variables.pref_params["ROOT_HEIGHT"] = now_height
        if now_x != Variables.pref_params["ROOT_X_POS"]:
            service.set_dotenv(
                dotenv_path=var.preferences,
                key="ROOT_X_POS",
                value=str(now_x),
            )
            Variables.pref_params["ROOT_X_POS"] = now_x
        if now_y != Variables.pref_params["ROOT_Y_POS"]:
            service.set_dotenv(
                dotenv_path=var.preferences,
                key="ROOT_Y_POS",
                value=str(now_y),
            )
            Variables.pref_params["ROOT_Y_POS"] = now_y

        if now_width != Variables.all_width:
            if now_width > Variables.window_width:
                t = var.platform_name.ljust((now_width - Variables.window_width) // 4)
                Variables.root.title(t)
            else:
                Variables.root.title(var.platform_name)
            Variables.all_width = now_width


class FormLabel(tk.Label):
    def __init__(
        self, master=None, row=0, column=0, colspan=None, sticky="NEWS", **kwargs
    ):
        super().__init__(master, **kwargs)
        self.configure(bg=Variables.book_color)
        self.grid(row=row, column=column, sticky=sticky, columnspan=colspan)


class ParametersFrame(tk.Label):
    def __init__(self, frame, row, name):
        self.sub = tk.Frame(frame, bg=Variables.book_color)
        self.sub.grid(row=row, column=0, sticky="NEWS")
        self.name = FormLabel(self.sub, text=name, row=0, column=0, sticky="W")
        self.value = FormLabel(self.sub, text=var.DASH, row=0, column=1, sticky="E")
        self.sub.grid_columnconfigure(0, weight=1)
        self.sub.grid_columnconfigure(1, weight=1)


def only_for_options(category):
    if "option" in category and "option_combo_" not in category:
        return True
    else:
        return False


class OrderForm:
    def title_on_hover(event):
        try:
            category = OrderForm.ws.Instrument[var.symbol].category
        except KeyError:
            return
        items = TreeTable.instrument.tree.selection()
        if "series" in items[0]:
            if only_for_options(category) is True:
                if "\n" in OrderForm.title["text"]:
                    text = "Option\nChain"
                else:
                    text = "Option Chain"
                OrderForm.title.config(bg=Variables.bg_select_color, text=text)

    def title_on_leave(event):
        title = service.order_form_title()
        OrderForm.title.config(bg=Variables.book_color, text=title)

    def title_on_select(event):
        if only_for_options(OrderForm.ws.Instrument[var.symbol].category) is True:
            items = TreeTable.instrument.tree.selection()
            if items:
                TreeTable.instrument.set_selection(items[0])

    if Variables.ostype != "Mac":
        ttk.Separator(Variables.frame_order_form, orient="horizontal").pack(fill="x")

    main = tk.Frame(Variables.frame_order_form, bg=Variables.book_color)
    ws: Markets = None
    instrument: Instrument
    main.pack(fill="both")
    main.grid_columnconfigure(0, weight=0)
    main.grid_columnconfigure(1, weight=1)
    main.grid_columnconfigure(2, weight=0)
    buttons = tk.Frame(main)
    buttons.grid_columnconfigure(0, weight=1)
    buttons.grid_columnconfigure(1, weight=1)
    sell_limit = tk.Button(buttons, text="Sell Limit")
    buy_limit = tk.Button(buttons, text="Buy Limit")
    buttons.grid(row=4, column=0, columnspan=3, sticky="NEWS")
    price_name = "price"
    qty_name = "quantity"
    price_var = tk.StringVar(name=price_name)
    qty_var = tk.StringVar(name=qty_name)
    warning = dict()
    entry_price = tk.Entry(
        main, width=10, bg=Variables.bg_color, textvariable=price_var
    )
    entry_quantity = tk.Entry(
        main, width=9, bg=Variables.bg_color, textvariable=qty_var
    )
    title = FormLabel(
        main, text=var.DASH, font=Variables.bold_font, row=0, column=0, colspan=3
    )
    title.bind("<Motion>", title_on_hover)
    title.bind("<Leave>", title_on_leave)
    title.bind("<ButtonRelease-1>", title_on_select)
    emi = FormLabel(main, text="Bot", row=1, column=0, sticky="W")
    quantity = FormLabel(main, text="Qty", row=2, column=0, sticky="W")
    price = FormLabel(main, text="Price", row=3, column=0, sticky="W")
    emi_var = tk.StringVar()
    options = [var.DASH]
    qty_currency = FormLabel(main, text="    ", row=2, column=2, sticky="W")
    price_currency = FormLabel(main, text="    ", row=3, column=2, sticky="W")
    option_emi = tk.OptionMenu(main, emi_var, *options)
    option_emi.grid(row=1, column=1, columnspan=2, sticky="W")
    entry_quantity.grid(row=2, column=1, sticky="NEWS")
    entry_price.grid(row=3, column=1, sticky="NEWS")
    buy_limit.grid(row=0, column=0, sticky="NEWS")
    sell_limit.grid(row=0, column=1, sticky="NEWS")

    # ttk.Separator(Variables.frame_order_form, orient="horizontal").pack(fill="x")

    # Instrument parameters

    parameters = tk.Frame(Variables.frame_order_form, bg=Variables.book_color)
    parameters.pack(fill="both")
    parameters.grid_columnconfigure(0, weight=1)
    market = ParametersFrame(parameters, 0, "Market")
    category = ParametersFrame(parameters, 1, "Category")
    settlcurrency = ParametersFrame(parameters, 2, "Settlement Currency")
    expiry = ParametersFrame(parameters, 3, "Expiry")
    markprice = ParametersFrame(parameters, 4, "Mark Price")
    state = ParametersFrame(parameters, 5, "State")
    ticksize = ParametersFrame(parameters, 6, "Tick Size")
    minOrderQty = ParametersFrame(parameters, 7, "Min Order Size")
    takerfee = ParametersFrame(parameters, 8, "Taker's Fee")
    makerfee = ParametersFrame(parameters, 9, "Maker's Fee")
    fundingRate = ParametersFrame(parameters, 10, "Funding Rate")
    delta = ParametersFrame(parameters, 11, "Delta")
    gamma = ParametersFrame(parameters, 12, "Gamma")
    vega = ParametersFrame(parameters, 13, "Vega")
    theta = ParametersFrame(parameters, 14, "Theta")
    rho = ParametersFrame(parameters, 15, "Rho")

    cache = dict()
    cache["markprice"] = var.DASH
    cache["funding"] = var.DASH
    cache["state"] = var.DASH
    cache["delta"] = var.DASH
    cache["gamma"] = var.DASH
    cache["vega"] = var.DASH
    cache["theta"] = var.DASH
    cache["rho"] = var.DASH
