from enum import Enum


class Message(str, Enum):
    SUBSCRIPTION_ADDED = "Subscription added for {SYMBOL}."
    DEFAULT_SYMBOL_ADDED = (
        "{MARKET} symbol list is empty. Added default symbol {SYMBOL}."
    )

    def __str__(self) -> str:
        return self.value


class ErrorMessage(str, Enum):
    BOT_FOLDER_NOT_FOUND = (
        "There was an error loading {MODULE}:\n\n{EXCEPTION}\n\n"
        + "Probably ``algo`` is missing a subdirectory named ``{BOT_NAME}``, "
        + "or ``{BOT_NAME}`` is missing a strategy.py file, or strategy.py has "
        + "an incorrect import."
    )
    BOT_LOADING_ERROR = (
        "There was an error loading {MODULE}:\n\n{EXCEPTION}\n\n"
        + "Correct the strategy file or delete ``{BOT_NAME}`` using the "
        + "``Bot Menu``.\n"
    )
    IMPOSSIBLE_SUBSCRIPTION = (
        "The {SYMBOL} instrument has a {STATE} status, but is normally Open. "
        + "The instrument has probably expired, but in the database there are "
        + " still positions that should not exist. Check your trading history."
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
        "A list was expected when the positions were loaded, but it was not received."
    )
    INSTRUMENT_NOT_FOUND = (
        "Request {PATH} received empty. ({TICKER} {CATEGORY}) instrument not found."
    )
    REQUEST_EMPTY = "Request {PATH} received empty."
    FAILED_SUBSCRIPTION = "Failed to subscribe to {SYMBOL}."

    def __str__(self) -> str:
        return self.value
