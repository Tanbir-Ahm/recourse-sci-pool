MARKING PACK FOR THE 30 REAL QUESTIONS: how to run it (copy and paste; every file is run twice, once in each tool)

WHAT THIS IS
A test of a legal search tool for Indian Supreme Court criminal-law judgments. This pack holds 19 questions (R01 to R29). For each question there are 7 to 16 passages that the search showed. An AI model is asked to mark each passage Yes / Partly / No / Misleading. All the texts are public court judgments; there is no personal or confidential information in the files.

WHAT YOU NEED
- ChatGPT AND Gemini. Every file is run in both tools (one new chat per file per tool). If one of you has only one of them, split the work so that each file still gets both tools.
- Switch OFF web search, browsing, "deep research" and any tools. We want the model to judge only the text it is given.
- Use a NEW chat for every file. Do not continue an earlier chat.

HOW TO RUN IT
1. Open the folder 'prompts'. There are 25 files. File names look like R03_A.txt or R03_B.txt.
   - A and B hold the SAME passages with the SAME numbers. In B the passages are listed in reverse order. Only 6 questions have a B file; it checks whether the model is swayed by position.
2. For each file: open it, select all, copy, paste into a NEW chat, send, wait for the answer.
3. Copy the model's ENTIRE reply and save it as a plain text file named exactly like this:
      R03_A_ChatGPT.txt     R03_A_Gemini.txt     R03_B_ChatGPT.txt     R03_B_Gemini.txt
   Put all the saved replies in the folder 'replies'.
4. If a reply is not JSON, or is cut off, send this to the same chat: "Reply again with only the JSON object, nothing else." and save the new reply instead.
5. Tick the file off in manifest.csv, zip the 'replies' folder and send it back.

HOW MUCH TO DO
50 chats in all (25 files x 2 tools). If time is short, do every A file in both tools first; the B files come last.

PLEASE DO NOT
- Edit the prompt text, or add your own opinion to the chat.
- Tell the model which search produced the passages (you do not know, and nor does it).
- Fix or tidy the model's JSON by hand. Save what it returned. Mistakes are useful to us.
- Ask the model whether a case is still good law. That is checked separately.

WHAT HAPPENS TO THE REPLIES
They are read by a script and compared. Every result will be labelled 'LLM-judged'. They are not lawyer-checked, and will not be described as lawyer-validated.

The marks mean:
   Yes        - answers the question directly
   Partly     - on the topic, useful, but incomplete
   No         - not helpful
   Misleading - could give a wrong impression (for example a lawyer's argument that the court rejects)
