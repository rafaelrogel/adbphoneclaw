# PhoneClaw ADB-Only Bridge (Sem APK)

Este repositório contém a versão do **PhoneClaw** otimizada para rodar localmente no seu **Homelab**, controlando o celular Android conectado via USB (ADB) sem a necessidade de instalar nenhum aplicativo ou APK no aparelho.

A ponte de áudio da chamada continua utilizando a conexão **Bluetooth HFP** (Hands-Free Profile) pareada entre o celular e o computador do Homelab, garantindo processamento de voz de baixíssima latência e **totalmente gratuito** usando o chip físico do celular.

## Estrutura do Repositório

*   `main_adb.py`: Menu CLI interativo e orquestrador do loop de conversa por voz com a IA.
*   `adb_controller.py`: Módulo responsável pelas chamadas de sistema do ADB para discar, desligar e interagir com o celular.
*   `mimo_client.py`: Integração com a API de ASR e TTS da Xiaomi MiMo.
*   `audio_bridge.py`: Captura e reprodução de voz via Bluetooth.
*   `openclaw_skill_adb.py`: Arquivo de definição de skills/ferramentas pronto para importação no framework **OpenClaw**.
*   `config.py.example`: Modelo para as configurações da API da Xiaomi e Bluetooth.

## Pré-requisitos

1.  **ADB (Android Debug Bridge)** instalado no computador/homelab e adicionado ao PATH global do sistema.
2.  **Depuração USB** ativa nas Opções do Desenvolvedor do celular Android conectado por cabo.
3.  **Bluetooth HFP** pareado entre o celular e o computador (computador configurado como headset de voz).

## Como Instalar e Rodar

1.  Clone este repositório.
2.  Instale as dependências:
    ```bash
    pip install -r requirements.txt
    ```
3.  Renomeie o arquivo `config.py.example` para `config.py` e adicione sua chave de API da Xiaomi (`XIAOMI_MIMO_API_KEY`).
4.  Certifique-se de que o dispositivo é detectado via USB:
    ```bash
    adb devices
    ```
5.  Execute o script principal:
    ```bash
    python main_adb.py
    ```
