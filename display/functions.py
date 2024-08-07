from datetime import datetime, timezone

from .variables import Variables as disp


def noll(val: str, length: int) -> str:
    r = ""
    for _ in range(length - len(val)):
        r = r + "0"

    return r + val


def info_display(name: str, message: str, tm=None, warning=False) -> None:
    if name:
        name += ": "
    if not tm:
        tm = datetime.now(tz=timezone.utc)
    text = (
        noll(str(tm.hour), 2)
        + ":"
        + noll(str(tm.minute), 2)
        + ":"
        + noll(str(tm.second), 2)
        + "."
        + noll(str(int(tm.microsecond / 1000)), 3)
        + "  "
        + name
        + message
        + "\n"
    )
    if isinstance(text, tuple):
        text = text[0]
    num = text.count("\n")
    disp.text_info.insert("1.0", text)
    if warning:
        disp.text_info.tag_add(name, "1.0", f"{num}.1000")
        disp.text_info.tag_config(name, foreground=disp.red_color)
    disp.info_display_counter += 1
    if disp.info_display_counter > 300:
        disp.text_info.delete("301.0", "end")
