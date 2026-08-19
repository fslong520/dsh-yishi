// dsh-yishi v0.2 真实 cordis 环境验证：
// 1) apply 同步 resources → ~/.local/share/忆时/{docs,scripts}
// 2) 指令 section 注入（读 docs/yishi-instructions.md）
// 3) memocap 技能注册（provider 读 docs/SKILL.md）
// 4) 同步后脚本可跑（memory_core.py stats）
import { Context } from 'file:///var/opt/node24/lib/node_modules/@deepseek-ai/dsh/node_modules/@deepseek-ai/cordis/lib/index.js';
import SkillRegistry from 'file:///var/opt/node24/lib/node_modules/@deepseek-ai/dsh/node_modules/@deepseek-ai/dsh-skill/lib/index.js';
import SystemPrompt from 'file:///var/opt/node24/lib/node_modules/@deepseek-ai/dsh/node_modules/@deepseek-ai/dsh-system-prompt/lib/index.js';
import { existsSync } from 'node:fs';
import { homedir } from 'node:os';
import { join } from 'node:path';

const dataBase = join(homedir(), '.local', 'share', '忆时');

const ctx = new Context();
await ctx.plugin(SkillRegistry);
await ctx.plugin(SystemPrompt);

const mod = await import('file:///home/fslong/Documents/yishi/lib/index.js');
console.log('plugin:', mod.name);

await ctx.plugin({ name: mod.name, inject: mod.inject, apply: mod.apply });

// 1. 同步验证
const docsSkill = join(dataBase, 'docs', 'SKILL.md');
const docsInstr = join(dataBase, 'docs', 'yishi-instructions.md');
const scriptsCore = join(dataBase, 'scripts', 'memory_core.py');
const scriptsViz = join(dataBase, 'scripts', 'viz', 'viz.py');
console.log('sync docs/SKILL.md:', existsSync(docsSkill));
console.log('sync docs/yishi-instructions.md:', existsSync(docsInstr));
console.log('sync scripts/memory_core.py:', existsSync(scriptsCore));
console.log('sync scripts/viz/viz.py:', existsSync(scriptsViz));

// 2. 指令 section
const assembly = await ctx.systemPrompt.assemble({});
const yishi = assembly.sections.find((s) => s.name === 'yishi:instructions');
console.log('yishi section:', Boolean(yishi), yishi ? `(${yishi.text.length} chars)` : '');

// 3. 技能注册
const skills = await ctx.skills.list({});
const memocap = skills.find((s) => s.name === 'memocap');
console.log(
	'memocap:',
	Boolean(memocap),
	memocap ? `provider=${memocap.provider} resourceBase=${JSON.stringify(memocap.resourceBase)}` : '',
);
if (memocap) {
	const def = await ctx.skills.get('memocap', {});
	console.log('memocap body head:', def?.content?.slice(0, 30).replace(/\n/g, ' '));
}

// 4. 同步后脚本可跑（用数据目录 scripts）
const { execFileSync } = await import('node:child_process');
if (existsSync(scriptsCore)) {
	const out = execFileSync('python3', [scriptsCore, 'stats'], {
		env: { ...process.env, MEMO_DIR: join(dataBase, 'data') },
		encoding: 'utf8',
		maxBuffer: 1024 * 1024,
	});
	console.log('script stats head:', out.split('\n').slice(0, 4).join(' | '));
}

console.log('REAL TEST OK');