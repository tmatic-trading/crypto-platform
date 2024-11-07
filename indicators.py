from common.data import BotData, Instrument


class BreakDown:
    symbols = dict()

    @staticmethod
    def add_bot(instrument: Instrument, bot: BotData) -> None:
        symbol = (instrument.symbol, instrument.market)
        if symbol not in BreakDown.symbols:
            BreakDown.symbols[symbol] = dict()
        if bot.timefr not in BreakDown.symbols[symbol]:
            BreakDown.symbols[symbol][bot.timefr] = dict()
        BreakDown.symbols[symbol][bot.timefr][bot] = {
            "bot_name": bot.name,
            "up": 0,
            "dn": 1000000000,
            "first": 0,
            "number": 0,
        }

        return BreakDown.symbols[symbol][bot.timefr][bot]
