"""
PhoneClaw ADB-Only OpenClaw Skill Integration
"""

import logging
from client_adb.adb_controller import AdbController

logger = logging.getLogger("OpenClaw.Skills.PhoneClawAdb")
adb = AdbController()

def get_phoneclaw_adb_skills() -> list:
    return [
        phoneclaw_adb_gsm_call,
        phoneclaw_adb_whatsapp_chat,
        phoneclaw_adb_end_call
    ]

def phoneclaw_adb_gsm_call(to: str) -> str:
    """
    Inicia uma chamada telefônica GSM tradicional via chip SIM no celular USB conectado.
    Use esta ferramenta quando precisar fazer uma ligação de operadora normal usando o cabo USB do homelab.

    Args:
        to (str): O número do telefone no formato internacional (ex: "+5511999999999").

    Returns:
        str: Status da chamada.
    """
    devices = adb.get_connected_devices()
    if not devices:
        return "Erro: Nenhum dispositivo Android conectado via USB (ADB)."
        
    sucesso = adb.make_gsm_call(to, devices[0])
    if sucesso:
        return f"Sucesso: Chamada GSM iniciada para {to}. O loop de voz está ativo."
    return f"Erro: Falha ao iniciar a chamada para {to}."

def phoneclaw_adb_whatsapp_chat(to: str) -> str:
    """
    Abre a conversa do WhatsApp para o número informado no celular USB.
    Use esta ferramenta para abrir o canal de comunicação no WhatsApp.

    Args:
        to (str): O número do telefone no formato internacional (ex: "+5511999999999").

    Returns:
        str: Status do comando.
    """
    devices = adb.get_connected_devices()
    if not devices:
        return "Erro: Nenhum dispositivo Android conectado via USB (ADB)."
        
    sucesso = adb.make_whatsapp_call(to, devices[0])
    if sucesso:
        return f"Sucesso: Tela de WhatsApp aberta para o número {to}."
    return f"Erro: Falha ao abrir o WhatsApp via ADB."

def phoneclaw_adb_end_call() -> str:
    """
    Encerra a chamada atual enviando o comando de desligamento via USB.
    Use esta ferramenta sempre que precisar desligar o telefone no final da conversa.

    Returns:
        str: Confirmação de encerramento.
    """
    devices = adb.get_connected_devices()
    if not devices:
        return "Erro: Nenhum dispositivo Android conectado via USB (ADB)."
        
    adb.end_call(devices[0])
    return "Sucesso: Comando de desligamento enviado ao celular."
