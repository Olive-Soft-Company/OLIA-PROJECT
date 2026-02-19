<script lang="ts">
	import { getContext, onMount, tick } from 'svelte';

	const i18n = getContext('i18n');

	import { getGroups, getGroupInfoById } from '$lib/apis/groups';
	import { getUserInfoById } from '$lib/apis/users';
	import { OLIA_API_BASE_URL } from '$lib/constants';

	import XMark from '$lib/components/icons/XMark.svelte';
	import Badge from '$lib/components/common/Badge.svelte';
	import Plus from '$lib/components/icons/Plus.svelte';
	import AddAccessModal from './AddAccessModal.svelte';
	import Tooltip from '$lib/components/common/Tooltip.svelte';

	// -----------------------------
	// Types
	// -----------------------------
	type AccessGrant = {
		id?: string;
		principal_type: 'user' | 'group';
		principal_id: string;
		permission: 'read' | 'write';
	};

	type LegacyAccessControl = {
		read: { group_ids: string[]; user_ids: string[] };
		write: { group_ids: string[]; user_ids: string[] };
	};

	// -----------------------------
	// Props
	// -----------------------------
	export let onChange: (grants: AccessGrant[]) => void = () => {};

	export let accessRoles: Array<'read' | 'write'> = ['read'];
	export let accessGrants: AccessGrant[] | any = [];
	// legacy (optional): null => public read, object => read/write lists, undefined => ignore
	export let accessControl: any = undefined;

	export let share = true;
	export let sharePublic = true;

	// -----------------------------
	// State
	// -----------------------------
	let groups: any[] = [];
	let accessGroups: any[] = [];

	let userById: Record<string, any> = {};
	let selectedUsers: any[] = [];

	let showAddAccessModal = false;
	let selectedUserIds: string[] = [];

	const resolvingGroupIds = new Set<string>();
	const resolvingUserIds = new Set<string>();

	// -----------------------------
	// Helpers
	// -----------------------------
	const dedupeAccessGrants = (grants: AccessGrant[] | null | undefined): AccessGrant[] => {
		if (!Array.isArray(grants)) return [];
		const map = new Map<string, AccessGrant>();

		for (const grant of grants) {
			if (!grant) continue;
			if (!grant.principal_type || !grant.principal_id || !grant.permission) continue;

			const key = `${grant.principal_type}:${grant.principal_id}:${grant.permission}`;
			map.set(key, {
				id: grant.id,
				principal_type: grant.principal_type,
				principal_id: grant.principal_id,
				permission: grant.permission
			});
		}

		return Array.from(map.values());
	};

	const stableStringify = (value: any): string => {
		try {
			return JSON.stringify(value ?? null);
		} catch {
			return '';
		}
	};

	const hasPublicReadGrant = (grants: AccessGrant[]): boolean =>
		grants.some(
			(g) => g.principal_type === 'user' && g.principal_id === '*' && g.permission === 'read'
		);

	const legacyAccessControlToGrants = (value: any): AccessGrant[] => {
		// Convention: accessControl === null => public read
		if (value === null) {
			return [{ principal_type: 'user', principal_id: '*', permission: 'read' }];
		}

		if (!value || typeof value !== 'object') return [];

		const grants: AccessGrant[] = [];
		for (const permission of ['read', 'write'] as const) {
			const entry = value?.[permission] ?? {};
			for (const groupId of entry?.group_ids ?? []) {
				grants.push({ principal_type: 'group', principal_id: groupId, permission });
			}
			for (const userId of entry?.user_ids ?? []) {
				grants.push({ principal_type: 'user', principal_id: userId, permission });
			}
		}

		return dedupeAccessGrants(grants);
	};

	const grantsToLegacyAccessControl = (grants: AccessGrant[]): null | LegacyAccessControl => {
		const normalized = dedupeAccessGrants(grants);

		// If public read => represent as null
		if (hasPublicReadGrant(normalized)) return null;

		const result: LegacyAccessControl = {
			read: { group_ids: [], user_ids: [] },
			write: { group_ids: [], user_ids: [] }
		};

		for (const grant of normalized) {
			if (grant.permission !== 'read' && grant.permission !== 'write') continue;

			if (grant.principal_type === 'group') {
				if (!result[grant.permission].group_ids.includes(grant.principal_id)) {
					result[grant.permission].group_ids = [
						...result[grant.permission].group_ids,
						grant.principal_id
					];
				}
			} else if (grant.principal_type === 'user' && grant.principal_id !== '*') {
				if (!result[grant.permission].user_ids.includes(grant.principal_id)) {
					result[grant.permission].user_ids = [
						...result[grant.permission].user_ids,
						grant.principal_id
					];
				}
			}
		}

		return result;
	};

	const normalizeInputToGrants = (value: any): AccessGrant[] => {
		if (value === null) return legacyAccessControlToGrants(null);
		if (Array.isArray(value)) return dedupeAccessGrants(value);
		if (value && typeof value === 'object' && ('read' in value || 'write' in value)) {
			return legacyAccessControlToGrants(value);
		}
		return [];
	};

	// -----------------------------
	// ✅ Safe sync (NO reactive assignment cycles)
	// -----------------------------
	let lastAccessControlSig = '';
	let lastAccessGrantsSig = '';
	const sig = (v: any) => stableStringify(v);

	// parent legacy -> grants
	const syncFromAccessControl = async () => {
		if (accessControl === undefined) return;

		const s = sig(accessControl);
		if (s === lastAccessControlSig) return;
		lastAccessControlSig = s;

		const grantsFromAC = normalizeInputToGrants(accessControl);

		if (sig(grantsFromAC) !== sig(accessGrants)) {
			accessGrants = grantsFromAC;
			lastAccessGrantsSig = sig(accessGrants);
		}

		await tick();
	};

	// grants -> legacy (only if legacy prop exists)
	const syncToAccessControl = async () => {
		if (accessControl === undefined) return;

		const s = sig(accessGrants);
		if (s === lastAccessGrantsSig) return;
		lastAccessGrantsSig = s;

		const normalized = dedupeAccessGrants(Array.isArray(accessGrants) ? accessGrants : []);
		const nextAccessControl = grantsToLegacyAccessControl(normalized);

		if (sig(nextAccessControl) !== sig(accessControl)) {
			accessControl = nextAccessControl;
			lastAccessControlSig = sig(accessControl);
		}

		await tick();
	};

	// If your parent can change accessControl AFTER mount,
	// keep a *one-way* watcher but DO NOT write accessControl inside it.
	$: if (accessControl !== undefined) {
		void syncFromAccessControl();
	}

	// -----------------------------
	// ✅ Read-only derived snapshot
	// -----------------------------
	$: normalizedGrants = dedupeAccessGrants(
		Array.isArray(accessGrants) ? (accessGrants as AccessGrant[]) : []
	);

	const getPrincipalIdsByPermissionFrom = (
		grants: AccessGrant[],
		principalType: 'user' | 'group',
		permission: 'read' | 'write'
	): string[] => {
		const ids = grants
			.filter((g) => g.principal_type === principalType && g.permission === permission)
			.map((g) => g.principal_id);
		return Array.from(new Set(ids));
	};

	const hasPrincipalGrant = (
		principalType: 'user' | 'group',
		principalId: string,
		permission: 'read' | 'write'
	): boolean =>
		normalizedGrants.some(
			(g) =>
				g.principal_type === principalType &&
				g.principal_id === principalId &&
				g.permission === permission
		);

	const commitAccessGrants = (next: AccessGrant[]) => {
		const deduped = dedupeAccessGrants(next);
		accessGrants = deduped;
		onChange(deduped);

		// keep legacy accessControl prop in sync without reactive $:
		void syncToAccessControl();
	};

	const setPublic = (isPublic: boolean) => {
		const filtered = normalizedGrants.filter(
			(g) => !(g.principal_type === 'user' && g.principal_id === '*' && g.permission === 'read')
		);

		if (isPublic) {
			filtered.push({ principal_type: 'user', principal_id: '*', permission: 'read' });
		}

		commitAccessGrants(filtered);
	};

	function handleVisibilityChange(e: Event) {
		const select = e.currentTarget as HTMLSelectElement | null;
		setPublic((select?.value ?? 'private') === 'public');
	}

	const upsertPrincipalGrant = (
		principalType: 'user' | 'group',
		principalId: string,
		permission: 'read' | 'write',
		grants: AccessGrant[]
	): AccessGrant[] => {
		const exists = grants.some(
			(g) =>
				g.principal_type === principalType &&
				g.principal_id === principalId &&
				g.permission === permission
		);
		if (exists) return grants;
		return [...grants, { principal_type: principalType, principal_id: principalId, permission }];
	};

	const removePrincipalGrant = (
		principalType: 'user' | 'group',
		principalId: string,
		permission: 'read' | 'write',
		grants: AccessGrant[]
	): AccessGrant[] =>
		grants.filter(
			(g) =>
				!(
					g.principal_type === principalType &&
					g.principal_id === principalId &&
					g.permission === permission
				)
		);

	const removePrincipal = (principalType: 'user' | 'group', principalId: string) => {
		let next = [...normalizedGrants];
		next = removePrincipalGrant(principalType, principalId, 'read', next);
		next = removePrincipalGrant(principalType, principalId, 'write', next);
		commitAccessGrants(next);
	};

	const togglePrincipalWrite = (principalType: 'user' | 'group', principalId: string) => {
		let next = [...normalizedGrants];
		const hasWrite = hasPrincipalGrant(principalType, principalId, 'write');

		if (hasWrite) {
			next = removePrincipalGrant(principalType, principalId, 'write', next);
		} else {
			// if write => ensure read too
			next = upsertPrincipalGrant(principalType, principalId, 'read', next);
			next = upsertPrincipalGrant(principalType, principalId, 'write', next);
		}

		commitAccessGrants(next);
	};

	const ensureUsersByIds = async (userIds: string[]) => {
		const pending = userIds.filter((id) => !userById[id] && !resolvingUserIds.has(id));
		if (!pending.length) return;

		pending.forEach((id) => resolvingUserIds.add(id));

		const fetched = await Promise.all(
			pending.map(async (id) => {
				const u = await getUserInfoById(localStorage.token, id).catch((err) => {
					console.error(err);
					return null;
				});
				return { id, user: u };
			})
		);

		const next = { ...userById };
		for (const item of fetched) {
			if (item.user?.id) next[item.id] = item.user;
			resolvingUserIds.delete(item.id);
		}

		userById = next;
	};

	const ensureGroupsByIds = async (groupIds: string[]) => {
		const pending = groupIds.filter(
			(id) => !groups.find((g) => g.id === id) && !resolvingGroupIds.has(id)
		);
		if (!pending.length) return;

		pending.forEach((id) => resolvingGroupIds.add(id));

		const fetched = await Promise.all(
			pending.map(async (id) => {
				const g = await getGroupInfoById(localStorage.token, id).catch((err) => {
					console.error(err);
					return null;
				});
				return g;
			})
		);

		const newGroups = fetched.filter(Boolean);
		if (newGroups.length) {
			groups = [...groups, ...newGroups].filter(
				(g, idx, self) => idx === self.findIndex((t) => t.id === g.id)
			);
		}

		pending.forEach((id) => resolvingGroupIds.delete(id));
	};

	const handleAddAccess = ({ userIds, groupIds }: { userIds: string[]; groupIds: string[] }) => {
		let next = [...normalizedGrants];

		for (const gid of groupIds) {
			next = upsertPrincipalGrant('group', gid, 'read', next);
		}
		for (const uid of userIds) {
			next = upsertPrincipalGrant('user', uid, 'read', next);
		}

		commitAccessGrants(next);
	};

	function onUserImgError(e: Event) {
		const img = e.currentTarget as HTMLImageElement | null;
		if (img) img.src = '/user.png';
	}

	// -----------------------------
	// Derived values
	// -----------------------------
	$: readGroupIds = getPrincipalIdsByPermissionFrom(normalizedGrants, 'group', 'read');
	$: writeGroupIds = getPrincipalIdsByPermissionFrom(normalizedGrants, 'group', 'write');

	$: readUserIds = getPrincipalIdsByPermissionFrom(normalizedGrants, 'user', 'read').filter(
		(id) => id !== '*'
	);
	$: writeUserIds = getPrincipalIdsByPermissionFrom(normalizedGrants, 'user', 'write').filter(
		(id) => id !== '*'
	);

	$: selectedUserIds = Array.from(new Set([...readUserIds, ...writeUserIds]));

	$: selectedUsers = selectedUserIds
		.map((id) => userById[id] ?? { id, name: id, email: '' })
		.sort((a, b) => (a.name ?? '').localeCompare(b.name ?? ''));

	$: accessGroups = groups
		.filter((g) => readGroupIds.includes(g.id) || writeGroupIds.includes(g.id))
		.sort((a, b) => (a.name ?? '').localeCompare(b.name ?? ''));

	$: if (selectedUserIds.length > 0) void ensureUsersByIds(selectedUserIds);
	$: if (readGroupIds.length > 0 || writeGroupIds.length > 0) {
		void ensureGroupsByIds(Array.from(new Set([...readGroupIds, ...writeGroupIds])));
	}

	// -----------------------------
	// Mount
	// -----------------------------
	onMount(async () => {
		// initial sync from parent accessControl -> accessGrants
		await syncFromAccessControl();

		const res = await getGroups(localStorage.token, true).catch((err) => {
			console.error(err);
			return [];
		});

		groups = [...groups, ...res].filter(
			(g, idx, self) => idx === self.findIndex((t) => t.id === g.id)
		);
	});
