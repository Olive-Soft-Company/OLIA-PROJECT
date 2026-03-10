/**
 * Map file extensions to Shiki language identifiers.
 * Only extensions whose Shiki lang id differs from the extension itself need explicit entries.
 */
const EXT_OVERRIDE: Record<string, string> = {
	py: 'python',
	js: 'javascript',
	ts: 'typescript',
	jsx: 'jsx',
	tsx: 'tsx',
	rb: 'ruby',
	rs: 'rust',
	kt: 'kotlin',
	cs: 'csharp',
	fs: 'fsharp',
	sh: 'bash',
	bash: 'bash',
	zsh: 'bash',
	yml: 'yaml',
	md: 'markdown',
	mdx: 'mdx',
	dockerfile: 'dockerfile',
	tf: 'terraform',
	hcl: 'hcl',
	ex: 'elixir',
	exs: 'elixir',
	erl: 'erlang',
	hs: 'haskell',
	ml: 'ocaml',
	mli: 'ocaml',
	pl: 'perl',
	pm: 'perl',
	r: 'r',
	m: 'objective-c',
	mm: 'objective-cpp',
	h: 'c',
	hpp: 'cpp',
	cc: 'cpp',
	cxx: 'cpp',
	proto: 'proto',
	nim: 'nim',
	zig: 'zig',
	v: 'v',
	svelte: 'svelte',
	vue: 'vue',
	astro: 'astro',
	prisma: 'prisma',
	graphql: 'graphql',
	gql: 'graphql',
	jsonc: 'jsonc',
	jsonl: 'jsonl'
};

/**
 * Common extensions that exactly match their Shiki language ID.
 */
const KNOWN_LANG_IDS = new Set([
	'ada','awk','bat','c','cmake','clojure','cpp','crystal','css','d','dart','diff',
	'elixir','elm','erlang','fish','gleam','glsl','go','groovy','haml','haskell',
	'hlsl','html','ini','java','javascript','json','json5','jsonc','jsx','julia',
	'kotlin','latex','less','lisp','log','lua','make','markdown','matlab','mdx',
	'mojo','nim','nix','nushell','ocaml','pascal','perl','php','postcss',
	'powershell','prisma','prolog','proto','pug','python','r','ruby','rust',
	'sass','scala','scheme','scss','solidity','sql','svelte','swift','tcl',
	'terraform','tex','toml','tsx','typescript','typst','v','vb','verilog',
	'vhdl','vue','wasm','wgsl','xml','yaml','zig'
]);

/**
 * Resolve a file extension to a Shiki language id, or null if not supported.
 */
export function extToLang(ext: string): string | null {
	const lower = ext.toLowerCase();

	if (EXT_OVERRIDE[lower]) {
		return EXT_OVERRIDE[lower];
	}

	if (KNOWN_LANG_IDS.has(lower)) {
		return lower;
	}

	return null;
}

/**
 * Returns true if the given file path has a code-file extension that Shiki can highlight.
 */
export function isCodeFile(path: string | null): boolean {
	if (!path) return false;

	const parts = path.split('.');
	if (parts.length < 2) return false;

	const ext = parts.pop()?.toLowerCase() ?? '';
	return extToLang(ext) !== null;
}

/**
 * Singleton loader for Shiki (loaded once only).
 */
let shikiModulePromise: Promise<any> | null = null;

async function loadShiki() {
	if (!shikiModulePromise) {
		shikiModulePromise = import(
			'https://cdn.jsdelivr.net/npm/shiki@1.0.0/dist/index.mjs'
		);
	}
	return shikiModulePromise;
}

/**
 * Escape HTML characters (fallback safety).
 */
function escapeHtml(str: string): string {
	return str
		.replace(/&/g, '&amp;')
		.replace(/</g, '&lt;')
		.replace(/>/g, '&gt;');
}

/**
 * Highlight code using Shiki with dual light/dark themes.
 * Returns an HTML string.
 */
export async function highlightCode(code: string, filePath: string): Promise<string> {
	const parts = filePath.split('.');
	const ext = parts.length > 1 ? parts.pop()?.toLowerCase() ?? '' : '';

	const lang = extToLang(ext) ?? 'text';

	try {
		const shiki = await loadShiki();

		const html = await shiki.codeToHtml(code, {
			lang,
			themes: {
				light: 'github-light',
				dark: 'github-dark'
			},
			defaultColor: 'light'
		});

		return html;
	} catch (error) {
		console.error('Shiki highlight error:', error);

		// Safe fallback if highlighting fails
		return `<pre><code>${escapeHtml(code)}</code></pre>`;
	}
}