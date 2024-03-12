import functions
from api.websockets import Websockets
from common.variables import Variables as var
from display.variables import Variables as disp

disp.root.bind("<F3>", lambda event: terminal_reload(event))
disp.root.bind("<F9>", lambda event: trade_state(event))


def terminal_reload(event) -> None:
    var.robots_thread_is_active = ""
    functions.info_display("Restarting...")
    disp.root.update()
    connect.connection()


def trade_state(event) -> None:
    if disp.f9 == "ON":
        disp.f9 = "OFF"
    elif disp.f9 == "OFF":
        disp.f9 = "ON"
        disp.messageStopped = ""
        ws = Websockets.connect[var.current_exchange]
        ws.logNumFatal = 0
    print(var.current_exchange, disp.f9)


'''class Tables:
    position: GridTable
    account: GridTable
    robots: GridTable
    exchange: GridTable
    orderbook: GridTable


def load_labels() -> None:
    functions.change_color(color=disp.title_color, container=disp.root)
    ws = Websockets.connect[var.current_exchange]
    Tables.position = GridTable(
        frame=disp.position_frame,
        name="position",
        size=max(5, var.position_rows + 1),
        title=var.name_pos,
        canvas_height=65,
        bind=functions.handler_pos,
        color=disp.bg_color,
        select=True,
    )
    Tables.account = GridTable(
        frame=disp.frame_4row_1_2_3col,
        name="account",
        size=var.account_rows + 1,
        title=var.name_acc,
        canvas_height=60,
        color=disp.bg_color,
    )
    Tables.robots = GridTable(
        frame=disp.frame_5row_1_2_3col,
        name="robots",
        size=max(disp.num_robots, len(ws.robots) + 1),
        title=var.name_robots,
        canvas_height=150,
        bind=functions.handler_robots,
        color=disp.title_color,
    )
    Tables.exchange = GridTable(
        frame=disp.frame_3row_1col,
        name="exchange",
        size=2,
        title=var.name_exchange,
        title_on=False,
        color=disp.title_color,
        select=True,
    )
    mod = Tables.robots.mod
    for row, emi in enumerate(ws.robots):
        if ws.robots[emi]["STATUS"] in ["NOT IN LIST", "OFF", "NOT DEFINED"] or (
            ws.robots[emi]["STATUS"] == "RESERVED" and ws.robots[emi]["POS"] != 0
        ):
            disp.labels["robots"][row + mod][5]["fg"] = "red"
        else:
            disp.labels["robots"][row + mod][5]["fg"] = "#212121"
    Tables.orderbook = GridTable(
        frame=disp.orderbook_frame,
        name="orderbook",
        size=disp.num_book,
        title=var.name_book,
        canvas_height=440,
        bind=functions.handler_orderbook,
        color=disp.bg_color,
    )
    num = int(disp.num_book / 2)
    mod = Tables.orderbook.mod
    for row in range(disp.num_book + mod - 1):
        for column in range(len(var.name_book)):
            if row > 0:
                if row <= num and column == 2:
                    disp.labels["orderbook"][row][column]["anchor"] = "w"
                if row > num and column == 0:
                    disp.labels["orderbook"][row][column]["anchor"] = "e"


trades = ListBoxTable(
    frame=disp.frame_trades, title=var.name_trade, size=0, expand=True
)
funding = ListBoxTable(
    frame=disp.frame_funding, title=var.name_funding, size=0, expand=True
)
orders = ListBoxTable(
    frame=disp.frame_orders,
    title=var.name_trade,
    bind=handlers.handler_order,
    size=0,
    expand=True,
)'''
