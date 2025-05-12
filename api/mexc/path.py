from enum import Enum


class Listing(str, Enum):
    pass

    def __str__(self) -> str:
        return self.value