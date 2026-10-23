import {MODES} from './classifier.js';
const clamp = value => Math.max(0, Math.min(100, value));
export function initialState() {
  return {m: 50, d: 50, sluggish: 0, feed: [], cards: [], seen: [], day: '', dayStart: 50, warning: ''};
}
export function mood(state, now = Date.now()) {
  const rapid = state.feed.filter(item => now - item.time < 120000).length >= 5;
  return state.m < 35 ? 'Dazed Dreamer' : state.m < 60 || rapid ? 'Sluggish Spark' : 'Sharp Thinker';
}
function rollDay(state, now) {
  const day = new Date(now).toLocaleDateString('en-CA');
  if (state.day !== day) { state.day = day; state.dayStart = state.m; }
}
export function applyInteraction(state, interaction, result, now = Date.now()) {
  if (state.seen.includes(interaction.id)) return state;
  rollDay(state, now);
  const delta = MODES[result.mode];
  state.m = clamp(state.m + delta.m); state.d = clamp(state.d + delta.d);
  if (result.mode === 'passive') state.sluggish += 1;
  state.feed.unshift({id: interaction.id, prompt: interaction.prompt, mode: result.mode, time: now, engine: result.engine});
  state.feed = state.feed.slice(0, 60);
  state.seen = [...state.seen, interaction.id].slice(-500);
  state.warning = result.warning || '';
  if (['offload', 'passive'].includes(result.mode) && result.question && result.explanation && state.cards.length < 100) {
    state.cards.push({id: interaction.id, question: result.question, explanation: result.explanation, url: interaction.url, time: now});
  }
  return state;
}
export function reviewCard(state, id, knew, now = Date.now()) {
  const index = state.cards.findIndex(card => card.id === id);
  if (index < 0) return false;
  rollDay(state, now);
  const [card] = state.cards.splice(index, 1);
  state.m = clamp(state.m + (knew ? 8 : -2));
  if (!knew) state.cards.push(card);
  return true;
}
