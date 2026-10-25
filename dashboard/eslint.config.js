import js from '@eslint/js'
import globals from 'globals'
import reactHooks from 'eslint-plugin-react-hooks'
import reactRefresh from 'eslint-plugin-react-refresh'
import jsxA11y from 'eslint-plugin-jsx-a11y'
import tseslint from 'typescript-eslint'
import { defineConfig, globalIgnores } from 'eslint/config'

// B12 (talimatname §13, D1/D2): static JSX is checked, not only types and hooks.
//   * eslint-plugin-jsx-a11y's recommended set — accessible names, roles, keyboard handlers.
//   * A literal value in a `style={{ … }}` object is a static style (S5): it belongs in a class, where the
//     type, spacing and colour tokens are linted. Runtime values (identifiers, template literals, calls) and
//     CSS custom properties (`'--x': …`) pass — S5 keeps inline style for what is computed at run time.
const STATIK_STIL = 'JSXAttribute[name.name="style"] > JSXExpressionContainer > ObjectExpression > ' +
  'Property:not([key.value=/^--/]) > Literal.value'

export default defineConfig([
  globalIgnores(['dist', 'src/baski/vendor']),
  {
    files: ['**/*.{ts,tsx}'],
    extends: [
      js.configs.recommended,
      tseslint.configs.recommended,
      reactHooks.configs.flat.recommended,
      reactRefresh.configs.vite,
    ],
    languageOptions: {
      ecmaVersion: 2020,
      globals: globals.browser,
    },
  },
  {
    files: ['src/**/*.tsx'],
    extends: [jsxA11y.flatConfigs.recommended],
    rules: {
      'no-restricted-syntax': ['error', {
        selector: STATIK_STIL,
        message: 'Statik satır içi stil (S5, B4): değeri bir sınıfa taşı; style yalnız çalışma anında hesaplanan değer taşır.',
      }],
    },
  },
])
