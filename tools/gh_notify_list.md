# Lista Curada — Disclosure Responsável (GitHub public code search)

Varredura: 135 repos bateram padrão → 55 candidatos → refinados conteúdo.
Regra: NUNCA usar/testar chave. Avisar só dono. Não notificar exemplo/doc.

## FORTES (notificar)
| # | Repo | Arquivo | Tipo | Obs |
|---|------|---------|------|-----|
| 1 | csrsm/go-proxy | pk.txt | RSA private key (completa) | arquivo dedicado a chave → quase certamente real |
| 2 | limseang/film_api_new | key.txt | private key | arquivo dedicado |
| 3 | gauthieralfa/ep2510 | Priv.txt | private key (EC ~861c) | "Priv" = privada |
| 4 | arcVaishali/stellar-vision | text.txt | GCP service account JSON (private_key + project_id littergraph) | chave real GCP |

## BORDERLINE (avisar "por favor confira")
| # | Repo | Arquivo | Tipo | Obs |
|---|------|---------|------|-----|
| 5 | diego3g/umbriel | .env.local.example | AWS key (example file) | valor em formato real; exemplo mas vale checar |

## SKIP (doc/tutorial oficial — NÃO notificar)
- okta/okta-sdk-python (README oficial SDK — exemplo de documentação)
- ideawu/Objective-C-RSA, antonscheffer/as_crypto, vikingmute/better-wechatpay,
  RamonPage/ex_azure_key_vault (tutoriais/exemplos)

---

## Mensagens prontas (PT + EN)

### 1) csrsm/go-proxy — pk.txt
PT:
```
Olá @csrsm,
Encontrei por acaso (busca pública de código no GitHub) uma chave privada RSA
commitada em `pk.txt` no repo `csrsm/go-proxy`.
Recomendo: 1) revogar/rotacionar a chave agora; 2) remover do repo E do histórico
(git filter-repo / BFG); 3) usar secrets não versionados.
Não usei a chave para nada. Só aviso para evitar abuso.
Abs
```
EN:
```
Hi @csrsm,
While doing a public code search on GitHub I noticed an RSA private key committed
in `pk.txt` in `csrsm/go-proxy`. Please revoke/rotate it, remove from repo + history,
and use non-committed secrets. I did not use the key. Just flagging.
```

### 2) limseang/film_api_new — key.txt
PT:
```
Olá @limseang,
Busca pública no GitHub achou uma chave privada em `key.txt` no repo
`limseang/film_api_new`. Se for real: revogue/rotacione já, remova do repo + histórico,
use env var. Não usei a chave. Aviso só.
```
EN:
```
Hi @limseang,
Public GitHub code search surfaced a private key in `key.txt` in `limseang/film_api_new`.
If real, please rotate it and purge from history. I did not use it. Flagging only.
```

### 3) gauthieralfa/ep2510 — Priv.txt
PT:
```
Olá @gauthieralfa,
Achei (busca pública GitHub) chave privada em `Priv.txt` no repo `gauthieralfa/ep2510`.
Recomendo rotacionar + remover do repo/histórico. Não usei a chave. Aviso preventivo.
```
EN:
```
Hi @gauthieralfa,
Public code search on GitHub found a private key in `Priv.txt` in `gauthieralfa/ep2510`.
Please rotate and remove from history. I did not use it. Just a heads-up.
```

### 4) arcVaishali/stellar-vision — text.txt (GCP SA)
PT:
```
Olá @arcVaishali,
Busca pública no GitHub encontrou um service account do GCP (com private_key e
project_id `littergraph`) em `text.txt` no repo `arcVaishali/stellar-vision`.
Recomendo: revogar a chave na GCP, remover do repo + histórico. Não usei nada. Aviso.
```
EN:
```
Hi @arcVaishali,
Public GitHub code search surfaced a GCP service account key (private_key,
project `littergraph`) in `text.txt` in `arcVaishali/stellar-vision`.
Please revoke it in GCP and purge from history. I did not use it. Flagging only.
```

### 5) diego3g/umbriel — .env.local.example (borderline)
PT:
```
Olá @diego3g,
Por acaso vi em `diego3g/umbriel` (`.env.local.example`) um `AWS_ACCESS_KEY_ID`
com valor em formato real. Como está em arquivo de exemplo, pode ser placeholder —
mas vale conferir se não é chave ativa. Se for, rotacione e remova do histórico.
Não usei nada. Aviso preventivo.
```
EN:
```
Hi @diego3g,
I noticed in `diego3g/umbriel` (`.env.local.example`) an AWS_ACCESS_KEY_ID with a
real-looking value. It's in an example file so may be a placeholder — but worth
checking it isn't a live key. If so, rotate and purge history. I didn't use it.
```

## Canais preferidos (privado)
1. GitHub Security Advisory (Settings > Security > Private vulnerability reporting)
2. Issue no repo (sem expor a chave completa)
3. Email do perfil (último recurso)

## Aviso segurança (nosso)
- No refine anterior vazou o AWS_SECRET_ACCESS_KEY de diego3g/umbriel no log do chat.
  Já está exposto nesta conversa. Não usar. Se for real, dono deve rotacionar.
- PAT do GitHub (`ghp_8h…O7Lr`) foi passado mascarado — incompleto, não utilizável.
  Recomendo revogar esse PAT depois (Settings > Developer settings).
- Nunca expor chave completa em issue pública.
