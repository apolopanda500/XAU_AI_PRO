// @ts-nocheck
// @ts-nocheck
import { useAppStore } from '../../hooks/useAppStore';

export default function MarketTab() {
  const theme = useTheme();
  const { quotes, selectedSymbol, setSelectedSymbol } = useAppStore();
  const [search, setSearch] = useState('');

  const filtered = quotes.filter(q =>
    q.symbol.toLowerCase().includes(search.toLowerCase())
  );

  const selectedQuote = quotes.find(q => q.symbol === selectedSymbol);

  return (
    <Box>
      <Typography variant="h4" sx={{ mb: 3, fontWeight: 'bold' }}>
        Mercado - Dados em Tempo Real
      </Typography>

      <Box sx={{ mb: 3 }}>
        <TextField
          size="small"
          placeholder="Buscar sÃƒÂ­mbolo (ex: XAUUSD)..."
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          sx={{ width: 300 }}
          InputProps={{
            startAdornment: (
              <InputAdornment position="start">
                
              </InputAdornment>
            ),
          }}
        />
      </Box>

      <Card sx={{ bgcolor: 'background.paper', mb: 3 }}>
        <CardHeader
          title={selectedQuote ? `${selectedQuote.symbol} - Detalhes` : 'Selecione um sÃƒÂ­mbolo'}
          titleTypographyProps={{ variant: 'h6' }}
        />
        <CardContent>
          {selectedQuote ? (
            <Box sx={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(150px, 1fr))', gap: 2 }}>
              <Box>
                <Typography variant="caption" color="text.secondary">ÃƒÅ¡ltimo</Typography>
                <Typography variant="h5" fontWeight="bold">{selectedQuote.last?.toFixed(selectedQuote.digits || 2)}</Typography>
              </Box>
              <Box>
                <Typography variant="caption" color="text.secondary">Bid</Typography>
                <Typography variant="h5" style={{ color: theme.palette.success.main }}>{selectedQuote.bid?.toFixed(selectedQuote.digits || 2)}</Typography>
              </Box>
              <Box>
                <Typography variant="caption" color="text.secondary">Ask</Typography>
                <Typography variant="h5" style={{ color: theme.palette.error.main }}>{selectedQuote.ask?.toFixed(selectedQuote.digits || 2)}</Typography>
              </Box>
              <Box>
                <Typography variant="caption" color="text.secondary">Spread</Typography>
                <Typography variant="h5">{selectedQuote.spread?.toFixed(1)} pips</Typography>
              </Box>
              <Box>
                <Typography variant="caption" color="text.secondary">VariaÃƒÂ§ÃƒÂ£o %</Typography>
                <Typography variant="h5" style={{
                  color: selectedQuote.change_pct >= 0 ? theme.palette.success.main : theme.palette.error.main
                }}>
                  {selectedQuote.change_pct >= 0 ? '+' : ''}{selectedQuote.change_pct?.toFixed(2)}%
                </Typography>
              </Box>
              <Box>
                <Typography variant="caption" color="text.secondary">Volume</Typography>
                <Typography variant="h5">{selectedQuote.volume?.toFixed(0)}</Typography>
              </Box>
            </Box>
          ) : (
            <Typography color="text.secondary">Clique em um sÃƒÂ­mbolo na tabela abaixo</Typography>
          )}
        </CardContent>
      </Card>

      <TableContainer component={Card} sx={{ bgcolor: 'background.paper' }}>
        <Table size="small">
          <TableHead>
            <TableRow>
              <TableCell>SÃƒÂ­mbolo</TableCell>
              <TableCell align="right">ÃƒÅ¡ltimo</TableCell>
              <TableCell align="right">Bid</TableCell>
              <TableCell align="right">Ask</TableCell>
              <TableCell align="right">Spread (pips)</TableCell>
              <TableCell align="right">Var. %</TableCell>
              <TableCell align="right">Var.</TableCell>
              <TableCell>Fonte</TableCell>
            </TableRow>
          </TableHead>
          <TableBody>
            {filtered.length === 0 && (
              <TableRow>
                <TableCell colSpan={8} align="center" sx={{ py: 3 }}>
                  <Typography color="text.secondary">Aguardando dados de mercado...</Typography>
                </TableCell>
              </TableRow>
            )}
            {filtered.map((q) => (
              <TableRow
                key={q.symbol}
                hover
                onClick={() => setSelectedSymbol(q.symbol)}
                sx={{ cursor: 'pointer' }}
              >
                <TableCell>
                  <Chip
                    label={q.symbol}
                    size="small"
                    icon={q.change_pct >= 0 ? <TrendingUp /> : <TrendingDown />}
                    iconPosition="start"
                    color={q.change_pct >= 0 ? 'success' : 'error'}
                    sx={{ mr: 1 }}
                  />
                </TableCell>
                <TableCell align="right" sx={{ fontFamily: 'monospace' }}>
                  {q.last?.toFixed(q.digits || 2)}
                </TableCell>
                <TableCell align="right" sx={{ fontFamily: 'monospace', color: theme.palette.success.main }}>
                  {q.bid?.toFixed(q.digits || 2)}
                </TableCell>
                <TableCell align="right" sx={{ fontFamily: 'monospace', color: theme.palette.error.main }}>
                  {q.ask?.toFixed(q.digits || 2)}
                </TableCell>
                <TableCell align="right" sx={{ fontFamily: 'monospace' }}>
                  {q.spread?.toFixed(1)}
                </TableCell>
                <TableCell align="right">
                                    <Chip
                    label={`${q.change_pct >= 0 ? '+' : ''}${q.change_pct?.toFixed(2)}%`}
                    color={q.change_pct >= 0 ? 'success' : 'error'}
                    size="small"
                  />
                </TableCell>
                <TableCell align="right" style={{
                  color: q.change >= 0 ? theme.palette.success.main : theme.palette.error.main
                }}>
                  {q.change >= 0 ? '+' : ''}{q.change?.toFixed(4)}
                </TableCell>
                <TableCell>{q.source}</TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </TableContainer>
    </Box>
  );
}












