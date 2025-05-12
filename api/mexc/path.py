from enum import Enum


class Listing(str, Enum):
    GET_ACTIVE_INSTRUMENTS = "/contract/detail"
    # OPEN_ORDERS = "private/get_open_orders"
    # GET_ACCOUNT_INFO = "private/get_account_summaries"
    # GET_POSITION_INFO = "private/get_positions"
    # TRADES_AND_FUNDING_TRANSACTION_LOG = "private/get_transaction_log"
    # TRADES_LAST_5_DAYS = "private/get_user_trades_by_currency_and_time"
    # GET_INSTRUMENT_DATA = "public/get_instrument"
    # TRADE_BUCKETED = "public/get_tradingview_chart_data"
    # PLACE_ORDER = "private/{SIDE}"
    # REPLACE_LIMIT = "private/edit"
    # REMOVE_ORDER = "private/cancel"
    # CANCEL_ALL_BY_INSTRUMENT = "private/cancel_all_by_instrument"

    def __str__(self) -> str:
        return self.value