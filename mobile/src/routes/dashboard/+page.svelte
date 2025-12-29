<script lang="ts">
	import { api } from '$lib/api';
	import { filters, filterParams } from '$lib/stores/filters';
	import type { KPIs, MovimentosResponse, Coluna, DriverData, ProdutoData } from '$lib/types';
	import { formatValue, getValueClass, getIcon, formatDateShort } from '$lib/utils/formatters';
	import KPIBar from '$lib/components/KPIBar.svelte';
	import FilterPanel from '$lib/components/FilterPanel.svelte';

	let kpis: KPIs | null = null;
	let movimentos: MovimentosResponse | null = null;
	let loading = true;
	let error: string | null = null;
	let expandedDrivers = new Set<string>();
	let filterCollapsed = true;

	// Estado de ordenação
	let sortColumn: string | null = null;
	let sortAscending = true;

	// Controle de requisições para evitar race condition
	let requestId = 0;

	$: showDriverKpis = $filters.driver !== 'TODOS';
	$: if ($filterParams) loadData();

	// Drivers ordenados
	$: sortedDrivers = sortDrivers(movimentos?.drivers || [], sortColumn, sortAscending, movimentos?.colunas || []);

	async function loadData() {
		const currentRequestId = ++requestId;
		console.log(`[loadData #${currentRequestId}] Iniciando com driver=${$filters.driver}`);
		loading = true; error = null;
		try {
			const params = {
				data_inicio: $filters.data_inicio,
				data_fim: $filters.data_fim,
				driver: $filters.driver
			};
			const [kpisResult, movimentosResult] = await Promise.all([api.kpis(params), api.movimentos(params)]);

			// Só atualiza se esta for a requisição mais recente
			if (currentRequestId !== requestId) {
				console.log(`[loadData #${currentRequestId}] ❌ Ignorando (atual: #${requestId})`);
				return;
			}

			console.log(`[loadData #${currentRequestId}] ✓ Aplicando: ${movimentosResult.drivers?.length || 0} drivers`);
			kpis = kpisResult;
			movimentos = movimentosResult;
			if ($filters.driver !== 'TODOS' && movimentos?.drivers.length === 1) {
				expandedDrivers = new Set([movimentos.drivers[0].driver]);
			}
		} catch (e) {
			if (currentRequestId !== requestId) return; // Ignora erro de requisição antiga
			console.error('Error:', e);
			error = e instanceof Error ? e.message : 'Erro';
		}
		finally {
			if (currentRequestId === requestId) loading = false;
		}
	}

	function toggleDriver(driver: string) {
		expandedDrivers.has(driver) ? expandedDrivers.delete(driver) : expandedDrivers.add(driver);
		expandedDrivers = expandedDrivers;
	}

	function getTipo(col: Coluna): 'estoque' | 'recarga' | 'saida' { return col.tipo; }

	// Handler para ordenação
	function handleSort(colKey: string) {
		if (sortColumn === colKey) {
			sortAscending = !sortAscending;
		} else {
			sortColumn = colKey;
			sortAscending = true;
		}
	}

	// Indicador de ordenação
	function getSortIndicator(colKey: string): string {
		if (sortColumn !== colKey) return '';
		return sortAscending ? ' ▲' : ' ▼';
	}

	// Ordenar drivers
	function sortDrivers(drivers: DriverData[], col: string | null, asc: boolean, colunas: Coluna[]): DriverData[] {
		if (!drivers.length) return drivers;

		let sorted = [...drivers];

		if (col === 'name') {
			sorted.sort((a, b) => a.driver.localeCompare(b.driver));
		} else if (col === 'total') {
			sorted.sort((a, b) => a.saldo_total - b.saldo_total);
		} else if (col) {
			sorted.sort((a, b) => (a.valores[col] || 0) - (b.valores[col] || 0));
		} else {
			sorted.sort((a, b) => a.driver.localeCompare(b.driver));
		}

		if (!asc) sorted.reverse();
		return sorted;
	}

	// Ordenar produtos
	function sortProducts(produtos: ProdutoData[], col: string | null, asc: boolean): ProdutoData[] {
		if (!produtos.length) return produtos;

		let sorted = [...produtos];

		if (col === 'name') {
			sorted.sort((a, b) => a.produto.localeCompare(b.produto));
		} else if (col === 'total') {
			sorted.sort((a, b) => a.saldo - b.saldo);
		} else if (col) {
			sorted.sort((a, b) => (a.valores[col] || 0) - (b.valores[col] || 0));
		} else {
			sorted.sort((a, b) => a.produto.localeCompare(b.produto));
		}

		if (!asc) sorted.reverse();
		return sorted;
	}
