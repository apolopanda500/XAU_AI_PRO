// @ts-nocheck
// @ts-nocheck
import { useAppStore } from '../../hooks/useAppStore';

export default function DashboardTab() {
  const theme = useTheme();
  const { quotes, account, positions, wsConnected, systemState } = useAppStore();

  return (
    <Box>
      <Typography variant="h4" sx={{ mb: 3, fontWeight: 'bold' }}>
        XAU AI PRO - Trading Dashboard
      </Typography>

      {/* Cards de status */}
      <Grid container spacing={2} sx={{ mb: 3 }}>
        <Grid item xs={12} sm={3}>
          <Card sx={{ bgcolor: 'background.paper' }}>
            <CardContent>
              <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, mb: 1 }}>
                <Box sx={{ width: 10, height: 10, borderRadius: '50%', bgcolor: wsConnected ? 'success.main' : 'error.main' }} />
                <Typography variant="caption" color={wsConnected ? 'success.main' : 'error.main'} fontWeight="bold">
                  {wsConnected ? 'WebSocket Online' : 'WebSocket Offline'}
                </Typography>
              </Box>
              <Typography variant="h6" color="text.secondary">ConexÃƒÂ£o</Typography>
            </CardContent>
          </Card>
        </Grid>

        <Grid item xs={12} sm={3}>
          <Card sx={{ bgcolor: 'background.paper' }}>
            <CardContent>
              <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, mb: 1 }}>
                <AccountBalance sx={{ color: theme.palette.primary.main, fontSize: 20 }} />
                <Typography variant="h5" fontWeight="bold">
                  {account ? `$${account.balance.toFixed(2)}` : '---'}
                </Typography>
              </Box>
              <Typography variant="h6" color="text.secondary">Saldo</Typography>
              {account && (
                <Typography variant="caption" color="text.secondary">
                  Equity: ${account.equity.toFixed(2)} | Free: ${account.free_margin.toFixed(2)}
                </Typography>
              )}
            </CardContent>
          </Card>
        </Grid>

        <Grid item xs={12} sm={3}>
          <Card sx={{ bgcolor: 'background.paper' }}>
            <CardContent>
              <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, mb: 1 }}>
                <ShowChart sx={{ color: theme.palette.success.main, fontSize: 20 }} />
                <Typography variant="h5" fontWeight="bold">
                  {positions.length}
                </Typography>
              </Box>
              <Typography variant="h6" color="text.secondary">PosiÃƒÂ§ÃƒÂµes Abertas</Typography>
            </CardContent>
          </Card>
        </Grid>

        <Grid item xs={12} sm={3}>
          <Card sx={{ bgcolor: 'background.paper' }}>
            <CardContent>
              <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, mb: 1 }}>
                <TrendingUp sx={{ color: theme.palette.warning.main, fontSize: 20 }} />
                <Typography variant="h5" fontWeight="bold">
                  {systemState?.status || '---'}
                </Typography>
              </Box>
              <Typography variant="h6" color="text.secondary">Status do Sistema</Typography>
            </CardContent>
          </Card>
        </Grid>
      </Grid>

      {/* Tabela de cotaÃƒÂ§ÃƒÂµes */}
      <Card sx={{ bgcolor: 'background.paper', mb: 3 }}>
        <CardHeader title="CotaÃƒÂ§ÃƒÂµes em Tempo Real" />
        <TableContainer component={Paper} sx={{ bgcolor: 'background.paper' }}>
          <Table size="small">
            <TableHead>
              <TableRow>
                <TableCell>SÃƒÂ­mbolo</TableCell>
                <TableCell align="right">PreÃƒÂ§o</TableCell>
                <TableCell align="right">Bid</TableCell>
                <TableCell align="right">Ask</TableCell>
                <TableCell align="right">Spread</TableCell>
                <TableCell align="right">VariaÃƒÂ§ÃƒÂ£o</TableCell>
                <TableCell align="right">Volume</TableCell>
                <TableCell>Fonte</TableCell>
              </TableRow>
            </TableHead>
            <TableBody>
              {quotes.map((q) => (
                <TableRow key={q.symbol} hover>
                  <TableCell>
                    <Typography variant="body2" fontWeight="bold">{q.symbol}</Typography>
                  </TableCell>
                  <TableCell align="right">{q.price?.toFixed(2) || '---'}</TableCell>
                  <TableCell align="right">{q.bid?.toFixed(2) || '---'}</TableCell>
                  <TableCell align="right">{q.ask?.toFixed(2) || '---'}</TableCell>
                  <TableCell align="right">{q.spread?.toFixed(1) || '0'} pips</TableCell>
                  <TableCell align="right">
                    <Chip
                                          label={`${q.change_pct >= 0 ? '+' : ''}${q.change_pct?.toFixed(2) || '0'}%`}
                      color={q.change_pct >= 0 ? 'success' : 'error'}
                      size="small"
                    />
                  </TableCell>
                  <TableCell align="right">{q.volume?.toFixed(0) || '0'}</TableCell>
                  <TableCell>{q.source}</TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </TableContainer>
      </Card>

      {/* PosiÃƒÂ§ÃƒÂµes recentes */}
      {positions.length > 0 && (
        <Card sx={{ bgcolor: 'background.paper' }}>
          <CardHeader title="PosiÃƒÂ§ÃƒÂµes Abertas" />
          <TableContainer>
            <Table size="small">
              <TableHead>
                <TableRow>
                  <TableCell>Ticket</TableCell>
                  <TableCell>SÃƒÂ­mbolo</TableCell>
                  <TableCell>Side</TableCell>
                  <TableCell align="right">Volume</TableCell>
                  <TableCell align="right">Open Price</TableCell>
                  <TableCell align="right">Current</TableCell>
                  <TableCell align="right">Profit</TableCell>
                </TableRow>
              </TableHead>
              <TableBody>
                {positions.map((p) => (
                  <TableRow key={p.ticket} hover>
                    <TableCell>{p.ticket}</TableCell>
                    <TableCell>{p.symbol}</TableCell>
                    <TableCell>
                      <Chip label={p.side} color={p.side === 'BUY' ? 'success' : 'error'} size="small" />
                    </TableCell>
                    <TableCell align="right">{p.volume}</TableCell>
                    <TableCell align="right">{p.open_price.toFixed(2)}</TableCell>
                    <TableCell align="right">{p.current_price.toFixed(2)}</TableCell>
                    <TableCell align="right" style={{ color: p.profit >= 0 ? '#00c853' : '#ff3d57' }}>
                      ${p.profit.toFixed(2)}
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </TableContainer>
        </Card>
      )}
    </Box>
  );
}












