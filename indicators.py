from common.data import BotData, Instrument


class BreakDown:
    symbols = dict()

    def __init__(self, instrument: Instrument, bot: BotData) -> None:
        self.symbol = (instrument.symbol, instrument.market)
        self.bot = bot
        self.name = "BreakDown"
        if self.symbol not in BreakDown.symbols:
            BreakDown.symbols[self.symbol] = dict()
        if bot.timefr not in BreakDown.symbols[self.symbol]:
            BreakDown.symbols[self.symbol][bot.timefr] = dict()
        self.setup()
        self.parameters = BreakDown.symbols[self.symbol][self.bot.timefr][self.bot.name]

    def setup(self):
        BreakDown.symbols[self.symbol][self.bot.timefr][self.bot.name] = {
            "bot_name": self.bot.name,
            "symbol": self.symbol,
            "up": 0,
            "dn": 1000000000,
            "first": 0,
            "number": 0,
        }

    def default(self):
        self.parameters["first"] = 0
        self.parameters["number"] = 0


def clean_indicators(bot_name: str, timefr="") -> None:
    for symbol in BreakDown.symbols.copy():
        if timefr:
            if timefr in BreakDown.symbols[symbol]:
                if bot_name in BreakDown.symbols[symbol][timefr]:
                    del BreakDown.symbols[symbol][timefr][bot_name]
                if not BreakDown.symbols[symbol][timefr]:
                    del BreakDown.symbols[symbol][timefr]
        else:
            for tf in BreakDown.symbols[symbol].copy():
                if bot_name in BreakDown.symbols[symbol][tf]:
                    del BreakDown.symbols[symbol][tf][bot_name]
                if not BreakDown.symbols[symbol][tf]:
                    del BreakDown.symbols[symbol][tf]
        if not BreakDown.symbols[symbol]:
            del BreakDown.symbols[symbol]

