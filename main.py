import common.init as common_init
import connect
from common.variables import Variables as var
from display.variables import Variables as disp
from display.variables import on_closing

var.logger = common_init.setup_logger()
connect.connection()


def refresh():
    """
    Main loop refresh
    """
    connect.refresh()
    disp.root.after(var.refresh_rate, refresh)


disp.refresh_var = disp.root.after_idle(refresh)
disp.root.protocol(
    "WM_DELETE_WINDOW",
    lambda root=disp.root, refresh_var=disp.refresh_var: on_closing(root, refresh_var),
)
disp.root.mainloop()
