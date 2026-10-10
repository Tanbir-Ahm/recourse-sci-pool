"""Tests for review_tools/normalise_replies.py. Run: python review_tools/test_normalise_replies.py"""
import json
import os
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import normalise_replies as N
import ingest_llm_reviews as ing

FAILS = []


def check(name, cond, detail=""):
    print(("PASS " if cond else "FAIL ") + name + ("" if cond else f"  [{detail}]"))
    if not cond:
        FAILS.append(name)


reply = {"question_id": "R03", "marks": [{"no": 1, "mark": "Yes", "evidence": 'the court said "no arrest" [see para 5] in snake_case', "reason": "x\\ny", "confidence": "high"},
                                         {"no": 2, "mark": "No", "evidence": "", "reason": "y", "confidence": "low"}], "good_answer_present": "Yes", "best_passage_no": 1, "caveats": ""}
clean = json.dumps(reply, indent=1)
escaped = clean.replace("_", "\\_").replace("[", "\\[").replace("]", "\\]")          # what a chat window's copy button does

un, n = N.unescape_markdown(escaped)
check("the three Markdown escapes are undone exactly, and the text is the original", un == clean and n == clean.count("_") + clean.count("[") + clean.count("]"), (n, un[:80]))
check("an escaped reply cannot be read, the unescaped one can", ing.parse_reply(escaped)[0] is None and ing.parse_reply(un)[0] is not None)
back = ing.parse_reply(un)[0]
check("every mark, number and quote survives unchanged, including a bracket and an underscore inside a quote and a JSON \\n escape", back == reply, back)
check("other backslashes are left alone", N.unescape_markdown('a \\" b \\\\ c \\n d')[0] == 'a \\" b \\\\ c \\n d' and N.unescape_markdown('x\\_y')[1] == 1)
prompt = "QUESTION ID: R02   (prompt version: order A)\n\nYou are helping...\n" + "=" * 20 + "\nEND OF PASSAGES. Now reply with the single JSON object for R02 (passages 1, 2, 3).\n"
check("a saved prompt is recognised, a reply is not", N.is_prompt_echo(prompt) and not N.is_prompt_echo(escaped) and not N.is_prompt_echo(clean))
topup_prompt = "QUESTION ID: R02   (top-up batch, prompt version: order A)\n\nYou are helping...\n" + "=" * 20 + "\nEND OF PASSAGES. Now reply with the single JSON object for R02 (passages 10, 11).\n"
check("a saved top-up prompt is recognised by its opening line alone", N.is_prompt_echo(topup_prompt.split("END OF PASSAGES")[0]) and N.is_prompt_echo(topup_prompt))

src, out = tempfile.mkdtemp(), os.path.join(tempfile.mkdtemp(), "out")
files = {"R03_A_ChatGPT.txt": escaped, "R03_A_Gemini.txt": clean, "R05_A_ChatGPT.txt": prompt, "R06_A_Gemini.txt": clean.replace("R03", "R06"), "R06_A_ChatGPT.txt": clean.replace("R03", "R06")}
for f, t in files.items():
    open(os.path.join(src, f), "w", encoding="utf-8").write(t)
m = N.run(src, out, drop=["R05_A_ChatGPT.txt", "R06_A_ChatGPT.txt"])
check("an escaped file is written unescaped, a clean file byte for byte as it was", open(os.path.join(out, "R03_A_ChatGPT.txt"), encoding="utf-8").read() == clean and open(os.path.join(out, "R03_A_Gemini.txt"), encoding="utf-8").read() == clean)
check("files named in --drop are not written, and the others are", sorted(f for f in os.listdir(out) if f.endswith(".txt")) == ["R03_A_ChatGPT.txt", "R03_A_Gemini.txt", "R06_A_Gemini.txt"], os.listdir(out))
check("the manifest is written next to the output folder, not inside it", os.path.exists(out + "_NORMALISATION.json") and "NORMALISATION.json" not in os.listdir(out), os.listdir(out))
check("the manifest names the prompt echo and the identical pair", m["prompt_echoes"] == ["R05_A_ChatGPT.txt"] and m["identical_files"] == [["R06_A_ChatGPT.txt", "R06_A_Gemini.txt"]], (m["prompt_echoes"], m["identical_files"]))
check("the manifest keeps both fingerprints and the count of escapes removed", m["files"]["R03_A_ChatGPT.txt"]["markdown_escapes_removed"] > 0 and m["files"]["R03_A_ChatGPT.txt"]["sha256_as_received"] != m["files"]["R03_A_ChatGPT.txt"]["sha256_as_written"]
      and m["files"]["R06_A_ChatGPT.txt"]["dropped"] and m["files"]["R06_A_ChatGPT.txt"]["sha256_as_written"] is None)
