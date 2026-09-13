// @ts-nocheck
// @ts-nocheck
import { useAppStore } from '../../hooks/useAppStore';

export default function StrategyTesterTab() {
  const theme = useTheme();
  const [isRunning, setIsRunning] = useState(false);
  const [progress, setProgress] = useState(0);
  const { quotes } = useAppStore();
  const [results, setResults] = useState<any[]>([]);

  const startTest = () => {
    setIsRunning(true);
    setProgress(0);

    const interval = setInterval(() => {
      setProgress(prev => {
        if (prev >= 100) {
          clearInterval(interval);
          setIsRunning(false);
          setResults([
            { symbol: 'XAUUSD', profit: 142.50, trades: 12, winRate: 75.0, maxDd: 45.2 },
            { symbol: 'EURUSD', profit: 87.30, trades: 8, winRate: 62.5, maxDd: 22.8 },
            { symbol: 'BTCUSD', profit: -23.40, trades: 5, winRate: 40.0, maxDd: 67.1 },
          ]);
          return 100;
        }
        return prev + Math.random() * 5;
      });
    }, 200);
  };

  const stopTest = () => {
    setIsRunning(false);
    setProgress(0);
  };

  return (
    <Box>
      <Typography variant="h4" sx={{ mb: 3, fontWeight: 'bold' }}>
        Teste de EstratÃƒÂ©gia
      </Typography>

      <Grid container spacing={3}>
        <Grid item xs={12} md={8}>
          <Card sx={{ bgcolor: 'background.paper', mb: 3 }}>
            <CardHeader title="ConfiguraÃƒÂ§ÃƒÂ£o do Teste" />
            <CardContent>
              <Box sx={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', gap: 2 }}>
                <FormControl size="small">
                  <InputLabel>EstratÃƒÂ©gia</InputLabel>
                  <Select defaultValue="xau-scalper-v2">
                    <MenuItem value="xau-scalper-v2">XAU Scalper v2</MenuItem>
                    <MenuItem value="ai-bot-v1">AI Bot v1</MenuItem>
                    <MenuItem value="grid-bot">Grid Bot</MenuItem>
                    <MenuItem value="dca-bot">DCA Bot</MenuItem>
                  </Select>
                </FormControl>
                <TextField label="PerÃƒÂ­odo Inicial" size="small" type="date" />
                <TextField label="PerÃƒÂ­odo Final" size="small" type="date" />
                <TextField label="DepÃƒÂ³sito Inicial" size="small" type="number" defaultValue="10000" />
                <FormControl size="small">
                  <InputLabel>Timeframe</InputLabel>
                  <Select defaultValue="M15">
                    <MenuItem value="M1">M1</MenuItem>
                    <MenuItem value="M5">M5</MenuItem>
                    <MenuItem value="M15">M15</MenuItem>
                    <MenuItem value="H1">H1</MenuItem>
                    <MenuItem value="D1">D1</MenuItem>
                  </Select>
                </FormControl>
              </Box>
              <Box sx={{ mt: 2 }}>
                <TextField label="SÃƒÂ­mbolos" size="small" defaultValue="XAUUSD,EURUSD,GBPUSD" fullWidth />
              </Box>
            </CardContent>
          </Card>

          <Card sx={{ bgcolor: 'background.paper' }}>
            <CardHeader
              title="Progresso"
              action={
                !isRunning ? (
                  <Button variant="contained" startIcon={<PlayArrow />} onClick={startTest}>
                    Iniciar Teste
                  </Button>
                ) : (
                  <Button variant="outlined" color="error" startIcon={<Stop />} onClick={stopTest}>
                    Parar
                  </Button>
                )
              }
            />
            <CardContent>
              <LinearProgress
                variant={isRunning ? 'indeterminate' : 'determinate'}
                value={progress}
                sx={{ height: 8, borderRadius: 4 }}
              />
              {progress > 0 && <Typography mt={1}>{progress.toFixed(0)}% concluÃƒÂ­do</Typography>}
            </CardContent>
          </Card>
        </Grid>

        <Grid item xs={12} md={4}>
          <Card sx={{ bgcolor: 'background.paper' }}>
            <CardHeader title="Resultados" />
            <CardContent>
              <Table size="small">
                <TableHead>
                  <TableRow>
                    <TableCell>SÃƒÂ­mbolo</TableCell>
                    <TableCell align="right">Profit</TableCell>
                    <TableCell align="right">Trades</TableCell>
                    <TableCell align="right">Win %</TableCell>
                    <TableCell align="right">Max DD</TableCell>
                  </TableRow>
                </TableHead>
                <TableBody>
                  {results.map((r, i) => (
                    <TableRow key={i} hover>
                      <TableCell>{r.symbol}</TableCell>
                      <TableCell align="right" style={{ color: r.profit >= 0 ? '#00c853' : '#ff3d57' }}>
                        ${r.profit.toFixed(2)}
                      </TableCell>
                      <TableCell align="right">{r.trades}</TableCell>
                      <TableCell align="right">{r.winRate.toFixed(1)}%</TableCell>
                      <TableCell align="right">{r.maxDd.toFixed(1)}%</TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </CardContent>
          </Card>
        </Grid>
      </Grid>
    </Box>
  );
}













