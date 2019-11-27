from __future__ import(absolute_import, division, print_function, unicode_literals)
from datetime import datetime, timedelta
import backtrader as bt
from backtrader import cerebro
import time
import ccxt
from ccxtbt import CCXTStore

#import TestStrategy


def connect_broker():
    apikey = 'siX-NO9IeVWstmn1zA2e904N'
    secret = 'ieEjNwz9TDAzg_B2EVkpgzkchDeNmyy9_UNB03B567Gwh0A_'
    
    cerebro = bt.Cerebro(quicknotify=True)
    
    
    # Add the strategy
    cerebro.addstrategy(TestStrategy)
    
    # Create our store
    config = {'apiKey': apikey,
                'secret': secret,
                'enableRateLimit': True
                }
    
    # IMPORTANT NOTE - Kraken (and some other exchanges) will not return any values
    # for get cash or value if You have never held any LTC coins in your account.
    # So switch LTC to a coin you have funded previously if you get errors
    store = CCXTStore(exchange='bitmex', currency='BTC', config=config, retries=5, debug=False, testnet=True)
    
    
    
    print("I am here")    
    print(store.exchange.urls)    
    
    
    broker = store.getbroker()
    cerebro.setbroker(broker)
    
    # Get our data
    # Drop newest will prevent us from loading partial data from incomplete candles
    hist_start_date = datetime.utcnow() - timedelta(minutes=50)
    data = store.getdata(dataname='BTC/USD', name="BTCUSD",
                             timeframe=bt.TimeFrame.Minutes, fromdate=hist_start_date,
                             compression=1, ohlcv_limit=50, drop_newest=True) #, historical=True)
    
    # Add the feed
    cerebro.adddata(data)
    
    # Run the strategy
    cerebro.run()

class TestStrategy(bt.Strategy):
    params = (
        ('maperiod', 1),
        ('printlog', True),
    )

    def log(self, txt, dt=None, doprint=False):
        ''' Logging function fot this strategy'''
        if self.params.printlog or doprint:
            dt = dt or self.datas[0].datetime.datetime(0)
            print('%s, %s' % (dt.isoformat(), txt))

    def __init__(self):
        # Keep a reference to the "close" line in the data[0] dataseries
        self.dataclose = self.datas[0].close
        self.dataopen = self.datas[0].open

        # To keep track of pending orders and buy price/commission
        self.order = None
        self.buyprice = None
        self.buycomm = None

        # Add a MovingAverageSimple indicator
        self.sma = bt.indicators.SimpleMovingAverage(
            self.datas[0], period=self.params.maperiod)

    def notify_order(self, order):
        if order.status in [order.Submitted, order.Accepted]:
            # Buy/Sell order submitted/accepted to/by broker - Nothing to do
            return

        # Check if an order has been completed
        # Attention: broker could reject order if not enough cash
        if order.status in [order.Completed]:
            if order.isbuy():
                self.log(
                    'BUY EXECUTED, Price: %.2f, Cost: %.2f, Comm %.2f' %
                    (order.executed.price,
                     order.executed.value,
                     order.executed.comm))

                self.buyprice = order.executed.price
                self.buycomm = order.executed.comm
            else:  # Sell
                self.log('SELL EXECUTED, Price: %.2f, Cost: %.2f, Comm %.2f' %
                         (order.executed.price,
                          order.executed.value,
                          order.executed.comm))

            self.bar_executed = len(self)

        elif order.status in [order.Canceled, order.Margin, order.Rejected]:
            self.log('Order Canceled/Margin/Rejected')

        # Write down: no pending order
        self.order = None

    def notify_trade(self, trade):
        if not trade.isclosed:
            return

        self.log('OPERATION PROFIT, GROSS %.2f, NET %.2f' %
                 (trade.pnl, trade.pnlcomm))

    def next(self):
        # Simply log the closing price of the series from the reference
        self.log('Open %.2f , Close %.2f' % (self.dataopen[0], self.dataclose[0]))

        # Check if an order is pending ... if yes, we cannot send a 2nd one
        if self.order:
            return

        # Check if we are in the market
        if not self.position:

            # Not yet ... we MIGHT BUY if ...
            #if self.dataclose[0] > self.sma[0]:

                # BUY, BUY, BUY!!! (with all possible default parameters)
                self.log('BUY CREATE, %.2f' % self.dataclose[0])

                # Keep track of the created order to avoid a 2nd order
                self.order = self.buy()

        else:

            if self.dataclose[0] < self.sma[0]:
                # SELL, SELL, SELL!!! (with all possible default parameters)
                self.log('SELL CREATE, %.2f' % self.dataclose[0])

                # Keep track of the created order to avoid a 2nd order
                self.order = self.sell()

    def stop(self):
        self.log('(MA Period %2d) Ending Value %.2f' %
                 (self.params.maperiod, self.broker.getvalue()), doprint=True)


if __name__ == '__main__':
    cerebro = bt.Cerebro()

    hist_start_date = datetime.utcnow() - timedelta(minutes=10)
    data_min = bt.feeds.CCXT(exchange='bitmex', symbol="BTC/USD", name="btc_usd_min", fromdate=hist_start_date,
                             timeframe=bt.TimeFrame.Minutes)
    
                  
    cerebro.adddata(data_min)
    cerebro.addstrategy(TestStrategy)
    connect_broker()
   
    
    # Set our desired cash start
#    cerebro.broker.setcash(1000.0)

    # Add a FixedSize sizer according to the stake
    cerebro.addsizer(bt.sizers.FixedSize, stake=10)

    # Set the commission
    cerebro.broker.setcommission(commission=0.0)

    # Run over everything
    cerebro.run(maxcpus=1)
    

