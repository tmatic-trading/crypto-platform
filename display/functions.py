import services as service

from .variables import Variables as disp


def info_display(market: str, message: str, warning=False, tm=None) -> None:
    message = service.format_message(market=market, message=message, tm=tm)
    num = message.count("\n")
    disp.text_info.insert("1.0", message)
    if warning:
        disp.text_info.tag_add(market, "1.0", f"{num}.1000")
        disp.text_info.tag_config(market, foreground=disp.red_color)
    disp.info_display_counter += 1
    if disp.info_display_counter > disp.text_line_limit:
        limit = f"{disp.text_line_limit + 1}.0"
        disp.text_info.delete(limit, "end")
