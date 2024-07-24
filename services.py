import traceback
from datetime import datetime, timezone
from typing import Union

from api.bybit.errors import exception
from common.variables import Variables as var


def ticksize_rounding(price: float, ticksize: float) -> float:
    """
    Rounds the price depending on the tickSize value
    """
    arg = 1 / ticksize
    res = round(price * arg, 0) / arg

    return res


def time_converter(
    time: Union[int, float, str, datetime], usec=False
) -> Union[datetime, int]:
    """
    The datetime always corresponds to utc time, the timestamp always
    corresponds to local time.
    int, float      -> datetime (utc)
    datetime utc    -> Unix timestamp (local time)
    str utc         -> datetime (utc)
    """
    if isinstance(time, int) or isinstance(time, float):
        return datetime.fromtimestamp(time, tz=timezone.utc)
    elif isinstance(time, datetime):
        return int(time.timestamp() * 1000)
    elif isinstance(time, str):
        time = time.replace("T", " ")
        time = time.replace("Z", "")
        f = time.find("+")
        if f > 0:
            time = time[:f]
        if usec:
            try:
                dt = datetime.strptime(time, "%Y-%m-%d %H:%M:%S.%f")
            except Exception:
                dt = datetime.strptime(time, "%Y-%m-%d %H:%M:%S")
        else:
            dt = datetime.strptime(time[:19], "%Y-%m-%d %H:%M:%S")
        dt = dt.replace(tzinfo=timezone.utc)
        return dt

    else:
        raise TypeError(type(time))


def exceptions_manager(cls):
    for attr in cls.__dict__:
        if callable(getattr(cls, attr)):
            if attr not in [
                "exit",
                "Position",
                "Instrument",
                "Account",
                "Result",
                "__init__",
            ]:
                setattr(cls, attr, exception(getattr(cls, attr)))
    return cls


def precision(number: float) -> int:
    r = str(number)
    if "e" in r:
        r = r.replace("e", "")
        r = r.replace(".", "")
        r = r.split("-")
        precision = len(r[0]) - 1 + int(r[1])
    elif "." in r:
        r = r.split(".")
        if int(r[1]) == 0:
            precision = 0
        else:
            precision = len(r[1])
    else:
        precision = 0

    return precision


def add_space(line: list) -> str:
    n = max(map(lambda x: len(x), line))
    lst = list()
    for l in line:
        lst.append((n - len(l)) * " " + l)

    return "\n".join(lst)


def close(markets):
    var.robots_thread_is_active = False
    for name in var.market_list:
        ws = markets[name]
        ws.exit()


def display_exception(exception):
    traceback.print_exception(type(exception), exception, exception.__traceback__)


def select_database(query: str) -> list:
    err_locked = 0
    while True:
        try:
            var.sql_lock.acquire(True)
            var.cursor_sqlite.execute(query)
            orig = var.cursor_sqlite.fetchall()
            var.sql_lock.release()
            data = []
            if orig:
                data = list(map(lambda x: dict(zip(orig[0].keys(), x)), orig))
            return data
        except Exception as e:  # var.error_sqlite
            if "database is locked" not in str(e):
                print("_____query:", query)
                var.logger.error("Sqlite Error: " + str(e) + ")")
                var.sql_lock.release()
                break
            else:
                err_locked += 1
                var.logger.error(
                    "Sqlite Error: Database is locked (attempt: "
                    + str(err_locked)
                    + ")"
                )
                var.sql_lock.release()

def insert_database(values: list, table: str) -> None:
    err_locked = 0
    while True:
        try:
            var.sql_lock.acquire(True)
            if table == "coins":
                var.cursor_sqlite.execute(
                    "insert into coins (EXECID,EMI,REFER,CURRENCY,SYMBOL,"
                    + "TICKER,CATEGORY,MARKET,SIDE,QTY,QTY_REST,PRICE,"
                    + "THEOR_PRICE,TRADE_PRICE,SUMREAL,COMMISS,CLORDID,TTIME,"
                    + "ACCOUNT) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                    values,
                )
            elif table == "robots":
                var.cursor_sqlite.execute(
                    "insert into robots (EMI,STATE) VALUES (?,?)",
                    values,
                )
            var.connect_sqlite.commit()
            var.sql_lock.release()
            break
        except Exception as e:  # var.error_sqlite
            if "database is locked" not in str(e):
                var.logger.error("Sqlite Error: " + str(e) + " execID=" + values[0])
                var.sql_lock.release()
                break
            else:
                err_locked += 1
                var.logger.error(
                    "Sqlite Error: Database is locked (attempt: "
                    + str(err_locked)
                    + ")"
                )
                var.connect_sqlite.rollback()
                var.sql_lock.release()

def update_database(query: list) -> None:
    err_locked = 0
    while True:
        try:
            var.sql_lock.acquire(True)
            var.cursor_sqlite.execute(query)
            var.connect_sqlite.commit()
            var.sql_lock.release()
            break
        except Exception as e:  # var.error_sqlite
            if "database is locked" not in str(e):
                print("_____query:", query)
                var.logger.error("Sqlite Error: " + str(e) + ")")
                var.sql_lock.release()
                break
            else:
                err_locked += 1
                var.logger.error(
                    "Sqlite Error: Database is locked (attempt: "
                    + str(err_locked)
                    + ")"
                )
                var.connect_sqlite.rollback()
                var.sql_lock.release()
