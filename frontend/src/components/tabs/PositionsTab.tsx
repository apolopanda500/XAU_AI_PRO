// @ts-nocheck
// @ts-nocheck
import { useAppStore } from '../../hooks/useAppStore';

export default function PositionsTab() {
  const theme = useTheme();
  const { positions, account, orders } = useAppStore();
  const [openDialog, setOpenDialog] = useState(false);
  const [orderSymbol, setOrderSymbol] = useState('');
  const [orderVolume, setOrderVolume] = useState('');
  const [orderType, setOrderType] = useState('BUY');

  React.useEffect(() => {
    // fetch positions/orders via API se backend disponivel
  }, []);

  const totalProfit = positions.reduce((sum, p) => sum + p.profit, 0);
  const totalPositions = positions.length;

  return (
    <Box>
      <Typography variant="h4" sx={{ mb: 3, fontWeight: 'bold' }}>
        Carteira - PosiÃƒÆ’Ã‚Â§ÃƒÆ’Ã‚Âµes & Ordens
      </Typography>

      <Grid container spacing={2} sx={{ mb: 3 }}>
        <Grid item xs={12} sm={4}>
          <Card sx={{ bgcolor: 'background.paper' }}>
            <CardContent>
              <Typography variant="caption" color="text.secondary">PosiÃƒÆ’Ã‚Â§ÃƒÆ’Ã‚Âµes Abertas</Typography>
              <Typography variant="h5" fontWeight="bold">{totalPositions}</Typography>
            </CardContent>
          </Card>
        </Grid>
        <Grid item xs={12} sm={4}>
          <Card sx={{ bgcolor: 'background.paper' }}>
            <CardContent>
              <Typography variant="caption" color="text.secondary">P&L Total</Typography>
              <Typography variant="h5" fontWeight="bold" style={{ color: totalProfit >= 0 ? '#00c853' : '#ff3d57' }}>
                ${totalProfit.toFixed(2)}
              </Typography>
            </CardContent>
          </Card>
        </Grid>
        <Grid item xs={12} sm={4}>
          <Card sx={{ bgcolor: 'background.paper' }}>
            <CardContent>
              <Typography variant="caption" color="text.secondary">Ordens Pendentes</Typography>
              <Typography variant="h5" fontWeight="bold">{orders.length}</Typography>
            </CardContent>
          </Card>
        </Grid>
      </Grid>

      {/* PosiÃƒÆ’Ã‚Â§ÃƒÆ’Ã‚Âµes */}
      <Card sx={{ bgcolor: 'background.paper', mb: 3 }}>
        <CardHeader title="PosiÃƒÆ’Ã‚Â§ÃƒÆ’Ã‚Âµes Abertas" />
        <TableContainer>
          <Table size="small">
            <TableHead>
              <TableRow>
                <TableCell>Ticket</TableCell>
                <TableCell>SÃƒÆ’Ã‚Â­mbolo</TableCell>
                <TableCell>Side</TableCell>
                <TableCell align="right">Volume</TableCell>
                <TableCell align="right">Open Price</TableCell>
                <TableCell align="right">Current Price</TableCell>
                <TableCell align="right">SL</TableCell>
                <TableCell align="right">TP</TableCell>
                <TableCell align="right">Profit</TableCell>
                <TableCell>Magic</TableCell>
              </TableRow>
            </TableHead>
            <TableBody>
              {positions.length === 0 && (
                <TableRow>
                  <TableCell colSpan={11} align="center" sx={{ py: 3 }}>
                    <Typography color="text.secondary">Nenhuma posiÃƒÆ’Ã‚Â§ÃƒÆ’Ã‚Â£o aberta</Typography>
                  </TableCell>
                </TableRow>
              )}
              {positions.map((p) => (
                <TableRow key={p.ticket} hover>
                  <TableCell>{p.ticket}</TableCell>
                  <TableCell>{p.symbol}</TableCell>
                  <TableCell>
                    <Chip label={p.side} color={p.side === 'BUY' || p.side === 'LONG' ? 'success' : 'error'} size="small" />
                  </TableCell>
                  <TableCell align="right">{p.volume}</TableCell>
                  <TableCell align="right" sx={{ fontFamily: 'monospace' }}>{p.open_price.toFixed(2)}</TableCell>
                  <TableCell align="right" sx={{ fontFamily: 'monospace' }}>{p.current_price.toFixed(2)}</TableCell>
                  <TableCell align="right" sx={{ fontFamily: 'monospace' }}>{p.sl?.toFixed(2) || '-'}</TableCell>
                  <TableCell align="right" sx={{ fontFamily: 'monospace' }}>{p.tp?.toFixed(2) || '-'}</TableCell>
                  <TableCell align="right" style={{ color: p.profit >= 0 ? '#00c853' : '#ff3d57' }}>
                    ${p.profit.toFixed(2)}
                  </TableCell>
                  <TableCell>{p.magic}</TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </TableContainer>
      </Card>

      {/* Ordens Pendentes */}
      <Card sx={{ bgcolor: 'background.paper' }}>
        <CardHeader
          title="Ordens Pendentes"
          action={
            <Button variant="contained" size="small" onClick={() => setOpenDialog(true)}>
              Nova Ordem
            </Button>
          }
        />
        <TableContainer>
          <Table size="small">
            <TableHead>
              <TableRow>
                <TableCell>Ticket</TableCell>
                <TableCell>SÃƒÆ’Ã‚Â­mbolo</TableCell>
                <TableCell>Tipo</TableCell>
                <TableCell align="right">PreÃƒÆ’Ã‚Â§o</TableCell>
                <TableCell align="right">Volume</TableCell>
                <TableCell align="right">SL</TableCell>
                <TableCell align="right">TP</TableCell>
                <TableCell>Status</TableCell>
              </TableRow>
            </TableHead>
            <TableBody>
              {orders.length === 0 && (
                <TableRow>
                  <TableCell colSpan={8} align="center" sx={{ py: 3 }}>
                    <Typography color="text.secondary">Nenhuma ordem pendente</Typography>
                  </TableCell>
                </TableRow>
              )}
              {orders.map((o) => (
                <TableRow key={o.ticket} hover>
                  <TableCell>{o.ticket}</TableCell>
                  <TableCell>{o.symbol}</TableCell>
                  <TableCell>{o.type}</TableCell>
                  <TableCell align="right">{o.price.toFixed(2)}</TableCell>
                  <TableCell align="right">{o.volume}</TableCell>
                  <TableCell align="right">{o.sl.toFixed(2)}</TableCell>
                  <TableCell align="right">{o.tp.toFixed(2)}</TableCell>
                  <TableCell>{o.type_time}</TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </TableContainer>
      </Card>

      {/* DiÃƒÆ’Ã‚Â¡logo de Nova Ordem */}
      <Dialog open={openDialog} onClose={() => setOpenDialog(false)} maxWidth="sm" fullWidth>
        <DialogTitle>Nova Ordem</DialogTitle>
        <DialogContent>
          <Box sx={{ display: 'grid', gridTemplateColumns: 'repeat(2, 1fr)', gap: 2, mt: 1 }}>
            <TextField label="SÃƒÆ’Ã‚Â­mbolo" value={orderSymbol} onChange={(e) => setOrderSymbol(e.target.value)} size="small" />
            <TextField label="Volume" value={orderVolume} onChange={(e) => setOrderVolume(e.target.value)} size="small" type="number" />
            <TextField label="Tipo" value={orderType} onChange={(e) => setOrderType(e.target.value)} size="small" />
            <TextField label="SL" type="number" size="small" />
            <TextField label="TP" type="number" size="small" />
          </Box>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setOpenDialog(false)}>Cancelar</Button>
          <Button variant="contained" color="primary" onClick={() => {
            // enviar ordem via WebSocket
            setOpenDialog(false);
          }}>
            Enviar Ordem
          </Button>
        </DialogActions>
      </Dialog>
    </Box>
  );
}











