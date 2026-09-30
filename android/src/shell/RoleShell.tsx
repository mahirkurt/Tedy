import React, {useMemo, useState} from 'react';
import {StyleSheet, View} from 'react-native';
import {
  BottomNavigationBar,
  Button,
  Text,
  getColor,
} from '@carbon/react-native';
import type {AuthUser} from '../data/user';
import type {TedyClient} from '../data/client';
import {TodayScreen} from '../today/TodayScreen';
import {WorkScreen} from '../work/WorkScreen';
import {AssistantScreen} from '../assistant/AssistantScreen';
import {LessonsScreen} from '../lessons/LessonsScreen';
import {BooksScreen} from '../books/BooksScreen';
import {MoreDestination, MoreList} from '../more/MoreScreen';
import {DESTINATION_ICONS} from './icons';
import {
  MORE_ID,
  MORE_LABEL,
  homeFor,
  primaryFor,
  secondaryFor,
  type Destination,
} from './routes';

function Surface({
  destination,
  client,
  onSessionExpired,
}: {
  destination: Destination | null;
  client: TedyClient;
  onSessionExpired: () => void;
}): React.JSX.Element {
  if (!destination || destination.id === 'today') {
    return <TodayScreen client={client} onSessionExpired={onSessionExpired} />;
  }
  if (destination.id === 'work') {
    return <WorkScreen />;
  }
  if (destination.id === 'assistant') {
    return <AssistantScreen />;
  }
  if (destination.id === 'lessons') {
    return <LessonsScreen />;
  }
  if (destination.id === 'books') {
    return <BooksScreen />;
  }
  return <MoreDestination item={destination} />;
}

export function RoleShell({
  user,
  client,
  onLogout,
}: {
  user: AuthUser;
  client: TedyClient;
  onLogout: () => void;
}): React.JSX.Element {
  const home = homeFor(user.role);
  const primary = primaryFor(user.role);
  const secondary = secondaryFor(user.role);
  const [currentId, setCurrentId] = useState(home.id);

  const allowed = useMemo(() => {
    const ids = new Set([...primary, ...secondary].map(item => item.id));
    if (secondary.length > 0) {
      ids.add(MORE_ID);
    }
    return ids;
  }, [primary, secondary]);

  const activeId = allowed.has(currentId) ? currentId : home.id;
  const showingMoreList = activeId === MORE_ID;
  const current =
    [...primary, ...secondary].find(item => item.id === activeId) ?? null;
  const moreActive =
    showingMoreList || secondary.some(item => item.id === activeId);

  const barItems = [
    ...primary.map(item => ({
      text: item.label,
      icon: DESTINATION_ICONS[item.id as keyof typeof DESTINATION_ICONS],
      active: activeId === item.id,
      onPress: () => setCurrentId(item.id),
    })),
    ...(secondary.length > 0
      ? [
          {
            text: MORE_LABEL,
            icon: DESTINATION_ICONS.more,
            active: moreActive,
            onPress: () => setCurrentId(MORE_ID),
          },
        ]
      : []),
  ];

  return (
    <View style={[styles.screen, {backgroundColor: getColor('background')}]}>
      <View style={styles.top}>
        <Text text="TEDY" type="heading-02" />
        <Button kind="ghost" text="Çıkış" onPress={onLogout} />
      </View>
      <View style={styles.body}>
        {showingMoreList ? (
          <MoreList items={secondary} onPress={setCurrentId} />
        ) : (
          <Surface
            destination={current}
            client={client}
            onSessionExpired={onLogout}
          />
        )}
      </View>
      <BottomNavigationBar items={barItems} />
    </View>
  );
}

const styles = StyleSheet.create({
  screen: {
    flex: 1,
  },
  top: {
    alignItems: 'center',
    flexDirection: 'row',
    justifyContent: 'space-between',
    paddingHorizontal: 16,
    paddingTop: 8,
  },
  body: {
    flex: 1,
  },
});
