# Evidence Task 15: API Gateway Facade & Dashboard Summary

## Perintah Dijalankan
```bash
DCIM_RUNTIME_ROOT=/tmp .venv/bin/python -m unittest tests/phase3/test_api_gateway.py
```

## Exit Code
`0`

## Hasil Happy Path
```
......
----------------------------------------------------------------------
Ran 6 tests in 0.145s

OK
```
Gateway proxy menyuntikkan `X-Internal-Token` untuk panggillan upstream ke asset-repository dan cmdb, mengembalikan 502 tersanitasi saat ConnectError, fail-closed saat env var upstream tidak diset, dan menyajikan `GET /api/v1/dashboard/summary`.

## Hasil Failure-Mutation & Restore
1. Mutation: Unset env `ASSET_REPOSITORY_URL` saat startup.
2. Test run: `create_app()` raises `UpstreamConfigurationError` (fail-closed).
3. Restore: Env var diset kembali -> Green.
