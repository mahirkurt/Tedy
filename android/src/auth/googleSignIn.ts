import {
  GoogleSignin,
  isErrorWithCode,
  isSuccessResponse,
  statusCodes,
} from '@react-native-google-signin/google-signin';
import {WEB_CLIENT_ID} from './webClient';

let configured = false;

export function configureGoogleSignIn(): void {
  if (configured) {
    return;
  }
  GoogleSignin.configure({
    webClientId: WEB_CLIENT_ID,
    offlineAccess: false,
  });
  configured = true;
}

export type GoogleIdTokenResult =
  | {ok: true; idToken: string}
  | {ok: false; message: string};

function googleFailureSentence(error: unknown): string {
  if (isErrorWithCode(error)) {
    if (error.code === statusCodes.SIGN_IN_CANCELLED) {
      return 'Giriş iptal edildi.';
    }
    if (error.code === statusCodes.IN_PROGRESS) {
      return 'Giriş zaten sürüyor.';
    }
    if (error.code === statusCodes.PLAY_SERVICES_NOT_AVAILABLE) {
      return 'Bu cihazda Google Play hizmeti yok.';
    }
  }
  return 'Google ile giriş tamamlanamadı. Biraz sonra yeniden dene.';
}

/** ID token whose audience is the existing web client. No API key is involved. */
export async function requestGoogleIdToken(): Promise<GoogleIdTokenResult> {
  try {
    configureGoogleSignIn();
    await GoogleSignin.hasPlayServices({showPlayServicesUpdateDialog: true});
    const response = await GoogleSignin.signIn();
    if (isSuccessResponse(response)) {
      const idToken = response.data.idToken;
      if (idToken) {
        return {ok: true, idToken};
      }
      return {ok: false, message: 'Google kimliği alınamadı. Yeniden dene.'};
    }
    return {ok: false, message: 'Giriş iptal edildi.'};
  } catch (error) {
    return {ok: false, message: googleFailureSentence(error)};
  }
}

export async function signOutGoogle(): Promise<void> {
  try {
    configureGoogleSignIn();
    await GoogleSignin.signOut();
  } catch {
    // A missing Android OAuth client must not block clearing the local session.
  }
}
