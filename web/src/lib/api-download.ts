import { getToken } from './auth-token';
import { getWorkspaceApiUrl } from './api-config';

export function apiDownload(path: string, signal?: AbortSignal): void {
  const token = getToken();
  const headers: Record<string, string> = {};
  if (token) headers.Authorization = `Bearer ${token}`;

  fetch(getWorkspaceApiUrl(path), { headers, signal })
    .then(res => res.blob())
    .then(blob => {
      const url = URL.createObjectURL(blob);
      const anchor = document.createElement('a');
      anchor.href = url;
      anchor.download = '';
      anchor.click();
      URL.revokeObjectURL(url);
    })
    .catch(error => {
      if ((error as Error).name !== 'AbortError') console.error(error);
    });
}
