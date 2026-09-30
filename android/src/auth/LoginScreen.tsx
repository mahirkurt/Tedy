import React, {useState} from 'react';
import {StyleSheet, View} from 'react-native';
import {Button, Notification, Text, getColor} from '@carbon/react-native';
import {requestGoogleIdToken} from './googleSignIn';
import {loginWithIdToken} from '../data/user';
import type {TedyClient} from '../data/client';
import type {AuthUser} from '../data/user';

export function LoginScreen({
  client,
  onSignedIn,
}: {
  client: TedyClient;
  onSignedIn: (user: AuthUser) => void;
}): React.JSX.Element {
  const [message, setMessage] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  const onPress = async () => {
    if (busy) {
      return;
    }
    setBusy(true);
    setMessage(null);
    const google = await requestGoogleIdToken();
    if (!google.ok) {
      setMessage(google.message);
      setBusy(false);
      return;
    }
    const login = await loginWithIdToken(client, google.idToken);
    if (!login.ok) {
      setMessage(login.message);
      setBusy(false);
      return;
    }
    onSignedIn(login.user);
    setBusy(false);
  };

  return (
    <View style={[styles.screen, {backgroundColor: getColor('background')}]}>
      <Text text="TEDY" type="heading-05" style={styles.title} />
      <Text
        text="Okul paneline Google hesabınla gir."
        type="body-01"
        style={styles.lead}
      />
      {message ? (
        <Notification
          kind="error"
          title="Giriş olmadı"
          subTitle={message}
          onDismiss={() => setMessage(null)}
          onDismissText="Kapat"
          style={styles.notice}
        />
      ) : null}
      <Button
        text={busy ? 'Giriş yapılıyor' : 'Google ile giriş yap'}
        onPress={onPress}
        disabled={busy}
      />
    </View>
  );
}

const styles = StyleSheet.create({
  screen: {
    flex: 1,
    justifyContent: 'center',
    padding: 16,
  },
  title: {
    marginBottom: 8,
  },
  lead: {
    marginBottom: 24,
  },
  notice: {
    marginBottom: 16,
  },
});
