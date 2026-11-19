#!/usr/bin/env python3
"""
Module: qa_manuscript
Purpose: Check the manuscript against Jev-prompt.md rules (citations per paragraph, reference cross-check,
         caption citations, no em/en dash, abstract length). Exits non-zero on any failure.
Author: Dr. Arli Aditya Parikesit
Date: 2026
"""
import os, re, sys, zipfile
from docx import Document

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PATH = sys.argv[1] if len(sys.argv) > 1 else os.path.join(ROOT, "jev-bioinformatics-Manuscript-Arli.docx")
doc = Document(PATH)
HEAD = {"Abstract", "INTRODUCTION", "MATERIALS AND METHODS", "RESULTS", "DISCUSSION",
        "CONCLUSION AND RECOMMENDATIONS", "ACKNOWLEDGEMENTS", "REFERENCES"}
section, body, refs, errors = None, [], [], []
for p in doc.paragraphs:
    t = p.text.strip()
    if t in HEAD:
        section = t; continue
    if not t:
        continue
    if section == "REFERENCES":
        refs.append(t)
    elif section in {"INTRODUCTION", "MATERIALS AND METHODS", "RESULTS", "DISCUSSION"}:
        is_sub = all(r.bold for r in p.runs if r.text.strip())
        is_cap = re.match(r"^(Table|Figure|Pseudocode) \d+\.", t)
        is_eq = p._p.find(".//{http://schemas.openxmlformats.org/officeDocument/2006/math}oMath") is not None
        if not (is_sub or is_cap or is_eq):
            body.append((section, t))
    elif section == "Abstract" and not t.startswith("Keywords"):
        n = len(t.split())
        if n > 300: errors.append(f"abstract {n} words > 300")

CIT = re.compile(r"\(([^()]*\d{4}[^()]*)\)|([A-Z][\w' -]+?(?: et al\.| and [A-Z][\w-]+)?) \((\d{4})\)")
for s, t in body:
    if not CIT.search(t): errors.append(f"[{s}] paragraph without citation: {t[:70]}")

# reference keys: first-author surname (or organisation) + year
keys = []
for r in refs:
    ym = re.search(r"\b(19|20)\d{2}\b", r)
    if not ym:
        errors.append(f"reference without a year: {r[:70]}"); continue
    y = ym.group(0)
    name = r.split(" ")[0] if not r.startswith(("van den", "Python Software", "Gemini Team", "TypeSafe AI")) else \
        {"van": "van den Hurk", "Python": "Python Software Foundation", "Gemini": "Gemini Team", "TypeSafe": "TypeSafe AI"}[r.split(" ")[0]]
    keys.append((name, y, r))
text = " ".join(t for _, t in body)
for name, y, r in keys:
    # \b stops "Li" matching "Lipman"; the optional "(" accepts the narrative form "Chow (1970)"
    if not re.search(r"\b" + re.escape(name) + r"\b[^()]{0,40}?\(?" + y, text):
        errors.append(f"reference not cited in body: {name} {y}")
# in-text citations resolve to a reference
for grp in re.findall(r"\(([^()]*\d{4}[a-z]?)\)", text):
    for c in grp.split(";"):
        c = c.strip()
        m = re.match(r"(.+?)(?: et al\.| and [\w' -]+)?,? (\d{4})$", c)
        # lower-case surname particles ("van den Hurk") are citations too; anything else in lower case is prose
        if not m or not re.match(r"^(?:[A-Z]|van |von |de |del |der |di |da |le |la )", c) or "Eq" in c: continue
        if not any(c.startswith(n) and y == m.group(2) for n, y, _ in keys):
            errors.append(f"citation without reference: {c}")
# captions and equations cited in body text
full = text
for lab in ["Table 1", "Table 2", "Table 3", "Figure 1", "Figure 2", "Pseudocode 1", "Pseudocode 2"]:
    if lab not in full: errors.append(f"{lab} not cited in text")
for i in range(1, 7):
    if f"Eq. ({i})" not in full and f"Eq. {i})" not in full: errors.append(f"Eq. ({i}) not cited in text")
# dashes anywhere in document XML (body, tables, captions)
xml = zipfile.ZipFile(PATH).read("word/document.xml").decode("utf8")
for ch, nm in (("—", "em dash"), ("–", "en dash")):
    if ch in xml: errors.append(f"{xml.count(ch)} {nm}(es) found")
# invisible unicode marks
for ch in ["​", "‌", "‍", "⁠", "﻿", "­", " "]:
    if ch in xml: errors.append(f"invisible char U+{ord(ch):04X} found")

words = sum(len(p.text.split()) for p in doc.paragraphs)
print(f"paragraphs checked: {len(body)}, references: {len(refs)}, total words (excl. tables): {words}")
print("\n".join(errors) if errors else "ALL CHECKS PASSED")
sys.exit(1 if errors else 0)
