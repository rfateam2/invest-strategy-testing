# python x.py 100 --start_date 2015-01-01 --end_date 2024-12-31 --skip_simple --skip_graf --ticker_1 QQQ --ticker_2 QLD --ticker_3 TQQQ --index QQQ --dropdown_1 0.10 --dropdown_2 0.20

import argparse
import os
import yfinance as yf
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from datetime import datetime, timedelta

def load_data(ticker, start_date, end_date):
    # Create a unique cache file name based on ticker and date range
    cache_file = f"{ticker}_{start_date}_{end_date}.csv"
    
    if os.path.exists(cache_file):
        data = pd.read_csv(cache_file)
        data['Date'] = pd.to_datetime(data['Date'])
    else:
        extended_end_date = pd.to_datetime(end_date) + pd.Timedelta(days=1)
        data = yf.download(ticker, start=start_date, end=extended_end_date)
        data = data.reset_index()  # Reset index to make 'Date' a column
        if 'Date' not in data.columns.get_level_values(0):
            raise ValueError(f"No 'Date' column found in the downloaded data for {ticker}.")
        
        # Rename the MultiIndex columns for simplicity 
        data.columns = [f"{col[0]}_{col[1]}" if col[1] else col[0] for col in data.columns]
        data = data[["Date", f"Close_{ticker}"]].rename(columns={f"Close_{ticker}": "Close"})
        data.to_csv(cache_file, index=False)  # Save to cache

    return data


def get_last_trading_day(data, target_date):
    """Получить последний торговый день до целевой даты."""
    row = data[data["Date"] <= target_date].iloc[-1:]  # Последний доступный день
    return row["Date"].values[0] if not row.empty else None


def calculate_drawdown(portfolio):
    """Расчет максимальной просадки портфеля."""
    peak = -np.inf
    max_drawdown = 0
    for value in portfolio:
        peak = max(peak, value)
        drawdown = (peak - value) / peak
        max_drawdown = max(max_drawdown, drawdown)
    return max_drawdown


def calculate_roi(initial, final, invested):
    """Расчет ROI."""
    return (final - initial) / invested


def calculate_cagr(start_value, end_value, years):
    """Расчет CAGR."""
    return (end_value / start_value) ** (1 / years) - 1 if years > 0 else 0


def apply_simple_strategy(data, weekly_investment, ticker_1, end_date):
    total_invested = 0
    total_units = 0
    portfolio_value = []
    invested_amounts = []
    dates = []

    # Track shares for the main ticker
    shares = {ticker_1: 0}

    for current_date in pd.date_range(data["Date"].min(), end_date, freq="W-FRI"):
        last_trading_day = get_last_trading_day(data, current_date)
        if last_trading_day is None:
            continue

        row = data[data["Date"] == last_trading_day].iloc[0]
        close = row["Close"]

        shares[ticker_1] += weekly_investment / close  # Add to ticker_1 share count
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
    portfolio_value = []
    invested_amounts = []
    dates = []

    # Track shares for each ticker
    shares = {ticker_1: 0, ticker_2: 0, ticker_3: 0}

    # Load and merge data for all tickers
    data_index = load_data(index, start_date, end_date)
    data_ticker1 = load_data(ticker_1, start_date, end_date)
    data_ticker2 = load_data(ticker_2, start_date, end_date)
    data_ticker3 = load_data(ticker_3, start_date, end_date)

    # Merge data
    data = data_index.drop_duplicates(subset=['Date'], keep='last')
    data['Date'] = pd.to_datetime(data['Date'])
    data = data.set_index('Date').resample('B').ffill().reset_index()

    # Merge ticker_1 data
    data = data.merge(data_ticker1[['Date', 'Close']], on="Date", how="left", suffixes=('', f'_{ticker_1}'))
    
    # Merge ticker_2 and ticker_3 data, ensuring we use unique column names
    data = data.merge(data_ticker2[['Date', 'Close']].rename(columns={'Close': f'Close_{ticker_2}'}), on="Date", how="left")
    data = data.merge(data_ticker3[['Date', 'Close']].rename(columns={'Close': f'Close_{ticker_3}'}), on="Date", how="left")

    for current_date in pd.date_range(data["Date"].min(), end_date, freq="W-FRI"):
        last_trading_day = get_last_trading_day(data, current_date)
        if last_trading_day is None:
            continue

        row = data[data["Date"] == last_trading_day].iloc[0]
        close = row["Close"]
        max_price = max(max_price, close)

        if close <= max_price * (1 - dropdown_2):
            ticker_3_close = row.get(f"Close_{ticker_3}", None)
            if ticker_3_close and not np.isnan(ticker_3_close):
                shares[ticker_3] += weekly_investment / ticker_3_close
                total_units += weekly_investment / ticker_3_close
        elif close <= max_price * (1 - dropdown_1):
            ticker_2_close = row.get(f"Close_{ticker_2}", None)
            if ticker_2_close and not np.isnan(ticker_2_close):
                shares[ticker_2] += weekly_investment / ticker_2_close
                total_units += weekly_investment / ticker_2_close
        else:
            shares[ticker_1] += weekly_investment / close
            total_units += weekly_investment / close

        total_invested += weekly_investment
        portfolio_value.append(total_units * close)
        invested_amounts.append(total_invested)
        dates.append(last_trading_day)

    # Return shares along with other results
    return total_invested, portfolio_value, invested_amounts, dates, shares


