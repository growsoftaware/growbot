import type { KPIs, MovimentosResponse, CardsResponse, HealthResponse } from './types';
import { config } from './stores/config';
import { get } from 'svelte/store';

async function fetchApi<T>(endpoint: string, params?: Record<string, string>): Promise<T> {
	const baseUrl = get(config).apiUrl;
	const url = new URL(endpoint, baseUrl);
	if (params) {
		Object.entries(params).forEach(([k, v]) => {
			if (v && v !== 'TODOS') url.searchParams.set(k, v);
		});
	}
	console.log(`[API] ${endpoint}`, params);
	const res = await fetch(url.toString());
	if (!res.ok) throw new Error(`API error: ${res.status}`);
	const data = await res.json();
	console.log(`[API] ${endpoint} →`, 'colunas' in data ? `${data.colunas?.length} cols, ${data.drivers?.length} drivers` : data);
	return data;
}

export const api = {
	health: () => fetchApi<HealthResponse>('/api/health'),
	drivers: async () => (await fetchApi<{ drivers: string[] }>('/api/drivers')).drivers,
	kpis: (params?: Record<string, string>) => fetchApi<KPIs>('/api/kpis', params),
	movimentos: (params?: Record<string, string>) => fetchApi<MovimentosResponse>('/api/movimentos', params),
	cards: (params?: Record<string, string>) => fetchApi<CardsResponse>('/api/cards', params),
};
