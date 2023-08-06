import numpy as np
import yfinance as yf
import datetime
import copy
import os
from email_functions import send_email

def run_portfolio_alert_algorithm(target_portfolio_file, portfolio_file, email_details_file):
    tolerance, position_type, portfolio_target_weights, minimal_weight_positions = read_target_portfolio(
        target_portfolio_file)

    target_portfolio_string = define_target_portfolio_string(portfolio_target_weights, position_type)

    check_portfolio_target_weights(portfolio_target_weights, position_type)

    date, portfolio, portfolio_history = read_portfolio(portfolio_file)

    portfolio_weights, portfolio_sum, portfolio_reb_weights, portfolio_reb_sum = calculate_portfolio_weights(
        portfolio, position_type)

    portfolio_status_string = define_portfolio_status_string(portfolio, position_type, portfolio_weights,
                                                             portfolio_reb_weights, portfolio_sum)

    # update the portfolio file with the price movement since the last update if needed
    last_date = date
    date_today = datetime.date.today().strftime('%d-%m-%Y')

    if date_today != last_date:

        stock_prices_last, stock_prices_today = get_stock_prices(last_date, portfolio, portfolio_target_weights)

        update_portfolio_file(portfolio_file, portfolio, portfolio_history, date_today, stock_prices_last,
                              stock_prices_today, portfolio_weights)

        portfolio_new, deltas_dict, total_sell_positions = sell_irrelevant_positions(portfolio,
                                                                                     portfolio_target_weights)

        portfolio_new, portfolio_target_weights = complete_missing_keys(portfolio_new, portfolio_target_weights)

        portfolio_weights, portfolio_sum, portfolio_reb_weights, portfolio_reb_sum = calculate_portfolio_weights(
            portfolio_new, position_type)

        rebalance_needed = check_if_rebalance_needed(portfolio_weights, portfolio_reb_weights, portfolio_target_weights,
                                                     tolerance, position_type)

        if rebalance_needed == True:
            portfolio_new2, deltas_dict = rebalance_portfolio(portfolio_new, portfolio_sum, minimal_weight_positions,
                                                              portfolio_target_weights, deltas_dict, position_type)

            portfolio_new3, sell_integer_stocks_dict, sell_integer_value_dict, buy_integer_stocks_dict, \
            buy_integer_value_dict = rebalance_with_integer_operations(portfolio, portfolio_new, deltas_dict,
                                                                       stock_prices_today)

            portfolio_weights, portfolio_sum, portfolio_reb_weights, portfolio_reb_sum = calculate_portfolio_weights(
                portfolio_new3, position_type)

            portfolio_status_post_string = define_portfolio_status_post_string(portfolio_new3, position_type,
                                                                               portfolio_weights, portfolio_reb_weights,
                                                                               portfolio_sum)

            instructions = compose_rebalancing_instructions(sell_integer_stocks_dict, sell_integer_value_dict,
                                                            total_sell_positions,
                                                            buy_integer_stocks_dict, buy_integer_value_dict)

            subject_line, message_lines = compose_email(date_today, portfolio_status_string, target_portfolio_string,
                                                        instructions,
                                                        portfolio_status_post_string)

            if email_details_file is None:
                print(subject_line)
                for line in message_lines:
                    print(line)
            else:
                send_email(subject_line, message_lines, email_details_file=email_details_file)

    return

def read_target_portfolio(target_portfolio_file='target_portfolio.txt'):
    # read and interpret target_portfolio file
    with open(os.path.dirname(__file__) + '/' + target_portfolio_file) as f:
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

    return tolerance, position_type, portfolio_target_weights, minimal_weight_positions

def define_target_portfolio_string(portfolio_target_weights, position_type):
    target_portfolio_string = ['=== Portfolio Target ===']
    for ticker in portfolio_target_weights.keys():
        target_portfolio_string += [ticker + ': ' + str(portfolio_target_weights[ticker])
                                    + '% (' + position_type[ticker] + ')']
    return target_portfolio_string

