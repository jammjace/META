import {request, paintCreature, renderReview} from '../shared/ui.js';
const status = document.getElementById('status');
async function init() {
  const {state, mood} = await request({type: 'GET_STATE'}); paintCreature(mood);
  renderReview(document.getElementById('review'), state.cards[0], async (id, knew) => {
    const {applied} = await request({type: 'REVIEW', id, knew});
    document.getElementById('review').hidden = true;
    status.textContent = !applied ? 'This card was already reviewed. You’re ready to continue.' : knew ? 'A thought made your own. +8 metacognition. You’re ready to continue.' : 'No rush. This card is back in the queue. −2 metacognition.';
    if (applied && knew) document.getElementById('creature').classList.add('trick');
  });
}
init().catch(error => { status.textContent = error.message; });
