from common.data import BotData, Instrument


class BreakDown:
    symbols = dict()

    def __init__(self, instrument: Instrument, bot: BotData) -> None:
        self.symbol = (instrument.symbol, instrument.market)
        self.bot = bot
        self.parameters = dict()
        self.name = "BreakDown"
        if self.symbol not in BreakDown.symbols:
            BreakDown.symbols[self.symbol] = dict()
        if bot.timefr not in BreakDown.symbols[self.symbol]:
            BreakDown.symbols[self.symbol][bot.timefr] = dict()
        self.default()

    def default(self):
        BreakDown.symbols[self.symbol][self.bot.timefr][self.bot] = {
            "bot_name": self.bot.name,
            "symbol": self.symbol,
            "up": 0,
            "dn": 1000000000,
            "first": 0,
            "number": 0,
        }
        self.parameters = BreakDown.symbols[self.symbol][self.bot.timefr][self.bot]
