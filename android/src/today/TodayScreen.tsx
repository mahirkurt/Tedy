import React, {useEffect, useState} from 'react';
import {StyleSheet, View} from 'react-native';
import {Text, getColor} from '@carbon/react-native';
import type {TedyClient} from '../data/client';
import {parseUser} from '../data/user';
import {parseHealth, todaySentence} from './sentence';

export function TodayScreen({
  client,
  onSessionExpired,
}: {
  client: TedyClient;
  onSessionExpired: () => void;
}): React.JSX.Element {
  const [sentence, setSentence] = useState('Bugün yükleniyor.');

  useEffect(() => {
    let alive = true;
    (async () => {
      try {
        const [healthRes, meRes] = await Promise.all([
          client.get('/api/health'),
          client.get('/api/auth/me'),
        ]);
        if (!alive) {
          return;
        }
        if (healthRes.status === 401 || meRes.status === 401) {
          setSentence(
            todaySentence({name: '', health: null, problem: 'session'}),
          );
          onSessionExpired();
          return;
        }
        if (!healthRes.ok || !meRes.ok) {
          setSentence(
            todaySentence({name: '', health: null, problem: 'unreachable'}),
          );
          return;
        }
        const user = parseUser(await meRes.json());
        const health = parseHealth(await healthRes.json());
        setSentence(
          todaySentence({
            name: user?.name ?? '',
            health,
            problem: 'none',
          }),
        );
      } catch {
        if (alive) {
          setSentence(
            todaySentence({name: '', health: null, problem: 'unreachable'}),
          );
        }
      }
    })();
    return () => {
      alive = false;
    };
  }, [client, onSessionExpired]);

  return (
    <View style={[styles.screen, {backgroundColor: getColor('background')}]}>
      <Text text="Bugün" type="heading-04" style={styles.title} />
      <Text text={sentence} type="body-01" />
    </View>
  );
}

const styles = StyleSheet.create({
  screen: {
    flex: 1,
    padding: 16,
  },
  title: {
    marginBottom: 12,
  },
});
