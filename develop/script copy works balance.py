import argparse
import os
import yfinance as yf
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from datetime import datetime, timedelta
import math

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

def calculate_drawdown(current_value, last_max):
    if last_max <= 0 or current_value >= last_max:
        return 0.0
    return ((last_max - current_value) / last_max) * 100

def calculate_max_drawdown(drawdown_history):
    return max(drawdown_history) if drawdown_history else 0.0

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
    last_max_portfolio = 0.0
    drawdown_history = []
    max_drawdown = 0.0

    with open('report_simple.txt', 'w') as report_file:
        report_file.write("Simple Strategy Report\n")
        for current_date in pd.date_range(data["Date"].min(), end_date, freq="W-FRI"):
            last_trading_day = get_last_trading_day(data, current_date)
            if last_trading_day is None:
                continue

            row = data[data["Date"] == last_trading_day].iloc[0]
            close = row["Close"]

            units = math.floor(weekly_investment / close)
            total_units += units
            total_invested += units * close
            portfolio_value_current = total_units * close
            current_drawdown = calculate_drawdown(portfolio_value_current, last_max_portfolio)
            drawdown_history.append(current_drawdown)
            max_drawdown = max(max_drawdown, current_drawdown)
            report_file.write(f"{pd.Timestamp(last_trading_day).to_pydatetime().strftime('%Y-%m-%d')}: Bought {ticker_1}, Units: {units:.2f}, Price: ${close:.2f}. Hold {ticker_1}, Units: {total_units:.2f}. Portfolio Value: ${portfolio_value_current:.2f}, Drawdown: {current_drawdown:.2f}%\n")
            if portfolio_value_current >= last_max_portfolio:
                last_max_portfolio = portfolio_value_current
                drawdown_history = []
            portfolio_value.append(portfolio_value_current)
            invested_amounts.append(total_invested)
            dates.append(last_trading_day)

    return total_invested, portfolio_value, invested_amounts, dates, {ticker_1: total_units}, max_drawdown

