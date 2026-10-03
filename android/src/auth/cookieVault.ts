export interface CookieStore {
  read(): Promise<string | null>;
  write(value: string | null): Promise<void>;
}

export class MemoryCookieStore implements CookieStore {
  constructor(private value: string | null = null) {}

  async read(): Promise<string | null> {
    return this.value;
  }

  async write(value: string | null): Promise<void> {
    this.value = value;
  }
}

type HeaderBag = {
  get(name: string): string | null;
  getSetCookie?: () => string[];
};

export function readSetCookieLines(headers: HeaderBag): string[] {
  if (typeof headers.getSetCookie === 'function') {
    const many = headers.getSetCookie();
    if (many && many.length > 0) {
      return many;
    }
  }
  const single = headers.get('set-cookie');
  return single ? [single] : [];
}

/** `session=…; HttpOnly; Path=/` → `session=…`. */
export function pairFromSetCookie(line: string): string | null {
  const pair = line.split(';', 1)[0]?.trim() ?? '';
  const eq = pair.indexOf('=');
  if (eq <= 0) {
    return null;
  }
  return pair;
}

export function mergeCookieHeader(
  existing: string | null,
  pairs: string[],
): string | null {
  const map = new Map<string, string>();
  for (const part of (existing ?? '').split(';')) {
    const trimmed = part.trim();
    const eq = trimmed.indexOf('=');
    if (eq > 0) {
      map.set(trimmed.slice(0, eq), trimmed);
    }
  }
  for (const pair of pairs) {
    const eq = pair.indexOf('=');
    if (eq > 0) {
      map.set(pair.slice(0, eq), pair);
    }
  }
  if (map.size === 0) {
    return null;
  }
  return [...map.values()].join('; ');
}

/**
 * React Native has no browser cookie jar. The Flask session cookie is kept
 * here and sent back as a Cookie header.
 */
export class CookieVault {
  constructor(private store: CookieStore) {}

  async header(): Promise<string | null> {
    const value = (await this.store.read())?.trim() ?? '';
    return value.length > 0 ? value : null;
  }

  async clear(): Promise<void> {
    await this.store.write(null);
  }

  async absorb(headers: HeaderBag): Promise<void> {
    const pairs = readSetCookieLines(headers)
      .map(pairFromSetCookie)
      .filter((pair): pair is string => pair !== null);
    if (pairs.length === 0) {
      return;
    }
    const existing = await this.store.read();
    await this.store.write(mergeCookieHeader(existing, pairs));
  }
}