def check_portfolio_target_weights(portfolio_target_weights, position_type):
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
    return
#
def read_portfolio(portfolio_file='portfolio.txt'):
    # read portfolio file which records the portfolio history
    with open(os.path.dirname(__file__) + '/' + portfolio_file) as f:
        lines = f.readlines()
    portfolio_history = {}
    for line in lines:
        if line != '\n':
            date = line.split(':')[0]
            elements = line.split(':')[1].split('\n')[0].strip().split(' ')

            if '(' in line or ')' in line: # skip the portfolio fraction information
                tickers = elements[0::3]
                values_raw = elements[1::3]
            else:
                tickers = elements[0::2]
                values_raw = elements[1::2]
            values = [v.split('$')[-1] for v in values_raw]

            portfolio = {}
            portfolio_sum = 0
            for ticker, value in zip(tickers, values):
                if ticker != 'total':
                    portfolio[ticker] = float(value)
                    portfolio_sum += portfolio[ticker]
            portfolio_history[date] = portfolio
    return date, portfolio, portfolio_history

def calculate_portfolio_weights(portfolio, position_type, verbosity=False):
     # normalize the most recent portfolio values, for the total portfolio or just the rebalanced portion
    portfolio_sum = sum([portfolio[ticker] for ticker in portfolio.keys()])
    portfolio_weights = {}
    for ticker in portfolio.keys():
        portfolio_weights[ticker] = portfolio[ticker] / portfolio_sum * 100

    if verbosity == True:
        print('portfolio_weights', portfolio_weights)

    try:
        portfolio_reb_sum = sum([portfolio[ticker] for ticker in portfolio.keys()
                                 if position_type[ticker] == 'rebalanced'])
        portfolio_reb_weights = {}
        for ticker in portfolio.keys():
            if position_type[ticker] == 'rebalanced':
                portfolio_reb_weights[ticker] = portfolio[ticker] / portfolio_reb_sum * 100
    except:
        portfolio_reb_sum, portfolio_reb_weights = None, None

    if verbosity == True:
        print('portfolio_reb_weights', portfolio_reb_weights)

    return portfolio_weights, portfolio_sum, portfolio_reb_weights, portfolio_reb_sum

def define_portfolio_status_string(portfolio, position_type, portfolio_weights, portfolio_reb_weights, portfolio_sum):
    portfolio_status_string = ['=== Portfolio Status ===']
    for ticker in portfolio.keys():
        curr_ticker_status = ticker + ': $' + '{:.2f}'.format(portfolio[ticker]) \
                             + ' (' + '{:.2f}'.format(portfolio_weights[ticker]) + '%)'
        if position_type[ticker] == 'rebalanced':
            curr_ticker_status += ' [' + '{:.2f}'.format(portfolio_reb_weights[ticker]) + '% reb]'
        portfolio_status_string += [curr_ticker_status]
    portfolio_status_string += ['*** TOTAL: $' + '{:.2f}'.format(portfolio_sum)]
    return portfolio_status_string

def get_stock_prices(last_date, portfolio, portfolio_target_weights):
    # download stock prices for the portfolio positions, today and in the last portfolio update
    date_last_obj = datetime.datetime.strptime(last_date, '%d-%m-%Y')
    date_last_obj_minus5days = date_last_obj - datetime.timedelta(days=5)
    stock_prices_last = {}
    stock_prices_today = {}
    for ticker in portfolio.keys():
        if ticker != 'cash':
            yf_ticker = yf.Ticker(ticker)
            try:
                stock_prices_last[ticker] = yf_ticker.history(start=date_last_obj_minus5days,
                                                              end=date_last_obj)['Close'].values[-1]
            except:
                raise ValueError('problem with loading ' + ticker + ' stock date for ' + last_date)
            stock_prices_today[ticker] = yf_ticker.history(period='1d')['Close'].values[0]

    # download stock prices for positions not yet in the portfolio
    for ticker in portfolio_target_weights.keys():
        if ticker != 'cash' and ticker not in stock_prices_today.keys():
            yf_ticker = yf.Ticker(ticker)
            stock_prices_today[ticker] = yf_ticker.history(period='1d')['Close'].values[0]

    return stock_prices_last, stock_prices_today

