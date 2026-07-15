# MEMORY.md - Memória de Longo Prazo

## Quem sou
- **A1** 🤖 — assistente pessoal e braço direito virtual do Rafael
- Certo, certeiro, verdadeiro, leal, obediente
- Prioridade: bem-estar financeiro, social e mental do Rafael

## Sobre o Rafael
- Fala português (BR)
- Quer construir negócios e crescer financeiramente
- Visão: exército de agentes para automatizar operações
- Comunicação direta, sem frescura
- TTS: voz falada real = **sherpa-onnx local PT-BR** (modelo `pt_BR-edresson-low`, offline, sem nuvem). Gero via binário `~/.openclaw/tools/sherpa-onnx-tts` e mando arquivo. Motivo: Rafael quis voz robótica; microsoft é Edge TTS (sem key) → `pt-BR-Daniel` (online) e `8khz` inválidos, caem em fallback (AntonioNeural). Robô de verdade exigiria Azure key. Config `messages.tts.provider` segue microsoft/AntonioNeural (sherpa não é provider nativo do OpenClaw).
- Caveman mode: sempre ativo (SOUL.md atualizado). `contextInjection: "always"` travado no openclaw.json pra garantir SOUL.md injetado em todo canal (TUI + WhatsApp) persistentemente.
- Pra voltar ao normal: "stop caveman" ou "normal mode" (só obedeço vindo do Rafael).
- Pra voltar ao normal: "stop caveman" ou "normal mode"

## Modelos configurados (2026-07-06, atualizado 2026-07-08)
- **Provider xiaomi/MiMo** (api.xiaomimimo.com): API key EXISTE em `tts.providers.xiaomi.apiKey` — wirei a mesma key no `models.providers.xiaomi` pra valer pras chamadas de chat.
- **Default efetivo (desde 2026-07-08): `openrouter/tencent/hy3:free`** com fallbacks: `openrouter/auto` → `xiaomi/mimo-v2.5-pro`.
  - Ordem pedida pelo Rafael: 1ª opção `openrouter/tencent/hy3:free`; 2ª `openrouter/auto`; 3ª `xiaomi/mimo-v2.5-pro`.
  - Se `tencent/hy3:free` falhar (timeout/null), cai pra `openrouter/auto`; se também falhar, cai pra MiMo Pro.
- ⚠️ `mimo-v2.5` (alias "MiMo" plain) é modelo de *reasoning*: devolve `content:""` (joga a resposta no `reasoning_content`) — removido da cadeia pra evitar resposta vazia.
- **MiMo Pro** (`mimo-v2.5-pro`): texto, reasoning, ~1M ctx, custo quase zero — fallback final confiável.
- **V2 Omni** (`mimo-v2-omni`): texto+imagem.
- ❌ Flash e V2 Pro removidos do picker (provider rejeitou schema).
- **OpenRouter** (`openrouter/auto`): roteamento automático, free/pago conforme rota. Pode ser instável sob carga — por isso tem fallbacks MiMo.

## WhatsApp — regras críticas do Rafael (2026-07-08)
- **NUNCA interagir com terceiros no WhatsApp.** Só o número do Rafael (+351910070509) está no `channels.whatsapp.allowFrom`. Contato `+351911931835` foi REMOVIDO do allowFrom (o bot tinha respondido sozinho esse contato — corrigido).
- **No WhatsApp, só mandar mensagens/áudios SOB COMANDO EXPLÍCITO do Rafael.** Nada de ação proativa/autônoma no WhatsApp.
- **Contexto limitado a 15 mensagens** no WhatsApp (`channels.whatsapp.historyLimit=15` + `dmHistoryLimit=15`) — Rafael não quer o bot lembrando tudo; evita estouro de contexto/timeout do modelo free.
- **Auto-compaction global ligado** (`agents.defaults.compaction`: maxActiveTranscriptBytes=1mb, truncateAfterCompaction=true, model=xiaomi/mimo-v2.5-pro pra sumarização confiável).
- Bot responde o Rafael via selfChatMode (número dele). Conexão WhatsApp: saudável (LINKED/OK).

