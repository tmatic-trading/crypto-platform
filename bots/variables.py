from collections import OrderedDict

from common.variables import Variables as var


class Variables:
    full_symbol_list = var.symbol_list.copy()
    robots = OrderedDict()
    frames = dict()
    framing = dict()
    emi_list = list()
    robo = dict()
    robots_status = dict()
    missing_days_number = 2
