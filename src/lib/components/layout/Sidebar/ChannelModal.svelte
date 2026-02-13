<script lang="ts">
	import { getContext } from 'svelte';
	const i18n = getContext('i18n');

	import { toast } from 'svelte-sonner';
	import { page } from '$app/stores';
	import { goto } from '$app/navigation';

	import { deleteChannelById } from '$lib/apis/channels';
	import { user } from '$lib/stores';

	import Spinner from '$lib/components/common/Spinner.svelte';
	import Modal from '$lib/components/common/Modal.svelte';
	import AccessControl from '$lib/components/workspace/common/AccessControl.svelte';
	import DeleteConfirmDialog from '$lib/components/common/ConfirmDialog.svelte';
	import XMark from '$lib/components/icons/XMark.svelte';
	import MemberSelector from '$lib/components/workspace/common/MemberSelector.svelte';
	import Visibility from '$lib/components/workspace/common/Visibility.svelte';
	import Tooltip from '$lib/components/common/Tooltip.svelte';
	import WebhooksModal from '$lib/components/channel/WebhooksModal.svelte';

	export let show = false;
	export let onSubmit: (payload: any) => Promise<any> | any = async () => {};
	export let onUpdate: () => void = () => {};

	export let channel: any = null;
	export let edit = false;

	let channelTypes: string[] = ['group', 'dm'];
	let type = '';
	let name = '';

	let isPrivate: boolean | null = null;
	let accessGrants: any[] = [];

	let groupIds: string[] = [];
	let userIds: string[] = [];

	let loading = false;

	let showDeleteConfirmDialog = false;
	let showWebhooksModal = false;

	// -----------------------------
	// ✅ FIX 1: avoid TS in template callbacks
	// -----------------------------
	const handleVisibilityChange = (value: string) => {
		isPrivate = value === 'private';
	};

	// -----------------------------
	// ✅ FIX 2: safer name normalization without reactive self-assignment loops
	// -----------------------------
	const normalizeName = (value: string) => value.replace(/\s+/g, '-').toLowerCase();

	const onNameInput = (e: Event) => {
		const input = e.currentTarget as HTMLInputElement | null;
		name = normalizeName(input?.value ?? '');
	};

	const onTypeChange = (nextType: string) => {
		if (nextType === 'group') {
			if (isPrivate === null) isPrivate = true;
		} else {
			isPrivate = null;
		}
	};

	$: onTypeChange(type);

	const submitHandler = async () => {
		loading = true;

		if (name.length > 128) {
			toast.error($i18n.t('Channel name must be less than 128 characters'));
			loading = false;
			return;
		}

		try {
			await onSubmit({
				type,
				name: normalizeName(name),
				is_private: type === 'group' ? (isPrivate ?? true) : null,
				// NOTE: keeping your original logic; if you intended AccessControl for type === ''
				// then this condition should be (type === '' ? accessGrants : []).
				access_grants: type === '' ? accessGrants : [],
				group_ids: groupIds,
				user_ids: userIds
			});
			show = false;
		} finally {
			loading = false;
		}
	};

	const init = () => {
		channelTypes = $user?.role === 'admin' ? ['', 'group', 'dm'] : ['group', 'dm'];

		type = channel?.type ?? channelTypes[0] ?? '';

		if (channel) {
			name = channel?.name ?? '';

			if (type === 'group') {
				isPrivate = typeof channel?.is_private === 'boolean' ? channel.is_private : true;
			} else {
				isPrivate = null;
			}

			accessGrants = channel?.access_grants ?? [];
			groupIds = channel?.group_ids ?? [];
			userIds = channel?.user_ids ?? [];
		} else {
			// defaults for "create"
			name = '';
			accessGrants = [];
			groupIds = [];
			userIds = [];
			isPrivate = type === 'group' ? true : null;
		}
	};

	const resetHandler = () => {
		type = '';
		name = '';
		isPrivate = null;
		accessGrants = [];
		groupIds = [];
		userIds = [];
		loading = false;
	};

	$: if (show) init();
	else resetHandler();

	const deleteHandler = async () => {
		showDeleteConfirmDialog = false;

		if (!channel?.id) {
			show = false;
			return;
		}

		const channelId = channel.id;

		const res = await deleteChannelById(localStorage.token, channelId).catch((error) => {
			toast.error(error?.message ?? String(error));
			return null;
		});

		if (res) {
			toast.success($i18n.t('Channel deleted successfully'));
			onUpdate();

			if ($page.url.pathname === `/channels/${channelId}`) {
				goto('/');
			}
		}

		show = false;
	};
</script>

