# Initial dataset audit — 2026-10-17

This is a source/terms review, not legal clearance. No dataset was downloaded.
`datasets/registry.json` is the executable policy. `training_allowed` and
`commercial_allowed` mean project authorization, not an assertion about every
possible legal use. Unknown or incomplete entries fail closed.

| Candidate | Evidence inspected | Current decision / next evidence |
|---|---|---|
| Barkopedia | [Official challenge](https://github.com/UTA-ACL2/Barkopedia) describes YouTube/Reddit sources. [Individual-ID subset](https://huggingface.co/datasets/ArlingtonCL2/Barkopedia_Individual_Dog_Recognition_Dataset/blob/main/README.md) advertises MIT metadata. | Unknown. Choose exact task/revision; check underlying media rights and platform permission. Identity-recognition labels alone do not supply bark event/context labels. |
| CatMeows | [Zenodo v1.0.2](https://zenodo.org/records/4008297) provides WAVs and animal IDs, with scientific/non-commercial terms. | Not approved for commercial product training. Resolve terms with rights holder; preserve cat IDs and pseudonymize owner IDs. Recording contexts are not mental states. |
| Meow-Net | [Official code](https://github.com/Yfyangd/meow) is MIT and uses CatMeows. | Not approved for data use. Code permission does not override CatMeows terms. Replication is pending rights. |
| AP-10K | [Official README/license](https://github.com/AlexTheBad/AP-10K#license) states CC-BY-4.0. | Unknown project approval. Pin version, attribution and image provenance. This is pose imagery, not audio training data; validate animal identity mapping separately. |
| Animal Kingdom | [Official repository](https://github.com/sutdcv/Animal-Kingdom) links a request form for dataset/code access. | Unknown. Obtain and review complete access/commercial terms and media provenance; no form submitted. |

Approval needs a reviewed version, source, license, rights evidence, consent basis,
reviewer/date and explicit training/commercial flags. Review policy changes in a
PR. The gate trusts the operator's reviewed local registry; it cannot verify that
claims entered by a person are true. Do not flip flags merely to get a run passing.
Generated sine-wave fixtures use their own registry under ignored `data/`.

## Project owner's commercial approval

On 2026-10-17 the user authorized commercial training in the task conversation.
This is recorded as `project_commercial_approval` on each candidate. It authorizes
our intended commercial use, but is not evidence of third-party licensing or
platform permission. `commercial_allowed` remains false until those rights are
verified, and the training gate remains closed. CatMeows/Meow-Net need appropriate
commercial permission or a replacement dataset. No paid API/cloud spend was approved.
