//+------------------------------------------------------------------+
//|                                               ZigZagBreakdown.mq4 |
//|                             Copyright 2000-2025, MetaQuotes Ltd. |
//|                                              http://www.mql5.com |
//+------------------------------------------------------------------+
#property copyright "2000-2025, MetaQuotes Ltd."
#property link      "https://www.mql5.com"
#property version   "1.00"
#property strict

#property indicator_chart_window
#property indicator_buffers 6 // 6 буферов: ZigZag, Buy, Sell, High Peaks, Low Peaks, MA
#property indicator_color1 clrRed    // Цвет линии ZigZag
#property indicator_color2 clrGreen  // Цвет сигнала на покупку
#property indicator_color3 clrRed    // Цвет сигнала на продажу
#property indicator_color4 clrGray   // Цвет сигнала пиков High ZigZag (серый)
#property indicator_color5 clrGray   // Цвет сигнала пиков Low ZigZag (серый)
#property indicator_color6 clrBlue   // Цвет MA

//---- indicator parameters
input int Depth=12;             // ZigZag Depth
input int Deviation=5;          // ZigZag Deviation
input int Backstep=3;           // ZigZag Backstep
input bool ShowZigZagLine=false; // Show ZigZag Line (default: off)
input int MAPeriod=70;          // Moving Average Period
input bool UseMAFilter=false;   // Use MA Filter (default: false)
input double StopLossPercent=1.0; // Stop Loss Percent

//---- indicator buffers
double ExtZigzagBuffer[];         // Buffer for ZigZag line
double ExtBuySignalBuffer[];      // Buffer for buy signal
double ExtSellSignalBuffer[];     // Buffer for sell signal
double ExtHighPeakSignalBuffer[]; // Buffer for High peaks
double ExtLowPeakSignalBuffer[];  // Buffer for Low peaks
double ExtMABuffer[];             // Buffer for MA
double ExtHighBuffer[];           // Auxiliary buffer for highs
double ExtLowBuffer[];            // Auxiliary buffer for lows

//--- globals
int    ExtLevel=3;                // Depth of extremum recalculation
double lastHighPeak = 0.0;        // Last High peak (Level A)
double lastLowPeak = 0.0;         // Last Low peak (Level B)
bool   signalBuyTriggered = false;// Flag for buy signal
bool   signalSellTriggered = false;// Flag for sell signal

//+------------------------------------------------------------------+
//| Custom indicator initialization function                         |
//+------------------------------------------------------------------+
int OnInit()
{
   if(Backstep >= Depth)
   {
      Print("Backstep cannot be greater or equal to Depth");
      return(INIT_FAILED);
   }

   IndicatorBuffers(8);

   SetIndexStyle(0, ShowZigZagLine ? DRAW_SECTION : DRAW_NONE); 
   SetIndexStyle(1, DRAW_ARROW, EMPTY, 2);   
   SetIndexArrow(1, 233);                    
   SetIndexStyle(2, DRAW_ARROW, EMPTY, 2);   
   SetIndexArrow(2, 234);                    
   SetIndexStyle(3, DRAW_ARROW, EMPTY, 2);   
   SetIndexArrow(3, 217);                    
   SetIndexStyle(4, DRAW_ARROW, EMPTY, 2);   
   SetIndexArrow(4, 218);                    
   SetIndexStyle(5, UseMAFilter ? DRAW_LINE : DRAW_NONE); 

   SetIndexBuffer(0, ExtZigzagBuffer);
   SetIndexBuffer(1, ExtBuySignalBuffer);
   SetIndexBuffer(2, ExtSellSignalBuffer);
   SetIndexBuffer(3, ExtHighPeakSignalBuffer);
   SetIndexBuffer(4, ExtLowPeakSignalBuffer);
   SetIndexBuffer(5, ExtMABuffer);
   SetIndexBuffer(6, ExtHighBuffer);
   SetIndexBuffer(7, ExtLowBuffer);
   
   SetIndexEmptyValue(0, 0.0);
   SetIndexEmptyValue(1, 0.0);
   SetIndexEmptyValue(2, 0.0);
   SetIndexEmptyValue(3, 0.0);
   SetIndexEmptyValue(4, 0.0);
   SetIndexEmptyValue(5, 0.0);

   IndicatorShortName("ZigZagBreakdown(" + string(Depth) + "," + string(Deviation) + "," + string(Backstep) + ")");
   
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
   int i, limit, back;
   double extremum;

   if(rates_total < Depth || Backstep >= Depth)
      return(0);

   if(prev_calculated == 0)
      limit = rates_total - Depth;
   else
      limit = rates_total - prev_calculated;

   if(UseMAFilter)
   {
      for(i = 0; i < rates_total; i++)
         ExtMABuffer[i] = iMA(NULL, 0, MAPeriod, 0, MODE_SMA, PRICE_CLOSE, i);
   }

   for(i = limit; i >= 0; i--)
   {
      extremum = low[iLowest(NULL, 0, MODE_LOW, Depth, i)];
      if(low[i] == extremum)
      {
         for(back = 1; back <= Backstep && (i + back) < rates_total; back++)
         {
            if(ExtLowBuffer[i + back] != 0 && ExtLowBuffer[i + back] > extremum)
               ExtLowBuffer[i + back] = 0.0;
         }
         ExtLowBuffer[i] = extremum;
      }
      else
         ExtLowBuffer[i] = 0.0;

      extremum = high[iHighest(NULL, 0, MODE_HIGH, Depth, i)];
      if(high[i] == extremum)
      {
         for(back = 1; back <= Backstep && (i + back) < rates_total; back++)
         {
            if(ExtHighBuffer[i + back] != 0 && ExtHighBuffer[i + back] < extremum)
               ExtHighBuffer[i + back] = 0.0;
         }
         ExtHighBuffer[i] = extremum;
      }
      else
         ExtHighBuffer[i] = 0.0;
   }

   bool lastWasHigh = false;
   for(i = limit; i >= 0; i--)
   {
      if(ExtHighBuffer[i] != 0.0)
      {
         if(ShowZigZagLine && !lastWasHigh)
            ExtZigzagBuffer[i] = high[i];
         lastHighPeak = high[i];
         signalBuyTriggered = false;
         ExtHighPeakSignalBuffer[i] = high[i];
         lastWasHigh = true;
      }
      else if(ExtLowBuffer[i] != 0.0)
      {
         if(ShowZigZagLine && lastWasHigh)
            ExtZigzagBuffer[i] = low[i];
         lastLowPeak = low[i];
         signalSellTriggered = false;
         ExtLowPeakSignalBuffer[i] = low[i];
         lastWasHigh = false;
      }

      bool maBuyCondition = UseMAFilter ? close[i] > ExtMABuffer[i] : true;
      if(maBuyCondition && high[i] > lastHighPeak && lastHighPeak != 0.0 && !signalBuyTriggered)
      {
         ExtBuySignalBuffer[i] = low[i];
         signalBuyTriggered = true;
      }
      else
         ExtBuySignalBuffer[i] = 0.0;

      bool maSellCondition = UseMAFilter ? close[i] < ExtMABuffer[i] : true;
      if(maSellCondition && low[i] < lastLowPeak && lastLowPeak != 0.0 && !signalSellTriggered)
      {
         ExtSellSignalBuffer[i] = low[i];
         signalSellTriggered = true;
      }
      else
         ExtSellSignalBuffer[i] = 0.0;
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
   ArrayInitialize(ExtMABuffer, 0.0);
   signalBuyTriggered = false;
   signalSellTriggered = false;
   return(Bars - Depth);
}
//+------------------------------------------------------------------+