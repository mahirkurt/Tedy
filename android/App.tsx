import React, {useCallback, useEffect, useState} from 'react';
import {StatusBar, StyleSheet, View} from 'react-native';
import {SafeAreaView} from 'react-native-safe-area-context';
import {Text, getColor} from '@carbon/react-native';
import {LoginScreen} from './src/auth/LoginScreen';
import {signOutGoogle} from './src/auth/googleSignIn';
import {sessionClient} from './src/data/sessionClient';
import {restoreSession, type AuthUser} from './src/data/user';
import {RoleShell} from './src/shell/RoleShell';

function App(): React.JSX.Element {
  const [user, setUser] = useState<AuthUser | null>(null);
  const [ready, setReady] = useState(false);
  const background = getColor('background');

  useEffect(() => {
    let alive = true;
    (async () => {
      const restored = await restoreSession(sessionClient);
      if (!alive) {
        return;
      }
      setUser(restored);
      setReady(true);
    })();
    return () => {
      alive = false;
    };
  }, []);

  const onLogout = useCallback(async () => {
    setUser(null);
    try {
      await sessionClient.postJson('/api/auth/logout', {});
    } catch {
      // Local sign-out still stands when the panel is unreachable.
    }
    await sessionClient.vault.clear();
    await signOutGoogle();
  }, []);

  let body: React.JSX.Element;
  if (!ready) {
    body = (
      <View style={styles.waiting}>
        <Text text="Oturum kontrol ediliyor." type="body-01" />
      </View>
    );
  } else if (!user) {
    body = <LoginScreen client={sessionClient} onSignedIn={setUser} />;
  } else {
    body = <RoleShell user={user} client={sessionClient} onLogout={onLogout} />;
  }

  return (
    <SafeAreaView style={[styles.screen, {backgroundColor: background}]}>
      <StatusBar barStyle="dark-content" backgroundColor={background} />
      {body}
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  screen: {
    flex: 1,
  },
  waiting: {
    flex: 1,
    justifyContent: 'center',
    padding: 16,
  },
});

export default App;
