import os
import tkinter as tk
from collections import OrderedDict
from pathlib import Path
from tkinter import StringVar, ttk

from dotenv import dotenv_values, set_key

import services as service
from common.variables import Variables as var
from display.tips import Tips
from display.variables import ClickLabel
from display.variables import Variables as disp


class SettingsApp:
    def __init__(self, root: tk.Frame):
        self.root_frame = root
        self.root_frame.config(bg=disp.bg_color)
        self.root_frame.grid_columnconfigure(0, weight=1)
        self.root_frame.grid_rowconfigure(0, weight=1)
        self.bg_select_color = disp.bg_select_color
        self.bg_entry = disp.light_gray_color
        self.bg_active = disp.bg_select_color
        self.fg_changed = disp.warning_color
        self.title_color = disp.title_color

        self.common_trace_changed = {}

        self.common_settings = OrderedDict()
        self.common_settings["MARKET_LIST"] = "Bitmex,Bybit,Deribit"
        self.common_settings["SQLITE_DATABASE"] = "tmatic.db"
        self.common_settings["ORDER_BOOK_DEPTH"] = "orderBook 7"
        self.common_settings["BOTTOM_FRAME"] = "Bots"
        self.common_settings["REFRESH_RATE"] = "5"
        self.common_settings["TESTNET"] = "YES"

        self.default_subscriptions = OrderedDict()
        self.default_subscriptions["Bitmex"] = var.default_symbol["Bitmex"]
        self.default_subscriptions["Bybit"] = var.default_symbol["Bybit"]
        self.default_subscriptions["Deribit"] = var.default_symbol["Deribit"]
        for setting in self.common_settings.keys():
            self.common_trace_changed[setting] = StringVar(name=setting + str(self))
            self.common_trace_changed[setting].set(self.common_settings[setting])
        self.common_defaults = {}
        self.common_flag = {}

        self.market_list = self.common_settings["MARKET_LIST"].split(",")
        self.market_settings = [
            "CONNECTED",
            "HTTP_URL",
            "WS_URL",
            "API_KEY",
            "API_SECRET",
            "TESTNET_HTTP_URL",
            "TESTNET_WS_URL",
            "TESTNET_API_KEY",
            "TESTNET_API_SECRET",
        ]
        self.market_color = {}
        self.market_defaults = {}
        self.market_trace = {}
        self.market_changed = {}
        self.market_saved = {}
        self.market_flag = {}
        for market in self.market_list:
            self.market_color[market] = self.bg_entry
            self.market_defaults[market] = {}
            self.market_changed[market] = {}
            self.market_saved[market] = {}
            self.market_flag[market] = {}
            for setting in self.market_settings:
                self.market_defaults[market][setting] = ""
                self.market_changed[market][setting] = ""
                self.market_saved[market][setting] = ""
                self.market_flag[market][setting] = 0
            if market == "Bitmex":
                self.market_defaults[market][
                    "HTTP_URL"
                ] = "https://www.bitmex.com/api/v1"
                self.market_defaults[market]["WS_URL"] = "wss://ws.bitmex.com/realtime"
                self.market_defaults[market][
                    "TESTNET_HTTP_URL"
                ] = "https://testnet.bitmex.com/api/v1"
                self.market_defaults[market][
                    "TESTNET_WS_URL"
                ] = "wss://testnet.bitmex.com/realtime"
            elif market == "Bybit":
                self.market_defaults[market]["HTTP_URL"] = "https://api.bybit.com/v5"
                self.market_defaults[market]["WS_URL"] = "wss://api.bybit.com/v5"
                self.market_defaults[market][
                    "TESTNET_HTTP_URL"
                ] = "https://api-testnet.bybit.com/v5"
                self.market_defaults[market][
                    "TESTNET_WS_URL"
                ] = "wss://api-testnet.bybit.com/v5"
            elif market == "Deribit":
                self.market_defaults[market]["HTTP_URL"] = "https://www.deribit.com"
                self.market_defaults[market]["WS_URL"] = "wss://ws.deribit.com/ws"
                self.market_defaults[market][
                    "TESTNET_HTTP_URL"
                ] = "https://test.deribit.com"
                self.market_defaults[market][
                    "TESTNET_WS_URL"
                ] = "wss://test.deribit.com/ws"
            self.market_defaults[market]["CONNECTED"] = "YES"
            self.market_defaults[market]["TESTNET"] = "YES"

        self.indent = "  "
        self.entry_width = 45

        # To keep track whether market is clicked
        self.click_market = "false"

        # To keep track of the selected frame
        self.selected_frame = None

        # If settings_flag value is not 0, than at least one setting is changed
        self.settings_flag = 0

        # DraggableFrame array
        self.settings_center = []

        self.env_file_settings = Path(var.settings)
        self.env_file_subscriptions = Path(var.subscriptions)
        self.setting_button = tk.Button(
            self.root_frame,
            bg=self.title_color,
            activebackground=self.bg_select_color,
            text="Settings Saved",
            command=lambda: self.save_dotenv("button"),
            anchor="center",
        )
        self.setting_button.config(state="disabled")
        self.initialized = False
        self.click_label = tk.Label()
        self.blank_lb = tk.Label()
        self.return_lb = tk.Label()
        self.return_main_page()

    def return_main_page(self):
        """
        Display a link to go to the main page. If there is no connected
        exchange, the link is replaced with a corresponding notification.
        """
        self.blank_lb.destroy()
        self.return_lb.destroy()
        self.blank_lb = tk.Label(disp.frame_tips, text=" ", bg=disp.light_gray_color)
        if "Fake" not in var.market_list:
            self.blank_lb.pack(anchor="nw")
            self.return_lb = ClickLabel(
                disp.frame_tips,
                text="Return to the main page",
                bg=disp.light_gray_color,
                cursor="hand2",
                justify=tk.LEFT,
                method=disp.on_main,
            )
        else:
            self.blank_lb.pack(anchor="nw")
            self.return_lb = tk.Label(
                disp.frame_tips,
                text="You don't have any exchanges connected at the moment.",
                bg=disp.light_gray_color,
                justify=tk.LEFT,
            )
            self.return_lb.pack(anchor="nw")
        service.wrap(disp.frame_tips, padx=5)

    def load(self):
        """
        Retrieves settings data from the files specified by the
        self.env_file_settings and self.env_file_subscriptions variables. If
        some variables are not found in the .env file, they are restored
        from their default values.
        """

        # Settings

        if not os.path.isfile(self.env_file_settings):
            # Set default settings for each market.
            for market in self.market_list:
                for setting in self.market_settings:
                    self.market_changed[market][setting] = self.market_defaults[market][
                        setting
                    ]
            self.save_dotenv("new")
        else:
            # Load common data from .env file
            missed_data = None
            dotenv_data = dotenv_values(self.env_file_settings)
            for setting in self.common_settings.keys():
                try:
                    self.common_defaults[setting] = dotenv_data[setting]
                except KeyError:
                    self.common_defaults[setting] = self.common_settings[setting]
                    missed_data = 1
                self.common_trace_changed[setting].set(self.common_defaults[setting])

            # Change markets sorting from default value (if differs)
            actual_list = self.common_defaults["MARKET_LIST"].split(",")
            actual_str = ""
            for market in self.market_list:
                if market not in actual_list:
                    # If this market is missing in .env file
                    actual_list.append(market)
                    missed_data = 1
            self.market_list = actual_list.copy()
            actual_str = self.get_str_markets()
            self.common_defaults["MARKET_LIST"] = actual_str
            self.common_trace_changed["MARKET_LIST"].set(actual_str)

            # Load data from .env file for each market

            for market in self.market_list:
                for setting in self.market_settings:
                    try:
                        self.market_saved[market][setting] = dotenv_data[
                            f"{market}_{setting}"
                        ].replace(f"_{market}", "")
                    except KeyError:
                        self.market_saved[market][setting] = self.market_defaults[
                            market
                        ][setting]
                        missed_data = 1
                    self.market_changed[market][setting] = self.market_saved[market][
                        setting
                    ]
            if missed_data is not None:
                os.remove(self.env_file_settings)
                self.save_dotenv("new")
        for setting in self.common_settings.keys():
            var.env[setting] = self.common_defaults[setting]
        for market in self.market_list:
            var.env[market] = dict()
            if self.market_saved[market]["CONNECTED"] == "YES":
                var.market_list.append(market)
            for setting in self.market_settings:
                var.env[market][setting] = self.market_saved[market][setting]

        # Symbol subscriptions

        if not os.path.isfile(self.env_file_subscriptions):
            self.save_dotenv_subscriptions(subscriptions=self.default_subscriptions)
        values = dotenv_values(self.env_file_subscriptions)
        for market in self.market_list:
            var.env[market]["SYMBOLS"] = list()
            try:
                sub = service.define_symbol_key(market=market)
                symbols = values[sub].replace(",", " ").split()
                if not symbols:
                    symbols = [var.default_symbol[market][0][0]]
                for symb in symbols:
                    var.env[market]["SYMBOLS"].append((symb, market))
            except KeyError:
                for symb in self.default_subscriptions[market]:
                    var.env[market]["SYMBOLS"].append((symb, market))
                set_key(
                    dotenv_path=self.env_file_subscriptions,
                    key_to_set=service.define_symbol_key(market=market),
                    value_to_set=str(self.default_subscriptions[market])[2:-2],
                )

        # Set parameters

        if var.market_list:
            var.current_market = var.market_list[0]
            var.symbol = var.env[var.current_market]["SYMBOLS"][0]
        book_depth = var.env["ORDER_BOOK_DEPTH"].split(" ")
        var.order_book_depth = book_depth[0]
        var.db_sqlite = var.env["SQLITE_DATABASE"]
        var.refresh_rate = min(max(100, int(1000 / int(var.env["REFRESH_RATE"]))), 1000)
        if var.order_book_depth != "quote":
            disp.num_book = int(book_depth[1]) * 2
        else:
            disp.num_book = 2
        if var.env["TESTNET"] == "YES":
            var.database_table = var.database_test
            var.platform_name = "Tmatic / testnet"
            disp.root.title(var.platform_name)
        else:
            var.database_table = var.database_real
            var.platform_name = "Tmatic"
            disp.root.title(var.platform_name)

    def save_dotenv_subscriptions(self, subscriptions: OrderedDict) -> None:
        """
        Saves instrument subscriptions to the file specified by the
        self.env_file_subscriptions variable.

        Parameters
        ----------
        subscriptions: OrderedDict
            Every dictionary item is a list of instrument symbols.
            Example:
                OrderedDict(
                    [('Bitmex', [('XBTUSDT', 'Bitmex')]),
                        ('Bybit', [('BTCUSDT', 'Bybit')]),
                            ('Deribit', [('BTC-PERPETUAL', 'Deribit')])]
                )
        """
        self.env_file_subscriptions.touch(mode=0o600)
        for market in self.market_list:
            for symbol in subscriptions[market]:
                set_key(
                    dotenv_path=self.env_file_subscriptions,
                    key_to_set=service.define_symbol_key(market=market),
                    value_to_set=symbol[0],
                )

    def init(self):
        """
        Create the initial static frames.
        """
        if not self.initialized:
            self.create_static_widgets()
            for i, market in enumerate(self.market_list):
                frame = DraggableFrame(
                    self.root_frame,
                    self,
                    market,
                    bd=0,
                )
                if self.market_saved[market]["CONNECTED"] == "YES":
                    frame.var.set(1)
                if i == 0:
                    self.selected_frame = frame
                self.settings_center.append(frame)
                frame.update_idletasks()
            self.reorder_frames()
            self.set_market_fields(self.market_list[0])

            # Bind event for focus change
            self.root_frame.bind("<FocusIn>", self.on_focus_in)

            self.initialized = True
            # service.wrap(frame=disp.frame_tips, padx=5)
        self.on_tip("SETTINGS")

    def on_focus_in(self, event):
        pass
        # self.reorder_frames()

    def reorder_frames(self):
        self.settings_center.sort(key=lambda f: f.winfo_y())
        total_height = self.static_widgets_height
        for frame in self.settings_center:
            frame_height = frame.winfo_reqheight()
            frame.place_configure(
                x=0,
                y=total_height + frame_height / 2,
                height=frame_height,
                relwidth=1.0,
            )
            total_height += frame_height
        # Update market_list
        self.market_list = [frame.market for frame in self.settings_center]
        # Remember the new market order
        self.common_trace_changed["MARKET_LIST"].set(self.get_str_markets())
        self.check_common_flag("MARKET_LIST")

    def update_positions(self, moving_frame):
        current_y = moving_frame.winfo_y()
        moving_index = self.settings_center.index(moving_frame)
        for i, frame in enumerate(self.settings_center):
            if frame is moving_frame:
                continue
            frame_y = frame.winfo_y()
            frame_height = frame.winfo_height()
            if current_y < frame_y and moving_index > i:
                self.settings_center.insert(i, self.settings_center.pop(moving_index))
                self.reorder_frames()
                break
            elif current_y > frame_y + frame_height and moving_index < i:
                self.settings_center.insert(
                    i + 1, self.settings_center.pop(moving_index)
                )
                self.reorder_frames()
                break

    def set_common_fields(self):
        """
        Fills the common settings with default values.
        """
        for setting, value in self.common_defaults.items():
            if setting != "MARKET_LIST":
                widget_type = self.entry_common[setting].winfo_class()
                if widget_type == "TCombobox":
                    self.entry_common[setting].set(value)
                else:
                    self.entry_common[setting].delete(0, tk.END)
                    self.entry_common[setting].insert(0, value)
                self.entry_common[setting].selection_clear()
                self.entry_common[setting].config(style=f"default.{widget_type}")

    def set_market_fields(self, market):
        """
        Fills the market settings with current values.
        """
        for setting, value in self.market_changed[market].items():
            if setting != "CONNECTED":
                widget_type = self.entry_market[setting].winfo_class()
                if widget_type == "TCombobox":
                    self.entry_market[setting].set(value)
                    if self.market_changed[market]["CONNECTED"] == "NO":
                        self.entry_market[setting].config(state="disabled")
                        self.market_label[setting].config(fg=disp.disabled_fg)
                    else:
                        self.entry_market[setting].config(state="readonly")
                        self.market_label[setting].config(fg=disp.fg_color)
                else:
                    self.entry_market[setting].config(state="normal")
                    self.entry_market[setting].delete(0, tk.END)
                    self.entry_market[setting].insert(0, value)
                    testnet_value = self.common_trace_changed["TESTNET"].get()
                    if testnet_value:
                        testnet_setting = setting.split("_")
                        if testnet_value == "YES":
                            if (
                                testnet_setting[0] != "TESTNET"
                                or self.market_changed[market]["CONNECTED"] == "NO"
                            ):
                                self.entry_market[setting].config(state="disabled")
                                self.market_label[setting].config(fg=disp.disabled_fg)
                            else:
                                self.entry_market[setting].config(state="normal")
                                self.market_label[setting].config(fg=disp.fg_color)
                        else:
                            if (
                                testnet_setting[0] == "TESTNET"
                                or self.market_changed[market]["CONNECTED"] == "NO"
                            ):
                                self.entry_market[setting].config(state="disabled")
                                self.market_label[setting].config(fg=disp.disabled_fg)
                            else:
                                self.entry_market[setting].config(state="normal")
                                self.market_label[setting].config(fg=disp.fg_color)
                self.entry_market[setting].selection_clear()
                if self.market_flag[market][setting] != 0:
                    self.entry_market[setting].config(style=f"changed.{widget_type}")
                else:
                    self.entry_market[setting].config(style=f"default.{widget_type}")
        self.root_frame.focus()

    def get_str_markets(self):
        return ",".join(str(x) for x in self.market_list)

    def insert_comment(self, file_path, comment):
        """
        Inserts a text comment into a file.
        """
        with open(file_path, "a") as file:
            file.write(f"# {comment}\n")

    def common_trace_callback(self, var, index, mode):
        """
        Called when the corresponding common setting changed.
        """
        if self.selected_frame is not None:
            self.set_market_fields(self.selected_frame.market)
        self.check_common_flag(var.replace(str(self), ""))

    def market_trace_callback(self, var, index, mode):
        """
        Called when the corresponding market setting changed.
        """
        var = var.replace(str(self), "")
        if self.selected_frame is not None and self.click_market == "false":
            market = self.selected_frame.market
            self.market_changed[market][var] = self.market_trace[var].get()
            self.check_market_flag(var, market)

    def check_common_flag(self, var):
        """
        Tracks and keeps changes for common settings until the moment they
        are saved.
        """
        if var in self.common_flag:
            if self.common_trace_changed[var].get() != self.common_defaults[var]:
                if self.common_flag[var] == 0:
                    self.settings_flag += 1
                    self.common_flag[var] = 1
                    if var != "MARKET_LIST":
                        widget_type = self.entry_common[var].winfo_class()
                        self.entry_common[var].config(style=f"changed.{widget_type}")
                        self.set_button_color(self.settings_flag, var)
                    else:
                        self.set_button_color(self.settings_flag, "MARKET")
            else:
                if self.common_flag[var] != 0:
                    self.settings_flag -= 1
                    self.common_flag[var] = 0
                    if var != "MARKET_LIST":
                        widget_type = self.entry_common[var].winfo_class()
                        self.entry_common[var].config(style=f"default.{widget_type}")
                        self.set_button_color(self.settings_flag, var)
                    else:
                        self.set_button_color(self.settings_flag, "MARKET")

    def market_color_update(self, market, color):
        for frame in self.settings_center:
            if frame.market == market:
                frame.check_box.config(fg=color, activeforeground=color)

    def check_market_flag(self, var, market):
        """
        Tracks and keeps changes for market settings until the moment they
        are saved.
        """
        if self.market_changed[market][var] != self.market_saved[market][var]:
            if self.market_flag[market][var] == 0:
                self.settings_flag += 1
                self.market_flag[market][var] = 1
                if var != "CONNECTED":
                    widget_type = self.entry_market[var].winfo_class()
                    self.entry_market[var].config(style=f"changed.{widget_type}")
                    self.set_button_color(self.settings_flag, var)
                else:
                    self.set_button_color(self.settings_flag, "MARKET")
                # self.market_color[market] = self.fg_changed
                self.market_color_update(market=market, color=self.fg_changed)

        else:
            if self.market_flag[market][var] != 0:
                self.settings_flag -= 1
                self.market_flag[market][var] = 0
                if var != "CONNECTED":
                    widget_type = self.entry_market[var].winfo_class()
                    self.entry_market[var].config(style=f"default.{widget_type}")
                    self.set_button_color(self.settings_flag, var)
                else:
                    self.set_button_color(self.settings_flag, "MARKET")
                # self.market_color[market] = self.bg_entry
                self.market_color_update(market=market, color=disp.fg_color)
                for setting in self.market_changed[market]:
                    if self.market_flag[market][setting] != 0:
                        # self.market_color[market] = self.fg_changed
                        self.market_color_update(market=market, color=self.fg_changed)
                        break
            else:
                self.market_color_update(market=market, color=disp.fg_color)
        if var == "TESTNET":
            self.set_market_fields(market)

    def set_button_color(self, flag, setting_name):
        if flag == 0:
            self.setting_button.configure(bg=self.title_color, text="Settings Saved")
            self.setting_button.config(state="disabled")
            self.on_tip(setting_name)
        else:
            self.setting_button.configure(bg=self.bg_select_color, text="Update")
            self.setting_button.config(state="active")

    def save_dotenv(self, status):
        """
        Saves common and market settings into .env file.
        """
        self.env_file_settings.touch(mode=0o600)
        for setting in self.common_settings.keys():
            set_key(
                dotenv_path=self.env_file_settings,
                key_to_set=setting,
                value_to_set=self.common_trace_changed[setting].get(),
            )
            self.common_defaults[setting] = self.common_trace_changed[setting].get()
        for market in self.market_list:
            if status != "button":
                self.insert_comment(self.env_file_settings, "")
            for setting in self.market_settings:
                set_key(
                    dotenv_path=self.env_file_settings,
                    key_to_set=f"{market}_{setting}",
                    value_to_set=self.market_changed[market][setting],
                )
                self.market_saved[market][setting] = self.market_changed[market][
                    setting
                ]
        self.set_all_flags_to_zero()
        if status != "new":
            self.set_market_fields(self.selected_frame.market)
            self.set_common_fields()
        self.set_button_color(0, "SETTINGS")
        self.setting_button.config(state="disabled")

    def set_all_flags_to_zero(self):
        self.settings_flag = 0
        for setting in self.common_settings.keys():
            self.common_flag[setting] = 0
        for market in self.market_list:
            self.market_color[market] = self.bg_entry
            for setting in self.market_settings:
                self.market_flag[market][setting] = 0
        for frame in self.settings_center:
            if frame != self.selected_frame:
                # frame.config(bg=self.market_color[frame.market])
                # frame.check_box.config(bg=self.market_color[frame.market])
                frame.check_box.config(fg=disp.fg_color)

    def create_static_widgets(self):
        widget_row = 0
        setting_label = tk.Label(
            self.root_frame,
            text="The settings are located in the .env.Settings file.\n",
            bg=disp.bg_color,
        )
        setting_label.grid(row=widget_row, column=0, sticky="W", columnspan=3)

        # Custom style for the Combobox and Entry widgets
        ttk.Style().map(
            "default.TCombobox",
            fieldbackground=[
                ("readonly", self.bg_entry),
                ("disabled", self.bg_entry),
            ],
        )
        ttk.Style().map(
            "changed.TCombobox",
            fieldbackground=[
                ("readonly", self.bg_entry),
                ("disabled", self.bg_entry),
            ],
            foreground=[
                ("readonly", self.fg_changed),
                ("disabled", self.fg_changed),
            ],
            selectforeground=[
                ("readonly", self.fg_changed),
                ("disabled", self.fg_changed),
            ],
        )
        ttk.Style().map(
            "default.TEntry",
            fieldbackground=[
                ("!disabled", self.bg_entry),
                ("disabled", self.bg_entry),
            ],
        )
        ttk.Style().map(
            "changed.TEntry",
            fieldbackground=[
                ("!disabled", self.bg_entry),  # disp.bg_color
                ("disabled", self.bg_entry),
            ],
            foreground=[
                ("!disabled", self.fg_changed),
                ("disabled", self.fg_changed),
            ],
        )

        # Draw grid for common settings
        self.entry_common = {}
        for setting in self.common_settings.keys():
            if setting != "MARKET_LIST":
                widget_row += 1
                tk.Label(self.root_frame, bg=disp.bg_color).grid(
                    row=widget_row, column=0
                )
                tk.Label(
                    self.root_frame,
                    text=setting + self.indent,
                    bg=disp.bg_color,
                ).grid(row=widget_row, column=1, sticky="W")
                self.common_trace_changed[setting].trace_add(
                    "write", self.common_trace_callback
                )
                if setting == "SQLITE_DATABASE":
                    self.entry_common[setting] = ttk.Entry(
                        self.root_frame,
                        width=self.entry_width,
                        textvariable=self.common_trace_changed[setting],
                        style="default.TEntry",
                    )
                elif setting == "ORDER_BOOK_DEPTH":
                    self.entry_common[setting] = ttk.Combobox(
                        self.root_frame,
                        width=self.entry_width,
                        textvariable=self.common_trace_changed[setting],
                        state="readonly",
                        style="default.TCombobox",
                    )
                    values = (
                        "quote",
                        "orderBook 2",
                        "orderBook 3",
                        "orderBook 4",
                        "orderBook 5",
                        "orderBook 6",
                        "orderBook 7",
                        "orderBook 8",
                        "orderBook 9",
                        "orderBook 10",
                    )
                    self.entry_common[setting]["values"] = values
                elif setting == "BOTTOM_FRAME":
                    self.entry_common[setting] = ttk.Combobox(
                        self.root_frame,
                        width=self.entry_width,
                        textvariable=self.common_trace_changed[setting],
                        state="readonly",
                        style="default.TCombobox",
                    )
                    self.entry_common[setting]["values"] = tuple(
                        disp.notebook_frames.keys()
                    )
                elif setting == "REFRESH_RATE":
                    self.entry_common[setting] = ttk.Combobox(
                        self.root_frame,
                        width=self.entry_width,
                        textvariable=self.common_trace_changed[setting],
                        state="readonly",
                        style="default.TCombobox",
                    )
                    values = ("1", "2", "3", "4", "5", "6", "7", "8", "9", "10")
                    self.entry_common[setting]["values"] = values
                elif setting == "TESTNET":
                    self.entry_common[setting] = ttk.Combobox(
                        self.root_frame,
                        width=self.entry_width,
                        textvariable=self.common_trace_changed[setting],
                        state="readonly",
                        style="default.TCombobox",
                    )
                    values = ("YES", "NO")
                    self.entry_common[setting]["values"] = values
                self.entry_common[setting].w_name = setting
                self.entry_common[setting].bind(
                    "<FocusIn>", lambda event: self.on_focused(event)
                )
                self.entry_common[setting].grid(row=widget_row, column=2, sticky="W")
                # Set the initial value for common setting
                self.common_defaults[setting] = self.entry_common[setting].get()
            else:
                # Set the initial value for common setting
                self.common_defaults[setting] = self.get_str_markets()
            self.common_trace_changed[setting].set(self.common_defaults[setting])
            self.common_flag[setting] = 0

        # Calculate the total height of static widgets
        self.static_widgets_height = setting_label.winfo_reqheight()
        for item in self.entry_common:
            self.static_widgets_height += self.entry_common[item].winfo_reqheight() + 1

        self.root_frame.grid_columnconfigure(0, weight=1)
        self.root_frame.grid_columnconfigure(1, weight=2)
        self.root_frame.grid_columnconfigure(2, weight=2)

        # Draw blank labels. They are of no use
        for i in range(len(self.market_list) + 1):
            widget_row += 1
            tk.Label(self.root_frame, bg=disp.bg_color).grid(row=widget_row, column=0)

        # Draw grid representing settings for markets
        self.entry_market = {}
        self.market_label = {}
        for setting in self.market_settings:
            self.market_trace[setting] = StringVar(name=setting + str(self))
            if setting != "CONNECTED":
                widget_row += 1
                tk.Label(self.root_frame, bg=disp.bg_color).grid(
                    row=widget_row, column=0
                )
                self.market_label[setting] = tk.Label(
                    self.root_frame,
                    text=setting + self.indent,
                    bg=disp.bg_color,
                    fg=disp.fg_color,
                )
                self.market_label[setting].grid(row=widget_row, column=1, sticky="W")
                self.market_trace[setting].trace_add(
                    "write", self.market_trace_callback
                )
                self.entry_market[setting] = ttk.Entry(
                    self.root_frame,
                    width=self.entry_width,
                    textvariable=self.market_trace[setting],
                    style="default.TEntry",
                )
                self.entry_market[setting].grid(row=widget_row, column=2, sticky="W")
                self.entry_market[setting].w_name = setting
                self.entry_market[setting].bind(
                    "<FocusIn>", lambda event: self.on_focused(event)
                )

        widget_row += 1
        tk.Label(self.root_frame, bg=disp.bg_color).grid(row=widget_row, column=0)

        widget_row += 1
        self.setting_button.grid(row=widget_row, column=0, columnspan=3)

        for i in range(widget_row):
            self.root_frame.grid_rowconfigure(i, weight=0)

    def on_focused(self, event) -> None:
        self.on_tip(event.widget.w_name)

    def on_tip(self, setting):
        """
        Displays a recommendation when the widget has focus.
        """
        text = Tips[setting].value
        if setting == "SQLITE_DATABASE":
            text = Tips.SQLITE_DATABASE.value.format(DATABASE=var.db_sqlite)
        disp.tips["text"] = setting + "\n\n" + text
        self.click_label.destroy()
        if "WS" in setting or "HTTP" in setting:
            link = Tips.docs.value[self.selected_frame.market][setting]
            self.click_label = ClickLabel(disp.frame_tips, text=link, link=link)
        elif "API" in setting:
            link = Tips.api.value[self.selected_frame.market][setting]
            self.click_label = ClickLabel(disp.frame_tips, text=link, link=link)
        self.return_main_page()


