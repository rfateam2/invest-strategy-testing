# python3 script.py QQQ 1000 2020-01-01 Friday 1 --end_date 2025-01-01
# QQQ — тикер акции.
# 1000 — сумма для еженедельного пополнения в $.
# 2020-01-01 — начальная дата периода тестирования.
# 2025-01-01 — конечная дата периода тестирования (опционально).

# python3 -m venv path/to/venv                                                                                     
# source path/to/venv/bin/activate
# pip install yfinance pandas numpy matplotlib
# python3 test_monthly_dinamic.py QQQ 1000 2020-01-01 --end_date 2025-01-01 --day_of_week Monday --price_step 1.5


import yfinance as yf
import pandas as pd
import numpy as np
from datetime import datetime
import matplotlib.pyplot as plt
import argparse
import os

# Аргументы командной строки
parser = argparse.ArgumentParser(description="Тестирование инвестиционной стратегии.")
parser.add_argument("ticker", type=str, help="Тикер актива.")
parser.add_argument("weekly_investment", type=float, help="Сумма еженедельного пополнения в долларах.")
parser.add_argument("start_date", type=str, help="Дата начала периода (в формате YYYY-MM-DD).")
parser.add_argument("--end_date", type=str, default=datetime.now().strftime("%Y-%m-%d"), help="Дата конца периода (в формате YYYY-MM-DD). По умолчанию текущая дата.")
parser.add_argument("--day_of_week", type=str, default="Friday", help="День недели для еженедельных инвестиций. По умолчанию Friday.")
parser.add_argument("--price_step", type=float, default=1, help="Шаг цены для расчёта дополнительных инвестиций. По умолчанию 1.")
args = parser.parse_args()

# Загрузка данных
start_date = args.start_date
end_date = args.end_date
ticker = args.ticker
weekly_investment = args.weekly_investment
day_of_week = args.day_of_week
price_step = args.price_step

data = yf.download(ticker, start=start_date, end=end_date)
data = data["Close"].reset_index()
data.columns = ["Date", "Close"]
data["DayOfWeek"] = data["Date"].dt.day_name()

if data.empty:
    raise ValueError(f"Не удалось загрузить данные для тикера {ticker}.")

# Параметры стратегии
additional_investments = {
    -0.10: weekly_investment * price_step * 2,
    -0.20: weekly_investment * price_step * 3,
    -0.30: weekly_investment * price_step * 4,
}

def apply_strategy(data):
    total_invested = 0
    total_units = 0
    max_price = 0
    portfolio_value = []
    monthly_investments = []

    for i, row in data.iterrows():
        date, close, dow = row["Date"], row["Close"], row["DayOfWeek"]
        max_price = max(max_price, close)
        
        if dow == day_of_week:
            total_units += weekly_investment / close
            total_invested += weekly_investment
            monthly_investments.append((date.strftime("%Y-%m"), weekly_investment))

        for threshold, amount in additional_investments.items():
            if close <= max_price * (1 + threshold):
                total_units += amount / close
                total_invested += amount
                monthly_investments.append((date.strftime("%Y-%m"), amount))
                break

        portfolio_value.append(total_units * close)

    return total_invested, portfolio_value, monthly_investments

def calculate_drawdown(portfolio_value):
    max_value = np.maximum.accumulate(portfolio_value)
    drawdown = (portfolio_value - max_value) / max_value
    return drawdown.min()

def simple_strategy(data):
    total_invested = 0
    total_units = 0
    portfolio_value = []

    for i, row in data.iterrows():
        date, close, dow = row["Date"], row["Close"], row["DayOfWeek"]
        if dow == day_of_week:
            total_units += weekly_investment / close
            total_invested += weekly_investment

        portfolio_value.append(total_units * close)

    return total_invested, portfolio_value

def calculate_cagr(start_value, end_value, start_date, end_date):
    years = (end_date - start_date).days / 365.25
    return (end_value / start_value) ** (1 / years) - 1

