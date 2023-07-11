

def calculate_portfolio_weights(portfolio, position_type, verbosity=True):
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


