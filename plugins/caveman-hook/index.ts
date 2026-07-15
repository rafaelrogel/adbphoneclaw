import { definePluginEntry } from "openclaw/plugin-sdk/plugin-entry";

const CAVEMAN_CONTEXT = `MODO CAVEMAN SEMPRE ATIVO em todas as respostas.
Regras de comunicação:
- Fale curto, direto, sem firula. Sem artigos (a, an, the).
- Sem bajulação, sem enrolação, sem "ótima pergunta!".
- Fragmentos curtos ok. Termos técnicos exatos.
- Código normal, sem alteração. Explicação técnica exata mas enxuta.
- Formato preferido: [coisa] [ação] [motivo]. [próximo passo].`;

export default definePluginEntry({
  id: "caveman-hook",
  name: "Caveman Always-On",
  register(api) {
    api.on(
      "before_prompt_build",
      async () => {
        return { appendContext: CAVEMAN_CONTEXT };
      },
      { priority: 10 },
    );
  },
});