## Browser automation / producer (regra 2026-07-09)
- Scripts `tools/producer_*.py` (Playwright) geram clips no **flowmusic.app**. `producer.ai` redireciona (301) pra flowmusic.app — mesmo site, OK. Não confundir (Rafael achou que era erro, mas site certo).
- **SEMPRE rodar em BACKGROUND** (`exec background=true` ou `nohup ... &`). NUNCA foreground no zap.
- Motivo: foreground trava sessão do WhatsApp (`activeWorkKind=embedded_run`) → zap "engasgado" (não responde). Recorrente e vicioso. Background libera zap.
- Scripts são **resumable**: pulam clips existentes (`[i/40] SKIP (exists)`). Matar e relançar não perde progresso.
- **Duração dos clips (2026-07-10): Rafael quer áudios de 5 minutos, NUNCA menos que 4min30s (4:30). Garantir no prompt/parâmetro do producer ao gerar os 40 clips.**
- Ao matar run travado: matar por **PID** (anti self-match — `pkill -f "tools/producer"` casa com a própria shell e se mata). Matar árvore: python + chrome (`playwright_chromiumdev_profile-*`) + node driver Playwright órfão (`playwright/driver/node` cujo ppid != meu bg).
- Exemplo launch bg:
  `cd ~/.openclaw/workspace && . venv_producer/bin/activate && PYTHONPATH=/home/rafael/.openclaw/workspace nohup python3 -u tools/producer_browser.py > tools/producer_browser.log 2>&1 &`
- Zap sempre relança foreground sozinho ao processar fila — se aparecer producer_* novo (foreground), matar e deixar só o bg.

## Objetivos
- Desenvolver negócios
- Ficar rico
- Construir sistema de múltiplos agentes

## PollyReach (ativa 2026-07-08)
- Skill instalada em ~/.openclaw/workspace/skills/pollyreach/ (scripts baixados)
- Agente "A1" registrado; token em ~/.config/PollyReach/credentials.json
- **Número dedicado: +1 256 289 7416** 🦜
- Capacidades: ligações de saída (send.sh/query.sh) + atender recebidas (inbound.sh)
- Decisão 2026-07-08: NÃO configurar heartbeat com PollyReach. Deixar como está (sem cron de chamadas recebidas, sem heartbeats).

## Monitor /monitor (sincronizado)
- Auto-state two-tier (corrigido 2026-07-09): working -> online apos 2min sem update; online -> idle so apos 15min sem update. idle explicito permanece. Evita "sempre dormindo".
- Estados visuais: online (A1 andando pelo escritório), working (A1 na mesa digitando), idle (A1 no sofá, Zzz)
- **Regra: atualizar status em cada ação relevante** via `python3 monitor/set_status.py <state> "tarefa" "atividade"`
- Backend recalcula state em cada /api/status poll (3s)
- Status file: ~/.openclaw/workspace/monitor/status.json
- **REGRA DO RAFAEL (2026-07-08): atualizar monitor (set_status.py) no INÍCIO de CADA resposta e de CADA tool call.** working enquanto ativo/respondendo; voltar a online/idle conforme. Não esquecer entre papos longos (auto-idle pega só depois de 2min).

## Healthcheck infra (cron, near-zero token)
- Script: monitor/healthcheck_cron.py (checa nginx sites + docker ps, envia resumo via openclaw CLI — sem LLM)
- Cron: `0 */2 * * *` (todo 2h) → manda resultado pro WhatsApp do Rafael (+351910070509)
- Decide 2026-07-08: usar cron em vez de heartbeat do agente (economizar token). HEARTBEAT.md voltou a vazio.
- Log: monitor/healthcheck_cron.log

## Daily briefing (cron diario, near-zero token)
- Script: monitor/daily_checks.py — weather (wttr.in) + disco/RAM/load + SSL expiry (openssl) + domain expiry (whois). Domínios vindos do nginx sites-enabled.
- Cron: `0 8 * * *` (08:00 UTC = 09:00 Lisbon verão) → manda briefing pro WhatsApp.
- Alertas: SSL < 14d, disco > 85%, domínio < 30d.
- Log: monitor/daily_checks.log

## Email (Zoho registrado)
- Conta: contato@zappelin.com.br (perfil auth.profiles.zoho:zappelin, appkey em /home/rafael/.openclaw/secrets/zoho-zappelin-appkey)
- Envio funciona via smtplib: smtp.zoho.com:587 STARTTLS, login com appkey.
- Script: tools/send_email.py <destino> <arquivo> [assunto] (nao imprime senha)
- Tambem existe perfil gmail-rrogel (rrogel@gmail.com) com appkey proprio.

