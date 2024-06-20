import json
import os
from collections import OrderedDict
from datetime import datetime
from typing import Union

import services as service
from api.http import Send

from .path import Listing
from .ws import Deribit


class Agent(Deribit):
    def get_active_instruments(self) -> int:
        data = Send.request(self, path=Listing.GET_ACTIVE_INSTRUMENTS, verb="GET")

        print("___________", type(data))

        for el in data["result"]:
            print("----------------------------")
            print(el)

        os.abort()
