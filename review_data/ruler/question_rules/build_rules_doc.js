const fs = require('fs');
const { Document, Packer, Paragraph, TextRun, Table, TableRow, TableCell, HeadingLevel, AlignmentType, LevelFormat, BorderStyle, WidthType, ShadingType, Footer, PageNumber } = require('docx');

const W = 9026; // A4 with 1-inch margins
const FONT = 'Arial';
const t = (s, o = {}) => new TextRun({ text: s, font: FONT, size: 21, ...o });
const p = (s, o = {}) => new Paragraph({ spacing: { after: 100 }, children: Array.isArray(s) ? s : [t(s)], ...o });
const b = (s) => t(s, { bold: true });
const h1 = (s) => new Paragraph({ heading: HeadingLevel.HEADING_1, spacing: { before: 280, after: 120 }, children: [new TextRun({ text: s, font: FONT, size: 28, bold: true, color: '1F3864' })] });
const h2 = (s) => new Paragraph({ heading: HeadingLevel.HEADING_2, spacing: { before: 200, after: 80 }, children: [new TextRun({ text: s, font: FONT, size: 23, bold: true, color: '2F5496' })] });
const bullet = (s, lvl = 0) => new Paragraph({ numbering: { reference: 'bul', level: lvl }, spacing: { after: 60 }, children: Array.isArray(s) ? s : [t(s)] });
const num = (s, ref = 'num') => new Paragraph({ numbering: { reference: ref, level: 0 }, spacing: { after: 60 }, children: Array.isArray(s) ? s : [t(s)] });
const callout = (title, lines, fill = 'FFF2CC') => [
  new Paragraph({ spacing: { before: 120, after: 0 }, shading: { type: ShadingType.CLEAR, fill }, border: { left: { style: BorderStyle.SINGLE, size: 18, color: 'BF9000', space: 6 } }, children: [t(title, { bold: true })] }),
  ...lines.map((l, i) => new Paragraph({ spacing: { after: i === lines.length - 1 ? 160 : 0 }, shading: { type: ShadingType.CLEAR, fill }, border: { left: { style: BorderStyle.SINGLE, size: 18, color: 'BF9000', space: 6 } }, children: [t(l)] })),
];
const bd = { style: BorderStyle.SINGLE, size: 4, color: 'A6A6A6' };
const borders = { top: bd, bottom: bd, left: bd, right: bd };
function table(widths, header, rows, fs = 18) {
  const mk = (txt, w, hdr) => new TableCell({
    borders, width: { size: w, type: WidthType.DXA }, margins: { top: 50, bottom: 50, left: 80, right: 80 },
    shading: hdr ? { type: ShadingType.CLEAR, fill: 'DDE6F0' } : undefined,
    children: String(txt).split('\n').map(line => new Paragraph({ spacing: { after: 20 }, children: [new TextRun({ text: line, font: FONT, size: fs, bold: hdr })] })),
  });
  return new Table({
    width: { size: widths.reduce((a, c) => a + c, 0), type: WidthType.DXA }, columnWidths: widths,
    rows: [new TableRow({ tableHeader: true, children: header.map((h, i) => mk(h, widths[i], true)) }), ...rows.map(r => new TableRow({ cantSplit: true, children: r.map((c, i) => mk(c, widths[i], false)) }))],
  });
}
const gap = () => new Paragraph({ spacing: { after: 80 }, children: [] });

const C = [];
C.push(new Paragraph({ alignment: AlignmentType.LEFT, spacing: { after: 60 }, children: [new TextRun({ text: 'Rules and Guidelines for the New Test Questions', font: FONT, size: 40, bold: true, color: '1F3864' })] }));
C.push(new Paragraph({ spacing: { after: 60 }, children: [t('The final test of the search recipe (Fix Test, version 1). Issued 11 October 2026. PRIVATE: for the question writer, the owner and Mr. Advocate only.', { color: '595959' })] }));
C.push(new Paragraph({ spacing: { after: 160 }, border: { bottom: { style: BorderStyle.SINGLE, size: 8, color: '1F3864', space: 4 } }, children: [] }));

C.push(...callout('The short version', [
  'HOW MANY: 30 questions (27 scored questions in domains A to J, plus 3 controls in domain K), plus up to 3 reserves. Not 29: the structure below depends on 27 + 3.',
  'WHO: someone who has not seen the search results. The questions must be fresh, real-sounding, anonymised and not copied from the earlier 30.',
  'WHAT MAKES THIS SET DIFFERENT: at least 8 "look-alike" questions (a special Act whose wording also fits ordinary criminal law), at least 3 that never name the Act, 2 twin pairs, at least 4 currency traps, and a fully verified answer key with ALL acceptable authorities.',
  'WHEN: the questions and the key are sealed with a fingerprint (hash) BEFORE any search. After that nothing can be changed. A question that fails our checks is replaced from the reserves before sealing, never afterwards.',
]));

