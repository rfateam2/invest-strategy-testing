# python test_x3_dropdown.py 100 --start_date 2015-01-01 --end_date 2024-12-31

import argparse
import yfinance as yf
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from datetime import datetime, timedelta


def load_data(start_date, end_date):
    """Загрузка данных QQQ за указанный период."""
    data = yf.download("QQQ", start=start_date, end=end_date)
    data = data.reset_index()  # Reset index to make 'Date' a column
    if 'Date' not in data.columns.get_level_values(0):
        raise ValueError("No 'Date' column found in the downloaded data.")
    
    # Rename the MultiIndex columns for simplicity 
    data.columns = [f"{col[0]}_{col[1]}" if col[1] else col[0] for col in data.columns]
    return data[["Date", "Close_QQQ"]].rename(columns={"Close_QQQ": "Close"})


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


def apply_simple_strategy(data, weekly_investment):
    total_invested = 0
    total_units = 0
    portfolio_value = []
    invested_amounts = []
    dates = []

    # Track shares for QQQ
    shares = {"QQQ": 0}

    for current_date in pd.date_range(data["Date"].min(), data["Date"].max(), freq="W-FRI"):
        last_trading_day = get_last_trading_day(data, current_date)
        if last_trading_day is None:
            continue

        row = data[data["Date"] == last_trading_day].iloc[0]
        close = row["Close"]

        shares["QQQ"] += weekly_investment / close  # Add to QQQ share count
        total_units += weekly_investment / close
        total_invested += weekly_investment
        portfolio_value.append(total_units * close)
        invested_amounts.append(total_invested)
        dates.append(last_trading_day)

    return total_invested, portfolio_value, invested_amounts, dates, shares


def apply_test_strategy(data, weekly_investment):
    total_invested = 0
    total_units = 0
    max_price = 0
    portfolio_value = []
    invested_amounts = []
    dates = []

    # Track shares for each ticker
    shares = {"QQQ": 0, "QLD": 0, "TQQQ": 0}

    data = data.drop_duplicates(subset=['Date'], keep='last')
    data['Date'] = pd.to_datetime(data['Date'])
    data = data.set_index('Date').resample('B').ffill().reset_index()

    tickers = {"QLD": None, "TQQQ": None}
    for ticker in tickers.keys():
        try:
            ticker_data = yf.download(ticker, start=data["Date"].min(), end=data["Date"].max(), progress=False)
            ticker_data = ticker_data.reset_index()
            ticker_data.columns = [f"{col[0]}_{col[1]}" if col[1] else col[0] for col in ticker_data.columns]
            tickers[ticker] = ticker_data[["Date", f"Close_{ticker}"]].rename(columns={f"Close_{ticker}": f"{ticker}_Close"})
        except Exception as e:
            print(f"Failed to download data for {ticker}: {e}")
            tickers[ticker] = pd.DataFrame(columns=["Date", f"{ticker}_Close"])  # Empty DataFrame if download fails

    for ticker, ticker_data in tickers.items():
        if not ticker_data.empty:
            data = data.merge(ticker_data, on="Date", how="left")

    for current_date in pd.date_range(data["Date"].min(), data["Date"].max(), freq="W-FRI"):
        last_trading_day = get_last_trading_day(data, current_date)
        if last_trading_day is None:
            continue

        row = data[data["Date"] == last_trading_day].iloc[0]
        close = row["Close"]
        max_price = max(max_price, close)

        if close <= max_price * 0.8:
            tqqq_close = row.get("TQQQ_Close", None)
            if tqqq_close and not np.isnan(tqqq_close):
                shares["TQQQ"] += weekly_investment / tqqq_close
                total_units += weekly_investment / tqqq_close
        elif close <= max_price * 0.9:
            qld_close = row.get("QLD_Close", None)
            if qld_close and not np.isnan(qld_close):
                shares["QLD"] += weekly_investment / qld_close
                total_units += weekly_investment / qld_close
        else:
            shares["QQQ"] += weekly_investment / close
            total_units += weekly_investment / close

        total_invested += weekly_investment
        portfolio_value.append(total_units * close)
        invested_amounts.append(total_invested)
        dates.append(last_trading_day)

    # Return shares along with other results
    return total_invested, portfolio_value, invested_amounts, dates, shares


