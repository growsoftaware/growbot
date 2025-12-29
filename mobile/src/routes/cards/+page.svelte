<script lang="ts">
	import { onMount } from 'svelte';
	import { api } from '$lib/api';
	import { filterParams } from '$lib/stores/filters';
	import type { Card } from '$lib/types';
	import FilterPanel from '$lib/components/FilterPanel.svelte';

	let cards: Card[] = [];
	let loading = true;
	let error: string | null = null;
	let expandedCards = new Set<string>();
	let filterCollapsed = true;

	$: if ($filterParams) loadData();
	onMount(() => loadData());

	async function loadData() {
		loading = true; error = null;
		try { cards = (await api.cards($filterParams)).cards; }
		catch (e) { error = e instanceof Error ? e.message : 'Erro'; }
		finally { loading = false; }
	}

	function toggle(key: string, section: string) {
		const k = `${key}-${section}`;
		expandedCards.has(k) ? expandedCards.delete(k) : expandedCards.add(k);
		expandedCards = expandedCards;
	}
</script>

<div class="h-full flex flex-col">
	<div class="bg-gb-panel border-b border-gb-border px-4 py-3 flex items-center justify-between">
		<h1 class="text-lg font-bold text-gb-header">🃏 Cards</h1>
		<button on:click={loadData} class="text-gray-400 hover:text-white" disabled={loading}>{loading ? '⏳' : '🔄'}</button>
	</div>

	<FilterPanel bind:collapsed={filterCollapsed} />

	{#if error}<div class="mx-2 p-3 bg-red-900/30 border border-red-700 rounded text-red-400 text-sm">{error}</div>{/if}

	<div class="flex-1 overflow-auto px-2 pb-2 space-y-3">
		{#if loading && cards.length === 0}
			<div class="flex items-center justify-center h-32 text-gray-500">Carregando...</div>
		{:else}
			{#each cards as card (`${card.data_iso}-${card.driver}`)}
				{@const key = `${card.data_iso}-${card.driver}`}
				<div class="bg-gb-card border border-gb-border rounded-lg overflow-hidden">
					<div class="p-3 border-b border-gray-700">
						<div class="flex items-center justify-between">
							<span class="font-bold text-gb-driver">{card.driver}</span>
							<span class="text-gray-400 text-sm">{card.data}</span>
						</div>
						<div class="text-sm text-gray-300 mt-1">📦 +{card.resumo.total_recargas} | 🏎️ {card.resumo.total_entregas} ({card.resumo.total_unidades} un)</div>
					</div>
					{#if card.entregas.length > 0}
						<button class="w-full px-3 py-2 text-left text-sm text-gray-400 hover:bg-gray-800/50 flex items-center justify-between border-b border-gray-800" on:click={() => toggle(key, 'e')}>
							<span>{expandedCards.has(`${key}-e`) ? '▾' : '▸'} Ver {card.entregas.length} entregas</span>
							<span class="text-gb-saida">{card.resumo.total_unidades} un</span>
						</button>
						{#if expandedCards.has(`${key}-e`)}
							<div class="px-3 py-2 bg-gray-900/50 space-y-1">
								{#each card.entregas as e}<div class="text-xs text-gray-300"><span class="text-gb-header">#{e.id}:</span> {e.produtos.join(', ')}</div>{/each}
							</div>
						{/if}
					{/if}
					{#if card.recargas.length > 0}
						<button class="w-full px-3 py-2 text-left text-sm text-gray-400 hover:bg-gray-800/50 flex items-center justify-between" on:click={() => toggle(key, 'r')}>
							<span>{expandedCards.has(`${key}-r`) ? '▾' : '▸'} Ver {card.recargas.length} recargas</span>
							<span class="text-gb-recarga">+{card.resumo.total_recargas}</span>
						</button>
						{#if expandedCards.has(`${key}-r`)}
							<div class="px-3 py-2 bg-gray-900/50 space-y-1">
								{#each card.recargas as r}<div class="text-xs text-gb-recarga">+{r.quantidade} {r.produto}</div>{/each}
							</div>
						{/if}
					{/if}
				</div>
			{/each}
			{#if cards.length === 0 && !loading}<div class="text-center text-gray-500 py-8">Nenhum card encontrado</div>{/if}
		{/if}
	</div>
</div>