def update_portfolio_file(portfolio_file, portfolio, portfolio_history, date_today, stock_prices_last,
                          stock_prices_today, portfolio_weights):
    # update the portfolio (and log) with the price movement
    portfolio_last = portfolio
    portfolio = {}
    portfolio_sum = 0
    with open(os.path.dirname(__file__) + '/' + portfolio_file, 'a') as f:
        updated_portfolio_line = '\n' + date_today + ': '
        for ticker in portfolio_last.keys():
            if ticker != 'cash':
                portfolio[ticker] = portfolio_last[ticker] * stock_prices_today[ticker] / stock_prices_last[ticker]
            else:
                # cash does not change
                portfolio[ticker] = portfolio_last[ticker]
            updated_portfolio_line += ticker + ' $' + '{:.2f}'.format(portfolio[ticker]) \
                                      + ' (' + '{:.2f}'.format(portfolio_weights[ticker]) + '%) '
            portfolio_sum += portfolio[ticker]
        updated_portfolio_line += 'total $' + '{:.2f}'.format(portfolio_sum) + ' '
        portfolio_history[date_today] = portfolio
        f.write(updated_portfolio_line)
    return portfolio_history


def sell_irrelevant_positions(portfolio, portfolio_target_weights):
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
    if abs(sum([deltas_dict[ticker] for ticker in deltas_dict.keys()])) > 1e-10:
        raise ValueError('deltas_dict does not sum to zero.')

    return portfolio_new, deltas_dict, total_sell_positions


def complete_missing_keys(portfolio_new, portfolio_target_weights):
    # add positions that exist (or not) in the current portfolio or target portfolio
    for ticker in portfolio_target_weights.keys():
        if ticker not in portfolio_new.keys():
            portfolio_new[ticker] = 0
    for ticker in portfolio_new.keys():
        if ticker not in portfolio_target_weights.keys():
            portfolio_target_weights[ticker] = 0
    return portfolio_new, portfolio_target_weights


def check_if_rebalance_needed(portfolio_weights, portfolio_reb_weights, portfolio_target_weights, tolerance,
                              position_type):
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
    return rebalance_needed


def rebalance_portfolio(portfolio_new, portfolio_sum, minimal_weight_positions, portfolio_target_weights, deltas_dict, position_type):
    # buy the minimal_weights positions if necessary
    delta_minimal_weights_total = 0
    portfolio_new2 = copy.deepcopy(portfolio_new)
    for ticker in minimal_weight_positions:
        delta = portfolio_sum * (portfolio_target_weights[ticker] - portfolio_new[ticker]) / 100.0
        if delta > 0:
            deltas_dict[ticker] = delta
            portfolio_new2[ticker] += delta
            delta_minimal_weights_total += delta

    # if the minimal_weights portion increased, need to proportional reduce the rebalanced portion
    portfolio_weights, portfolio_sum, portfolio_reb_weights, portfolio_reb_sum = calculate_portfolio_weights(
        portfolio_new2, position_type)

    reduce_rebalanced_factor = (portfolio_reb_sum - delta_minimal_weights_total) / portfolio_reb_sum
    delta_rebalanced_total = 0
    # for ticker in rebalanced_positions:
    for ticker in portfolio_new2.keys():
        if position_type[ticker] == 'rebalanced':
            delta = - (1 - reduce_rebalanced_factor) * portfolio_new2[ticker]
            if ticker not in deltas_dict.keys():
                deltas_dict[ticker] = 0  # initialize
            deltas_dict[ticker] += delta
            portfolio_new2[ticker] += delta
            delta_rebalanced_total += delta

    # the left-over from the minimal_weights positions is the rebalanced portion of the portfolio
    portfolio_weights, portfolio_sum, portfolio_reb_weights, portfolio_reb_sum = calculate_portfolio_weights(
        portfolio_new2, position_type)

    # buy/sell the rebalanced positions
    for ticker in portfolio_new2.keys():
        if position_type[ticker] == 'rebalanced':
            # for ticker in rebalanced_positions:

            if ticker not in portfolio_reb_weights.keys():
                portfolio_reb_weights[ticker] = 0

            delta = portfolio_reb_sum * (portfolio_target_weights[ticker] - portfolio_reb_weights[ticker]) / 100.0
            deltas_dict[ticker] += delta
            portfolio_new2[ticker] += delta

    # check deltas_dict sums to zero
    if abs(sum([deltas_dict[ticker] for ticker in deltas_dict.keys()])) > 1e-10:
        raise ValueError('deltas_dict does not sum to zero.')

    return portfolio_new2, deltas_dict

