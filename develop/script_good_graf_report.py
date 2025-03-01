import argparse
import os
import yfinance as yf
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from datetime import datetime, timedelta

def load_data(ticker, start_date, end_date):
    cache_file = f"{ticker}_{start_date}_{end_date}.csv"
    
    if os.path.exists(cache_file):
        data = pd.read_csv(cache_file)
        data['Date'] = pd.to_datetime(data['Date'])
    else:
        extended_end_date = pd.to_datetime(end_date) + pd.Timedelta(days=1)
        data = yf.download(ticker, start=start_date, end=extended_end_date)
        data = data.reset_index()
        if 'Date' not in data.columns:
            raise ValueError(f"No 'Date' column found in the downloaded data for {ticker}.")
        
        data.columns = [col if isinstance(col, str) else col[0] + "_" + col[1] if col[1] else col[0] for col in data.columns]
        data = data[["Date", f"Close_{ticker}"]].rename(columns={f"Close_{ticker}": "Close"})
        data.to_csv(cache_file, index=False)
    return data

def get_last_trading_day(data, target_date):
    row = data[data["Date"] <= target_date].iloc[-1:]
    return row["Date"].values[0] if not row.empty else None

def calculate_drawdown(portfolio):
    peak = -np.inf
    max_drawdown = 0
    for value in portfolio:
        peak = max(peak, value)
        drawdown = (peak - value) / peak
        max_drawdown = max(max_drawdown, drawdown)
    return max_drawdown

def calculate_roi(initial, final, invested):
    return (final - initial) / invested if invested > 0 else 0

def calculate_cagr(start_value, end_value, years):
    return (end_value / start_value) ** (1 / years) - 1 if years > 0 and start_value > 0 else 0

def apply_simple_strategy(data, weekly_investment, ticker_1, end_date):
    total_invested = 0
    total_units = 0
    portfolio_value = []
    invested_amounts = []
    dates = []
    shares = {ticker_1: 0}

    for current_date in pd.date_range(data["Date"].min(), end_date, freq="W-FRI"):
        last_trading_day = get_last_trading_day(data, current_date)
        if last_trading_day is None:
            continue

        row = data[data["Date"] == last_trading_day].iloc[0]
        close = row["Close"]

        shares[ticker_1] += weekly_investment / close
        total_units += weekly_investment / close
        total_invested += weekly_investment
        portfolio_value.append(total_units * close)
        invested_amounts.append(total_invested)
        dates.append(last_trading_day)

    return total_invested, portfolio_value, invested_amounts, dates, shares

