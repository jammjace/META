import {request, paintCreature, renderReview} from '../shared/ui.js';
import {MODES} from '../background/classifier.js';
const $ = id => document.getElementById(id);
let currentCard;
let savedKeys = {openai: false, gemini: false};
function updateProviderLabel() {
  const provider = $('provider').value;
  $('key-label').textContent = provider === 'gemini' ? 'Gemini API key' : 'OpenAI API key';
  $('key-state').textContent = savedKeys[provider] ? '· saved' : '· local mode';
}
$('provider').onchange = () => { $('api-key').value = ''; updateProviderLabel(); };
async function refresh(force = false) {
  const {state, mood, provider, keyStates, nudges} = await request({type: 'GET_STATE'});
  $('mood').textContent = mood; paintCreature(mood);
  $('score').textContent = `${state.m} / 100`; $('meter').value = state.m;
  const delta = state.day === new Date().toLocaleDateString('en-CA') ? state.m - state.dayStart : 0;
  $('trend').textContent = `Today’s change: ${delta > 0 ? '+' : ''}${delta}`;
  $('digestion').textContent = `${state.d} / 100`;
  $('sluggish').textContent = state.sluggish ? `Sluggish ticks: ${state.sluggish}` : '';
  $('count').textContent = `${state.cards.length} pending`;
  $('warning').textContent = state.warning;
  savedKeys = keyStates;
  if (!document.activeElement?.closest('#settings')) $('provider').value = provider;
  updateProviderLabel();
  if (document.activeElement?.closest('#settings') === null) $('nudges').checked = nudges;
  const card = state.cards[0];
  if (force || currentCard !== card?.id) {
    currentCard = card?.id;
    renderReview($('review'), card, async (id, knew) => {
      const {applied} = await request({type: 'REVIEW', id, knew});
      await refresh(true);
      if (applied && knew) $('creature').classList.add('trick');
      $('status').textContent = applied ? (knew ? 'A thought made your own. +8 metacognition.' : 'Another chance is waiting in the queue. −2 metacognition.') : 'This card was already reviewed in another tab.';
    });
  }
  $('empty').hidden = state.feed.length > 0;
  $('feed').replaceChildren(...state.feed.map(item => {
    const li = document.createElement('li'); const badge = document.createElement('span'); const p = document.createElement('p'); const time = document.createElement('small');
    badge.className = `pill ${item.mode}`; badge.textContent = MODES[item.mode].label;
    p.textContent = item.prompt.slice(0, 240); time.textContent = `${new Date(item.time).toLocaleTimeString([], {hour: 'numeric', minute: '2-digit'})} · ${item.engine}`;
    li.append(badge, p, time); return li;
  }));
}
$('settings').onsubmit = async event => {
  event.preventDefault();
  try { await request({type: 'SET_SETTINGS', provider: $('provider').value, apiKey: $('api-key').value, nudges: $('nudges').checked}); $('api-key').value = ''; $('status').textContent = 'Preferences saved.'; await refresh(); }
  catch (error) { $('status').textContent = error.message; }
};
$('remove-key').onclick = async () => {
  try { await request({type: 'SET_SETTINGS', provider: $('provider').value, removeKey: true, nudges: $('nudges').checked}); $('api-key').value = ''; $('status').textContent = 'Key removed. Local rules are active.'; await refresh(); }
  catch (error) { $('status').textContent = error.message; }
};
chrome.storage.onChanged.addListener((changes, area) => { if (area === 'local') refresh().catch(error => $('status').textContent = error.message); });
refresh(true).catch(error => $('status').textContent = error.message);
