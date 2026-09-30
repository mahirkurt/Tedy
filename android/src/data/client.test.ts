import {CookieVault, MemoryCookieStore} from '../auth/cookieVault';
import {TedyClient, type FetchLike} from './client';

test('a stored session cookie is sent as a Cookie header', async () => {
  const vault = new CookieVault(new MemoryCookieStore('session=stored-value'));
  const seen: Array<string | null> = [];
  const fetchImpl: FetchLike = async (_url, init) => {
    seen.push(new Headers(init?.headers).get('Cookie'));
    return new Response('{}', {status: 200});
  };
  const client = new TedyClient(vault, fetchImpl, 'https://tedy.online');

  await client.get('/api/health');

  expect(seen).toEqual(['session=stored-value']);
});

test('a Set-Cookie from login is sent on the next request', async () => {
  const vault = new CookieVault(new MemoryCookieStore());
  const seen: Array<string | null> = [];
  const fetchImpl: FetchLike = async (url, init) => {
    seen.push(new Headers(init?.headers).get('Cookie'));
    if (String(url).endsWith('/api/auth/login')) {
      return new Response('{}', {
        status: 200,
        headers: {'set-cookie': 'session=abc; HttpOnly; Path=/; Secure'},
      });
    }
    return new Response('{}', {status: 200});
  };
  const client = new TedyClient(vault, fetchImpl, 'https://tedy.online');

  await client.postJson('/api/auth/login', {credential: 'id-token'});
  await client.get('/api/auth/me');

  expect(seen).toEqual([null, 'session=abc']);
});
