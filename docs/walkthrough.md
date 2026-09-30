# Ten-minute walkthrough

1. Start the built app using the README. Notice **Demo responses** is selected and persistently labeled.
2. Read the bundled trees document. Highlight the sentence about evapotranspiration. The selected text appears beside the question box; keyboard selection works too.
3. Click **How do trees cool cities?**. Explain that this answer is prepared, not generated. Click `[1]`, expand the evidence, and open the EPA source.
4. Paste your own Markdown. Ask a question in Demo. Point out the **not document-grounded** label; this avoids misleading users during a mock demonstration.
5. Upload a selectable-text PDF. Compare formatted text with **Original PDF**. Explain why original-view selection is out of scope and why OCR would be a separate feature.
6. With keys configured, choose **Live RAG**. Explain the privacy notice: the question and selection go to providers, not the full uploaded document. Ask a specific question.
7. Open citations and compare each claim with the evidence. A citation ID is structurally validated; its support for a claim still needs evaluation.
8. Expand Usage. Contrast monthly search credits, daily model tokens, minute-level limits, and last-response provider headers. Restarting resets app counts, not the provider's account limits.
9. With local Grafana or Cloud configured, find the returned trace ID. Explain search, extract, rank, and generate latency; correlate logs without seeing document text.
10. Discuss next steps: semantic ranking, claim-level citation evaluation, durable quotas, controlled public hosting. Keep these separate from the working current scope.

## Interview prompts

- Why is a search result snippet insufficient evidence? Explain the separate extraction step.
- How would a malicious URL reach private infrastructure? Describe DNS validation, pinning, redirects, host checks, and timeouts.
- What happens when Groq returns 429? A safe error reaches the user, the reservation is retained, and Demo is offered explicitly.
- What does an OpenTelemetry span add beyond a log? Parent-child timing and causal correlation across pipeline stages.
- Why no vector database? Five fresh results fit a bounded in-memory ranker; adding infrastructure should solve a measured retrieval problem.
- What does testing with mocks establish? Request/response contracts and failure behavior, not credentials, provider availability, or factual answer quality.
