import React from 'react';
import {NavigationList} from '@carbon/react-native';
import type {Destination} from '../shell/routes';
import {EmptySurface} from '../shell/EmptySurface';

const SENTENCES: Record<string, string> = {
  grades: 'Notlar burada duracak.',
  calendar: 'Yaklaşan bir kayıt yok.',
  teams: 'Takım etkinliği burada duracak.',
  progress: 'Platform ilerlemesi burada duracak.',
  announcements: 'Yeni bir duyuru yok.',
  profile: 'Profil bilgisi burada duracak.',
  modules: 'Modüller burada duracak.',
};

export function MoreList({
  items,
  onPress,
}: {
  items: Destination[];
  onPress: (id: string) => void;
}): React.JSX.Element {
  return (
    <NavigationList
      style={{flex: 1}}
      items={items.map(item => ({
        id: item.id,
        text: item.label,
        hasChevron: true,
        onPress: () => onPress(item.id),
      }))}
    />
  );
}

export function MoreDestination({
  item,
}: {
  item: Destination;
}): React.JSX.Element {
  return (
    <EmptySurface
      title={item.label}
      sentence={SENTENCES[item.id] ?? 'Bu bölüm burada duracak.'}
    />
  );
}
