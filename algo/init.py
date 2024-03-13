# Robot strategy initialization file

from bots.variables import Variables as bot
import algo.strategy
from api.websockets import Websockets

def init_algo():
    pass
    '''ws = Websockets.connect["Bitmex"]
    bot.robo["Super"] = algo.strategy.algo
    algo.strategy.init_variables(robot=ws.robots["Super"])
    bot.robo["2"] = algo.strategy.algo
    algo.strategy.init_variables(robot=ws.robots["2"])
    bot.robo["Eth"] = algo.strategy.algo
    algo.strategy.init_variables(robot=ws.robots["Eth"])'''