</script>

<div class="h-full flex flex-col">
	<div class="bg-gb-panel border-b border-gb-border px-4 py-3 flex items-center justify-between">
		<h1 class="text-lg font-bold text-gb-header">📊 Dashboard</h1>
		<button on:click={loadData} class="text-gray-400 hover:text-white" disabled={loading}>{loading ? '⏳' : '🔄'}</button>
	</div>

	<FilterPanel bind:collapsed={filterCollapsed} />
	<KPIBar {kpis} {loading} {showDriverKpis} />

	{#if error}
		<div class="mx-2 p-3 bg-red-900/30 border border-red-700 rounded text-red-400 text-sm">{error}</div>
	{/if}

	<div class="flex-1 overflow-auto px-2 pb-2">
		{#if loading && !movimentos}
			<div class="flex items-center justify-center h-32 text-gray-500">Carregando...</div>
		{:else if movimentos}
			<div class="overflow-x-auto">
				<table class="w-full text-sm">
					<thead class="sticky top-0 bg-gb-bg">
						<tr class="text-gray-400 text-xs">
							<!-- Header: Driver/Produto (clicável) -->
							<th
								class="text-left px-2 py-2 sticky left-0 bg-gb-bg z-10 cursor-pointer hover:text-white select-none"
								on:click={() => handleSort('name')}
							>
								Driver/Produto{getSortIndicator('name')}
							</th>

							<!-- Headers das colunas de data/tipo (clicáveis) -->
							{#each movimentos.colunas as col}
								{@const colKey = `${col.data}_${col.tipo}`}
								<th
									class="text-center px-1 py-1 min-w-[50px] cursor-pointer hover:text-white select-none"
									on:click={() => handleSort(colKey)}
								>
									<div>{getIcon(getTipo(col))}</div>
									<div class="text-[10px]">{formatDateShort(col.data)}{getSortIndicator(colKey)}</div>
								</th>
							{/each}

							<!-- Header: Total (clicável) -->
							<th
								class="text-center px-2 py-1 min-w-[60px] cursor-pointer hover:text-white select-none"
								on:click={() => handleSort('total')}
							>
								<div>💰</div>
								<div class="text-[10px]">TOTAL{getSortIndicator('total')}</div>
							</th>
						</tr>
					</thead>

					<tbody>
						{#each sortedDrivers as driver}
							<!-- Driver Row -->
							<tr
								class="border-t border-gray-800 cursor-pointer hover:bg-gray-800/50"
								on:click={() => toggleDriver(driver.driver)}
							>
								<td class="px-2 py-2 sticky left-0 bg-gb-bg font-bold text-gb-driver">
									{expandedDrivers.has(driver.driver) ? '▾' : '▸'} {driver.driver}
								</td>
								{#each movimentos.colunas as col}
									{@const val = driver.valores[`${col.data}_${col.tipo}`]}
									<td class="px-1 py-2 text-center tabular-nums {getValueClass(val, getTipo(col))}">{formatValue(val, getTipo(col))}</td>
								{/each}
								<td class="px-2 py-2 text-center tabular-nums font-bold {getValueClass(driver.saldo_total, 'saldo')}">{formatValue(driver.saldo_total, 'saldo')}</td>
							</tr>

							<!-- Product Rows (expanded, also sorted) -->
							{#if expandedDrivers.has(driver.driver)}
								{#each sortProducts(driver.produtos, sortColumn, sortAscending) as produto}
									<tr class="bg-gray-900/30 text-xs">
										<td class="px-2 py-1 pl-6 sticky left-0 bg-gb-bg/90 text-gray-300">
											└ {produto.produto} {#if produto.saldo < 0}<span class="text-red-400">⚠️</span>{/if}
										</td>
										{#each movimentos.colunas as col}
											{@const val = produto.valores[`${col.data}_${col.tipo}`]}
											<td class="px-1 py-1 text-center tabular-nums {getValueClass(val, getTipo(col))}">{formatValue(val, getTipo(col))}</td>
										{/each}
										<td class="px-2 py-1 text-center tabular-nums {getValueClass(produto.saldo, 'saldo')}">{formatValue(produto.saldo, 'saldo')}</td>
									</tr>
								{/each}
							{/if}
						{/each}
					</tbody>
				</table>
			</div>

			{#if movimentos.drivers.length === 0}
				<div class="text-center text-gray-500 py-8">Nenhum movimento encontrado</div>
			{/if}
		{/if}
	</div>
</div>
