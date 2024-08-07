from enum import Enum


class Message(str, Enum):
    pass

    def __str__(self) -> str:
        return self.value


class ErrorMessage(str, Enum):
    BOT_FOLDER_NOT_FOUND = (
        "``{BOT_NAME}`` bot is in the database but there is no subdirectory named "
        + "``{BOT_NAME}`` in the ``algo`` folder. You should either delete this "
        + "bot using ``Bot menu`` or restore its folder in the ``algo`` folder, "
        + "then restart <f3> Tmatic."
    )
    BOT_ATTRIBUTE_ERROR = (
        "There was an error loading strategy.py:\n\n{EXCEPTION}\n\n"
        + "You are probably trying to use an exchange that is not connected. "
        + "You should either delete ``{BOT_NAME}`` using the ``Bot Menu`` or "
        + "correct the strategy file or add the exchange in the .env file."
    )

    def __str__(self) -> str:
        return self.value
