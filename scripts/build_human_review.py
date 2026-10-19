"""Build review/human-review.html: a standalone page where a person checks the system's answers and the Serbian translation.

    python scripts/build_human_review.py

Reads cached answers (no model calls when the scratch caches already hold them), embeds everything in one HTML file and
needs no network. The reviewer's choices are exported as JSON; src/human_agreement.py compares them with the AI-written labels.
"""

import json
import random
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.chunking import build_chunks  # noqa: E402
from src.corpus import load_corpus  # noqa: E402
from src.candidate_runner import corpus_chunks  # noqa: E402
from src.eval_runner import load_eval_set  # noqa: E402
from src.llm import is_yes_no_question  # noqa: E402
from src.rag import QUOTE_PREFIX, build_grounded_answer  # noqa: E402
from src.retrieval_metrics import EVAL_DIR, SETS  # noqa: E402
from src.scratch import use_scratch_caches  # noqa: E402

OTHER_ANSWERS = 20  # non yes/no answers added to the yes/no ones
OUT = ROOT / "review" / "human-review.html"


def answers() -> list[dict]:
    use_scratch_caches(ROOT / "results" / "scratch-final6")
    base = build_chunks(load_corpus())
    yes_no, other = [], []
    for set_name in ("test3", "test4", "test5", "test6"):
        chunks = corpus_chunks(set_name, base)
        text = {c.chunk_id: c.text for c in chunks}
        for item in load_eval_set(EVAL_DIR / SETS[set_name]):
            if item["expected_behaviour"] != "answer":
                continue
            result = build_grounded_answer(item["question"], chunks)
            if result.refused:
                continue
            sentence = "\n".join(l for l in result.answer.splitlines() if not l.startswith(QUOTE_PREFIX)).strip()
            row = {"id": f"{set_name}:{item['id']}", "question": item["question"], "answer": sentence,
                   "passages": [text[c] for c in result.citations], "fallback": result.generation_fallback_reason}
            (yes_no if is_yes_no_question(item["question"]) else other).append(row)
    random.Random(7).shuffle(other)
    return yes_no + other[:OTHER_ANSWERS]


def translation() -> list[dict]:
    data = json.loads((ROOT / "data" / "sr-handbook.json").read_text())
    english = {c.chunk_id: c.text for c in build_chunks(load_corpus())}
    return [{"id": cid, "en": english[cid], "sr": item["text"]} for cid, item in data["chunks"].items()]


