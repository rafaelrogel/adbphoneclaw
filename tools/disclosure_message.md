# Mensagem de Divulgação Responsável (Responsible Disclosure)

Enviar APENAS após verificar que a chave é REAL (abrir arquivo no GitHub, confirmar que não é placeholder/example).
NUNCA testar a chave. NUNCA usar. Só avisar.

---

## PT-BR (padrão)

```
Olá {owner},

Por acaso encontrei (via busca pública de código no GitHub) o que parece ser uma
credencial ativa no seu repositório {repo}, no arquivo `{path}`.

Se for uma chave real, recomendo:
1. Revogar/rotacionar a credencial AGORA (no provedor correspondente)
2. Remover do repositório E do histórico (git filter-repo ou BFG Repo-Cleaner)
3. Migrar segredos para variáveis de ambiente não versionadas

Não usei a chave para nada e não a compartilhei. Só estou avisando para evitar abuso.

Abs,
{seu_nome}
```

---

## EN (para donos internacionais)

```
Hi {owner},

While doing a public code search on GitHub, I noticed what appears to be a live
credential in your repo {repo}, file `{path}`.

If it's a real key, I'd suggest:
1. Revoke/rotate it immediately (at the provider)
2. Remove it from the repo AND its history (git filter-repo or BFG Repo-Cleaner)
3. Move secrets to non-committed env vars

I did not use or share the key — just flagging it so it doesn't get abused.

Best,
{your_name}
```

---

## Canais de envio (preferir privado)
- GitHub Security Advisory (Settings > Security > Private vulnerability reporting) — melhor
- Issue no repo (se não tiver advisory)
- Email do owner (perfil GitHub) como último recurso

## Não fazer
- Não expor a chave completa em issue pública
- Não testar se a chave funciona
- Não notificar por exemplo/.env.sample (falso positivo)
