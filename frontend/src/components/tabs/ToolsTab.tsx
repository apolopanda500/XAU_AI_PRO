// @ts-nocheck
// @ts-nocheck
import { useAppStore } from '../../hooks/useAppStore';

export default function ToolsTab() {
  const { settings, setSettings, quotes } = useAppStore();

  return (
    <Box>
      <Typography variant="h4" sx={{ mb: 3, fontWeight: 'bold' }}>
        Ferramentas
      </Typography>

      <Grid container spacing={3}>
        {/* Calculator */}
        <Grid item xs={12} md={6}>
          <Card sx={{ bgcolor: 'background.paper' }}>
            <CardHeader title="Calculadora de PosiÃƒÂ§ÃƒÂ£o" />
            <CardContent>
              <Box sx={{ display: 'grid', gap: 2, gridTemplateColumns: 'repeat(2, 1fr)' }}>
                <TextField label="Conta (balanÃƒÂ§o)" size="small" type="number" defaultValue="10000" />
                <TextField label="Risco (%)" size="small" type="number" defaultValue="2" />
                <TextField label="PreÃƒÂ§o de Entrada" size="small" type="number" />
                <TextField label="SL (pips)" size="small" type="number" />
                <Button variant="contained" color="primary" sx={{ mt: 2 }}>Calcular</Button>
              </Box>
            </CardContent>
          </Card>
        </Grid>

        {/* Symbol Info */}
        <Grid item xs={12} md={6}>
          <Card sx={{ bgcolor: 'background.paper' }}>
            <CardHeader title="InformaÃƒÂ§ÃƒÂµes do SÃƒÂ­mbolo" />
            <CardContent>
              <Table size="small">
                <TableHead>
                  <TableRow>
                    <TableCell>SÃƒÂ­mbolo</TableCell>
                    <TableCell align="right">Bid</TableCell>
                    <TableCell align="right">Ask</TableCell>
                    <TableCell align="right">Spread</TableCell>
                    <TableCell>Categoria</TableCell>
                  </TableRow>
                </TableHead>
                <TableBody>
                  {quotes.slice(0, 8).map((q) => (
                    <TableRow key={q.symbol} hover>
                      <TableCell>{q.symbol}</TableCell>
                      <TableCell align="right" sx={{ fontFamily: 'monospace' }}>{q.bid.toFixed(2)}</TableCell>
                      <TableCell align="right" sx={{ fontFamily: 'monospace' }}>{q.ask.toFixed(2)}</TableCell>
                      <TableCell align="right">{q.spread.toFixed(1)}</TableCell>
                      <TableCell>
                        <Chip label="Forex" size="small" />
                      </TableCell>
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











