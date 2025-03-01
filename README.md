# invest-strategy-testing

## Тестируемые Стратегии Инвестирования

**Название стратегии**: QQQ/QLD/TQQQ - Тестируемая стратегия еженедельного инвестирования.

**Название стратегии**: develop - Другие стратегии.

### Как запустить скрипт
```
cd qqq

python3 -m venv path/to/venv                                                                                     
source path/to/venv/bin/activate
pip install yfinance pandas numpy matplotlib ta

python investing.py 1000 --start_date 2015-01-01 --end_date 2024-12-31 --ticker_1 QQQ --ticker_2 QLD --ticker_3 TQQQ --index QQQ --dropdown_1 0.10 --dropdown_2 0.20 --sell_threshold 0.10 --skip_graf --skip_simple

python3 daily_check.py
```