export function createEventSource(url, options = {}) {
  const session = options.session;
  const headers = options.headers || {};

  if (session?.accessToken) {
    headers.Authorization = `Bearer ${session.accessToken}`;
  }

  return new EventSource(url, { headers });
}

export async function* readEventStream(source) {
  try {
    while (source.readyState !== EventSource.CLOSED) {
      await new Promise((resolve) => {
        source.onmessage = (event) => {
          resolve({ data: JSON.parse(event.data) });
        };
        source.onerror = () => {
          source.close();
          resolve({ error: new Error("Event stream error") });
        };
      });
      yield source;
    }
  } catch (error) {
    source.close();
    throw error;
  }
}