check("the files as received are untouched", open(os.path.join(src, "R03_A_ChatGPT.txt"), encoding="utf-8").read() == escaped)
# a later upload added to the same output folder with its own manifest: the first manifest and the first files stay as they were
src2 = tempfile.mkdtemp()
open(os.path.join(src2, "R05_A_ChatGPT.txt"), "w", encoding="utf-8").write(escaped.replace("R03", "R05"))
first_manifest = open(out + "_NORMALISATION.json", encoding="utf-8").read()
m2 = N.run(src2, out, manifest_path=out + "_second_upload.json")
check("a second run adds its file to the same folder and writes its manifest where it was told", os.path.exists(out + "_second_upload.json") and "R05_A_ChatGPT.txt" in os.listdir(out), os.listdir(out))
check("the first manifest and the first files are not touched by the second run", open(out + "_NORMALISATION.json", encoding="utf-8").read() == first_manifest and open(os.path.join(out, "R03_A_ChatGPT.txt"), encoding="utf-8").read() == clean)
check("the second file is written unescaped", ing.parse_reply(open(os.path.join(out, "R05_A_ChatGPT.txt"), encoding="utf-8").read())[0]["question_id"] == "R05")
try:
    N.run(src, out + "2", drop=["nope.txt"])
    bad = False
except SystemExit:
    bad = True
check("a --drop that names no file is refused", bad)

# 2026-10-10 (third batch): a backtick escape, and a doubled-escaped quotation mark inside a quote
bt = {"question_id": "R07", "marks": [{"no": 1, "mark": "Partly", "evidence": "a `fine' serves", "reason": "r", "confidence": "high"}, {"no": 2, "mark": "No", "evidence": 'He said "I will see." and left', "reason": "r", "confidence": "high"}], "good_answer_present": "Yes", "best_passage_no": 1, "caveats": ""}
bt_text = json.dumps(bt)                                          # the model's own valid JSON: a backtick, and a quoted \" inside a quote
bt_copy = bt_text.replace("`", "\\`").replace('\\"', '\\\\"').replace("_", "\\_")      # what the copy button hands over
check("the copy-button version of that reply cannot be read", ing.parse_reply(bt_copy)[0] is None, bt_copy[:120])
u1, n1 = N.unescape_markdown(bt_copy)
check("a backslash before a backtick is undone, like the other three escapes", "`" in u1 and "\\`" not in u1 and n1 >= 1, u1[:100])
u2, n2 = N.repair_doubled_quote_escapes(u1)
check("a doubled-escaped quotation mark is repaired, and only then the reply reads", ing.parse_reply(u1)[0] is None and n2 == 2 and ing.parse_reply(u2)[0] is not None, (n2, u2[:150]))
check("every mark, number and quote survives the two repairs (the evidence is the text the model wrote)", ing.parse_reply(u2)[0] == bt, ing.parse_reply(u2)[0])
check("a reply that already reads is never touched by the doubled-quote repair, even if it holds an escaped backslash before a closing quote",
      N.repair_doubled_quote_escapes(json.dumps({"marks": [{"no": 1, "mark": "Yes", "evidence": "ends with a backslash \\"}]})) == (json.dumps({"marks": [{"no": 1, "mark": "Yes", "evidence": "ends with a backslash \\"}]}), 0))
unfixable = '{"marks": [{"no": 1, "mark": "Yes", "evidence": "bad \\\\" here"}, {"no": 2 "mark": "No"}]}'
check("a file the repair cannot make readable is left exactly as it was", N.repair_doubled_quote_escapes(unfixable) == (unfixable, 0))
src3, out3 = tempfile.mkdtemp(), os.path.join(tempfile.mkdtemp(), "out")
open(os.path.join(src3, "R07_A_ChatGPT.txt"), "w", encoding="utf-8").write(bt_copy)
m3 = N.run(src3, out3)
w3 = open(os.path.join(out3, "R07_A_ChatGPT.txt"), encoding="utf-8").read()
check("run() writes the repaired file, reads back to the original, and the manifest counts both repairs", ing.parse_reply(w3)[0] == bt and m3["files"]["R07_A_ChatGPT.txt"]["doubled_quote_escapes_repaired"] == 2 and m3["files"]["R07_A_ChatGPT.txt"]["markdown_escapes_removed"] >= 1, m3)
check("the file as received is untouched by run()", open(os.path.join(src3, "R07_A_ChatGPT.txt"), encoding="utf-8").read() == bt_copy)

print()
print("FAILED: " + ", ".join(FAILS) if FAILS else "all passed")
sys.exit(1 if FAILS else 0)
