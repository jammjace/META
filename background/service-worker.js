import {classify} from './classifier.js';
import {initialState, applyInteraction, reviewCard, mood} from './state-manager.js';

const ready = chrome.storage.local.setAccessLevel({accessLevel: 'TRUSTED_CONTEXTS'});
let queue = Promise.resolve();
chrome.sidePanel.setPanelBehavior({openPanelOnActionClick: true});
async function read() { await ready; return (await chrome.storage.local.get('state')).state || initialState(); }
async function save(state) {
  await chrome.storage.local.set({state});
  const sharp = mood(state) === 'Sharp Thinker';
  const canvas = new OffscreenCanvas(32, 32); const ctx = canvas.getContext('2d');
  ctx.fillStyle = sharp ? '#79bba2' : '#c6b6df'; ctx.beginPath(); ctx.arc(16, 16, 14, 0, Math.PI * 2); ctx.fill();
  ctx.fillStyle = '#253b34';
  for (const x of [10, 21]) ctx.fillRect(x, 12, 3, sharp ? 5 : 2);
  ctx.fillRect(13, 22, 7, 2);
  await chrome.action.setIcon({imageData: ctx.getImageData(0, 0, 32, 32)});
  await chrome.action.setBadgeText({text: state.cards.length ? String(state.cards.length) : ''});
  await chrome.action.setBadgeBackgroundColor({color: '#405e51'});
}
chrome.runtime.onInstalled.addListener(() => { queue = queue.then(async () => save(await read())); });
chrome.runtime.onStartup.addListener(() => { queue = queue.then(async () => save(await read())); });

chrome.runtime.onMessage.addListener((message, sender, respond) => {
  const fromChat = sender.tab && sender.url?.startsWith('https://chatgpt.com/');
  const trusted = !sender.tab && sender.url?.startsWith(chrome.runtime.getURL('')) || sender.url?.startsWith(chrome.runtime.getURL('newtab/'));
  const job = async () => {
    if (message.type === 'INTERACTION' && fromChat) {
      if (typeof message.id !== 'string' || message.id.length > 300 || typeof message.prompt !== 'string' || !message.prompt.trim()) throw new Error('Invalid interaction');
      const state = await read();
      if (state.seen.includes(message.id)) return {};
      const interaction = {id: message.id, prompt: message.prompt.slice(0, 12000), url: sender.url.split('?')[0]};
      const {apiKey = '', geminiApiKey = '', provider = 'openai', nudges = true} = await chrome.storage.local.get(['apiKey', 'geminiApiKey', 'provider', 'nudges']);
      const result = await classify(interaction.prompt, String(message.output || '').slice(0, 12000), state.feed.filter(item => Date.now() - item.time < 120000).length, provider === 'gemini' ? geminiApiKey : apiKey, provider);
      await save(applyInteraction(state, interaction, result));
      return {nudge: nudges && result.mode === 'offload'};
    }
    if (!trusted) throw new Error('Unsupported sender');
    if (message.type === 'GET_STATE') {
      const state = await read(); const settings = await chrome.storage.local.get(['apiKey', 'geminiApiKey', 'provider', 'nudges']);
      const provider = settings.provider || 'openai';
      const keyStates = {openai: Boolean(settings.apiKey), gemini: Boolean(settings.geminiApiKey)};
      return {state, mood: mood(state), provider, keyStates, hasKey: keyStates[provider], nudges: settings.nudges !== false};
    }
    if (message.type === 'SET_SETTINGS') {
      const provider = message.provider || (await chrome.storage.local.get('provider')).provider || 'openai';
      if (!['openai', 'gemini'].includes(provider)) throw new Error('Invalid provider');
      const settings = {nudges: Boolean(message.nudges), provider};
      const keyField = provider === 'gemini' ? 'geminiApiKey' : 'apiKey';
      if (typeof message.apiKey === 'string' && message.apiKey.trim()) settings[keyField] = message.apiKey.trim();
      if (message.removeKey) settings[keyField] = '';
      await chrome.storage.local.set(settings); return {};
    }
    if (message.type === 'REVIEW' && typeof message.knew === 'boolean') {
      const state = await read(); const applied = reviewCard(state, message.id, message.knew);
      await save(state); return {applied};
    }
    throw new Error('Unknown request');
  };
  const pending = queue.then(job); queue = pending.catch(() => {});
  pending.then(result => respond({ok: true, ...result}), () => respond({ok: false, error: 'Could not complete this action. Please try again.'}));
  return true;
});
