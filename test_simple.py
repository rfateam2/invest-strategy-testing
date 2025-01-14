# python3 -m venv path/to/venv                                                                                     
# source path/to/venv/bin/activate
# pip install yfinance pandas numpy matplotlib
# python test_simple.py QQQ 100 2024-01-01 --end_date 2024-12-31

import yfinance as yf
import pandas as pd
import numpy as np
import argparse
from datetime import datetime
import matplotlib.pyplot as plt
import os

def load_data(ticker, start_date, end_date):
    data = yf.download(ticker, start=start_date, end=end_date)
    if data.empty:
        raise ValueError(f"Не удалось загрузить данные для тикера {ticker}. Проверьте тикер и диапазон дат.")
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

def calculate_drawdown(portfolio_value):
    if len(portfolio_value) == 0:
        return 0
    max_value = np.maximum.accumulate(portfolio_value)
    # Избегаем деления на ноль
    with np.errstate(divide='ignore', invalid='ignore'):
        drawdown = np.where(max_value > 0, (portfolio_value - max_value) / max_value, 0)
    return drawdown.min() if len(drawdown) > 0 else 0


def calculate_roi(start_value, end_value, total_invested):
    return (end_value - total_invested) / total_invested if total_invested > 0 else 0

def plot_results(data, simple_values, simple_monthly):
    simple_monthly_totals = simple_monthly.groupby("YearMonth")["Investment"].sum().reset_index()
    simple_monthly_totals["YearMonth"] = pd.to_datetime(simple_monthly_totals["YearMonth"])

    plt.figure(figsize=(14, 7))
    # plt.xticks(rotation=45)
    # plt.tight_layout()
    plt.plot(data["Date"], simple_values, label="Простая стратегия: Стоимость портфеля")
    plt.title("Динамика стоимости портфеля и пополнений")
    plt.xlabel("Дата")
    plt.ylabel("Доллары ($)")
    plt.legend()
    plt.grid()
    plt.show()
    # plt.savefig("portfolio_performance.png")

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
    simple_drawdown = calculate_drawdown(simple_values)
    simple_end_value = simple_values[-1] if simple_values else 0
    simple_roi = calculate_roi(0, simple_end_value, simple_invested)
    simple_cagr = (1 + simple_roi) ** (1 / ((datetime.fromisoformat(args.end_date) - datetime.fromisoformat(args.start_date)).days / 365)) - 1

    # Вывод краткого отчета в терминал
    print(f"\n=== Простая стратегия ===")
    print(f"Сумма недельного пополнения: ${args.weekly_investment:.2f}")
    print(f"Общая сумма вложений: ${simple_invested:.2f}")
    print(f"Итоговая стоимость портфеля: ${simple_end_value:.2f}")
    print(f"Итоговая прибыль: ${simple_end_value - simple_invested:.2f}")
    print(f"Максимальная просадка: {simple_drawdown * 100:.2f}%")
    print(f"ROI: {simple_roi * 100:.2f}%")
    print(f"CAGR: {simple_cagr * 100:.2f}%\n")

    # Сохранение полного отчета в файл
    report_path = os.path.join(os.getcwd(), "report.txt")
    with open(report_path, "w") as report_file:
        report_file.write(f"=== Простая стратегия ===\n")
        report_file.write(f"Сумма стандартного недельного пополнения: ${args.weekly_investment:.2f}\n")
        report_file.write(f"Общая сумма вложений: ${simple_invested:.2f}\n")
        report_file.write(f"Итоговая стоимость портфеля: ${simple_end_value:.2f}\n")
        report_file.write(f"Итоговая прибыль: ${simple_end_value - simple_invested:.2f}\n")        
        report_file.write(f"Максимальная просадка: {simple_drawdown * 100:.2f}%\n")
        report_file.write(f"ROI: {simple_roi * 100:.2f}%\n")
        report_file.write(f"CAGR: {simple_cagr * 100:.2f}%\n\n")

    print(f"Полный отчёт сохранён в файл: {report_path}")
    plot_results(data, simple_values, simple_monthly)

if __name__ == "__main__":
    main()
