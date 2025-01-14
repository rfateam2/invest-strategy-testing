## python 0_test_3_3.py QQQ 1000 2023-01-01 --end_date 2024-12-31 --day_of_week Friday


import yfinance as yf
import pandas as pd
import numpy as np
import argparse
from datetime import datetime
import matplotlib.pyplot as plt
import os

def load_data(ticker, start_date, end_date):
    data = yf.download(ticker, start=start_date, end=end_date)
    data = data["Close"].reset_index()
    data.columns = ["Date", "Close"]
    data["DayOfWeek"] = data["Date"].dt.day_name()
    if data.empty:
        raise ValueError(f"Не удалось загрузить данные для тикера {ticker}.")
    return data

def apply_simple_strategy(data, weekly_investment, day_of_week):
    total_invested = 0
    total_units = 0
    portfolio_value = []
    monthly_investments = []

    for _, row in data.iterrows():
        date, close, day_name = row["Date"], row["Close"], row["DayOfWeek"]

        if day_name == day_of_week:
            total_units += weekly_investment / close
            total_invested += weekly_investment
            monthly_investments.append((date.strftime("%Y-%m"), weekly_investment))

        portfolio_value.append(total_units * close)

    return total_invested, portfolio_value, pd.DataFrame(monthly_investments, columns=["YearMonth", "Investment"])

def apply_test_strategy(data, weekly_investment, price_step, day_of_week):
    total_invested = 0
    total_units = 0
    max_price = 0
    portfolio_value = []
    monthly_investments = []

    for _, row in data.iterrows():
        date, close, day_name = row["Date"], row["Close"], row["DayOfWeek"]
        max_price = max(max_price, close)

        if day_name == day_of_week:
            total_units += weekly_investment / close
            total_invested += weekly_investment
            monthly_investments.append((date.strftime("%Y-%m"), weekly_investment))

        for threshold, multiplier in {0.10: 2, 0.20: 3, 0.30: 4}.items():
            if close <= max_price * (1 - threshold):
                extra_investment = weekly_investment * price_step * multiplier
                total_units += extra_investment / close
                total_invested += extra_investment
                monthly_investments.append((date.strftime("%Y-%m"), extra_investment))
                break

        portfolio_value.append(total_units * close)

    return total_invested, portfolio_value, pd.DataFrame(monthly_investments, columns=["YearMonth", "Investment"])

def calculate_drawdown(portfolio_value):
    if len(portfolio_value) == 0:
        return 0
    max_value = np.maximum.accumulate(portfolio_value)
    drawdown = np.where(max_value > 0, (portfolio_value - max_value) / max_value, 0)
    return drawdown.min() if len(drawdown) > 0 else 0

def calculate_roi(start_value, end_value, total_invested):
    return (end_value - total_invested) / total_invested if total_invested > 0 else 0

def plot_results(data, simple_values, test_values, simple_monthly, test_monthly):
    simple_monthly_totals = simple_monthly.groupby("YearMonth")["Investment"].sum().reset_index()
    simple_monthly_totals["YearMonth"] = pd.to_datetime(simple_monthly_totals["YearMonth"])

    test_monthly_totals = test_monthly.groupby("YearMonth")["Investment"].sum().reset_index()
    test_monthly_totals["YearMonth"] = pd.to_datetime(test_monthly_totals["YearMonth"])

    plt.figure(figsize=(14, 7))
    plt.plot(data["Date"], simple_values, label="Простая стратегия: Стоимость портфеля")
    plt.plot(data["Date"], test_values, label="Тестируемая стратегия: Стоимость портфеля")
    plt.bar(test_monthly_totals["YearMonth"], test_monthly_totals["Investment"], width=20, alpha=0.3, label="Тестируемая стратегия: Пополнения", color="orange")
    plt.title("Динамика стоимости портфеля и пополнений")
    plt.xlabel("Дата")
    plt.ylabel("Доллары ($)")
    plt.legend()
    plt.grid()
    plt.show()

def main():
    parser = argparse.ArgumentParser(description="Тестирование инвестиционных стратегий.")
    parser.add_argument("ticker", type=str, help="Тикер акции (например, QQQ).")
    parser.add_argument("weekly_investment", type=float, help="Сумма еженедельного пополнения в долларах.")
    parser.add_argument("start_date", type=str, help="Дата начала периода (YYYY-MM-DD).")
    parser.add_argument("--end_date", type=str, default=datetime.now().strftime("%Y-%m-%d"), help="Дата конца периода (YYYY-MM-DD).")
    parser.add_argument("--day_of_week", type=str, default="Friday", help="День недели для еженедельного пополнения.")
    parser.add_argument("--price_step", type=float, default=1.0, help="Шаг цены для расчёта дополнительных инвестиций.")
    args = parser.parse_args()

    data = load_data(args.ticker, args.start_date, args.end_date)

    simple_invested, simple_values, simple_monthly = apply_simple_strategy(data, args.weekly_investment, args.day_of_week)
    test_invested, test_values, test_monthly = apply_test_strategy(data, args.weekly_investment, args.price_step, args.day_of_week)

    simple_drawdown = calculate_drawdown(simple_values)
    test_drawdown = calculate_drawdown(test_values)

    simple_end_value = simple_values[-1] if simple_values else 0
    test_end_value = test_values[-1] if test_values else 0

    simple_roi = calculate_roi(0, simple_end_value, simple_invested)
    test_roi = calculate_roi(0, test_end_value, test_invested)

    simple_cagr = (1 + simple_roi) ** (1 / ((datetime.fromisoformat(args.end_date) - datetime.fromisoformat(args.start_date)).days / 365)) - 1
    test_cagr = (1 + test_roi) ** (1 / ((datetime.fromisoformat(args.end_date) - datetime.fromisoformat(args.start_date)).days / 365)) - 1

    report_path = os.path.join(os.getcwd(), "report.txt")
    with open(report_path, "w") as report_file:
        report_file.write(f"=== Простая стратегия ===\n")
        report_file.write(f"Общая сумма вложений: ${simple_invested:.2f}\n")
        report_file.write(f"Итоговая стоимость портфеля: ${simple_end_value:.2f}\n")
        report_file.write(f"Максимальная просадка: {simple_drawdown * 100:.2f}%\n")
        report_file.write(f"ROI: {simple_roi * 100:.2f}%\n")
        report_file.write(f"CAGR: {simple_cagr * 100:.2f}%\n\n")

        report_file.write(f"=== Тестируемая стратегия ===\n")
        report_file.write(f"Общая сумма вложений: ${test_invested:.2f}\n")
        report_file.write(f"Итоговая стоимость портфеля: ${test_end_value:.2f}\n")
        report_file.write(f"Максимальная просадка: {test_drawdown * 100:.2f}%\n")
        report_file.write(f"ROI: {test_roi * 100:.2f}%\n")
        report_file.write(f"CAGR: {test_cagr * 100:.2f}%\n\n")

        report_file.write("Ежемесячные вложения:\n")
        report_file.write(test_monthly.groupby("YearMonth")["Investment"].sum().to_string())

    print(f"Отчёт сохранён в {report_path}")

    plot_results(data, simple_values, test_values, simple_monthly, test_monthly)

if __name__ == "__main__":
    main()