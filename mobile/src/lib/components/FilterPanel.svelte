<script lang="ts">
	import { filters } from '../stores/filters';
	import { DRIVERS } from '../types';
	export let collapsed = true;
</script>

<div class="bg-gb-panel border border-gb-border rounded-lg mx-2 mb-2">
	<button on:click={() => collapsed = !collapsed} class="w-full flex items-center justify-between p-3 text-left">
		<span class="text-gb-header font-bold text-sm">{collapsed ? '▸' : '▾'} FILTROS</span>
		<span class="text-xs text-gray-400">
			{$filters.driver === 'TODOS' ? '👤 Todos' : `👤 ${$filters.driver}`} | 📅 {$filters.data_inicio} → {$filters.data_fim}
		</span>
	</button>
	{#if !collapsed}
		<div class="border-t border-gray-700 p-3 space-y-3">
			<div>
				<label class="text-xs text-gray-400 block mb-1">Data Início</label>
				<div class="flex items-center gap-1">
					<button on:click={() => filters.ajustarData('inicio', -1)} class="btn-ghost px-2 py-1 text-sm">−</button>
					<input type="text" value={$filters.data_inicio} on:change={(e) => filters.setDataInicio(e.currentTarget.value)} class="input flex-1 text-center text-sm" />
					<button on:click={() => filters.ajustarData('inicio', 1)} class="btn-ghost px-2 py-1 text-sm">+</button>
				</div>
			</div>
			<div>
				<label class="text-xs text-gray-400 block mb-1">Data Fim</label>
				<div class="flex items-center gap-1">
					<button on:click={() => filters.ajustarData('fim', -1)} class="btn-ghost px-2 py-1 text-sm">−</button>
					<input type="text" value={$filters.data_fim} on:change={(e) => filters.setDataFim(e.currentTarget.value)} class="input flex-1 text-center text-sm" />
					<button on:click={() => filters.ajustarData('fim', 1)} class="btn-ghost px-2 py-1 text-sm">+</button>
				</div>
			</div>
			<div>
				<label class="text-xs text-gray-400 block mb-1">Driver</label>
				<select value={$filters.driver} on:change={(e) => filters.setDriver(e.currentTarget.value)} class="input w-full">
					<option value="TODOS">TODOS</option>
					{#each DRIVERS as driver}<option value={driver}>{driver}</option>{/each}
				</select>
			</div>
			<button on:click={() => filters.reset()} class="btn btn-ghost w-full text-sm">Limpar</button>
		</div>
	{/if}
</div>
