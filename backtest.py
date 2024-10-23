import backtest.init
import services as service
from algo.a3 import strategy
from backtest import functions as backtest


bot = strategy.bot
service.display_backtest_parameters(bot=bot)
backtest.load_backtest_data(bot=bot)
backtest.run(bot=bot, strategy=strategy.strategy)
res = backtest.results(bot=bot)

print("\nResults by symbols:")
print("---")
for symbol, values in res.items():
    print("Symbol:", symbol[0])
    print("Start date:", int(bot.backtest_data[symbol][0]["date"]))
    print("End date:", int(bot.backtest_data[symbol][-1]["date"]))
    print("Result:", values["currency"][0], values["result"])
    print("Volume:", values["volume_currency"], values["volume"])
    print("Commission", values["currency"][0], values["commission"])
    print("Max position", values["volume_currency"], values["max_position"])
    print("---")
