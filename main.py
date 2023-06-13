from ib_insync import *
import datetime

# Connect to IBKR
ib = IB()
ib.connect('127.0.0.1', 4002, clientId=1)

# Define the contract for the options
contract = Option('SPX', '', '', 'SMART', right='P', exchange='SMART')

# Define the order parameters
sell_order = Order(action='SELL', totalQuantity=1, orderType='MKT')
buy_order = Order(action='BUY', totalQuantity=1, orderType='MKT')

# Define the target and stop loss percentages
target_pct = 0.8
stop_loss_pct = 0.2

# Define the allocation percentage
allocation_pct = 0.1

# Define the maximum number of positions and contracts
max_positions = 1
max_contracts = 1

# Define the delta values for selecting the legs
sell_delta = 0.5
buy_delta = 0.05

# Define the trailing stop loss amount
trailing_stop_loss_pct = 0.2

# Get the current time
now = datetime.datetime.now()

# Check if it is time to enter the market
if now.hour == 15 and now.minute == 0:
    # Check if there are already open positions
    open_positions = ib.positions()
    if len(open_positions) < max_positions:
        # Check if there are already open contracts
        open_contracts = ib.positions(contract)
        if len(open_contracts) < max_contracts:
            # Calculate the allocation amount based on available funds
            account_summary = ib.accountSummary()
            available_funds = float(next((item for item in account_summary if item.tag == 'AvailableFunds'), None).value)
            allocation_amount = available_funds * allocation_pct

            # Get the current option chain and select the legs by delta
            option_chain = ib.reqSecDefOptParams(contract.symbol, '', contract.secType, contract.conId)
            put_chain = [c for c in option_chain if c.right == 'P']
            strikes = sorted(set(c.strike for c in put_chain))
            atm_strike = strikes[len(strikes) // 2]
            atm_options = [c for c in put_chain if c.strike == atm_strike]
            sell_option = sorted(atm_options, key=lambda c: abs(c.delta - sell_delta))[0]
            buy_option = sorted(atm_options, key=lambda c: abs(c.delta - buy_delta))[0]

            # Calculate the order prices based on the option prices and allocation amount
            sell_price = sell_option.ask * sell_option.multiplier * sell_option.conId
            buy_price = buy_option.bid * buy_option.multiplier * buy_option.conId
            order_total = sell_price - buy_price
            order_quantity = int(allocation_amount / order_total)

            # Place the order
            sell_order.totalQuantity = order_quantity
            buy_order.totalQuantity = order_quantity
            sell_order.orderRef = 'Sell Put Spread'
            buy_order.orderRef = 'Buy Put Spread'
            trade = ib.placeOrder(contract, sell_order)
            ib.placeOrder(contract, buy_order)

            # Monitor the price of the spread each minute and use a trailing stop to exit
            while True:
                # Wait for a minute
                ib.sleep(60)

                # Check if the trade is still open
                if trade.orderStatus.status != 'Filled':
                    break

                # Get the current price of the spread and calculate the trailing stop loss amount
                sell_price = ib.reqMktData(sell_option.contract, '', False, False).marketPrice()
                buy_price = ib.reqMktData(buy_option.contract, '', False, False).marketPrice()
                current_price = sell_price - buy_price
                stop_loss_amount = current_price * trailing_stop_loss_pct

                # Check if the current price has reached the profit target or trailing stop loss level
                if current_price >= order_total * target_pct or current_price <= order_total - stop_loss_amount:
                    # Place a market order to close the position and exit the loop
                    close_order = Order(action='BUY', totalQuantity=order_quantity * 2, orderType='MKT')
                    close_order.orderRef = 'Close Put Spread'
                    ib.placeOrder(contract, close_order)
                    break

    # Disconnect from IBKR after executing the strategy for the day
    ib.disconnect()