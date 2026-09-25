// Carbon token discipline for the dashboard's stylesheets (stylelint-plugin-carbon-tokens).
//
// Accepted beside Carbon's own tokens: the Tedy layer (--ted-*, --tedy-*: every
// value is a Carbon token or palette step, pinned by tests/test_tedy_tasarim_tutarliligi.py
// and tests/test_pano_tasarim_sistemi.py), its --status-* aliases, and Carbon
// palette steps named through @carbon/colors (`#{colors.$blue-10}`), which the
// design system allows where no role token fits.
//
// Tedy Books is out of scope: the reading room is its own world with cloth and
// paper the system does not describe (docs/frontend-surface-designs.md §4.11).
// Its component sheets are ignored here and its part of ted-theme.scss opens
// with a stylelint-disable comment.
const kabul = [
  '/^var\\(--ted-/', '/^var\\(--tedy-/', '/^var\\(--status-/', '/^#\\{colors\\.\\$/',
  'transparent', 'currentColor', 'currentcolor', 'inherit', 'initial', 'unset', 'none', '0', 'auto',
  // CSS system colours, for Windows high contrast (forced-colors) rules only.
  'ButtonText', 'CanvasText', 'Canvas', 'Highlight', 'HighlightText', 'GrayText', 'LinkText',
]
const ortak = { severity: 'error', acceptCarbonCustomProp: true, acceptValues: kabul }

export default {
  customSyntax: 'postcss-scss',
  plugins: ['stylelint-plugin-carbon-tokens'],
  ignoreFiles: ['src/theme/_subjects.scss', 'src/components/BookReader*.scss', 'dist/**', 'node_modules/**'],
  rules: {
    // acceptValues replaces the plugin's own list, so its defaults are restated:
    // border styles, lengths inside borders and shadows, background-clip keywords.
    'carbon/theme-use': [true, {
      ...ortak,
      validateGradients: 'strict',
      acceptValues: [...kabul, '/^(solid|dashed|dotted|double|inset|outset|hidden)$/',
        '/^-?\\d+\\.?\\d*(px|rem|em)$/', '/padding-box|border-box|content-box/', '/^\\$spacing-/'],
    }],
    // 1px is a hairline — a border offset or an optical nudge — not spacing.
    'carbon/layout-use': [true, { ...ortak, acceptValues: [...kabul, '1px', '-1px'] }],
    // Size, leading, weight and family come from Carbon's type scale; the
    // tracking of an uppercase label and tabular figures are typesetting, not
    // tokens. Carbon's weights are exactly 300, 400 and 600, and the plugin
    // does not recognise type.font-weight() itself.
    'carbon/type-use': [true, {
      ...ortak,
      includeProps: ['font-size', 'line-height', 'font-weight', 'font-family'],
      acceptValues: [...kabul, '300', '400', '600', 'normal'],
    }],
    // 0s is the focus mode's switch that turns motion off, not a duration.
    'carbon/motion-duration-use': [true, { ...ortak, acceptValues: [...kabul, '0s', '0ms'] }],
    'carbon/motion-easing-use': [true, ortak],
  },
}