// ---------------------------------------------------------------- 1
C.push(h1('1. Why this set matters'));
C.push(p('The first 30 questions were used up. Eleven of them were sealed and run once; the search missed two of the four quality floors, so nothing can be connected to the live site on that evidence. We then found four different causes behind the misses, and designed small changes to the search. These new questions are the only fair way to test whether those changes work, because nobody may tune on questions already seen.'));
C.push(p([b('This one set does two jobs in a single run:')]));
C.push(num('It decides whether any of three small changes (C: at most 2 passages per judgment in the top 5; N1 and N2: a small boost for judgments about the Act the question names) is better than today\'s recipe. Today\'s recipe wins every tie.', 'n1'));
C.push(num('It tests whether the recipe that wins meets the four floors needed before anything goes toward the lawyer panel (see section 12).', 'n1'));
C.push(p('So the questions must be representative of what real people ask, at the difficulty real people bring. Do not make them easier or harder to push the result either way. A hard, honest set that the search fails is more useful than an easy one it passes.'));

// ---------------------------------------------------------------- 2
C.push(h1('2. How many questions'));
C.push(table([2600, 6426], ['Item', 'Rule'], [
  ['Required', '30 questions in total: 27 scored questions (domains A to J) and 3 controls (domain K).'],
  ['Reserves', 'Up to 3 extra questions, numbered NR1 to NR3, each marked with the domain letter it can replace. A reserve is used only to replace a question rejected by our checks (section 11), in the same domain, before sealing.'],
  ['Why 30 and not 29', 'The domain table below adds up to 27 + 3. Dropping one question breaks either a domain count or the controls, and the pooled shares we score get noisier. Twenty-four usable questions is the absolute floor after checks; below that the test is cancelled, not run.'],
  ['Why not more', 'Each question costs two chats from J and S per search version (about 60 chats for 30 questions). More than 33 files would overload them.'],
  ['Ids', 'N01 to N30 in the order of the table in section 4. Reserves NR1 to NR3. The ids are fixed when the file is sealed.'],
]));
C.push(gap());

// ---------------------------------------------------------------- 3
C.push(h1('3. Who writes them, and the independence rules'));
C.push(bullet([b('Preferred writer: '), t('Mr. Advocate, or another practising advocate who has not seen the results of the earlier test. If the owner writes them, the declaration sheet must say so.')]));
C.push(bullet('The writer must not have seen: the answers or the search results for the sealed 11 questions, any marks from J and S, or the results of the fix test.'));
C.push(bullet('The writer may have seen the earlier 30 questions. In that case they must write NEW topics, NEW key authorities and NEW facts. We run an automatic duplicate check (section 11); duplicates are returned.'));
C.push(bullet('Write the questions the way a real client would, from the legal substance. Do NOT consult the list of trigger words while writing, and do NOT choose wording to make a boost fire or not fire. The "Act concerned" tag is decided by the law that governs the issue, not by the words used.'));
C.push(bullet('If an AI tool drafted any question or any part of a key, say which tool and for what on the declaration sheet. Everything it produced must still be checked against the judgment text (section 9). The first set was an AI research pass whose keys were only partly checked; that weakened it.'));
C.push(bullet('Do not run the questions through any chatbot or search tool, including the Recourse site, and do not adjust wording after seeing any answer.'));
C.push(bullet('Do not show the questions to J, S or anyone else before they are sealed.'));