</script>

<AddAccessModal bind:show={showAddAccessModal} onAdd={handleAddAccess} />

<div class="rounded-lg flex flex-col gap-1">
	<div class="py-2">
		<div class="flex gap-2.5 items-center">
			<div>
				<div class="p-2 bg-black/5 dark:bg-white/5 rounded-full">
					{#if !hasPublicReadGrant(normalizedGrants)}
						<svg
							xmlns="http://www.w3.org/2000/svg"
							fill="none"
							viewBox="0 0 24 24"
							stroke-width="1.5"
							stroke="currentColor"
							class="w-5 h-5"
						>
							<path
								stroke-linecap="round"
								stroke-linejoin="round"
								d="M16.5 10.5V6.75a4.5 4.5 0 10-9 0v3.75m-.75 11.25h10.5a2.25 2.25 0 002.25-2.25v-6.75a2.25 2.25 0 00-2.25-2.25H6.75a2.25 2.25 0 00-2.25 2.25v6.75a2.25 2.25 0 002.25 2.25z"
							/>
						</svg>
					{:else}
						<svg
							xmlns="http://www.w3.org/2000/svg"
							fill="none"
							viewBox="0 0 24 24"
							stroke-width="1.5"
							stroke="currentColor"
							class="w-5 h-5"
						>
							<path
								stroke-linecap="round"
								stroke-linejoin="round"
								d="M6.115 5.19l.319 1.913A6 6 0 008.11 10.36L9.75 12l-.387.775c-.217.433-.132.956.21 1.298l1.348 1.348c.21.21.329.497.329.795v1.089c0 .426.24.815.622 1.006l.153.076c.433.217.956.132 1.298-.21l.723-.723a8.7 8.7 0 002.288-4.042 1.087 1.087 0 00-.358-1.099l-1.33-1.108c-.251-.21-.582-.299-.905-.245l-1.17.195a1.125 1.125 0 01-.98-.314l-.295-.295a1.125 1.125 0 010-1.591l.13-.132a1.125 1.125 0 011.3-.21l.603.302a.809.809 0 001.086-1.086L14.25 7.5l1.256-.837a4.5 4.5 0 001.528-1.732l.146-.292M6.115 5.19A9 9 0 1017.18 4.64M6.115 5.19A8.965 8.965 0 0112 3c1.929 0 3.716.607 5.18 1.64"
							/>
						</svg>
					{/if}
				</div>
			</div>

			<div>
				<Tooltip
					content={!(share && sharePublic) && !hasPublicReadGrant(normalizedGrants)
						? $i18n.t('You do not have permission to make this public')
						: ''}
				>
					<select
						id="visibility"
						class="dark:bg-gray-900 outline-none bg-transparent text-sm font-medium block w-fit pr-10 max-w-full placeholder-gray-400"
						value={!hasPublicReadGrant(normalizedGrants) ? 'private' : 'public'}
						on:change={handleVisibilityChange}
					>
						<option class="text-gray-700" value="private">{$i18n.t('Private')}</option>
						{#if (share && sharePublic) || hasPublicReadGrant(normalizedGrants)}
							<option class="text-gray-700" value="public">{$i18n.t('Public')}</option>
						{/if}
					</select>
				</Tooltip>

				<div class="text-xs text-gray-400 font-medium">
					{#if !hasPublicReadGrant(normalizedGrants)}
						{$i18n.t('Only select users and groups with permission can access')}
					{:else}
						{$i18n.t('Accessible to all users')}
					{/if}
				</div>
			</div>
		</div>
	</div>

	{#if share}
		<div class="flex items-center justify-between text-xs font-medium text-gray-500 my-1">
			<div>{$i18n.t('Access List')}</div>

			<div class="flex gap-1">
				<button
					class="px-2 py-1 bg-transparent hover:bg-gray-100 dark:hover:bg-gray-800 rounded-lg transition text-xs font-medium flex items-center gap-1"
					type="button"
					on:click={() => (showAddAccessModal = true)}
				>
					<Plus className="size-3" />
					{$i18n.t('Add Access')}
				</button>
			</div>
		</div>

		<div class="flex flex-col gap-2">
			<!-- Groups -->
			{#each accessGroups as group (group.id)}
				<div class="flex items-center gap-3 justify-between text-sm w-full transition pb-1">
					<div class="flex items-center gap-2 w-full flex-1">
						<div
							class="size-5 rounded-full bg-gray-100 dark:bg-gray-850 flex items-center justify-center text-xs"
						>
							{(group.name ?? '').charAt(0).toUpperCase()}
						</div>

						<div class="truncate text-sm flex items-center gap-2">
							{group.name}
							<span class="text-xs text-gray-400 font-normal">
								{group?.member_count} {$i18n.t('members')}
							</span>
						</div>
					</div>

					<div class="w-full flex justify-end items-center gap-2">
						<button
							type="button"
							on:click={() => {
								if (accessRoles.includes('write')) togglePrincipalWrite('group', group.id);
							}}
						>
							{#if writeGroupIds.includes(group.id)}
								<Badge type="success" content={$i18n.t('Write')} />
							{:else}
								<Badge type="info" content={$i18n.t('Read')} />
							{/if}
						</button>

						<button
							class="rounded-full p-1 hover:bg-gray-100 dark:hover:bg-gray-850 transition"
							type="button"
							on:click={() => removePrincipal('group', group.id)}
						>
							<XMark className="size-4" />
						</button>
					</div>
				</div>
			{/each}

			<!-- Users -->
			{#each selectedUsers as u (u.id)}
				<div
					class="flex items-center gap-3 justify-between text-sm w-full transition border-b border-gray-50 dark:border-gray-850 pb-2 last:border-0"
				>
					<div class="flex items-center gap-2 w-full flex-1">
						<img
							class="rounded-full size-5 object-cover"
							src={`${OLIA_API_BASE_URL}/users/${u.id}/profile/image`}
							alt={u.name ?? u.id}
							on:error={onUserImgError}
						/>
						<div class="w-full">
							<Tooltip content={u.email} placement="top-start">
								<div class="truncate text-sm">{u.name ?? u.id}</div>
							</Tooltip>
						</div>
					</div>

					<div class="w-full flex justify-end items-center gap-2">
						<button
							type="button"
							on:click={() => {
								if (accessRoles.includes('write')) togglePrincipalWrite('user', u.id);
							}}
						>
							{#if writeUserIds.includes(u.id)}
								<Badge type="success" content={$i18n.t('Write')} />
							{:else}
								<Badge type="info" content={$i18n.t('Read')} />
							{/if}
						</button>

						<button
							class="rounded-full p-1 hover:bg-gray-100 dark:hover:bg-gray-850 transition"
							type="button"
							on:click={() => removePrincipal('user', u.id)}
						>
							<XMark className="size-4" />
						</button>
					</div>
				</div>
			{/each}

			{#if !hasPublicReadGrant(normalizedGrants) && accessGroups.length === 0 && selectedUsers.length === 0}
				<div class="text-xs text-gray-500 text-center py-4">
					{$i18n.t('No access grants. Private to you.')}
				</div>
			{/if}
		</div>
	{/if}
</div>