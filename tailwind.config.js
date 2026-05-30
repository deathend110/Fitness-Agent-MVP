/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{js,jsx,ts,tsx}'],
  theme: {
    extend: {
      colors: {
        repmind: {
          bg: '#f7f9ff',
          canvas: '#f3f6ff',
          panel: '#ffffff',
          panelMuted: '#eef2ff',
          border: '#d7def0',
          borderStrong: '#c3cee7',
          text: '#182033',
          textMuted: '#5f6b85',
          textSoft: '#7f8aa3',
          accent: '#6d5efc',
          accentStrong: '#5a4cf2',
          accentSoft: '#eef0ff',
          success: '#12a150',
          successSoft: '#e9f9ef',
          warning: '#b86a00',
          warningSoft: '#fff4df',
          danger: '#d33b57',
          dangerSoft: '#ffedf0',
        },
        fitloop: {
          // 兼容旧组件类名，先映射到新的冷白 + 蓝紫主题语义色。
          ink: '#eef2ff',
          panel: '#ffffff',
          line: '#d7def0',
          orange: '#6d5efc',
          mint: '#12a150',
        },
      },
    },
  },
  plugins: [],
}
