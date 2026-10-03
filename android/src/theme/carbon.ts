import {forceTheme, getColor} from '@carbon/react-native';

// School screens use Carbon g10 (light). The book reader does not.
forceTheme('light');

export {forceTheme, getColor};