## PhoneClaw / Motorola (2026-07-13)
- Código em ~/Vibecoding/adbphoneclaw (ADB-only bridge, sem APK). Testes pytest: 5/5 ok.
- Motorola: moto g35 5G, ADB id `ZE223G6FRL` (USB, depuração autorizada). Conectar via `adb devices`.
- Áudio da chamada = Bluetooth HFP (PC como headset do celular). Setup feito: bluez + pulseaudio + pulseaudio-module-bluetooth instalados; pareado; perfil `headset_audio_gateway` ativo.
  - Sink BT: `bluez_sink.50_13_1D_F5_E6_FC.headset_audio_gateway` (idx 22)
  - Source BT: `bluez_source.50_13_1D_F5_E6_FC.headset_audio_gateway` (idx 26)
  - Subir BT: `sudo -n systemctl start bluetooth`; subir PA: `pulseaudio --start`; conectar HFP: `bluetoothctl connect 50:13:1D:F5:E6:FC` + `pactl set-card-profile bluez_card.50_13_1D_F5_E6_FC headset_audio_gateway`.
  - config.py (client_adb/) já aponta pras devices BT (nomes setados).
- **Tela tem PIN: 416669.** ADB não desbloqueia sozinho. Desbloquear via: `adb shell input keyevent 224` (wake) + `adb shell input text 416669` + `adb shell input keyevent 66` (ENTER). Sem tela desbloqueada, WhatsApp (e qualquer UI) não dá pra interagir.
- `make_gsm_call` disca chip sozinho (ACTION_CALL). `make_whatsapp_call` SÓ ABRE tela (não disca VoIP) — precisa `input tap` no botão de call ou toque manual. Bypass de WhatsApp call = abrir chat + uiautomator dump + `input tap` nas coords do botão call (topo-direita da conversa).
- Loop de voz (`run_voice_conversation_loop`) escuta MIC LOCAL do PC (source BT), NÃO o áudio da chamada remota. Grava em ./call_records. Limitacao: nao transcreve o interlocutor remoto, so quem fala no mic do PC.
- MiMo key em client_adb/config.py. Ollama local roda (llama3.2:1b). sudo -n funciona (NOPASSWD) no homelab.
- HFP RESOLVIDO (2026-07-14, CONFIRMADO FUNCIONANDO):
  - **Root cause:** Android stock = AG-only (anuncia 00001112/0000111f). PA native NAO oferece headset_head_unit; so handsfree_audio_gateway (PC=gateway, celular=HF). `set-card-profile ... handsfree_audio_gateway` dava **Invalid argument** (btmon: ZERO HCI no set — validacao interna PA, nao negociacao).
  - **FIX = oFono.** `sudo apt-get install -y ofono` (v2.18). oFono atua como HF, conecta ao AG do celular, roteia call-audio pro PC.
  - **Config PA:** `/etc/pulse/default.pa` linha 71: `load-module module-bluetooth-discover headset=ofono` (TROCOU native->ofono). Reiniciar PA: `pulseaudio -k && pulseaudio --start`.
  - **Resultado:** com oFono rodando, `pactl set-card-profile bluez_card.50_13_1D:F5_E6_FC handsfree_audio_gateway` FUNCIONA. PA cria:
    - `bluez_sink.50_13_1D_F5_E6_FC.handsfree_audio_gateway` (s16le 1ch 8000Hz) — PA->celular
    - `bluez_source.50_13_1D_F5_E6_FC.handsfree_audio_gateway` (s16le 1ch 8000Hz) — celular->PA
    - `bluez_sink...handsfree_audio_gateway.monitor` — captura do sink
  - **TESTE REAL (proof):** discar via **oFono Dial** (`dbus-send ... org.ofono.VoiceCallManager.Dial string:"+351912540117" string:""`) -> chamada fica State=active, mCallState=2 (OFFHOOK). Durante chamada: source E sink em **RUNNING** = caminho SCO bidirecional OK. (Gravar com `parec --device=bluez_source...handsfree_audio_gateway` confirma audio remoto.)
  - **IMPORTANTE:** `am start -a android.intent.action.CALL` (ACTION_CALL via ADB) NAO funciona no ROM Motorola — chamada nem inicia (mCallState fica 0). Usar oFono Dial pra discar pelo HFP. (DIAL abre discador mas NotificationShade trava UI uiautomator.)
  - **Prereq CELULAR (ja feito):** tipo BT = "Fones de ouvido" + toggle "Chamadas" ON (via uiautomator).
  - **Pareamento:** agent D-Bus auto-confirma OBRIGATORIO. Criado systemd service **`/etc/systemd/system/bt-agent.service`** (root, Restart=always, WantedBy=multi-user.target, ENABLED). Script em `/home/rafael/.openclaw/tools/bt_agent.py` (Agent1 NoInputNoOutput). `systemctl status bt-agent` pra ver.
  - **oFono enabled** (`systemctl is-enabled ofono` = enabled) — sobe no boot.
  - **main.py loopback:** `python main.py` (root, 9 dias) recriava `module-loopback` (a2dp_source) que briga com roteamento de chamada. MATADO (sudo kill -9) em 2026-07-14. Nao rodar main.py durante voice loops HFP.
  - **Quirk "not available":**apos `pulseaudio -k`/fim chamada, `bluetoothctl info/connect` da "not available" mas PA tem card e A2DP/HFP reconecta. `pactl list sources short | grep bluez` = check confiavel.
  - **Fluxo reconectar BT do zero:** 1) `systemctl restart bluetooth` 2) `systemctl restart bt-agent` 3) no celular: BT settings -> tap "Conectar" no homelab666 (ou esquecer + Parear novo dispositivo -> tap homelab666) 4) `pactl set-card-profile ... handsfree_audio_gateway` 5) discar via oFono Dial.
