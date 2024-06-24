from typing import Union
from api.bitmex.ws import Bitmex
from api.bybit.ws import Bybit
from api.deribit.ws import Deribit

class MetaMarket(type):
    dictionary = dict()
    names = {"Bitmex": Bitmex, "Bybit": Bybit, "Deribit": Deribit}

    def __getitem__(self, item) -> Union[Bitmex, Bybit, Deribit]:
        if item not in self.names:
            raise ValueError(f"{item} not found")
        if item not in self.dictionary:
            self.dictionary[item] = self.names[item]()
            return self.dictionary[item]
        else:
            return self.dictionary[item]


class Markets(Bitmex, Bybit, Deribit, metaclass=MetaMarket):
    pass