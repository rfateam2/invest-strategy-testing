# python test_x2.py 100 --start_date 2015-01-01 --end_date 2024-12-31

import yfinance as yf
import pandas as pd
import numpy as np
import argparse
from datetime import datetime, timedelta
import matplotlib.pyplot as plt


def load_data(start_date, end_date):
    """Загрузка данных для тикера QQQ."""
    data = yf.download("QQQ", start=start_date, end=end_date)
    if data.empty:
        raise ValueError("Не удалось загрузить данные для тикера QQQ. Проверьте диапазон дат.")
    data = data["Close"].reset_index()
    data.columns = ["Date", "Close"]
    return data


def get_last_trading_day(data, target_date):
    """Возвращает последнюю торговую дату до указанной (включительно)."""
    trading_days = data[data["Date"] <= target_date]
    if trading_days.empty:
        return None
    return trading_days.iloc[-1]["Date"]


def apply_simple_strategy(data, weekly_investment):
    """Простая стратегия: покупка QQQ каждую неделю."""
    total_invested = 0
    total_units = 0
    portfolio_value = []
    dates = []

    for current_date in pd.date_range(data["Date"].min(), data["Date"].max(), freq="W-FRI"):
        last_trading_day = get_last_trading_day(data, current_date)
        if last_trading_day is None:
            continue

        row = data[data["Date"] == last_trading_day].iloc[0]
        close = row["Close"]

        total_units += weekly_investment / close
        total_invested += weekly_investment
        portfolio_value.append(total_units * close)
        dates.append(last_trading_day)

    return total_invested, portfolio_value, dates


def apply_test_strategy(data, weekly_investment):
    """Тестируемая стратегия с перераспределением вложений."""
    total_invested = 0
    total_units = 0
    max_price = 0
    portfolio_value = []
    dates = []

    # Загрузка данных для QLD и TQQQ
    tickers = {"QLD": None, "TQQQ": None}
    for ticker in tickers.keys():
        ticker_data = yf.download(ticker, start=data["Date"].min(), end=data["Date"].max())
        tickers[ticker] = ticker_data["Close"].reset_index()
        tickers[ticker].columns = ["Date", f"{ticker}_Close"]

    # Объединение данных QQQ, QLD и TQQQ
    for ticker, ticker_data in tickers.items():
        data = data.merge(ticker_data, on="Date", how="left")

    # Применение стратегии
    for current_date in pd.date_range(data["Date"].min(), data["Date"].max(), freq="W-FRI"):
        last_trading_day = get_last_trading_day(data, current_date)
        if last_trading_day is None:
            continue

        row = data[data["Date"] == last_trading_day].iloc[0]
        close, max_price = row["Close"], max(max_price, row["Close"])

        # Логика вложений
        if close <= max_price * 0.8:  # Покупка TQQQ
            tqqq_close = row.get("TQQQ_Close", None)
            if tqqq_close and not np.isnan(tqqq_close):
                total_units += weekly_investment / tqqq_close
        elif close <= max_price * 0.9:  # Покупка QLD
            qld_close = row.get("QLD_Close", None)
            if qld_close and not np.isnan(qld_close):
                total_units += weekly_investment / qld_close
        else:  # Покупка QQQ
            total_units += weekly_investment / close

        total_invested += weekly_investment
        portfolio_value.append(total_units * close)
        dates.append(last_trading_day)

    return total_invested, portfolio_value, dates


def calculate_drawdown(portfolio_value):
    """Расчёт максимальной просадки."""
    if len(portfolio_value) == 0:
        return 0
    max_value = np.maximum.accumulate(portfolio_value)
    drawdown = (portfolio_value - max_value) / max_value
    return drawdown.min()


def calculate_roi(start_value, end_value, total_invested):
    """Расчёт ROI."""
    return (end_value - total_invested) / total_invested if total_invested > 0 else 0


def plot_results(simple_dates, simple_portfolio, test_dates, test_portfolio):
    """Отображение результатов стратегий."""
    plt.figure(figsize=(14, 7))
    plt.plot(simple_dates, simple_portfolio, label="Простая стратегия", alpha=0.7)
    plt.plot(test_dates, test_portfolio, label="Тестируемая стратегия", alpha=0.7)
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
    simple_invested, simple_portfolio, simple_dates = apply_simple_strategy(data, args.weekly_investment)
    test_invested, test_portfolio, test_dates = apply_test_strategy(data, args.weekly_investment)

    # Итоговые значения
    simple_end_value = simple_portfolio[-1] if simple_portfolio else 0
    test_end_value = test_portfolio[-1] if test_portfolio else 0

    # Вывод результатов
    print("=== Простая стратегия ===")
    print(f"Общая сумма вложений: ${simple_invested:.2f}")
    print(f"Итоговая стоимость портфеля: ${simple_end_value:.2f}")
    print(f"Итоговая прибыль: ${simple_end_value - simple_invested:.2f}")
    print(f"Максимальная просадка: {calculate_drawdown(simple_portfolio) * 100:.2f}%")
    print(f"ROI: {calculate_roi(0, simple_end_value, simple_invested) * 100:.2f}%")

    print("\n=== Тестируемая стратегия ===")
    print(f"Общая сумма вложений: ${test_invested:.2f}")
    print(f"Итоговая стоимость портфеля: ${test_end_value:.2f}")
    print(f"Итоговая прибыль: ${test_end_value - test_invested:.2f}")
    print(f"Максимальная просадка: {calculate_drawdown(test_portfolio) * 100:.2f}%")
    print(f"ROI: {calculate_roi(0, test_end_value, test_invested) * 100:.2f}%")

    # Отображение графика
    plot_results(simple_dates, simple_portfolio, test_dates, test_portfolio)



if __name__ == "__main__":
    main()
