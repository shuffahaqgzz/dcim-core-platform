# Known Limitations

- Development dijalankan satu developer pada satu VM; bus factor satu dan tidak ada independent Dev approval.
- Public repository tidak dapat menyimpan runtime data, credential, source inventory, atau operational evidence.
- Production-connected Development belum diaktifkan; source authorization dan read-only identity masih private prerequisites.
- Kafka single-broker direncanakan hanya untuk Development; tidak ada HA atau durability claim Production.
- SNMPv2c merupakan temporary technical debt; future exception memerlukan source-IP ACL, short retention, dan migration plan ke SNMPv3 authPriv.
- Tidak ada HA, Production SLA, Production claim, atau dukungan 24x7.
- Ownership tim Staging, retention final, security contact final, serta repository license masih TBD.
- Phase 0 tidak membuktikan deployability application stack, recovery stack, throughput, atau operational source behavior.
- Phase 1 foundation hanya membuktikan lifecycle synthetic `dcim-build`; hasilnya tidak membuktikan P1/P2 vertical slice, Kafka backup, HA, Staging, atau Production readiness.
