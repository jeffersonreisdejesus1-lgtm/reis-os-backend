# W05 D02 — Inventário canônico das 72 OCSs

Procedimento: CUPUWA-OCS-INDIVIDUAL-QUALIFICATION-001
Branch: cupuwa/ocs-individual-qualification-001
Base: f3a175568be622c6f6edbee8310a45c659111b17
Artefato anterior: docs/cupuwa/W05-OCS-INVENTORY-BASELINE.md

## Fonte de composição

O registro canônico é composto por quatro conjuntos:

- FOUNDATION_OCS: 10 identidades em profiles.py;
- ELEVENTH_OCS: TÊMIS;
- CUPUWA_SPECIALIST_OCS: 19 identidades visuais;
- MOBILE_FULLSTACK_OCS: 42 identidades mobile/fullstack.

Total declarado pelo código: 10 + 1 + 19 + 42 = 72.

A função validate_canonical_registry() exige 72 identidades, namespaces de estado e memória distintos, especialidades distintas, envelope de autoridade explícito e ausência de adapters/permissões de ferramenta diretos.

## Lista canônica

### Fundação e stewardship — 11

NÓESIS, DÉDALA, SÝNESIS, ÍRIS, LYRA, SOFIA, MÊTIS, ÁGORA, AURI, SYNERGEIA, TÊMIS.

Fonte:
- app/profile_bindings/profiles.py
- app/profile_bindings/canonical_registry.py

### Pacote visual CUPUWA — 19

AURA, EIKÓN, TÝPOS, GRAMMÉ, LÉXIS, CHRÔMA, SÊMA, KINÉSIS, FIGMA, DÉSMOS, GÉPHYRA, HÉSTIA, ROTA, PRÁXIS, MORPHÉ, ARGOS, DOKIMÉ, LEÍA, KRITÉRION.

Fonte:
- app/profile_bindings/cupuwa_visual_profiles.py

### Pacote mobile/fullstack — 42

AXÍA, HOROS, ODÓS, DOMÉA, NOMÍSMA, ARCHÉ, STÁTE, MNÉME, DIKTYO, SYNCHRÓN, SÝNDESI, KOTLIN, COMPOSÉ, DROÍD, GRADLE, FORMA, SWIFT, SWIFTUI, CUPERTINO, XCODE, APPLÉIA, APÍON, DATON, AUTHÉN, SERVÍA, THREAT, KRYPTÓ, ASPÍS, PRIVÁTA, MONÁDA, SÝMPLEX, TELOS, A11Y, ANTÍPALOS, TÁCHOS, MNEMOS, ENERGEIA, PHAROS, PIPELINE, KLEIS, MIKRÓN, NEURÁ.

Fonte:
- app/profile_bindings/mobile_fullstack_profiles.py

## Estado da evidência

| Item | Estado |
|---|---|
| Lista de 72 derivada do registro | DECLARED / REGISTERED |
| Identidade e especialidade no perfil | MATERIALMENTE DECLARADAS |
| Fisiologia individual completa | NÃO PROVADA |
| Host disponível por identidade | NÃO PROVADO |
| Runtime bound por identidade | NÃO PROVADO |
| Runtime enforced por identidade | NÃO PROVADO |
| Execução individual reproduzível | NÃO PROVADA |
| Receipt individual por identidade | NÃO PROVADO |

O inventário não transforma os perfis em OCSs qualificadas. Ele fornece a base de rastreabilidade para D03: vincular cada identidade a fisiologia, capability, autoridade, entrypoint, teste e evidência.

## Controles preservados

- pool não é ativado em massa;
- capability não concede autoridade;
- perfil não concede efeito direto;
- ausência de evidência permanece HOLD;
- nenhuma promoção foi realizada.

D02 = PASS_WITH_LIMITS
D03–D06 = PENDING
