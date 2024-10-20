import backtest.init
import services as service
from algo.a3 import strategy
from backtest import functions as backtest

bot = strategy.bot
service.display_backtest_parameters(bot=bot)
backtest.load_backtest_data(
    market="Bitmex", symb="XBTUSD", timefr="1min", bot_name=bot.name
)

# data = strategy.bot.backtest_data
# print(data)

"""for bot.iter in range(len(data)):
    print(data[bot.iter])"""


# strategy.strategy()
