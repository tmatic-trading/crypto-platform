from enum import Enum


class ErrorStatus(Enum):
    RETRY = {}
    FATAL = {
        "Market is not open",
        "Underlying leg market is not open",
        "Authorization Required",
    }
    BLOCK = {
        "Account does not exist",
        "Duplicate clOrdID",
        "Accounts do not match",
        "Invalid account",
        "Account is suspended",
        "Position is in liquidation",
        "Account is in margin call",
        "Account has insufficient Available Balance",
    }
    IGNORE = {
        "table is not valid",
        "filter values are not valid",
        "startTime is invalid",
        "endTime is invalid",
        "depth is invalid",
        "filter columns are not valid",
        "start is invalid",
        "count is invalid",
        "columns are not valid",
        "Negative withdrawal amount",
        "Negative fee amount",
        "Invalid withdrawal amount",
        "Invalid fee amount",
        "Account has insufficient Withdrawable Balance",
        # "Withdrawal ban expires at [Date]
        "Withdrawals currently disabled, please contact Customer Support",
        "transactStatus is not Pending",
        "Invalid orderID",
        "Duplicate orderID",
        "Invalid symbol",
        "Instruments do not match",
        "Instrument not listed for trading yet",
        "Instrument expired",
        "Instrument has no mark price",
        # "Account has no [XBt]"
        "Invalid ordStatus",
        "Invalid triggered",
        "Invalid workingIndicator",
        "Invalid side",
        "Invalid orderQty or simpleOrderQty",
        "Invalid simpleOrderQty",
        "Invalid orderQty",
        "Invalid simpleLeavesQty",
        "Invalid simpleCumQty",
        "Invalid leavesQty",
        "Invalid cumQty",
        "Invalid avgPx",
        "Invalid price",
        "Invalid price tickSize",
        "Invalid displayQty",
        "Unsupported ordType",
        "Unsupported pegPriceType",
        "Invalid pegPriceType for ordType",
        "Invalid pegOffsetValue for pegPriceType",
        "Invalid pegOffsetValue tickSize",
        "Invalid stopPx for ordType",
        "Invalid stopPx tickSize",
        "Unsupported timeInForce",
        "Unsupported execInst",
        "Invalid execInst",
        "Invalid ordType or timeInForce for execInst",
        "Invalid displayQty for execInst",
        "Invalid ordType for execInst",
        "Unsupported contingencyType",
        "Invalid clOrdLinkID for contingencyType",
        "Invalid multiLegReportingType",
        "Invalid currency",
        "Invalid settlCurrency",
        "Underlying leg instrument has no mark price",
        "Price greater than limitUpPrice",
        "Price less than limitDownPrice",
        "Value of positions and orders exceeds account Risk Limit",
        "Value of position and orders exceeds position Risk Limit",
        "Order price is below the liquidation price of current long position",
        "Order price is above the liquidation price of current short position",
        "Executing at order price would lead to immediate liquidation",
        "Executing at order price would push account deeper into margin call",
        "Executing at order price would put account into margin call",
        # "Order had execInst of [Close|ReduceOnly] and side of [Buy|Sell] but current",
        # "position is [100]",
        "Cannot exceed the maximum effective leverage",
        "Value of position and orders exceeds position Risk Limit",
        "Instrument is not taxable",
        "Invalid leverage",
        "Cannot exceed the maximum entry leverage",
        "Position has cross margin enabled",
        "Invalid amount for isolated margin transfer",
        "Position has insufficient isolated margin",
    }
    CANCEL = {
        # 400: "Bad Request",
        401: "Unauthorized",
        403: "Account Restrictions or Bans, Incorrect API Key Permissions, Authentication and Authorization Issues, Network or Server Issues",
        404: "Not Found",
        429: "Rate limit exceeded",
        503: "Service Unavailable, or Deployment/Restart, or System Overload",
        504: "Server Error: Gateway Time-out",
        530: "Server Error",
    }

    def status(res):
        error = res["error"]["message"]
        for status in ErrorStatus:
            if error in status.value:
                return status.name
        error = res["error"]["code"]
        for status in ErrorStatus:
            if error in status.value:
                return status.name
