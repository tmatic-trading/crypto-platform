from enum import Enum


class Listing(str, Enum):
    GET_ACTIVE_INSTRUMENTS = "/instrument/active"
    GET_ACCOUNT_INFO = "/user"
    GET_INSTRUMENT_DATA = "/instrument?symbol={SYMBOL}"
    GET_POSITION = "/position?filter=%7B%22symbol%22%3A%22{SYMBOL}%22%7D"
    TRADE_BUCKETED = (
        "/trade/bucketed?binSize={TIMEFRAME}&count=1000&reverse="
        + "false&partial=true&symbol={SYMBOL}&columns=open%2C%20high%2C%20low%2C"
        + "%20close&startTime={TIME}"
    )
    TRADING_HISTORY = (
        "/execution/tradeHistory?count={HISTCOUNT}&reverse=false" + "&startTime={TIME}"
    )
    ORDER_ACTIONS = "/order"
    GET_POSITION_INFO = "/position"
    OPEN_ORDERS = "/order?filter=%7B%22open%22%3A%20true%7D&reverse=false"
    CANCEL_ALL_BY_INSTRUMENT = "/order/all?symbol={SYMBOL}"

    def __str__(self) -> str:
        return self.value
