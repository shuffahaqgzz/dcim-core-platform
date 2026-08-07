# Opsi Resolusi OD-06 — Inkonsistensi Penerimaan Apache-2.0

- **Disusun:** 2026-08-03
- **Pemilik keputusan:** `shuffahaqgzz`
- **Catatan keputusan:** [OD-06](OPEN-DECISIONS.md), diterima 2026-07-27; [ADR-0019](../adr/0019-apache-2-0-repository-license.md)
- **Scope:** decision brief saja. Dokumen ini tidak menambah lisensi, tidak
  mengubah status keputusan, tidak mengotorisasi publication image, dan tidak
  mengubah batas public/private.

## Keputusan yang diperlukan

Pilih salah satu jalur di bawah. **Direkomendasikan: Opsi A, diimplementasikan
sebagai follow-up yang scoped secara sengaja dan mencakup code, konfigurasi,
test, serta dokumentasi current-facing.** Opsi A adalah satu-satunya pilihan
yang menjadikan keputusan owner yang sudah diterima benar secara mekanis sambil
mempertahankan larangan terpisah untuk publish atau distribute derived images.

## State saat ini dan inkonsistensi

Catatan keputusan otoritatif menyatakan bahwa OD-06 adalah **ACCEPTED
2026-07-27 — Apache-2.0** ([OPEN-DECISIONS.md:12](OPEN-DECISIONS.md#L12));
ADR-0011 berstatus `Accepted` dan mengarahkan penambahan `LICENSE` dan `NOTICE`
di root repository, koreksi README, serta inventori komponen runtime non-
permissif yang menghadap adopter ([ADR-0019:30-41](../adr/0019-apache-2-0-repository-license.md#decision)).

`main` saat ini tidak dapat menghormati acceptance tersebut:

1. File `LICENSE` dan `NOTICE` di root repository tidak ada.
2. README masih menyatakan tidak ada open-source license yang dipilih dan OD-06
   tetap open ([README.md:64](../../README.md#L64));
   [LICENSE-DECISION.md:1-19](LICENSE-DECISION.md) seluruhnya adalah instruksi
   state OPEN.
3. Disposition manifest derived-image menyatakan `"od_06": "OPEN"`
   ([license-dispositions.json:4-12](../../deploy/compose/derived-images/license-dispositions.json#L4-L12)).
   `foundation_supply_chain.py` menolak nilai lain
   ([scripts/foundation_supply_chain.py:239-254](../../scripts/foundation_supply_chain.py#L239-L254)).
4. `foundation_images.py` menulis `OD-06 OPEN` ke metadata evidence segar dan
   upgraded
   ([scripts/foundation_images.py:370-380](../../scripts/foundation_images.py#L370-L380),
   [577-585](../../scripts/foundation_images.py#L577-L585));
   `foundation_supply_chain.py` juga melakukan hal yang sama
   ([448](../../scripts/foundation_supply_chain.py#L448)).
5. Test fixtures secara sengaja meng-encode kontrak OPEN-only yang mustahil:
   `tests/test_foundation_supply_chain.py:31` dan
   `tests/test_foundation_images.py:86`.
6. Stale-document research mengidentifikasi 20 file dan 27+ lokasi current-state.
   Sebagian adalah historical evidence: harus dipertahankan sebagai evidence
   tanggal observasi dan dianotasi, bukan ditulis ulang seolah sejarah berubah.

Lisensi repository dan lisensi komponen runtime/image adalah berbeda.
`deploy/compose/images.json:5` dengan benar menyatakan bahwa review runtime-
component tidak sendiri menyelesaikan OD-06; Grafana tetap menjadi item review
AGPL eksplisit. ADR-0019 juga mempertahankan constraint publication ADR-0013
([ADR-0019:39-41](../adr/0019-apache-2-0-repository-license.md#L39-L41)).
Oleh karena itu, menerima Apache-2.0 **tidak mengotorisasi** publication atau
Distribution derived-image.

## Ketersediaan commit dan penilaian cherry-pick

`chore/agent-docs-drift` berisi `0dce268ee3fcc01b9e310de277cef7af44647e0a`
(`chore(docs): Apache-2.0 license, reading checklist, gate rename, stale-doc
fixes`). Commit tersebut menambahkan `LICENSE` (teks Apache-2.0 standar),
`NOTICE`, dan mengupdate README serta ADR-0011. Commit tersebut juga mengubah
materi agent-reading, safety-skill, Codex prompt/setup, dan gate-naming yang
tidak terkait.

Commit tersebut bukan ancestor dari `main`. Simulasi three-way merge terhadap
`main` saat ini menunjukkan satu content conflict di `README.md` karena kedua
baris berubah sejak commit base: milestone text Phase 2 di `main` saat ini
berkonflik dengan milestone text Phase 1 yang sudah usang di commit tersebut.
Path lain merge dengan bersih. Oleh karena itu commit tersebut **tidak bisa
dicleanly cherry-pick sebagai satu commit**. Reuse mekanis yang aman adalah
cherry-pick/selectively apply hanya `LICENSE`, `NOTICE`, paragraf lisensi README
(sambil mempertahankan milestone text Phase 2 saat ini), dan koreksi state
ADR-0011; jangan mengimpor perubahan drift yang tidak terkait hanya untuk
menyelesaikan OD-06.

## Opsi resolusi

### Opsi A — Hormati keputusan Apache-2.0 yang diterima secara komprehensif

Tambahkan artifact dari `0dce268`, sinkronkan semua active assertion dan
reference current-facing, dan anotasi (bukan tulis ulang) historical evidence
yang dengan benar mencatat state OPEN sebelumnya.

**Perubahan mekanis yang diperlukan**

1. Tambahkan `LICENSE` dan `NOTICE` root menggunakan konten yang sudah direview
dari `0dce268`; konfirmasi independently pemegang copyright/NOTICE wording
sebelum merge.
2. Ubah `README.md:64`, `docs/governance/LICENSE-DECISION.md:1-19`, dan
`docs/adr/0011-public-repository-license-decision-pending.md:1-14` untuk
menggambarkan state accepted/superseded dan link ke ADR-0019, `LICENSE`, dan
`NOTICE`.
3. Ubah disposition contract di `scripts/foundation_supply_chain.py:239-254`
dari OPEN-only ke nilai accepted-state eksplisit (misalnya
`ACCEPTED-APACHE-2.0`), pertahankan revalidation trigger, dan pertahankan
`publication == false` dan `distribution == false`. Update generated evidence
strings di baris 448 dan tiga string ekuivalen di
`scripts/foundation_images.py:373,577,585`.
4. Update `deploy/compose/derived-images/license-dispositions.json:4-12` ke
nilai accepted-state dan tanggal acceptance yang dipilih; pertahankan scope
local-Development dan publication/distribution false. Update
`deploy/compose/images.json:5` sehingga membedakan repository licensing yang
sudah diterima dari runtime component obligations yang terpisah.
5. Update `tests/test_foundation_supply_chain.py:31` dan
`tests/test_foundation_images.py:86`, plus semua test yang mengassert error text
atau evidence string lama, untuk membuktikan accepted Apache-2.0 diizinkan dan
state OPEN/mismatch ditolak.
6. Update dokumen active ADR/plan/handover/current-state di bawah. Historical
evidence dipertahankan dengan anotasi bertanggal seperti: “Historical evidence;
OD-06 diterima pada 2026-07-27; lihat ADR-0019.”

**Keuntungan**

- Menjadikan acceptance otoritatif benar di file, policy enforcement, dan
generated evidence.
- Mencegah keputusan yang diterima ditolak oleh supply-chain gate.
- Menghapus pernyataan reuse-right dan “no license” yang menyesatkan dari
materi current-facing.
- Mempertahankan safety boundary yang lebih kuat: image publication/
distribution tetap false dan masih membutuhkan upstream-obligation review.

**Kerugian dan risiko**

- Review surface terbesar: 20 file/27+ lokasi yang didokumentasikan plus
perubahan code/config/test contract.
- Membutuhkan pembedaan sengaja antara fakta historis dan kebijakan saat ini;
replace massal buta akan merusak evidence.
- Wording `NOTICE` dan owner/copyright yang diklaim harus disetujui eksplisit
oleh owner.

**Blast radius**

- Consumer dan contributor repository mendapatkan ketentuan reuse Apache-2.0.
- Perilaku schema foundation qualification dan supply-chain evidence berubah;
image lock eksternal yang ada mungkin perlu divalidasi ulang/diupgrade karena
perubahan disposition digest.
- Tidak ada publication image Docker, registry push, Staging, Production,
connector, atau kemampuan runtime-write yang ditambahkan.

### Opsi B — Revert OD-06 ke OPEN sampai implementasi siap

Balikkan status register dan ADR sehingga file dan script saat ini kembali
mewakili state governing; jangan tambahkan `LICENSE` atau `NOTICE`.

**Perubahan mekanis yang diperlukan**

1. Ubah `docs/governance/OPEN-DECISIONS.md:12` dari ACCEPTED ke OPEN.
2. Ganti atau supersede `docs/adr/0019-apache-2-0-repository-license.md:3-4,30-41,79-83`
dengan catatan proposed/deferred yang secara eksplisit menyatakan implementasi
dan owner re-approval pending; restore ADR-0011 sebagai active pending record
atau tambahkan ADR superseding yang menjelaskan reversal.
3. Ubah `docs/adr/README.md:16,25` dan research decision summaries yang
menyebutkan OD-06 accepted sehingga tidak mengklaim acceptance.
4. Pertahankan `LICENSE-DECISION.md`, nilai `OPEN` di manifest, script, dan
test apa adanya; update dokumen stale apa pun yang mengassert Apache-2.0 sudah
diterima menjadi history “withdrawn/deferred” bertanggal.

**Keuntungan**

- Perubahan code/config terkecil; enforcement saat ini tetap internally
consistent.
- Menunda review ownership `NOTICE` dan repository-license rollout.

**Kerugian dan risiko**

- Bertentangan dengan arah owner yang tercatat kecuali owner secara eksplisit
membalikkannya.
- Membuka kembali keputusan yang primary reasons-nya sudah tercatat dalam ADR
Accepted.
- Terus menolak reuse rights yang jelas dan menunda klaim contribution/
publication.

**Blast radius**

- Hanya governance dan decision history; perilaku supply-chain saat ini tetap
tidak berubah.
- Tidak mengubah constraint non-publication/distribution derived-image.

### Opsi C — Minimal accepted-state repair; tunda historical annotations

Merge/tambahkan `LICENSE` dan `NOTICE`, koreksi file current-facing kritis dan
executable policy, tetapi tunda anotasi historical evidence dan archival plan/
handover non-kritis ke follow-up yang ter-track.

**Perubahan mekanis yang dilakukan sekarang**

1. Terapkan perubahan Opsi A untuk `LICENSE`, `NOTICE`, `README.md:64`,
`docs/governance/LICENSE-DECISION.md`, ADR-0011, dua foundation script, kedua
JSON manifest, dan kedua foundation test file.
2. Update `docs/adr/README.md:16,25` dan active derived-image guidance di
`docs/adr/0013:147`, `docs/adr/0014:94`, `docs/adr/0015:55,99`, dan
`deploy/compose/README.md:79`.
3. Catat follow-up terbatas untuk menganotasi semua sisa historical evidence/
dokumen Phase 0/Phase 1; harus menyatakan bahwa tidak ada historical evidence
yang akan ditulis ulang secara diam-diam.

**Keuntungan**

- Cepat menghilangkan kontradiksi legal/policy dan memperbaiki gate behavior.
- Membatasi PR pertama ke sumber current user-facing dan executable.
- Mempertahankan integritas historical evidence sampai dapat direview dengan
hati-hati.

**Kerugian dan risiko**

- Membiarkan 27+ lokasi stale terlihat selama periode interim, termasuk materi
handover/plan yang masih terlihat aktif.
- Membutuhkan follow-up yang tracked dan owner-visible; jika tidak, documentation
drift akan bertahan.

**Blast radius**

- Efek executable dan reuse-right sama dengan Opsi A, dengan inkonsistensi
dokumentasi sementara.
- Tidak ada perubahan pada kebijakan publication/distribution.

## Inventori stale reference dan disposisi

Inventori berikut menggunakan stale-document research dan lokasi baris saat
ini. “Update” berarti mengubah klaim kebijakan saat ini; “annotate” berarti
mempertahankan historical evidence bertanggal dan menambahkan pointer ke state
kemudian. Daftar ini adalah scope eksak untuk Opsi A; Opsi C hanya menerapkan
entri yang ditandai **critical now** dan menunda sisanya.

| File dan baris | Pernyataan stale saat ini | Disposisi A | Waktu C |
|---|---|---|---|
| `README.md:64` | No license / no reuse / OPEN | Update | **critical now** |
| `docs/governance/LICENSE-DECISION.md:1-19` | Instruksi OPEN | Replace/update | **critical now** |
| `docs/adr/0011-public-repository-license-decision-pending.md:1,4,14` | Pending/OPEN ADR | Supersede/link ADR-0019 | **critical now** |
| `docs/adr/README.md:16` | License pending crosswalk | Update | **critical now** |
| `docs/adr/0013-derived-hardened-foundation-images.md:147` | OD-06 OPEN | Update sambil mempertahankan non-publication | **critical now** |
| `docs/adr/0014-official-release-binary-source-provenance.md:94` | OD-06 OPEN | Update sambil mempertahankan no publication | **critical now** |
| `docs/adr/0015-full-source-prometheus-grpc-remediation.md:55,99` | OD-06 OPEN/no distribution | Update status; pertahankan no distribution | **critical now** |
| `deploy/compose/README.md:79` | OD-06 change requires review | Clarify accepted status still triggers review | **critical now** |
| `deploy/compose/images.json:5` | Inventory does not resolve OD-06 | Update distinction | **critical now** |
| `deploy/compose/derived-images/license-dispositions.json:11` | Nilai manifest OPEN | Update contract value | **critical now** |
| `scripts/foundation_supply_chain.py:253-254,448` | OPEN-only reject/generated text | Update contract/text | **critical now** |
| `scripts/foundation_images.py:373,577,585` | Generated OPEN text | Update text | **critical now** |
| `tests/test_foundation_supply_chain.py:31` | Fixture OPEN | Update/add contract tests | **critical now** |
| `tests/test_foundation_images.py:86` | Fixture OPEN | Update/add contract tests | **critical now** |
| `docs/phase0/evidence-index.md:17` | OPEN current summary | Annotate historical state | defer |
| `docs/phase0/repository-preflight-report.md:12` | No license/OPEN | Annotate historical state | defer |
| `docs/phase0/open-decisions.md:5` | OPEN/do not add LICENSE | Annotate atau replace archival index | defer |
| `docs/phase0/dev-entry-gate.md:16` | License decision open | Annotate completed historical gate | defer |
| `docs/phase1/DEVELOPMENT-HANDOVER.md:28,51,107` | OD-06 unchanged/OPEN | Update current handover wording | defer |
| `docs/phase1/ISSUE-9-CLOSURE-PACKAGE.md:94,182,216,317` | OPEN/unchanged | Annotate dated closure history | defer |
| `docs/phase1/ISSUE-9-ACCEPTANCE-MATRIX.md:100` | unchanged/no rights | Annotate atau update current matrix note | defer |
| `docs/plan/PHASE1-COMPACT-INFRASTRUCTURE-FOUNDATION.md:199,414` | decision open | Annotate historical plan | defer |
| `docs/evidence/2026-07-17-phase0-safety-baseline.md:36` | OPEN | Annotate historical evidence | defer |
| `docs/evidence/2026-07-19-phase0-corrective-controls.md:40` | OPEN | Annotate historical evidence | defer |
| `docs/evidence/2026-07-20-phase1-derived-image-qualification.md:32,63,123` | OPEN | Annotate historical evidence | defer |
| `docs/evidence/2026-07-20-phase1-image-qualification-no-go.md:82,152` | OPEN | Annotate historical evidence | defer |
| `docs/evidence/2026-07-21-phase1-foundation-lifecycle.md:60` | OPEN | Annotate historical evidence | defer |

Research count tidak mencakup materi planning/evidence private `.omo/` dari
scope public remediation; catatan tersebut harus tetap immutable sebagai
historical agent artifacts kecuali kebijakan archival terpisah menyatakan lain.

## Jalur yang direkomendasikan dan acceptance checklist

Pilih **Opsi A**, dengan PR implementasi pertama yang tetap koheren daripada
mengimpor seluruh `0dce268`:

1. Owner mengonfirmasi bahwa Apache-2.0 tetap menjadi keputusan yang dimaksud
   dan menyetujui wording `NOTICE` copyright/attribution.
2. Implementasikan inventori Opsi A, secara selektif mereuse license artifacts
   dan delta relevan dari `0dce268`; resolve conflict README dengan
   mempertahankan status Phase 2 saat ini.
3. Definisikan satu nilai accepted-state machine di disposition schema dan
   uji. Jangan sekadar menghapus validasi: validator harus menolak state yang
   tidak terduga dan mempertahankan revalidation trigger.
4. Pertahankan `publication` dan `distribution` false di manifest dan
   pertahankan semua kontrol ADR-0013/0014/0015. Lisensi repository Apache-2.0
   tidak boleh dipresentasikan sebagai approval redistribution image.
5. Jalankan local gate yang didokumentasikan (`make phase0-check`) dan focused
   foundation test suite; Docker-dependent gates tetap CI/milestone-only
   sesuai baseline.
6. Tambahkan catatan evidence PR public-safe yang secara eksplisit menyatakan:
   source repository berlisensi Apache-2.0; runtime components tetap berlisensi
   secara independen; derived images tetap menjadi artifact Development lokal
   dan tidak dipublish maupun didistribute.

Ini menutup discrepancy tanpa secara diam-diam mengubah keputusan image-
distribution yang terpisah.
