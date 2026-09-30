export type Role = 'full' | 'reader';

/** Shape of POST /api/auth/login and GET /api/auth/me. */
export interface AuthUser {
  email: string;
  name: string;
  picture: string;
  role: Role;
  student: boolean;
}

/** Anything the API does not label "full" is least privilege. */
export function parseUser(data: unknown): AuthUser | null {
  if (!data || typeof data !== 'object') {
    return null;
  }
  const row = data as Record<string, unknown>;
  const email = typeof row.email === 'string' ? row.email : '';
  if (!email) {
    return null;
  }
  return {
    email,
    name: typeof row.name === 'string' ? row.name : '',
    picture: typeof row.picture === 'string' ? row.picture : '',
    role: row.role === 'full' ? 'full' : 'reader',
    student: row.student === true,
  };
}

export function loginFailureSentence(status: number): string {
  if (status === 403) {
    return 'Bu hesapla giriş yapılamaz.';
  }
  if (status === 400) {
    return 'Google kimliği eksik. Yeniden dene.';
  }
  return 'Giriş tamamlanamadı. Biraz sonra yeniden dene.';
}

export async function loginWithIdToken(
  client: {postJson(path: string, body: unknown): Promise<Response>},
  credential: string,
): Promise<{ok: true; user: AuthUser} | {ok: false; message: string}> {
  if (!credential.trim()) {
    return {ok: false, message: 'Google kimliği alınamadı. Yeniden dene.'};
  }
  let response: Response;
  try {
    response = await client.postJson('/api/auth/login', {credential});
  } catch {
    return {
      ok: false,
      message: 'Panele şu an ulaşılamıyor. Biraz sonra yeniden dene.',
    };
  }
  if (!response.ok) {
    return {ok: false, message: loginFailureSentence(response.status)};
  }
  let body: unknown = null;
  try {
    body = await response.json();
  } catch {
    body = null;
  }
  const user = parseUser(body);
  if (!user) {
    return {
      ok: false,
      message: 'Giriş tamamlanamadı. Biraz sonra yeniden dene.',
    };
  }
  return {ok: true, user};
}

export async function restoreSession(client: {
  vault: {header(): Promise<string | null>; clear(): Promise<void>};
  get(path: string): Promise<Response>;
}): Promise<AuthUser | null> {
  const cookie = await client.vault.header();
  if (!cookie) {
    return null;
  }
  try {
    const response = await client.get('/api/auth/me');
    if (!response.ok) {
      if (response.status === 401) {
        await client.vault.clear();
      }
      return null;
    }
    return parseUser(await response.json());
  } catch {
    return null;
  }
}
