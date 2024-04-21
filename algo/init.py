# Robot strategy initialization file


from bots.variables import Variables as bot
import algo.strategy
from api.api import Markets

def init_algo():
    bybit = Markets["Bybit"]
    bitmex = Markets["Bitmex"]
    bot.robo["Btc"] = algo.strategy.algo
    algo.strategy.init_variables(robot=bybit.robots["Btc"])
    bot.robo["Super"] = algo.strategy.algo
    algo.strategy.init_variables(robot=bitmex.robots["Super"])
    bot.robo["Btc_inverse"] = algo.strategy.algo
    algo.strategy.init_variables(robot=bybit.robots["Btc_inverse"])
