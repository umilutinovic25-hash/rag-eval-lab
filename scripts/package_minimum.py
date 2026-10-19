"""Build the mandatory M5 checkpoint plus its evidence, without advanced models."""
from io import BytesIO
from pathlib import Path
import subprocess
import zipfile

ROOT = Path(__file__).resolve().parents[1]
TARGET = ROOT / 'deliverables' / 'week07-M5-minimum.zip'


def build():
    archive = subprocess.run(['git', 'archive', '--format=zip', '45b8172'], cwd=ROOT, check=True, capture_output=True).stdout
    report = (ROOT / 'REPORT_BEFORE_AFTER.md').read_text().split('## 12.')[0]
    start = report.index('> Obavezni deo')
    end = report.index('\n\n', start)
    report = report[:start] + '> Ovaj paket sadrži samo M5 checkpoint 45b8172. Napredni eksperimenti su odvojeni u glavnom repozitorijumu.' + report[end:]
    report = report.replace('; dalji krugovi do `54358d4`', '').replace(' (poslednje ažuriranje 2026-10-19: odeljak 22)', '')
    report += '''\n## Dokazi

Svi obavezni dokazi su u `evidence/`: `before.json`, `after.json`, `compare.txt`, `change.diff`, CLI izlazi za E06 i izlazi testova pre/posle. Specifikacija je u `docs/change-spec.md` (commit `2ceaced`), implementacija u commitu `45b8172`. Napredni eksperimenti (odeljci 12 i dalje u glavnom repozitorijumu) nisu deo ovog paketa.
'''
    instructions = '''# Nedelja 7 — obavezni eksperiment M5

Ovaj paket je kod checkpointa 45b8172, a ne napredni HEAD. Nema embeddinga, Ollama ni LLM-a.

1. Python 3.12: python3.12 -m venv .venv
2. Aktivacija: . .venv/bin/activate (Windows: .venv\\Scripts\\activate)
3. pip install -r requirements.txt
4. python -m pytest — očekivano 19 passed
5. python -m src.eval_runner --out results/reproduced-after.json — očekivano 7/12
6. python -m src.eval_compare evidence/before.json results/reproduced-after.json
   Očekivano Fixed E06, Regressed none, promenjeno samo CURRENT_ONLY, isti SHA-256.
7. python -m src.cli --question "How many days per week can I work remotely?" --show-retrieved

REPORT_BEFORE_AFTER.md je obavezni izveštaj. evidence/ sadrži pre/posle JSON, poređenje,
diff, testove i CLI provere. docs/change-spec.md prethodi implementaciji u istoriji repoa.

Projekat je poslat na pregled para (odeljak 9 izveštaja).
Autor je Uroš Milutinović, koji je radio samostalno i lično proverio sve rezultate.
Ovo nije zvanični šablon tutora.
'''
    TARGET.parent.mkdir(exist_ok=True)
    with zipfile.ZipFile(BytesIO(archive)) as source, zipfile.ZipFile(TARGET, 'w', zipfile.ZIP_DEFLATED) as out:
        for info in source.infolist():
            if not info.is_dir():
                out.writestr(info.filename, source.read(info.filename))
        for name in ['before.json', 'after.json', 'compare.txt', 'change.diff', 'cli-E06-before.txt', 'cli-E06-after.txt', 'pytest-before.txt', 'pytest-after.txt']:
            out.write(ROOT / 'evidence' / name, f'evidence/{name}')
        out.write(ROOT / 'docs/sablon-izvestaj-pre-posle.md', 'docs/sablon-izvestaj-pre-posle.md')
        for name in ['NEDELJNI_IZVESTAJ_UROS.md', 'MOJ_KOMENTAR.md']:
            out.write(ROOT / 'deliverables' / name, name)
        out.write(ROOT / 'evidence/upgrade/human-confirmation-21.json', 'evidence/human-confirmation-21.json')
        out.writestr('REPORT_BEFORE_AFTER.md', report)
        out.writestr('PRED_PREDAJU.md', instructions)
    print(TARGET)


if __name__ == '__main__':
    build()
