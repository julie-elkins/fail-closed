---
name: humanizer
description: >-
  Strip the tells of machine-written prose from a draft without flattening it into corporate
  mush. Use on anything with a reader — a README, a design doc, a pull request description, a
  wiki page, a LinkedIn post, a résumé bullet, a meeting note. It works by SCANNING for structural
  patterns and triaging each hit in context, never by running a blacklist of words. It does
  NOT make prose shorter, simpler or friendlier, and it must not touch identifiers, wire
  values, quoted output, or a dense technical register the repo uses on purpose. It cannot
  tell you whether the content is correct — use /fact-check for that.
---

# Humanizer

The goal is **not** "sounds human". The goal is **sounds like the author wrote it**: dense,
arguing the non-obvious call, naming what the wrong choice would have cost. Prose that is
merely inoffensive has failed this skill as surely as prose full of "delve".

If the project records the author's register anywhere, read it first — it tells you what this
particular author's register actually is, which is the thing you are protecting.

## Scan, don't hand-list

A hand-built word list is the wrong instrument and always has been. It misses whole
families, misses every capitalised form, and its hits are mostly false. **Scan for
structural patterns instead**, then triage each hit against the sentence it's in.

The patterns worth scanning for:

- **Empty intensifiers and hedges** doing no work: `very`, `quite`, `really`, `truly`,
  `arguably`, `it's worth noting that`, `it's important to remember`.
- **Announced structure** — sentences about the text rather than the subject: "In this
  section we will…", "Let's dive into…", "First, let's understand…". Delete the
  announcement, keep the content.
- **The rule-of-three tic.** Three parallel adjectives or clauses where the third adds
  nothing: "robust, scalable, and maintainable". Keep the one that's load-bearing.
- **Symmetrical contrast frames**: "It's not just X — it's Y", "This isn't about X, it's
  about Y". One is fine and can be sharp; three in a document is a tell.
- **Nominalizations** hiding a verb: "performs validation of" → "validates"; "provides
  support for" → "supports".
- **Closing summary paragraphs** that restate what was just said. Cut them entirely.
- **Uniform sentence length.** Real prose varies. A page where every sentence runs 18–24
  words reads synthetic even when every word is right.
- **Hollow superlatives**: "seamlessly", "effortlessly", "cutting-edge", "best-in-class",
  "game-changing", "leverage" as a verb.

## Triage every hit before touching it — three categories

This is the step a word-list approach skips, and skipping it is how a sweep breaks a repo:

1. **Prose** — the reader-facing sentence. Fair game. Rewrite it.
2. **Identifier** — a function, class, variable, file, test or skill name. **Never touch.**
   `validate_technical_accuracy` is not "corporate"; it's a symbol. Renaming it from a prose
   sweep breaks imports, and in a repo that pins documentation citations with a test it
   breaks that test from a Markdown file.
3. **Wire value / quoted output** — a JSON key, an enum member, a log line, a schema
   `description` string a test pins, a pasted tool reply, a citation. **Never touch.** A
   README example in these repos is a real recorded run; editing its text towards what reads
   better makes the README lie, and some repos have a test that exists because of exactly
   that.

When a hit is ambiguous, leave it and say so. A false negative costs a slightly clunky
sentence; a false positive costs a broken build or a document that misstates a measurement.

## The em dash question, answered specifically

Do **not** apply a blanket em-dash rule. It splits by destination:

- **Inside a repo**, if house style is `--` rather than `—`, converting is correct and may
  be *required*: at least one repo has an invariant test that caught a drift which was
  nothing but an em dash against `--`. Check the repo's CLAUDE.md for which it uses.
- **In outward prose** (LinkedIn, a résumé, an email), the em dash is fine and often the
  right punctuation. Stripping it because "AI uses em dashes" is cargo cult, and the
  replacement is usually worse.

Never do the conversion the other way inside a repo.

## What to preserve, actively

A dense technical register is deliberate house style, not padding, and the reflex to
"simplify" it is the main way this skill does damage:

- **Dense docstrings that argue each nontrivial decision in place.** Keep them.
- **Naming what the wrong choice would have cost.** That is the most valuable sentence
  pattern in these repos. Never cut it as redundant.
- **`OBSERVED` / `MEASURED` / `MODELLING ASSUMPTION` / `NOT ESTABLISHED` labels and their
  dates.** These are provenance, not verbiage.
- **Emphatic capitals on load-bearing claims.** They mark the sentence a reader must not
  skim. Lowercasing them is a real loss.
- **Long sentences that earn it.** Length is not a defect; unvarying length is.

## Output

Return a **diff or a marked-up version**, never a silently rewritten file — the author needs
to see what changed to judge whether a change cost something. Alongside it, list:

- hits you changed, grouped by pattern;
- hits you found and **deliberately left**, with the reason (usually: identifier, wire
  value, or load-bearing register);
- anything ambiguous you want their call on.

If the draft is already in the author's voice, say so and change nothing. A skill that
always finds work is one that invents it.