// ---------------------------------------------------------------- 4
C.push(h1('4. The composition: domains and the slot plan'));
C.push(p('Domains A to K are the same as the first test, so our scoring machinery stays unchanged. The "slot plan" below is a recommended allocation that satisfies every mix rule in section 5. The writer chooses the actual topics freely, but may change the plan only if every rule in section 5 still holds (we recount).'));
const plan = [
  ['N01', 'A', 'General arrest or custody question', '-', '-', '-', 'N', 'NEW', 'N'],
  ['N02', 'A', 'Search or arrest of a person in a drug case: the Act\'s own search rules versus ordinary arrest/search law', 'NDPS', 'Y', 'unnamed', 'E', 'NONE', 'N'],
  ['N03', 'A', 'General arrest procedure or police custody', '-', '-', '-', 'L', 'OLD', 'N'],
  ['N04', 'B', 'Bail under the anti-terror Act versus ordinary bail', 'UAPA', 'Y', 'named', 'L', 'OLD', 'N'],
  ['N05', 'B', 'General regular/default bail (currency trap)', '-', '-', '-', 'N', 'NEW', 'Y'],
  ['N06', 'B', 'Caste abuse: SC/ST Act versus ordinary assault/insult; bail or quashing', 'SC/ST', 'Y', 'unnamed', 'E', 'NONE', 'N'],
  ['N07', 'C', 'Bounced cheque (everyday)', 'NI Act', 'Y', 'named', 'E', 'NONE', 'N'],
  ['N08', 'C', 'Bounced cheque (currency trap)', 'NI Act', '-', 'named', 'N', 'NONE', 'Y'],
  ['N09', 'C', 'Section 138 point in legal wording', 'NI Act', '-', 'named', 'L', 'NONE', 'N'],
  ['N10', 'D', 'Drug case point in legal wording', 'NDPS', '-', 'named', 'L', 'NONE', 'N'],
  ['N11', 'D', 'Drug case, lay description only (pills, bag, car)', 'NDPS', 'Y', 'unnamed', 'E', 'NONE', 'N'],
  ['N12', 'E', 'Quashing: civil dispute dressed as crime (currency trap)', '-', '-', '-', 'L', 'NEW', 'Y'],
  ['N13', 'E', 'Cheating complaint over a cheque or loan; TWIN of N07 (same surface facts, general law)', '-', 'Y', '-', 'N', 'OLD', 'N'],
  ['N14', 'E', 'Online fraud / hacked account / fake profile versus cheating', 'IT Act', 'Y', 'unnamed', 'E', 'NONE', 'N'],
  ['N15', 'F', 'Living with an abusive partner or in-laws: right to stay, protection; TWIN of N17', 'PWDVA', 'Y', 'unnamed', 'E', 'NONE', 'N'],
  ['N16', 'F', 'Dowry demand and being thrown out (two Acts at once)', 'DPA + PWDVA', 'Y', 'unnamed', 'N', 'NONE', 'N'],
  ['N17', 'F', 'Same family facts as N15 but the criminal-complaint route; TWIN of N15', '-', 'Y', '-', 'L', 'NEW', 'N'],
  ['N18', 'G', 'Child sexual abuse, lay description; TWIN of N20', 'POCSO', 'Y', 'unnamed', 'N', 'NONE', 'N'],
  ['N19', 'G', 'Juvenile accused of an offence, age and procedure', 'JJ Act + POCSO', 'Y', 'named', 'E', 'NONE', 'N'],
  ['N20', 'G', 'Adult rape question (consent, general law); TWIN of N18', '-', 'Y', '-', 'L', 'NEW', 'N'],
  ['N21', 'H', 'Firearm found plus an injury: Arms Act versus violent-crime law', 'Arms Act', 'Y', 'unnamed', 'E', 'NONE', 'N'],
  ['N22', 'H', 'Drunk or rash driving causing death versus negligence offences', 'MV Act', 'Y', 'unnamed', 'N', 'OLD', 'N'],
  ['N23', 'H', 'Murder / culpable homicide / hurt (currency trap)', '-', '-', '-', 'L', 'OLD', 'Y'],
  ['N24', 'I', 'Bail or arrest in a money-laundering case versus ordinary bail (currency trap)', 'PMLA', 'Y', 'named', 'L', 'NEW', 'Y'],
  ['N25', 'I', 'Bribery / sanction for prosecution of a public servant', 'PC Act', 'Y', 'named', 'N', 'NONE', 'N'],
  ['N26', 'J', 'Remission, parole or premature release (currency trap)', '-', '-', '-', 'E', 'NEW', 'Y'],
  ['N27', 'J', 'Appeal against conviction or suspension of sentence', '-', '-', '-', 'L', 'OLD', 'N'],
  ['N28', 'K', 'Control K1: civil, tax or divorce question', '-', '-', '-', 'E', 'NONE', '-'],
  ['N29', 'K', 'Control K2: point settled only by a High Court, or by a ruling after 30 June 2026', '-', '-', '-', 'L', 'NONE', '-'],
  ['N30', 'K', 'Control K3: answered by a statute or table, not a judgment', '-', '-', '-', 'E', 'NONE', '-'],
];
C.push(table([620, 520, 3560, 1100, 650, 860, 520, 700, 496], ['Id', 'Dom.', 'Intended type', 'Act(s) concerned', 'Look-alike', 'Act named in text?', 'Phr.', 'Code tag', 'Trap'], plan, 16));
C.push(p([t('Phr.: E = everyday, L = legal wording, N = long narrative. Code tag: NEW = BNS/BNSS/BSA section number in the text, OLD = IPC/CrPC/Evidence Act number, NONE = no section number. Trap: currency trap (section 7). "Act named in text?" refers to the Act\'s title, acronym or section in the question itself. NR1 to NR3 are reserves for any domain.', { size: 18, color: '595959' })]));