class DraggableFrame(tk.Frame):
    def __init__(self, master, app: SettingsApp, market, **kwargs):
        super().__init__(master, **kwargs)
        self.app = app
        self.market = market
        self.var = tk.IntVar()
        self.check_box = tk.Checkbutton(
            self,
            bd=0,
            highlightthickness=0,
            text=market,
            variable=self.var,
            onvalue=1,
            offvalue=0,
            activebackground=self.app.bg_active,
        )
        if len(self.app.settings_center) == 0:
            self.bg_market(self, self.app.bg_select_color)
        else:
            self.bg_market(self, self.app.bg_entry)
        self.check_box.pack()
        self.w_name = "MARKET"
        self.bind("<ButtonPress-1>", self.on_press)
        self.bind("<B1-Motion>", self.on_drag)
        self.bind("<ButtonRelease-1>", self.on_release)
        self.bind("<Motion>", self.on_hover)
        self.bind("<Leave>", self.on_leave)
        self.check_box.bind("<ButtonPress-1>", self.on_press)
        self.check_box.bind("<B1-Motion>", self.on_drag)
        self.check_box.bind("<ButtonRelease-1>", self.on_release)
        self.check_box.bind("<Motion>", self.on_hover)
        self.check_box.bind("<Leave>", self.on_leave)
        self.start_y = None
        self.is_dragging = False

    def bg_market(self, widget, color):
        widget.config(bg=color)
        widget.check_box.config(bg=color)

    def on_hover(self, event):
        if self != self.app.selected_frame:
            self.bg_market(self, self.app.bg_select_color)

    def on_leave(self, event):
        if self != self.app.selected_frame:
            self.bg_market(self, self.app.market_color[self.market])

    def on_press(self, event):
        self.app.on_tip("MARKET")
        self.start_y = event.y_root
        self.is_dragging = True

        # Bring the frame to the front
        self.lift()

        box_x = self.check_box.winfo_rootx()
        x = self.app.root_frame.winfo_pointerx()
        checked = "false"

        if x < box_x or x > box_x + 20:
            # No check or uncheck here
            self.check_box.config(state="disabled")
        else:
            checked = "true"
            if self.var.get() == 0:
                self.app.market_changed[self.market]["CONNECTED"] = "YES"
            else:
                self.app.market_changed[self.market]["CONNECTED"] = "NO"
            self.app.check_market_flag("CONNECTED", self.market)
        self.set_background_color(checked)

    def on_drag(self, event):
        if self.is_dragging:
            dy = event.y_root - self.start_y
            self.start_y = event.y_root
            current_y = self.winfo_y()
            new_y = current_y + dy
            # Restrict dragging to within the parent frame
            new_y = max(
                0, min(new_y, self.app.root_frame.winfo_height() - self.winfo_height())
            )
            self.place_configure(y=new_y)
            self.app.update_positions(self)

    def on_release(self, event):
        self.is_dragging = False
        self.app.reorder_frames()
        if self.check_box["state"] == "disabled":
            self.check_box.config(state="normal")

    def set_background_color(self, checked):
        """
        Set background color for selected market.
        """
        if self != self.app.selected_frame or checked == "true":
            self.bg_market(
                self.app.selected_frame,
                self.app.market_color[self.app.selected_frame.market],
            )
            self.app.selected_frame = self
            self.bg_market(self, self.app.bg_select_color)
            self.app.click_market = "true"
            self.app.set_market_fields(self.market)
            self.app.click_market = "false"
