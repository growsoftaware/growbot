<script lang="ts">
	import { goto } from '$app/navigation';
	import { onMount } from 'svelte';
	onMount(() => goto('/dashboard'));
</script>

<div class="h-full flex items-center justify-center">
	<div class="text-center">
		<div class="text-4xl mb-4">🌱</div>
		<div class="text-gb-header text-xl font-bold">GrowBot</div>
		<div class="text-gray-500 mt-2">Carregando...</div>
	</div>
</div>
