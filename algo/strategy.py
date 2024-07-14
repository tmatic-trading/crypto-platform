import services as service
from api.api import Markets
from common.data import Instrument
from functions import Function


def algo(robot: dict, frame: dict, instrument: Instrument) -> None:
    ws = Markets[robot["MARKET"]]
    period = robot["PERIOD"]
    quantaty = robot["lotSize"] * robot["CAPITAL"]
    emi = robot["EMI"]
    symbol = robot["SYMBOL"]
    indent = frame[-1]["hi"] / 10 #(frame[-1]["hi"] - frame[-1]["lo"]) / 3
    sell_price = service.ticksize_rounding(
        price=(instrument.asks[0][0] + indent), ticksize=instrument.tickSize
    )
    buy_price = service.ticksize_rounding(
        price=(instrument.bids[0][0] - indent), ticksize=instrument.tickSize
    )
    if frame[-1]["ask"] > frame[-1 - period]["ask"]:
        buy_quantaty = quantaty - robot["POS"]
        clOrdID = order_search(ws, emi=emi, side="Buy")
        # Move an existing order
        if clOrdID:
            if (
                buy_price != ws.orders[clOrdID]["price"]
                or buy_quantaty != ws.orders[clOrdID]["leavesQty"]
            ):
                if robot["POS"] < quantaty:
                    clOrdID = Function.put_order(
                        ws,
                        clOrdID=clOrdID,
                        price=buy_price,
                        qty=buy_quantaty,
                    )
        # Place a new order
        else:
            if robot["POS"] < quantaty:
                clOrdID = Function.post_order(
                    ws,
                    name=robot["MARKET"],
                    symbol=symbol,
                    emi=emi,
                    side="Buy",
                    price=buy_price,
                    qty=buy_quantaty,
                )
                delete_orders(ws, emi=emi, side="Sell")
    elif frame[-1]["bid"] <= frame[-1 - period]["bid"]:
        sell_quantaty = quantaty + robot["POS"]
        clOrdID = order_search(ws, emi=emi, side="Sell")
        # Move an existing order
        if clOrdID:
            if (
                sell_price != ws.orders[clOrdID]["price"]
                or sell_quantaty != ws.orders[clOrdID]["leavesQty"]
            ):
                if robot["POS"] > -quantaty:
                    clOrdID = Function.put_order(
                        ws,
                        clOrdID=clOrdID,
                        price=sell_price,
                        qty=sell_quantaty,
                    )
        # Place a new order
        else:
            if robot["POS"] > -quantaty:
                clOrdID = Function.post_order(
                    ws,
                    name=robot["MARKET"],
                    symbol=symbol,
                    emi=emi,
                    side="Sell",
                    price=sell_price,
                    qty=sell_quantaty,
                )
                delete_orders(ws, emi=emi, side="Buy")


def init_variables(robot: dict):
    robot["PERIOD"] = 10


def order_search(ws: Markets, emi: int, side: str) -> str:
    res = ""
    for clOrdID, order in ws.orders.items():
        if order["EMI"] == emi and order["SIDE"] == side:
            res = clOrdID
            break

    return res


def delete_orders(ws, emi: int, side: str) -> None:
    for clOrdID, order in ws.orders.copy().items():
        if order["EMI"] == emi and order["SIDE"] == side:
            Function.del_order(ws, order=order, clOrdID=clOrdID)
