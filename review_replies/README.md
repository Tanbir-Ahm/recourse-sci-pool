# review_replies: where the reviewers' reply files go

Real replies only. Put each reply as a plain text file in the folder for the pack it answers:

| Folder | What goes in it |
|---|---|
| `J_first_pack/` | J's replies to the first pack (`Q01_A_...txt` to `Q12_A_...txt`, and `Q03_B_...`, `Q09_B_...` and any other B files) |
| `S_top_up/` | S's replies to the top-up pack (`Q02_TA_...txt` and so on) and to any overlap files (`Q03_A_...`, `Q09_A_...`) |

## File names

`Q<question>_<A|B|TA>_<tool>-<initials>.txt`, for example `Q03_A_ChatGPT-J.txt` or `Q03_TA_Gemini-S.txt`.

- Use the same tool name every time (`ChatGPT`, `Gemini`), so a tool's replies group together.
- The initials keep J's and S's files apart if they use the same tool.
- Keep the reply text exactly as the tool gave it. Do not edit it.

## Not counted

The mock-trial replies (ChatGPT Q03 TA/TB, Gemini Q03 TA) are not real results and must not be put here.

## Reading them

The reader takes one folder, so both are copied into one before reading:

    python review_tools/ingest_llm_reviews.py --replies ALL_REPLIES_DIR --out RESULTS_DIR

Every figure it prints is LLM-judged. Nothing here is lawyer-validated.
