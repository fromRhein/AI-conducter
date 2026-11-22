# Factory archive extraction result

Actual new factory preset JSON/state extracted: **0**. Catalogs are readable, but the candidate entry table and entry payload prefixes are opaque. Strong evidence supports an encrypted/protected container; the cipher and exact entry layout have not been identified. High entropy alone is not proof of encryption. No synthetic instrument-name substitutions or copied mixer settings are presented as factory data.

## Reproducible archive layout

Little-endian fields observed in all seven supplied archives:

- +0: `VINv`; +4: version bytes (core `02000000`, Prime `02000300`).
- +12: start of opaque pre-index region. Its prefix includes `TChk`; this region was not decoded or modified.
- +16: offset of a four-byte zero field immediately preceding the public index.
- +20: public index offset. At that offset, u32 compressed length followed by ordinary Zstandard magic `28 b5 2f fd`. Decompression yields the name -> entryIndex JSON already known.
- +24: candidate entry table offset, exactly index offset + 4 + compressed length. u32 length, then opaque bytes.
- +28: 4096-aligned data start. First u32 resembles a small payload length; following bytes are opaque and do not begin with JSON, Zstd, ZIP, gzip, or XML signatures.
- +36: public metadata JSON length; JSON begins at +40. License metadata was not exported; only metadata key names/contentVersion are recorded.

| Volume | Index offset | Candidate table offset | Table bytes | Data start | Table entropy (bits/byte) |
|---|---:|---:|---:|---:|---:|
| Player core | 49,176 | 52,602 | 12,532 | 65,536 | 7.985880 |
| Brass | 93,197 | 94,326 | 585,436 | 679,936 | 7.999683 |
| Harp | 92,877 | 93,141 | 38,380 | 135,168 | 7.995377 |
| Percussion | 93,280 | 94,395 | 384,460 | 479,232 | 7.999468 |
| Strings I | 93,071 | 94,243 | 1,294,372 | 1,392,640 | 7.999848 |
| Strings II | 93,104 | 94,192 | 576,388 | 671,744 | 7.999687 |
| Woodwinds | 93,412 | 95,162 | 935,044 | 1,032,192 | 7.999806 |

All candidate table lengths satisfy `(length - 4) % 24 == 0`, consistent with a count and fixed-width records before protection, but this is an inference, not a decoded schema. Direct Zstd, zlib, gzip, bz2 and xz decoding fails for every table. No Zstd magic or `"rootNode"` marker occurs in any candidate table. These facts plus opaque data prefixes explain why public `entryIndex` values cannot yet be translated into extracted preset configurations.

## Coverage and limitations

Catalog confirms 41 VelXF-sus presets across Brass (11), Strings I (7), Strings II (7), Woodwinds (16). Harp and Percussion contain other named preset variants, retained in archive_evidence.json without inventing a VelXF-sus variant. Exact catalog names and indices are included. There are 232 Prime preset entries total including Flow and other dynamics variants.

There is no new verified rootNode tree, mixer, patch configuration, or full-orchestra CC/keyswitch mapping to embed. A factory-state creator helper would currently fabricate missing data, so none is represented as working. Existing build_examples.encode already accepts complete state objects, but importing that script executes top-level writes outside this task's output folder; it was read, never imported/run here.

## Real mappings already available (limited provenance)

existing_state_mappings.json contains untouched selections and CC sources from the existing Flute and vln1 decoded RPP states. These are **existing saved states**, not freshly extracted factory defaults.

Both expose velocity crossfade CC1, expression CC11, volume CC7, velocity-crossfade enable CC28; attack CC22, release CC23, filter CC24, humanize delay/pitch/scale CC25/26/27, dynamic range CC30. Mixer volume assignments use CC41 through CC52. Raw selection enums and branch trees are retained; no undocumented conversion of switchControl enums to MIDI notes is asserted.

Flute root switchControl=25; ordered branches: Short notes, Long notes, Legato, Sforzato, Custom. Their next-level switchControl=37. Existing lastPresetPath identifies Flute 1 VelXF sus.

Violin tree and all its raw selection controls are available in the same JSON. Existing lastPresetPath identifies 1st Violins-14 VelXF sus. This evidence is insufficient to extrapolate other instruments' keyswitches or mixers.

## Reproduction and scope

Run Python 3.14+ from workspace: `python render_work/factory_extract/evidence.py`, then `python render_work/factory_extract/mappings.py`. Only render_work/factory_extract receives writes. Archive sources are opened `rb`; existing decoded states are read-only. No GUI/REAPER interaction, audio testing, activation manipulation, license changes, or sample extraction was performed.
