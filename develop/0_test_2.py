# python3 script.py QQQ 1000 2020-01-01 Friday 1 --end_date 2025-01-01
# QQQ — тикер акции.
# 1000 — сумма для еженедельного пополнения в $.
# 2020-01-01 — начальная дата периода тестирования.
# 2025-01-01 — конечная дата периода тестирования (опционально).

# pip install yfinance pandas numpy matplotlib
# python3 script.py QQQ 100 2023-01-01 --end_date 2024-12-31 --day_of_week Friday --price_step 1.5


import yfinance as yf
import pandas as pd
import numpy as np
import argparse
from datetime import datetime, timedelta
import matplotlib.pyplot as plt
import os

# Функция для загрузки данных
def load_data(ticker, start_date, end_date):
    data = yf.download(ticker, start=start_date, end=end_date)
    data = data[["Close"]].reset_index()
    data.columns = ["Date", "Close"]
    data["DayOfWeek"] = data["Date"].dt.day_name()
    if data.empty:
        raise ValueError(f"Не удалось загрузить данные для тикера {ticker}. Проверьте тикер или подключение к интернету.")
    return data

# Функция расчёта стратегии
def apply_strategy(data, weekly_investment, price_step, day_of_week):
    total_invested = 0
    total_units = 0
    max_price = 0
    portfolio_value = []
    monthly_investments = []

    for i, row in data.iterrows():
        date, close, day_name = row["Date"], row["Close"], row["DayOfWeek"]
        max_price = max(max_price, close)

        # Еженедельное пополнение
        if day_name == day_of_week:
            total_units += weekly_investment / close
            total_invested += weekly_investment
            monthly_investments.append((date.strftime("%Y-%m"), weekly_investment))

        # Дополнительные покупки
        for threshold, multiplier in {0.10: 2, 0.20: 3, 0.30: 4}.items():
            if close <= max_price * (1 - threshold):
                extra_investment = weekly_investment * price_step * multiplier
                total_units += extra_investment / close
                total_invested += extra_investment
                monthly_investments.append((date.strftime("%Y-%m"), extra_investment))
                break

        portfolio_value.append(total_units * close)

    return total_invested, portfolio_value, pd.DataFrame(monthly_investments, columns=["YearMonth", "Investment"])

# Функция расчёта максимальной просадки
def calculate_drawdown(portfolio_value):
    if len(portfolio_value) == 0:
        return 0
    max_value = np.maximum.accumulate(portfolio_value)
    drawdown = np.where(max_value > 0, (portfolio_value - max_value) / max_value, 0)
    return drawdown.min() if len(drawdown) > 0 else 0

# Функция расчёта ROI
def calculate_roi(start_value, end_value, total_invested):
    return (end_value - total_invested) / total_invested if total_invested > 0 else 0

# Функция для построения графиков
def plot_results(data, strategy_name, portfolio_values, monthly_data):
    # Агрегирование инвестиций по месяцам
    monthly_totals = monthly_data.groupby("YearMonth")["Investment"].sum().reset_index()
    monthly_totals["YearMonth"] = pd.to_datetime(monthly_totals["YearMonth"])
    
    plt.figure(figsize=(14, 7))
    plt.plot(data["Date"], portfolio_values, label=f"{strategy_name}: Стоимость портфеля")
    plt.bar(monthly_totals["YearMonth"], monthly_totals["Investment"], width=20, alpha=0.3, label=f"{strategy_name}: Пополнения", color="orange")
    plt.title(f"{strategy_name} - Динамика стоимости портфеля и пополнений")
    plt.xlabel("Дата")
    plt.ylabel("Доллары ($)")
    plt.legend()
    plt.grid()
    plt.show()

# Основная функция
def main():
    parser = argparse.ArgumentParser(description="Тестирование инвестиционных стратегий.")
    parser.add_argument("ticker", type=str, help="Тикер акции (например, QQQ).")
    parser.add_argument("weekly_investment", type=float, help="Сумма еженедельного пополнения в долларах.")
    parser.add_argument("start_date", type=str, help="Дата начала периода (YYYY-MM-DD).")
    parser.add_argument("--end_date", type=str, default=datetime.now().strftime("%Y-%m-%d"), help="Дата конца периода (YYYY-MM-DD).")
    parser.add_argument("--day_of_week", type=str, default="Friday", help="День недели для еженедельного пополнения.")
    parser.add_argument("--price_step", type=float, default=1.0, help="Шаг цены для расчёта дополнительных инвестиций.")
    args = parser.parse_args()

    # Загрузка данных
    data = load_data(args.ticker, args.start_date, args.end_date)

    # Расчёт стратегии
    total_invested, portfolio_value, monthly_data = apply_strategy(data, args.weekly_investment, args.price_step, args.day_of_week)
    max_drawdown = calculate_drawdown(portfolio_value)
    end_value = portfolio_value[-1] if portfolio_value else 0
    roi = calculate_roi(0, end_value, total_invested)
    cagr = (1 + roi) ** (1 / ((datetime.fromisoformat(args.end_date) - datetime.fromisoformat(args.start_date)).days / 365)) - 1

    # Создание отчёта
    report_path = os.path.join(os.getcwd(), "report.txt")
    with open(report_path, "w") as report_file:
        report_file.write(f"=== Стратегия {args.ticker} ===\n")
        report_file.write(f"Общая сумма вложений: ${total_invested:.2f}\n")
        report_file.write(f"Итоговая стоимость портфеля: ${end_value:.2f}\n")
        report_file.write(f"Максимальная просадка: {max_drawdown * 100:.2f}%\n")
        report_file.write(f"ROI: {roi * 100:.2f}%\n")
        report_file.write(f"CAGR: {cagr * 100:.2f}%\n\n")
        report_file.write("Ежемесячные вложения:\n")
        report_file.write(monthly_data.to_string(index=False))
    print(f"Отчёт сохранён в {report_path}")

    # Построение графиков
    plot_results(data, "Тестируемая стратегия", portfolio_value, monthly_data)

if __name__ == "__main__":
    main()
