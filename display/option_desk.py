import tkinter as tk

from api.api import Markets
from common.data import Instrument
from common.variables import Variables as var
from display.variables import Variables as disp
from display.variables import on_canvas_leave
from services import define_symbol_key, set_dotenv, symbols_to_string

from .headers import Header
from .variables import ScrollFrame, TreeTable, TreeviewTable


class OptionDesk:
    def __init__(self) -> None:
        self.is_on = False
        self.ws: Markets
        self.dash = [var.DASH for _ in range(9)]

    def on_closing(self) -> None:
        on_canvas_leave("", self.desk, disp.ostype)
        self.is_on = False
        self.desk.destroy()

    def create(self, instrument: Instrument, update: callable):
        self.update = update
        self.market = instrument.market
        self.category = instrument.category
        self.currency = instrument.settlCurrency[0]
        self.symbol = instrument.symbol
        self.ws = Markets[self.market]
        self.calls = sorted(self.ws.instrument_index[self.category][self.currency][
            instrument.symbol
        ]["CALLS"])
        self.puts = sorted(self.ws.instrument_index[self.category][self.currency][
            instrument.symbol
        ]["PUTS"])
        self.calls_set = set(self.calls)
        self.puts_set = set(self.puts)
        self.strikes = list()
        strike_calls = {}
        strike_puts = {}
        # Some strikes look like: "0d12", "0d2176", "0d6", etc.
        # Therefore we replace "d" with "." to make float sort possible
        for item in self.calls:
            opt_strike = self.ws.Instrument[(item, self.market)].optionStrike
            if "d" in opt_strike:
                opt_strike = float(opt_strike.replace("d", "."))
            else:
                opt_strike = int(opt_strike)
            strike_calls[opt_strike] = item
            self.strikes.append(opt_strike)
        for item in self.puts:
            opt_strike = self.ws.Instrument[(item, self.market)].optionStrike
            if "d" in opt_strike:
                opt_strike = float(opt_strike.replace("d", "."))
            else:
                opt_strike = int(opt_strike)
            strike_puts[opt_strike] = item
        self.strikes = sorted(self.strikes)
        self.calls_list = list()
        self.puts_list = list()
        for item in self.strikes:
            self.calls_list.append(strike_calls[item])
            self.puts_list.append(strike_puts[item])

        if not self.is_on:
            self.desk = tk.Toplevel()
            self.desk.geometry(
                "{}x{}".format(disp.window_width, int(disp.window_height * 0.5))
            )
            self.desk.title(f"{self.market} options ({self.currency})")
            self.desk.protocol("WM_DELETE_WINDOW", self.on_closing)
            self.desk.grid_rowconfigure(0, weight=0)
            self.desk.grid_rowconfigure(1, weight=1000)  # change weight to 4
            self.desk.grid_columnconfigure(0, weight=1)
            self.desk.grid_columnconfigure(1, weight=0)
            self.desk.grid_columnconfigure(2, weight=1)

            self.label = tk.Label(self.desk, text="Calls", font=disp.bold_font)
            self.label.grid(row=0, column=0, sticky="NSEW")
            tk.Label(self.desk, text=instrument.symbol, font=disp.bold_font).grid(
                row=0, column=1, sticky="NSEW"
            )
            tk.Label(self.desk, text="Puts", font=disp.bold_font).grid(
                row=0, column=2, sticky="NSEW"
            )

            bottom = tk.Frame(self.desk, bg=disp.bg_color)
            bottom.grid(row=1, column=0, columnspan=3, sticky="NSEW")
            bottom.grid_rowconfigure(0, weight=0)
            bottom.grid_rowconfigure(1, weight=100)
            bottom.grid_columnconfigure(0, weight=6)
            bottom.grid_columnconfigure(1, weight=1)
            bottom.grid_columnconfigure(2, weight=6)
            bottom.grid_columnconfigure(3, weight=0)
            self.calls_headers = tk.Frame(bottom)
            strikes_headers = tk.Frame(bottom)
            puts_headers = tk.Frame(bottom)
            self.calls_headers.grid(row=0, column=0, sticky="NEWS")
            strikes_headers.grid(row=0, column=1, sticky="NEWS")
            puts_headers.grid(row=0, column=2, sticky="NEWS")
            trim = tk.Label(bottom, text="  ")
            trim.grid(row=0, column=3)

            headers_calls = TreeviewTable(
                frame=self.calls_headers,
                name="t",
                title=Header.name_calls,
                size=0,
                cancel_scroll=True,
            )
            headers_puts = TreeviewTable(
                frame=puts_headers,
                name="t",
                title=Header.name_puts,
                size=0,
                cancel_scroll=True,
            )

            bottom_sub = tk.Frame(bottom, bg=disp.bg_color)
            bottom_sub.grid_rowconfigure(0, weight=1)
            bottom_sub.grid_columnconfigure(0, weight=1)
            bottom_sub.grid(row=1, column=0, columnspan=4, sticky="NEWS")
            main = ScrollFrame(bottom_sub, bg=disp.bg_color, bd=0, trim=trim)
            main.grid_rowconfigure(0, weight=1)
            main.grid_columnconfigure(0, weight=6)
            main.grid_columnconfigure(1, weight=1)
            main.grid_columnconfigure(2, weight=6)
            calls_body = tk.Frame(main, bg=disp.bg_color)
            strikes_body = tk.Frame(main, bg=disp.bg_color)
            puts_body = tk.Frame(main, bg=disp.bg_color)
            calls_body.grid(row=0, column=0, sticky="NEWS")
            strikes_body.grid(row=0, column=1, sticky="NEWS")
            puts_body.grid(row=0, column=2, sticky="NEWS")

            TreeTable.calls = TreeviewTable(
                frame=calls_body,
                name="calls",
                title=Header.name_calls,
                size=len(self.strikes),
                bind=lambda event: self.select_instrument(event, "calls", self.market),
                style="option.Treeview",
                cancel_scroll=True,
                headings=False,
            )
            TreeTable.strikes = TreeviewTable(
                frame=strikes_body,
                name="strikes",
                title=Header.name_strikes,
                size=len(self.strikes),
                style="option.Treeview",
                cancel_scroll=True,
                headings=False,
                hover=False,
                selectmode="none",
                bold=True,
            )
            TreeTable.puts = TreeviewTable(
                frame=puts_body,
                name="puts",
                title=Header.name_puts,
                size=len(self.strikes),
                bind=lambda event: self.select_instrument(event, "puts", self.market),
                style="option.Treeview",
                cancel_scroll=True,
                headings=False,
            )

            headers_calls.tree.bind(
                "<B1-Motion>", lambda event: trim_columns(event, TreeTable.calls)
            )
            headers_puts.tree.bind(
                "<B1-Motion>", lambda event: trim_columns(event, TreeTable.puts)
            )

            for num, strike in enumerate(self.strikes):
                values = [strike]
                TreeTable.strikes.update(num, values=values)

            self.desk.lift()
            self.is_on = True
            self.close_window = False

            option = var.selected_option[(self.symbol, self.market)]
            if self.ws.Instrument[option].optionType == "CALLS":
                indx = self.calls_list.index(option[0])
                TreeTable.calls.set_selection(index=indx)
            elif self.ws.Instrument[option].optionType == "PUTS":
                indx = self.puts_list.index(option[0])
                TreeTable.puts.set_selection(index=indx)

    def select_instrument(self, event, kind, market):
        if self.close_window:
            tree = event.widget
            items = tree.selection()
            if items:
                iid = int(items[0])
                if kind == "calls":
                    options = self.calls_list
                else:
                    options = self.puts_list
                if options[iid] != var.DASH:
                    var.symbol = (options[iid], market)
                    var.current_market = market
                    var.selected_option[(self.symbol, self.market)] = var.symbol
                    set_dotenv(
                        dotenv_path=var.subscriptions,
                        key=define_symbol_key(market=market),
                        value=symbols_to_string(var.env[market]["SYMBOLS"]),
                    )
                    self.update()
                    self.on_closing()
        self.close_window = True


def trim_columns(event, body: TreeTable):
    headers = event.widget
    cols = ("#0",) + headers.cget("columns")  # tuple of all columns
    for column in cols:
        body.tree.column(column, width=headers.column(column, "width"))


options_desk = OptionDesk()
