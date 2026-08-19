const calls = { sections: [], providers: [] };
const ctx = {
  logger: { info: (m) => console.log('[yishi]', m) },
  systemPrompt: { section: (s) => calls.sections.push(s) },
  skills: { registerProvider: (f) => { calls.providers.push(f); return () => {}; } },
  effect: (fn, label) => { console.log('effect:', label); return fn(); },
};
const mod = await import('file:///home/fslong/Documents/yishi/lib/index.js');
mod.apply(ctx);
console.log('inject:', JSON.stringify(mod.inject));
console.log('sections:', calls.sections.map(s => `${s.name}@${s.order} bytes=${s.text.length}`));
const head = calls.sections[0]?.text.slice(0, 40).replace(/\n/g, ' ');
console.log('section head:', head);
const provider = calls.providers[0]();
const cands = await provider.list({});
console.log('candidates:', cands.map(c => `${c.name} | rank=${c.rank} | provider=${c.provider}`));
const def = await provider.get(cands[0], {});
console.log('def.content head:', def.content.slice(0, 40).replace(/\n/g, ' '));
console.log('SMOKE OK');