// ---------------------------------------------------------------- 5
C.push(h1('5. The mix rules (all must hold; we recount before sealing)'));
C.push(table([3300, 1500, 4226], ['Rule', 'Requirement', 'Why'], [
  ['Domain counts (A to J)', 'A 3, B 3, C 3, D 2, E 3, F 3, G 3, H 3, I 2, J 2 = 27', 'Keeps the scoring and the per-domain lights unchanged.'],
  ['Controls (K)', 'Exactly 3: one each of K1, K2, K3', 'Questions with no good answer in the index; the search should not look confident on them.'],
  ['Everyday phrasing', 'at least 6 of the 27', 'Real users write like this. Short, plain, no legal terms.'],
  ['Legal-wording phrasing', 'at least 6 of the 27', 'Lawyer-style questions; statute terms allowed, case names not.'],
  ['Long-narrative phrasing', 'at least 6 of the 27', 'Messy, multi-fact stories with one answerable core.'],
  ['New-code numbers (BNS/BNSS/BSA)', 'at least 6', 'Users now speak the new codes; the index mostly speaks IPC/CrPC.'],
  ['Old-code numbers (IPC/CrPC/Evidence Act)', 'at least 6', 'Legacy cases and the index\'s own language.'],
  ['No section number', 'the rest (at least 8)', 'Most real users give no section.'],
  ['Currency traps (A to J)', 'at least 4 (target 6)', 'The first ruling a search finds was later overruled, narrowed or replaced. Needed for rule 4 of the choice rules and the currency light.'],
  ['Best law from 2017 or later', 'at least 10 of the 27', 'Recent law is where search is weakest.'],
  ['Act-concerning questions', 'at least 14 of the 27, covering at least 10 of the 13 listed Acts; NDPS, NI Act, PWDVA and POCSO at least 2 each', 'The named-Act boost can only be tested where an Act applies. The slot plan covers all 13.'],
  ['General criminal-law questions (no listed Act)', 'at least 8 of the 27', 'To catch any harm the boost does to ordinary questions.'],
  ['Look-alike questions', 'at least 8 (target 10 or more)', 'See section 6. This is the heart of the test.'],
  ['Look-alikes that do not name the Act', 'at least 3 (target 5)', 'A boost that fires only when the Act is named would miss most real users.'],
  ['Twin pairs', 'at least 2 pairs (the plan has 3)', 'Same surface facts, one under the special Act and one under general law. Shows whether the boost helps one without hurting the other.'],
  ['Index gaps', 'at most 3 questions whose primary authority is not in our index', 'We check; a gap question is scored apart and wastes the slot.'],
  ['Hinglish', 'optional, 0 to 3, counted as everyday and tagged Y', 'Only if real users write that way. Write them exactly as a user would.'],
]));
C.push(gap());
C.push(p([b('The 13 listed Acts: '), t('Protection of Women from Domestic Violence Act 2005 (PWDVA); NDPS Act 1985; POCSO Act 2012; SC/ST (Prevention of Atrocities) Act 1989; Negotiable Instruments Act 1881 (section 138); Prevention of Money-Laundering Act 2002; UAPA 1967; Dowry Prohibition Act 1961; Juvenile Justice Act 2015; Prevention of Corruption Act 1988; Arms Act 1959; Information Technology Act 2000; Motor Vehicles Act 1988.')]));
C.push(p([b('Do not set scored questions on '), t('the Immoral Traffic Act, Child Marriage Act, Protection of Civil Rights Act, GST Act, Muslim Women (Protection of Rights on Marriage) Act, the Public Property Damage Act or the Companies Act: our index holds almost nothing on them. They may appear only as controls.')]));

// ---------------------------------------------------------------- 6
C.push(h1('6. Look-alike questions: the most important requirement'));
C.push(h2('6.1 What a look-alike is'));
C.push(p('A look-alike is a question whose subject sits under a special Act, but whose words also fit ordinary criminal law (or a different Act), so a search can easily return passages from the wrong regime. The passages look relevant but answer a different legal question.'));
C.push(p([b('Why we need them: '), t('in the first test the single worst failure was of exactly this kind: a woman asked about her rights under a special protective Act, and the top results were about time limits for ordinary criminal complaints. Another question on arrest duties pulled passages about search rules under a drug law. Such passages are marked Misleading, and they alone sank two of the four floors.')]));
C.push(h2('6.2 What each look-alike must have'));
C.push(bullet('A real, defensible answer under the special Act (or under the general law for a twin), supported by Supreme Court authority in our index.'));
C.push(bullet('A named "neighbour regime": the other law that a careless search would pull in. Record it on the sheet.'));
C.push(bullet('The neighbour must be genuinely plausible, not a stretch. Test: would a trained clerk, skimming, confuse the two?'));
C.push(bullet('At least 3 of the look-alikes must describe the facts in lay words without naming the Act, its acronym, or its section. Example of the idea (not to be copied): a person describes an abusive spouse and a threatened eviction without ever saying "domestic violence".'));
C.push(h2('6.3 Twin pairs'));
C.push(p('A twin pair is two questions with similar surface facts but different governing law: one under the special Act, one under general law. Mark each with "Twin of Nxx". At least 2 pairs; the slot plan has 3 (N07/N13, N15/N17, N18/N20). The point is to check that a boost for the special Act lifts the right passages for one question and does not drag wrong ones into the other.'));
C.push(h2('6.4 Neighbour catalogue (ideas, one per Act; the writer picks and varies freely)'));
C.push(table([2300, 3300, 3426], ['Act', 'Typical neighbour a search confuses it with', 'Kind of lay question that sits on the boundary'], [
  ['PWDVA', 'Cruelty offence (IPC 498A / BNS 85), maintenance under CrPC/BNSS, limitation rules for criminal complaints', 'Right to stay in the home; protection from an abusive partner or in-laws; live-in relationships; monetary relief'],
  ['NDPS', 'Ordinary arrest and search law (CrPC/BNSS), Evidence Act on statements to officers, ordinary bail', 'Police search of a person or vehicle; pills or "weed" found; statement signed at an office; bail in a drug case'],
  ['POCSO', 'Rape and sexual-assault offences in the general code; Child Marriage law; Juvenile law', 'A child touched or messaged; relationship between teenagers; age of the child versus age of consent'],
  ['SC/ST Act', 'Ordinary insult, assault, intimidation; anticipatory bail rules; Civil Rights Act (untouchability)', 'Caste abuse in public; denied access to a place; false-case allegations'],
  ['NI Act (s.138)', 'Cheating (IPC 420 / BNS 318), civil recovery, breach of trust', 'Bounced cheque given as security; part payment; notice and complaint timing'],
  ['PMLA', 'Ordinary bail and arrest law; the underlying offence\'s own trial', 'Agency questions, property attached, arrest by the Directorate, bail conditions'],
  ['UAPA', 'Ordinary bail law; sedition-type or public-order offences', 'Booked as linked to a banned group; bail after a long wait'],
  ['Dowry Prohibition Act', 'Cruelty (498A / BNS 85), dowry death (304B), abetment of suicide', 'Demand for money or goods after marriage; return of gifts'],
  ['Juvenile Justice Act', 'Ordinary trial and bail; POCSO if the child is the victim', 'A teenager arrested; proof of age; observation home versus jail'],
  ['Prevention of Corruption Act', 'Cheating, criminal breach of trust, general sanction rules (CrPC 197)', 'Official demanding money; trap case; sanction to prosecute; unexplained wealth'],
  ['Arms Act', 'Murder, hurt, general weapons offences', 'Gun or cartridges found; no licence; weapon used in a fight'],
  ['IT Act', 'Cheating by personation (IPC/BNS), defamation, sexual offences', 'OTP fraud, hacked account, fake profile, photos shared without consent'],
  ['Motor Vehicles Act', 'Death by negligence (IPC 304A / BNS 106), rash driving offences', 'Drink-driving crash; hit-and-run; no licence or insurance'],
]));
C.push(gap());

