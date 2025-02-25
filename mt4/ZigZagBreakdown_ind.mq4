//+------------------------------------------------------------------+
//|                                               ZigZagBreakdown.mq4 |
//|                             Copyright 2000-2025, MetaQuotes Ltd. |
//|                                              http://www.mql5.com |
//+------------------------------------------------------------------+
#property copyright "2000-2025, MetaQuotes Ltd."
#property link      "https://www.mql5.com"
#property strict

#property indicator_chart_window
#property indicator_buffers 5 // 5 буферов: ZigZag, сигнал на покупку, сигнал пиков High, сигнал пиков Low, сигнал на продажу
#property indicator_color1  Red   // Цвет линии ZigZag
#property indicator_color2  Green // Цвет сигнала на покупку
#property indicator_color3  Green // Цвет сигнала пиков High ZigZag
#property indicator_color4  Red   // Цвет сигнала пиков Low ZigZag
#property indicator_color5  Red   // Цвет сигнала на продажу

//---- indicator parameters
input int InpDepth=12;         // Depth
input int InpDeviation=5;      // Deviation
input int InpBackstep=3;       // Backstep
input bool ShowZigZagLine=false; // Показывать линию ZigZag (по умолчанию отключена)

//---- indicator buffers
double ExtZigzagBuffer[];         // Буфер для линии ZigZag
double ExtBuySignalBuffer[];      // Буфер для сигнала на покупку
double ExtHighPeakSignalBuffer[]; // Буфер для сигнала пиков High ZigZag
double ExtLowPeakSignalBuffer[];  // Буфер для сигнала пиков Low ZigZag
double ExtSellSignalBuffer[];     // Буфер для сигнала на продажу
double ExtHighBuffer[];           // Вспомогательный буфер для максимумов
double ExtLowBuffer[];            // Вспомогательный буфер для минимумов

//--- globals
int    ExtLevel=3;           // Глубина пересчета экстремумов
double lastPeakValue = 0.0;  // Значение последнего пика High ZigZag
double lastLowPeakValue = 0.0; // Значение последнего пика Low ZigZag
bool   signalBuyTriggered = false; // Флаг для отслеживания первого сигнала на покупку
bool   signalSellTriggered = false; // Флаг для отслеживания первого сигнала на продажу

//+------------------------------------------------------------------+
//| Custom indicator initialization function                         |
//+------------------------------------------------------------------+
int OnInit()
{
   if(InpBackstep >= InpDepth)
   {
      Print("Backstep cannot be greater or equal to Depth");
      return(INIT_FAILED);
   }

   // Устанавливаем 7 буферов (5 видимых + 2 вспомогательных)
   IndicatorBuffers(7);

   // Настройка стилей
   SetIndexStyle(0, ShowZigZagLine ? DRAW_SECTION : DRAW_NONE); // Линия ZigZag (отключается по умолчанию)
   SetIndexStyle(1, DRAW_ARROW);   // Сигнал на покупку (стрелка)
   SetIndexArrow(1, 233);          // Код символа стрелки вверх для сигнала на покупку
   SetIndexStyle(2, DRAW_ARROW);   // Сигнал пиков High ZigZag (кружок)
   SetIndexArrow(2, 159);          // Код символа кружка с точкой для пиков High
   SetIndexStyle(3, DRAW_ARROW);   // Сигнал пиков Low ZigZag (кружок)
   SetIndexArrow(3, 159);          // Код символа кружка с точкой для пиков Low
   SetIndexStyle(4, DRAW_ARROW);   // Сигнал на продажу (стрелка)
   SetIndexArrow(4, 234);          // Код символа стрелки вниз для сигнала на продажу

   // Привязка буферов
   SetIndexBuffer(0, ExtZigzagBuffer);
   SetIndexBuffer(1, ExtBuySignalBuffer);
   SetIndexBuffer(2, ExtHighPeakSignalBuffer);
   SetIndexBuffer(3, ExtLowPeakSignalBuffer);
   SetIndexBuffer(4, ExtSellSignalBuffer);
   SetIndexBuffer(5, ExtHighBuffer);
   SetIndexBuffer(6, ExtLowBuffer);
   
   SetIndexEmptyValue(0, 0.0);
   SetIndexEmptyValue(1, 0.0);
   SetIndexEmptyValue(2, 0.0);
   SetIndexEmptyValue(3, 0.0);
   SetIndexEmptyValue(4, 0.0);

   // Короткое имя индикатора
   IndicatorShortName("ZigZagBreakdown(" + string(InpDepth) + "," + string(InpDeviation) + "," + string(InpBackstep) + ")");

   return(INIT_SUCCEEDED);
}

