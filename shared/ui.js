export async function request(message) {
  const result = await chrome.runtime.sendMessage(message);
  if (!result?.ok) throw new Error(result?.error || 'Extension unavailable. Reload and try again.');
  return result;
}
export function paintCreature(mood) {
  const el = document.getElementById('creature');
  el.className = 'creature' + (mood === 'Sharp Thinker' ? '' : ' sleepy') + (mood === 'Dazed Dreamer' ? ' dazed' : '');
}
export function renderReview(container, card, onReview) {
  container.replaceChildren();
  if (!card) { const p = document.createElement('p'); p.className = 'muted'; p.textContent = 'Nothing waiting. Take your next thought with you.'; container.append(p); return; }
  const question = document.createElement('p'); question.textContent = card.question;
  const answer = document.createElement('textarea'); answer.placeholder = 'In your own words…'; answer.setAttribute('aria-label', 'Your answer');
  const explanation = document.createElement('div'); explanation.className = 'explanation'; explanation.textContent = card.explanation; explanation.hidden = true;
  const show = document.createElement('button'); show.textContent = 'Show explanation';
  const buttons = document.createElement('div'); buttons.className = 'buttons';
  const ratings = document.createElement('div'); ratings.className = 'buttons'; ratings.hidden = true;
  show.onclick = () => { explanation.hidden = false; ratings.hidden = false; show.hidden = true; };
  for (const [label, knew] of [['I knew this', true], ['Fuzzy / forgot', false]]) {
    const button = document.createElement('button'); button.textContent = label; if (knew) button.className = 'primary';
    button.onclick = async () => {
      ratings.querySelectorAll('button').forEach(b => b.disabled = true);
      try { await onReview(card.id, knew); } catch (error) {
        document.getElementById('status').textContent = error.message;
        ratings.querySelectorAll('button').forEach(b => b.disabled = false);
      }
    }; ratings.append(button);
  }
  const source = document.createElement('small'); source.textContent = `From ChatGPT · ${new Date(card.time).toLocaleDateString()}`;
  buttons.append(show); container.append(source, question, answer, buttons, explanation, ratings);
}
