<script lang="ts">
	import '../app.css';
	import { page } from '$app/stores';
	const navItems = [
		{ href: '/dashboard', label: 'Dashboard', icon: '📊' },
		{ href: '/cards', label: 'Cards', icon: '🃏' },
		{ href: '/settings', label: 'Config', icon: '⚙️' }
	];
	$: currentPath = $page.url.pathname;
</script>

<div class="h-screen flex flex-col bg-gb-bg">
	<main class="flex-1 overflow-hidden"><slot /></main>
	<nav class="bg-gb-panel border-t border-gb-border" style="padding-bottom: env(safe-area-inset-bottom)">
		<div class="flex justify-around py-2">
			{#each navItems as item}
				<a href={item.href} class="nav-item {currentPath.startsWith(item.href) ? 'active' : ''}">
					<span class="text-xl">{item.icon}</span>
					<span class="text-xs mt-1">{item.label}</span>
				</a>
			{/each}
		</div>
	</nav>
</div>