//+------------------------------------------------------------------+
//| Custom indicator iteration function                              |
//+------------------------------------------------------------------+
int OnCalculate(const int rates_total,
                const int prev_calculated,
                const datetime &time[],
                const double &open[],
                const double &high[],
                const double &low[],
                const double &close[],
                const long &tick_volume[],
                const long &volume[],
                const int &spread[])
{
   int i, limit, counterZ, whatlookfor = 0;
   int back, pos, lasthighpos = 0, lastlowpos = 0;
   double extremum;
   double curlow = 0.0, curhigh = 0.0, lasthigh = 0.0, lastlow = 0.0;

   // Проверка истории и входных данных
   if(rates_total < InpDepth || InpBackstep >= InpDepth)
      return(0);

   // Инициализация при первом запуске
   if(prev_calculated == 0)
      limit = InitializeAll();
   else
   {
      i = counterZ = 0;
      while(counterZ < ExtLevel && i < 100)
      {
         if(ExtZigzagBuffer[i] != 0.0)
            counterZ++;
         i++;
      }
      if(counterZ == 0)
         limit = InitializeAll();
      else
      {
         limit = i - 1;
         if(ExtLowBuffer[i] != 0.0)
         {
            curlow = ExtLowBuffer[i];
            whatlookfor = 1;
         }
         else
         {
            curhigh = ExtHighBuffer[i];
            whatlookfor = -1;
         }
         for(i = limit - 1; i >= 0; i--)
         {
            ExtZigzagBuffer[i] = 0.0;
            ExtLowBuffer[i] = 0.0;
            ExtHighBuffer[i] = 0.0;
            ExtBuySignalBuffer[i] = 0.0;
            ExtHighPeakSignalBuffer[i] = 0.0;
            ExtLowPeakSignalBuffer[i] = 0.0;
            ExtSellSignalBuffer[i] = 0.0;
         }
      }
   }

   // Основной цикл
   for(i = limit; i >= 0; i--)
   {
      // Поиск минимума
      extremum = low[iLowest(NULL, 0, MODE_LOW, InpDepth, i)];
      if(extremum == lastlow)
         extremum = 0.0;
      else
      {
         lastlow = extremum;
         if(low[i] - extremum > InpDeviation * Point)
            extremum = 0.0;
         else
         {
            for(back = 1; back <= InpBackstep; back++)
            {
               pos = i + back;
               if(ExtLowBuffer[pos] != 0 && ExtLowBuffer[pos] > extremum)
                  ExtLowBuffer[pos] = 0.0;
            }
         }
      }
      if(low[i] == extremum)
         ExtLowBuffer[i] = extremum;
      else
         ExtLowBuffer[i] = 0.0;

      // Поиск максимума
      extremum = high[iHighest(NULL, 0, MODE_HIGH, InpDepth, i)];
      if(extremum == lasthigh)
         extremum = 0.0;
      else
      {
         lasthigh = extremum;
         if(extremum - high[i] > InpDeviation * Point)
            extremum = 0.0;
         else
         {
            for(back = 1; back <= InpBackstep; back++)
            {
               pos = i + back;
               if(ExtHighBuffer[pos] != 0 && ExtHighBuffer[pos] < extremum)
                  ExtHighBuffer[pos] = 0.0;
            }
         }
      }
      if(high[i] == extremum)
         ExtHighBuffer[i] = extremum;
      else
         ExtHighBuffer[i] = 0.0;
   }

   // Финальная обработка и сигналы
   if(whatlookfor == 0)
   {
      lastlow = 0.0;
      lasthigh = 0.0;
   }
   else
   {
      lastlow = curlow;
      lasthigh = curhigh;
   }

   for(i = limit; i >= 0; i--)
   {
      switch(whatlookfor)
      {
         case 0: // Поиск пика или впадины
            if(lastlow == 0.0 && lasthigh == 0.0)
            {
               if(ExtHighBuffer[i] != 0.0)
               {
                  lasthigh = High[i];
                  lasthighpos = i;
                  whatlookfor = -1;
                  if(ShowZigZagLine) ExtZigzagBuffer[i] = lasthigh;
                  lastPeakValue = lasthigh;
                  signalBuyTriggered = false;
                  ExtHighPeakSignalBuffer[i] = high[i];
               }
               if(ExtLowBuffer[i] != 0.0)
               {
                  lastlow = Low[i];
                  lastlowpos = i;
                  whatlookfor = 1;
                  if(ShowZigZagLine) ExtZigzagBuffer[i] = lastlow;
                  lastLowPeakValue = lastlow; // Сохраняем последний нижний пик
                  signalSellTriggered = false;
                  ExtLowPeakSignalBuffer[i] = low[i];
               }
            }
            break;
         case 1: // Поиск пика
            if(ExtLowBuffer[i] != 0.0 && ExtLowBuffer[i] < lastlow && ExtHighBuffer[i] == 0.0)
            {
               if(ShowZigZagLine) ExtZigzagBuffer[lastlowpos] = 0.0;
               lastlowpos = i;
               lastlow = ExtLowBuffer[i];
               if(ShowZigZagLine) ExtZigzagBuffer[i] = lastlow;
               lastLowPeakValue = lastlow; // Обновляем последний нижний пик
               signalSellTriggered = false;
               ExtLowPeakSignalBuffer[i] = low[i];
            }
            if(ExtHighBuffer[i] != 0.0 && ExtLowBuffer[i] == 0.0)
            {
               lasthigh = ExtHighBuffer[i];
               lasthighpos = i;
               if(ShowZigZagLine) ExtZigzagBuffer[i] = lasthigh;
               whatlookfor = -1;
               lastPeakValue = lasthigh;
               signalBuyTriggered = false;
               ExtHighPeakSignalBuffer[i] = high[i];
            }
            break;
         case -1: // Поиск впадины
            if(ExtHighBuffer[i] != 0.0 && ExtHighBuffer[i] > lasthigh && ExtLowBuffer[i] == 0.0)
            {
               if(ShowZigZagLine) ExtZigzagBuffer[lasthighpos] = 0.0;
               lasthighpos = i;
               lasthigh = ExtHighBuffer[i];
               if(ShowZigZagLine) ExtZigzagBuffer[i] = lasthigh;
               lastPeakValue = lasthigh;
               signalBuyTriggered = false;
               ExtHighPeakSignalBuffer[i] = high[i];
            }
            if(ExtLowBuffer[i] != 0.0 && ExtHighBuffer[i] == 0.0)
            {
               lastlow = ExtLowBuffer[i];
               lastlowpos = i;
               if(ShowZigZagLine) ExtZigzagBuffer[i] = lastlow;
               whatlookfor = 1;
               lastLowPeakValue = lastlow; // Обновляем последний нижний пик
               signalSellTriggered = false;
               ExtLowPeakSignalBuffer[i] = low[i];
            }
            break;
      }

      // Сигнал на покупку: High текущего бара выше последнего пика ZigZag, только для первого бара
      if(high[i] > lastPeakValue && lastPeakValue != 0.0 && !signalBuyTriggered)
      {
         ExtBuySignalBuffer[i] = low[i];
         signalBuyTriggered = true;
      }
      else
      {
         ExtBuySignalBuffer[i] = 0.0;
      }

      // Сигнал на продажу: Low текущего бара ниже последнего нижнего пика ZigZag, только для первого бара
      if(low[i] < lastLowPeakValue && lastLowPeakValue != 0.0 && !signalSellTriggered)
      {
         ExtSellSignalBuffer[i] = low[i];
         signalSellTriggered = true;
      }
      else
      {
         ExtSellSignalBuffer[i] = 0.0;
      }
   }

   return(rates_total);
}

//+------------------------------------------------------------------+
//| Инициализация всех буферов                                       |
//+------------------------------------------------------------------+
int InitializeAll()
{
   ArrayInitialize(ExtZigzagBuffer, 0.0);
   ArrayInitialize(ExtHighBuffer, 0.0);
   ArrayInitialize(ExtLowBuffer, 0.0);
   ArrayInitialize(ExtBuySignalBuffer, 0.0);
   ArrayInitialize(ExtHighPeakSignalBuffer, 0.0);
   ArrayInitialize(ExtLowPeakSignalBuffer, 0.0);
   ArrayInitialize(ExtSellSignalBuffer, 0.0);
   signalBuyTriggered = false;
   signalSellTriggered = false;
   return(Bars - InpDepth);
}
//+------------------------------------------------------------------+