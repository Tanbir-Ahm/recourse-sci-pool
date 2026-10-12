MARKING PACK, THIRD BATCH: how to run it (copy and paste; every file is run twice, once in each tool)

WHAT THIS IS
A test of a legal search tool for Indian Supreme Court criminal-law judgments. This pack holds 29 questions (N01 to N30). For each question there are 9 to 11 passages that the search showed. An AI model is asked to mark each passage Yes / Partly / No / Misleading. All the texts are public court judgments; there is no personal or confidential information in the files. All the files are new questions; nothing here repeats an earlier pack.

WHAT YOU NEED
- ChatGPT AND Gemini. Every file is run in both tools (one new chat per file per tool). If one of you has only one of them, split the work so that each file still gets both tools.
- Switch OFF web search, browsing, "deep research" and any tools. We want the model to judge only the text it is given.
- Use a NEW chat for every file. Do not continue an earlier chat.

HOW TO RUN IT
1. Open the folder 'prompts'. There are 29 files, named like N01_A.txt. (One file per question; no reversed files.)
2. For each file: open it, select all, copy, paste into a NEW chat, send, wait for the answer.
3. Copy the model's ENTIRE reply and save it as a plain text file named exactly like this:
      N01_A_ChatGPT.txt        N01_A_Gemini.txt
   Put all the saved replies in the folder 'replies'.
4. If a reply is not JSON, or is cut off, send this to the same chat: "Reply again with only the JSON object, nothing else." and save the new reply instead.
5. BEFORE you zip, open each saved file and check two things (two files in an earlier round were wrong this way):
   a. it is the model's REPLY (it starts with { and has a "marks" list), not the prompt you pasted;
   b. the ChatGPT file and the Gemini file for the same question are different replies: each tool's own answer, not one saved twice.
6. Tick the file off in manifest.csv, zip the 'replies' folder and send it back.

HOW MUCH TO DO
58 chats in all (29 files x 2 tools). Each file lists the passage numbers to cover; use exactly the numbers shown.

PLEASE DO NOT
- Edit the prompt text, or add your own opinion to the chat.
- Fix or tidy the model's JSON by hand. Save what it returned. If a ChatGPT reply has backslashes before underscores or square brackets, leave them: a script removes them.
- Ask the model whether a case is still good law. That is checked separately.

WHAT HAPPENS TO THE REPLIES
They are read by a script and compared. Every result will be labelled 'LLM-judged'. They are not lawyer-checked, and will not be described as lawyer-validated.

The marks mean:
   Yes        - answers the question directly
   Partly     - on the topic, useful, but incomplete
   No         - not helpful
   Misleading - could give a wrong impression (for example a lawyer's argument that the court rejects)
