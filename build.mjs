// dsh-yishi 构建：esbuild 打包 src/index.ts → lib/index.js（ESM node 插件）。
// 忆时插件纯 node 端，仅依赖内置模块；bundle 为单文件，随包分发。
import { build } from 'esbuild';

await build({
	entryPoints: ['src/index.ts'],
	outfile: 'lib/index.js',
	bundle: true,
	platform: 'node',
	format: 'esm',
	target: 'node20',
	sourcemap: true,
	external: ['@deepseek-ai/cordis'],
});

console.log('dsh-yishi build -> lib/index.js');
