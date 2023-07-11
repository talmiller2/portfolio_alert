
import numpy as np
import yfinance as yf
import datetime
import copy
from portfolio_functions import calculate_portfolio_weights

# read and interpret target_portfolio file
# target_portfolio_file = 'target_portfolio.txt'
# target_portfolio_file = 'target_portfolio2.txt'
target_portfolio_file = 'target_portfolio3.txt'
with open(target_portfolio_file) as f:
    lines = f.readlines()
portfolio_target_weights = {}
position_type = {}
minimal_weight_positions = []
rebalanced_positions = []
tolerance = None
for line in lines:
    if 'tolerance' not in line:
        elements = line.split('\n')[0].split(' ')
        ticker = elements[0]
        if elements[1][0] == '>':
            # treat case of positions that is required to have a minimal weighting
            percents = float(elements[1].split('>')[1].split('%')[0])
            position_type[ticker] = 'minimal_weight'
            minimal_weight_positions += [ticker]

            # cash cannot be used as a minimal_weight position
            if ticker == 'cash':
                raise ValueError('cash cannot be used as a minimal_weight position')
        else:
            percents = float(elements[1].split('%')[0])
            position_type[ticker] = 'rebalanced'
            rebalanced_positions += [ticker]
        portfolio_target_weights[ticker] = float(percents)
    else:
        tolerance = float(line.split('\n')[0].split(' ')[1].split('%')[0])

# check a tolerance percent was defined
if tolerance is None:
    raise ValueError('tolerance was not defined')

# add cash to positions_types is not defined
if 'cash' not in position_type.keys():
    position_type['cash'] = 'rebalanced'

target_portfolio_string = '=== Portfolio Target ===\n'
for ticker in portfolio_target_weights.keys():
    target_portfolio_string += ticker + ': ' + str(portfolio_target_weights[ticker]) + '% (' + position_type[ticker] + ')\n'

# check that all percentages of minimal_weight positions are less than 100%
percent_counter_minimal_weight = 0
for ticker in portfolio_target_weights.keys():
    if position_type[ticker] == 'minimal_weight':
        percent_counter_minimal_weight += portfolio_target_weights[ticker]
if percent_counter_minimal_weight > 100:
    raise ValueError('positions of "minimal_weight" type are weighed > 100%')

# check that all percentages of rebalanced positions add up to 100%
percent_counter_rebalanced = 0
for ticker in portfolio_target_weights.keys():
    if position_type[ticker] == 'rebalanced':
        percent_counter_rebalanced += portfolio_target_weights[ticker]
if percent_counter_rebalanced != 100:
    raise ValueError('positions of "rebalanced" type do not add to 100%')

# read portfolio file which records the portfolio history
portfolio_file = 'portfolio.txt'
with open(portfolio_file) as f:
    lines = f.readlines()
portfolio_history = {}
for line in lines:
    if line != '\n':
        date = line.split(':')[0]
        elements = line.split(':')[1].split('\n')[0].strip().split(' ')
        tickers = elements[0::2]
        values = elements[1::2]
        portfolio = {}
        portfolio_sum = 0
        for ticker, value in zip(tickers, values):
            portfolio[ticker] = float(value)
            portfolio_sum += portfolio[ticker]
        portfolio_history[date] = portfolio

print(0)
portfolio_weights, portfolio_sum, portfolio_reb_weights, portfolio_reb_sum = calculate_portfolio_weights(
    portfolio, position_type)

portfolio_status_string = '=== Portfolio Status ===\n'
for ticker in portfolio.keys():
    portfolio_status_string += ticker + ': $' + '{:.2f}'.format(portfolio[ticker]) \
                               + ' (' + '{:.2f}'.format(portfolio_weights[ticker]) + '%)\n'
portfolio_status_string += '*** TOTAL: $' + '{:.2f}'.format(portfolio_sum) + '\n'

# # list of tickers except cash
# tickers_portfolio = list(portfolio)
# if 'cash' in tickers_portfolio:
#     tickers_portfolio.remove('cash')

# update the portfolio file with the price movement since the last update if needed
last_date = date
date_today = datetime.date.today().strftime('%d-%m-%Y')

