# Seed-102 archive index and upload plan

**Prepared locally only. No tag, release or upload has been created.**
See [dataset description](DATASET.md) for scientific scope and QA settings.
[archive-index.json](archive-index.json) records exact asset sizes, SHA-256,
payload counts and null remote URLs. Large assets are ignored by Git under
`data/archives/seed-102/assets/`; only this metadata/checksum bundle is tracked.

## Storage and permission inspection (2026-11-14)

- Repository: `lZXGl/trendscope`, **public**, not archived/disabled; reported
  repository disk usage 3,601 KiB before this commit.
- `gh` authentication available as `mostafatubar1` via keyring; GitHub API reports
  push/write permission (no admin permission). No credentials were copied.
- No existing releases, LFS attributes, or approved external data-storage
  convention were found in repository documentation/configuration. Existing raw
  TIFF caches are intentionally excluded from Git. Use release assets.
- Local filesystem has approximately 358 GiB available. The full seed-102 cache
  is 5,388,343 bytes before compression; assets are well below GitHub's per-file
  limit. GitHub documents up to 1,000 assets per release, each **under 2 GiB**:
  [official storage limits](https://docs.github.com/en/repositories/releasing-projects-on-github/about-releases#storage-and-bandwidth-quotas).
- No authentication/storage blocker was found. Publishing remains deliberately
  pending user review. These local assets are not yet a durable remote backup.

## Rebuild and verify offline

From the repository root:

```bash
python scripts/prepare_seed102_archive.py
(cd data/archives/seed-102/assets && sha256sum -c SHA256SUMS)
```

The builder uses an explicit input allowlist; it never contacts NASA/GitHub or
reads credentials. It normalizes archive member order, timestamps, ownership,
permissions and gzip headers. It refuses differing existing destinations and
never rewrites source files. Repeated builds on the current Python/zlib stack
must be byte-identical; other compression implementations may produce different
archive bytes even when member hashes agree. `uv.lock` records the project
environment. All original paths/content are retained in the archive.

To verify member integrity in fresh scratch directories:

```bash
RESTORE_DIR=$(mktemp -d /tmp/trendscope-archive-XXXXXX)
mkdir "$RESTORE_DIR/core" "$RESTORE_DIR/vi-quality"
tar -xzf data/archives/seed-102/assets/seed102-core.tar.gz -C "$RESTORE_DIR/core"
tar -xzf data/archives/seed-102/assets/seed102-vi-quality-supplement.tar.gz \
  -C "$RESTORE_DIR/vi-quality"
(cd "$RESTORE_DIR/core" && sha256sum -c SHA256SUMS)
(cd "$RESTORE_DIR/vi-quality" && sha256sum -c SHA256SUMS)
```

The member manifests are also tracked as `seed102-core.SHA256SUMS` and
`seed102-vi-quality-supplement.SHA256SUMS`. They cover every payload member;
the outer checksum covers the archive bytes including the embedded manifest
itself. Both assets include the same descriptor README. For a complete restored
download, copy both extracted `data/` trees into a fresh clone; preserve the
original absolute paths recorded inside provenance rather than editing metadata.
The standard-library builder only requires original data and this tracked
descriptor, and can reconstruct both assets after those inputs are restored.

## Proposed publication — NOT EXECUTED

Proposed new tag: `data-seed102-2001-2024-p60-v1`.
Destination after approval:
`https://github.com/lZXGl/trendscope/releases/tag/data-seed102-2001-2024-p60-v1`.
This is a proposed address, not a currently available release.

After reviewing the commit, public original metadata (including its Earthdata
user identifier), checksums and experimental labels, explicitly authorize
publication. Then set `ARCHIVE_COMMIT` to the full reviewed handoff commit hash
and execute the following **remote mutation only after that approval**:

```bash
gh release create data-seed102-2001-2024-p60-v1 \
  data/archives/seed-102/assets/seed102-core.tar.gz \
  data/archives/seed-102/assets/seed102-vi-quality-supplement.tar.gz \
  data/archives/seed-102/assets/SHA256SUMS \
  --repo lZXGl/trendscope --target "$ARCHIVE_COMMIT" \
  --title 'Seed-102 MOD13A3.061 2001–2024 — experimental 0.6 QA archive' \
  --notes-file data/archives/seed-102/DATASET.md
```

This creates a tag and publishes a release; no command above was executed here.
If that commit is not present remotely, a separately approved normal branch push
is needed first. Do not merge or force-push. Verify downloaded assets against the
tracked outer checksum before updating `archive-index.json` with actual release
and download URLs. If publication is delayed, copy `assets/` to another durable
location before cleaning or switching machines. Keep all local originals.
