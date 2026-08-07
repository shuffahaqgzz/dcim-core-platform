# Evidence Task 17: Workflow Service & m0004 Migration

## Perintah Dijalankan
```bash
DCIM_RUNTIME_ROOT=/tmp .venv/bin/python -m unittest tests/phase3/test_workflow.py tests/phase3/test_workflow_safety.py
```

## Exit Code
`0`

## Hasil Happy Path
```
.........
----------------------------------------------------------------------
Ran 9 tests in 0.210s

OK
```
Migration m0004 (`phase2.workflow_drafts` dan role `dcim_workflow_rw`) berhasil diterapkan. Service menyajikan draft dan simulation-approval saja. AST negative test membuktikan tidak ada kapabilitas eksekusi subprocess/socket/network.

## Hasil Failure-Mutation & Restore
1. Mutation: Sisipkan `import subprocess` ke dalam `services/workflow/src/dcim_workflow/main.py`.
2. Test run: `test_workflow_package_has_no_execution_or_network_imports` FAILS.
3. Restore: `git checkout services/workflow/src/dcim_workflow/main.py` -> Green.
