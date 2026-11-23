# Ecom Radar — PRODUCT.md

**What it is.** A self-hosted ad-intelligence radar for DTC e-commerce, built for one operator (Chry, media buyer + creative strategist). Give it a brand URL and it maps the whole advertiser: every Facebook/Instagram page the brand runs (main page + persona/alias pages), every ad ever archived (active and past), every landing page and funnel behind the ads, the store's tech stack, EU transparency KPIs (reach, age/gender/country), running time, iteration count, and a winner ranking with an honest estimated-spend model. It also searches the whole Meta Ad Library live by keyword, page or domain across countries.

**Unique mechanism.** Page-network reconstruction from landing-domain clustering + full archive pagination + EU DSA transparency data, fused into one ranked board ("the ads worth stealing this month") the operator filters by format, brand, market, age and signal.

**Audience & scene.** One expert user at a desk, mostly at night (Meta actions happen at midnight), dark room, MacBook + external monitor, dense information, long sessions, fast scanning of hundreds of thumbnails. Mode: **Operate**.

**Jobs.** (1) Add a brand → dossier in minutes. (2) Market report: what is winning right now. (3) Search anything: keyword, page, domain, hook text, transcript. (4) Open an ad → everything: media, copy, landing screenshot, KPIs, page, siblings. (5) Track changes: new ads, killed ads, new landing pages, new alias pages.

**Assumptions (inferred from the brief, unconfirmed).** Single user, local machine, Italian UI copy with English data labels; no login; localhost:8772; media cached lazily.

**Constraints.** Python 3.9 stdlib + Playwright + SQLite; no paid APIs; public Ad Library only; no logged-in Meta automation; respect rate limits.
