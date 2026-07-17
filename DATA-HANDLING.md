# Data Handling — Public Repository

## Tujuan dan klasifikasi

Dokumen ini menetapkan batas antara public development artifact dan private runtime/operations material.

- **Public:** generic code, schema, template, dan synthetic fixture yang telah lulus review; boleh masuk Git.
- **Internal:** planning/evidence non-sensitive yang belum disetujui untuk publik; simpan di controlled workspace, bukan Git publik.
- **Confidential:** business context, source authorization metadata, masked operational summary; simpan pada approved private system.
- **Restricted:** credential, key/certificate, endpoint, topology, raw payload/log/capture/dump, Production identifier, video, dan incident evidence; dilarang masuk Git, issue, PR, Actions log, prompt, atau demo.

Unknown classification diperlakukan sebagai Restricted sampai owner memutuskan.

## Boleh masuk Git

- generic source code, configuration template, JSON/Avro schema;
- synthetic fixture memakai reserved domain/range dan invented identifier;
- sanitized architecture diagram tanpa real topology;
- reviewed public-safe evidence tanpa operational identifier/payload;
- generic deployment dan runbook template.

## Dilarang pada Git, issue, PR, Actions log, prompt, dan demo

- credential, token, key, certificate, password, SNMP community;
- real IP, hostname, FQDN, serial, asset tag, rack/site/camera name;
- source inventory, firewall matrix, management network, office topology;
- raw Redfish/SNMP/ISAPI/syslog payload, packet capture, log, trace, dump, backup;
- screenshot, recording, ticket, incident text, prompt, atau video operasional;
- material dengan authorization/classification tidak diketahui.

## Logical planes

1. **DEV-BUILD / SIMULATION:** mutable code dan synthetic fixture.
2. **DEV-INTEGRATION-RO:** manually promoted pinned image, dedicated read-only credential, restricted network/egress, private runtime storage.
3. **DEV-DEMO:** synthetic atau approved sanitized snapshot.

Setiap plane memakai project, network, volume, environment file, dan credential terpisah. Runtime material tetap di luar repository.

## Sanitization

Sanitization harus menghapus atau irreversibly replace direct/quasi identifier, endpoint, topology, free-text secret, dan unique operational pattern. Aggregation saja tidak cukup untuk small population. Multi-team stage memerlukan second-person review; selama Solo Development, owner merekam metode dan menjalankan automated public-safety checks.

## Log, screenshot, artifact, retention, dan deletion

- Log publik hanya boleh regenerated dari synthetic input; redact token, endpoint, identity, free text, dan topology.
- Screenshot wajib dibuat ulang pada `dcim-demo`; screenshot Production selalu Restricted.
- Build/test artifact hanya memuat synthetic result dan minimum metadata; unknown classification tidak boleh di-upload.
- Public artifact mengikuti Git retention. Private runtime/evidence mengikuti authorization register; sebelum nilai disetujui, simpan minimum dan hapus setelah review.
- Private deletion dilakukan pada approved system dan dicatat tanpa menyalin isi. Git exposure memerlukan revoke/rotate dahulu, owner-approved history remediation, lalu cache/fork review.

## Stop conditions dan incident response

Stop saat live/suspected-live data terlihat, connector dapat write/control, external service akan menerima office data, authorization tidak ada, collector/Hermes tidak dapat dihentikan, atau sanitization tidak terbukti.

1. Hentikan push/automation terkait.
2. Revoke/rotate credential sebelum history cleanup.
3. Simpan incident record private; jangan copy nilai ke public issue.
4. Jalankan history rewrite hanya melalui owner-approved procedure.
5. Ulangi secret/public-safety scan dan review fork/cache.
6. Publikasikan hanya sanitized prevention summary.