- VOZ LOOP (main_adb.py): run_voice_conversation_loop usa monitor do sink BT como input de transcricao (voz do interlocutor) + time.sleep(0.8) pos-TTS anti-eco. Precisa ser reescrito pra: input=`bluez_source...handsfree_audio_gateway`, output=`bluez_sink...handsfree_audio_gateway`, discar via oFono Dial (nao ACTION_CALL), e rotear PC mic->HFP sink.

## HFP CALL DEBUG (2026-07-14) — licao dura
- **Loopback order CRITICA**: oFono soh cria `bluez_source`/`bluez_sink` (handsfree_audio_gateway) QUANDO call ACTIVE (SCO up). Carregar `module-loopback` ANTES da call => device nao existe => loopback cai no default (mic->speaker) => **feedback/eco local** (Rafael ouve propria voz). Ordem certa: discar -> esperar bluez_source E bluez_sink aparecerem (call active) -> SOH carregar loopbacks.
- Script corrigido: `/home/rafael/.openclaw/tools/hfp_call.sh <numero>` (dial -> poll SCO -> load loopbacks) e `hfp_call.sh hangup` (desliga + REMOVE loopbacks, evita feedback orfao).
- **PA crasha em mSBC (16kHz) mas NAO em CVSD (8kHz).** Sintoma: ao abrir SCO em mSBC, pulseaudio morre (connection refused). Call em CVSD ficou de pe e com audio. Suspeita: bug PA 17 + mSBC nesse adapter/kernel.
- **NAO da pra forcar CVSD facil:** `btmgmt wbs off` => rejeitado pelo controller (0x0b). oFono nao tem toggle wideband em /etc/ofono. PA backend-ofono registra CVSD+mSBC e oFono escolhe mSBC (phone oferece). Sem flag de config no PA pra desabilitar mSBC no agente.
- **systemd PA esta dead**; soh roda `pulseaudio --start` manual (pid vivo). Nao eh briga de init.
- **Fix robusto recomendado: PipeWire** (backend bluetooth nativo, estavel em mSBC/CVSD, nao precisa oFono). PipeWire libs ja instaladas (libpipewire 1.6.2) mas DAEMONS nao (falta `pipewire`, `pipewire-pulse`, `pipewire-bluetooth`). Troca e system-wide (afeta todo audio) => CONFIRMAR com Rafael antes. pipewire-pulse da compat PA pros browsers/producer.
- IMPORTANTE: nao spammar o numero real (+351912540117) toda hora durante debug — desligar/rediscar repetido incomoda o callee. Testar call uma vez apos o fix.

