# Cognitive Mirror

A small Chrome Manifest V3 extension for **ChatGPT only**. No build step, dependencies, account, or backend.

## Install

1. Open `chrome://extensions` in Chrome desktop (116 or later).
2. Enable **Developer mode**, choose **Load unpacked**, and select this folder (`META`).
3. Refresh any already-open ChatGPT tabs. Pin Cognitive Mirror and click its icon to open the side panel.
4. Send a new prompt at `https://chatgpt.com`. Opening an existing chat does not score its history.
5. Open a new tab to review one pending concept question. The address bar remains available at all times. Chrome may ask you to keep the new-tab change; accept it to use reviews there.

## API providers (optional)

In the side panel, expand **API & preferences**, choose **OpenAI** or **Google Gemini**, paste your own key, and save. OpenAI uses `gpt-4.1-mini` via the Responses API; Gemini uses `gemini-2.5-flash` via Google's GenerateContent API. Get a Gemini Developer API key from [Google AI Studio](https://aistudio.google.com/apikey). Vertex AI credentials are not supported.

The extension sends up to 12,000 characters of each new prompt and captured reply to the selected provider only. Provider data policies, charges, and quotas apply. OpenAI requests use `store: false`; Gemini has no equivalent flag in this request. Keys are saved separately for each provider; existing OpenAI keys continue to work after upgrading. Switching providers requires saving preferences. Removing the selected provider's key returns that provider to local mode without deleting the other key. Requests time out after 20 seconds; API errors use local rules and show a provider-specific warning.

After updating this extension, click **Reload** at `chrome://extensions`, accept the additional Google API host permission if Chrome prompts, then refresh ChatGPT. Select **Google Gemini**, paste your key, and save. This enables Gemini as the classifier; ChatGPT remains the only monitored website.

Keys are stored unencrypted in `chrome.storage.local`, accessible only to trusted extension contexts, never to ChatGPT content scripts. This is a personal unpacked extension using your own key; it does not embed a shared developer key. Do not distribute your browser profile or a key. No analytics or other remote services are used.

Official implementation references: [Structured Outputs](https://developers.openai.com/api/docs/guides/structured-outputs), [GPT-4.1 mini](https://developers.openai.com/api/docs/models/gpt-4.1-mini), [Chrome storage](https://developer.chrome.com/docs/extensions/reference/api/storage), [Gemini GenerateContent](https://ai.google.dev/api/generate-content), [Gemini structured output](https://ai.google.dev/gemini-api/docs/generate-content/structured-output).

## Scope and behavior

- Companion moods, dynamic toolbar face, metacognition and digestion bars, daily score change, recent prompt feed, optional two-second nudge, concept queue, and self-rated reviews.
- Both scores start at 50 and stay between 0 and 100. Offload: −8 M / −5 D; passive: −5 M and one sluggish tick; active: +10 M / +5 D; synthesis: +5 M / +2 D. Reviews: knew +8 M, fuzzy −2 M and card returns to queue. Self-rating is intentional; answers are not graded or stored.
- Sharp Thinker requires M ≥ 60 and fewer than five recent prompts in two minutes. M < 35 gives Dazed Dreamer; otherwise Sluggish Spark. Sluggish ticks are a cumulative indicator; the spec does not define a countdown duration.
- Local rules are approximate. They recognize synthesis/learning wording and rapid repeated generation, defaulting other prompts to offload. Local concept cards cover async/await, useEffect, useState, and confirmation bias. Either API provider can cover other concepts.
- Reviews appear in the side panel and once per new-tab page. A typed answer stays on screen until the explanation is revealed and the user self-rates. No automatic navigation or blocking redirect.
- Keeps the latest 60 prompts, 100 pending cards, and 500 deduplication IDs locally to bound storage. Reply text is used transiently for classification, not retained. Source URL and creation time accompany stored cards.
- No streaks, cosmetics, Claude/Gemini website capture, telemetry, or server.

## Check

Run `npm test` with Node 22+ for scoring, queue, classification, API fallback, manifest, and worker message/security checks. JavaScript syntax can be checked with `node --check <file>`.

For a real Chrome smoke test: submit a new offloading prompt, confirm a single feed entry and score drop; submit an active-learning prompt and confirm the increase; generate a concept card (e.g. “Write code using async await for me”), open a new tab, reveal the explanation, and self-rate; confirm a fuzzy answer requeues and a known answer removes it. Check an existing conversation does not add history. Test each provider with a valid key, then a bad key to confirm its local fallback warning. Confirm switching providers keeps keys separate, and remove the selected key to return to local mode. Close/reopen Chrome to check persistence.

ChatGPT's DOM can change. Capture uses submitted user message nodes and a MutationObserver; it does not intercept network traffic, read drafts, or scrape conversation history. Waits for streaming to settle, so scores may appear after a reply completes. Reloading during a pending reply can lose that interaction. File uploads, voice, edited prompts, and regenerated answers are outside this first version's capture support. Live ChatGPT capture and a paid API request require manual verification in your signed-in Chrome profile.

Disable or remove the extension at `chrome://extensions` to restore your previous new-tab page. Removing it also clears its local data.
