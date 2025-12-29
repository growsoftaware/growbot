export interface KPIs {
	entregas: number;
	retiradas: number;
	negativos: number;
	total_recarga: number;
	total_entrega: number;
	total_estoque: number;
	saldo: number;
}

export interface Coluna {
	data: string;
	tipo: 'estoque' | 'recarga' | 'saida';
}

export interface ProdutoData {
	produto: string;
	saldo: number;
	valores: Record<string, number>;
}

export interface DriverData {
	driver: string;
	saldo_total: number;
	valores: Record<string, number>;
	produtos: ProdutoData[];
}

export interface MovimentosResponse {
	colunas: Coluna[];
	drivers: DriverData[];
}

export interface Card {
	data: string;
	data_iso: string;
	driver: string;
	resumo: { total_entregas: number; total_unidades: number; total_recargas: number; };
	entregas: { id: string; produtos: string[]; }[];
	recargas: { produto: string; quantidade: number; }[];
}

export interface CardsResponse { cards: Card[]; }

export interface HealthResponse {
	status: 'ok' | 'error';
	db_connected: boolean;
	total_registros?: number;
	error?: string;
	timestamp: string;
}

export type TipoMovimento = 'estoque' | 'recarga' | 'saida';
export const DRIVERS = ['RAFA', 'FRANCIS', 'RODRIGO', 'KAROL', 'ARTHUR'] as const;
