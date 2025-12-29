/** @type {import('tailwindcss').Config} */
export default {
	content: ['./src/**/*.{html,js,svelte,ts}'],
	darkMode: 'class',
	theme: {
		extend: {
			colors: {
				'gb-bg': '#0d0d0d',
				'gb-card': '#16213e',
				'gb-panel': '#1a1a2e',
				'gb-border': '#0891b2',
				'gb-estoque': '#22c55e',
				'gb-recarga': '#5eead4',
				'gb-saida': '#f87171',
				'gb-driver': '#facc15',
				'gb-header': '#22d3ee',
				'gb-saldo-pos': '#22c55e',
				'gb-saldo-neg': '#ef4444',
			},
			fontFamily: {
				mono: ['JetBrains Mono', 'Fira Code', 'SF Mono', 'monospace'],
			},
		},
	},
	plugins: [],
};