// ---------------------------------------------------------------- 7
C.push(h1('7. Currency traps'));
C.push(p('A currency trap is a question where the ruling a search is most likely to find first has since been overruled, modified, put on hold, or replaced by a statute. At least 4 are needed (target 6) among questions A to J.'));
C.push(bullet('Only Supreme Court-to-Supreme Court changes and statute replacements count as "stale" in our scoring. A ruling that is merely narrower than today\'s law does not count; list it as "narrower" and do not rely on it as a trap.'));
C.push(bullet([b('For every trap record: '), t('(a) the older ruling by name, year and court; (b) the later ruling or statute that changed it, with year; (c) exactly what changed, in one or two sentences; (d) the current authority. Mr. Advocate checks these before sealing.')]));
C.push(bullet('The older ruling must be in our index (or the trap cannot be measured). We check. If the later ruling is not in our index, say so: that is a different, harder kind of trap.'));
C.push(bullet('Avoid traps that depend on law still moving in October 2026 (pending reviews or reconstituted benches). If one is unavoidable, mark Conf as G and add it to the "To verify" column.'));
C.push(bullet('Use the offence-date rule correctly: conduct on or before 30 June 2024 is tried under the IPC; from 1 July 2024 under the BNS; proceedings pending on 1 July 2024 continue under the CrPC (BNSS section 531). The key must state which code applies and why.'));

// ---------------------------------------------------------------- 8
C.push(h1('8. Controls (domain K)'));
C.push(table([1100, 3400, 4526], ['Control', 'What it is', 'Lesson from the first set'], [
  ['K1', 'A civil, tax or divorce question: no criminal-law judgment answers it.', 'Should be unmistakably outside criminal law. The search should show nothing confident.'],
  ['K2', 'A point settled only by a High Court, or by a Supreme Court ruling decided after 30 June 2026.', 'The first K2 was not clean: its ruling was a Supreme Court one and the index covers the period only partly. Before submitting, check that NO Supreme Court judgment decided on or before 30 June 2026 answers it. State how you checked.'],
  ['K3', 'A point answered by a statute or comparison table (for example, a section-mapping question) rather than a judgment.', 'A case-law index cannot answer it. The correct behaviour is to say it is not checked.'],
]));
C.push(gap());

