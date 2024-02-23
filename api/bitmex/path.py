from enum import Enum


class Listing(str, Enum):
    GET_ACTIVE_INSTRUMENTS = "/instrument/active"
    GET_ACCOUNT_INFO ="/user"
    GET_INSTRUMENT_DATA = "/instrument?symbol={SYMBOL}"
    GET_POSITION = "/position?filter=%7B%22symbol%22%3A%22{SYMBOL}%22%7D"



    '''GET_WALLET_BALANCE = "/v5/account/wallet-balance"
    UPGRADE_TO_UNIFIED_ACCOUNT = "/v5/account/upgrade-to-uta"
    GET_BORROW_HISTORY = "/v5/account/borrow-history"
    GET_COLLATERAL_INFO = "/v5/account/collateral-info"
    GET_COIN_GREEKS = "/v5/asset/coin-greeks"
    GET_FEE_RATE = "/v5/account/fee-rate"
    GET_ACCOUNT_INFO = "/v5/account/info"
    GET_TRANSACTION_LOG = "/v5/account/transaction-log"
    SET_MARGIN_MODE = "/v5/account/set-margin-mode"
    SET_MMP = "/v5/account/mmp-modify"
    RESET_MMP = "/v5/account/mmp-reset"
    GET_MMP_STATE = "/v5/account/mmp-state"'''

    def __str__(self) -> str:
        return self.value