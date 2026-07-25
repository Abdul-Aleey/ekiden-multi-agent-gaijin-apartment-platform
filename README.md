# Ekiden 駅伝

Ekiden is an AI agent relay that helps foreign residents rent apartments in Japan. It searches live listings nationwide, reveals the true cost beyond the advertised rent, checks for bait listing risk, reads applicant eligibility straight from what each listing actually says, and drafts a negotiation strategy along with the first contact email.

Tagline: Know before you sign.

Built for the Agent Forge AI Hackathon Tokyo, under the theme of an AI agent or swarm of agents solving a real world problem through the lens of Tokyo and Japanese creativity.

## The problem

Renting an apartment in Japan as a foreigner involves four compounding problems.

1. Foreigners often do not know where to even start looking. Listing sites return thousands of results with no sense of which ones would actually accept them, or what they truly cost.
2. The advertised rent hides most of the real cost. Security deposit, key money, agency fee, guarantor company fees, fire insurance, and key exchange fees typically add several months of rent up front, and listing sites sort by the one number that hides all of this.
3. Applicants often do not know if they will be refused. Many landlords have conditions around nationality, guarantors, or Japanese ability, stated only in Japanese free text. Applicants frequently find out only after viewing, applying, and waiting.
4. Applicants cannot write the inquiry. First contact with a Japanese agency is expected in formal business Japanese, which most foreign applicants cannot produce.

## How it works

Full flowcharts of the whole pipeline are in [ARCHITECTURE.md](ARCHITECTURE.md).

Ekiden works as a relay of specialist agents, in keeping with its name, the Japanese word for a long distance relay race. A user states what they want in chat. A preference agent extracts structured search criteria. An area resolution agent maps free text to a real Japanese prefecture or ward. A search agent fetches live listings from two independent sites concurrently, deduplicates them, and ranks the best matches, guaranteeing a full shortlist whenever the market has enough candidates.

For each shortlisted listing, four agents run at once. A cost auditor computes the true cost from only what the listing actually states. A trust checker flags bait listing signals using an independent model vendor. An eligibility agent checks the applicant's profile against the listing's own stated conditions, with every finding grounded in a verbatim quote from the listing. A strategy advisor produces a negotiation and screening plan using the other three agents' findings.

On request, a follow up agent answers questions about a specific listing, and an inquiry email agent drafts a formal Japanese email together with an English translation alongside it.

## Sponsor tools and models

Qwen Cloud, running qwen3.5 flash, powers the high volume tasks: preference extraction, area resolution, search ranking, fee extraction, translation, and follow up questions. These are called many times per search, so speed matters more than deep reasoning.

ai& provides two model tiers on one account. The fast tier backs up trust checking. The quality tier handles eligibility analysis, the inquiry email, and the strategy advisor, since these benefit from careful multi step reasoning.

GMI Cloud is the primary provider for the trust check and the strategy advisor, deliberately a different vendor from Qwen and ai& so the trust check functions as a genuine independent opinion rather than the same model checking its own ranking decisions.

Daytona executes the true cost arithmetic inside a real, isolated cloud sandbox rather than trusting inline code.

Vertex AI, running Gemini 3.5 flash, is a universal fallback. Every single agent call in the system automatically retries against Vertex AI if its primary provider is unavailable, using Google Cloud's own service account authentication, with no API key to manage.

Every provider call follows the same pattern. Try the best fit model for the task, fall back to a secondary real model, fall back to Vertex AI, and only as a last resort fall back to deterministic logic such as regex extraction, rule based heuristics, or a fixed template. The product never crashes or blanks out because one provider is down.

A more detailed table of every model, the exact tasks it powers, and the reasoning behind each tier choice is in [PRESENTATION_BRIEF.md](PRESENTATION_BRIEF.md).

## Honesty by design

Ekiden never fabricates a cost it cannot verify. Any fee not explicitly stated by a listing is excluded from every total and disclosed separately as not stated, rather than filled in with an average guess.

Every eligibility finding must quote the exact source text from the listing, or it is dropped before being shown to the user.

The true cost breakdown is split into three parts that are mathematically guaranteed to add up correctly. An upfront cost breakdown covers everything paid once at move in. An effective monthly breakdown covers rent, management fee, and the move in costs spread evenly across a standard lease term. A separate section covers renewal costs that occur after moving in, such as the guarantor company's annual renewal and the lease renewal fee, which are never hidden inside a blended monthly number.

## Ethical framing

The eligibility feature is applicant side only. It does not predict landlord prejudice. It extracts requirements a listing already publishes and checks them against the applicant's own stated situation, always pairing any concern with a path forward, such as an alternative guarantor company that accepts foreign nationals. There is no landlord facing version of this feature.

## Deployment

Ekiden runs as a single Google Cloud Run service. The Next.js frontend is built as a static export and served directly by the same FastAPI process that runs the API, so there is one container, one URL, and no cross origin complexity between frontend and backend.

## Local development

The backend requires Python 3.11. From the backend folder, create a virtual environment, install the packages in requirements.txt, copy .env.example to .env and fill in real values, then run uvicorn main:app with reload enabled.

The frontend requires Node 20. From the frontend folder, copy .env.local.example to .env.local, run npm install, then npm run dev.

## Project structure

The backend folder contains the FastAPI application, one file per agent under agents, the prompts each agent uses, the provider abstraction that every model call goes through, and the services that talk to live listing sites, the fallback data corpus, and Daytona.

The frontend folder contains the Next.js App Router application, including the chat interface, the shortlist cards, and the listing detail panel.

## License

MIT. See [LICENSE](LICENSE).
