from enum import Enum


class Listing(str, Enum):
    GET_ACTIVE_INSTRUMENTS = "public/get_instruments"
    OPEN_ORDERS = "private/get_open_orders"
    GET_ACCOUNT_INFO = "private/get_account_summaries"
    GET_POSITION_INFO = "private/get_positions"
    """
    GET_INSTRUMENT_DATA = "instrument?symbol={SYMBOL}"
    GET_POSITION = "position?filter=%7B%22symbol%22%3A%22{SYMBOL}%22%7D"
    TRADE_BUCKETED = (
        "trade/bucketed?binSize={TIMEFRAME}&count=1000&reverse="
        + "false&partial=true&symbol={SYMBOL}&columns=open%2C%20high%2C%20low%2C"
        + "%20close&startTime={TIME}"
    )
    TRADING_HISTORY = (
        "execution/tradeHistory?count={HISTCOUNT}&reverse=false" + "&startTime={TIME}"
    )
    URGENT_ANNOUNCEMENT = "announcement/urgent"
    ORDER_ACTIONS = "order"
    """

    def __str__(self) -> str:
        return self.value
