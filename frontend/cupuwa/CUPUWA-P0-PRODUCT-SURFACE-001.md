# CUPUWA-P0-PRODUCT-SURFACE-001

ENVELOPE_ID = CUPUWA-P0-PRODUCT-SURFACE-001
PATH = B
PUBLIC_APP_NAME = CUPUWA
PUBLISHER = J-SON Software
APPLICATION_ID = com.jsonsoftware.cupuwa
ARCH_OWNER = DEDALA@GROK
ENG_OWNER = SOFIA@GROK
COMMAND_APK = KEEP_SEPARATE
PROMOTE = NEVER
MERGE = NOT_AUTHORIZED

## Verdict on previous P0

The LinearLayout-from-code skeleton is a ledger proof, not a product.
This tranche replaces that surface without leaving the money domain.

## IN_CORE

- Material 3 XML home (saldo, hoje, ações, lista)
- Dedicated movement screen (entrada/saída/editar)
- formatBrl with BR thousands (1.250,90) and integer cents
- persist with commit()
- createdAt on each row; day totals; edit; delete confirm
- launcher vector icon
- no INTERNET; no Command import

## OUT

WhatsApp, pedidos, clientes, PDF, rede, IA, Atlas, loja, Command.

## Gates

G1 SOURCE = this commit on sofia/cupuwa-p0-001
G2 CI = cupuwa-p0-material assemble + LedgerMathTest + AAPT identity
G3 DEVICE = 25,90 shows R$ 25,90; edit; delete; kill/reopen keeps saldo
G4 MERGE = Founder only after G3
