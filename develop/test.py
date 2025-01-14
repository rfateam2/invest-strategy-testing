# python3 script.py QQQ 1000 2020-01-01 2025-01-01
# QQQ — тикер акции.
# 1000 — сумма для еженедельного пополнения в $.
# 2020-01-01 — начальная дата периода тестирования.
# 2025-01-01 — конечная дата периода тестирования (опционально).

# pip install yfinance pandas numpy matplotlib

import yfinance as yf
import pandas as pd
import numpy as np
import argparse
from datetime import datetime

# Парсинг аргументов командной строки
parser = argparse.ArgumentParser(description="Backtesting investment strategy.")
parser.add_argument("ticker", type=str, help="Тикер акции для анализа.")
parser.add_argument("weekly_investment", type=float, help="Сумма для еженедельного пополнения, в долларах.")
parser.add_argument("start_date", type=str, help="Дата начала периода тестирования (в формате YYYY-MM-DD).")
parser.add_argument("end_date", type=str, nargs="?", default=datetime.now().strftime("%Y-%m-%d"), help="Дата конца периода тестирования (в формате YYYY-MM-DD, по умолчанию - текущая дата).")
args = parser.parse_args()

# Загрузка исторических данных
start_date = args.start_date
end_date = args.end_date
ticker = args.ticker
weekly_investment = args.weekly_investment

try:
    data = yf.download(ticker, start=start_date, end=end_date)
    data = data[["Close"]].reset_index()
    data.columns = ["Date", "Close"]
    data["DayOfWeek"] = data["Date"].dt.day_name()
except Exception as e:
    raise ValueError(f"Ошибка при загрузке данных для тикера {ticker}: {e}")

# Проверяем наличие данных
if data.empty:
    raise ValueError("Не удалось загрузить данные для тикера. Проверьте подключение к интернету и корректность тикера.")

# Параметры стратегии
initial_investment = weekly_investment
additional_investments = {
    -0.10: weekly_investment * 2,  # -10% от максимума
    -0.20: weekly_investment * 3,  # -20% от максимума
    -0.30: weekly_investment * 4,  # -30% от максимума
}

# Функция расчета стратегии
def apply_strategy(data):
    total_invested = 0
    total_units = 0
    max_price = 0
    portfolio_value = []

    for i, row in data.iterrows():
        date, close, day_of_week = row["Date"], row["Close"], row["DayOfWeek"]
        # Обновляем максимальную цену
        max_price = max(max_price, close)

        # Покупка на weekly_investment каждый понедельник
        if day_of_week == "Monday":
            total_units += initial_investment / close
            total_invested += initial_investment

        # Дополнительные покупки при падении от максимума
        for threshold, amount in additional_investments.items():
            if close <= max_price * (1 + threshold):
                total_units += amount / close
                total_invested += amount
                break

        # Текущая стоимость портфеля
        portfolio_value.append(total_units * close)

    return total_invested, portfolio_value

# Применение стратегии
total_invested, portfolio_value = apply_strategy(data)
data["PortfolioValue"] = portfolio_value

# Проверяем, что значения портфеля рассчитаны
if not portfolio_value:
    raise ValueError("Значения портфеля не рассчитаны. Проверьте логику функции apply_strategy.")

# Максимальная просадка
def calculate_drawdown(portfolio_value):
    if len(portfolio_value) == 0:
        raise ValueError("Невозможно рассчитать просадку, так как список стоимости портфеля пуст.")

    max_value = np.maximum.accumulate(portfolio_value)
    with np.errstate(divide='ignore', invalid='ignore'):
        drawdown = np.where(max_value > 0, (portfolio_value - max_value) / max_value, 0)
    max_drawdown = drawdown.min()
    return max_drawdown

max_drawdown = calculate_drawdown(data["PortfolioValue"].values)

# Альтернативная стратегия: только weekly_investment каждый понедельник
def simple_strategy(data):
    total_invested = 0
    total_units = 0
    portfolio_value = []

    for i, row in data.iterrows():
        date, close, day_of_week = row["Date"], row["Close"], row["DayOfWeek"]
        if day_of_week == "Monday":
            total_units += initial_investment / close
            total_invested += initial_investment

        portfolio_value.append(total_units * close)

    return total_invested, portfolio_value

simple_invested, simple_portfolio = simple_strategy(data)
data["SimplePortfolio"] = simple_portfolio

# Результаты
print("=== Результаты стратегии ===")
print(f"Общая сумма вложений: ${total_invested:.2f}")
print(f"Максимальная просадка: {max_drawdown * 100:.2f}%")
print(f"Итоговая стоимость портфеля: ${data['PortfolioValue'].iloc[-1]:.2f}")

print("\n=== Простая стратегия ===")
print(f"Общая сумма вложений: ${simple_invested:.2f}")
print(f"Итоговая стоимость портфеля: ${data['SimplePortfolio'].iloc[-1]:.2f}")

# Построение графиков
import matplotlib.pyplot as plt
plt.figure(figsize=(12, 6))
plt.plot(data["Date"], data["PortfolioValue"], label="Продвинутая стратегия")
plt.plot(data["Date"], data["SimplePortfolio"], label="Простая стратегия", linestyle="--")
plt.title("Сравнение стратегий")
plt.xlabel("Дата")
plt.ylabel("Стоимость портфеля, $")
plt.legend()
plt.grid()
plt.show()
