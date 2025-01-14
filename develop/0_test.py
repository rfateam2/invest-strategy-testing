# python3 script.py QQQ 1000 2020-01-01 Friday 1 --end_date 2025-01-01
# QQQ — тикер акции.
# 1000 — сумма для еженедельного пополнения в $.
# 2020-01-01 — начальная дата периода тестирования.
# 2025-01-01 — конечная дата периода тестирования (опционально).

# pip install yfinance pandas numpy matplotlib

import yfinance as yf
import pandas as pd
import numpy as np
from datetime import datetime
import argparse
import matplotlib.pyplot as plt

# Аргументы командной строки
parser = argparse.ArgumentParser(description="Инвестиционная стратегия.")
parser.add_argument("ticker", type=str, help="Тикер акций.")
parser.add_argument("weekly_amount", type=float, help="Сумма еженедельного пополнения в долларах.")
parser.add_argument("start_date", type=str, help="Дата начала периода в формате YYYY-MM-DD.")
parser.add_argument("--end_date", type=str, default=datetime.now().strftime("%Y-%m-%d"), help="Дата конца периода в формате YYYY-MM-DD. По умолчанию текущая дата.")
parser.add_argument("--day_of_week", type=str, default="Friday", help="День недели для регулярного пополнения. По умолчанию Friday.")
parser.add_argument("--price_step", type=float, default=1, help="Шаг цены для дополнительного инвестирования. По умолчанию 1.")
args = parser.parse_args()

# Загрузка данных
start_date = args.start_date
end_date = args.end_date
ticker = args.ticker
weekly_amount = args.weekly_amount
day_of_week = args.day_of_week
price_step = args.price_step

data = yf.download(ticker, start=start_date, end=end_date)
data = data[["Close"]].reset_index()
data.columns = ["Date", "Close"]
data["DayOfWeek"] = data["Date"].dt.day_name()

if data.empty:
    raise ValueError(f"Не удалось загрузить данные для тикера {ticker}. Проверьте подключение к интернету и корректность тикера.")

# Параметры стратегии
additional_investments = {
    -0.10: 2 * price_step,  # -10% от максимума
    -0.20: 3 * price_step,  # -20% от максимума
    -0.30: 4 * price_step,  # -30% от максимума
}

# Функция расчета стратегии
def apply_strategy(data, weekly_amount, day_of_week):
    total_invested = 0
    total_units = 0
    max_price = 0
    portfolio_value = []
    monthly_investments = []

    for i, row in data.iterrows():
        date, close, day = row["Date"], row["Close"], row["DayOfWeek"]
        max_price = max(max_price, close)

        # Еженедельные покупки
        if day == day_of_week:
            total_units += weekly_amount / close
            total_invested += weekly_amount
            monthly_investments.append((date.strftime("%Y-%m"), weekly_amount))

        # Дополнительные покупки при падении цены
        for threshold, multiplier in additional_investments.items():
            if close <= max_price * (1 + threshold):
                extra_amount = weekly_amount * multiplier
                total_units += extra_amount / close
                total_invested += extra_amount
                monthly_investments.append((date.strftime("%Y-%m"), extra_amount))
                break

        portfolio_value.append(total_units * close)

    monthly_df = pd.DataFrame(monthly_investments, columns=["Month", "Amount"])
    monthly_df = monthly_df.groupby("Month")["Amount"].sum().reset_index()
    return total_invested, portfolio_value, total_units, monthly_df

# Простая стратегия
def simple_strategy(data, weekly_amount, day_of_week):
    total_invested = 0
    total_units = 0
    portfolio_value = []

    for i, row in data.iterrows():
        date, close, day = row["Date"], row["Close"], row["DayOfWeek"]
        if day == day_of_week:
            total_units += weekly_amount / close
            total_invested += weekly_amount

        portfolio_value.append(total_units * close)

    return total_invested, portfolio_value, total_units

# Вычисление стратегий
total_invested, portfolio_value, total_units, monthly_df = apply_strategy(data, weekly_amount, day_of_week)
simple_invested, simple_portfolio, simple_units = simple_strategy(data, weekly_amount, day_of_week)

# Максимальная просадка
def calculate_drawdown(portfolio_value):
    max_value = np.maximum.accumulate(portfolio_value)
    drawdown = np.where(max_value == 0, 0, (portfolio_value - max_value) / max_value)
    max_drawdown = drawdown.min()
    return max_drawdown

max_drawdown = calculate_drawdown(portfolio_value)
simple_drawdown = calculate_drawdown(simple_portfolio)

# Итоги
final_price = data["Close"].iloc[-1]
test_strategy_final_value = total_units * final_price
simple_strategy_final_value = simple_units * final_price

def calculate_cagr(initial_investment, final_value, start_date, end_date):
    years = (datetime.strptime(end_date, "%Y-%m-%d") - datetime.strptime(start_date, "%Y-%m-%d")).days / 365.25
    cagr = (final_value / initial_investment) ** (1 / years) - 1
    return cagr

test_strategy_cagr = calculate_cagr(total_invested, test_strategy_final_value, start_date, end_date)
simple_strategy_cagr = calculate_cagr(simple_invested, simple_strategy_final_value, start_date, end_date)

# Отчет
print("=== Результаты Продвинутой стратегии ===")
print(f"Общая сумма вложений: ${total_invested:.2f}")
print(f"Максимальная просадка: {max_drawdown * 100:.2f}%")
print(f"Количество акций на конец тестирования: {total_units:.2f}")
print(f"Итоговая стоимость портфеля: ${test_strategy_final_value:.2f}")
print(f"Среднегодовой возврат: {test_strategy_cagr * 100:.2f}%")
print("Ежемесячные пополнения:")
print(monthly_df)

print("\n=== Результаты Простой стратегии ===")
print(f"Общая сумма вложений: ${simple_invested:.2f}")
print(f"Максимальная просадка: {simple_drawdown * 100:.2f}%")
print(f"Количество акций на конец тестирования: {simple_units:.2f}")
print(f"Итоговая стоимость портфеля: ${simple_strategy_final_value:.2f}")
print(f"Среднегодовой возврат: {simple_strategy_cagr * 100:.2f}%")

# Графики
plt.figure(figsize=(14, 8))
plt.plot(data["Date"], portfolio_value, label="Продвинутая стратегия")
plt.plot(data["Date"], simple_portfolio, label="Простая стратегия", linestyle="--")
plt.bar(monthly_df["Month"], monthly_df["Amount"], alpha=0.5, label="Ежемесячные пополнения", color="orange")
plt.title("Сравнение стратегий и динамика пополнений")
plt.xlabel("Дата")
plt.ylabel("Стоимость портфеля, $")
plt.legend()
plt.grid()
plt.show()
