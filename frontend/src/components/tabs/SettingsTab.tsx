// @ts-nocheck
// @ts-nocheck
import { useAppStore } from '../../hooks/useAppStore';
import { Theme } from '../../hooks/useTheme';

export default function SettingsTab() {
  const { settings, setSettings } = useAppStore();

  const updateSetting = (key: string, value: any) => {
    setSettings({ [key]: value });
  };

  return (
    <Box>
      <Typography variant="h4" sx={{ mb: 3, fontWeight: 'bold' }}>
        ConfiguraÃƒÂ§ÃƒÂµes
      </Typography>

      <Grid container spacing={3}>
        <Grid item xs={12} md={6}>
          <Card sx={{ bgcolor: 'background.paper', mb: 3 }}>
            <CardHeader title="AparÃƒÂªncia" />
            <CardContent>
              <FormControl fullWidth sx={{ mb: 2 }} size="small">
                <InputLabel>Tema</InputLabel>
                <Select
                  value={settings.theme || 'dark'}
                  label="Tema"
                  onChange={(e) => updateSetting('theme', e.target.value)}
                >
                  <MenuItem value="dark">Dark (PadrÃƒÂ£o)</MenuItem>
                  <MenuItem value="xau_dark">XAU Dark</MenuItem>
                  <MenuItem value="btc_dark">BTC Dark</MenuItem>
                  <MenuItem value="light">Light</MenuItem>
                </Select>
              </FormControl>

              <FormControlLabel
                control={
                  <Switch
                    checked={settings.animations}
                    onChange={(_, checked) => updateSetting('animations', checked)}
                  />
                }
                label="AnimaÃƒÂ§ÃƒÂµes"
              />
              <FormControlLabel
                control={
                  <Switch
                    checked={settings.soundEnabled}
                    onChange={(_, checked) => updateSetting('soundEnabled', checked)}
                  />
                }
                label="Efeitos Sonoros"
              />
              <FormControlLabel
                control={
                  <Switch
                    checked={settings.autoScroll}
                    onChange={(_, checked) => updateSetting('autoScroll', checked)}
                  />
                }
                label="Auto-scroll"
              />
            </CardContent>
          </Card>

          <Card sx={{ bgcolor: 'background.paper' }}>
            <CardHeader title="NotificaÃƒÂ§ÃƒÂµes" />
            <CardContent>
              <FormControlLabel
                control={
                  <Switch
                    checked={settings.notifications}
                    onChange={(_, checked) => updateSetting('notifications', checked)}
                  />
                }
                label="NotificaÃƒÂ§ÃƒÂµes de Alertas"
              />
            </CardContent>
          </Card>
        </Grid>

        <Grid item xs={12} md={6}>
          <Card sx={{ bgcolor: 'background.paper', mb: 3 }}>
            <CardHeader title="MT5" />
            <CardContent>
              <TextField
                label="Terminal Path"
                value={settings.mt5Path || ''}
                onChange={(e) => updateSetting('mt5Path', e.target.value)}
                fullWidth
                size="small"
                margin="dense"
              />
              <FormControlLabel
                control={
                  <Switch
                    checked={settings.mt5AutoConnect}
                    onChange={(_, checked) => updateSetting('mt5AutoConnect', checked)}
                  />
                }
                label="Auto-conectar MT5"
              />
              <FormControlLabel
                control={
                  <Switch
                    checked={settings.aiEnabled}
                    onChange={(_, checked) => updateSetting('aiEnabled', checked)}
                  />
                }
                label="AI Engine Ativado"
              />
            </CardContent>
          </Card>

          <Card sx={{ bgcolor: 'background.paper' }}>
            <CardHeader title="Performance" />
            <CardContent>
              <TextField
                label="Precision (decimals)"
                type="number"
                value={settings.precision || 2}
                onChange={(e) => updateSetting('precision', parseInt(e.target.value))}
                fullWidth
                size="small"
                margin="dense"
              />
              <TextField
                label="Refresh Interval (ms)"
                type="number"
                value={settings.refreshInterval || 1000}
                onChange={(e) => updateSetting('refreshInterval', parseInt(e.target.value))}
                fullWidth
                size="small"
                margin="dense"
              />
            </CardContent>
          </Card>
        </Grid>
      </Grid>

      <Box sx={{ mt: 3, display: 'flex', justifyContent: 'flex-end', gap: 2 }}>
        <Button variant="outlined">Resetar ConfiguraÃƒÂ§ÃƒÂµes</Button>
        <Button variant="contained" color="primary">
          Salvar Tudo
        </Button>
      </Box>
    </Box>
  );
}











