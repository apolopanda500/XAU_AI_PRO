// @ts-nocheck
// @ts-nocheck
import { useAppStore } from '../../hooks/useAppStore';

export default function RobotTab() {
  const { robotStatus, magicNumber, aiStatus, settings, setSettings, setRobotStatus } = useAppStore();
  const [eaCheckResult, setEaCheckResult] = useState('');
  const [openCloseDialog, setOpenCloseDialog] = useState(false);
  const [closeSymbol, setCloseSymbol] = useState('');

  const checkEA = () => {
    setEaCheckResult('Verificando EA...');
    setTimeout(() => {
      setEaCheckResult('EA Conectado - v2.1.0 | Magic: ' + magicNumber);
      setRobotStatus('Conectado ao MT5');
    }, 1500);
  };

  const connectMT5 = () => {
    setRobotStatus('Conectando ao MT5...');
    setTimeout(() => {
      setRobotStatus('Conectado ao MT5');
    }, 2000);
  };

  const disconnectMT5 = () => {
    setRobotStatus('Desconectando...');
    setTimeout(() => {
      setRobotStatus('Desconectado');
    }, 1000);
  };

  return (
    <Box>
      <Typography variant="h4" sx={{ mb: 3, fontWeight: 'bold' }}>
        Controle do RobÃƒÂ´ MT5
      </Typography>

      {/* Status do RobÃƒÂ´ */}
      <Card sx={{ bgcolor: 'background.paper', mb: 3 }}>
        <CardHeader
          title="Status do RobÃƒÂ´"
          titleTypographyProps={{ variant: 'h6' }}
        />
        <CardContent>
          <Box sx={{ display: 'flex', alignItems: 'center', gap: 2, mb: 2 }}>
            <Box sx={{ width: 12, height: 12, borderRadius: '50%', bgcolor: robotStatus.includes('Conectado') ? 'success.main' : 'warning.main' }} />
            <Typography variant="h6">{robotStatus}</Typography>
            {eaCheckResult && (
              <Chip label={eaCheckResult} variant="outlined" size="small" />
            )}
          </Box>

          <Grid container spacing={2}>
            <Grid item xs={12} sm={3}>
              <Button
                variant="contained"
                color="primary"
                onClick={connectMT5}
                fullWidth
                size="large"
              >
                Conectar MT5
              </Button>
            </Grid>
            <Grid item xs={12} sm={3}>
              <Button
                variant="outlined"
                color="warning"
                onClick={disconnectMT5}
                fullWidth
                size="large"
              >
                Desconectar
              </Button>
            </Grid>
            <Grid item xs={12} sm={3}>
              <Button
                variant="outlined"
                color="info"
                onClick={checkEA}
                fullWidth
                size="large"
              >
                Verificar EA
              </Button>
            </Grid>
            <Grid item xs={12} sm={3}>
              <Button
                variant="outlined"
                color="success"
                onClick={() => {}}
                fullWidth
                size="large"
              >
                Sincronizar PrediÃƒÂ§ÃƒÂµes
              </Button>
            </Grid>
          </Grid>
        </CardContent>
      </Card>

      {/* Health Check */}
      <Card sx={{ bgcolor: 'background.paper', mb: 3 }}>
        <CardHeader title="Health Check" />
        <CardContent>
          <Box sx={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', gap: 2 }}>
            <Box sx={{ p: 2, bgcolor: 'background.default', borderRadius: 1 }}>
              <Typography variant="caption" color="text.secondary">Terminal MT5</Typography>
              <Typography variant="h6" fontWeight="bold">Online</Typography>
            </Box>
            <Box sx={{ p: 2, bgcolor: 'background.default', borderRadius: 1 }}>
              <Typography variant="caption" color="text.secondary">EA Status</Typography>
              <Typography variant="h6" fontWeight="bold">Ativo</Typography>
            </Box>
            <Box sx={{ p: 2, bgcolor: 'background.default', borderRadius: 1 }}>
              <Typography variant="caption" color="text.secondary">Magic Number</Typography>
              <Typography variant="h6" fontWeight="bold">{magicNumber}</Typography>
            </Box>
            <Box sx={{ p: 2, bgcolor: 'background.default', borderRadius: 1 }}>
              <Typography variant="caption" color="text.secondary">PrediÃƒÂ§ÃƒÂµes</Typography>
              <Typography variant="h6" fontWeight="bold">Sincronizadas</Typography>
            </Box>
          </Box>
        </CardContent>
      </Card>

      {/* AÃƒÂ§ÃƒÂµes Manuais */}
      <Card sx={{ bgcolor: 'background.paper', mb: 3 }}>
        <CardHeader title="AÃƒÂ§ÃƒÂµes Manuais" />
        <CardContent>
          <Grid container spacing={2}>
            <Grid item xs={12} sm={2}>
              <TextField label="SÃƒÂ­mbolo" size="small" defaultValue="XAUUSD" fullWidth />
            </Grid>
            <Grid item xs={12} sm={2}>
              <TextField label="Volume" size="small" type="number" defaultValue="0.01" fullWidth />
            </Grid>
            <Grid item xs={12} sm={2}>
              <TextField label="SL" size="small" type="number" placeholder="Stop Loss" fullWidth />
            </Grid>
            <Grid item xs={12} sm={2}>
              <TextField label="TP" size="small" type="number" placeholder="Take Profit" fullWidth />
            </Grid>
            <Grid item xs={12} sm={4} sx={{ display: 'flex', gap: 1 }}>
              <Button variant="contained" color="success" onClick={() => {}}>
                BUY
              </Button>
              <Button variant="contained" color="error" onClick={() => {}}>
                SELL
              </Button>
              <Button variant="outlined" color="info" onClick={() => setOpenCloseDialog(true)}>
                Fechar PosiÃƒÂ§ÃƒÂ£o
              </Button>
            </Grid>
          </Grid>
        </CardContent>
      </Card>

      {/* AI Engine */}
      <Card sx={{ bgcolor: 'background.paper' }}>
        <CardHeader
          title="AI Engine"
          titleTypographyProps={{ variant: 'h6' }}
          subheader={`Status: ${aiStatus}`}
        />
        <CardContent>
          <Grid container spacing={2} alignItems="center">
            <Grid item xs={12} sm={6}>
              <FormControlLabel
                control={<Switch checked={settings.aiEnabled} onChange={(_, checked) => setSettings({ aiEnabled: checked })} />}
                label="AI Engine Ativado"
              />
            </Grid>
            <Grid item xs={12} sm={6} sx={{ textAlign: 'right' }}>
              <Button variant="contained" onClick={() => {}}>
                Treinar Agora
              </Button>
            </Grid>
          </Grid>
        </CardContent>
      </Card>

      {/* DiÃƒÂ¡logo Fechar PosiÃƒÂ§ÃƒÂ£o */}
      <Dialog open={openCloseDialog} onClose={() => setOpenCloseDialog(false)}>
        <DialogTitle>Fechar PosiÃƒÂ§ÃƒÂ£o</DialogTitle>
        <DialogContent>
          <TextField
            label="SÃƒÂ­mbolo"
            value={closeSymbol}
            onChange={(e) => setCloseSymbol(e.target.value)}
            fullWidth
            margin="dense"
          />
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setOpenCloseDialog(false)}>Cancelar</Button>
          <Button variant="contained" color="error" onClick={() => setOpenCloseDialog(false)}>
            Fechar Todas
          </Button>
        </DialogActions>
      </Dialog>
    </Box>
  );
}











