import {CookieVault} from '../auth/cookieVault';

export const API_ORIGIN = 'https://tedy.online';

export type FetchLike = (
  input: string,
  init?: RequestInit,
) => Promise<Response>;

/**
 * tedy.online client. The session cookie is attached by hand because
 * React Native does not keep a browser cookie jar.
 */
export class TedyClient {
  constructor(
    readonly vault: CookieVault,
    private fetchImpl: FetchLike = fetch,
    private origin: string = API_ORIGIN,
  ) {}

  async request(path: string, init: RequestInit = {}): Promise<Response> {
    const headers = new Headers(init.headers);
    const cookie = await this.vault.header();
    if (cookie) {
      headers.set('Cookie', cookie);
    }
    const response = await this.fetchImpl(`${this.origin}${path}`, {
      ...init,
      headers,
    });
    await this.vault.absorb(response.headers);
    return response;
  }

  get(path: string): Promise<Response> {
    return this.request(path, {method: 'GET'});
  }

  postJson(path: string, body: unknown): Promise<Response> {
    return this.request(path, {
      method: 'POST',
      headers: {
        Accept: 'application/json',
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(body),
    });
  }
}
