# python3 -m venv path/to/venv                                                                                     
# source path/to/venv/bin/activate
# pip install yfinance pandas numpy matplotlib
# python test_advince_dvd.py QQQ 100 2024-01-01 --end_date 2024-12-31

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
    # Избегаем деления на ноль
    with np.errstate(divide='ignore', invalid='ignore'):
        drawdown = np.where(max_value > 0, (portfolio_value - max_value) / max_value, 0)
    return drawdown.min() if len(drawdown) > 0 else 0


def calculate_roi(start_value, end_value, total_invested):
    return (end_value - total_invested) / total_invested if total_invested > 0 else 0

def plot_results(data, simple_values, test_values, simple_monthly, test_monthly, simple_invested, test_invested):
    simple_monthly_totals = simple_monthly.groupby("YearMonth")["Investment"].sum().reset_index()
    simple_monthly_totals["YearMonth"] = pd.to_datetime(simple_monthly_totals["YearMonth"])

    test_monthly_totals = test_monthly.groupby("YearMonth")["Investment"].sum().reset_index()
    test_monthly_totals["YearMonth"] = pd.to_datetime(test_monthly_totals["YearMonth"])

    # Расчёт вложенных средств для отображения на графике
    simple_cumulative_investment = simple_monthly_totals["Investment"].cumsum()
    test_cumulative_investment = test_monthly_totals["Investment"].cumsum()

    plt.figure(figsize=(14, 7))
    plt.plot(data["Date"], simple_values, label="Простая стратегия: Стоимость портфеля", color="blue")
    plt.plot(data["Date"], test_values, label="Тестируемая стратегия: Стоимость портфеля", color="orange")
    plt.bar(test_monthly_totals["YearMonth"], test_monthly_totals["Investment"], width=20, alpha=0.3, label="Тестируемая стратегия: Пополнения", color="orange")

    # Добавление кривых вложенных средств
    plt.plot(data["Date"], np.interp(data["Date"], simple_monthly_totals["YearMonth"], simple_cumulative_investment),
             label="Простая стратегия: Вложенные средства", color="blue", linestyle="--", alpha=0.5)
    plt.plot(data["Date"], np.interp(data["Date"], test_monthly_totals["YearMonth"], test_cumulative_investment),
             label="Тестируемая стратегия: Вложенные средства", color="orange", linestyle="--", alpha=0.5)

    plt.title("Динамика стоимости портфеля и пополнений")
    plt.xlabel("Дата")
    plt.ylabel("Доллары ($)")
    plt.legend()
    plt.grid()
    plt.show()


def load_dividend_data(ticker, start_date, end_date):
    """Загрузка данных о дивидендах для тикера."""
    data = yf.Ticker(ticker).history(start=start_date, end=end_date)
    if "Dividends" in data.columns:
        dividends = data[["Dividends"]].reset_index()
        dividends = dividends[dividends["Dividends"] > 0]  # Учитывать только даты с дивидендами
        return dividends
    else:
        return pd.DataFrame(columns=["Date", "Dividends"])

# def apply_dividend_reinvestment(data, dividends, total_units):
#     """Реинвестирование дивидендов."""
#     for _, row in dividends.iterrows():
#         dividend_date = row["Date"]
#         dividend_amount = row["Dividends"]
#         # Найти цену закрытия в дату выплаты дивиденда
#         close_price = data.loc[data["Date"] == dividend_date, "Close"]
#         if not close_price.empty:
#             close_price = close_price.iloc[0]
#             # Расчёт количества новых акций, купленных на сумму дивидендов
#             dividend_investment = total_units * dividend_amount
#             new_units = dividend_investment / close_price
#             # Обновление общего количества акций
#             total_units += new_units
#     return total_units

