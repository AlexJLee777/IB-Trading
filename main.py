from ib_insync import *
from ib_insync.order import LimitOrder
import datetime
import pytz

tz = pytz.timezone('US/Eastern')
now = datetime.datetime.now(tz)

ib = IB()
ib.connect('127.0.0.1', 7497, clientId=1)

contractDate = now.strftime('%Y%m%d')

cds = ib.reqContractDetails(Option('SPX', contractDate, right="P", exchange='SMART'))

buyTicker = sellTicker = ib.reqMktData(cds[0].contract)
buyContractDetail = sellContractDetail = None
for idx in range(1, len(cds)):
    ticker = ib.reqMktData(cds[idx].contract)
    while ticker.modelGreeks is None or buyTicker.modelGreeks is None:
        ib.sleep()

    if (buyTicker.modelGreeks.delta + 0.05) * (ticker.modelGreeks.delta + 0.05) < 0 and abs(buyTicker.modelGreeks.delta + 0.05) > abs(ticker.modelGreeks.delta + 0.05):
        buyTicker = ticker
        buyContractDetail = cds[idx]

    if (sellTicker.modelGreeks.delta + 0.5) * (ticker.modelGreeks.delta + 0.5) < 0 and abs(sellTicker.modelGreeks.delta + 0.5) > abs(ticker.modelGreeks.delta + 0.5):
        sellTicker = ticker
        sellContractDetail = cds[idx]

print("Buy: ", buyTicker, "\n")
print("Details: ", buyContractDetail, "\n\n")
print("Sell: ", sellTicker, "\n")
print("Details: ", sellContractDetail, "\n\n")

buyLeg = buyTicker.contract
sellLeg = sellTicker.contract

ib.qualifyContracts(buyLeg)
ib.qualifyContracts(sellLeg)

contract = Option(symbol='SPX', lastTradeDateOrContractMonth=contractDate, right='P', exchange='SMART', multiplier=100, currency='USD')
contract = Contract()
contract.symbol = 'SPX'
contract.secType = 'BAG'
contract.lastTradeDateOrContractMonth = contractDate
contract.right = 'P'
contract.exchange = 'SMART'
contract.currency = 'USD'
contract.comboLegs = [
    ComboLeg(conId=buyLeg.conId, ratio=1, action='BUY', exchange='SMART'),
    ComboLeg(conId=sellLeg.conId, ratio=1, action='SELL', exchange='SMART')
]

order = Order()
order.action = 'BUY'
order.orderType = 'LMT'
order.totalQuantity = 1
order.multiplier = 1
minPriceIncrement = buyContractDetail.minTick
minPrice = buyContractDetail.priceMagnifier * minPriceIncrement
order.lmtPrice = round((buyTicker.bid + buyTicker.ask - sellTicker.bid - sellTicker.ask) / 2.0 / minPrice) * minPrice
order.account = ib.managedAccounts()[0]

trade = ib.placeOrder(contract, order)
ib.sleep(5)
print("Open: \n", trade, "\n\n")


soldPrice = (sellTicker.bid + sellTicker.ask) / 2.0
profitTarget = soldPrice * 0.2
stopPrice = (soldPrice - (buyTicker.bid + buyTicker.ask) / 2.0) * 1.2
flg = False
while True:
    spreadPrice = midPrice = (sellTicker.bid + sellTicker.ask - buyTicker.bid - buyTicker.ask) / 2.0
    if spreadPrice * 1.2 < stopPrice:
        print(f"Spread Price({spreadPrice}) * 1.2 < Stop Price({stopPrice})")
        stopPrice = spreadPrice * 1.2

    print(f"Spread Price: {spreadPrice}, Stop Price: {stopPrice}, Profit Target: {profitTarget}")
    # midPrice = (sellTicker.bid + sellTicker.ask - buyTicker.bid + buyTicker.ask) / 4.0

    if midPrice > stopPrice:
        print(f"Mid Price({midPrice}) > Stop Price({stopPrice})")
        if flg:
            break
        else:
            flg = True

    if spreadPrice <= profitTarget:
        print(f"Spread Price({spreadPrice}) is lower than Sold Price * 0.2({profitTarget})")
        break
    
    print("\n")
    
    ib.sleep(60)

closingOrder = Order()
closingOrder.action = 'SELL'
closingOrder.orderType = 'LMT'
closingOrder.totalQuantity = 1
closingOrder.multiplier = 1
minPriceIncrement = sellContractDetail.minTick
minPrice = sellContractDetail.priceMagnifier * minPriceIncrement
closingOrder.lmtPrice = round((buyTicker.bid + buyTicker.ask - sellTicker.bid - sellTicker.ask) / 2.0 / minPrice) * minPrice
closingOrder.account = ib.managedAccounts()[0]

trade = ib.placeOrder(contract, closingOrder)
ib.sleep(5)
print("Close: \n", trade, "\n\n")

ib.disconnect()
