import test from 'node:test';
import assert from 'node:assert/strict';

test('worker restricts settings to extension pages and serializes duplicate submissions', async () => {
  const previousChrome = globalThis.chrome, previousCanvas = globalThis.OffscreenCanvas;
  const stored = {}; let listener, accessLevel;
  const noop = () => Promise.resolve();
  globalThis.chrome = {
    storage: {local: {
      setAccessLevel: async value => {accessLevel = value.accessLevel;},
      get: async keys => Object.fromEntries((Array.isArray(keys) ? keys : [keys]).filter(key=>Object.hasOwn(stored,key)).map(key=>[key,structuredClone(stored[key])])),
      set: async value => Object.assign(stored, structuredClone(value))
    }},
    sidePanel: {setPanelBehavior: noop},
    action: {setIcon: noop, setBadgeText: noop, setBadgeBackgroundColor: noop},
    runtime: {getURL: path => `chrome-extension://test/${path}`, onInstalled:{addListener(){}}, onStartup:{addListener(){}}, onMessage:{addListener(fn){listener=fn;}}}
  };
  globalThis.OffscreenCanvas = class {getContext(){return {beginPath(){},arc(){},fill(){},fillRect(){},getImageData(){return {};}};}};
  try {
    await import('../background/service-worker.js');
    const send = (message,sender) => new Promise(resolve=>listener(message,sender,resolve));
    const chat = {url:'https://chatgpt.com/c/test',tab:{id:1}};
    const panel = {url:'chrome-extension://test/sidepanel/index.html'};
    assert.equal(accessLevel,'TRUSTED_CONTEXTS');
    const denied = await send({type:'SET_SETTINGS',apiKey:'secret'},chat);
    assert.equal(denied.ok,false); assert.equal(stored.apiKey,undefined);
    await send({type:'SET_SETTINGS',apiKey:'secret',nudges:false},panel);
    const publicState = await send({type:'GET_STATE'},panel);
    assert.equal(publicState.hasKey,true); assert.equal(JSON.stringify(publicState).includes('secret'),false);
    assert.equal((await send({type:'GET_STATE'},chat)).ok,false);
    await send({type:'SET_SETTINGS',removeKey:true,nudges:true},panel);
    const interaction = {type:'INTERACTION',id:'same',prompt:'Write code using async await',output:''};
    const results = await Promise.all([send(interaction,chat),send(interaction,chat)]);
    assert.ok(results.every(r=>r.ok));
    const {state} = await send({type:'GET_STATE'},panel);
    assert.equal(state.m,42); assert.equal(state.feed.length,1); assert.equal(state.cards.length,1);
    const newtab = {url:'chrome-extension://test/newtab/flashcard.html',tab:{id:2}};
    assert.equal((await send({type:'REVIEW',id:'same',knew:true},newtab)).applied,true);
    assert.equal((await send({type:'REVIEW',id:'same',knew:true},newtab)).applied,false);
    assert.equal(stored.state.m,50);
    assert.equal((await send(interaction,{url:'https://unrelated.example',tab:{id:3}})).ok,false);
    await send({type:'SET_SETTINGS',provider:'openai',apiKey:'openai-secret',nudges:true},panel);
    await send({type:'SET_SETTINGS',provider:'gemini',apiKey:'gemini-secret',nudges:true},panel);
    assert.equal(stored.apiKey,'openai-secret'); assert.equal(stored.geminiApiKey,'gemini-secret');
    const geminiState = await send({type:'GET_STATE'},panel);
    assert.equal(geminiState.provider,'gemini'); assert.equal(geminiState.hasKey,true);
    assert.deepEqual(geminiState.keyStates,{openai:true,gemini:true});
    assert.equal(JSON.stringify(geminiState).includes('gemini-secret'),false);
    assert.equal((await send({type:'SET_SETTINGS',provider:'unknown'},panel)).ok,false);
    await send({type:'SET_SETTINGS',provider:'gemini',removeKey:true,nudges:true},panel);
    assert.equal(stored.geminiApiKey,''); assert.equal(stored.apiKey,'openai-secret');
  } finally {globalThis.chrome=previousChrome; globalThis.OffscreenCanvas=previousCanvas;}
});