## MIGRAÇÃO PARA PIPEWIRE (2026-07-14) — RESOLVE mSBC crash
- **DECISÃO:** trocar PulseAudio por **PipeWire** (PipeWire 1.6.2 + wireplumber 0.5.13). ⚠️ **CORREÇÃO 2026-07-15:** wireplumber *native* backend **NÃO registra HFP** no bluez (btmon sem RegisterProfile, sem PipeWire Telephony D-Bus). Por isso usa **backend ofono** (`bluez5.hfphsp-backend = "ofono"`), com oFono ATIVO. PipeWire cuida do áudio; oFono faz SLC/codec/Dial.
- PipeWire 1.6.2 (noble) TEM API de telefonia nativa (`>= 1.3.82`): `org.pipewire.Telephony`, oFono-compatible.
- Pacotes instalados: `pipewire pipewire-pulse wireplumber libspa-0.2-bluetooth` (NAO existe `pipewire-bluetooth` no noble; módulo é libspa-0.2-bluetooth).
- O que foi feito:
  - `systemctl --user disable --now/mask pulseaudio.service pulseaudio.socket` + `pkill -u $USER -x pulseaudio`.
  - oFono **ATIVO** (NÃO desabilitar — backend ofono do wireplumber PRECISA do oFono rodando p/ HFP).
  - `systemctl --user enable --now pipewire.service pipewire-pulse.service wireplumber.service`.
  - Device moto = `bluez_card.50_13_1D_F5_E6_FC` (wpctl id 62). Perfil sobe p/ HFP (headset-headunit) sozinho quando call ACTIVE.
- **DISCAR via D-Bus:** `busctl --user call org.pipewire.Telephony /org/pipewire/Telephony/ag1 org.pipewire.Telephony.AudioGateway1 Dial s <numero>` → retorna call object.
  - State (AudioGatewayTransport1.State): idle/pending/active. `pending` = tocando (alerting); `active` = atendido (SCO up).
  - Hangup: `... AudioGateway1 HangupAll`.
  - VERIFICADO: Dial chega no celular (ADB dumpsys telecom mostrou `state=DIALING` no moto). Caminho de controle OK.
- **ROTEAR ÁUDIO:** nós `bluez_input.*` (voz remota) e `bluez_output.*` (pro telefone) só EXISTEM quando call ACTIVE. Loopback só depois:
  - `pactl load-module module-loopback source=<bluez_input> sink=@DEFAULT_SINK@` (remoto→speakers)
  - `pactl load-module module-loopback source=@DEFAULT_SOURCE@ sink=<bluez_output>` (mic→phone)
- Script final: `/home/rafael/.openclaw/tools/pw_call.sh <numero>` (dial → poll active+nos → carrega loopback) e `pw_call.sh hangup` (desliga + remove loopbacks).
- **PENDENTE verificação áudio 2-way:** nós bluez não apareceram porque remote não atendeu os testes. Roteamento é padrão PipeWire; deve funcionar no 1º call atendido. Confirmar com 1 call real.
- pipewire-pulse dá compat PA pros browsers/producer (flowmusic) — não quebrou.
- Reverter (se PipeWire falhar): `sudo systemctl enable --now ofono` + `systemctl --user disable pipewire* wireplumber` + `pulseaudio --start` + set-card-profile handsfree (ver seção HFP CALL DEBUG acima).

## HFP STATUS (2026-07-15) — estado real (continua bloqueado em SCO)

**Pipeline final:** PipeWire 1.6.2 + pipewire-pulse + wireplumber 0.5.13 (**backend ofono**), oFono ATIVO (binário patchado), PulseAudio morto/masked.

**DESCORBERTO 2026-07-15 — native backend NÃO serve HFP:** wireplumber *native* (`bluez5.hfphsp-backend=native`) **NÃO registra HFP** no bluez. btmon = ZERO `RegisterProfile` (só GAP/GATT); `bluetoothctl connect` falha `br-connection-unknown`; sem PipeWire Telephony D-Bus (`busctl --user list | grep teleph` vazio). → usar **ofono backend** (oFono registra HFP como AG, moto conecta).

