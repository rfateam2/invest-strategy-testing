import yfinance as yf
import pandas as pd
import numpy as np
import argparse
from datetime import datetime
import matplotlib.pyplot as plt
import os


def load_data(ticker, start_date, end_date):
    """Загрузка данных о закрытии цен акций."""
    data = yf.download(ticker, start=start_date, end=end_date)
    if data.empty:
        raise ValueError(f"Не удалось загрузить данные для тикера {ticker}. Проверьте тикер и диапазон дат.")
    data = data[["Close"]].reset_index()
    data.columns = ["Date", "Close"]
    data["DayOfWeek"] = data["Date"].dt.day_name()
    return data


def apply_simple_strategy(data, weekly_investment, day_of_week):
    """Простая стратегия еженедельных инвестиций."""
    total_invested = 0
    total_units = 0
    portfolio_value = []
    monthly_investments = []

    for _, row in data.iterrows():
        date, close, day_name = row["Date"], row["Close"], row["DayOfWeek"]
        if day_name == day_of_week:
            units_bought = weekly_investment / close
            total_units += units_bought
            total_invested += weekly_investment
            monthly_investments.append((date.strftime("%Y-%m"), weekly_investment))
        portfolio_value.append(total_units * close)

    return total_invested, portfolio_value, pd.DataFrame(monthly_investments, columns=["YearMonth", "Investment"])


def apply_test_strategy(data, weekly_investment, multiplier, day_of_week):
    """Тестируемая стратегия с увеличением инвестиций на снижениях."""
    total_invested = 0
    total_units = 0
    max_price = 0
    portfolio_value = []
    monthly_investments = []

    for _, row in data.iterrows():
        date, close, day_name = row["Date"], row["Close"], row["DayOfWeek"]
        max_price = max(max_price, close)

        if day_name == day_of_week:
            units_bought = weekly_investment / close
            total_units += units_bought
            total_invested += weekly_investment
            monthly_investments.append((date.strftime("%Y-%m"), weekly_investment))

        if close <= max_price * (1 - 0.1):  # 10% снижение
            extra_investment = weekly_investment * multiplier
            units_bought = extra_investment / close
            total_units += units_bought
            total_invested += extra_investment
            monthly_investments.append((date.strftime("%Y-%m"), extra_investment))

        portfolio_value.append(total_units * close)

    return total_invested, portfolio_value, pd.DataFrame(monthly_investments, columns=["YearMonth", "Investment"])


def calculate_drawdown(portfolio_value):
    """Вычисление максимальной просадки портфеля."""
    max_value = np.maximum.accumulate(portfolio_value)
    drawdown = (portfolio_value - max_value) / max_value
    return drawdown.min()


def calculate_roi(end_value, total_invested):
    """Расчёт ROI."""
    return (end_value - total_invested) / total_invested if total_invested > 0 else 0


def plot_results(data, simple_values, test_values):
    """Построение графиков результатов."""
    plt.figure(figsize=(12, 6))
    plt.plot(data["Date"], simple_values, label="Простая стратегия", color="blue")
    plt.plot(data["Date"], test_values, label="Тестируемая стратегия", color="orange")
    plt.title("Результаты стратегий")
    plt.xlabel("Дата")
    plt.ylabel("Стоимость портфеля ($)")
    plt.legend()
    plt.grid()
    plt.show()


def main():
    parser = argparse.ArgumentParser(description="Тестирование инвестиционных стратегий.")
    parser.add_argument("ticker", type=str, help="Тикер акции (например, QQQ).")
    parser.add_argument("weekly_investment", type=float, help="Сумма еженедельного пополнения ($).")
    parser.add_argument("start_date", type=str, help="Дата начала (YYYY-MM-DD).")
    parser.add_argument("--end_date", type=str, default=datetime.now().strftime("%Y-%m-%d"), help="Дата окончания (YYYY-MM-DD).")
    parser.add_argument("--day_of_week", type=str, default="Friday", help="День недели для инвестиций (по умолчанию 'Friday').")
    parser.add_argument("--multiplier", type=float, default=1.5, help="Множитель для тестируемой стратегии.")
    args = parser.parse_args()

    # Загрузка данных
    data = load_data(args.ticker, args.start_date, args.end_date)

    # Применение стратегий
    simple_invested, simple_values, _ = apply_simple_strategy(data, args.weekly_investment, args.day_of_week)
    test_invested, test_values, _ = apply_test_strategy(data, args.weekly_investment, args.multiplier, args.day_of_week)

    # Расчёт метрик
    simple_end_value = simple_values[-1] if simple_values else 0
    test_end_value = test_values[-1] if test_values else 0
    simple_roi = calculate_roi(simple_end_value, simple_invested)
    test_roi = calculate_roi(test_end_value, test_invested)
    simple_drawdown = calculate_drawdown(simple_values)
    test_drawdown = calculate_drawdown(test_values)

    # Вывод результатов
    print(f"=== Простая стратегия ===")
    print(f"Итоговая стоимость: ${simple_end_value:.2f}")
    print(f"Общая вложенная сумма: ${simple_invested:.2f}")
    print(f"ROI: {simple_roi * 100:.2f}%")
    print(f"Максимальная просадка: {simple_drawdown * 100:.2f}%\n")

    print(f"=== Тестируемая стратегия ===")
    print(f"Итоговая стоимость: ${test_end_value:.2f}")
    print(f"Общая вложенная сумма: ${test_invested:.2f}")
    print(f"ROI: {test_roi * 100:.2f}%")
    print(f"Максимальная просадка: {test_drawdown * 100:.2f}%\n")

    # Построение графика
    plot_results(data, simple_values, test_values)


if __name__ == "__main__":
    main()