def plot_results(simple_dates, simple_portfolio, simple_invested, test_dates, test_portfolio, test_invested, qqq_prices, skip_simple, skip_graf, dropdown_1, dropdown_2):
    """Отображение результатов стратегий с подсветкой периодов падения цены."""
    if not skip_graf:
        plt.figure(figsize=(14, 7))
        if not skip_simple:
            plt.plot(simple_dates, simple_portfolio, label="Простая стратегия", alpha=0.7)
            plt.plot(simple_dates, simple_invested, "--", label="Инвестиции", alpha=0.7)
        plt.plot(test_dates, test_portfolio, label="Тестируемая стратегия", alpha=0.7)

        # Calculate max price up to each point
        max_price = 0
        for date, price in zip(qqq_prices['Date'], qqq_prices['Close']):
            max_price = max(max_price, price)
            
            if price <= max_price * (1 - dropdown_2):  # dropdown_2 below max
                plt.axvspan(date, date + pd.Timedelta(days=1), facecolor='red', alpha=0.2)
            elif price <= max_price * (1 - dropdown_1):  # dropdown_1 below max
                plt.axvspan(date, date + pd.Timedelta(days=1), facecolor='orange', alpha=0.2)

        plt.title("Сравнение стратегий")
        plt.xlabel("Дата")
        plt.ylabel("Стоимость портфеля ($)")
        plt.legend()
        plt.grid()
        plt.show()