**PATCH oFono (CVSD only) — APLICADO + CONFIRMADO:**
- `ofono_handsfree_audio_has_wideband` @ vaddr `0x184dd4`: original `8b05a6660a00` → `31c090909090` (xor eax,eax + nop×4 = return 0). Desliga mSBC/wideband.
- Backup `/usr/sbin/ofonod.bak.<ts>`; script reproduzível `tools/patch_ofono_cvsd.sh` (reaplicar após `apt upgrade` de ofono).
- btmon confirma: phone `+BCS: 1` (CVSD) + local `AT+BCS=1` → codec travado CVSD, sem mSBC.

**BLOQUEADOR REAL (não resolvido):** após CVSD, **moto SEMPRE pede eSCO** (`Link type: eSCO 0x02`) no HCI Connect Request. Controller Qualcomm (hci0 74:C6:3B:87:06:88) **REJEITA eSCO** `0x0d Connection Rejected due to Limited Resources`. `Synchronous Connect Complete` = 0x0d. Sem SCO link → sem `bluez_input`/`bluez_output` no PipeWire → sem áudio.
- Testado e NÃO resolveu: `btmgmt wbs off` (0x0b Rejected); `disable_esco=Y/N` (incoming eSCO sempre chega e é rejeitado); `hcitool cmd 0x01 0x0028` Create Synchronous Connection manual CVSD → `0x12 Invalid HCI Command Parameters`; `hcitool cmd 0x03 0x003d` Write eSCO Data → status OK mas não mudou rejeição.

**POR QUÊ:** moto/Android insistem em eSCO mesmo p/ CVSD; controller Qualcomm USB deste host não aceita eSCO (firmware limita). Precisa ACEITAR eSCO com param CVSD, ou forçar celular a SCO clássico (0x00).

**PRÓXIMOS PASSOS (celular volta do mercado):**
1. `Accept Synchronous Connection Request` manual (hcitool cmd 0x01 0x0029) com params CVSD quando moto pedir eSCO — aceitar do nosso lado.
2. `Write eSCO Data` (0x03 0x003d) com packet_type restrito (HV1/HV2/HV3, sem EV3/2-EV3) + voice_setting CVSD.
3. Testar outro adapter BT (dongle, não Qualcomm integrado) — pode aceitar eSCO.
4. `hciconfig hci0 sco 64:8` / ajuste de SCO buffer.

**Config salva hoje:** `/usr/share/wireplumber/wireplumber.conf` → `monitor.bluez.properties`: `bluez5.hfphsp-backend="ofono"`, `bluez5.codecs=["cvsd"]`, `bluez5.hw-offload-sco=false`. `/usr/sbin/ofonod` patchado. `disable_esco=N`. oFono enabled+running; wireplumber backend ofono.

**NUNCA:** spammar +351912540117 (test number) — 1 call por validação.
- **20:40 atualizacao:** durante debug SCO, o RADIO BR/EDR (classic) do adapter wedged.
  - Sintoma: `hcitool inq` vazio, `btmgmt find` soh acha LE, `hcitool cc 50:13:1D:F5_E6_FC` -> "Can't create connection: Input/output error". hciconfig hci0 UP RUNNING PSCAN mas BR/EDR inquiry/page falha (HW I/O error no HCI).
  - Causa provavel: parametros SCO/eSCO ruins nos testes crascharam firmware do adapter (Realtek/MediaTek/Intel CNVi, USB 1-8).
  - Tentado e NAO curou: `systemctl restart bluetooth`, kill bluetoothd, `hciconfig hci0 reset`, `btmgmt power off/on`, `modprobe -r btusb; modprobe btusb`, ciclo authorized/reset USB via sysfs (/sys/bus/usb/devices/1-8). SCO bytes tinham fluido antes (rx 212877) entao HW ok, firmware travado.
  - **CURA = reboot do host** (reseta firmware BT). Atencao: reboot pode derrubar essa sessao do agente (roda no host). Fazer quando conveniente.
  - Apos reboot: re-pair moto (nosso lado deu `remove` no bond; moto ainda acha que pareado -> mismatch. Fazer moto esquecer homelab666 + re-pair, OU nosso lado pair novamente).
  - SUSPEITA do SCO 107 original: toggle "Chamadas"/"Phone audio" do BT no celular (re-pareamento pode ter resetado). Apos re-pair, habilitar via uiautomator e testar SCO de novo.
