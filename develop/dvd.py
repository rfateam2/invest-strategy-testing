import pandas as pd
import numpy as np

# Пример данных
data = pd.DataFrame({
    "Date": pd.date_range(start="2024-01-01", periods=365, freq="D"),
    "Close": np.random.uniform(50, 150, 365)
})

dividends = pd.DataFrame({
    "Date": [
        "2024-03-18 00:00:00-04:00",
        "2024-06-24 00:00:00-04:00",
        "2024-09-23 00:00:00-04:00",
        "2024-12-23 00:00:00-05:00"
    ],
    "Dividends": [0.573, 0.762, 0.677, 0.835]
})

# Функция для реинвестирования дивидендов
# Исправленный код для обработки дат с временными зонами
def apply_dividend_reinvestment(data, dividends, initial_units):
    # Преобразование даты
    data["Date"] = pd.to_datetime(data["Date"]).dt.normalize()
    dividends["Date"] = pd.to_datetime(dividends["Date"], utc=True).dt.tz_convert(None).dt.normalize()

    # Добавление пропущенных дат
    missing_dates = dividends.loc[~dividends["Date"].isin(data["Date"]), "Date"]
    for date in missing_dates:
        data = pd.concat([data, pd.DataFrame({"Date": [date], "Close": [None]})], ignore_index=True)

    # Сортировка данных
    data = data.sort_values("Date").reset_index(drop=True)

    # Интерполяция цен закрытия
    data["Close"] = data["Close"].interpolate(method="linear")

    # Лог реинвестирования
    dividend_logs = []
    total_units = initial_units

    for _, row in dividends.iterrows():
        dividend_date = row["Date"]
        dividend_amount = row["Dividends"]

        # Найти цену закрытия на дату выплаты дивиденда
        close_price = data.loc[data["Date"] == dividend_date, "Close"]
        if close_price.empty or pd.isna(close_price.iloc[0]):
            print(f"Пропущена дата: {dividend_date} (нет валидной цены закрытия)")
            continue

        close_price = close_price.iloc[0]

        # Расчёт дивидендного дохода
        dividend_income = total_units * dividend_amount

        # Расчёт количества новых акций
        new_units = dividend_income / close_price

        dividend_logs.append({
            "Date": dividend_date,
            "Dividend_Per_Share": dividend_amount,
            "Close_Price": close_price,
            "Total_Units_Before": total_units,
            "Dividend_Investment": dividend_income,
            "New_Units": new_units
        })

        # Обновление общего количества акций
        total_units += new_units

    return total_units, pd.DataFrame(dividend_logs)


# Параметры начальной стратегии
initial_units = 100  # Начальное количество акций

# Применение функции
total_units, dividend_log = apply_dividend_reinvestment(data, dividends, initial_units)

# Результаты
print(f"Итоговое количество акций: {total_units}")
print("\n=== Лог дивидендов ===")
print(dividend_log)

# Итоговая стоимость портфеля с учётом дивидендов
final_portfolio_value = total_units * data["Close"].iloc[-1]
print(f"\nИтоговая стоимость портфеля: ${final_portfolio_value:.2f}")
