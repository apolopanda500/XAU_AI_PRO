// Notificações nativas do SO via plugin Tauri, com fallback silencioso no modo web.
import { isPermissionGranted, requestPermission, sendNotification } from '@tauri-apps/plugin-notification';

export async function notify(title: string, body: string): Promise<void> {
  try {
    let granted = await isPermissionGranted();
    if (!granted) {
      const permission = await requestPermission();
      granted = permission === 'granted';
    }
    if (granted) sendNotification({ title, body });
  } catch {
    // Modo web (fora do Tauri) ou permissão negada: falha em silêncio.
  }
}