def apply_test_strategy(data, weekly_investment, ticker_1, ticker_2, ticker_3, index, end_date, dropdown_1, dropdown_2, start_date):
    total_invested = 0
    total_units = 0
    max_price = 0
    cash_balance = 0.0
    sell_price = None
    has_sold = False
    portfolio_value = []
    invested_amounts = []
    dates = []
    shares = {ticker_1: [], ticker_2: [], ticker_3: []}  # List of (units, purchase_price) tuples
    prev_close = None

    data_index = load_data(index, start_date, end_date)
    data_ticker1 = load_data(ticker_1, start_date, end_date)
    data_ticker2 = load_data(ticker_2, start_date, end_date)
    data_ticker3 = load_data(ticker_3, start_date, end_date)

    data = data_index.drop_duplicates(subset=['Date'], keep='last')
    data['Date'] = pd.to_datetime(data['Date'])
    data = data.set_index('Date').resample('B').ffill().reset_index()
    data = data.merge(data_ticker1[['Date', 'Close']], on="Date", how="left", suffixes=('', f'_{ticker_1}'))
    data = data.merge(data_ticker2[['Date', 'Close']].rename(columns={'Close': f'Close_{ticker_2}'}), on="Date", how="left")
    data = data.merge(data_ticker3[['Date', 'Close']].rename(columns={'Close': f'Close_{ticker_3}'}), on="Date", how="left")

    with open('report.txt', 'a') as report_file:
        for current_date in pd.date_range(data["Date"].min(), end_date, freq="W-FRI"):
            last_trading_day = get_last_trading_day(data, current_date)
            if last_trading_day is None:
                continue

            row = data[data["Date"] == last_trading_day].iloc[0]
            close = row["Close"]
            max_price = max(max_price, close)

            # Convert numpy.datetime64 to datetime.datetime
            last_trading_day_dt = pd.Timestamp(last_trading_day).to_pydatetime()

            # Sell all assets at 10% drawdown
            if not has_sold and close <= max_price * (1 - 0.10):
                cash_balance = 0
                for ticker in shares:
                    ticker_close = row["Close"] if ticker == ticker_1 else row.get(f"Close_{ticker}", row["Close"])
                    if ticker_close and not np.isnan(ticker_close):
                        sold_units = sum(units for units, _ in shares[ticker])
                        if sold_units > 0:
                            cash_balance += sold_units * ticker_close
                            print(f"Sold on {last_trading_day_dt.strftime('%Y-%m-%d')}: {ticker}, Units Sold: {sold_units:.2f}, Price: {ticker_close:.2f}, Remaining Shares: 0.00, Cash Balance: {cash_balance:.2f}")
                            report_file.write(f"{last_trading_day_dt.strftime('%Y-%m-%d')}: Sold {ticker}, Units: {sold_units:.2f}, Price: {ticker_close:.2f}\n")
                        shares[ticker] = []  # Sell all shares
                total_units = 0
                has_sold = True
                sell_price = close

            # Repurchase QQQ when price crosses sell_price upwards
            if has_sold and cash_balance > 0 and prev_close is not None and prev_close < sell_price and close >= sell_price:
                repurchase_units = cash_balance / close
                shares[ticker_1].append((repurchase_units, close))
                total_units += repurchase_units
                print(f"Repurchased QQQ on {last_trading_day_dt.strftime('%Y-%m-%d')}: Units: {repurchase_units:.2f}, Amount: {cash_balance:.2f}, Price: {close:.2f}")
                report_file.write(f"{last_trading_day_dt.strftime('%Y-%m-%d')}: Bought {ticker_1}, Units: {repurchase_units:.2f}, Price: {close:.2f}\n")
                cash_balance = 0

            # Weekly investment
            investment_source = 0
            if cash_balance >= weekly_investment:
                cash_balance -= weekly_investment
                investment_source = weekly_investment
            elif cash_balance > 0:
                investment_source = cash_balance
                cash_balance = 0
            else:
                investment_source = weekly_investment
                total_invested += weekly_investment

            if investment_source > 0:
                if close <= max_price * (1 - 0.20):  # 20% drawdown for TQQQ
                    ticker_3_close = row.get(f"Close_{ticker_3}", None)
                    if ticker_3_close and not np.isnan(ticker_3_close):
                        shares[ticker_3].append((investment_source / ticker_3_close, ticker_3_close))
                        total_units += investment_source / ticker_3_close
                        report_file.write(f"{last_trading_day_dt.strftime('%Y-%m-%d')}: Bought {ticker_3}, Units: {investment_source / ticker_3_close:.2f}, Price: {ticker_3_close:.2f}\n")
                elif close <= max_price * (1 - 0.10):  # 10% drawdown for QLD
                    ticker_2_close = row.get(f"Close_{ticker_2}", None)
                    if ticker_2_close and not np.isnan(ticker_2_close):
                        shares[ticker_2].append((investment_source / ticker_2_close, ticker_2_close))
                        total_units += investment_source / ticker_2_close
                        report_file.write(f"{last_trading_day_dt.strftime('%Y-%m-%d')}: Bought {ticker_2}, Units: {investment_source / ticker_2_close:.2f}, Price: {ticker_2_close:.2f}\n")
                else:  # Above 10% drawdown, buy QQQ
                    shares[ticker_1].append((investment_source / close, close))
                    total_units += investment_source / close
                    report_file.write(f"{last_trading_day_dt.strftime('%Y-%m-%d')}: Bought {ticker_1}, Units: {investment_source / close:.2f}, Price: {close:.2f}\n")

            portfolio_value.append(total_units * close + cash_balance)
            invested_amounts.append(total_invested)
            dates.append(last_trading_day)

            # Check for recovery to max_price
            if has_sold and close >= max_price:
                has_sold = False
                max_price = close
                print(f"Price recovered to max_price {max_price} on {last_trading_day_dt.strftime('%Y-%m-%d')}, new cycle started")

            prev_close = close  # Update previous close for next iteration

    final_shares = {ticker: sum(units for units, _ in shares[ticker]) for ticker in shares}
    return total_invested, portfolio_value, invested_amounts, dates, final_shares

def plot_results(simple_dates, simple_portfolio, simple_invested, test_dates, test_portfolio, test_invested, qqq_prices, skip_simple, skip_graf, dropdown_1, dropdown_2):
    if not skip_graf:
        plt.figure(figsize=(14, 7))
        if not skip_simple:
            plt.plot(simple_dates, simple_portfolio, label="Simple Strategy", alpha=0.7)
            plt.plot(simple_dates, simple_invested, "--", label="Invested (Simple)", alpha=0.7)
        plt.plot(test_dates, test_portfolio, label="Test Strategy", alpha=0.7)
        plt.plot(test_dates, test_invested, "--", label="Invested (Test)", alpha=0.7)

        max_price = np.max(qqq_prices['Close'])
        for date, price in zip(qqq_prices['Date'], qqq_prices['Close']):
            if price <= max_price * (1 - dropdown_2):
                plt.axvspan(date, date + pd.Timedelta(days=1), facecolor='red', alpha=0.2)
            elif price <= max_price * (1 - dropdown_1):
                plt.axvspan(date, date + pd.Timedelta(days=1), facecolor='orange', alpha=0.2)

        plt.title("Strategy Comparison")
        plt.xlabel("Date")
        plt.ylabel("Portfolio Value ($)")
        plt.legend()
        plt.grid()
        plt.show()