// ---------------------------------------------------------------- 9
C.push(h1('9. How to write each question'));
C.push(h2('9.1 Style by type'));
C.push(table([1700, 3100, 4226], ['Type', 'Length and voice', 'Example of the idea (not for use)'], [
  ['Everyday (E)', 'One to three sentences, up to about 60 words; plain words; as a worried relative would type.', '"Police took my brother, no paper shown. Is that legal?"'],
  ['Legal wording (L)', 'One or two sentences, up to about 50 words; statutory terms and section numbers allowed; no case names.', '"Whether X requires Y before Z under Section N."'],
  ['Long narrative (N)', 'Four to eight sentences, up to about 120 words; chronology, irrelevant detail, mixed facts, but ONE answerable core issue.', 'A messy story ending in a single clear legal question.'],
]));
C.push(gap());
C.push(h2('9.2 Do'));
C.push(bullet('Make each question answerable by a lawyer in five lines or fewer, citing at least one Supreme Court authority that is in our index.'));
C.push(bullet('Ask what the law is or how courts treat the point. Do not ask for a prediction of the outcome ("will I win?").'));
C.push(bullet('Sound like a real client of an Indian legal-aid or advice service: realistic mistakes, mixed English, uncertainty.'));
C.push(bullet('Keep one issue per question. Where two Acts genuinely apply (for example dowry and domestic violence), say so in the Act tag; the answerable core is still one.'));
C.push(bullet('Include dates only when the date matters to the law (for example the offence date for IPC/BNS).'));
C.push(h2('9.3 Do not'));
C.push(bullet('Do not name any case, judge or court order in the question. Do not paste the answer or the doctrine\'s name into the question.'));
C.push(bullet('Do not include personal names, organisation names, FIR or case numbers, phone numbers, or addresses. Name a city or court only when the territory is legally material (for example jurisdiction).'));
C.push(bullet('Do not copy or lightly reword any of the earlier 30 questions or their topics.'));
C.push(bullet('Do not write multi-issue questions, hypotheticals about law that does not exist, or questions whose answer turns on facts nobody could know.'));
C.push(bullet('Do not make the question easier or harder than a real person\'s question to influence the result.'));
C.push(h2('9.4 Privacy'));
C.push(p('The questions go to Voyage (search and re-ranking), to ChatGPT and Gemini (marking, run by J and S) and into the private repository. Anonymise accordingly. The answer key never goes to Voyage, ChatGPT, Gemini, J or S.'));

// ---------------------------------------------------------------- 10
C.push(h1('10. The answer key: what to record and how to verify it'));
C.push(p('The first set\'s key was partly AI-researched and only partly checked (seven items were left "to verify"). A weak key is the quickest way to misjudge the search. This time Mr. Advocate reviews the key BEFORE sealing.'));
C.push(table([2800, 6226], ['Field', 'What to write'], [
  ['Expected answer', 'The correct, current answer in plain words, up to 120 words, as of the date of submission. State which code (IPC/BNS, CrPC/BNSS, Evidence Act/BSA) applies when it matters.'],
  ['Primary authority', 'The single best Supreme Court judgment: name, year, neutral citation or SCC reference. Decided on or before 30 June 2026.'],
  ['Other acceptable authorities', 'EVERY other judgment that would also be a right answer (at least two where they exist). In the first test the key named only one case, so correct answers were counted as misses. This field matters.'],
  ['Older ruling a search may wrongly show', 'For traps: the older ruling, the later change, what changed, the current authority (section 7). For non-traps: "none known".'],
  ['Neighbour regime', 'For look-alikes: the other law a careless search would pull in (section 6).'],
  ['Source URLs', 'Prefer the judgment text on the Supreme Court site or an official report. News summaries alone are not enough.'],
  ['How verified', 'One of: read the judgment text; read an official or standard law report; secondary source only. "Secondary only" forces Conf = G and a "To verify" entry.'],
  ['Conf', 'C = certain the answer is correct and current; L = likely; G = guessing.'],
  ['To verify', 'Anything a practising advocate should confirm, with the reason. Leave nothing silent.'],
]));
C.push(gap());
C.push(h2('10.1 Index coverage: what our index can and cannot answer'));
C.push(bullet('The index holds 10,503 Supreme Court criminal-law judgments (236,155 passages), from 1951 to at least 13 July 2026, plus 19 added judgments. 2026 coverage is partial.'));
C.push(bullet('It holds no High Court judgments and no statutes. A point decided only by a High Court cannot be answered (that is control K2).'));
C.push(bullet('It was built with a criminal-law density filter, so some borderline judgments are missing. Authorities that are mainly civil or constitutional may be absent.'));
C.push(bullet('We check every primary and acceptable authority against the index after you submit. If more than 3 questions have a primary authority outside the index, the surplus are returned for replacement.'));

