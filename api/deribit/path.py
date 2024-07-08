from enum import Enum


class Listing(str, Enum):
    GET_ACTIVE_INSTRUMENTS = "public/get_instruments"
    OPEN_ORDERS = "private/get_open_orders"
    GET_ACCOUNT_INFO = "private/get_account_summaries"
    GET_POSITION_INFO = "private/get_positions"
    TRADES_AND_FUNDING_TRANSACTION_LOG = "private/get_transaction_log"
    TRADES_LAST_5_DAYS = "private/get_user_trades_by_currency_and_time"
    GET_INSTRUMENT_DATA = "public/get_instrument"
    TRADE_BUCKETED = "public/get_tradingview_chart_data"
    PLACE_LIMIT = "private/{SIDE}"
    """
    GET_POSITION = "position?filter=%7B%22symbol%22%3A%22{SYMBOL}%22%7D"
    URGENT_ANNOUNCEMENT = "announcement/urgent"
    ORDER_ACTIONS = "order"
    """

    def __str__(self) -> str:
        return self.value


class Matching_engine:
    PATHS = {
        "private/buy",
        "private/sell",
        "private/edit",
        "private/edit_by_label",
        "private/cancel",
        "private/cancel_by_label",
        "private/cancel_all",
        "private/cancel_all_by_instrument",
        "private/cancel_all_by_currency",
        "private/cancel_all_by_kind_or_type",
        "private/close_position",
        "private/verify_block_trade",
        "private/execute_block_trade",
        "private/move_positions",
        "private/mass_quote",
        "private/cancel_quotes",
    }
