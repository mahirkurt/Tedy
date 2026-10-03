import React from 'react';
import {StyleSheet, View} from 'react-native';
import {ErrorState, getColor} from '@carbon/react-native';

export function EmptySurface({
  title,
  sentence,
}: {
  title: string;
  sentence: string;
}): React.JSX.Element {
  return (
    <View style={[styles.screen, {backgroundColor: getColor('background')}]}>
      <ErrorState type="empty" title={title} subTitle={sentence} noImage />
    </View>
  );
}

const styles = StyleSheet.create({
  screen: {
    flex: 1,
  },
});
