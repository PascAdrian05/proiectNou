export function createEventSource(url, options = {}) {
  const session = options.session;
  const headers = options.headers || {};

  if (session?.accessToken) {
    // EventSource doesn't support headers natively, so we pass token as query param
    // The server needs to be updated to support this or use a library that supports headers
    const urlWithToken = new URL(url, window.location.origin);
    urlWithToken.searchParams.append("token", session.accessToken);
    return new EventSource(urlWithToken.toString());
  }

  return new EventSource(url);
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
