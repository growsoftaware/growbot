<script lang="ts">
	import { onMount } from 'svelte';
	import { config } from '$lib/stores/config';
	import { api } from '$lib/api';
	import type { HealthResponse } from '$lib/types';

	let apiUrl = '';
	let health: HealthResponse | null = null;
	let checking = false;

	onMount(() => { apiUrl = $config.apiUrl; });

	async function checkHealth() {
		checking = true; health = null;
		try { health = await api.health(); }
		catch (e) { health = { status: 'error', db_connected: false, error: e instanceof Error ? e.message : 'Erro', timestamp: new Date().toISOString() }; }
		finally { checking = false; }
	}

	function save() { config.setApiUrl(apiUrl); checkHealth(); }
</script>

<div class="h-full flex flex-col">
	<div class="bg-gb-panel border-b border-gb-border px-4 py-3">
		<h1 class="text-lg font-bold text-gb-header">⚙️ Configurações</h1>
	</div>

	<div class="flex-1 overflow-auto p-4 space-y-6">
		<div class="bg-gb-card border border-gb-border rounded-lg p-4">
			<h2 class="text-sm font-bold text-gray-300 mb-3">Conexão API</h2>
			<div class="space-y-3">
				<div>
					<label class="text-xs text-gray-400 block mb-1">URL do Backend</label>
					<input type="url" bind:value={apiUrl} class="input w-full" placeholder="http://localhost:8000" />
				</div>
				<div class="flex gap-2">
					<button on:click={save} class="btn btn-primary flex-1">Salvar</button>
					<button on:click={checkHealth} class="btn btn-ghost" disabled={checking}>{checking ? '⏳' : '🔍'} Testar</button>
				</div>
				{#if health}
					<div class="mt-3 p-3 rounded {health.status === 'ok' ? 'bg-green-900/30 border border-green-700' : 'bg-red-900/30 border border-red-700'}">
						<div class="flex items-center gap-2">
							<span class="{health.status === 'ok' ? 'text-green-400' : 'text-red-400'}">{health.status === 'ok' ? '✅' : '❌'}</span>
							<span class="text-sm {health.status === 'ok' ? 'text-green-300' : 'text-red-300'}">{health.status === 'ok' ? 'Conectado' : 'Erro'}</span>
						</div>
						{#if health.status === 'ok'}<div class="text-xs text-gray-400 mt-1">{health.total_registros} registros</div>
						{:else if health.error}<div class="text-xs text-red-400 mt-1">{health.error}</div>{/if}
					</div>
				{/if}
			</div>
		</div>

		<div class="bg-gb-card border border-gb-border rounded-lg p-4">
			<h2 class="text-sm font-bold text-gray-300 mb-3">Legenda</h2>
			<div class="grid grid-cols-2 gap-2 text-sm">
				<div class="flex items-center gap-2"><span>📸</span><span class="text-gb-estoque">Estoque</span></div>
				<div class="flex items-center gap-2"><span>📦</span><span class="text-gb-recarga">Recarga</span></div>
				<div class="flex items-center gap-2"><span>🏎️</span><span class="text-gb-saida">Saída</span></div>
				<div class="flex items-center gap-2"><span>💰</span><span class="text-gb-saldo-pos">Saldo</span></div>
			</div>
		</div>

		<div class="text-center text-gray-500 text-xs">GrowBot Mobile v1.0.0 | SvelteKit + Capacitor</div>
	</div>
</div>
