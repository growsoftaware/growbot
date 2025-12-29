import { writable, derived } from 'svelte/store';
import { format, addDays, parse } from 'date-fns';

interface FilterState { data_inicio: string; data_fim: string; driver: string; }

function createFiltersStore() {
	const hoje = new Date();
	const initial: FilterState = {
		data_inicio: format(addDays(hoje, -7), 'dd/MM/yyyy'),
		data_fim: format(hoje, 'dd/MM/yyyy'),
		driver: 'TODOS'
	};
	const { subscribe, set, update } = writable<FilterState>(initial);
	return {
		subscribe,
		setDriver: (driver: string) => update(s => ({ ...s, driver })),
		setDataInicio: (data: string) => update(s => ({ ...s, data_inicio: data })),
		setDataFim: (data: string) => update(s => ({ ...s, data_fim: data })),
		ajustarData: (campo: 'inicio' | 'fim', dias: number) => {
			update(s => {
				const key = campo === 'inicio' ? 'data_inicio' : 'data_fim';
				const curr = parse(s[key], 'dd/MM/yyyy', new Date());
				return { ...s, [key]: format(addDays(curr, dias), 'dd/MM/yyyy') };
			});
		},
		reset: () => set(initial)
	};
}

export const filters = createFiltersStore();
export const filterParams = derived(filters, $f => ({
	data_inicio: $f.data_inicio,
	data_fim: $f.data_fim,
	driver: $f.driver
}));
