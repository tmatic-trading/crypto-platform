from api.api import WS, Markets
import services as service


def get_instrument(ws: Markets, symbol: tuple):
    """
    When running backtesting outside main.py there is no connection to any 
    market and no information about instruments is received. Therefore, we 
    have to get information via an http request. This request is made only 
    once, since the received information is saved in the database in the 
    `backtest` table to speed up the program.
    """
    if ws.Instrument.get_keys() == None:
        WS.get_active_instruments(ws)
    elif symbol not in ws.Instrument.get_keys():
        qwr = (
            "select * from backtest where SYMBOL ='"
            + symbol[0]
            + "' and MARKET = '"
            + ws.name
            + "';"
        )
        data = service.select_database(qwr)
        if not data:
            WS.get_active_instruments(ws)
            service.add_symbol_database(
                    instrument=ws.Instrument[symbol], table="backtest"
                )
        else:
            data = data[0]
            instrument = ws.Instrument.add(symbol)
            service.set_symbol(instrument=instrument, data=data)

    