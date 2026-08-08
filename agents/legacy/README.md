# Legacy agents

Superseded by the composable library in `agents/lib/`, kept because published
results in `docs/` cite them by name.

`probe_template.py` + `probes/` and `adversary_template.py` + `adv/` were two
separate ad-hoc generators. Every strategy they expressed is now a point in the
atom space (`tools/registry.py`), so new work should go there instead.

| Legacy agent | Equivalent atom composition |
|---|---|
| `probes/one_quadrant` | `homestead-crew-orchardherd-metered-blind-muck` |
| `probes/two_quadrant` | `smallhold-crew-orchardherd-metered-blind-muck` |
| `probes/four_quadrant` | `latifundium-crew-orchardherd-metered-blind-muck` |
| `probes/mono_melon` | `estate-crew-melonrush-metered-blind-muck` |
| `probes/mono_cow` | `estate-crew-dairy-metered-blind-muck` |
| `probes/mono_sheep` | `estate-crew-woolworks-metered-blind-muck` |
| `probes/mono_goose` | `estate-crew-henhouse-metered-blind-muck` |
| `probes/dump_all` | `*-*-*-flood-blind-muck` |
| `probes/hoarder` | `*-*-*-vault-blind-muck` |
| `probes/no_hire` | `*-solo-*` |
| `probes/hire_max` | `*-swarm-*` |
| `probes/fert_only` | `*-*-ranchmix-*-*-dung` |
| `probes/product_only` | `*-*-ranchmix-*-*-nomuck` |
| `adv/frontrun` | `*-*-*-metered-frontrun-muck` |
| `adv/evade` / `avoid` | `*-*-*-metered-evade-muck` |
| `adv/spite` | `*-*-*-metered-spite-muck` |
| `adv/parasite` | `homestead-lean-rootcellar-flood-spite-muck` |

The compositions are close equivalents, not bit-identical: the library engine
fixed several bugs the ad-hoc generators had.
