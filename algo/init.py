# Robot strategy initialization file


from bots.variables import Variables as bot
import algo.strategy
from api.api import Markets

def init_algo(self: Markets):
    for emi, robot in self.robots.items():
        if robot["STATUS"] == "WORK":
            bot.robo[emi] = algo.strategy.algo
            algo.strategy.init_variables(robot=self.robots[emi])