def main():
    parser = argparse.ArgumentParser(description="Testing Investment Strategy")
    parser.add_argument("--start_date", type=str, required=True, help="Start date (YYYY-MM-DD)")
    parser.add_argument("--end_date", type=str, default=datetime.now().strftime("%Y-%m-%d"), help="End date (YYYY-MM-DD)")
    parser.add_argument("weekly_investment", type=float, help="Weekly investment in dollars")
    parser.add_argument("--skip_simple", action="store_true", help="Skip simple strategy")
    parser.add_argument("--skip_graf", action="store_true", help="Skip graph display")
    parser.add_argument("--ticker_1", type=str, required=True, help="Main ticker (e.g., QQQ)")
    parser.add_argument("--ticker_2", type=str, required=True, help="Ticker for 10% dropdown (e.g., QLD)")
    parser.add_argument("--ticker_3", type=str, help="Ticker for 20% dropdown (e.g., TQQQ)")
    parser.add_argument("--index", type=str, required=True, help="Base ticker for drawdown (e.g., QQQ)")
    parser.add_argument("--dropdown_1", type=float, required=True, help="First drawdown level (e.g., 0.10)")
    parser.add_argument("--dropdown_2", type=float, required=True, help="Second drawdown level (e.g., 0.20)")
    args = parser.parse_args()

    if args.ticker_3 is None:
        args.ticker_3 = args.ticker_2

    end_date = pd.to_datetime(args.end_date)
    data = load_data(args.index, args.start_date, args.end_date)

    # Clear report file at start for test strategy only
    with open('report.txt', 'w') as report_file:
        report_file.write("Investment Strategy Report\n")

    if not args.skip_simple:
        simple_invested, simple_portfolio, simple_invested_curve, simple_dates, simple_shares = apply_simple_strategy(data, args.weekly_investment, args.ticker_1, end_date)
        simple_end_value = simple_portfolio[-1] if simple_portfolio else 0

    test_invested, test_portfolio, test_invested_curve, test_dates, test_shares = apply_test_strategy(
        data, args.weekly_investment, args.ticker_1, args.ticker_2, args.ticker_3, 
        args.index, end_date, args.dropdown_1, args.dropdown_2, args.start_date
    )
    test_end_value = test_portfolio[-1] if test_portfolio else 0

    start_year = datetime.strptime(args.start_date, "%Y-%m-%d").year
    end_year = end_date.year
    years = end_year - start_year + 1

    if not args.skip_simple:
        simple_cagr = calculate_cagr(simple_invested, simple_end_value, years)
        print("=== Simple Strategy ===")
        print(f"Total Invested: ${simple_invested:.2f}")
        print(f"Final Portfolio Value: ${simple_end_value:.2f}")
        print(f"Profit: ${simple_end_value - simple_invested:.2f}")
        print(f"Max Drawdown: {calculate_drawdown(simple_portfolio) * 100:.2f}%")
        print(f"ROI: {calculate_roi(0, simple_end_value, simple_invested) * 100:.2f}%")
        print(f"CAGR: {simple_cagr * 100:.2f}%")
        for ticker, count in simple_shares.items():
            print(f"Shares of {ticker}: {count:.2f}")

    test_cagr = calculate_cagr(test_invested, test_end_value, years)
    print("\n=== Test Strategy ===")
    print(f"Total Invested: ${test_invested:.2f}")
    print(f"Final Portfolio Value: ${test_end_value:.2f}")
    print(f"Profit: ${test_end_value - test_invested:.2f}")
    print(f"Max Drawdown: {calculate_drawdown(test_portfolio) * 100:.2f}%")
    print(f"ROI: {calculate_roi(0, test_end_value, test_invested) * 100:.2f}%")
    print(f"CAGR: {test_cagr * 100:.2f}%")

    end_prices = data[data['Date'].dt.date == end_date.date()]
    if end_prices.empty:
        last_trading_day = data['Date'].iloc[-1].date()
        print(f"Warning: Data for {end_date.date()} not found. Using last trading day {last_trading_day}.")
        end_prices = data.iloc[-1:]

    for ticker, count in test_shares.items():
        close_price = end_prices[f"Close_{ticker}"].iloc[0] if f"Close_{ticker}" in end_prices.columns else end_prices['Close'].iloc[0]
        value = count * close_price
        percentage = (value / test_end_value) * 100 if test_end_value > 0 else 0
        print(f"Shares of {ticker}: {count:.2f}, ${value:.2f}, {percentage:.2f}%")

    if not args.skip_simple:
        plot_results(simple_dates, simple_portfolio, simple_invested_curve, test_dates, test_portfolio, test_invested_curve, data, args.skip_simple, args.skip_graf, args.dropdown_1, args.dropdown_2)
    else:
        plot_results(None, None, None, test_dates, test_portfolio, test_invested_curve, data, args.skip_simple, args.skip_graf, args.dropdown_1, args.dropdown_2)

if __name__ == "__main__":
    main()