def apply_dividend_reinvestment(data, dividends, total_units):
    dividend_logs = []

    for _, row in dividends.iterrows():
        dividend_date = row["Date"]
        dividend_amount = row["Dividends"]
        
        # Найти цену закрытия в дату выплаты дивиденда
        close_price = data.loc[data["Date"] == dividend_date, "Close"]
        if close_price.empty:
            print(f"Пропущена дата: {dividend_date} (нет данных о цене закрытия)")
            continue

        close_price = close_price.iloc[0]

        # Расчёт количества новых акций, купленных на сумму дивидендов
        dividend_investment = total_units * dividend_amount
        new_units = dividend_investment / close_price

        dividend_logs.append({
            "Date": dividend_date,
            "Dividend_Per_Share": dividend_amount,
            "Close_Price": close_price,
            "Total_Units_Before": total_units,
            "Dividend_Investment": dividend_investment,
            "New_Units": new_units
        })

        total_units += new_units

    return total_units, pd.DataFrame(dividend_logs)




def main():
    parser = argparse.ArgumentParser(description="Тестирование инвестиционных стратегий.")
    parser.add_argument("ticker", type=str, help="Тикер акции (например, QQQ).")
    parser.add_argument("weekly_investment", type=float, help="Сумма еженедельного пополнения в долларах.")
    parser.add_argument("start_date", type=str, help="Дата начала периода (YYYY-MM-DD).")
    parser.add_argument("--end_date", type=str, default=datetime.now().strftime("%Y-%m-%d"), help="Дата конца периода (YYYY-MM-DD).")
    parser.add_argument("--day_of_week", type=str, default="Friday", help="День недели для еженедельного пополнения.")
    parser.add_argument("--multiplier", type=float, default=1.5, help="Множитель для дополнительных инвестиций.")
    args = parser.parse_args()

    data = load_data(args.ticker, args.start_date, args.end_date)
    dividends = load_dividend_data(args.ticker, args.start_date, args.end_date)
    print(dividends)

    # Применение стратегий
    simple_invested, simple_values, simple_monthly = apply_simple_strategy(data, args.weekly_investment, args.day_of_week)
    test_invested, test_values, test_monthly = apply_test_strategy(data, args.weekly_investment, args.multiplier, args.day_of_week)

    # Реинвестирование дивидендов
    total_units_simple = simple_invested / data["Close"].iloc[0]
    total_units_simple, simple_dividend_logs = apply_dividend_reinvestment(data, dividends, total_units_simple)
    simple_end_value_with_dividends = total_units_simple * data["Close"].iloc[-1]

    total_units_test = test_invested / data["Close"].iloc[0]
    total_units_test, test_dividend_logs = apply_dividend_reinvestment(data, dividends, total_units_test)
    test_end_value_with_dividends = total_units_test * data["Close"].iloc[-1]

    # Вывод данных о дивидендах
    print("\n=== Лог дивидендов для простой стратегии ===")
    print(simple_dividend_logs)

    print("\n=== Лог дивидендов для тестируемой стратегии ===")
    print(test_dividend_logs)


    # # Реинвестирование дивидендов
    # total_units_simple = simple_invested / data["Close"].iloc[0]
    # total_units_simple = apply_dividend_reinvestment(data, dividends, total_units_simple)
    # simple_end_value_with_dividends = total_units_simple * data["Close"].iloc[-1]

    # total_units_test = test_invested / data["Close"].iloc[0]
    # total_units_test = apply_dividend_reinvestment(data, dividends, total_units_test)
    # test_end_value_with_dividends = total_units_test * data["Close"].iloc[-1]

    # Вычисление метрик
    simple_drawdown = calculate_drawdown(simple_values)
    test_drawdown = calculate_drawdown(test_values)

    simple_end_value = simple_values[-1] if simple_values else 0
    test_end_value = test_values[-1] if test_values else 0

    simple_roi = calculate_roi(0, simple_end_value, simple_invested)
    test_roi = calculate_roi(0, test_end_value, test_invested)

    simple_cagr = (1 + simple_roi) ** (1 / ((datetime.fromisoformat(args.end_date) - datetime.fromisoformat(args.start_date)).days / 365)) - 1
    test_cagr = (1 + test_roi) ** (1 / ((datetime.fromisoformat(args.end_date) - datetime.fromisoformat(args.start_date)).days / 365)) - 1

    # Вывод результатов в консоль
    print(f"\n=== Простая стратегия ===")
    print(f"Сумма стандартного недельного пополнения: ${args.weekly_investment:.2f}")
    print(f"Общая сумма вложений: ${simple_invested:.2f}")
    print(f"Итоговая стоимость портфеля: ${simple_end_value:.2f}")
    print(f"Итоговая стоимость портфеля (с дивидендами): ${simple_end_value_with_dividends:.2f}")
    print(f"Итоговая прибыль: ${simple_end_value - simple_invested:.2f}")
    print(f"Максимальная просадка: {simple_drawdown * 100:.2f}%")
    print(f"ROI: {simple_roi * 100:.2f}%")
    print(f"CAGR: {simple_cagr * 100:.2f}%\n")

    print(f"=== Тестируемая стратегия ===")
    print(f"Сумма стандартного недельного пополнения: ${args.weekly_investment:.2f}")
    print(f"Общая сумма вложений: ${test_invested:.2f}")
    print(f"Итоговая стоимость портфеля: ${test_end_value:.2f}")
    print(f"Итоговая стоимость портфеля (с дивидендами): ${test_end_value_with_dividends:.2f}")
    print(f"Итоговая прибыль: ${test_end_value - test_invested:.2f}")
    print(f"Максимальная просадка: {test_drawdown * 100:.2f}%")
    print(f"ROI: {test_roi * 100:.2f}%")
    print(f"CAGR: {test_cagr * 100:.2f}%\n")

    # Сохранение полного отчета в файл
    report_path = os.path.join(os.getcwd(), "report.txt")
    with open(report_path, "w") as report_file:
        report_file.write(f"=== Простая стратегия ===\n")
        report_file.write(f"Сумма стандартного недельного пополнения: ${args.weekly_investment:.2f}\n")
        report_file.write(f"Общая сумма вложений: ${simple_invested:.2f}\n")
        report_file.write(f"Итоговая стоимость портфеля: ${simple_end_value:.2f}\n")
        report_file.write(f"Итоговая стоимость портфеля (с дивидендами): ${simple_end_value_with_dividends:.2f}\n")
        report_file.write(f"Итоговая прибыль: ${simple_end_value - simple_invested:.2f}\n")
        report_file.write(f"Максимальная просадка: {simple_drawdown * 100:.2f}%\n")
        report_file.write(f"ROI: {simple_roi * 100:.2f}%\n")
        report_file.write(f"CAGR: {simple_cagr * 100:.2f}%\n\n")

        report_file.write(f"=== Тестируемая стратегия ===\n")
        report_file.write(f"Сумма стандартного недельного пополнения: ${args.weekly_investment:.2f}\n")
        report_file.write(f"Общая сумма вложений: ${test_invested:.2f}\n")
        report_file.write(f"Итоговая стоимость портфеля: ${test_end_value:.2f}\n")
        report_file.write(f"Итоговая стоимость портфеля (с дивидендами): ${test_end_value_with_dividends:.2f}\n")
        report_file.write(f"Итоговая прибыль: ${test_end_value - test_invested:.2f}\n")
        report_file.write(f"Максимальная просадка: {test_drawdown * 100:.2f}%\n")
        report_file.write(f"ROI: {test_roi * 100:.2f}%\n")
        report_file.write(f"CAGR: {test_cagr * 100:.2f}%\n\n")

        report_file.write("Ежемесячные вложения:\n")
        report_file.write(test_monthly.groupby("YearMonth")["Investment"].sum().to_string())

    print(f"Полный отчёт сохранён в файл: {report_path}")

    plot_results(data, simple_values, test_values, simple_monthly, test_monthly, simple_invested, test_invested)

if __name__ == "__main__":
    main()
