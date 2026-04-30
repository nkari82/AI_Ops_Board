type CacheEntry<T> = {
  value: T;
  timestamp: number;
};

const cache = new Map<string, CacheEntry<unknown>>();

export function getCachedValue<T>(key: string, ttlMs: number): T | null {
  const entry = cache.get(key) as CacheEntry<T> | undefined;
  if (!entry) return null;

  if (Date.now() - entry.timestamp > ttlMs) {
    cache.delete(key);
    return null;
  }

  return entry.value;
}

export function setCachedValue<T>(key: string, value: T): void {
  cache.set(key, {
    value,
    timestamp: Date.now(),
  });
}

export function clearCachedValue(key: string): void {
  cache.delete(key);
}

export function clearCacheByPrefix(prefix: string): void {
  for (const key of cache.keys()) {
    if (key.startsWith(prefix)) {
      cache.delete(key);
    }
  }
}
