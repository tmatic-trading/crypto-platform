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