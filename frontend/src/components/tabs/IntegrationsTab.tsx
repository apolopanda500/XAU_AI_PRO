// @ts-nocheck
// @ts-nocheck
import { useAppStore } from '../../hooks/useAppStore';

export default function IntegrationsTab() {
  const { settings, setSettings } = useAppStore();
  const [slackWebhook, setSlackWebhook] = useState('');
  const [telegramBot, setTelegramBot] = useState('');
  const [discordWebhook, setDiscordWebhook] = useState('');

  const saveIntegration = (type: string) => {
    console.log(`Salvando ${type}`);
  };

  return (
    <Box>
      <Typography variant="h4" sx={{ mb: 3, fontWeight: 'bold' }}>
        IntegraÃƒÂ§ÃƒÂµes
      </Typography>

      <Grid container spacing={3}>
        {/* Slack */}
        <Grid item xs={12} md={4}>
          <Card sx={{ bgcolor: 'background.paper' }}>
            <CardHeader
              title="Slack"
              titleTypographyProps={{ style: { color: '#4A154F' } }}
            />
            <CardContent>
              <TextField
                label="Webhook URL"
                value={slackWebhook}
                onChange={(e) => setSlackWebhook(e.target.value)}
                fullWidth
                size="small"
                margin="dense"
              />
              <FormControlLabel control={<Switch defaultChecked />} label="Ativo" />
              <Button variant="contained" fullWidth sx={{ mt: 1 }} onClick={() => saveIntegration('slack')}>
                Salvar
              </Button>
            </CardContent>
          </Card>
        </Grid>

        {/* Telegram */}
        <Grid item xs={12} md={4}>
          <Card sx={{ bgcolor: 'background.paper' }}>
            <CardHeader
              title="Telegram"
              titleTypographyProps={{ style: { color: '#0088cc' } }}
            />
            <CardContent>
              <TextField
                label="Bot Token"
                value={telegramBot}
                onChange={(e) => setTelegramBot(e.target.value)}
                fullWidth
                size="small"
                margin="dense"
              />
              <TextField
                label="Chat ID"
                fullWidth
                size="small"
                margin="dense"
              />
              <FormControlLabel
                control={
                  <Switch
                    defaultChecked
                    onChange={(_, checked) => setSettings({ notifications: checked })}
                  />
                }
                label="NotificaÃƒÂ§ÃƒÂµes"
              />
              <Button variant="contained" fullWidth sx={{ mt: 1 }} onClick={() => saveIntegration('telegram')}>
                Salvar
              </Button>
            </CardContent>
          </Card>
        </Grid>

        {/* Discord */}
        <Grid item xs={12} md={4}>
          <Card sx={{ bgcolor: 'background.paper' }}>
            <CardHeader
              title="Discord"
              titleTypographyProps={{ style: { color: '#7289DA' } }}
            />
            <CardContent>
              <TextField
                label="Webhook URL"
                value={discordWebhook}
                onChange={(e) => setDiscordWebhook(e.target.value)}
                fullWidth
                size="small"
                margin="dense"
              />
              <FormControlLabel control={<Switch />} label="Ativo" />
              <Button variant="contained" fullWidth sx={{ mt: 1 }} onClick={() => saveIntegration('discord')}>
                Salvar
              </Button>
            </CardContent>
          </Card>
        </Grid>
      </Grid>
    </Box>
  );
}











