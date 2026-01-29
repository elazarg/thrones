/**
 * Vegas language definition for Monaco Editor.
 * Provides syntax highlighting for .vg files.
 */
import type { languages } from 'monaco-editor';

export const vegasLanguageId = 'vegas';

export const vegasLanguageConfig: languages.LanguageConfiguration = {
  comments: {
    lineComment: '//',
    blockComment: ['/*', '*/'],
  },
  brackets: [
    ['{', '}'],
    ['[', ']'],
    ['(', ')'],
  ],
  autoClosingPairs: [
    { open: '{', close: '}' },
    { open: '[', close: ']' },
    { open: '(', close: ')' },
    { open: '"', close: '"' },
  ],
  surroundingPairs: [
    { open: '{', close: '}' },
    { open: '[', close: ']' },
    { open: '(', close: ')' },
    { open: '"', close: '"' },
  ],
};

export const vegasTokensProvider: languages.IMonarchLanguage = {
  defaultToken: '',
  tokenPostfix: '.vg',

  keywords: [
    'game',
    'join',
    'yield',
    'commit',
    'reveal',
    'withdraw',
    'type',
    'or',
    'split',
    'public',
  ],

  typeKeywords: ['bool', 'int'],

  constants: ['true', 'false'],

  operators: [
    '->',
    '?',
    ':',
    '&&',
    '||',
    '!',
    '==',
    '!=',
    '<=',
    '>=',
    '<',
    '>',
    '+',
    '-',
    '*',
    '/',
    '%',
    '$',
  ],

  symbols: /[=><!~?:&|+\-*\/\^%$]+/,

  tokenizer: {
    root: [
      // Comments
      [/\/\/.*$/, 'comment'],
      [/\/\*/, 'comment', '@comment'],

      // Numbers
      [/\d+/, 'number'],

      // Type ranges: {0 .. 100}
      [/\{/, { token: 'delimiter.curly', next: '@braceContent' }],

      // Identifiers and keywords
      [
        /[a-zA-Z_]\w*/,
        {
          cases: {
            '@keywords': 'keyword',
            '@typeKeywords': 'type',
            '@constants': 'constant',
            '@default': 'identifier',
          },
        },
      ],

      // Operators
      [
        /@symbols/,
        {
          cases: {
            '@operators': 'operator',
            '@default': '',
          },
        },
      ],

      // Delimiters
      [/[{}()\[\]]/, '@brackets'],
      [/[;,]/, 'delimiter'],

      // Whitespace
      [/\s+/, 'white'],
    ],

    comment: [
      [/[^\/*]+/, 'comment'],
      [/\*\//, 'comment', '@pop'],
      [/[\/*]/, 'comment'],
    ],

    braceContent: [
      [/\.\./, 'operator'], // Range operator
      [/\d+/, 'number'],
      [/\s+/, 'white'],
      [/\}/, { token: 'delimiter.curly', next: '@pop' }],
      [/./, ''], // Anything else
    ],
  },
};

/**
 * Register Vegas language with Monaco Editor.
 */
export function registerVegasLanguage(monaco: typeof import('monaco-editor')) {
  // Register language
  monaco.languages.register({ id: vegasLanguageId, extensions: ['.vg'] });

  // Set language configuration
  monaco.languages.setLanguageConfiguration(vegasLanguageId, vegasLanguageConfig);

  // Set tokenizer
  monaco.languages.setMonarchTokensProvider(vegasLanguageId, vegasTokensProvider);

  // Define a theme contribution for Vegas
  monaco.editor.defineTheme('vegas-dark', {
    base: 'vs-dark',
    inherit: true,
    rules: [
      { token: 'keyword', foreground: 'c586c0' }, // Purple for keywords
      { token: 'type', foreground: '4ec9b0' }, // Teal for types
      { token: 'constant', foreground: '569cd6' }, // Blue for constants
      { token: 'identifier', foreground: '9cdcfe' }, // Light blue for identifiers
      { token: 'number', foreground: 'b5cea8' }, // Green for numbers
      { token: 'operator', foreground: 'd4d4d4' }, // Gray for operators
      { token: 'comment', foreground: '6a9955' }, // Green for comments
    ],
    colors: {},
  });
}
