<script lang="ts">
	import { getVersionUpdates } from '$lib/apis';
	import { getOllamaVersion } from '$lib/apis/ollama';
	import { OLIA_BUILD_HASH, OLIA_VERSION } from '$lib/constants';
	import { OLIA_NAME, config, showChangelog } from '$lib/stores';
	import { compareVersion } from '$lib/utils';
	import { onMount, getContext } from 'svelte';

	import Tooltip from '$lib/components/common/Tooltip.svelte';

	const i18n = getContext('i18n');

	let ollamaVersion = '';

	let updateAvailable = null;
	let version = {
		current: '',
		latest: ''
	};

	const checkForVersionUpdates = async () => {
		updateAvailable = null;
		version = await getVersionUpdates(localStorage.token).catch((error) => {
			return {
				current: OLIA_VERSION,
				latest: OLIA_VERSION
			};
		});

		console.log(version);

		updateAvailable = compareVersion(version.latest, version.current);
		console.log(updateAvailable);
	};

	onMount(async () => {
		ollamaVersion = await getOllamaVersion(localStorage.token).catch((error) => {
			return '';
		});

		if ($config?.features?.enable_version_update_check) {
			checkForVersionUpdates();
		}
	});
</script>

<div id="tab-about" class="flex flex-col h-full justify-between space-y-3 text-sm mb-6">
	<div class=" space-y-3 overflow-y-scroll max-h-[28rem] md:max-h-full">
		<div>
			<div class=" mb-2.5 text-sm font-medium flex space-x-2 items-center">
				<div>
					{$OLIA_NAME}
					{$i18n.t('Version') + ` ${OLIA_VERSION}`}
				</div>
			</div>
		</div>

		{#if ollamaVersion}
			<hr class=" border-gray-100/30 dark:border-gray-850/30" />

			<div>
				<div class=" mb-2.5 text-sm font-medium">{$i18n.t('Ollama Version')}</div>
				<div class="flex w-full">
					<div class="flex-1 text-xs text-gray-700 dark:text-gray-200">
						{ollamaVersion ?? 'N/A'}
					</div>
				</div>
			</div>
		{/if}

		<hr class=" border-gray-100/30 dark:border-gray-850/30" />

		{#if $config?.license_metadata}
			<div class="mb-2 text-xs">
				{#if !$OLIA_NAME.includes('OLIA')}
					<span class=" text-gray-500 dark:text-gray-300 font-medium">{$OLIA_NAME}</span> -
				{/if}

				<span class=" capitalize">{$config?.license_metadata?.type}</span> license purchased by
				<span class=" capitalize">{$config?.license_metadata?.organization_name}</span>
			</div>
		{:else}
			<div class="flex space-x-1">
				<a href="https://www.facebook.com/OliveSoft.tech" target="_blank">
					<img
						alt="Facebook Page"
						src="https://img.shields.io/badge/Olivesoft-%231877F2.svg?style=for-the-badge&logo=Facebook&logoColor=white"
					/>
				</a>

				<a href="https://www.linkedin.com/company/olivesoft/" target="_blank">
					<img
						alt="Linkedin Page"
						src="https://img.shields.io/badge/linkedin-%230077B5.svg?style=for-the-badge&logo=linkedin&logoColor=white"
					/>
				</a>

				<a href="https://www.olivesoft.fr" target="_blank">
					<img
						alt="Web site"
						src="https://img.shields.io/badge/Website-brightgreen?style=for-the-badge"
					/>
				</a>

			</div>
		{/if}
	</div>
</div>