def rebalance_with_integer_operations(portfolio, portfolio_new, deltas_dict, stock_prices_today):
    # translate deltas_dict into integer stock amounts
    sell_integer_stocks_dict = {}
    sell_integer_value_dict = {}
    portfolio_new3 = copy.deepcopy(portfolio)
    for ticker in deltas_dict.keys():

        if ticker not in portfolio_new3:  # initialize
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


    return portfolio_new3, sell_integer_stocks_dict, sell_integer_value_dict, buy_integer_stocks_dict, \
           buy_integer_value_dict


def define_portfolio_status_post_string(portfolio_new3, position_type, portfolio_weights, portfolio_reb_weights, portfolio_sum):
    portfolio_status_post_string = ['=== Portfolio Post Rebalancing (should approximately be) ===']
    for ticker in portfolio_new3.keys():
        if portfolio_weights[ticker] > 0.1:
            curr_ticker_status = ticker + ': $' + '{:.2f}'.format(portfolio_new3[ticker]) \
                                 + ' (' + '{:.2f}'.format(portfolio_weights[ticker]) + '%)'
            if position_type[ticker] == 'rebalanced':
                curr_ticker_status += ' [' + '{:.2f}'.format(portfolio_reb_weights[ticker]) + '% reb]'
            portfolio_status_post_string += [curr_ticker_status]
    portfolio_status_post_string += ['*** TOTAL: $' + '{:.2f}'.format(portfolio_sum)]
    return portfolio_status_post_string


def compose_rebalancing_instructions(sell_integer_stocks_dict, sell_integer_value_dict, total_sell_positions,
                                     buy_integer_stocks_dict, buy_integer_value_dict):
    # print the instructions
    instructions = ['=== Rabalancing Instructions ===']

    if len(sell_integer_stocks_dict) > 0:
        instructions += ['Sell list:']
        for ticker in sell_integer_stocks_dict.keys():
            if ticker != 'cash':
                instruction = ticker + ': ' + str(sell_integer_stocks_dict[ticker]) \
                              + ' stocks (worth $' + '{:.2f}'.format(sell_integer_value_dict[ticker]) + ')'
                if ticker in total_sell_positions:
                    instruction += ' (liquidate entire position)'
                instructions += [instruction]

    if len(buy_integer_stocks_dict) > 0:
        instructions += ['Buy list:']
        for ticker in buy_integer_stocks_dict.keys():
            if ticker != 'cash':
                instructions += [ticker + ': ' + str(buy_integer_stocks_dict[ticker])
                                 + ' stocks (worth $' + '{:.2f}'.format(buy_integer_value_dict[ticker]) + ')']

    return instructions

def compose_email(date_today, portfolio_status_string, target_portfolio_string, instructions,
                  portfolio_status_post_string):
    # add a section about the current stock prices and the state of the portfolio before and after the rebalancing
    subject_line = 'Portfolio Alert! (' + date_today + ')'
    message_lines = portfolio_status_string + [''] + target_portfolio_string + [''] \
                    + instructions + [''] + portfolio_status_post_string
    return subject_line, message_lines
