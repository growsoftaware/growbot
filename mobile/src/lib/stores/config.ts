import { writable } from 'svelte/store';
import { browser } from '$app/environment';

interface Config { apiUrl: string; }

function createConfigStore() {
	let initial: Config = { apiUrl: 'http://localhost:8001' };
	if (browser) {
		const stored = localStorage.getItem('growbot-config');
		if (stored) try { initial = JSON.parse(stored); } catch {}
	}
	const { subscribe, update } = writable<Config>(initial);
	return {
		subscribe,
		setApiUrl(url: string) {
			update(c => {
				const n = { ...c, apiUrl: url };
				if (browser) localStorage.setItem('growbot-config', JSON.stringify(n));
				return n;
			});
		}
	};
}

export const config = createConfigStore();
