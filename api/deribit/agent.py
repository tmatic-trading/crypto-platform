import json
import os
import threading
import time
from collections import OrderedDict
from datetime import datetime, timedelta, timezone
from typing import Union

import services as service
from api.http import Send

from .path import Listing
from .ws import Deribit


class Agent(Deribit):
    def get_active_instruments(self) -> int:
        """
        Retrieves available trading instruments. This method can be used to
        see which instruments are available for trading, or which
        instruments have recently expired.
        """
        path = self.api_version + Listing.GET_ACTIVE_INSTRUMENTS
        data = Send.request(self, path=path, verb="GET")
        if isinstance(data, dict):
            if "result" in data:
                if isinstance(data["result"], list):
                    for values in data["result"]:
                        Agent.fill_instrument(
                            self,
                            values=values,
                        )
                    if self.Instrument.get_keys():
                        for symbol in self.symbol_list:
                            if symbol not in self.Instrument.get_keys():
                                self.logger.error(
                                    "Unknown symbol: "
                                    + str(symbol)
                                    + ". Check the SYMBOLS in the .env.Deribit file. Perhaps the name of the symbol does not correspond to the category or such symbol does not exist. Reboot."
                                )
                                return 1001
                    else:
                        self.logger.error(
                            "There are no entries in the Instrument class."
                        )
                        return 1001
                    return 0
                else:
                    error = "A list was expected when loading instruments, but was not received. Reboot"
            else:
                error = "When loading instruments 'result' was not received."
        else:
            error = "Invalid data was received when loading tools. " + str(data)
        self.logger.error(error)

        return 1001

    def get_instrument(self, symbol: str) -> None:
        path = Listing.GET_INSTRUMENT_DATA
        self.logger.info("Sending " + path + " - symbol - " + symbol)
        params = {"instrument_name": symbol}
        id = f"{path}_{symbol}"
        self.response[id] = {
            "request_time": time.time() + self.ws_request_delay,
            "result": None,
        }
        Agent.ws_request(self, path=path, id=id, params=params)
        while time.time() < self.response[id]["request_time"]:
            if self.response[id]["result"]:
                Agent.fill_instrument(self, values=self.response[id]["result"])
                break
            time.sleep(0.05)
        else:
            self.logger.error(
                "No response to websocket instrument data request symbol="
                + symbol
                + " within "
                + self.ws_request_delay
                + " seconds. Reboot"
            )

    def fill_instrument(self, values: dict) -> str:
        """
        Filling the instruments data.

        The data is stored in the Instrument class using MetaInstrument class.
        The data fields of different exchanges are unified through the
        Instrument class. See detailed description of the fields there.
        """
        category = values["kind"] + " " + values["instrument_type"]
        self.symbol_category[values["instrument_name"]] = category
        symbol = (values["instrument_name"], category, self.name)
        instrument = self.Instrument[symbol]
        instrument.symbol = values["instrument_name"]
        instrument.category = category
        instrument.baseCoin = values["base_currency"]
        instrument.quoteCoin = values["quote_currency"]
        if "settlement_currency" in values:
            instrument.settlCurrency = (values["settlement_currency"], self.name)
        else:
            instrument.settlCurrency = (
                "None",
                self.name,
            )
        instrument.expire = service.time_converter(
            values["expiration_timestamp"] / 1000
        )
        if instrument.expire.year == 3000:
            instrument.expire = "Perpetual"
        instrument.tickSize = values["tick_size"]
        instrument.price_precision = service.precision(number=instrument.tickSize)
        instrument.minOrderQty = values["min_trade_amount"]
        instrument.qtyStep = values["contract_size"]
        instrument.precision = service.precision(number=instrument.qtyStep)
        if values["is_active"]:
            instrument.state = "Normal"
        else:
            instrument.state = "Inactive"
        instrument.multiplier = 1
        instrument.myMultiplier = 1
        if category == "spot":
            self.Instrument[symbol].fundingRate = "None"
            self.Instrument[symbol].avgEntryPrice = "None"
            self.Instrument[symbol].marginCallPrice = "None"
            self.Instrument[symbol].currentQty = "None"
            self.Instrument[symbol].unrealisedPnl = "None"
        if category == "option":
            self.Instrument[symbol].fundingRate = "None"
        self.Instrument[symbol].asks = [[0, 0]]
        self.Instrument[symbol].bids = [[0, 0]]
        self.Instrument[symbol].valueOfOneContract = 1

    def open_orders(self) -> int:
        """
        Retrieves list of user's open orders across many currencies.
        """
        msg = {
            "jsonrpc": "2.0",
            "id": 1953,
            "method": "private/get_open_orders",
            "params": {},
        }
        path = self.api_version + Listing.OPEN_ORDERS
        data = Send.request(self, path=path, verb="POST", postData=msg)
        if isinstance(data, dict):
            if "result" in data:
                if isinstance(data["result"], list):
                    for order in data["result"]:
                        category = self.symbol_category[order["instrument_name"]]
                        symbol = (order["instrument_name"], category, self.name)
                        instrument = self.Instrument[symbol]
                        order["symbol"] = symbol
                        order["orderID"] = order["order_id"]
                        if "label" in order and order["label"]:
                            order["clOrdID"] = order["label"]
                        order["orderQty"] = order["amount"]
                        order["settlCurrency"] = instrument.settlCurrency
                        order["ordStatus"] = order["order_state"]
                        order["leavesQty"] = order["amount"] - order["filled_amount"]
                        order["transactTime"] = service.time_converter(
                            time=int(order["last_update_timestamp"]) / 1000, usec=True
                        )
                    self.setup_orders = data["result"]
                    return 0
                else:
                    error = "The list was expected when the orders were loaded, but was not received. Reboot"
            else:
                error = "When loading instruments 'result' was not received."
        else:
            error = "Invalid data was received when loading instruments. " + str(data)
        self.logger.error(error)

        return 1001

    def get_user(self) -> None:
        """
        Returns the user ID and other useful information about the user and
        places it in self.user. If unsuccessful, logNumFatal is not 0.
        """
        path = self.api_version + Listing.GET_ACCOUNT_INFO
        msg = {
            "jsonrpc": "2.0",
            "id": 2515,
            "method": "private/get_account_summaries",
            "params": {"extended": True},
        }
        data = Send.request(self, path=path, verb="POST", postData=msg)
        if isinstance(data, dict):
            self.user_id = data["result"]["id"]
            for values in data["result"]["summaries"]:
                account = self.Account[values["currency"]]
                account.account = data["result"]["id"]
                account.settlCurrency = values["currency"]
            return
        self.logNumFatal = 1001
        message = (
            "A user ID was requested from the exchange but was not received. Reboot"
        )
        self.logger.error(message)

    def get_wallet_balance(self) -> None:
        """
        Receives data on currency accounts through the websocket channel
        user.portfolio.any in the api/deribit/ws.py
        """
        pass

    def get_position_info(self):
        path = self.api_version + Listing.GET_POSITION_INFO
        data = Send.request(self, path=path, verb="GET")
        if isinstance(data, dict):
            for values in data["result"]:
                category = self.symbol_category[values["instrument_name"]]
                symbol = (values["instrument_name"], category, self.name)
                instrument = self.Instrument[symbol]
                instrument.currentQty = values["size"]
                if values["direction"] == "sell":
                    instrument.currentQty = -instrument.currentQty
                instrument.avgEntryPrice = values["average_price"]
                instrument.unrealisedPnl = values["total_profit_loss"]
                instrument.marginCallPrice = values["estimated_liquidation_price"]
                instrument.state = "None"
        else:
            self.logger.error(
                "The dict was expected when the positions were loaded, but it was not received. Reboot."
            )
            self.logNumFatal = 1001

    def trading_history(self, histCount: int, start_time=None) -> list:
        """
        Downloading trading and funding history from the endpoints:
            private/get_user_trades_by_currency_and_time
            history from private/get_transaction_log

        Provided data
        -------------
        endpoint                                        trades  funding period
        private/get_user_trades_by_currency_and_time    yes     no      last 5 days
        private/get_transaction_log                     yes     yes     full

        Deribit only provides trading history from
        'private/get_user_trades_by_currency_and_time' endpoint for last 5
        days, so we use 'private/get_transaction_log' endpoint to get
        trades made earlier than 5 days ago.

        label (clOrdID)
        ---------------
        endpoint                                        supported
        private/get_user_trades_by_currency_and_time    yes
        private/get_transaction_log                     no

        Trades made more than 5 days ago will be downloaded without the
        clOrdID field.

        Parameters
        ----------
            histCount - the function returns data by chunks in the amount of
        histCount
            start_time - date when a new chunk of data will be downloaded

        Notes
        -----
        The function gets the same trades from two different endpoints. So 
        there will be trades with the same execID. It is preferable to save 
        trades to the database from the
        ``private/get_user_trades_by_currency_and_time`` becuase it contains 
        the label (clOrdID) field. As far Tmatic saves trades with the same 
        execID only once and ignores repeating trades, this function 
        corrects the timestamp of the trades from the endpoint mentioned 
        above for 1ms ahead. Thus after sorting, the trades from the 
        ``private/get_user_trades_by_currency_and_time`` are always first.
        """
        trade_history = []
        startTime = service.time_converter(start_time)
        limit = min(200, histCount)  # must be > 1
        limit = 28
        step = 86400000  # 8640000000 # +100 days
        step = 8640000000
        """msg = \
        {
        "jsonrpc" : "2.0",
        "id" : 5275,
        "method" : "private/sell",
        "params" : {
            "instrument_name" : "BTC-PERPETUAL",
            "amount" : 40,
            "type" : "market",
            "label" : "Btc_Deribit"
        }
        }
        self.ws.send(json.dumps(msg))
        os.abort()"""

        def get_in_thread(path, currency, start, end, limit, data_type, success, num):
            nonlocal trade_history
            cursor = limit
            print(";;;;;")
            print(start, service.time_converter(time=start / 1000))
            print(end, service.time_converter(time=end / 1000))
            print(limit)
            last_execID = ""
            execID = ""
            continuation = 0
            id = f"{path}_{currency}"
            while cursor > limit - 1:
                print("______cursor", cursor)
                params = {
                    "currency": currency,
                    "start_timestamp": start,
                    "end_timestamp": end,  # 2524597200000,  # Fri Dec 31 2049 21:00:00 GMT+0000
                    #"query": "settlement, trade",
                    "count": limit,
                }
                if data_type == "trades":
                    params["sorting"] = "asc"
                if continuation:
                    params["continuation"] = continuation
                self.response[id] = {
                    "request_time": time.time() + self.ws_request_delay,
                    "result": None,
                }
                self.logger.info(
                    "Sending "
                    + path
                    + " - currency - "
                    + currency
                    + " - start - "
                    + str(service.time_converter(start / 1000))
                    + " - end - "
                    + str(service.time_converter(end / 1000))
                )
                Agent.ws_request(self, path=path, id=id, params=params)
                while time.time() < self.response[id]["request_time"]:
                    if self.response[id]["result"]:
                        print(id)
                        print("======================================")
                        #print(self.response[id]["result"])
                        print(":::::::::::::::::::", id, data_type, "____", *self.response[id]["result"])
                        res = self.response[id]["result"][data_type]
                        """for r in res:
                            t = service.time_converter(time = r["timestamp"]/1000)
                            if r["type"] == "trade":
                                print("-------------------")
                                #print(service.time_converter(time = r["timestamp"]/1000))
                                #for key, value in r.items():
                                #    print(key, value)
                                print(t, r["side"], r["trade_id"], r["amount"], r["price"], r["order_id"], r["instrument_name"])
                            print("-------------------")
                            if "label" in r:
                                l = r["label"]
                            else:
                                l = "None"
                            print(t, r["direction"], r["trade_id"], r["amount"], r["price"], r["order_id"], l)
                        os.abort()"""

                        if data_type == "logs":
                            res = list(filter(lambda x: x["type"] in ["settlement", "trade"], res))
                            continuation = self.response[id]["result"]["continuation"]
                            print("___________________", continuation)

                        if isinstance(res, list):
                            for row in res:
                                    '''if data_type == "trades" or (
                                        data_type == "logs"
                                        and row["type"] in ["settlement", "trade"]
                                    ):'''
                                    print("----------------")
                                    #print(row)
                                    if (
                                        not row["instrument_name"]
                                        in self.symbol_category
                                    ):
                                        Agent.get_instrument(
                                            self, symbol=row["instrument_name"]
                                        )
                                    row["symbol"] = (
                                        row["instrument_name"],
                                        self.symbol_category[row["instrument_name"]],
                                        self.name,
                                    )
                                    if data_type == "logs":
                                        if row["type"] == "settlement":
                                            row["execType"] = "Funding"
                                            row["execID"] = (
                                                str(row["user_seq"])
                                                + "_"
                                                + self.name
                                                + "_"
                                                + currency
                                            )
                                            row["leavesQty"] = row["position"]
                                            row["execFee"] = row["total_interest_pl"]
                                        elif row["type"] == "trade":
                                            row["execType"] = "Trade"
                                            row["execID"] = (
                                                str(row["trade_id"])
                                                + "_"
                                                + str(row["user_seq"])
                                                + "_"
                                                + self.name
                                                + "_"
                                                + currency
                                            )
                                            row["orderID"] = (
                                                row["order_id"]
                                                + "_"
                                                + self.name
                                                + "_"
                                                + currency
                                            )
                                            row[
                                                "leavesQty"
                                            ] = 9999999999999  # leavesQty is 
                                            # not supported by Deribit
                                            # row["execFee"] = row["commission"]
                                        if (
                                            "buy" in row["side"]
                                            or row["side"] == "long"
                                        ):
                                            row["side"] = "Buy"
                                        elif (
                                            "sell" in row["side"]
                                            or row["side"] == "short"
                                        ):
                                            row["side"] = "Sell"
                                    else:
                                        row["execType"] = "Trade"
                                        row["execID"] = (
                                            str(row["trade_id"])
                                            + "_"
                                            + str(row["trade_seq"])
                                            + "_"
                                            + self.name
                                            + "_"
                                            + currency
                                        )
                                        row["orderID"] = (
                                            row["order_id"] + self.name + currency
                                        )
                                        row[
                                            "leavesQty"
                                        ] = 9999999999999  # leavesQty is not 
                                        # supported by Deribit
                                        row["execFee"] = row["fee"]
                                        if row["direction"] == "sell":
                                            row["side"] = "Sell"
                                        else:
                                            row["side"] = "Buy"
                                        row["timestamp"] -= 1 # Puts the trades
                                        # from data_type="trades" in front of 
                                        # the same trades from data_type="logs"
                                    if "label" in row:
                                        row["clOrdID"] = row["label"]
                                    row["category"] = self.symbol_category[
                                        row["instrument_name"]
                                    ]
                                    row["lastPx"] = row["price"]
                                    row["transactTime"] = service.time_converter(
                                        time=row["timestamp"] / 1000, usec=True
                                    )
                                    if row["category"] == "spot":
                                        row["settlCurrency"] = (
                                            row["fee_currency"],
                                            self.name,
                                        )
                                    else:
                                        row["settlCurrency"] = self.Instrument[
                                            row["symbol"]
                                        ].settlCurrency
                                    row["lastQty"] = row["amount"]
                                    row["market"] = self.name
                                    if row["execType"] == "Funding":
                                        if row["side"] == "Sell":
                                            row["lastQty"] = -row["lastQty"]
                                    row["commission"] = "Not supported"
                                    row["price"] = "Not supported"
                                    print(row["transactTime"])

                                    trade_history.append(row)
                        else:
                            self.logger.error(
                                "The list was expected when the trading history were loaded, but for the currency "
                                + currency
                                + " it was not received. Reboot."
                            )
                            cursor = -1
                            break
                        cursor = len(res)
                        print("______________cursor +", cursor)
                        if cursor:
                            end = res[-1]["timestamp"]
                            last_execID = res[-1]["execID"]
                            if data_type == "trades":
                                end = res[-1]["timestamp"]
                            print("__________________________start", start, res[0]["timestamp"], res[-1]["timestamp"], res[0]["timestamp"] - res[-1]["timestamp"], res[-1]["execID"])
                            time.sleep(0.5)
                        break
                    time.sleep(0.05)
                else:
                    self.logger.error(
                        "No response to websocket trading history data request within "
                        + str(self.ws_request_delay)
                        + " seconds. Reboot"
                    )
                    cursor = -1
                if execID == last_execID:
                    print("____________exit", execID, last_execID)
                    break
                execID = last_execID
                if continuation is None:
                    break
            if cursor > -1:
                success[num] = "success"

        """for currency in self.settleCoin_list:
            """

        """path = Listing.TRADING_HISTORY
        for currency in self.settleCoin_list:
            params = {
                "currency": currency,
                "start_timestamp": service.time_converter(time=start_time),
                "end_timestamp": 2524597200000,  # Fri Dec 31 2049 21:00:00 GMT+0000
                "count": histCount,
            }"""

        while startTime < service.time_converter(datetime.now(tz=timezone.utc)):
            endTime = startTime + step
            if endTime < 1577826000000:  # Dec 31 2019 21:00:00 GMT+0000
                endTime = 1577826000000
            get_last_trades = False
            if endTime >= service.time_converter(datetime.now(tz=timezone.utc)):
                get_last_trades = True
            print(
                "))))))))))))))))))))))))))))))",
                startTime,
                service.time_converter(datetime.now(tz=timezone.utc)),
            )
            threads, success = [], []
            for currency in ["BTC"]:  # self.settleCoin_list:
                success.append(None)
                path = Listing.TRADES_AND_FUNDING_TRANSACTION_LOG
                t = threading.Thread(
                    target=get_in_thread,
                    args=(
                        path,
                        currency,
                        startTime,
                        endTime,
                        limit,
                        "logs",
                        success,
                        len(success) - 1,
                    ),
                )
                threads.append(t)
                t.start()
                '''if get_last_trades:
                    print("______________________________________get_last_trades")
                    success.append(None)
                    path = Listing.TRADES_LAST_5_DAYS
                    t = threading.Thread(
                        target=get_in_thread,
                        args=(
                            path,
                            currency,
                            startTime,
                            endTime,
                            limit,
                            "trades",
                            success,
                            len(success) - 1,
                        ),
                    )
                    threads.append(t)
                    t.start()'''
            [thread.join() for thread in threads]
            for s in success:
                if not s:
                    return
                
            tmp = []
            for el in trade_history:
                if el not in tmp:
                    tmp.append(el)
            trade_history = tmp
            message = (
                self.name
                + " - loading trading history, start_time="
                + str(service.time_converter(startTime / 1000))
                + ", received: "
                + str(len(trade_history))
                + " records."
            )
            self.logger.info(message)
            if len(trade_history) > histCount:
                break
            startTime = endTime
        trade_history.sort(key=lambda x: x["transactTime"])

        

        print("___________________________FINISH", len(trade_history))
        for row in trade_history:
            print(
                row["transactTime"],
                row["execType"],
                row["symbol"],
                row["side"],
                row["lastQty"],
                row["lastPx"],
                # row["lastQty"],
                row["execID"],
            )

        os.abort()

        return trade_history

        msg = {
            "method": "private/get_transaction_log",
            "params": {
                "currency": "BTC",
                "start_timestamp": 1717243432000,
                "end_timestamp": 1719489832000,
                "count": 50,
            },
            "jsonrpc": "2.0",
            "id": 4,
        }

        path = self.api_version + "private/get_transaction_log"
        data = Send.request(self, path=path, verb="POST", postData=msg)
        for res in data["result"]["logs"]:
            print("--------------")
            for key, value in res.items():
                print(key, value)
            """print("type", res["type"])
            print("side", res["side"])
            if "amount" in res:
                print("amount", res["amount"])
            print("interest_pl", res["interest_pl"])
            print("trade_id", res["trade_id"])
            print("commission", res["commission"])
            print("symbol", res["instrument_name"])
            print("equity", res["equity"])"""
            print("timestamp", service.time_converter(time=res["timestamp"] / 1000))
            # print(service.time_converter(time=set["timestamp"] / 1000))
        # print("___________________history", data)

        msg = {
            "jsonrpc": "2.0",
            "id": 8304,
            "method": "private/get_settlement_history_by_currency",
            "params": {"currency": "BTC", "type": "settlement", "count": 100},
        }

        path = self.api_version + "private/get_settlement_history_by_currency"
        data = Send.request(self, path=path, verb="POST", postData=msg)

        print(data)

        for res in data["result"]["settlements"]:
            print("----------------")
            print(res)
            print(service.time_converter(time=res["timestamp"] / 1000))

    def ws_request(self, path: str, id: str, params: dict) -> None:
        msg = {"method": path, "params": params, "jsonrpc": "2.0", "id": id}
        self.ws.send(json.dumps(msg))
