import type { Config } from 'tailwindcss'

const config: Config = {
  darkMode: ['class'],
  content: ['./index.html', './src/**/*.{js,ts,jsx,tsx}'],
  theme: {
    extend: {
      colors: {
        background: 'var(--color-bg)',
        'background-elevated': 'var(--color-bg-elevated)',
        'background-hover': 'var(--color-bg-hover)',
        border: 'var(--color-border)',
        'border-subtle': 'var(--color-border-subtle)',
        foreground: 'var(--color-text-primary)',
        'foreground-secondary': 'var(--color-text-secondary)',
        'foreground-muted': 'var(--color-text-muted)',
        tool: 'var(--color-tool)',
        'tool-bg': 'var(--color-tool-bg)',
        mcp: 'var(--color-mcp)',
        'mcp-bg': 'var(--color-mcp-bg)',
        skill: 'var(--color-skill)',
        'skill-bg': 'var(--color-skill-bg)',
        opus: 'var(--color-opus)',
        sonnet: 'var(--color-sonnet)',
        haiku: 'var(--color-haiku)',
      },
      fontFamily: {
        mono: ['var(--font-mono)'],
        sans: ['var(--font-sans)'],
      },
    },
  },
  plugins: [],
}

export default config
