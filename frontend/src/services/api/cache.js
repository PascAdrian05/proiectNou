const store = new Map();

export function getCachedValue(key) {
  const entry = store.get(key);
  if (!entry) {
    return null;
  }

  if (Date.now() > entry.expiresAt) {
    store.delete(key);
    return null;
  }

  return entry.value;
}

export function setCachedValue(key, value, ttlMs = 30000) {
  store.set(key, {
    value,
    expiresAt: Date.now() + ttlMs,
  });
}

export function invalidateCache(keys) {
  keys.forEach((key) => store.delete(key));
}
