import docx, glob, re, sys, json
sys.path.insert(0,"/home/user/recourse")
import section_checks as SC
CODES={"BNS":"BNS","BNSS":"BNSS","BSA":"BSA","Motor Vehicles Act":"MVACT","IT Act":"ITACT","Prevention of Corruption Act":"PCACT","PMLA":"PMLA","POCSO":"POCSO","NI Act":"NIACT"}
tot_ans=0; flagged=[]; absent=[]
for f in sorted(glob.glob("/root/.claude/uploads/33686f69-1895-5643-b31d-21bed3d4a6ee/*recourse*.docx")):
    d=docx.Document(f); lines=[p.text for p in d.paragraphs]
    # split into answers at "Answer" ... "Sources and checks"
    i=0
    while i<len(lines):
        if lines[i].strip()=="Answer":
            j=i+1
            while j<len(lines) and not lines[j].startswith("Sources and checks"): j+=1
            ans="\n".join(lines[i+1:j])
            # statute boxes after this up to next "Question N" or end
            k=j; end=len(lines)
            for t in range(j+1,len(lines)):
                if re.match(r"^Question \d+$", lines[t].strip()): end=t; break
            secs=[]; t=j
            while t<end:
                m=re.match(r"^(BNSS|BNS|BSA|IT Act|NI Act|Motor Vehicles Act|[A-Z][A-Za-z ,.()'-]*? Act(?:, \d{4})?) Section (\d{1,3}[A-Z]{0,2})\s*$", lines[t].strip())
                if m:
                    body=[]; t+=1
                    while t<end and not re.match(r"^(BNSS|BNS|BSA|IT Act|NI Act|Motor Vehicles Act|[A-Z][A-Za-z ,.()'-]*? Act(?:, \d{4})?) Section \d", lines[t].strip()) and not lines[t].startswith(("Official text","Authorities","The sections")):
                        body.append(lines[t]); t+=1
                    secs.append({"type":"statute","act":m.group(1),"act_display":m.group(1),"section_number":m.group(2),"text":"\n".join(body)})
                else: t+=1
            secs=[x for x in secs if len(x["text"])>40]
            tot_ans+=1
            g=SC.section_gloss(ans,secs,"")
            a=SC.absence_arguments(ans)
            for x in g: flagged.append((f.split("/")[-1][9:40], x))
            for x in a: absent.append((f.split("/")[-1][9:40], x))
            i=j
        else: i+=1
print("answers read:", tot_ans)
print("gloss flagged:", len(flagged))
for f,x in flagged: print("  ", f, x["act"], x["section"], x["words"], x["borrowed_from"], "|", x["sentence"][:150])
print("absence sentences:", len(absent))
for f,x in absent: print("  ", f, "|", x[:200])
