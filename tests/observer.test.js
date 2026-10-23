import test from 'node:test';
import assert from 'node:assert/strict';
import vm from 'node:vm';
import {readFile} from 'node:fs/promises';

const source = await readFile(new URL('../content/chat-observer.js', import.meta.url), 'utf8');
function harness() {
  const listeners = {}, sent = [], timers = new Map();
  const nodes = []; let mutation; let timerId = 0;
  const bubble = (text, kind = 'bubble', parent = null) => ({
    innerText: text, dataset: {}, parentElement: {closest: () => parent},
    closest: () => null, kind, compareDocumentPosition: () => 4
  });
  nodes.push(bubble('Old conversation'));
  const document = {
    body: {}, addEventListener: (name, fn) => {listeners[name] = fn;},
    querySelector: () => null,
    querySelectorAll: selector => {
      if (selector === '[data-message-author-role]') return [];
      return nodes.filter(node => node.kind === 'role' ? selector.includes('[data-message-author-role="user"]') : selector.includes('[data-user-message-bubble="true"]'));
    }
  };
  vm.runInNewContext(source, {document, location: {pathname: '/c/example'},
    MutationObserver: class {constructor(fn) {mutation = fn;} observe() {}},
    setTimeout: fn => {timers.set(++timerId,fn); return timerId;}, clearTimeout: id => timers.delete(id),
    crypto: {randomUUID: () => `test-${nodes.length}`}, console, Node: {DOCUMENT_POSITION_FOLLOWING:4},
    chrome: {runtime: {sendMessage: async message => {sent.push(message); return {ok:true,nudge:false};}}}
  });
  return {nodes, bubble, sent, mutation: () => mutation(), listeners,
    flush: async () => {const work = [...timers.values()]; timers.clear(); for (const fn of work) await fn();},
    enter: (shiftKey = false) => listeners.keydown({key:'Enter',shiftKey,isComposing:false,target:{closest: selector => selector.includes('[role="textbox"][aria-label="Ask ChatGPT"]') ? {} : null}})
  };
}
test('new bubble markup and Ask ChatGPT composer capture only submitted prompts', async () => {
  const h = harness(); h.mutation(); await h.flush(); assert.equal(h.sent.length,0);
  h.enter(); h.nodes.push(h.bubble('New prompt')); h.mutation(); await h.flush();
  assert.equal(h.sent.length,1); assert.equal(h.sent[0].prompt,'New prompt');
  h.mutation(); await h.flush(); assert.equal(h.sent.length,1);
});
test('legacy role markup still works and nested bubbles are counted once', async () => {
  const h = harness(); h.enter();
  const role = h.bubble('Legacy prompt','role');
  h.nodes.push(role,h.bubble('Legacy prompt','bubble',role));
  h.mutation(); await h.flush(); assert.equal(h.sent.length,1);
});
test('Shift+Enter does not arm prompt capture', async () => {
  const h = harness(); h.enter(true); h.nodes.push(h.bubble('Not submitted'));
  h.mutation(); await h.flush(); assert.equal(h.sent.length,0);
});
