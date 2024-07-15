# import common.init as common_init
import connect
from common.variables import Variables as var
from connect import on_closing
from display.variables import Variables as disp

#var.logger = common_init.setup_logger()

connect.setup()


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
