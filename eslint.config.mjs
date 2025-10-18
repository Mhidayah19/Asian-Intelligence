import { dirname } from 'path';
import { fileURLToPath } from 'url';
import { FlatCompat } from '@eslint/eslintrc';

const __filename = fileURLToPath(import.meta.url);
const __dirname = dirname(__filename);

const compat = new FlatCompat({
  baseDirectory: __dirname,
});

const eslintConfig = [
  ...compat.extends(
    'next/core-web-vitals',
    'next/typescript',
    'plugin:import/recommended',
    'prettier',
    'plugin:prettier/recommended'
  ),
  {
    rules: {
      // Allow @ts-expect-error without description
      '@typescript-eslint/ban-ts-comment': 'off',
      
      // Allow unescaped quotes/apostrophes in JSX
      'react/no-unescaped-entities': 'off',
      
      // Make unused vars a warning instead of error
      '@typescript-eslint/no-unused-vars': 'warn',
    },
  },
];

export default eslintConfig;