if date_today != last_date:
# if True:
    date_last_obj = datetime.datetime.strptime(date, '%d-%m-%Y')
    date_last_obj_minus5days = date_last_obj - datetime.timedelta(days=5)

    stock_prices_last = {}
    stock_prices_today = {}
    # for ticker in tickers_portfolio:
    for ticker in portfolio.keys():
        if ticker != 'cash':
            yf_ticker = yf.Ticker(ticker)
            try:
                stock_prices_last[ticker] = yf_ticker.history(start=date_last_obj_minus5days,
                                                              end=date_last_obj)['Close'].values[-1]
            except:
                raise ValueError('problem with loading ' + ticker + ' stock date for ' + last_date)
            stock_prices_today[ticker] = yf_ticker.history(period='1d')['Close'].values[0]

    # update the portfolio (and log) with the price movement
    portfolio_last = portfolio
    portfolio = {}
    portfolio_sum = 0
    with open(portfolio_file, 'a') as f:
        updated_portfolio_line = '\n' + date_today + ': '
        for ticker in portfolio_last.keys():
            if ticker != 'cash':
                portfolio[ticker] = portfolio_last[ticker] * stock_prices_today[ticker] / stock_prices_last[ticker]
                updated_portfolio_line += ticker + ' ' + '{:.2f}'.format(portfolio[ticker]) + ' '
            else:
                # cash does not change
                portfolio[ticker] = portfolio_last[ticker]
                updated_portfolio_line += ticker + ' ' + '{:.2f}'.format(portfolio[ticker]) + ' '
            portfolio_sum += portfolio[ticker]
        portfolio_history[date] = portfolio
        f.write(updated_portfolio_line)

    # if the current portfolio contains things that do not exist in the target, immediately sell them and proceed
    deltas_dict = {}
    total_sell_positions = []
    portfolio_new = {}
    portfolio_new['cash'] = 0
    deltas_dict['cash'] = 0
    for ticker in portfolio.keys():
        if ticker == 'cash':
            portfolio_new['cash'] += portfolio[ticker]
        elif ticker in portfolio_target_weights.keys():
        # if   portfolio_target_weights.keys():
            portfolio_new[ticker] = portfolio[ticker]
        else:
            portfolio_new['cash'] += portfolio[ticker]
            deltas_dict['cash'] += portfolio[ticker]
            deltas_dict[ticker] = -portfolio[ticker]
            total_sell_positions += [ticker]

    # check deltas_dict sums to zero
    if sum([deltas_dict[ticker] for ticker in deltas_dict.keys()]) != 0:
        raise ValueError('deltas_dict does not sum to zero.')

    # load the stock prices for all needed stocks
    for ticker in portfolio_target_weights.keys():
        if ticker != 'cash' and ticker not in stock_prices_today.keys():
            yf_ticker = yf.Ticker(ticker)
            stock_prices_today[ticker] = yf_ticker.history(period='1d')['Close'].values[0]

    # add positions that exist (or not) in the current portfolio or target portfolio
    for ticker in portfolio_target_weights.keys():
        if ticker not in portfolio_new.keys():
            portfolio_new[ticker] = 0
    for ticker in portfolio_new.keys():
        if ticker not in portfolio_target_weights.keys():
            portfolio_target_weights[ticker] = 0


    print(1)
    portfolio_weights, portfolio_sum, portfolio_reb_weights, portfolio_reb_sum = calculate_portfolio_weights(
        portfolio_new, position_type)

    # check if tolerance in exceeded (treat case of minimal_weight as well)
    rebalance_needed = False
    for ticker in portfolio_target_weights.keys():
        if position_type[ticker] == 'minimal_weight':
            if portfolio_weights[ticker] <= portfolio_target_weights[ticker] - tolerance:
                rebalance_needed = True
                break
        elif position_type[ticker] == 'rebalanced':
            if abs(portfolio_reb_weights[ticker] - portfolio_target_weights[ticker]) >= tolerance:
                rebalance_needed = True
                break
        else:
            raise ValueError('invalid position_type', position_type[ticker], 'for ticker', ticker)

    # portfolio_new2 = {}
    if rebalance_needed == True:
        print('rebalance_needed')

        # buy the minimal_weights positions if necessary
        delta_minimal_weights_total = 0
        portfolio_new2 = copy.deepcopy(portfolio_new)
        for ticker in minimal_weight_positions:
            delta = portfolio_sum * (portfolio_target_weights[ticker] - portfolio_weights[ticker]) / 100.0
            if delta > 0:
                deltas_dict[ticker] = delta
                portfolio_new2[ticker] += delta
                delta_minimal_weights_total += delta

        # if the minimal_weights portion increased, need to proportional reduce the rebalanced portion
        print(2)
        portfolio_weights, portfolio_sum, portfolio_reb_weights, portfolio_reb_sum = calculate_portfolio_weights(
            portfolio_new2, position_type)

        reduce_rebalanced_factor = (portfolio_reb_sum - delta_minimal_weights_total) / portfolio_reb_sum
        delta_rebalanced_total = 0
        # for ticker in rebalanced_positions:
        for ticker in portfolio_new2.keys():
            if position_type[ticker] == 'rebalanced':
                delta = - (1 - reduce_rebalanced_factor) * portfolio_new2[ticker]
                if ticker not in deltas_dict.keys():
                    deltas_dict[ticker] = 0 # initialize
                deltas_dict[ticker] += delta
                portfolio_new2[ticker] += delta
                delta_rebalanced_total += delta

        # the left-over from the minimal_weights positions is the rebalanced portion of the portfolio
        print(3)
        portfolio_weights, portfolio_sum, portfolio_reb_weights, portfolio_reb_sum = calculate_portfolio_weights(
            portfolio_new2, position_type)

        # buy/sell the rebalanced positions
        for ticker in portfolio_new2.keys():
            if position_type[ticker] == 'rebalanced':
                # for ticker in rebalanced_positions:

                if ticker not in portfolio_reb_weights.keys(): #TODO do this elsewhere during refactoring
                    portfolio_reb_weights[ticker] = 0

                delta = portfolio_reb_sum * (portfolio_target_weights[ticker] - portfolio_reb_weights[ticker]) / 100.0
                deltas_dict[ticker] += delta
                portfolio_new2[ticker] += delta

        # check deltas_dict sums to zero
        if sum([deltas_dict[ticker] for ticker in deltas_dict.keys()]) != 0:
            raise ValueError('deltas_dict does not sum to zero.')


        print(4)
        portfolio_weights, portfolio_sum, portfolio_reb_weights, portfolio_reb_sum = calculate_portfolio_weights(
            portfolio_new2, position_type)


        # translate deltas_dict into integer stock amounts
        sell_integer_stocks_dict = {}
        sell_integer_value_dict = {}
        # portfolio_new3 = copy.deepcopy(portfolio_new)
        portfolio_new3 = copy.deepcopy(portfolio)
        for ticker in deltas_dict.keys():

            if ticker not in portfolio_new3: # initialize
                portfolio_new3[ticker] = 0


            if ticker != 'cash' and deltas_dict[ticker] < 0:
                integer_num_stocks = np.round(deltas_dict[ticker] / stock_prices_today[ticker])
                sell_integer_stocks_dict[ticker] = int(integer_num_stocks)
                sell_integer_value_dict[ticker] = integer_num_stocks * stock_prices_today[ticker]
                portfolio_new3[ticker] += sell_integer_value_dict[ticker]
            elif ticker == 'cash' and deltas_dict[ticker] < 0:
                portfolio_new3[ticker] += deltas_dict[ticker]


        buy_integer_stocks_dict = {}
        buy_integer_value_dict = {}
        for ticker in deltas_dict.keys():
            if ticker in portfolio_new:

                if ticker != 'cash' and deltas_dict[ticker] > 0:
                    integer_num_stocks = np.round(deltas_dict[ticker] / stock_prices_today[ticker])
                    buy_integer_stocks_dict[ticker] = int(integer_num_stocks)
                    buy_integer_value_dict[ticker] = integer_num_stocks * stock_prices_today[ticker]
                    portfolio_new3[ticker] += buy_integer_value_dict[ticker]
                elif ticker == 'cash' and deltas_dict[ticker] > 0:
                    portfolio_new3[ticker] += deltas_dict[ticker]

        print(5)
        portfolio_weights, portfolio_sum, portfolio_reb_weights, portfolio_reb_sum = calculate_portfolio_weights(
            portfolio_new3, position_type)

        portfolio_status_post_string = '=== Portfolio Post Rebalancing (should approximately be) ===\n'
        for ticker in portfolio_new3.keys():
            if portfolio_weights[ticker] > 0.1:
                portfolio_status_post_string += ticker + ': $' + '{:.2f}'.format(portfolio_new3[ticker]) \
                                                + ' (' + '{:.2f}'.format(portfolio_weights[ticker]) + '%)\n'
        portfolio_status_post_string += '*** TOTAL: $' + '{:.2f}'.format(portfolio_sum)

        # print the instructions
        instructions = '=== Rabalancing Instructions ===\n'
        instructions += 'Sell list:\n'
        for ticker in sell_integer_stocks_dict.keys():
            if ticker != 'cash':
                instructions += ticker + ': ' + str(sell_integer_stocks_dict[ticker]) \
                                + ' stocks (worth $' + '{:.2f}'.format(sell_integer_value_dict[ticker]) + ')'
                if ticker in total_sell_positions:
                    instructions += ' (liquidate entire position)'
                instructions += '\n'
        instructions += 'Buy list:\n'
        for ticker in buy_integer_stocks_dict.keys():
            if ticker != 'cash':
                instructions += ticker + ': ' + str(buy_integer_stocks_dict[ticker]) \
                                + ' stocks (worth $' + '{:.2f}'.format(buy_integer_value_dict[ticker]) + ')'
                instructions += '\n'

        # add a section about the current stock prices and the state of the portfolio before and after the rebalancing
        subject_line = 'Subject: Portfolio Alert! (' + date_today + ')'
        email_string = subject_line + '\n\n'
        email_string += portfolio_status_string + '\n'
        email_string += target_portfolio_string + '\n'
        email_string += instructions + '\n'
        email_string += portfolio_status_post_string

        instructions_file = 'instructions.txt'
        with open(instructions_file, 'w') as f:
            # f.write(instructions)
            f.write(email_string)

        # send_mail()

