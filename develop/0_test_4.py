# python3 0_test_4.py --ticker QQQ --weekly 1000 --start_date 2020-01-01 --end_date 2024-12-31 --day_of_week Friday


import yfinance as yf
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from datetime import datetime, timedelta
import argparse
import os

# Расчет максимальной просадки
def calculate_drawdown(portfolio_value):
    max_value = np.maximum.accumulate(portfolio_value)
    drawdown = np.where(max_value > 0, (portfolio_value - max_value) / max_value, 0)
    return drawdown.min()

# Расчет CAGR
def calculate_cagr(start_value, end_value, start_date, end_date):
    years = (end_date - start_date).days / 365.25
    return ((end_value / start_value) ** (1 / years) - 1) * 100 if years > 0 else 0

# Применение стратегии
def apply_strategy(data, weekly_amount, step_price, day_of_week):
    total_invested = 0
    total_units = 0
    max_price = 0
    portfolio_value = []
    monthly_totals = []

    for i, row in data.iterrows():
        date, close, dow = row["Date"], row["Close"], row["DayOfWeek"]
        max_price = max(max_price, close)

        # Еженедельные вложения
        if dow == day_of_week:
            total_units += weekly_amount / close
            total_invested += weekly_amount

        # Покупки при падении цены
        if close <= max_price * (1 - 0.10):
            total_units += (weekly_amount * step_price * 2) / close
            total_invested += weekly_amount * step_price * 2
        elif close <= max_price * (1 - 0.20):
            total_units += (weekly_amount * step_price * 3) / close
            total_invested += weekly_amount * step_price * 3
        elif close <= max_price * (1 - 0.30):
            total_units += (weekly_amount * step_price * 4) / close
            total_invested += weekly_amount * step_price * 4

        portfolio_value.append(total_units * close)

        # Ежемесячные данные
        if i == len(data) - 1 or (i + 1 < len(data) and data.iloc[i + 1]["Date"].month != date.month):
            monthly_totals.append((date.strftime("%Y-%m"), total_invested))

    return total_invested, portfolio_value, monthly_totals

# Простая стратегия
def simple_strategy(data, weekly_amount, day_of_week):
    total_invested = 0
    total_units = 0
    portfolio_value = []

    # Сброс индекса и убедимся, что DayOfWeek содержит строки
    if isinstance(data.index, pd.MultiIndex):
        data = data.reset_index()
    data["DayOfWeek"] = data["DayOfWeek"].astype(str)

    for idx, row in data.iterrows():
        date = row["Date"]
        close = row["Close"]
        dow = row["DayOfWeek"]  # Это строка
        
        # Проверка совпадения с днем недели
        if dow == day_of_week:
            total_units += weekly_amount / close
            total_invested += weekly_amount
        
        portfolio_value.append(total_units * close)

    return total_invested, portfolio_value



# Построение графика
def plot_results(data, strategy_name, portfolio_value):
    plt.plot(data["Date"], portfolio_value, label=f"{strategy_name}: Доходность")
    plt.xlabel("Дата")
    plt.ylabel("Стоимость портфеля, $")
    plt.title("Сравнение стратегий")
    plt.legend()
    plt.grid()

# Основная функция
def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--ticker", required=True, help="Тикер акции")
    parser.add_argument("--weekly", type=float, required=True, help="Сумма еженедельного пополнения")
    parser.add_argument("--start_date", required=True, help="Дата начала в формате YYYY-MM-DD")
    parser.add_argument("--end_date", default=datetime.today().strftime("%Y-%m-%d"), help="Дата конца")
    parser.add_argument("--day_of_week", default="Friday", help="День недели для пополнений (по умолчанию: Friday)")
    parser.add_argument("--step_price", type=float, default=1, help="Шаг цены (по умолчанию: 1)")
    args = parser.parse_args()

    # Загрузка данных
    data = yf.download(args.ticker, start=args.start_date, end=args.end_date)
    data = data[["Close"]].reset_index()
    data["DayOfWeek"] = data["Date"].dt.day_name()
    print(data.head())  # Отладочный вывод для проверки данных
    if data.empty:
        raise ValueError(f"Нет данных для тикера {args.ticker}.")
    

    # Применение стратегий
    total_invested_simple, simple_portfolio = simple_strategy(data, args.weekly, args.day_of_week)
    total_invested_test, test_portfolio, monthly_totals = apply_strategy(
        data, args.weekly, args.step_price, args.day_of_week
    )

    # Подготовка отчета
    max_drawdown_simple = calculate_drawdown(simple_portfolio)
    max_drawdown_test = calculate_drawdown(test_portfolio)
    cagr_simple = calculate_cagr(total_invested_simple, simple_portfolio[-1], pd.to_datetime(args.start_date), pd.to_datetime(args.end_date))
    cagr_test = calculate_cagr(total_invested_test, test_portfolio[-1], pd.to_datetime(args.start_date), pd.to_datetime(args.end_date))

    with open("report.txt", "w") as f:
        f.write(f"=== Простая стратегия ===\n")
        f.write(f"Общая сумма вложений: ${total_invested_simple:.2f}\n")
        f.write(f"Итоговая стоимость портфеля: ${simple_portfolio[-1]:.2f}\n")
        f.write(f"Максимальная просадка: {max_drawdown_simple * 100:.2f}%\n")
        f.write(f"CAGR: {cagr_simple:.2f}%\n\n")

        f.write(f"=== Тестируемая стратегия ===\n")
        f.write(f"Общая сумма вложений: ${total_invested_test:.2f}\n")
        f.write(f"Итоговая стоимость портфеля: ${test_portfolio[-1]:.2f}\n")
        f.write(f"Максимальная просадка: {max_drawdown_test * 100:.2f}%\n")
        f.write(f"CAGR: {cagr_test:.2f}%\n\n")

        f.write("Ежемесячные вложения:\n")
        for month, amount in monthly_totals:
            f.write(f"{month}: ${amount:.2f}\n")

    # Краткий отчет в терминал
    print(f"=== Тестируемая стратегия ===")
    print(f"Общая сумма вложений: ${total_invested_test:.2f}")
    print(f"Итоговая стоимость портфеля: ${test_portfolio[-1]:.2f}")
    print(f"Максимальная просадка: {max_drawdown_test * 100:.2f}%")
    print(f"CAGR: {cagr_test:.2f}%")

    # Построение графиков
    plt.figure(figsize=(12, 6))
    plot_results(data, "Простая стратегия", simple_portfolio)
    plot_results(data, "Тестируемая стратегия", test_portfolio)
    plt.show()

if __name__ == "__main__":
    main()