PAGE = """<!doctype html>
<html lang="sr"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Ljudska provera izvor.</title>
<style>
:root{--bg:#fff;--fg:#1c2b25;--muted:#51645b;--line:#d5e0da;--green:#123c35;--soft:#eef4f0;--bad:#8a2d1f;--ok:#1d6a4a}
@media (prefers-color-scheme:dark){:root{--bg:#10201b;--fg:#e8f0ec;--muted:#a6b9b0;--line:#2c4a40;--green:#7fd1b2;--soft:#173229;--bad:#ff9d8a;--ok:#7fd1b2}}
body{margin:0;background:var(--bg);color:var(--fg);font:16px/1.5 system-ui,sans-serif}
main{max-width:860px;margin:0 auto;padding:16px}
h1{font-family:Georgia,serif;font-size:26px;margin:8px 0}
.bar{position:sticky;top:0;background:var(--bg);border-bottom:1px solid var(--line);padding:10px 0;display:flex;gap:10px;flex-wrap:wrap;align-items:center}
button,input,select{font:inherit;color:inherit;background:var(--soft);border:1px solid var(--line);border-radius:8px;padding:8px 12px;min-height:44px}
button.on{background:var(--green);color:var(--bg);border-color:var(--green)}
.card{border:1px solid var(--line);border-radius:12px;padding:14px;margin:14px 0}
.q{font-family:Georgia,serif;font-size:19px;margin:0 0 8px}
.a{background:var(--soft);padding:10px;border-radius:8px;margin:8px 0;white-space:pre-wrap}
.p{color:var(--muted);font-size:14px;border-left:3px solid var(--line);padding-left:10px;margin:6px 0}
.row{display:flex;gap:8px;flex-wrap:wrap;margin-top:10px}
.muted{color:var(--muted);font-size:14px}.tag{font-size:12px;color:var(--muted)}
textarea{width:100%;box-sizing:border-box;font:inherit;color:inherit;background:var(--bg);border:1px solid var(--line);border-radius:8px;padding:8px;min-height:44px}
</style></head><body><main>
<h1>Ljudska provera</h1>
<p class="muted">Dva zadatka. Rezultat se čuva u ovom browseru dok radiš; na kraju klikni „Preuzmi JSON“ i pošalji mi fajl. Ništa se ne šalje na mrežu.</p>
<div class="bar">
 <label>Ime recenzenta <input id="who" autocomplete="name"></label>
 <button id="t1" class="on">1. Odgovori (<span id="n1"></span>)</button>
 <button id="t2">2. Prevod (<span id="n2"></span>)</button>
 <button id="dl">Preuzmi JSON</button><span id="prog" class="muted" role="status"></span>
</div>
<section id="s1"></section><section id="s2" hidden></section>
</main>
<script>
const ANSWERS=__ANSWERS__, TRANS=__TRANS__;
const KEY="izvor.human-review.v1"; let state={who:"",answers:{},trans:{}};
try{state=Object.assign(state,JSON.parse(localStorage.getItem(KEY)||"{}"))}catch(e){}
const save=()=>{try{localStorage.setItem(KEY,JSON.stringify(state))}catch(e){}; prog()};
const $=s=>document.querySelector(s);
const esc=t=>t.replace(/[&<>]/g,c=>({"&":"&amp;","<":"&lt;",">":"&gt;"}[c]));
function btn(group,id,val,label,store){const on=(store[id]||{}).v===val;return `<button data-g="${group}" data-id="${id}" data-v="${val}" class="${on?'on':''}" aria-pressed="${on}">${label}</button>`}
function render(){
 $("#n1").textContent=ANSWERS.length;$("#n2").textContent=TRANS.length;
 $("#s1").innerHTML=ANSWERS.map((a,i)=>`<div class="card"><div class="tag">${i+1}/${ANSWERS.length} · ${a.id}${a.fallback?' · prikazani originalni odlomci':''}</div>
 <p class="q">${esc(a.question)}</p><div class="a">${esc(a.answer)}</div>
 ${a.passages.map(p=>`<div class="p">${esc(p)}</div>`).join("")}
 <div class="row">${btn("a",a.id,"ok","Tačno",state.answers)}${btn("a",a.id,"wrong","Netačno",state.answers)}${btn("a",a.id,"partial","Delimično / nejasno",state.answers)}</div>
 <textarea data-c="a" data-id="${a.id}" placeholder="Komentar (nije obavezno)" aria-label="Komentar uz ${a.id}">${esc((state.answers[a.id]||{}).c||"")}</textarea></div>`).join("");
 $("#s2").innerHTML=TRANS.map((t,i)=>`<div class="card"><div class="tag">${i+1}/${TRANS.length} · ${t.id}</div>
 <div class="p" lang="en">${esc(t.en)}</div><div class="a" lang="sr">${esc(t.sr)}</div>
 <div class="row">${btn("t",t.id,"ok","Prevod je dobar",state.trans)}${btn("t",t.id,"fix","Treba ispraviti",state.trans)}</div>
 <textarea data-c="t" data-id="${t.id}" placeholder="Predlog ispravke" aria-label="Predlog ispravke za ${t.id}">${esc((state.trans[t.id]||{}).c||"")}</textarea></div>`).join("");
 $("#who").value=state.who||""; prog();
}
function prog(){const a=Object.keys(state.answers).filter(k=>state.answers[k].v).length,t=Object.keys(state.trans).filter(k=>state.trans[k].v).length;$("#prog").textContent=`Urađeno: odgovori ${a}/${ANSWERS.length}, prevod ${t}/${TRANS.length}`}
document.addEventListener("click",e=>{const b=e.target.closest("button[data-g]");if(!b)return;const s=b.dataset.g==="a"?state.answers:state.trans;s[b.dataset.id]=Object.assign(s[b.dataset.id]||{},{v:b.dataset.v});save();const y=window.scrollY;render();window.scrollTo(0,y)});
document.addEventListener("input",e=>{if(e.target.id==="who"){state.who=e.target.value;save();return}const c=e.target.dataset.c;if(!c)return;const s=c==="a"?state.answers:state.trans;s[e.target.dataset.id]=Object.assign(s[e.target.dataset.id]||{},{c:e.target.value});save()});
$("#t1").onclick=()=>{$("#s1").hidden=false;$("#s2").hidden=true;$("#t1").classList.add("on");$("#t2").classList.remove("on")};
$("#t2").onclick=()=>{$("#s2").hidden=false;$("#s1").hidden=true;$("#t2").classList.add("on");$("#t1").classList.remove("on")};
$("#dl").onclick=()=>{const blob=new Blob([JSON.stringify({reviewer:state.who,created_at:new Date().toISOString(),answers:state.answers,translation:state.trans},null,1)],{type:"application/json"});const a=document.createElement("a");a.href=URL.createObjectURL(blob);a.download="human-review.json";a.click()};
render();
</script></body></html>
"""


def main() -> None:
    page = PAGE.replace("__ANSWERS__", json.dumps(answers(), ensure_ascii=False)).replace("__TRANS__", json.dumps(translation(), ensure_ascii=False))
    OUT.write_text(page, encoding="utf-8")
    print(f"wrote {OUT} ({len(page) // 1024} KB)")


if __name__ == "__main__":
    main()
