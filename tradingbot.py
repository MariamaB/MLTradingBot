from alpaca_trade_api.common import URL
from lumibot.brokers import Alpaca
from lumibot.backtesting import YahooDataBacktesting
from lumibot.entities import Asset
from lumibot.strategies.strategy import Strategy
from lumibot.traders import Trader
from datetime import datetime 
from alpaca_trade_api import REST 
from timedelta import Timedelta 
from finbert_utils import estimate_sentiment

API_KEY = "YOUR API KEY" 
API_SECRET = "YOUR API SECRET" 
BASE_URL = "https://paper-api.alpaca.markets"

ALPACA_CREDS = {
    "API_KEY":API_KEY, 
    "API_SECRET": API_SECRET, 
    "PAPER": True
}
SYMBOL = "TSLA"
ASSET_TYPE = "stock"

class MLTrader(Strategy): 
    def initialize(self, symbol: str = SYMBOL, cash_at_risk: float = .5):
        self.symbol = symbol
        self.sleeptime = "1M"
        self.last_trade = None 
        self.cash_at_risk = cash_at_risk
        self.api = REST(base_url=URL(BASE_URL), key_id=API_KEY, secret_key=API_SECRET)

    def position_sizing(self): 
        cash = self.get_portfolio_value()
        last_price = self.get_last_price(self.symbol)
        quantity = round(cash * self.cash_at_risk / last_price,0)
        return cash, last_price, quantity

    def get_dates(self): 
        today = self.get_datetime()
        three_days_prior = today - Timedelta(days=3)
        return today.strftime('%Y-%m-%d'), three_days_prior.strftime('%Y-%m-%d')

    def get_sentiment(self): 
        today, three_days_prior = self.get_dates()
        news = self.api.get_news(symbol=self.symbol, 
                                 start=three_days_prior, 
                                 end=today) 
        news = [ev.__dict__["_raw"]["headline"] for ev in news]
        probability, sentiment = estimate_sentiment(news)
        return probability, sentiment 

    def on_trading_iteration(self):
        cash, last_price, quantity = self.position_sizing() 
        probability, sentiment = self.get_sentiment()

        if cash > last_price: 
            if sentiment == "positive" and probability > .999: 
                if self.last_trade == "sell": 
                    self.sell_all() 
                order = self.create_order(
                    Asset(symbol=self.symbol, asset_type=ASSET_TYPE),
                    # self.symbol,
                    quantity, 
                    "buy", 
                    type="bracket", 
                    take_profit_price=last_price*1.20, 
                    stop_loss_price=last_price*.95
                )
                self.submit_order(order) 
                self.last_trade = "buy"

            elif sentiment == "negative" and probability > .999: 
                if self.last_trade == "buy": 
                    self.sell_all() 
                order = self.create_order(
                    Asset(symbol=self.symbol, asset_type=ASSET_TYPE),
                    # self.symbol,
                    quantity, 
                    "sell", 
                    type="bracket", 
                    take_profit_price=last_price*.8, 
                    stop_loss_price=last_price*1.05
                )
                self.submit_order(order) 
                self.last_trade = "sell"

    def list_alpaca_symbols(self):
        # Get all active assets
        active_assets = self.broker.api.get_all_assets()
        for asset in active_assets:
            print(f'{asset.symbol}: {asset.name}')

    def get_opening_hours(self):
        # Check if the market is open now.
        clock = self.api.get_clock()
        print('The market is {}'.format('open.' if clock.is_open else 'closed.'))

        # Check when the market was open on Dec. 1, 2018
        date = '2018-12-01'
        calendar = self.api.get_calendar(start=date, end=date)[0]
        print('The market opened at {} and closed at {} on {}.'.format(
            calendar.open,
            calendar.close,
            date))

# start_date = datetime(2020,1,1)
# end_date = datetime(2023,12,31)
broker = Alpaca(ALPACA_CREDS)

strategy = MLTrader(name='mlstrat', broker=broker,
                    parameters={"symbol": SYMBOL,
                                "cash_at_risk": .5})
# strategy.backtest(
#     YahooDataBacktesting,
#     start_date,
#     end_date,
#     parameters={"symbol": SYMBOL, "cash_at_risk": .5}
# )

trader = Trader()
trader.add_strategy(strategy)
trader.run_all()
