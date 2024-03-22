from typing import Union

from api.variables import Variables


class Send(Variables):
    def request(
        self,
        path: str = None,
        verb: str = None,
        postData=None,
        timeout=7,
        teorPrice=None,
    ) -> Union[dict, list, None]:
        """
        Sends a request to the exchange
        """
        print(self.symbol_list)