// ---------------------------------------------------------------- 11
C.push(h1('11. File format, and what we check after you send it'));
C.push(h2('11.1 The file'));
C.push(p('One Excel workbook with three sheets. Keep the column names exactly.'));
C.push(table([1900, 7126], ['Sheet', 'Columns'], [
  ['Questions', 'Id; Domain (A to K); Question text; Phr (E/L/N); Hinglish (Y/N); Sec (NEW/OLD/NONE); CT (Y/N); Era 2017+ (Y/N); Control type (K1/K2/K3, domain K only); Act(s) concerned (from the 13, or "none"); Act, section or acronym named in the question text (Y/N); Look-alike (Y/N); Neighbour regime; Twin of (Id or blank); Reserve for domain (reserves only).'],
  ['Key', 'Id; Expected answer; Primary authority; Other acceptable authorities; Older ruling a search may wrongly show (traps) with what changed and the current authority; Code that applies and why; Source URLs; How verified; Conf; To verify.'],
  ['Declaration', 'Writer\'s name and role; date; has the writer seen the earlier 30 questions (Y/N); has the writer seen the trigger-word list (Y/N); AI tools used and for what; confirmation that no search tool or chatbot was run on the questions; confirmation that no one else has seen the questions.'],
]));
C.push(gap());
C.push(h2('11.2 Our checks (before anything is sealed)'));
C.push(num('Format and counts: every rule in section 5 recounted automatically. Shortfalls are listed.', 'n2'));
C.push(num('Duplicates: each question compared by meaning and by authority with the earlier 30 and the ruler\'s 16 topics. Overlaps are returned.', 'n2'));
C.push(num('Index coverage: every primary and acceptable authority looked up in the index; gaps counted (at most 3 questions).', 'n2'));
C.push(num('Trigger check: whether the Act tags match what our word-matching actually detects. This measures the matching on the new questions BEFORE any search, so we know how often the boost can fire and how often it misfires.', 'n2'));
C.push(num('Mr. Advocate reviews the Key sheet: primary authority, what changed, which code applies, the To-verify items. Corrections are made before sealing.', 'n2'));
C.push(num('Replacement: a question that fails any check is replaced from the reserves (same domain) or rewritten once. If fewer than 24 usable questions remain, the test is cancelled.', 'n2'));
C.push(num('Sealing: ids fixed, the file fingerprinted (SHA-256), committed to the private repository, and a one-time hand-out guard installed, all before any search.', 'n2'));

// ---------------------------------------------------------------- 12
C.push(h1('12. What the questions will decide'));
C.push(h2('12.1 The run'));
C.push(bullet('One search of the 30 questions, once. Versions: today\'s recipe and each change that passed the free pre-check on the old questions (C, N1, N2). All passages pooled and shuffled, so reviewers cannot tell which version found what.'));
C.push(bullet('Every passage marked Yes / Partly / No / Misleading by both ChatGPT and Gemini, run by J and S: about 60 chats, in one round. Marks are AI marks, not lawyer marks; every figure is labelled "LLM-judged".'));
C.push(bullet('The answer key is opened only after the marks are scored. Nothing is re-run and nothing is changed after a mark exists.'));
C.push(h2('12.2 Choosing a change'));
C.push(p('A change replaces today\'s recipe only if all six hold: its average top-5 grade is no lower in all four ways of settling disagreements between the two judges; its Misleading share is at most 2 points higher and its useful share at most 2 points lower; it is better on at least two more questions than it is worse; it finds the named case at least as often and lets in no more overruled cases; the two judges agree on at least 60% of passages; and on the look-alike questions it lowers the Misleading share by at least 5 points or finds the named case more often. If none passes, today\'s recipe stays.'));
C.push(h2('12.3 The four floors (for the chosen recipe)'));
C.push(table([3000, 3000, 3026], ['Floor', 'Needed', 'Last time (11 sealed questions)'], [
  ['F1 useful passages (Yes or Partly) in the top 5; where the judges disagree take the lower mark', '70% or more', '69.1%: missed'],
  ['F2 Misleading passages in the top 5: lower-mark / higher-mark', '15% or less / 10% or less', '18.2% / 5.5%: missed'],
  ['F3 named authority in the top 10 (answerable questions)', '60% or more', '60%: met exactly'],
  ['F4 direct (Yes) answers', '25% or more', '34.5%: met'],
]));
C.push(gap());
C.push(p('Meeting the floors leads only to shadow mode (a background job, nothing shown to users) in the eligible domains, and never to the verified answer path. Missing a floor again means more new questions. Even a tool as good as in the early tests would miss at least one floor in roughly 30 to 40% of runs of this size, because of noise; that is why the questions must be honest rather than flattering.'));
C.push(h2('12.4 What the set cannot show'));
C.push(p('Whether a change helps questions unlike these; whether two changes together help; anything a lawyer would grade; answer writing; real users. Thirty questions cannot show a difference smaller than about 8 to 10 points, so the rules ask for no loss plus a gain on the look-alikes, not a large gain.'));

// ---------------------------------------------------------------- 13
C.push(h1('13. Timeline and responsibilities'));
C.push(table([700, 5200, 3126], ['Step', 'What happens', 'Who'], [
  ['1', 'Mr. Advocate reviews the Machine Spec and Claude Review sheets of the trigger workbook', 'Mr. Advocate'],
  ['2', 'Questions and key written; declaration filled; sent as one workbook', 'Writer (owner / Mr. Advocate)'],
  ['3', 'Our checks (section 11.2, items 1 to 4) and report listing any fixes', 'Claude'],
  ['4', 'Key review and corrections', 'Mr. Advocate, writer'],
  ['5', 'Replacements from reserves; final recount; seal and fingerprint', 'Claude'],
  ['6', 'Fix-test rules frozen; the three changes coded and pre-checked on the old questions (under $1)', 'Claude (owner approved the spend)'],
  ['7', 'One search; pack built (about 60 chats)', 'Claude'],
  ['8', 'Marking by ChatGPT and Gemini; replies returned exactly as received', 'J and S (owner forwards)'],
  ['9', 'Scoring in two stages (marks first, key second); plain-terms report; Mr. Advocate reads every Misleading passage and a random 20 others', 'Claude, Mr. Advocate'],
]));
C.push(gap());

