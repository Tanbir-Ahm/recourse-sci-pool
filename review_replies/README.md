# review_replies: where the reviewers' reply files go

Real replies only. Put each reply as a plain text file in the folder for the pack it answers:

| Folder | What goes in it |
|---|---|
| `J_first_pack/` | J's replies to the first pack (`Q01_A_...txt` to `Q12_A_...txt`, and `Q03_B_...`, `Q09_B_...` and any other B files) |
| `S_top_up/` | S's replies to the top-up pack (`Q02_TA_...txt` and so on) and to any overlap files (`Q03_A_...`, `Q09_A_...`) |

## What is in the folders (2026-10-07)

| Folder | Who and which tool | What |
|---|---|---|
| `J_first_pack/` | J, ChatGPT | Q01 to Q06, both orders (A and B), as Rich Text (`A01_A.rtf` ...). Convert with `--tool ChatGPT-J`. |
| `J_second_pack_gemini/` | J, **Gemini** | Q07, Q08, Q10, Q11, Q12, both orders, as Rich Text (`A07_A.rtf` ...). Convert with `--tool Gemini-J`, a separate run from the folder above, because the names are the same. **Q09 (A and B) is missing.** `A08_A.rtf` came with the code box's heading "JSON" in front of the reply; the converter drops that one label and says so, nothing else is changed. |
| `S_top_up/` | S (initials **SK**), ChatGPT | The ten top-up replies (Q02, Q03, Q04, Q05, Q07, Q08, Q09, Q10, Q11, Q12; there are no top-up passages for Q01 and Q06) and the two overlap replies `Q03_A` and `Q09_A`. Received as `Q03_A_SK_chatgpt.txt` and so on; only the names were changed, to `Q03_A_ChatGPT-SK.txt`. |

J used two tools (ChatGPT for Q01 to Q06, Gemini for Q07 to Q12), so no question was judged by both tools, and nothing shows whether one is stricter. The reader treats each tool-and-person pair as its own run.

The first full read is in `../review_results/2026-10-07_full_read/`.

## File names

`Q<question>_<A|B|TA>_<tool>-<initials>.txt`, for example `Q03_A_ChatGPT-J.txt` or `Q03_TA_Gemini-S.txt`.

- Use the same tool name every time (`ChatGPT`, `Gemini`), so a tool's replies group together.
- The initials keep J's and S's files apart if they use the same tool.
- Keep the reply text exactly as the tool gave it. Do not edit it.

## If a reply was saved as Rich Text (.rtf)

A reply pasted into a rich-text editor (for example Mac TextEdit) becomes an `.rtf` file named like `A01_A.rtf`. The reader cannot read that, so convert it first:

    python review_tools/rtf_to_txt.py review_replies/J_first_pack OUT_DIR --tool ChatGPT-J

It writes `Q01_A_ChatGPT-J.txt` and so on, checks each reply's `question_id` against the file name, and leaves the originals untouched.

## Not counted

The mock-trial replies (ChatGPT Q03 TA/TB, Gemini Q03 TA) are not real results and must not be put here.

## Reading them

The reader takes one folder, so both are copied into one before reading:

    python review_tools/ingest_llm_reviews.py --replies ALL_REPLIES_DIR --out RESULTS_DIR

Every figure it prints is LLM-judged. Nothing here is lawyer-validated.
