# G2-P8 live4 owner-packet custody

Status: `CUSTODY_ONLY / NON-AUTHORIZING / B_PACKET_AUDIT / AUDIT_HOLD`

Recorded: `2026-08-08`

This companion record binds the corrected owner-decision packet as an immutable content object. It
does not establish `B_OWNER_PACKET_READY`, issue or fill an owner act, issue a lease, place a
credential, arm egress, authorize a launch or retry, clear a residual, record terminal clearance,
authorize Lane A, or grant landing or merge authority.

## 1. Corrected packet identity

| Binding | Exact value |
|---|---|
| Packet path | `docs/campaign-records/2026-08-08-g2-p8-live4-owner-decision-packet.md` |
| Packet content commit | `48305f1a7c84012ba15b7c98c45f866835b1d83d` |
| Packet content tree | `e418488dcb6a3dfe683cfa489271050dcd9a3ca6` |
| Packet content parent | `0bd57cfc9a0e8eaa4fbce03d8f41d76d982ba06f` |
| Packet content parent tree | `e3ed40c27e8931c39b5d337a06751f7ac9cf0b3c` |
| Packet Git blob | `78adb72591185c46fba85dea225ae5188e41e13d` |
| Packet raw SHA-256 | `844a0c183d795731f8dc5b25b7b8da68bc2a69ea04546d8b9678581adefa6c68` |
| Packet raw bytes | `21410` |
| Packet physical lines | `336` |
| Packet encoding / line endings | `UTF-8 without BOM / LF-only` |
| Packet commit fence | exactly one `M docs/campaign-records/2026-08-08-g2-p8-live4-owner-decision-packet.md` |
| Local branch | `codex/dl-owner-packet-v3` |
| Remote custody | `NOT CLAIMED; rederive before any action` |

The packet-content commit is a direct child of the earlier packet commit. Its only path change is the
corrected packet above. The older `0bd57cfc...` packet, tree `e3ed40c2...`, blob `e0255a17...`, and raw
SHA-256 `60fd0dab...` remain historical pre-correction identities and must not be reused as the final
owner-packet subject.

## 2. Pre-packet evidence and controlling design

| Binding | Exact value | Qualification |
|---|---|---|
| Verification-base `main` | `0b65b4f0b06fdbd1e34460800ef8251cebbb9307` | CURRENT-REF-CHECKED; not run authority; rederive before action |
| Pre-packet evidence-base commit | `e32da9925ca52ba0391ccedb4f81a7548a2ca429` | packet grandparent; not corrected-packet identity |
| Pre-packet evidence-base tree | `50843c56a2c374426919f509c66611cca4f5c0d2` | packet grandparent tree; not corrected-packet identity |
| Operating-design commit | `20e68d901f9f249c14dcf41428edf60da6a86208` | local `codex/docs-sync` custody; not main authority |
| Operating-design tree | `67adf13aa51ffd652e54019df041f322cdb65229` | local custody |
| Operating-design path | `docs/superpowers/specs/2026-08-08-ab-design.md` | session-local safety policy; non-authorizing |
| Operating-design blob | `8cba0de6047ad19e2a7de5bbc6160ebb3aef7008` | exact object |
| Operating-design raw SHA-256 | `03b9dddf8b4a2a32a4f4c593f199d22c53038cd43ec79c3eade49476816aa4e2` | exact bytes |
| Frontier-record path | `docs/campaign-records/2026-08-08-frontier-sync.md` | dated reconciliation; non-authorizing |
| Frontier-record blob | `425bf87cfe7de2f5617ba6d634512556ab1d4ce6` | exact object at operating-design commit |
| Frontier-record raw SHA-256 | `4ac948474176f150eb3f1c89bf556ce72c65c54cce18123966fdc4c6569caf2a` | exact bytes |

The design and frontier objects are cross-branch evidence. Their inclusion here does not promote the
docs branch to main, reopen its frozen changed-file fence, or grant program, owner, runtime, landing,
or merge authority.

## 3. Lane B subject cross-check

These values are duplicated only as a compact cross-check. The corrected packet identity in §1 is
the content binding; every time-sensitive or runtime fact still requires fresh rederivation.

