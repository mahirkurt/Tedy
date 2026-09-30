import AsyncStorage from '@react-native-async-storage/async-storage';
import type {CookieStore} from './cookieVault';

const STORAGE_KEY = 'tedy.session.cookie';

export function asyncStorageCookieStore(): CookieStore {
  return {
    async read() {
      return AsyncStorage.getItem(STORAGE_KEY);
    },
    async write(value) {
      if (!value) {
        await AsyncStorage.removeItem(STORAGE_KEY);
        return;
      }
      await AsyncStorage.setItem(STORAGE_KEY, value);
    },
  };
}
