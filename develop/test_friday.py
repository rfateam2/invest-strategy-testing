# python3 script.py QQQ 1000 2020-01-01 2025-01-01
# QQQ — тикер акции.
# 1000 — сумма для еженедельного пополнения в $.
# 2020-01-01 — начальная дата периода тестирования.
# 2025-01-01 — конечная дата периода тестирования (опционально).

# pip install yfinance pandas numpy matplotlib

import yfinance as yf
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import matplotlib.pyplot as plt
import argparse

# Параметры командной строки
parser = argparse.ArgumentParser(description="Инвестиционная стратегия.")
parser.add_argument("ticker", type=str, help="Тикер для анализа.")
parser.add_argument("weekly_investment", type=float, help="Сумма еженедельного пополнения в долларах.")
parser.add_argument("start_date", type=str, help="Дата начала периода (YYYY-MM-DD).")
parser.add_argument("--end_date", type=str, default=datetime.now().strftime("%Y-%m-%d"), help="Дата конца периода (YYYY-MM-DD), по умолчанию текущая дата.")
args = parser.parse_args()

# Загрузка исторических данных
start_date = args.start_date
end_date = args.end_date
ticker = args.ticker
weekly_investment = args.weekly_investment

data = yf.download(ticker, start=start_date, end=end_date)
data = data[["Close"]].reset_index()
data.columns = ["Date", "Close"]
data["DayOfWeek"] = data["Date"].dt.day_name()
data["YearMonth"] = data["Date"].dt.to_period("M")

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
        date, close, day_of_week, year_month = row["Date"], row["Close"], row["DayOfWeek"], row["YearMonth"]
        max_price = max(max_price, close)

        # Покупка на $1000 каждую Пятницу
        if day_of_week == "Friday":
            total_units += weekly_investment / close
            total_invested += weekly_investment
            monthly_investments.append((year_month, weekly_investment))

        # Дополнительные покупки при падении от максимума
        for threshold, amount in additional_investments.items():
            if close <= max_price * (1 + threshold):
                total_units += amount / close
                total_invested += amount
                monthly_investments.append((year_month, amount))
                break

        # Текущая стоимость портфеля
        portfolio_value.append(total_units * close)

    return total_invested, portfolio_value, monthly_investments

# Применение стратегии
total_invested, portfolio_value, monthly_investments = apply_strategy(data)
data["PortfolioValue"] = portfolio_value

# Проверяем, что значения портфеля рассчитаны
if not portfolio_value:
    raise ValueError("Значения портфеля не рассчитаны. Проверьте логику функции apply_strategy.")

# Максимальная просадка
def calculate_drawdown(portfolio_value):
    if len(portfolio_value) == 0:
        raise ValueError("Невозможно рассчитать просадку, так как список стоимости портфеля пуст.")

    max_value = np.maximum.accumulate(portfolio_value)
    drawdown = np.where(max_value > 0, (portfolio_value - max_value) / max_value, 0)
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

# Ежемесячные вложения
monthly_data = pd.DataFrame(monthly_investments, columns=["YearMonth", "Investment"])
monthly_summary = monthly_data.groupby("YearMonth")["Investment"].sum().reset_index()

# Результаты
print("=== Результаты стратегии ===")
print(f"Общая сумма вложений: ${total_invested:.2f}")
print(f"Максимальная просадка: {max_drawdown * 100:.2f}%")
print(f"Итоговая стоимость портфеля: ${data['PortfolioValue'].iloc[-1]:.2f}")
print("\nЕжемесячные вложения:")
print(monthly_summary)

print("\n=== Простая стратегия ===")
print(f"Общая сумма вложений: ${simple_invested:.2f}")
print(f"Итоговая стоимость портфеля: ${data['SimplePortfolio'].iloc[-1]:.2f}")

# Построение графиков
plt.figure(figsize=(12, 6))
plt.plot(data["Date"], data["PortfolioValue"], label="Продвинутая стратегия")
plt.plot(data["Date"], data["SimplePortfolio"], label="Простая стратегия", linestyle="--")
plt.bar(monthly_summary["YearMonth"].astype(str), monthly_summary["Investment"], alpha=0.3, label="Ежемесячные вложения")
plt.title(f"Сравнение стратегий и вложений ({ticker})")
plt.xlabel("Дата")
plt.ylabel("Стоимость портфеля, $")
plt.legend()
plt.grid()
plt.show()
