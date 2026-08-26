// dsh-yishi：忆时记忆系统 DSH 插件（node 端，自包含）。
//
// 职责（全功能迁入插件，不依赖 opencode 技能目录）：
//   1. 同步资源——把插件包内 docs（SKILL.md / yishi-instructions.md /
//      modules / references）与 scripts（memory_core.py / viz/）复制到
//      忆时根目录（~/.local/share/yishi/），幂等覆盖，插件版本为权威。
//   2. 注入忆时指令——systemPrompt.section 读
//      <忆时根>/docs/yishi-instructions.md。
//   3. 保障忆时技能——ctx.skills.registerProvider 注册 memocap，
//      读 <忆时根>/docs/SKILL.md，resourceBase 指向 docs/。
//
// 数据（data/ Chroma 库、models/ bge 模型）亦存忆时根目录，双栖共用——
// opencode 忆时技能作废后，插件为唯一提供者。
//
// 环境变量：
//   YISHI_DATA_DIR   忆时根目录（默认 ~/.local/share/yishi）
//   DSH_YISHI_DISABLE 设为 1 禁用插件

import { cpSync, existsSync, mkdirSync, openSync, closeSync, readFileSync, writeSync } from 'node:fs';
import { spawn } from 'node:child_process';
import { homedir } from 'node:os';
import { join } from 'node:path';
import { fileURLToPath } from 'node:url';

export const name = 'dsh-yishi';
export const inject = ['systemPrompt', 'skills'];

const SKILL_NAME = 'memocap';
const PROVIDER_NAME = 'dsh-yishi';
// 兜底 rank：低于 bundled(600)，高于 user-agents(500)；filesystem 之
// custom(300) 同层时更近者胜，故插件 rank 仅作最末兜底。
const PROVIDER_RANK = 550;

/** 插件包根目录（lib/index.js → 包根）。 */
const PLUGIN_DIR = fileURLToPath(new URL('..', import.meta.url));

/** 忆时根目录解析：环境变量 > 默认 ~/.local/share/yishi（全英文，跨平台统一，避免中文路径乱码）。 */
function resolveDataBase() {
	const env = process.env.YISHI_DATA_DIR;
	return env ? env : join(homedir(), '.local', 'share', 'yishi');
}