def apply_test_strategy(data, weekly_investment, ticker_1, ticker_2, ticker_3, index, end_date, dropdown_1, dropdown_2, start_date, sell_threshold=None):
    cash_balance = 0.0  # Виртуальный cash_balance, инициализированный как 0
    total_invested = 0
    total_units = 0
    max_price = 0
    sell_price = None
    has_sold = False
    portfolio_value = []
    invested_amounts = []
    dates = []
    shares = {ticker_1: [], ticker_2: [], ticker_3: []}
    prev_close = None

    # Загрузка данных
    data_index = load_data(index, start_date, end_date)
    data = data_index.drop_duplicates(subset=['Date']).set_index('Date').resample('B').ffill().reset_index()
    data_ticker1 = load_data(ticker_1, start_date, end_date)
    data_ticker2 = load_data(ticker_2, start_date, end_date)
    data_ticker3 = load_data(ticker_3, start_date, end_date)
    data = data.merge(data_ticker1[['Date', 'Close']], on="Date", how="left", suffixes=('', f'_{ticker_1}'))
    data = data.merge(data_ticker2[['Date', 'Close']].rename(columns={'Close': f'Close_{ticker_2}'}), on="Date", how="left")
    data = data.merge(data_ticker3[['Date', 'Close']].rename(columns={'Close': f'Close_{ticker_3}'}), on="Date", how="left")

    with open('report_test.txt', 'w') as report_file:
        report_file.write("Test Strategy Report\n")
        for current_date in pd.date_range(data["Date"].min(), end_date, freq="W-FRI"):
            last_trading_day = get_last_trading_day(data, current_date)
            if last_trading_day is None:
                continue

            row = data[data["Date"] == last_trading_day].iloc[0]
            qqq_close = row["Close"]
            qld_close = row.get(f"Close_{ticker_2}", 0) if not pd.isna(row.get(f"Close_{ticker_2}")) else 0
            tqqq_close = row.get(f"Close_{ticker_3}", 0) if not pd.isna(row.get(f"Close_{ticker_3}")) else 0
            max_price = max(max_price, qqq_close)
            last_trading_day_str = pd.Timestamp(last_trading_day).strftime('%Y-%m-%d')

            # Продажа при достижении sell_threshold
            if sell_threshold and not has_sold and qqq_close <= max_price * (1 - sell_threshold):
                total_sale_amount = 0
                for ticker in shares:
                    ticker_close = qqq_close if ticker == ticker_1 else qld_close if ticker == ticker_2 else tqqq_close
                    if ticker_close > 0:
                        sold_units = sum(units for units, _ in shares[ticker])
                        if sold_units > 0:
                            sale_amount = sold_units * ticker_close
                            total_sale_amount += sale_amount
                            report_file.write(f"{last_trading_day_str}: Sold {ticker}, Units: {sold_units:.2f}, Price: ${ticker_close:.2f}, Amount: ${sale_amount:.2f}\n")
                        shares[ticker] = []
                cash_balance += total_sale_amount
                total_units = 0
                has_sold = True
                sell_price = qqq_close
                portfolio_value.append(cash_balance)
                invested_amounts.append(total_invested)
                dates.append(last_trading_day)

            # Выкуп QQQ
            if has_sold and cash_balance > 0 and prev_close and prev_close < sell_price and qqq_close >= sell_price:
                units = math.floor(cash_balance / qqq_close)
                if units > 0:
                    shares[ticker_1].append((units, qqq_close))
                    total_units += units
                    purchase_amount = units * qqq_close
                    cash_balance -= purchase_amount
                    report_file.write(f"{last_trading_day_str}: Repurchased {ticker_1}, Units: {units:.2f}, Price: ${qqq_close:.2f}, Amount: ${purchase_amount:.2f}, Remaining Cash Balance: ${cash_balance:.2f}\n")
                    has_sold = False
                portfolio_value.append(sum(units * qqq_close for units, _ in shares[ticker_1]) + cash_balance)
                invested_amounts.append(total_invested)
                dates.append(last_trading_day)

            # Пополнение cash_balance и покупка
            min_price = min([p for p in [qqq_close, qld_close, tqqq_close] if p > 0] or [1.0])
            if cash_balance < weekly_investment:  # Пополняем cash_balance до weekly_investment каждый раз
                cash_balance += weekly_investment
                total_invested += weekly_investment
            investment_amount = min(cash_balance, weekly_investment)

            if investment_amount > 0:
                if qqq_close >= max_price * (1 - dropdown_1):
                    units = math.floor(investment_amount / qqq_close)
                    if units > 0:
                        shares[ticker_1].append((units, qqq_close))
                        total_units += units
                        purchase_amount = units * qqq_close
                        cash_balance -= purchase_amount
                        report_file.write(f"{last_trading_day_str}: Bought {ticker_1}, Units: {units:.2f}, Price: ${qqq_close:.2f}, Remaining Cash Balance: ${cash_balance:.2f}\n")
                elif qqq_close >= max_price * (1 - dropdown_2) and qld_close > 0:
                    units = math.floor(investment_amount / qld_close)
                    if units > 0:
                        shares[ticker_2].append((units, qld_close))
                        total_units += units
                        purchase_amount = units * qld_close
                        cash_balance -= purchase_amount
                        report_file.write(f"{last_trading_day_str}: Bought {ticker_2}, Units: {units:.2f}, Price: ${qld_close:.2f}, Remaining Cash Balance: ${cash_balance:.2f}\n")
                elif tqqq_close > 0:
                    units = math.floor(investment_amount / tqqq_close)
                    if units > 0:
                        shares[ticker_3].append((units, tqqq_close))
                        total_units += units
                        purchase_amount = units * tqqq_close
                        cash_balance -= purchase_amount
                        report_file.write(f"{last_trading_day_str}: Bought {ticker_3}, Units: {units:.2f}, Price: ${tqqq_close:.2f}, Remaining Cash Balance: ${cash_balance:.2f}\n")

            # Обновление портфеля
            qqq_value = sum(units * qqq_close for units, _ in shares[ticker_1]) if qqq_close > 0 else 0
            qld_value = sum(units * qld_close for units, _ in shares[ticker_2]) if qld_close > 0 else 0
            tqqq_value = sum(units * tqqq_close for units, _ in shares[ticker_3]) if tqqq_close > 0 else 0
            portfolio_value_current = qqq_value + qld_value + tqqq_value + cash_balance
            portfolio_value.append(portfolio_value_current)
            invested_amounts.append(total_invested)
            dates.append(last_trading_day)
            prev_close = qqq_close

    final_shares = {ticker: sum(units for units, _ in shares[ticker]) for ticker in shares}
    return total_invested, portfolio_value, invested_amounts, dates, final_shares, 0, cash_balance  # Max drawdown пока опущен для простоты

