# Pangea Chat: Gen AI Intern Task Submission

This is a language feedback API for language learners. It analyzes user-written sentences and returns structured correction feedback. Built with FastAPI and Claude Haiku, it identifies grammatical errors, provides learner-friendly explanations in the user's native language, and assigns a CEFR difficulty rating to each sentence.

## How to run

### Local Development
1. Clone the repo
```bash
git clone https://github.com/chohbein/pangea-intern-task-2026.git
cd pangea-intern-task-2026
```
2. Create a virtual environment and activate it
```bash
python -m venv .venv
source .venv/bin/activate
```
3. Install dependencies in requirements.txt
```bash
pip install -r requirements.txt
```
4. Add your Anthropic API key to .env
```bash
cp .env.example .env
```
5. Start the server
```bash
uvicorn app.main:app --reload
```
6. Run tests
```bash
pytest -v
```


## Design Decisions
We used Anthropic's Claude Haiku for this API. Haiku is a light-weight model that prioritizes speed and cost-efficiency, making it well suited for production scale where users' requests need to be processed quickly and frequently without sacrificing accuracy on these straight-forward grammar corrections.

We used Anthropic's tool feature to guarantee structured JSON outputs instead of parsing raw text responses. This ensures every response conforms to the schema, including enforcing valid datatypes for `error_type` and `difficulty`, eliminating the risk of malformed responses.

Instead of manually rewriting the response schema as a tool definition, we load it directly from `schema/response.schema.json`, which is the same file used to validate responses. This ensures the tool definition stays in sync with the schema automatically.

We implemented basic in-memory caching keyed on the sentence, target language, and native language. This avoids redundant API calls, reducing latency and costs at scale. The current implementation resets on server restart and would not extend to multiple instances; a production deployment would require Redis or any dedicated caching solution.

The API intentionally does not enforce that the input sentence matches the specified `target_language`. In practice, Claude infers the language from the sentence itself, so if a user forgets to update the target language field, the API still returns valuable feedback rather than failing. This is a trade-off favoring flexibility to accommodate the user over strict input validation.



## Prompt Strategy
Testing the baseline prompt, it already performed well across various cases. Overall, the prompt is concise and lightweight. Two specific tests showed some shortfalls of it, however.

1. A fundamental problem with this API is with high-density erroneous sentences; as error density increases, intended meaning of the sentence becomes ambiguous. While this shouldn't be common in practice, very novice language learners may have this problem (See limitations for more on this). To combat this as best as possible, we added rule 7: "When the sentence has many errors and the intended meaning is unclear, make reasonable assumptions about what the learner meant and state your assumption in the explanation."

2. In sentences with a large number of errors, the model would tend to flag the entire sentence as erroneous under `original` and `correction`. To combat this, we added rule 8: "Each error should identify the most specific span of text that contains the issue. Avoid flagging the entire sentence as an error unless the problem truly affects the whole sentence."


## Testing Approach
We designed 5 custom test cases to address potential pitfalls of the model and ensure accurate performance for every feature.

1. Multiple error detection. In a sentence with 4+ errors, will the model correctly address each one individually?
2. Does a highly difficult sentence correctly get a high CEFR rating, despite its short length and correct grammar structure?
3. Does a low difficulty sentence correctly get a low CEFR rating, despite its long length?
4. Can the model correctly classify specific errors, in this case `missing_word` error, in a non-Latin language?
5. Does the model identify the most specific text span for each error, rather than flagging the entire sentence?


## Limitations
1. Our caching approach is limited and intended for local development only. Scaling to production would require using a service like Redis for multi-instance and persistent caching.
2. As stated earlier, there is an inherent issue with this service that may come up with novice language-learners; as error density in a sentence increases, the apparent meaning the user intended behind that sentence becomes more vague. We tried to combat this as best as possible in the prompt, however it is just an inherent issue to keep in mind.
3. `target_language` is not enforced. Claude infers the language strictly through the inputted sentence. This may fail with highly-erroneous sentences in languages that share similarities with another, (e.g. Spanish & Portuguese). As stated earlier, we elected to leave this because of the tradeoff between that and the more likely case of a user incorrectly setting `target_language`. The API returns useful feedback in either case.
