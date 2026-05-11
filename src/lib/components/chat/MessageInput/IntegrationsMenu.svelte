<script lang="ts">
	import { getContext, onMount, tick } from 'svelte';
	import { fly } from 'svelte/transition';

	import {
		config,
		user,
		tools as _tools,
		mobile,
		settings,
		toolServers,
		terminalServers
	} from '$lib/stores';

	import { getOAuthClientAuthorizationUrl } from '$lib/apis/configs';
	import { deleteOAuthSession } from '$lib/apis/auths';
	import { getTools } from '$lib/apis/tools';

	import { toast } from 'svelte-sonner';

	import Knobs from '$lib/components/icons/Knobs.svelte';
	import Dropdown from '$lib/components/common/Dropdown.svelte';
	import Tooltip from '$lib/components/common/Tooltip.svelte';
	import Switch from '$lib/components/common/Switch.svelte';
	import Spinner from '$lib/components/common/Spinner.svelte';
	import Wrench from '$lib/components/icons/Wrench.svelte';
	import Sparkles from '$lib/components/icons/Sparkles.svelte';
	import GlobeAlt from '$lib/components/icons/GlobeAlt.svelte';
	import Photo from '$lib/components/icons/Photo.svelte';
	import Terminal from '$lib/components/icons/Terminal.svelte';

	// ✅ You were using these in the "tab === 'tools'" branch but they were missing
	import ChevronLeft from '$lib/components/icons/ChevronLeft.svelte';
	import LinkSlash from '$lib/components/icons/LinkSlash.svelte';

	const i18n = getContext('i18n');

	export let selectedToolIds: string[] = [];

	export let selectedModels: string[] = [];
	export let fileUploadCapableModels: string[] = [];

	export let toggleFilters: { id: string; name: string; description?: string; icon?: string }[] = [];
	export let selectedFilterIds: string[] = [];

	export let showWebSearchButton = false;
	export let webSearchEnabled = false;
	export let showImageGenerationButton = false;
	export let imageGenerationEnabled = false;
	export let showCodeInterpreterButton = false;
	export let codeInterpreterEnabled = false;

	export let onShowValves: (payload: any) => void;
	export let onClose: () => void;
	export let closeOnOutsideClick = true;

	let show = false;
	let tools: Record<string, any> | null = null;

	// ✅ You reference `tab` in markup; declare it
	let tab: '' | 'tools' = '';

	$: if (show) {
		void init();
	}

	let fileUploadEnabled = true;
	$: fileUploadEnabled =
		fileUploadCapableModels.length === selectedModels.length &&
		($user?.role === 'admin' || $user?.permissions?.chat?.file_upload);

	const init = async () => {
		if ($_tools === null) {
			_tools.set(await getTools(localStorage.token));
		}

		// ensure tools dict exists
		let dict: Record<string, any> = {};

		if ($_tools) {
			dict = $_tools.reduce((a: any, tool: any) => {
				a[tool.id] = {
					name: tool.name,
					description: tool?.meta?.description ?? '',
					enabled: selectedToolIds.includes(tool.id),
					...tool
				};
				return a;
			}, {} as Record<string, any>);
		}

		if ($toolServers) {
			for (const serverIdx in $toolServers) {
				const server = $toolServers[serverIdx];
				if (server?.info) {
					dict[`direct_server:${serverIdx}`] = {
						name: server?.info?.title ?? server.url,
						description: server?.info?.description ?? '',
						enabled: selectedToolIds.includes(`direct_server:${serverIdx}`)
					};
				}
			}
		}

		tools = dict;

		// keep only existing tool ids
		selectedToolIds = selectedToolIds.filter((id) => Object.keys(dict).includes(id));
	};

	const toggleToolExclusive = async (toolId: string, e?: Event) => {
		if (!tools) return;

		if (!(tools[toolId]?.authenticated ?? true)) {
			e?.preventDefault();

			const parts = toolId.split(':');
			const serverId = parts?.at(-1) ?? toolId;

			const authUrl = getOAuthClientAuthorizationUrl(serverId, 'mcp');
			window.open(authUrl, '_self', 'noopener');
			return;
		}

		const wasEnabled = !!tools[toolId]?.enabled;

		if (wasEnabled) {
			tools[toolId].enabled = false;
			selectedToolIds = selectedToolIds.filter((id) => id !== toolId);
		} else {
			// disable all custom tools
			Object.keys(tools).forEach((id) => (tools![id].enabled = false));

			// disable built-in toggles
			webSearchEnabled = false;
			imageGenerationEnabled = false;
			codeInterpreterEnabled = false;

			// enable only selected tool
			tools[toolId].enabled = true;
			selectedToolIds = [toolId];
		}

		await tick();
	};

	const toggleWebSearchExclusive = () => {
		if (webSearchEnabled) {
			webSearchEnabled = false;
			return;
		}

		webSearchEnabled = true;
		imageGenerationEnabled = false;
		codeInterpreterEnabled = false;

		if (tools) Object.keys(tools).forEach((id) => (tools[id].enabled = false));
		selectedToolIds = [];
	};

	const toggleImageExclusive = () => {
		if (imageGenerationEnabled) {
			imageGenerationEnabled = false;
			return;
		}

		imageGenerationEnabled = true;
		webSearchEnabled = false;
		codeInterpreterEnabled = false;

		if (tools) Object.keys(tools).forEach((id) => (tools[id].enabled = false));
		selectedToolIds = [];
	};

	const toggleCodeInterpreterExclusive = () => {
		if (codeInterpreterEnabled) {
			codeInterpreterEnabled = false;
			return;
		}

		codeInterpreterEnabled = true;
		webSearchEnabled = false;
		imageGenerationEnabled = false;

		if (tools) Object.keys(tools).forEach((id) => (tools[id].enabled = false));
		selectedToolIds = [];
	};
