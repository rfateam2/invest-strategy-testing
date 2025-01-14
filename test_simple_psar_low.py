# python test_simple_psar_low.py QQQ 100 2024-01-01 --end_date 2024-12-31

import yfinance as yf
import pandas as pd
import numpy as np
import argparse
from datetime import datetime
import matplotlib.pyplot as plt
import os
import ta

def load_data(ticker, start_date, end_date):
    data = yf.download(ticker, start=start_date, end=end_date)
    if data.empty:
        raise ValueError(f"Не удалось загрузить данные для тикера {ticker}. Проверьте тикер и диапазон дат.")
    data.reset_index(inplace=True)

    # Обработка MultiIndex
    if isinstance(data.columns, pd.MultiIndex):
        # print("\nMultiIndex обнаружен, объединяю уровни индексов.")
        data.columns = [col[0] for col in data.columns]
        #print("Столбцы данных после обработки MultiIndex:", data.columns)

    # Проверка наличия необходимых столбцов
    if not {"High", "Low", "Close"}.issubset(data.columns):
        print("\nДанные после обработки:")
        print(data.head())
        raise ValueError("Данные не содержат необходимых столбцов 'High', 'Low', 'Close'.")

    # Проверяем, есть ли пустые значения
    if data[["High", "Low", "Close"]].isnull().any().any():
        raise ValueError("Данные содержат пустые значения в столбцах 'High', 'Low' или 'Close'.")

    return data

def calculate_psar(data):
    """Реализация Parabolic SAR."""
    high = data['High'].values
    low = data['Low'].values
    close = data['Close'].values
    
    # Начальные параметры PSAR
    af = 0.02  # Коэффициент ускорения
    af_max = 0.2
    psar = np.zeros_like(close)
    trend = np.ones_like(close)  # 1 - восходящий, -1 - нисходящий
    
    ep = high[0]  # Экстремальная точка
    psar[0] = low[0]  # Начальное значение PSAR
    
    for i in range(1, len(close)):
        previous_psar = psar[i - 1]
        previous_trend = trend[i - 1]
        
        # Обновляем значение PSAR
        if previous_trend == 1:
            psar[i] = previous_psar + af * (ep - previous_psar)
            if low[i] < psar[i]:
                trend[i] = -1
                psar[i] = ep
                ep = low[i]
                af = 0.02
            else:
                trend[i] = 1
                if high[i] > ep:
                    ep = high[i]
                    af = min(af + 0.02, af_max)
        else:
            psar[i] = previous_psar + af * (ep - previous_psar)
            if high[i] > psar[i]:
                trend[i] = 1
                psar[i] = ep
                ep = high[i]
                af = 0.02
            else:
                trend[i] = -1
                if low[i] < ep:
                    ep = low[i]
                    af = min(af + 0.02, af_max)
    
    data['PSAR'] = psar
    return data


def resample_to_weekly(data):
    required_columns = ['Open', 'High', 'Low', 'Close', 'Volume']
    for col in required_columns:
        if col not in data.columns:
            raise ValueError(f"Не найден столбец {col} в данных")
    
    weekly_data = data.resample('W', on='Date').agg({
        'Open': 'first',
        'High': 'max',
        'Low': 'min',
        'Close': 'last',
        'Volume': 'sum'
    }).dropna()

    # Сброс индекса, чтобы вернуть 'Date' как столбец
    weekly_data = weekly_data.reset_index()
    # print(weekly_data.head())
    # print(weekly_data.columns)
    return weekly_data

def apply_simple_strategy(data, weekly_investment, day_of_week):
    total_invested = 0
    total_units = 0
    portfolio_value = []
    monthly_investments = []

    required_columns = ['Date', 'Close', 'PSAR']
    for col in required_columns:
        if col not in data.columns:
            raise ValueError(f"Не найден столбец {col} в данных")

    for _, row in data.iterrows():
        date, close, psar = row['Date'], row['Close'], row['PSAR']

        # Условие покупки: PSAR выше цены закрытия
        if psar > close:
            total_units += weekly_investment / close
            total_invested += weekly_investment
            monthly_investments.append((date.strftime("%Y-%m"), weekly_investment))

        portfolio_value.append(total_units * close)

    return total_invested, portfolio_value, pd.DataFrame(monthly_investments, columns=["YearMonth", "Investment"])

def calculate_drawdown(portfolio_value):
    if len(portfolio_value) == 0:
        return 0
    max_value = np.maximum.accumulate(portfolio_value)
    with np.errstate(divide='ignore', invalid='ignore'):
        drawdown = np.where(max_value > 0, (portfolio_value - max_value) / max_value, 0)
    return drawdown.min() if len(drawdown) > 0 else 0

def calculate_roi(start_value, end_value, total_invested):
    return (end_value - total_invested) / total_invested if total_invested > 0 else 0

def plot_results(data, simple_values, simple_monthly):
    simple_monthly_totals = simple_monthly.groupby("YearMonth")["Investment"].sum().reset_index()
    simple_monthly_totals["YearMonth"] = pd.to_datetime(simple_monthly_totals["YearMonth"])

    plt.figure(figsize=(14, 7))
    plt.plot(data["Date"], simple_values, label="Простая стратегия: Стоимость портфеля")
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
    args = parser.parse_args()

    data = load_data(args.ticker, args.start_date, args.end_date)
    data.reset_index(inplace=True)  # Убедитесь, что 'Date' является столбцом
    # print(data.head())
    # print(data.columns)

    data = resample_to_weekly(data)
    # Вместо ta.trend import PSAR
    # Используем calculate_psar(data)
    # print(data.head())
    # print(data.columns)
    data = calculate_psar(data)

    # Перед вызовом стратегии проверьте данные
    # print(data.head())
    # print(data.columns)

    # Вызов функции
    simple_invested, simple_values, simple_monthly = apply_simple_strategy(data, args.weekly_investment, "Friday")

    simple_drawdown = calculate_drawdown(simple_values)
    simple_end_value = simple_values[-1] if simple_values else 0
    simple_roi = calculate_roi(0, simple_end_value, simple_invested)

    print(f"\n=== Простая стратегия. Покупка выше PSAR ===")
    print(f"Общая сумма вложений: ${simple_invested:.2f}")
    print(f"Итоговая стоимость портфеля: ${simple_end_value:.2f}")
    print(f"Итоговая прибыль: ${simple_end_value - simple_invested:.2f}")
    print(f"Максимальная просадка: {simple_drawdown * 100:.2f}%")
    print(f"ROI: {simple_roi * 100:.2f}%")

    plot_results(data, simple_values, simple_monthly)

if __name__ == "__main__":
    main()
