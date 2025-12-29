<script lang="ts">
	import type { KPIs } from '../types';
	export let kpis: KPIs | null = null;
	export let loading = false;
	export let showDriverKpis = false;
</script>

<div class="overflow-x-auto py-2">
	<div class="flex gap-2 px-2 min-w-max">
		{#if loading}
			{#each Array(5) as _}
				<div class="kpi-card w-20 animate-pulse">
					<div class="h-4 bg-gray-700 rounded mb-1"></div>
					<div class="h-6 bg-gray-700 rounded"></div>
				</div>
			{/each}
		{:else if kpis}
			<div class="kpi-card w-20 flex-shrink-0">
				<div class="text-xs text-gray-400">🏎️ Entregas</div>
				<div class="text-lg font-bold text-blue-400 tabular-nums">{kpis.entregas}</div>
			</div>
			<div class="kpi-card w-20 flex-shrink-0">
				<div class="text-xs text-gray-400">📦 Retiradas</div>
				<div class="text-lg font-bold text-green-400 tabular-nums">{kpis.retiradas}</div>
			</div>
			<div class="kpi-card w-20 flex-shrink-0">
				<div class="text-xs text-gray-400">⚠️ Negativos</div>
				<div class="text-lg font-bold tabular-nums {kpis.negativos > 0 ? 'text-red-400' : 'text-green-400'}">{kpis.negativos}</div>
			</div>
			<div class="kpi-card w-20 flex-shrink-0">
				<div class="text-xs text-gray-400">📦 Tot.Ret</div>
				<div class="text-lg font-bold text-gb-recarga tabular-nums">{kpis.total_recarga}</div>
			</div>
			<div class="kpi-card w-20 flex-shrink-0">
				<div class="text-xs text-gray-400">🏎️ Tot.Del</div>
				<div class="text-lg font-bold text-gb-saida tabular-nums">{kpis.total_entrega}</div>
			</div>
			{#if showDriverKpis}
				<div class="kpi-card w-20 flex-shrink-0">
					<div class="text-xs text-gray-400">📸 Estoque</div>
					<div class="text-lg font-bold text-gb-estoque tabular-nums">{kpis.total_estoque}</div>
				</div>
				<div class="kpi-card w-20 flex-shrink-0">
					<div class="text-xs text-gray-400">💰 Saldo</div>
					<div class="text-lg font-bold tabular-nums {kpis.saldo >= 0 ? 'text-gb-saldo-pos' : 'text-gb-saldo-neg'}">{kpis.saldo}</div>
				</div>
			{/if}
		{/if}
	</div>
</div>