// ---------------------------------------------------------------- 14
C.push(h1('14. Checklist for the writer (tick before sending)'));
const checks = [
  '30 scored-and-control questions present (27 + 3), plus up to 3 reserves marked with a domain.',
  'Domain counts exactly A3 B3 C3 D2 E3 F3 G3 H3 I2 J2 K3.',
  'At least 6 everyday, 6 legal, 6 narrative among the 27; Hinglish (if any) tagged.',
  'At least 6 NEW-code, 6 OLD-code, the rest with no section number.',
  'At least 4 currency traps, each with older ruling, change, current authority.',
  'At least 10 of the 27 turn on law from 2017 or later.',
  'At least 14 Act-concerning questions covering at least 10 of the 13 Acts; NDPS, NI, PWDVA, POCSO at least twice each.',
  'At least 8 questions with no listed Act.',
  'At least 8 look-alikes, each with a named neighbour regime; at least 3 of them never name the Act; at least 2 twin pairs, cross-referenced.',
  'Controls K1, K2, K3 present; K2 checked to have no Supreme Court answer on or before 30 June 2026.',
  'No case names, personal names, case numbers or addresses in any question.',
  'No question copies or rewords an earlier one.',
  'Every question has one answerable core issue; none asks for an outcome prediction.',
  'Every primary authority is a Supreme Court judgment decided on or before 30 June 2026.',
  'Every key lists all other acceptable authorities.',
  'Every key states the applicable code (IPC/BNS etc.) and how it was verified; secondary-only items marked G and listed under To verify.',
  'Act tags were decided from the law, not from the wording.',
  'Declaration sheet complete; AI use disclosed; no chatbot or search tool was run on the questions; nobody else has seen them.',
];
checks.forEach(c => C.push(new Paragraph({ spacing: { after: 50 }, children: [t('☐  ' + c)] })));

// ---------------------------------------------------------------- 15
C.push(h1('15. Plain-terms glossary'));
C.push(table([2400, 6626], ['Term', 'Meaning'], [
  ['Look-alike', 'A question under a special Act whose wording also fits ordinary law, so the search may return the wrong kind of law.'],
  ['Twin pair', 'Two questions with similar facts, one under the special Act and one under general law.'],
  ['Currency trap', 'The first ruling a search finds was later overruled, narrowed or replaced.'],
  ['Index gap', 'The right Supreme Court judgment is not in our collection, so the search cannot find it.'],
  ['Control', 'A question the collection should not be able to answer; the search should not look confident.'],
  ['Primary / acceptable authority', 'The best judgment, and every other judgment that would also be a right answer.'],
  ['Sealing', 'Fixing the questions and the key with a fingerprint before any search, so nothing can be changed afterwards.'],
  ['Hash (fingerprint)', 'A short code that changes if even one letter of the file changes.'],
  ['Floor', 'A minimum quality figure the search must meet before the next step.'],
  ['Named-Act boost', 'A small lift for judgments that are about the Act the question names.'],
  ['LLM-judged', 'Marked by AI tools (ChatGPT, Gemini), not by a lawyer.'],
]));

const doc = new Document({
  creator: 'Recourse project', title: 'Rules and Guidelines for the New Test Questions',
  styles: { default: { document: { run: { font: FONT, size: 21 } } } },
  numbering: { config: [
    { reference: 'bul', levels: [{ level: 0, format: LevelFormat.BULLET, text: '•', alignment: AlignmentType.LEFT, style: { paragraph: { indent: { left: 540, hanging: 270 } } } }, { level: 1, format: LevelFormat.BULLET, text: '–', alignment: AlignmentType.LEFT, style: { paragraph: { indent: { left: 1080, hanging: 270 } } } }] },
    ...['num', 'n1', 'n2'].map(r => ({ reference: r, levels: [{ level: 0, format: LevelFormat.DECIMAL, text: '%1.', alignment: AlignmentType.LEFT, style: { paragraph: { indent: { left: 540, hanging: 360 } } } }] })),
  ] },
  sections: [{
    properties: { page: { size: { width: 11906, height: 16838 }, margin: { top: 1300, bottom: 1300, left: 1440, right: 1440 } } },
    footers: { default: new Footer({ children: [new Paragraph({ alignment: AlignmentType.CENTER, children: [new TextRun({ text: 'New test questions: rules and guidelines (private) - page ', font: FONT, size: 16, color: '7F7F7F' }), new TextRun({ children: [PageNumber.CURRENT], font: FONT, size: 16, color: '7F7F7F' })] })] }) },
    children: C,
  }],
});
Packer.toBuffer(doc).then(buf => { fs.writeFileSync(process.argv[2], buf); console.log('written', process.argv[2], buf.length); });
