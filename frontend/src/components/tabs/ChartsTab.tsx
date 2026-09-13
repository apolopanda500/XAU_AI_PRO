// @ts-nocheck
// @ts-nocheck
import { useAppStore } from '../../hooks/useAppStore';

export default function ChartsTab() {
  const theme = useTheme();
  const chartContainerRef = useRef<HTMLDivElement>(null);
  const chartInstanceRef = useRef<any>(null);
  const { selectedSymbol, quotes } = useAppStore();
  const [timeframe, setTimeframe] = React.useState('M15');

  const TIMEFRAMES = ['M1', 'M5', 'M15', 'M30', 'H1', 'H4', 'D1'];

  useEffect(() => {
    if (chartContainerRef.current) {
      // Limpa instancia anterior
      if (chartInstanceRef.current) {
        chartInstanceRef.current.remove();
      }

      // Cria chart (lightweight-charts sera carregado dinamicamente)
      const initChart = async () => {
        const { createChart } = await import('lightweight-charts');
        const chart = createChart(chartContainerRef.current!, {
          layout: { background: { type: 'solid', color: theme.palette.background.paper }, textColor: theme.palette.text.primary },
          grid: { vertLines: { color: 'rgba(36, 50, 68, 0.5)' }, horzLines: { color: 'rgba(36, 50, 68, 0.5)' } },
          rightPriceScale: { borderVisible: false },
          timeScale: { borderVisible: false },
          crosshair: { mode: 0 },
        });

        // Dados simulados (substituir por dados reais do backend)
        const candleData = generateCandles(100);
        const areaData = candleData.map(c => ({ time: c.time, value: c.close }));

        const candlestickSeries = chart.addCandlestickSeries({
          upColor: '#00c853',
          downColor: '#ff3d57',
          borderDownColor: '#ff3d57',
          borderUpColor: '#00c853',
          wickDownColor: '#ff3d57',
          wickUpColor: '#00c853',
        });
        candlestickSeries.setData(candleData);

        const areaSeries = chart.addAreaSeries({
          topColor: 'rgba(0, 198, 251, 0.3)',
          bottomColor: 'rgba(0, 198, 251, 0.05)',
          lineColor: 'rgba(0, 198, 251, 0.5)',
          lineWidth: 2,
        });
        areaSeries.setData(areaData);

        chart.timeScale().fitContent();
        chartInstanceRef.current = chart;
      };

      initChart();

      return () => {
        if (chartInstanceRef.current) {
          chartInstanceRef.current.remove();
          chartInstanceRef.current = null;
        }
      };
    }
  }, [selectedSymbol, timeframe, theme]);

  return (
    <Box>
      <Typography variant="h4" sx={{ mb: 3, fontWeight: 'bold' }}>
        GrÃƒÂ¡ficos - {selectedSymbol}
      </Typography>

      <Card sx={{ bgcolor: 'background.paper', mb: 2 }}>
        <CardContent sx={{ display: 'flex', gap: 2, alignItems: 'center' }}>
          <FormControl size="small" sx={{ minWidth: 150 }}>
            <InputLabel>Timeframe</InputLabel>
            <Select
              value={timeframe}
              label="Timeframe"
              onChange={(e) => setTimeframe(e.target.value)}
            >
              {TIMEFRAMES.map((tf) => (
                <MenuItem key={tf} value={tf}>{tf}</MenuItem>
              ))}
            </Select>
          </FormControl>
          <Select
            size="small"
            value={selectedSymbol}
            onChange={(e) => useAppStore.getState().setSelectedSymbol(e.target.value)}
            sx={{ minWidth: 150 }}
          >
            {quotes.map((q) => (
              <MenuItem key={q.symbol} value={q.symbol}>{q.symbol}</MenuItem>
            ))}
          </Select>
        </CardContent>
      </Card>

      <Card sx={{ bgcolor: 'background.paper' }}>
        <CardContent sx={{ p: 0 }}>
          <div ref={chartContainerRef} style={{ height: 500, width: '100%' }} />
        </CardContent>
      </Card>
    </Box>
  );
}

function generateCandles(count: number) {
  const data: any[] = [];
  const baseTime = Math.floor(Date.now() / 1000);
  let price = 2350.0;

  for (let i = count - 1; i >= 0; i--) {
    const time = baseTime - i * 60 * 15;
    const open = price + (Math.random() - 0.5) * 5;
    const close = open + (Math.random() - 0.5) * 3;
    const high = Math.max(open, close) + Math.random() * 2;
    const low = Math.min(open, close) - Math.random() * 2;
    price = close;
    data.push({ time, open, high, low, close });
  }

  return data;
}
