def write_report(filename, simple_report, advanced_report, monthly_data):
    with open(filename, "w") as f:
        f.write(simple_report)
        f.write("\n\n")
        f.write(advanced_report)
        f.write("\n\nЕжемесячные вложения:\n")
        f.write(monthly_data.to_string(index=False))

# Применение стратегий
start_dt = datetime.strptime(start_date, "%Y-%m-%d")
end_dt = datetime.strptime(end_date, "%Y-%m-%d")

total_invested_simple, simple_portfolio = simple_strategy(data)
total_invested_advanced, advanced_portfolio, monthly_investments = apply_strategy(data)

# Подготовка данных
monthly_data = pd.DataFrame(monthly_investments, columns=["YearMonth", "Investment"]).groupby("YearMonth").sum().reset_index()

simple_drawdown = calculate_drawdown(simple_portfolio)
advanced_drawdown = calculate_drawdown(advanced_portfolio)

simple_cagr = calculate_cagr(total_invested_simple, simple_portfolio[-1], start_dt, end_dt)
advanced_cagr = calculate_cagr(total_invested_advanced, advanced_portfolio[-1], start_dt, end_dt)

simple_units = total_invested_simple / data["Close"].iloc[-1]
advanced_units = total_invested_advanced / data["Close"].iloc[-1]

# Формирование отчета
simple_report = f"""=== Простая стратегия ===
Сумма еженедельного пополнения в долларах: {weekly_investment}. Тикер: {ticker}
Общая сумма вложений: ${total_invested_simple:.2f}
Итоговая стоимость портфеля: ${simple_portfolio[-1]:.2f}
Количество акций в портфеле на конец периода: {simple_units:.4f}
Прибыль на конец периода без учета дивидендов: ${simple_portfolio[-1] - total_invested_simple:.2f}
Возврат от инвестиций без учета дивидендов за весь период: {((simple_portfolio[-1] / total_invested_simple) - 1) * 100:.2f}%
Максимальная просадка: {simple_drawdown * 100:.2f}%
Среднегодовой Возврат от инвестиций за период без учета дивидендов (CAGR): {simple_cagr * 100:.2f}%"""

advanced_report = f"""=== Результаты стратегии Тестовой стратегии ===
Сумма еженедельного пополнения в долларах: {weekly_investment}. Тикер: {ticker}
Общая сумма вложений: ${total_invested_advanced:.2f}
Итоговая стоимость портфеля: ${advanced_portfolio[-1]:.2f}
Количество акций в портфеле на конец периода: {advanced_units:.4f}
Прибыль на конец периода без учета дивидендов: ${advanced_portfolio[-1] - total_invested_advanced:.2f}
Возврат от инвестиций без учета дивидендов за весь период: {((advanced_portfolio[-1] / total_invested_advanced) - 1) * 100:.2f}%
Максимальная просадка: {advanced_drawdown * 100:.2f}%
Среднегодовой Возврат от инвестиций за период без учета дивидендов (CAGR): {advanced_cagr * 100:.2f}%"""

write_report("report.txt", simple_report, advanced_report, monthly_data)

print(simple_report)
print("\n\n" + advanced_report)
print("\n\nЕжемесячные вложения:\n")
print(monthly_data)

# Построение графиков
plt.figure(figsize=(12, 8))
plt.plot(data["Date"], simple_portfolio, label="Простая стратегия")
plt.plot(data["Date"], advanced_portfolio, label="Тестовая стратегия")
plt.bar(pd.to_datetime(monthly_data["YearMonth"] + "-01"), monthly_data["Investment"], width=20, alpha=0.5, label="Ежемесячные вложения")
plt.title("Сравнение стратегий и динамика вложений")
plt.xlabel("Дата")
plt.ylabel("Стоимость портфеля, $")
plt.legend()
plt.grid()
plt.show()
