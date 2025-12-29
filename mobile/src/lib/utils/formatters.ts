import type { TipoMovimento } from '../types';

export function formatValue(v: number | null | undefined, tipo: TipoMovimento | 'saldo'): string {
	if (!v) return '-';
	if (tipo === 'saldo' && v < 0) return `(${Math.abs(v)})`;
	return String(v);
}

export function getValueClass(v: number | null | undefined, tipo: TipoMovimento | 'saldo'): string {
	if (!v) return 'text-gray-500';
	const map: Record<string, string> = {
		estoque: 'text-gb-estoque',
		recarga: 'text-gb-recarga',
		saida: 'text-gb-saida',
	};
	if (tipo === 'saldo') return v >= 0 ? 'text-gb-saldo-pos' : 'text-gb-saldo-neg font-bold';
	return map[tipo] || 'text-gray-100';
}

export function getIcon(tipo: TipoMovimento | 'saldo'): string {
	return { estoque: '📸', recarga: '📦', saida: '🏎️', saldo: '💰' }[tipo] || '';
}

export function formatDateShort(iso: string): string {
	try {
		const [y, m, d] = iso.split('-');
		const date = new Date(+y, +m - 1, +d);
		const dias = ['Dom', 'Seg', 'Ter', 'Qua', 'Qui', 'Sex', 'Sáb'];
		return `${d}/${m} ${dias[date.getDay()]}`;
	} catch { return iso; }
}
