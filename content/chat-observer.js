(() => {
  // Baseline existing turns: opening a conversation must not score its history.
  const known = new WeakSet();
  const userSelector = '[data-message-author-role="user"], [data-user-message-bubble="true"]';
  const composerSelector = '#prompt-textarea, textarea, [role="textbox"][aria-label="Ask ChatGPT"]';
  // Some layouts nest the bubble inside a role wrapper. Count the outer turn once.
  const userNodes = () => [...document.querySelectorAll(userSelector)].filter(node => !node.parentElement?.closest(userSelector));
  const baseline = () => userNodes().forEach(node => known.add(node));
  baseline();
  let armed = false, path = location.pathname, timer;
  document.addEventListener('submit', () => { armed = true; }, true);
  document.addEventListener('click', event => {
    if (event.target.closest('[data-testid="send-button"], button[aria-label="Send prompt"], button[aria-label="Send message"]')) armed = true;
  }, true);
  document.addEventListener('keydown', event => {
    if (event.key === 'Enter' && !event.shiftKey && !event.isComposing && event.target.closest(composerSelector)) armed = true;
  }, true);
  let pending = null;
  async function flush() {
    if (!pending) return;
    if (document.querySelector('[data-testid="stop-button"], button[aria-label="Stop streaming"]')) { timer = setTimeout(flush, 1500); return; }
    const item = pending; pending = null;
    const turns = [...document.querySelectorAll('[data-message-author-role]')];
    const output = turns.find(node => node.dataset.messageAuthorRole === 'assistant' &&
      (item.node.compareDocumentPosition(node) & Node.DOCUMENT_POSITION_FOLLOWING))?.innerText || '';
    try {
      const result = await chrome.runtime.sendMessage({type: 'INTERACTION', id: item.id, prompt: item.text, output});
      if (!result?.ok) console.warn('Cognitive Mirror: prompt could not be saved.', result?.error || 'No response');
      if (result.nudge) {
        const host = document.createElement('div'); const shadow = host.attachShadow({mode: 'closed'});
        const toast = document.createElement('div'); toast.textContent = 'Are we letting AI pick our path?';
        toast.style.cssText = 'position:fixed;bottom:100px;right:24px;z-index:2147483647;padding:15px 20px;border-radius:16px;background:#edf3e9;color:#253b34;box-shadow:0 4px 25px #0002;font:15px system-ui';
        shadow.append(toast); document.documentElement.append(host); setTimeout(() => host.remove(), 2000);
      }
    } catch { console.warn('Cognitive Mirror: communication failed. Refresh ChatGPT after reloading the extension.'); }
  }
  new MutationObserver(() => {
    if (path !== location.pathname) {
      path = location.pathname;
      if (!armed && !pending) baseline();
    }
    for (const node of userNodes()) {
      if (known.has(node)) continue;
      const text = node.innerText.trim(); if (!text) continue;
      known.add(node);
      if (!armed) continue;
      if (pending) { clearTimeout(timer); void flush(); }
      pending = {node, text, id: node.dataset.messageId || node.closest('[data-message-id]')?.dataset.messageId || crypto.randomUUID()};
      armed = false;
    }
    if (pending) { clearTimeout(timer); timer = setTimeout(flush, 1800); }
  }).observe(document.body, {childList: true, subtree: true, characterData: true});
})();
