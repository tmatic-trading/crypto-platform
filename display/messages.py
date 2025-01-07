from enum import Enum


class Message(str, Enum):
    SUBSCRIPTION_WAITING = (
        "Subscription to {SYMBOL}. Waiting for confirmation from {MARKET}."
    )
    SUBSCRIPTION_ADDED = "Added subscription to {SYMBOL}."
    UNCLOSED_POSITION_FOUND = (
        "An open position {POSITION} for {SYMBOL} was found in the database, "
        + "but there is no subscription for {SYMBOL}. The subscription will "
        + "be added."
    )
    UNSUBSCRIPTION_WAITING = (
        "Unsubscribe from {SYMBOL}. Waiting for confirmation from {MARKET}."
    )
    UNSUBSCRIBED = "Unsubscribed from {SYMBOL}."
    DEFAULT_SYMBOL_ADDED = (
        "{MARKET} symbol list is empty. Added default symbol {SYMBOL}."
    )
    WEBSOCKET_SUBSCRIPTION = "sending ws subscription - {NAME} - channel - {CHANNEL}"
    WEBSOCKET_UNSUBSCRIBE = "sending ws unsubscribe - {NAME} - channel - {CHANNEL}"
    WEBSOCKET_SUBSCRIPTION_SKIPPED = (
        "Already subscribed symbol {SKIPPED} skipped during websocket subscription "
        + "to {SYMBOL}."
    )

    def __str__(self) -> str:
        return self.value


class ErrorMessage(str, Enum):
    BOT_FOLDER_NOT_FOUND = (
        "There was an error loading {MODULE}:\n\n{EXCEPTION}\n\n"
        + "Probably ``algo`` is missing a subdirectory named ``{BOT_NAME}``, "
        + "or ``{BOT_NAME}`` is missing a strategy.py file, or strategy.py has "
        + "an incorrect import.\n"
    )
    BOT_LOADING_ERROR = (
        "There was an error loading {MODULE}:\n\n{CLASS} {EXCEPTION}\n"
        + "Correct the strategy file or delete ``{BOT_NAME}`` using the "
        + "``Bot Menu``.\n"
    )
    IMPOSSIBLE_SUBSCRIPTION = (
        "The {SYMBOL} symbol has a non-open status, but in the database there are "
        + "still open positions that should not exist. This instrument has probably "
        + "expired. Check your trading history."
    )
    IMPOSSIBLE_DATABASE_POSITION = (
        "{SYMBOL} expired and a delivery in the amount of {DELIVERY} is "
        + "received from {MARKET} but there is a position of {POSITION} "
        + "{SYMBOL} in the database, which cannot be possible. The delivery "
        + "amount and the position in the database must be equal. This "
        + "delivery is not recorded in the database. Please check the "
        + "database and your trading history."
    )
    EMPTY_ORDERBOOK = (
        "Failed to place order {ORDER} because {SYMBOL} order book is empty."
    )
    NO_CURRENCY = (
        "Failed to add instrument {TICKER}. This instrument uses currency "
        + "{CURRENCY}, which is not in dictionary ``currency_divisor``. "
        + "{TICKER} is ignored."
    )
    UNKNOWN_SYMBOL = (
        "Unknown {MARKET} symbol {SYMBOL}. Check the SYMBOLS in the "
        + ".env.Subscriptions file. It is possible that the symbol name is "
        + "misspelled, or such symbol does not exist, or the instrument has "
        + "expired. Symbol has been removed from {MARKET} subscription."
    )
    USER_ID_NOT_FOUND = (
        "A response from the exchange has been received, but it does not "
        + "contain a user ID."
    )
    USER_ID_NOT_RECEIVED = (
        "A user ID was requested from the exchange but was not received."
    )
    POSITIONS_NOT_RECEIVED = (
        "A list was expected when the positions were loaded, but it was not "
        + "received."
    )
    INSTRUMENT_NOT_FOUND = (
        "Request {PATH} received empty. ({TICKER} {CATEGORY}) instrument not "
        + "found."
    )
    REQUEST_EMPTY = "Request {PATH} received empty."
    FAILED_SUBSCRIPTION = "Failed to subscribe to {SYMBOL}. Reboot"
    FAILED_UNSUBSCRIPTION = "Unable to unsubscribe from {SYMBOL}. Reboot"
    UNSUBSCRIPTION_WARNING = (
        "You can't unsubscribe from all instruments. At least one must be in "
        + "the list."
    )
    SUBSCRIPTION_WARNING = "The {SYMBOL} instrument is already subscribed."
    CHECK_BACKTEST_DATA_SIZE = (
        "Backtest data error. The {REFERENCE} has {REFERENCE_NUMBER} records "
        + "and the {SYMBOL} has {NUMBER} records. The numbers should be "
        + "equal. Check the backtest data files. Exiting."
    )
    BOT_KLINE_ERROR = (
        "Bot `{BOT_NAME}` is trying to get kline data for the {INSTRUMENT} "
        + "instrument with the status `{STATUS}`. Expiry date of the "
        + "{INSTRUMENT} is {EXPIRE}. Check the strategy file at {FILE}."
    )
    BOT_INSTRUMENT_EXPIRED = (
        "Bot instrument `{INSTRUMENT}` expired. Check the strategy file at " + "{FILE}."
    )
    BOT_PNL_CALCULATIONS = (
        "The bot `{BOT_NAME}` had trades on {MARKET}, but {MARKET} is not "
        + "connected. The results of these trades are not included in the "
        + "PNL calculations."
    )
    EMPTY_ORDERBOOK_DATA = (
        "Unable to obtain best {SIDE} price from {SYMBOL} because the "
        + "order book is empty."
    )
    EMPTY_ORDERBOOK_DATA_KLINE = (
        "When adding a new kline entry could not get best {SIDE} price from "
        + "{SYMBOL} because the order book is empty; {SIDE} was assigned to "
        + "its previous value of {PRICE}."
    )
    UNSUBSCRIPTION_WARNING_ORDERS = (
        "Instrument {SYMBOL} has open orders. Please cancel orders before "
        + "canceling subscription."
    )
    UNSUBSCRIPTION_WARNING_POSITION = (
        "Instrument {SYMBOL} has an open position {POSITION}. The position "
        + "should be closed before canceling subscription."
    )
    UNSUBSCRIPTION_WARNING_UNSETTLED = (
        "The balance of the instrument {SYMBOL} is zero, but not the balance "
        + "of the bot(s).\n\nOpen positions of Tmatic internal accounting:\n\n"
        + "{LIST}\nYou should close bot positions or delete bot(s) to settle "
        + "the balance."
    )

    def __str__(self) -> str:
        return self.value
