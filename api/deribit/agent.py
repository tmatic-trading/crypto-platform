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
                                return -1
                    else:
                        self.logger.error(
                            "There are no entries in the Instrument class."
                        )
                        return -1
                    return 0
                else:
                    error = "A list was expected when loading instruments, but was not received. Reboot"
            else:
                error = "When loading instruments 'result' was not received."
        error = "Invalid data was received when loading tools. " + str(data)
        self.logger.error(error)

        return -1

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
        error = "Invalid data was received when loading tools. " + str(data)
        self.logger.error(error)

        return -1

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
        self.logNumFatal = -1
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
            self.logNumFatal = -1

    def trading_history(self, histCount: int, start_time=None) -> list:
        trade_history = []
        startTime = service.time_converter(start_time)
        limit = min(200, histCount)
        step = 8640000000 # +100 days

        def get_in_thread(id, currency, start, end, limit, data_type, success, num):
            nonlocal trade_history
            cursor = 2
            while cursor > 1:
                print("______cursor", cursor)
                params = {
                    "currency": currency,
                    "start_timestamp": start,
                    "end_timestamp": end, # 2524597200000,  # Fri Dec 31 2049 21:00:00 GMT+0000
                    #"query": "settlement", 
                    "count": limit,
                }
                self.response[id] = {
                    "request_time": time.time() + self.ws_request_delay,
                    "result": None,
                }
                self.logger.info(
                    "Sending "
                    + path
                    + " - currency - "
                    + currency
                    + " - start time - "
                    + str(service.time_converter(start / 1000))
                )
                Agent.ws_request(self, path=path, id=id, params=params)
                while time.time() < self.response[id]["request_time"]:
                    if self.response[id]["result"]:
                        print(id)
                        print("======================================")
                        print(self.response[id])
                        res = self.response[id]["result"][data_type]
                        if isinstance(res, list):
                            for row in res:
                                print("----------------")
                                print(row)
                                if not row["instrument_name"] in self.symbol_category:
                                    Agent.get_instrument(
                                        self, symbol=row["instrument_name"]
                                    )
                                row["symbol"] = (
                                    row["instrument_name"],
                                    self.symbol_category[row["instrument_name"]],
                                    self.name,
                                )
                                if data_type == "logs":
                                    row["execType"] = "Funding"
                                    row["execID"] = (
                                        str(row["user_seq"]) + "_" + currency
                                    )
                                    row["leavesQty"] = row["position"]
                                else:
                                    row["execType"] = "Trade"
                                    row["execID"] = (
                                        str(row["trade_id"]) + self.name + currency
                                    )
                                    row["orderID"] = (
                                        row["order_id"] + self.name + currency
                                    )
                                    row["leavesQty"] = 9999999999999 # leavesQty is not supported by Deribit
                                    row["execFee"] = float(row["fee"])
                                row["category"] = self.symbol_category[
                                    row["instrument_name"]
                                ]
                                row["lastPx"] = row["price"]
                                row["transactTime"] = service.time_converter(
                                    time=row["timestamp"] / 1000, usec=True
                                )
                                if row["category"] == "spot":
                                    row["settlCurrency"] = (row["fee_currency"], self.name)
                                else:
                                    row["settlCurrency"] = self.Instrument[
                                        row["symbol"]
                                    ].settlCurrency
                                row["lastQty"] = row["amount"]
                                row["market"] = self.name
                                if row["direction"] == "sell":
                                    row["side"] = "Sell"
                                else:
                                    row["side"] = "Buy"
                                if row["execType"] == "Funding":
                                    if row["side"] == "Sell":
                                        row["lastQty"] = -row["lastQty"]
                                row["commission"] = "Not supported"
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
                        print("______cursor +", cursor)
                        if cursor:
                            start = res[-1]["timestamp"]
                        break
                    time.sleep(0.05)
                else:
                    self.logger.error(
                        "No response to websocket trading history data request within "
                        + self.ws_request_delay
                        + " seconds. Reboot"
                    )
                    cursor = -1
            if cursor > -1:
                success[num] = "success"

        path = Listing.TRADING_HISTORY
        '''for currency in self.settleCoin_list:
            '''

        '''path = Listing.TRADING_HISTORY
        for currency in self.settleCoin_list:
            params = {
                "currency": currency,
                "start_timestamp": service.time_converter(time=start_time),
                "end_timestamp": 2524597200000,  # Fri Dec 31 2049 21:00:00 GMT+0000
                "count": histCount,
            }'''
        while startTime < service.time_converter(datetime.now(tz=timezone.utc)):
            endTime = startTime + step
            if endTime < 1577826000000: # Dec 31 2019 21:00:00 GMT+0000
                endTime = 1577826000000
            print("))))))))))))))))))))))))))))))", startTime, service.time_converter(datetime.now(tz=timezone.utc)))
            threads, success = [], []
            for currency in ["BTC"]: # self.settleCoin_list:
                success.append(None)
                id = f"{path}_{currency}"
                t = threading.Thread(
                    target=get_in_thread,
                    args=(id, currency, startTime, endTime, limit, "trades", success, len(success) - 1),
                )
                threads.append(t)
                t.start()
            [thread.join() for thread in threads]
            for s in success:
                if not s:
                    return
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
