# Probe za izbor B4 i B5

Skripte su pokrenute iz scratchpad-a, uz privremeni keš, i ne menjaju repo. Pokreću se sa `python <skripta> <putanja do repoa> <scratch dir> ...`. Rezultati su prepisani u `docs/maxlvl-specs.md` (tabele „Drugi krug“ i „B4b“).

- `judge_sweep.py`: model × upit za da/ne judge (eval + holdout).
- `judge_sweep2.py`: izvlačenje sa proverom za gemma, qwen i mistral, i judge preko verovatnoće „yes“ (logprob) sa pragovima 0.5, 0.2, 0.05 i 0.01.
- `judge_sweep3.py`: popravke provere izvlačenja i unija judge-a (eval + holdout + test 1, koji je tada već viđen).
- `gen_sweep.py`: upit i model za generisanje, mereno brojem sadržajnih reči kojih nema u pasusima.