def main():
    parser = argparse.ArgumentParser(description="Тестирование инвестиционной стратегии.")
    parser.add_argument("--start_date", type=str, required=True, help="Дата начала периода (YYYY-MM-DD).")
    parser.add_argument("--end_date", type=str, default=datetime.now().strftime("%Y-%m-%d"), help="Дата конца периода (YYYY-MM-DD).")
    parser.add_argument("weekly_investment", type=float, help="Сумма еженедельного пополнения в долларах.")
    parser.add_argument("--skip_simple", action="store_true", help="Не проводить простое тестирование.")
    parser.add_argument("--skip_graf", action="store_true", help="Не отображать график.")
    parser.add_argument("--ticker_1", type=str, required=True, help="Основной тикер для инвестиций.")
    parser.add_argument("--ticker_2", type=str, required=True, help="Тикер для покупки при просадке на 10%.")
    parser.add_argument("--ticker_3", type=str, help="Тикер для покупки при просадке на 20%.")
    parser.add_argument("--index", type=str, required=True, help="Базовый тикер для расчета просадок.")
    parser.add_argument("--dropdown_1", type=float, required=True, help="Величина первой просадки для расчетов (например, 0.10 для 10%).")
    parser.add_argument("--dropdown_2", type=float, required=True, help="Величина второй просадки для расчетов (например, 0.20 для 20%).")
    args = parser.parse_args()

    # If ticker_3 is not provided, use ticker_2
    if args.ticker_3 is None:
        args.ticker_3 = args.ticker_2

    # Convert end_date to datetime for easier manipulation
    end_date = pd.to_datetime(args.end_date)

    # Загрузка данных для базового индекса, with end_date extended by one day
    data = load_data(args.index, args.start_date, args.end_date)

    if not args.skip_simple:
        simple_invested, simple_portfolio, simple_invested_curve, simple_dates, simple_shares = apply_simple_strategy(data, args.weekly_investment, args.ticker_1, end_date)
        simple_end_value = simple_portfolio[-1] if simple_portfolio else 0

    test_invested, test_portfolio, test_invested_curve, test_dates, test_shares = apply_test_strategy(data, args.weekly_investment, args.ticker_1, args.ticker_2, args.ticker_3, args.index, end_date, args.dropdown_1, args.dropdown_2, args.start_date)
    test_end_value = test_portfolio[-1] if test_portfolio else 0

    # Расчет CAGR
    start_year = datetime.strptime(args.start_date, "%Y-%m-%d").year
    end_year = end_date.year
    years = end_year - start_year + 1

    if not args.skip_simple:
        simple_cagr = calculate_cagr(simple_invested, simple_end_value, years)
        print("=== Простая стратегия ===")
        print(f"Общая сумма вложений: ${simple_invested:.2f}")
        print(f"Итоговая стоимость портфеля: ${simple_end_value:.2f}")
        print(f"Итоговая прибыль: ${simple_end_value - simple_invested:.2f}")
        print(f"Максимальная просадка: {calculate_drawdown(simple_portfolio) * 100:.2f}%")
        print(f"ROI: {calculate_roi(0, simple_end_value, simple_invested) * 100:.2f}%")
        print(f"CAGR: {simple_cagr * 100:.2f}%")
        for ticker, count in simple_shares.items():
            print(f"Количество акций {ticker}: {count:.2f}")

    test_cagr = calculate_cagr(test_invested, test_end_value, years)
    print("\n=== Тестируемая стратегия ===")
    print(f"Общая сумма вложений: ${test_invested:.2f}")
    print(f"Итоговая стоимость портфеля: ${test_end_value:.2f}")
    print(f"Итоговая прибыль: ${test_end_value - test_invested:.2f}")
    print(f"Максимальная просадка: {calculate_drawdown(test_portfolio) * 100:.2f}%")
    print(f"ROI: {calculate_roi(0, test_end_value, test_invested) * 100:.2f}%")
    print(f"CAGR: {test_cagr * 100:.2f}%")

    # Get the closing prices for the exact end date
    end_prices = data[data['Date'].dt.date == end_date.date()]
    
    if end_prices.empty:
        last_trading_day = data['Date'].iloc[-1].date()
        print(f"Внимание: Данные для {end_date.date()} отсутствуют. Используем последний доступный торговый день {last_trading_day}.")
        end_prices = data.iloc[-1:]  # Use the last available data if end_date is not in dataset

    for ticker, count in test_shares.items():
        close_price = end_prices[f"{ticker}_Close"].iloc[0] if f"{ticker}_Close" in end_prices.columns else end_prices['Close'].iloc[0]
        value = count * close_price
        percentage = (value / test_end_value) * 100
        print(f"Количество акций {ticker}: {count:.2f}, ${value:.2f}, {percentage:.2f}%")

    # Отображение графика
    if not args.skip_simple:
        plot_results(simple_dates, simple_portfolio, simple_invested_curve, test_dates, test_portfolio, test_invested_curve, data, args.skip_simple, args.skip_graf, args.dropdown_1, args.dropdown_2)
    else:
        plot_results(None, None, None, test_dates, test_portfolio, test_invested_curve, data, args.skip_simple, args.skip_graf, args.dropdown_1, args.dropdown_2)

if __name__ == "__main__":
    main()