import { useEffect } from 'react';

export function useMobileResilientSync(onSyncNow: () => void, intervalMs = 5000): void {
  useEffect(() => {
    const handleResume = () => {
      if (document.visibilityState === 'visible' && navigator.onLine) {
        onSyncNow();
      }
    };

    const timer = window.setInterval(() => {
      if (document.visibilityState === 'visible' && navigator.onLine) {
        onSyncNow();
      }
    }, intervalMs);

    document.addEventListener('visibilitychange', handleResume);
    window.addEventListener('online', handleResume);
    window.addEventListener('focus', handleResume);

    return () => {
      window.clearInterval(timer);
      document.removeEventListener('visibilitychange', handleResume);
      window.removeEventListener('online', handleResume);
      window.removeEventListener('focus', handleResume);
    };
  }, [onSyncNow, intervalMs]);
}

export default useMobileResilientSync;
