// @ts-nocheck
// @ts-nocheck
import { useAppStore } from '../../hooks/useAppStore';
interface Prediction {
  symbol: string;
  direction: 'LONG' | 'SHORT';
  confidence: number;
  timeframe: string;
  target: number;
  stop: number;
  timestamp: string;
}

export default function RobotVisionTab() {
  const theme = useTheme();
  const { predictions, aiStatus, selectedSymbol, quotes } = useAppStore();
  const [predictionList, setPredictionList] = useState<Prediction[]>([]);
  const [loading, setLoading] = useState(false);

  // Simula prediÃƒÂ§ÃƒÂµes de IA
  useEffect(() => {
    const mockPredictions: Prediction[] = quotes.map((q) => ({
      symbol: q.symbol,
      direction: Math.random() > 0.5 ? 'LONG' : 'SHORT',
      confidence: Math.floor(Math.random() * 30 + 70),
      timeframe: 'M15',
      target: q.last + (Math.random() - 0.5) * 10,
      stop: q.last - (Math.random() * 5 + 2),
      timestamp: new Date().toISOString(),
    }));
    setPredictionList(mockPredictions);
  }, [quotes]);

  const runPrediction = () => {
    setLoading(true);
    setTimeout(() => {
      setLoading(false);
      const newPredictions: Prediction[] = predictionList.map(p => ({
        ...p,
        confidence: Math.floor(Math.random() * 30 + 70),
        direction: Math.random() > 0.5 ? 'LONG' : 'SHORT',
      }));
      setPredictionList(newPredictions);
    }, 2000);
  };

  const selectedPrediction = predictionList.find(p => p.symbol === selectedSymbol);

  return (
    <Box>
      <Typography variant="h4" sx={{ mb: 3, fontWeight: 'bold' }}>
        AI Vision - PrediÃƒÂ§ÃƒÂµes da EstratÃƒÂ©gia
      </Typography>

      <Box sx={{ display: 'flex', alignItems: 'center', gap: 2, mb: 3 }}>
        <Chip
          
          label={aiStatus}
          color="primary"
          size="small"
        />
        <Button variant="contained" onClick={runPrediction} disabled={loading}>
          {loading ? 'Analisando...' : 'Executar PrediÃƒÂ§ÃƒÂ£o'}
        </Button>
      </Box>

      {/* Detalhes do sÃƒÂ­mbolo selecionado */}
      {selectedPrediction && (
        <Card sx={{ bgcolor: 'background.paper', mb: 3 }}>
          <CardHeader
            title={`${selectedSymbol} - ${selectedPrediction.direction}`}
            titleTypographyProps={{
              style: {
                color: selectedPrediction.direction === 'LONG' ? theme.palette.success.main : theme.palette.error.main,
                fontSize: 20,
              }
            }}
            subheader={`ConfianÃƒÂ§a: ${selectedPrediction.confidence}%`}
          />
          <CardContent>
            <Grid container spacing={2}>
              <Grid item xs={12} md={3}>
                <Typography variant="caption" color="text.secondary">Target</Typography>
                <Typography variant="h6" fontWeight="bold" style={{ color: theme.palette.success.main }}>
                  {selectedPrediction.target.toFixed(2)}
                </Typography>
              </Grid>
              <Grid item xs={12} md={3}>
                <Typography variant="caption" color="text.secondary">Stop Loss</Typography>
                <Typography variant="h6" fontWeight="bold" style={{ color: theme.palette.error.main }}>
                  {selectedPrediction.stop.toFixed(2)}
                </Typography>
              </Grid>
              <Grid item xs={12} md={3}>
                <Typography variant="caption" color="text.secondary">Timeframe</Typography>
                <Typography variant="h6">{selectedPrediction.timeframe}</Typography>
              </Grid>
              <Grid item xs={12} md={3}>
                <Typography variant="caption" color="text.secondary">ÃƒÅ¡ltima AtualizaÃƒÂ§ÃƒÂ£o</Typography>
                <Typography variant="h6">
                  {new Date(selectedPrediction.timestamp).toLocaleTimeString()}
                </Typography>
              </Grid>
            </Grid>
          </CardContent>
        </Card>
      )}

      {/* Lista de prediÃƒÂ§ÃƒÂµes */}
      <Card sx={{ bgcolor: 'background.paper' }}>
        <CardHeader title="Todas as PrediÃƒÂ§ÃƒÂµes" />
        <CardContent sx={{ p: 0 }}>
          <Grid container>
            {predictionList.map((p) => (
              <Grid item xs={12} sm={6} md={3} key={p.symbol}>
                <Box sx={{
                  p: 2,
                  m: 1,
                  bgcolor: 'background.default',
                  borderRadius: 1,
                  border: `1px solid ${p.direction === 'LONG' ? theme.palette.success.main : theme.palette.error.main}`,
                  borderLeftWidth: 3,
                }}>
                  <Typography variant="subtitle1" fontWeight="bold">{p.symbol}</Typography>
                  <Chip
                    label={p.direction}
                    color={p.direction === 'LONG' ? 'success' : 'error'}
                    size="small"
                    sx={{ mt: 1 }}
                  />
                  <Box sx={{ display: 'flex', alignItems: 'center', mt: 1 }}>
                    <LinearProgress
                      variant="determinate"
                      value={p.confidence}
                      sx={{ flex: 1, height: 6, borderRadius: 3 }}
                    />
                    <Typography variant="caption" sx={{ ml: 1 }}>
                      {p.confidence}%
                    </Typography>
                  </Box>
                  <Typography variant="caption" color="text.secondary" display="block" mt={1}>
                    Target: {p.target.toFixed(2)}
                  </Typography>
                </Box>
              </Grid>
            ))}
          </Grid>
        </CardContent>
      </Card>
    </Box>
  );
}















