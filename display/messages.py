from enum import Enum


class Message(str, Enum):
    pass

    def __str__(self) -> str:
        return self.value
    
    
class ErrorMessage(str, Enum):
    BOT_FOLDER_NOT_FOUND = (
        "``{BOT_NAME}`` bot is in the database but there is no the folder named "
        + "``{BOT_NAME}`` in the ``algo`` folder. You should either delete this "
        + "bot using ``Bot menu`` or restore its folder in the ``algo`` folder, "
        + "then restart <f3> Tmatic."
    )

    def __str__(self) -> str:
        return self.value
    