def plot_results(simple_dates, simple_portfolio, simple_invested, test_dates, test_portfolio, test_invested, data, ticker_1, ticker_2, ticker_3, skip_simple, skip_graf, dropdown_1, dropdown_2):
    if not skip_graf:
        plt.figure(figsize=(14, 7))
        if not skip_simple and simple_portfolio and simple_dates:
            plt.plot(simple_dates, simple_portfolio, label="Simple Strategy", color='blue', alpha=0.7)
            plt.plot(simple_dates, simple_invested, "--", label="Invested (Simple)", color='orange', alpha=0.7)
        if test_portfolio and test_dates:
            plt.plot(test_dates, test_portfolio, label="Test Strategy", color='green', alpha=0.7)
            if test_invested:
                plt.plot(test_dates, test_invested, "--", label="Invested (Test)", color='red', alpha=0.7)

        max_price = np.max(data['Close']) if data['Close'].size > 0 else 0
        for date, price in zip(data['Date'], data['Close']):
            last_trading_day = get_last_trading_day(data, date)
            if last_trading_day:
                row = data[data["Date"] == last_trading_day].iloc[0]
                qqq_close = row["Close"]
                qld_close = row.get(f"Close_{ticker_2}", 0) if not np.isnan(row.get(f"Close_{ticker_2}", 0)) else 0
                tqqq_close = row.get(f"Close_{ticker_3}", 0) if not np.isnan(row.get(f"Close_{ticker_3}", 0)) else 0
                if qqq_close <= max_price * (1 - 0.20) and tqqq_close > 0:
                    plt.axvspan(date, date + pd.Timedelta(days=1), facecolor='red', alpha=0.2)
                elif qqq_close <= max_price * (1 - 0.10) and qld_close > 0 and tqqq_close == 0:
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
    parser.add_argument("--sell_threshold", type=float, help="Threshold for selling all assets (e.g., 0.10 for 10%)")
    args = parser.parse_args()

    if args.ticker_3 is None:
        args.ticker_3 = args.ticker_2

    end_date = pd.to_datetime(args.end_date)
    data = load_data(args.index, args.start_date, args.end_date)
    data_ticker1 = load_data(args.ticker_1, args.start_date, args.end_date)
    data_ticker2 = load_data(args.ticker_2, args.start_date, args.end_date)
    data_ticker3 = load_data(args.ticker_3, args.start_date, args.end_date)

    with open('report_simple.txt', 'w') as report_simple_file:
        report_simple_file.write("Simple Strategy Report\n")
    with open('report_test.txt', 'w') as report_test_file:
        report_test_file.write("Test Strategy Report\n")

    if not args.skip_simple:
        simple_invested, simple_portfolio, simple_invested_curve, simple_dates, simple_shares, simple_max_drawdown = apply_simple_strategy(data, args.weekly_investment, args.ticker_1, end_date)
        simple_end_value = simple_portfolio[-1] if simple_portfolio else 0

    test_invested, test_portfolio, test_invested_curve, test_dates, test_shares, test_max_drawdown, final_cash_balance = apply_test_strategy(
        data, args.weekly_investment, args.ticker_1, args.ticker_2, args.ticker_3, 
        args.index, end_date, args.dropdown_1, args.dropdown_2, args.start_date, args.sell_threshold
    )
    test_end_value = test_portfolio[-1] + (final_cash_balance if final_cash_balance is not None else 0) if test_portfolio else 0

    start_year = datetime.strptime(args.start_date, "%Y-%m-%d").year
    end_year = end_date.year
    years = end_year - start_year + 1

    if not args.skip_simple:
        simple_cagr = calculate_cagr(simple_invested, simple_end_value, years)
        print("=== Simple Strategy ===")
        print(f"Total Invested: ${simple_invested:.2f}")
        print(f"Final Portfolio Value: ${simple_end_value:.2f}")
        print(f"Profit: ${simple_end_value - simple_invested:.2f}")
        print(f"Max Drawdown: {simple_max_drawdown:.2f}%")
        print(f"ROI: {calculate_roi(0, simple_end_value, simple_invested) * 100:.2f}%")
        print(f"CAGR: {simple_cagr * 100:.2f}%")
        for ticker, count in simple_shares.items():
            print(f"Shares of {ticker}: {count:.2f}")

    test_cagr = calculate_cagr(test_invested, test_end_value, years)
    print("\n=== Test Strategy ===")
    print(f"Total Invested: ${test_invested:.2f}")
    print(f"Final Portfolio Value: ${test_end_value:.2f}")
    print(f"Profit: ${test_end_value - test_invested:.2f}")
    print(f"Max Drawdown: {test_max_drawdown:.2f}%")
    print(f"ROI: {calculate_roi(0, test_end_value, test_invested) * 100:.2f}%")
    print(f"CAGR: {test_cagr * 100:.2f}%")

    end_date_qqq = data_ticker1[data_ticker1['Date'].dt.date == end_date.date()]
    end_date_qld = data_ticker2[data_ticker2['Date'].dt.date == end_date.date()]
    end_date_tqqq = data_ticker3[data_ticker3['Date'].dt.date == end_date.date()]
    
    qqq_close = end_date_qqq['Close'].iloc[-1] if not end_date_qqq.empty and len(end_date_qqq) > 0 else data_ticker1.iloc[-1]['Close'] if not data_ticker1.empty else 0
    qld_close = end_date_qld['Close'].iloc[-1] if not end_date_qld.empty and len(end_date_qld) > 0 else data_ticker2.iloc[-1]['Close'] if not data_ticker2.empty else 0
    tqqq_close = end_date_tqqq['Close'].iloc[-1] if not end_date_tqqq.empty and len(end_date_tqqq) > 0 else data_ticker3.iloc[-1]['Close'] if not data_ticker3.empty else 0
    
    final_value_qqq = test_shares[args.ticker_1] * qqq_close if test_shares[args.ticker_1] > 0 else 0
    final_value_qld = test_shares[args.ticker_2] * qld_close if test_shares[args.ticker_2] > 0 else 0
    final_value_tqqq = test_shares[args.ticker_3] * tqqq_close if test_shares[args.ticker_3] > 0 else 0
    final_portfolio_value = final_value_qqq + final_value_qld + final_value_tqqq
    print(f"Shares of {args.ticker_1}: {test_shares[args.ticker_1]:.2f}, ${final_value_qqq:.2f}, {(final_value_qqq / final_portfolio_value * 100 if final_portfolio_value > 0 else 0):.2f}%")
    print(f"Shares of {args.ticker_2}: {test_shares[args.ticker_2]:.2f}, ${final_value_qld:.2f}, {(final_value_qld / final_portfolio_value * 100 if final_portfolio_value > 0 else 0):.2f}%")
    print(f"Shares of {args.ticker_3}: {test_shares[args.ticker_3]:.2f}, ${final_value_tqqq:.2f}, {(final_value_tqqq / final_portfolio_value * 100 if final_portfolio_value > 0 else 0):.2f}%")
    print(f"Remaining Cash Balance: ${final_cash_balance:.2f}")

    if not args.skip_simple:
        plot_results(simple_dates, simple_portfolio, simple_invested_curve, test_dates, test_portfolio, test_invested_curve, data, args.ticker_1, args.ticker_2, args.ticker_3, args.skip_simple, args.skip_graf, args.dropdown_1, args.dropdown_2)
    else:
        plot_results(None, None, None, test_dates, test_portfolio, test_invested_curve, data, args.ticker_1, args.ticker_2, args.ticker_3, args.skip_simple, args.skip_graf, args.dropdown_1, args.dropdown_2)

if __name__ == "__main__":
    main()