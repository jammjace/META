import test from 'node:test';
import assert from 'node:assert/strict';
import {readFile} from 'node:fs/promises';
import {initialState, applyInteraction, reviewCard, mood} from '../background/state-manager.js';
import {localClassify, classify, validateResult} from '../background/classifier.js';

test('four modes apply exact score deltas, bounded and deduplicated', () => {
  for (const [mode, m, d] of [['offload',42,45],['passive',45,50],['active',60,55],['synthesis',55,52]]) {
    const state = initialState(); const interaction = {id: mode, prompt: 'example', url: 'https://chatgpt.com/'};
    applyInteraction(state, interaction, {mode, engine:'local'}, 1000);
    assert.equal(state.m, m); assert.equal(state.d, d);
    applyInteraction(state, interaction, {mode}, 1001); assert.equal(state.m, m);
  }
  const state = initialState(); state.m = 99; state.d = 99;
  applyInteraction(state, {id:'1'}, {mode:'active'}, 1000); assert.equal(state.m,100); assert.equal(state.d,100);
  state.m = 1; state.d = 1; applyInteraction(state, {id:'2'}, {mode:'offload'}, 1001); assert.equal(state.m,0); assert.equal(state.d,0);
});
test('reviews remove known cards, requeue fuzzy cards and reject stale IDs', () => {
  const state = initialState(); state.cards = [{id:'a'}, {id:'b'}];
  assert.equal(reviewCard(state, 'a', false), true); assert.equal(state.m,48);
  assert.deepEqual(state.cards.map(c=>c.id), ['b','a']);
  reviewCard(state, 'a', true); assert.equal(state.m,56);
  assert.equal(reviewCard(state, 'a', true), false); assert.equal(state.m,56);
});
test('only offload/passive create complete cards and queue stays bounded', () => {
  const state = initialState();
  applyInteraction(state,{id:'a'},{mode:'active',question:'Why?',explanation:'Because.'}); assert.equal(state.cards.length,0);
  applyInteraction(state,{id:'b'},{mode:'offload',question:'Why?',explanation:'Because.'}); assert.equal(state.cards.length,1);
  for(let i=0;i<120;i++) applyInteraction(state,{id:String(i)},{mode:'passive',question:'Why?',explanation:'Because.'});
  assert.equal(state.cards.length,100); assert.equal(state.feed.length,60);
});
test('local heuristics distinguish learning, synthesis, velocity, concept capture', () => {
  assert.equal(localClassify('Here is my logic, critique it',0).mode,'active');
  assert.equal(localClassify('Give pros and cons, I will decide',0).mode,'synthesis');
  assert.equal(localClassify('Fix this error',4).mode,'passive');
  assert.equal(localClassify('Write this email',0).mode,'offload');
  assert.ok(localClassify('Write code using async await',0).question);
  assert.equal(localClassify('Explain async await',0).question,'');
  assert.throws(()=>validateResult({mode:'invalid',question:'',explanation:''}));
  assert.throws(()=>validateResult({mode:'toString',question:'',explanation:''}));
});
test('moods react to score and recent velocity', () => {
  const state = initialState(); state.m = 70; assert.equal(mood(state,1000),'Sharp Thinker');
  state.feed = Array.from({length:5},()=>({time:900})); assert.equal(mood(state,1000),'Sluggish Spark');
  state.m = 20; assert.equal(mood(state,1000),'Dazed Dreamer');
});
test('API failure safely falls back; valid structured output is parsed', async () => {
  const original = globalThis.fetch;
  try {
    globalThis.fetch = async () => ({ok:false,status:401});
    const fallback = await classify('Write an email','',0,'fake'); assert.equal(fallback.engine,'local fallback'); assert.ok(fallback.warning);
    globalThis.fetch = async (_url, options) => {
      const body = JSON.parse(options.body); assert.equal(body.store,false); assert.equal(body.text.format.strict,true);
      return {ok:true,json:async()=>({output:[{content:[{type:'output_text',text:JSON.stringify({mode:'synthesis',question:'',explanation:''})}]}]})};
    };
    const result = await classify('options','reply',0,'fake'); assert.equal(result.mode,'synthesis'); assert.equal(result.engine,'OpenAI');
  } finally {globalThis.fetch = original;}
});
test('manifest limits capture to ChatGPT and all entry files exist', async () => {
  const manifest = JSON.parse(await readFile(new URL('../manifest.json',import.meta.url)));
  assert.equal(manifest.manifest_version,3); assert.deepEqual(manifest.content_scripts[0].matches,['https://chatgpt.com/*']);
  for (const file of [manifest.background.service_worker,manifest.side_panel.default_path,manifest.chrome_url_overrides.newtab,...manifest.content_scripts[0].js]) await readFile(new URL(`../${file}`,import.meta.url));
});

test('Gemini uses header authentication and structured output; errors fall back locally', async () => {
  const original = globalThis.fetch;
  try {
    globalThis.fetch = async (url, options) => {
      assert.match(url, /generativelanguage\.googleapis\.com.*gemini-2\.5-flash:generateContent$/);
      assert.equal(url.includes('secret'), false);
      assert.equal(options.headers['x-goog-api-key'], 'secret');
      assert.equal(options.headers.Authorization, undefined);
      const body = JSON.parse(options.body);
      assert.equal(body.generationConfig.responseMimeType, 'application/json');
      assert.equal(body.generationConfig.thinkingConfig.thinkingBudget, 0);
      assert.equal(JSON.parse(body.contents[0].parts[0].text).output, 'reply');
      return {ok: true, json: async () => ({candidates: [{finishReason: 'STOP', content: {parts: [{text: JSON.stringify({mode:'offload',question:'Why?',explanation:'Because.'})}]}}]})};
    };
    const result = await classify('Write code', 'reply', 0, 'secret', 'gemini');
    assert.equal(result.engine, 'Gemini'); assert.equal(result.question, 'Why?');
    for (const response of [
      {ok:false,status:429},
      {ok:true,json:async()=>({candidates:[]})},
      {ok:true,json:async()=>({candidates:[{finishReason:'MAX_TOKENS'}]})},
      {ok:true,json:async()=>({candidates:[{finishReason:'STOP',content:{parts:[{text:'invalid json'}]}}]})}
    ]) {
      globalThis.fetch = async () => response;
      const fallback = await classify('Write code using await', '', 0, 'secret', 'gemini');
      assert.equal(fallback.engine, 'local fallback'); assert.match(fallback.warning, /Gemini/);
      assert.ok(fallback.question);
    }
    globalThis.fetch = async () => { throw new Error('Must not call API without a key'); };
    assert.equal((await classify('Write code', '', 0, '', 'gemini')).engine, 'local');
  } finally {globalThis.fetch = original;}
});