def plot_results(simple_dates, simple_portfolio, simple_invested, test_dates, test_portfolio, test_invested, qqq_prices):
    """Отображение результатов стратегий с подсветкой периодов падения цены QQQ."""
    plt.figure(figsize=(14, 7))
    plt.plot(test_dates, test_portfolio, label="Тестируемая стратегия", alpha=0.7)
    plt.plot(simple_dates, simple_portfolio, label="Простая стратегия", alpha=0.7)
    plt.plot(simple_dates, simple_invested, "--", label="Инвестиции", alpha=0.7)

    # Calculate max price up to each point
    max_price = 0
    for date, price in zip(qqq_prices['Date'], qqq_prices['Close']):
        max_price = max(max_price, price)
        
        if price <= max_price * 0.8:  # 20% below max
            plt.axvspan(date, date + pd.Timedelta(days=1), facecolor='red', alpha=0.2)
        elif price <= max_price * 0.9:  # 10% below max
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
    args = parser.parse_args()

    # Загрузка данных
    data = load_data(args.start_date, args.end_date)

    # Применение стратегий
    simple_invested, simple_portfolio, simple_invested_curve, simple_dates, simple_shares = apply_simple_strategy(data, args.weekly_investment)
    test_invested, test_portfolio, test_invested_curve, test_dates, test_shares = apply_test_strategy(data, args.weekly_investment)

    # Итоговые значения
    simple_end_value = simple_portfolio[-1] if simple_portfolio else 0
    test_end_value = test_portfolio[-1] if test_portfolio else 0

    # Расчет CAGR
    start_year = datetime.strptime(args.start_date, "%Y-%m-%d").year
    end_year = datetime.strptime(args.end_date, "%Y-%m-%d").year
    years = end_year - start_year + 1
    simple_cagr = calculate_cagr(simple_invested, simple_end_value, years)
    test_cagr = calculate_cagr(test_invested, test_end_value, years)

    # Вывод результатов
    print("=== Простая стратегия ===")
    print(f"Общая сумма вложений: ${simple_invested:.2f}")
    print(f"Итоговая стоимость портфеля: ${simple_end_value:.2f}")
    print(f"Итоговая прибыль: ${simple_end_value - simple_invested:.2f}")
    print(f"Максимальная просадка: {calculate_drawdown(simple_portfolio) * 100:.2f}%")
    print(f"ROI: {calculate_roi(0, simple_end_value, simple_invested) * 100:.2f}%")
    print(f"CAGR: {simple_cagr * 100:.2f}%")
    for ticker, count in simple_shares.items():
        print(f"Количество акций {ticker}: {count:.2f}")

    print("\n=== Тестируемая стратегия ===")
    print(f"Общая сумма вложений: ${test_invested:.2f}")
    print(f"Итоговая стоимость портфеля: ${test_end_value:.2f}")
    print(f"Итоговая прибыль: ${test_end_value - test_invested:.2f}")
    print(f"Максимальная просадка: {calculate_drawdown(test_portfolio) * 100:.2f}%")
    print(f"ROI: {calculate_roi(0, test_end_value, test_invested) * 100:.2f}%")
    print(f"CAGR: {test_cagr * 100:.2f}%")
    for ticker, count in test_shares.items():
        print(f"Количество акций {ticker}: {count:.2f}")

    # Отображение графика
    plot_results(simple_dates, simple_portfolio, simple_invested_curve, test_dates, test_portfolio, test_invested_curve, data)

if __name__ == "__main__":
    main()
