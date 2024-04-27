from datetime import datetime, timezone

from .variables import Variables as disp


def noll(val: str, length: int) -> str:
    r = ""
    for _ in range(length - len(val)):
        r = r + "0"

    return r + val


def info_display(name: str, message: str) -> None:
    t = datetime.now(tz=timezone.utc)
    disp.text_info.configure(state="normal")
    disp.text_info.insert(
        "1.0",
        noll(str(t.hour), 2)
        + ":"
        + noll(str(t.minute), 2)
        + ":"
        + noll(str(t.second), 2)
        + "."
        + noll(str(int(t.microsecond / 1000)), 3)
        + " "
        + " "
        + name
        + ": "
        + message
        + "\n",
    )
    disp.info_display_counter += 1
    if disp.info_display_counter > 40:
        disp.text_info.delete("41.0", "end")
    disp.text_info.configure(state="disabled")