<Modal size="md" bind:show>
	<div>
		<div class="flex justify-between dark:text-gray-300 px-5 pt-4 pb-1">
			<div class="text-lg font-medium self-center">
				{#if edit}
					{$i18n.t('Edit Channel')}
				{:else}
					{$i18n.t('Create Channel')}
				{/if}
			</div>
			<button class="self-center" type="button" on:click={() => (show = false)}>
				<XMark className="size-5" />
			</button>
		</div>

		<div class="flex flex-col md:flex-row w-full px-5 pb-4 md:space-x-4 dark:text-gray-200">
			<div class="flex flex-col w-full sm:flex-row sm:justify-center sm:space-x-6">
				<form class="flex flex-col w-full" on:submit|preventDefault={submitHandler}>
					{#if !edit}
						<div class="flex flex-col w-full mt-2 mb-1">
							<div class="mb-1 text-xs text-gray-500">{$i18n.t('Channel Type')}</div>

							<div class="flex-1">
								<Tooltip
									content={type === 'dm'
										? $i18n.t('A private conversation between you and selected users')
										: type === 'group'
											? $i18n.t('A collaboration channel where people join as members')
											: $i18n.t('A discussion channel where access is controlled by groups and permissions')}
									placement="top-start"
								>
									<select
										class="w-full text-sm bg-transparent placeholder:text-gray-300 dark:placeholder:text-gray-700 outline-hidden"
										bind:value={type}
									>
										{#each channelTypes as channelType, channelTypeIdx (channelType)}
											<option value={channelType} selected={channelTypeIdx === 0}>
												{#if channelType === 'group'}
													{$i18n.t('Group Channel')}
												{:else if channelType === 'dm'}
													{$i18n.t('Direct Message')}
												{:else if channelType === ''}
													{$i18n.t('Channel')}
												{/if}
											</option>
										{/each}
									</select>
								</Tooltip>
							</div>
						</div>
					{/if}

					<div class="text-gray-300 dark:text-gray-700 text-xs">
						{#if type === ''}
							{$i18n.t('Discussion channel where access is based on groups and permissions')}
						{:else if type === 'group'}
							{$i18n.t('Collaboration channel where people join as members')}
						{:else if type === 'dm'}
							{$i18n.t('Private conversation between selected users')}
						{/if}
					</div>

					<div class="flex flex-col w-full mt-2">
						<div class="mb-1 text-xs text-gray-500">
							{$i18n.t('Channel Name')}
							<span class="text-xs text-gray-200 dark:text-gray-800 ml-0.5">
								{type === 'dm' ? `${$i18n.t('Optional')}` : ''}
							</span>
						</div>

						<div class="flex-1">
							<input
								class="w-full text-sm bg-transparent placeholder:text-gray-300 dark:placeholder:text-gray-700 outline-hidden"
								type="text"
								value={name}
								on:input={onNameInput}
								placeholder={`${$i18n.t('new-channel')}`}
								autocomplete="off"
								required={type !== 'dm'}
								maxlength="128"
							/>
						</div>
					</div>

					{#if type !== 'dm'}
						<div class="-mx-2 mb-1 mt-2.5 px-2">
							{#if type === ''}
								<AccessControl bind:accessGrants accessRoles={['read', 'write']} />
							{:else if type === 'group'}
								<!-- ✅ FIX 3: no TS in markup: onChange={(value: string) => ...} -->
								<Visibility
									state={isPrivate ? 'private' : 'public'}
									onChange={handleVisibilityChange}
								/>
							{/if}
						</div>
					{/if}

					{#if ['dm'].includes(type)}
						<div>
							<MemberSelector bind:userIds includeGroups={false} />
						</div>
					{/if}

					{#if edit}
						<div class="flex w-full mt-2 items-center justify-between">
							<div class="text-xs text-gray-500">{$i18n.t('Webhooks')}</div>

							<button
								class="text-xs bg-transparent placeholder:text-gray-300 dark:placeholder:text-gray-700 outline-hidden text-left"
								type="button"
								on:click={() => (showWebhooksModal = true)}
							>
								{$i18n.t('Manage')}
							</button>
						</div>
					{/if}

					<div class="flex justify-end pt-3 text-sm font-medium gap-1.5">
						{#if edit}
							<button
								class="px-3.5 py-1.5 text-sm font-medium dark:bg-black dark:hover:bg-black/90 dark:text-white bg-white text-black hover:bg-gray-100 transition rounded-full flex flex-row space-x-1 items-center"
								type="button"
								on:click={() => (showDeleteConfirmDialog = true)}
							>
								{$i18n.t('Delete')}
							</button>
						{/if}

						<button
							class="px-3.5 py-1.5 text-sm font-medium bg-black hover:bg-gray-950 text-white dark:bg-white dark:text-black dark:hover:bg-gray-100 transition rounded-full flex flex-row space-x-1 items-center {loading ? ' cursor-not-allowed' : ''}"
							type="submit"
							disabled={loading}
						>
							{#if edit}
								{$i18n.t('Update')}
							{:else}
								{$i18n.t('Create')}
							{/if}

							{#if loading}
								<div class="ml-2 self-center">
									<Spinner />
								</div>
							{/if}
						</button>
					</div>
				</form>
			</div>
		</div>
	</div>
</Modal>

<DeleteConfirmDialog
	bind:show={showDeleteConfirmDialog}
	message={$i18n.t('Are you sure you want to delete this channel?')}
	confirmLabel={$i18n.t('Delete')}
	on:confirm={deleteHandler}
/>

<WebhooksModal bind:show={showWebhooksModal} {channel} />