</script>

<Dropdown
	bind:show
	onOpenChange={(state) => {
		if (state === false) {
			onClose();
		}
	}}
>
	<Tooltip content={$i18n.t('Integrations')} placement="top">
		<slot />
	</Tooltip>

	<div slot="content">
		<div
			class="min-w-70 max-w-70 rounded-2xl px-1 py-1 border border-gray-100 dark:border-gray-800 z-50 bg-white dark:bg-gray-850 dark:text-white shadow-lg max-h-72 overflow-y-auto overflow-x-hidden scrollbar-thin"
		>
			{#if tab === ''}
				<!-- ✅ main list -->
				<div in:fly={{ x: -20, duration: 150 }}>
					{#if tools === null}
						<div class="py-4">
							<Spinner />
						</div>
					{:else}
						{#if toggleFilters && toggleFilters.length > 0}
							{#each toggleFilters
								.sort((a, b) => a.name.localeCompare(b.name, undefined, { sensitivity: 'base' }))
								as filter (filter.id)}
								<Tooltip content={filter?.description} placement="top-start">
									<button
										class="flex w-full justify-between gap-2 items-center px-3 py-1.5 text-sm cursor-pointer rounded-xl hover:bg-gray-50 dark:hover:bg-gray-800/50"
										type="button"
										on:click={() => {
											if (selectedFilterIds.includes(filter.id)) {
												selectedFilterIds = selectedFilterIds.filter((id) => id !== filter.id);
											} else {
												selectedFilterIds = [...selectedFilterIds, filter.id];
											}
										}}
									>
										<div class="flex-1 truncate">
											<div class="flex flex-1 gap-2 items-center">
												<div class="shrink-0">
													{#if filter?.icon}
														<div class="size-4 items-center flex justify-center">
															<img
																src={filter.icon}
																class="size-3.5 {filter.icon.includes('data:image/svg')
																	? 'dark:invert-[80%]'
																	: ''}"
																style="fill: currentColor;"
																alt={filter.name}
															/>
														</div>
													{:else}
														<Sparkles className="size-4" strokeWidth="1.75" />
													{/if}
												</div>
												<div class="truncate">{filter?.name}</div>
											</div>
										</div>

										{#if filter?.has_user_valves &&
										($user?.role === 'admin' || ($user?.permissions?.chat?.valves ?? true))}
											<div class="shrink-0">
												<Tooltip content={$i18n.t('Valves')}>
													<button
														class="self-center w-fit text-sm text-gray-600 dark:text-gray-400 hover:text-gray-700 dark:hover:text-gray-300 transition rounded-full"
														type="button"
														on:click={(e) => {
															e.stopPropagation();
															e.preventDefault();
															onShowValves?.({ type: 'function', id: filter.id });
														}}
													>
														<Knobs />
													</button>
												</Tooltip>
											</div>
										{/if}

										<div class="shrink-0">
											<Switch
												state={selectedFilterIds.includes(filter.id)}
												on:change={async () => {
													await tick();
												}}
											/>
										</div>
									</button>
								</Tooltip>
							{/each}
						{/if}

						{#if tools && Object.keys(tools).length > 0}
							{#each Object.keys(tools)
								.sort((a, b) =>
									(tools?.[a]?.name ?? '').localeCompare(tools?.[b]?.name ?? '', undefined, {
										sensitivity: 'base'
									})
								) as toolId (toolId)}
								<button
									class="relative flex w-full justify-between gap-2 items-center px-3 py-1.5 text-sm cursor-pointer rounded-xl hover:bg-gray-50 dark:hover:bg-gray-800/50"
									type="button"
									on:click={(e) => toggleToolExclusive(toolId, e)}
								>
									{#if !(tools[toolId]?.authenticated ?? true)}
										<div class="absolute inset-0 opacity-50 rounded-xl cursor-pointer z-10" />
									{/if}

									<div class="flex-1 truncate">
										<div class="flex flex-1 gap-2 items-center">
											<div class="shrink-0">
												<Wrench />
											</div>

											<Tooltip content={tools[toolId]?.description ?? ''} placement="top-start">
												<div class="truncate">{tools[toolId]?.name ?? toolId}</div>
											</Tooltip>
										</div>
									</div>

									{#if tools[toolId]?.has_user_valves}
										<div class="shrink-0">
											<Tooltip content={$i18n.t('Valves')}>
												<button
													class="self-center w-fit text-sm text-gray-600 dark:text-gray-400 hover:text-gray-700 dark:hover:text-gray-300 transition rounded-full"
													type="button"
													on:click={(e) => {
														e.stopPropagation();
														e.preventDefault();
														onShowValves?.({ type: 'tool', id: toolId });
													}}
												>
													<Knobs />
												</button>
											</Tooltip>
										</div>
									{/if}

									<div class="shrink-0">
										<Switch state={tools[toolId]?.enabled ?? false} />
									</div>
								</button>
							{/each}
						{/if}

						{#if showWebSearchButton}
							<Tooltip content={$i18n.t('Search the internet')} placement="top-start">
								<button
									class="flex w-full justify-between gap-2 items-center px-3 py-1.5 text-sm cursor-pointer rounded-xl hover:bg-gray-50 dark:hover:bg-gray-800/50"
									type="button"
									on:click={toggleWebSearchExclusive}
								>
									<div class="flex-1 truncate">
										<div class="flex flex-1 gap-2 items-center">
											<div class="shrink-0"><GlobeAlt /></div>
											<div class="truncate">{$i18n.t('Web Search')}</div>
										</div>
									</div>

									<div class="shrink-0">
										<Switch
											state={webSearchEnabled}
											on:change={async () => {
												await tick();
											}}
										/>
									</div>
								</button>
							</Tooltip>
						{/if}

						{#if showImageGenerationButton}
							<Tooltip content={$i18n.t('Generate an image')} placement="top-start">
								<button
									class="flex w-full justify-between gap-2 items-center px-3 py-1.5 text-sm cursor-pointer rounded-xl hover:bg-gray-50 dark:hover:bg-gray-800/50"
									type="button"
									on:click={toggleImageExclusive}
								>
									<div class="flex-1 truncate">
										<div class="flex flex-1 gap-2 items-center">
											<div class="shrink-0">
												<Photo className="size-4" strokeWidth="1.5" />
											</div>
											<div class="truncate">{$i18n.t('Image')}</div>
										</div>
									</div>

									<div class="shrink-0">
										<Switch
											state={imageGenerationEnabled}
											on:change={async () => {
												await tick();
											}}
										/>
									</div>
								</button>
							</Tooltip>
						{/if}

						{#if showCodeInterpreterButton}
							<Tooltip content={$i18n.t('Execute code for analysis')} placement="top-start">
								<button
									class="flex w-full justify-between gap-2 items-center px-3 py-1.5 text-sm cursor-pointer rounded-xl hover:bg-gray-50 dark:hover:bg-gray-800/50"
									type="button"
									aria-pressed={codeInterpreterEnabled}
									aria-label={codeInterpreterEnabled
										? $i18n.t('Disable Code Interpreter')
										: $i18n.t('Enable Code Interpreter')}
									on:click={toggleCodeInterpreterExclusive}
								>
									<div class="flex-1 truncate">
										<div class="flex flex-1 gap-2 items-center">
											<div class="shrink-0">
												<Terminal className="size-3.5" strokeWidth="1.75" />
											</div>
											<div class="truncate">{$i18n.t('Code Interpreter')}</div>
										</div>
									</div>

									<div class="shrink-0">
										<Switch
											state={codeInterpreterEnabled}
											on:change={async () => {
												await tick();
											}}
										/>
									</div>
								</button>
							</Tooltip>
						{/if}
					{/if}
				</div>

			{:else if tab === 'tools' && tools}
				<!-- ✅ tools tab -->
				<div in:fly={{ x: 20, duration: 150 }}>
					<button
						class="flex w-full justify-between gap-2 items-center px-3 py-1.5 text-sm cursor-pointer rounded-xl hover:bg-gray-50 dark:hover:bg-gray-800/50"
						type="button"
						on:click={() => (tab = '')}
					>
						<ChevronLeft />
						<div class="flex items-center w-full justify-between">
							<div>
								{$i18n.t('Tools')}
								<span class="ml-0.5 text-gray-500">{Object.keys(tools).length}</span>
							</div>
						</div>
					</button>

					{#each Object.keys(tools) as toolId (toolId)}
						<button
							class="relative flex w-full justify-between gap-2 items-center px-3 py-1.5 text-sm cursor-pointer rounded-xl hover:bg-gray-50 dark:hover:bg-gray-800/50"
							on:click={async (e) => {
								if (!(tools[toolId]?.authenticated ?? true)) {
									e.preventDefault();

									let parts = toolId.split(':');
									let serverId = parts?.at(-1) ?? toolId;

									// Persist the tool ID so we can re-enable it after OAuth redirect
									sessionStorage.setItem('pendingOAuthToolId', toolId);

									const authUrl = getOAuthClientAuthorizationUrl(serverId, 'mcp');
									window.open(authUrl, '_self', 'noopener');
								} else {
									tools[toolId].enabled = !tools[toolId].enabled;

									const state = tools[toolId].enabled;
									await tick();

									if (state) {
										selectedToolIds = [...selectedToolIds, toolId];
									} else {
										selectedToolIds = selectedToolIds.filter((id) => id !== toolId);
									}
								}
							}}
						>
							{#if !(tools[toolId]?.authenticated ?? true)}
								<div class="absolute inset-0 opacity-50 rounded-xl cursor-pointer z-10" />
							{/if}

							<div class="flex-1 truncate">
								<div class="flex flex-1 gap-2 items-center">
									<div class="shrink-0"><Wrench /></div>
									<Tooltip content={tools[toolId]?.description ?? ''} placement="top-start">
										<div class="truncate">{tools[toolId]?.name ?? toolId}</div>
									</Tooltip>
								</div>
							</div>

							{#if (tools[toolId]?.authenticated ?? true) && toolId.startsWith('server:mcp:')}
								<div class="shrink-0">
									<Tooltip content={$i18n.t('Disconnect OAuth')}>
										<button
											class="self-center w-fit text-sm text-gray-600 dark:text-gray-400 hover:text-gray-700 dark:hover:text-gray-300 transition rounded-full"
											type="button"
											on:click={async (e) => {
												e.stopPropagation();
												e.preventDefault();

												const parts = toolId.split(':');
												const serverId = parts.at(-1) ?? toolId;
												const provider = `mcp:${serverId}`;

												try {
													await deleteOAuthSession(localStorage.token, provider);
													toast.success($i18n.t('OAuth session disconnected'));

													// Refresh tools to update authenticated state
													_tools.set(await getTools(localStorage.token));
													selectedToolIds = selectedToolIds.filter((id) => id !== toolId);
													await init();
												} catch (err) {
													toast.error(err ?? $i18n.t('Failed to disconnect'));
												}
											}}
										>
											<LinkSlash className="size-3.5" />
										</button>
									</Tooltip>
								</div>
							{/if}

							{#if tools[toolId]?.has_user_valves && ($user?.role === 'admin' || ($user?.permissions?.chat?.valves ?? true))}
								<div class=" shrink-0">
									<Tooltip content={$i18n.t('Valves')}>
										<button
											class="self-center w-fit text-sm text-gray-600 dark:text-gray-400 hover:text-gray-700 dark:hover:text-gray-300 transition rounded-full"
											type="button"
											on:click={(e) => {
												e.stopPropagation();
												e.preventDefault();
												onShowValves?.({ type: 'tool', id: toolId });
											}}
										>
											<Knobs />
										</button>
									</Tooltip>
								</div>
							{/if}

							<div class="shrink-0">
								<Switch state={tools[toolId]?.enabled ?? false} />
							</div>
						</button>
					{/each}
				</div>
			{/if}
		</div>
	</div>
</Dropdown>