/** 极简 frontmatter 解析（YAML 子集）：取 name 与 description。 */
function parseFrontmatter(md) {
	const m = /^---\r?\n([\s\S]*?)\r?\n---/.exec(md);
	if (!m) return null;
	const fm = m[1];
	const line = (key) => {
		const re = new RegExp(`^${key}:\\s*(.+?)\\s*$`, 'm');
		const v = re.exec(fm)?.[1];
		return v ? v.replace(/^["']|["']$/g, '') : undefined;
	};
	return { name: line('name'), description: line('description') };
}

/** 去掉 frontmatter，返回纯 Markdown 正文。 */
function stripFrontmatter(md) {
	return md.replace(/^---\r?\n[\s\S]*?\r?\n---\r?\n?/, '');
}

/** kebab-case 技能名校验（DSH 要求）。 */
function isKebabName(s) {
	return /^[a-z0-9]+(?:-[a-z0-9]+)*$/.test(s);
}

/** 同步插件资源至忆时根（docs+scripts），幂等覆盖，失败仅警告不中断。 */
function syncResources(ctx, dataBase) {
	const docsDest = join(dataBase, 'docs');
	const scriptsDest = join(dataBase, 'scripts');
	const docsItems = [
		['SKILL.md', join(PLUGIN_DIR, 'SKILL.md')],
		['yishi-instructions.md', join(PLUGIN_DIR, 'yishi-instructions.md')],
		['modules', join(PLUGIN_DIR, 'modules')],
		['references', join(PLUGIN_DIR, 'references')],
	];
	try {
		mkdirSync(docsDest, { recursive: true });
		mkdirSync(scriptsDest, { recursive: true });
		for (const [name, src] of docsItems) {
			if (!existsSync(src)) continue;
			cpSync(src, join(docsDest, name), { recursive: true, force: true });
		}
		const scriptsSrc = join(PLUGIN_DIR, 'scripts');
		if (existsSync(scriptsSrc)) {
			cpSync(scriptsSrc, scriptsDest, { recursive: true, force: true });
		}
		return { docsDest, scriptsDest };
	} catch (e) {
		ctx.logger?.warn?.(`${name}: sync failed: ${String(e?.message ?? e)}`);
		return null;
	}
}

export function apply(ctx) {
	if (process.env.DSH_YISHI_DISABLE === '1') {
		ctx.logger?.info?.(`${name}: disabled by DSH_YISHI_DISABLE`);
		return;
	}

	const dataBase = resolveDataBase();
	const synced = syncResources(ctx, dataBase);
	const docsDir = synced ? synced.docsDest : join(dataBase, 'docs');
	const instructionsPath = join(docsDir, 'yishi-instructions.md');
	const skillPath = join(docsDir, 'SKILL.md');

	// ── 3. 环境保障：依赖缺失 → 后台安装；模型缺失 → 后台下载；
	//    模型就绪后建 data；幂等合并 opencode 外挂提示词 ───────────
	// 统一入口 scripts/install.py（幂等，sys.executable 自定解释器，无 python3/python 之争）。
	// 独立 try/catch 且置于注入/注册之前——任一环节失败不阻断注入。
	// 输出落盘 install.log，失败有痕可查。
	try {
		const scriptsDir = synced ? synced.scriptsDest : join(dataBase, 'scripts');
		const installPy = join(scriptsDir, 'install.py');
		if (!existsSync(installPy)) {
			ctx.logger?.warn?.(`${name}: 无自愈脚本 ${installPy}；环境问题请手动运行 install.py`);
		} else {
			// 跨平台解释器候选：Windows 用 python/py（仅 python 亦可用），其余 python3。
			const pyCandidates =
				process.platform === 'win32' ? ['python', 'py', 'python3'] : ['python3', 'python'];
			// 后台跑 python <args>，输出落盘 <logFile>；候选解释器逐个试。
			const runPython = (args, logFile, label, onDone) => {
				const out = openSync(logFile, 'a');
				const stamp = `\n[${new Date().toISOString()}] ${name} ${label}\n`;
				writeSync(out, stamp);
				let pyIdx = 0;
				const trySpawn = () => {
					if (pyIdx >= pyCandidates.length) {
						try { closeSync(out); } catch {}
						ctx.logger?.error?.(
							`${name}: python 解释器均不可用（${pyCandidates.join(', ')}）；请手动运行 ${installPy}`,
						);
						return;
					}
					const child = spawn(pyCandidates[pyIdx], args, {
						detached: true,
						stdio: ['ignore', out, out],
					});
					child.on('error', (err) => {
						pyIdx += 1;
						trySpawn();
					});
					child.on('exit', (code) => {
						try { closeSync(out); } catch {}
						onDone?.(code);
					});
					child.unref();
				};
				trySpawn();
			};
			// 3a. 依赖检测：import 失败 → 后台 pip 安装
			const depsCheck = () =>
				runPython(
					['-c', 'import chromadb, jieba, onnxruntime, tokenizers, numpy'],
					join(dataBase, 'deps-check.log'),
					'deps-check',
					(code) => {
						if (code !== 0) {
							ctx.logger?.info?.(`${name}: 依赖缺失（rc=${code}），后台安装依赖`);
							runPython(
								[installPy, '--deps-only'],
								join(dataBase, 'install.log'),
								'deps-install',
								(c) => ctx.logger?.info?.(`${name}: 依赖安装退出码 ${c}`),
							);
						}
					},
				);
			// 3b. 模型保障：缺失 → 后台下载（install.py 幂等，跳过已装依赖）；
			//     模型就绪后链跑 --init-only 建 data（init 需加载 embedding，须在模型后）
			const modelFile = join(dataBase, 'models', 'bge-base-zh-v1.5', 'onnx', 'model.onnx');
			const initData = () =>
				runPython(
					[installPy, '--init-only'],
					join(dataBase, 'install.log'),
					'init-data',
					(code) => ctx.logger?.info?.(`${name}: 数据初始化退出码 ${code}`),
				);
			if (!existsSync(modelFile)) {
				depsCheck();
				ctx.logger?.info?.(
					`${name}: bge 模型缺失，尝试后台下载（${pyCandidates[0]}）；若未生效请手动运行 ${installPy}，日志 ${join(dataBase, 'install.log')}`,
				);
				runPython(
					[installPy, '--model-only'],
					join(dataBase, 'install.log'),
					'model-download',
					(code) => {
						ctx.logger?.info?.(`${name}: 模型下载退出码 ${code}`);
						initData(); // 模型就绪后再建 data
					},
				);
			} else {
				depsCheck();
				initData();
			}
			// 3c. opencode 双栖配置：幂等合并 opencode.json(.c) 的 instructions——
			// 指到插件同步出的 yishi-instructions.md，免用户手编 JSON。
			runPython(
				[installPy, '--opencode-only'],
				join(dataBase, 'install.log'),
				'opencode-config',
				(code) => ctx.logger?.info?.(`${name}: opencode 配置退出码 ${code}`),
			);
		}
	} catch (e) {
		ctx.logger?.warn?.(
			`${name}: 环境保障失败: ${String(e?.message ?? e)}`,
		);
	}

	// ── 1. 注入忆时记忆指令 ─────────────────────────────────────────────
	try {
		if (existsSync(instructionsPath)) {
			const text = readFileSync(instructionsPath, 'utf8');
			ctx.effect(
				() =>
					ctx.systemPrompt.section({
						name: 'yishi:instructions',
						order: 1,
						text: `# 忆时记忆系统指令（附加行为要求）\n\n${text}`,
					}),
				`${name}: instructions section`,
			);
		} else {
			ctx.logger?.info?.(`${name}: instructions missing at ${instructionsPath}`);
		}
	} catch (e) {
		ctx.logger?.warn?.(`${name}: 指令注入失败: ${String(e?.message ?? e)}`);
	}

	// ── 2. 保障忆时技能注册（provider） ─────────────────────────────────
	try {
		if (existsSync(skillPath)) {
			const dispose = ctx.skills.registerProvider(() => ({
				name: PROVIDER_NAME,
				list: async () => {
					const md = readFileSync(skillPath, 'utf8');
					const fm = parseFrontmatter(md);
					const skillName =
						fm?.name && isKebabName(fm.name) ? fm.name : SKILL_NAME;
					return [
						{
							name: skillName,
							description:
								fm?.description || '忆时记忆胶囊系统——模拟人类记忆检索',
							invocation: { modelInvocable: true, userInvocable: true },
							source: 'bundled',
							provider: PROVIDER_NAME,
							rank: PROVIDER_RANK,
							locator: skillPath,
							path: skillPath,
							resourceBase: { kind: 'directory', path: docsDir },
						},
					];
				},
				get: async (candidate) => {
					if (!existsSync(skillPath)) return undefined;
					const md = readFileSync(skillPath, 'utf8');
					return {
						...candidate,
						content: stripFrontmatter(md),
						path: skillPath,
						resourceBase: { kind: 'directory', path: docsDir },
					};
				},
			}));
			ctx.effect(() => dispose, `${name}: skills provider`);
		} else {
			ctx.logger?.info?.(`${name}: SKILL.md missing at ${skillPath}`);
		}
	} catch (e) {
		ctx.logger?.warn?.(`${name}: 技能注册失败: ${String(e?.message ?? e)}`);
	}

	ctx.logger?.info?.(
		`${name}: ready; dataBase=${dataBase}; docs=${existsSync(instructionsPath)}; skill=${existsSync(skillPath)}; disabled=${process.env.DSH_YISHI_DISABLE === '1'}`,
	);
}