| Binding | Exact value |
|---|---|
| Runtime revision | `d781adfcaab2eb880456aef7ac49ee589105bbbe` |
| Runtime tree | `da21ee59890e03c0245ff12f2bec5ae3ce1730a0` |
| Frozen plan blob | `68f740af86dc7d1ac2227f81a6ea28e7e2c7458f` |
| B1a seal blob | `b8a89df28ed1ed5adfd8ded7ee12d28863cf0ed2` |
| Campaign ID | `ff1af01b-785e-4c12-98d1-3f278039b4ea` |
| Campaign fingerprint | `3c415b6fe717810c47c506c9de8ce9c0ec5b78e9a633db080cdce91f16915e01` |
| Authority expiry | `2026-08-14T14:06:52.580652Z` |
| Strict owner-packet/latest-launch cutoff | `trusted UTC < 2026-08-13T14:06:52.580652Z`; equality is terminal HOLD |
| Minimum TTL | `>= 86400` seconds at packet-readiness and launch-final preflights |
| NRC grant ID | `nrc-aps-fa4cc6c53e76` |
| NRC raw-grant SHA-256 | `8f0e5c778f76d0da272ba636308faeaef85693bbce95e4c9b508185ac91e79e1` |
| NRC canonical fingerprint | `af753222bcbf4a524f63275dde2a1563b5edb6ee9952a3edae430bf4b0b86c38` |
| NRC expected-marker SHA-256 | `1a862282ee40ecfaa30c52075584ae592486c3bc1f84ef9ad9499b18b2a68841` |
| ScienceBase grant ID | `sciencebase-mcs-8ae20b6e8f89` |
| ScienceBase raw-grant SHA-256 | `b1819f62ffbf3f7f83814ec061f0e37f99937d9e5e3e2c39b81370071787dd8d` |
| ScienceBase canonical fingerprint | `f9b868cef8051af749c5de74d78d46162a3cf7c25123963fb705ba302dd400ae` |
| ScienceBase expected-marker SHA-256 | `85a68fe3c92312a817a828fe4f202cd1e029bdbc9863b3735badec6240d5e371` |

The staging-script hash measured during the prior audit is not packet-authorized and is deliberately
not promoted into this custody subject. Any future readiness receipt or lease must freshly bind the
exact staging-script identity required by the corrected packet.

## 4. Current state and nonclaims

After this record's containing commit is mechanically verified, the bounded artifact result may be
reported as:

`packet_content_complete=true; custody_bound=true; state=B_PACKET_AUDIT/AUDIT_HOLD`

That result does not establish `B_OWNER_PACKET_READY`. In particular:

- all packet-readiness rows remain `UNVERIFIED NOW / RECHECK REQUIRED` for future issuance;
- external producer quiescence is not established by local process inspection or this record;
- the three direct owner fields and three later owner actions remain blank or unperformed;
- `LEASE_STATE_OBSERVATION: NO LEASE EXISTS` is not terminal `NO_LEASE_ISSUED`;
- no `B_CLEARANCE_RECORDED` receipt exists; and
- Lane A remains locked.

The exact 16-file CI debt remains disclosed. Disclosure does not make exact-branch CI green. Before
any transition beyond `B_OWNER_PACKET_READY`, that exact set must be resolved or explicitly contained
by a separately authorized policy decision bound to the same set.

## 5. Companion self-identity rule

This record cannot embed its own Git blob, containing commit, or containing tree without changing the
object being named. The containing add-only commit therefore becomes the immutable custody revision
after commit. No third self-pinning commit is required.

Every future readiness receipt, owner act, or lease must bind both:

1. the packet tuple in §1; and
2. this companion record's exact path, containing commit/tree, and blob as derived after commit.

It must also rederive then-current main/branch state, trusted time, runtime checkout identity,
campaign/grants, markers, evidence roots, preparation-script identity, dependencies, database,
denied-network resolver behavior, and external producer quiescence. No generic, relayed, inherited,
draft, or context-free token may substitute.

## 6. Mechanical acceptance criteria

The custody commit is valid only if all of the following pass:

1. its parent is packet-content commit `48305f1a7c84012ba15b7c98c45f866835b1d83d`;
2. its diff fence is exactly one added companion path and no packet modification;
3. its tree retains packet blob `78adb72591185c46fba85dea225ae5188e41e13d`;
4. `git diff` from the packet-content commit to the custody commit is empty for the packet path;
5. every identity above rederives exactly from Git objects or raw bytes;
6. this file is strict UTF-8, contains no credential or owner-field value, and passes whitespace
   checks; and
7. no P8, credential, egress, lease, launch, retry, clearance, Lane A, landing, or merge authority is
   claimed or performed.

Failure of any criterion leaves the subject in `B_PACKET_AUDIT / AUDIT_HOLD` without valid companion
custody. Passing all criteria proves artifact identity only; it does not prove readiness or authority.
