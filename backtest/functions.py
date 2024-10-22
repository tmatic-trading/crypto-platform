import os
from collections import OrderedDict
from datetime import datetime
from typing import Union

import services as service
from api.api import WS, Markets
from common.data import BotData, Bots, Instrument
from common.variables import Variables as var
from display.messages import ErrorMessage
from functions import Function


def get_instrument(ws: Markets, symbol: tuple):
    """
    When running backtesting outside main.py there is no connection to any
    market and no information about instruments is received. Therefore, we
    have to get information via an http request. This request is made only
    once, since the received information is saved in the database in the
    `backtest` table to speed up the program.
    """
    qwr = (
        "select * from backtest where SYMBOL ='"
        + symbol[0]
        + "' and MARKET = '"
        + ws.name
        + "';"
    )
    data = service.select_database(qwr)
    if not data:
        symbols = ws.Instrument.get_keys()
        if symbols == None or symbol not in symbols:
            WS.get_active_instruments(ws)
        service.add_symbol_database(instrument=ws.Instrument[symbol], table="backtest")
    else:
        data = data[0]
        instrument = ws.Instrument.add(symbol)
        service.set_symbol(instrument=instrument, data=data)


def load_backtest_data(market: str, symb: str, timefr: str, bot_name: str):
    def fill(header, record, num, line):
        if header in ["dt", "tm"]:
            record[header] = int(line[num])
        else:
            record[header] = float(line[num])

    bot = Bots[bot_name]
    for symbol in var.backtest_symbols:
        bot.backtest_data[symbol] = list()
        b_data: list = bot.backtest_data[symbol]
        filename = os.getcwd() + f"/backtest/data/{market}/{symbol[0]}/{timefr}.csv"
        print("\nLoading backtest data from", filename)
        with open(filename, "r") as file:
            headers = next(file).strip("\n").split(";")
            for line in file:
                line = line.strip("\n").split(";")
                record = dict()
                for num, header in enumerate(headers):
                    fill(header, record, num, line)
                b_data.append(record)

    # Checking if the sizes of all backtesting data records are the same.

    if len(var.backtest_symbols) > 1:
        reference_size = len(bot.backtest_data[var.backtest_symbols[0]])
        reference_symbol = var.backtest_symbols[0]
        for symbol in var.backtest_symbols:
            if len(bot.backtest_data[symbol]) != reference_size:
                message = ErrorMessage.CHECK_BACKTEST_DATA_SIZE.format(
                    REFERENCE=reference_symbol,
                    REFERENCE_NUMBER=reference_size,
                    SYMBOL=symbol,
                    NUMBER=len(bot.backtest_data[symbol]),
                )
                print(message)
                exit(1)


def _trade(
    instrument: Instrument,
    bot: BotData,
    side: str,
    qty: float,
    price: float,
    clOrdID: Union[str, None],
) -> str:
    ws = Markets[instrument.market]
    if side == "Sell":
        quantity = -qty
    calc = Function.calculate(
        ws,
        symbol=(instrument.symbol, instrument.market),
        price=price,
        qty=quantity,
        rate=instrument.makerFee,
        fund=1,
    )
    service.process_position(
        bot=bot,
        symbol=(instrument.symbol, instrument.market),
        instrument=instrument,
        user_id=0,
        qty=quantity,
        calc=calc,
        ttime="Not used",
    )
    if clOrdID:
        del var.orders[bot.name][clOrdID]
    else:
        clOrdID = service.set_clOrdID(emi=bot.name)

    return clOrdID


def _check_trades(bot: BotData):
    orders: OrderedDict = var.orders[bot.name]
    orders_copy = orders.copy()
    for clOrdID, order in orders_copy.items():
        data = bot.backtest_data[order["symbol"]][bot.iter]
        if (order["side"] == "Sell" and data["hi"] > order["price"]) or (
            order["side"] == "Buy" and data["lo"] < order["price"]
        ):
            ws = Markets[order["market"]]
            instrument = ws.Instrument[order["symbol"]]
            _trade(
                instrument=instrument,
                bot=bot,
                side=order["side"],
                qty=order["leavesQty"],
                price=order["price"],
                clOrdID=clOrdID,
            )


def run(bot: BotData, strategy: callable):
    symbols = list(bot.backtest_data.keys())
    size = len(bot.backtest_data[symbols[0]]) - 1
    for bot.iter in range(size):
        _check_trades(bot=bot)
        strategy()


def results(bot: BotData):
    symbols = list(bot.backtest_data.keys())
    values = dict()
    for symbol in symbols:
        ws = Markets[symbol[1]]
        instrument = ws.Instrument[symbol]
        position = bot.bot_positions[symbol]
        calc = Function.calculate(
            ws,
            symbol=symbol,
            price=bot.backtest_data[symbol][-1]["open_bid"],
            qty=position["position"],
            rate=instrument.makerFee,
            fund=1,
        )
        values[symbol] = {
            "result": position["sumreal"] - calc["sumreal"],
            "commission": position["commiss"] + calc["commiss"],
            "volume": round(
                position["volume"] + position["position"], instrument.precision
            ),
            "currency": instrument.settlCurrency,
            "volume_currency": instrument.quoteCoin,
            "max_position": position["max_position"],
        }

    return values
