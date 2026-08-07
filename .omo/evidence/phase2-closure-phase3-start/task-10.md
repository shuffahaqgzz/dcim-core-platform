# Evidence Task 10: Extended phase2-check gate (8 -> 11 stages)

## Perintah Dijalankan
```bash
DCIM_RUNTIME_ROOT=/tmp .venv/bin/python -m unittest tests/phase2/test_phase2_check.py tests/phase2/test_latency.py
```

## Exit Code
`0`

## Hasil Happy Path
```
.....................
----------------------------------------------------------------------
Ran 21 tests in 0.160s

OK
```
`scripts/phase2/check.py` diperluas dengan 3 stage baru setelah 8 stage lama (total 11 stage): `topic-verify`, `stream-roundtrip`, dan `latency-assert`.

## Hasil Failure-Mutation & Restore
1. Mutation: `sed -i 's/5000/0/' scripts/phase2/latency.py`
2. Test run: `DCIM_RUNTIME_ROOT=/tmp .venv/bin/python -m unittest tests/phase2/test_latency.py` -> FAILS (`AssertionError: p95 latency threshold exceeded`).
3. Restore: `git checkout scripts/phase2/latency.py` -> Green.
