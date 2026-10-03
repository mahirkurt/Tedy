import {CookieVault} from '../auth/cookieVault';
import {asyncStorageCookieStore} from '../auth/persistCookie';
import {TedyClient} from './client';

export const sessionVault = new CookieVault(asyncStorageCookieStore());
export const sessionClient = new TedyClient(sessionVault);
