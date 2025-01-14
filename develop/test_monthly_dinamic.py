# python3 script.py QQQ 1000 2020-01-01 2025-01-01
# QQQ — тикер акции.
# 1000 — сумма для еженедельного пополнения в $.
# 2020-01-01 — начальная дата периода тестирования.
# 2025-01-01 — конечная дата периода тестирования (опционально).

# pip install yfinance pandas numpy matplotlib

import yfinance as yf
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from datetime import datetime, timedelta
import sys

# Проверка и обработка аргументов командной строки
if len(sys.argv) < 4:
    print("Usage: python3 script.py <ticker> <weekly_investment> <start_date> [<end_date>]")
    sys.exit(1)

ticker = sys.argv[1]
weekly_investment = float(sys.argv[2])
start_date = sys.argv[3]
end_date = sys.argv[4] if len(sys.argv) > 4 else datetime.today().strftime("%Y-%m-%d")

# Загрузка исторических данных
data = yf.download(ticker, start=start_date, end=end_date)
data = data[["Close"]].reset_index()
data.columns = ["Date", "Close"]
data["DayOfWeek"] = data["Date"].dt.day_name()
data["Month"] = data["Date"].dt.to_period("M")

# Проверяем наличие данных
if data.empty:
    raise ValueError(f"Не удалось загрузить данные для тикера {ticker}. Проверьте подключение к интернету и корректность тикера.")

# Параметры стратегии
additional_investments = {
    -0.10: 2000,  # -10% от максимума
    -0.20: 3000,  # -20% от максимума
    -0.30: 4000,  # -30% от максимума
}

# Функция расчета стратегии

def apply_strategy(data):
    total_invested = 0
    total_units = 0
    max_price = 0
    portfolio_value = []
    monthly_investments = []

    for i, row in data.iterrows():
        date, close, day_of_week, month = row["Date"], row["Close"], row["DayOfWeek"], row["Month"]
        max_price = max(max_price, close)

        # Покупка на еженедельную сумму
        if day_of_week == "Monday":
            total_units += weekly_investment / close
            total_invested += weekly_investment

        # Дополнительные покупки при падении от максимума
        for threshold, amount in additional_investments.items():
            if close <= max_price * (1 + threshold):
                total_units += amount / close
                total_invested += amount
                break

        # Текущая стоимость портфеля
        portfolio_value.append(total_units * close)

        # Ежемесячное пополнение
        if len(monthly_investments) == 0 or monthly_investments[-1]["Month"] != month:
            monthly_investments.append({"Month": month, "Investment": total_invested})

    return total_invested, portfolio_value, monthly_investments

# Применение стратегии
total_invested, portfolio_value, monthly_investments = apply_strategy(data)
data["PortfolioValue"] = portfolio_value

# Максимальная просадка

def calculate_drawdown(portfolio_value):
    if len(portfolio_value) == 0:
        raise ValueError("Невозможно рассчитать просадку, так как список стоимости портфеля пуст.")

    max_value = np.maximum.accumulate(portfolio_value)
    drawdown = (portfolio_value - max_value) / max_value
    max_drawdown = drawdown.min()
    return max_drawdown

max_drawdown = calculate_drawdown(data["PortfolioValue"].values)

# Альтернативная стратегия: только $1000 каждый понедельник

def simple_strategy(data):
    total_invested = 0
    total_units = 0
    portfolio_value = []

    for i, row in data.iterrows():
        date, close, day_of_week = row["Date"], row["Close"], row["DayOfWeek"]
        if day_of_week == "Monday":
            total_units += weekly_investment / close
            total_invested += weekly_investment

        portfolio_value.append(total_units * close)

    return total_invested, portfolio_value

simple_invested, simple_portfolio = simple_strategy(data)
data["SimplePortfolio"] = simple_portfolio

# Результаты
print("=== Результаты стратегии ===")
print(f"Общая сумма вложений: ${total_invested:.2f}")
print(f"Максимальная просадка: {max_drawdown * 100:.2f}%")
print(f"Итоговая стоимость портфеля: ${data['PortfolioValue'].iloc[-1]:.2f}")

print("\nЕжемесячные пополнения:")
for entry in monthly_investments:
    print(f"{entry['Month']}: ${entry['Investment']:.2f}")

print("\n=== Простая стратегия ===")
print(f"Общая сумма вложений: ${simple_invested:.2f}")
print(f"Итоговая стоимость портфеля: ${data['SimplePortfolio'].iloc[-1]:.2f}")

# Построение графиков
plt.figure(figsize=(12, 6))
plt.plot(data["Date"], data["PortfolioValue"], label="Продвинутая стратегия")
plt.plot(data["Date"], data["SimplePortfolio"], label="Простая стратегия", linestyle="--")

# Добавление графика ежемесячных пополнений
monthly_dates = [entry['Month'].start_time for entry in monthly_investments]
monthly_values = [entry['Investment'] for entry in monthly_investments]
plt.step(monthly_dates, monthly_values, label="Ежемесячные пополнения", linestyle="-.", where='post')

plt.title("Сравнение стратегий")
plt.xlabel("Дата")
plt.ylabel("Стоимость портфеля, $")
plt.legend()
plt.grid()
plt.show()
