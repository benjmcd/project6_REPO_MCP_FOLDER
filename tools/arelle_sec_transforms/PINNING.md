# SEC Inline Transform Plugin Pin

This directory vendors the SEC inline transform plugin required for EDGAR iXBRL facts that use the `http://www.sec.gov/inlineXBRL/transformation/2015-08-31` registry.

The files were copied from operator-staged references in `state/agent-inbox` on 2026-07-05. This lane did not perform a network fetch.

| Local file | Upstream source | Fetched | SHA256 | Provenance |
| --- | --- | --- | --- | --- |
| `__init__.py` | `https://github.com/Arelle/EDGAR/blob/master/transform/__init__.py` | 2026-07-05 | `2296586f945ffd95ab37d3d4147c4e45f42ce4e5f397f61143e053208adefbf1` | SEC staff work; see preserved 17 U.S.C. 105 header. |
| `text2num.py` | `https://github.com/Arelle/EDGAR/blob/master/transform/text2num.py` | 2026-07-05 | `6c9b26354320a2fb34fe380cdc71ff7f8d1cc712811e6b10c661e512f0383409` | MIT-licensed `text2num` helper; see preserved header. |
