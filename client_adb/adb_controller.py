import subprocess
import logging
import re
import time

logger = logging.getLogger("PhoneClaw.AdbController")

class AdbController:
    def __init__(self):
        # Garante que temos o executável adb disponível
        self.check_adb_installed()

    def check_adb_installed(self) -> bool:
        try:
            subprocess.run(["adb", "--version"], stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True)
            return True
        except Exception:
            logger.error("Erro: 'adb' não está instalado ou não está no PATH do sistema. Por favor, instale o Android SDK Platform-Tools.")
            return False

    def get_connected_devices(self) -> list:
        """
        Retorna a lista de IDs de dispositivos conectados via USB.
        """
        try:
            result = subprocess.run(["adb", "devices"], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, check=True)
            lines = result.stdout.strip().split("\n")
            devices = []
            for line in lines[1:]:  # Pula a primeira linha ("List of devices attached")
                if not line.strip():
                    continue
                parts = line.split()
                if len(parts) >= 2 and parts[1] == "device":
                    devices.append(parts[0])
            return devices
        except Exception as e:
            logger.error(f"Erro ao listar dispositivos ADB: {e}")
            return []

    def execute_shell(self, command: str, device_id: str = None) -> str:
        """
        Executa um comando shell ADB no dispositivo.
        """
        args = ["adb"]
        if device_id:
            args.extend(["-s", device_id])
        args.extend(["shell", command])
        
        try:
            result = subprocess.run(args, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, check=True)
            return result.stdout.strip()
        except subprocess.CalledProcessError as e:
            logger.error(f"Erro ao executar comando ADB shell: {e.stderr.strip()}")
            return ""

    def make_gsm_call(self, phone_number: str, device_id: str = None) -> bool:
        """
        Inicia uma chamada telefônica GSM tradicional via chip SIM.
        """
        clean_number = re.sub(r"[^0-9+]", "", phone_number)
        logger.info(f"Disparando ligação GSM via ADB para {clean_number}...")
        
        # O comando 'am start' com a intent ACTION_CALL disca diretamente.
        # Caso o aparelho não possua a permissão direta concedida ao ADB, abre a tela de discagem.
        cmd = f"am start -a android.intent.action.CALL -d tel:{clean_number}"
        output = self.execute_shell(cmd, device_id)
        
        if "Starting: Intent" in output:
            logger.info("Ligação iniciada com sucesso via ADB.")
            return True
        else:
            # Fallback usando ACTION_DIAL (abre com número pronto para o usuário clicar no botão físico)
            logger.warning("Falha na chamada direta. Tentando abrir discador como fallback...")
            fallback_cmd = f"am start -a android.intent.action.DIAL -d tel:{clean_number}"
            fallback_output = self.execute_shell(fallback_cmd, device_id)
            return "Starting: Intent" in fallback_output

    def make_whatsapp_call(self, phone_number: str, device_id: str = None) -> bool:
        """
        Abre o chat do WhatsApp para o número informado.
        Devido a restrições do WhatsApp, não é possível discar VoIP 100% diretamente via ADB simples
        sem emular toques na tela (input tap). O script abre a conversa para o usuário iniciar a chamada.
        """
        clean_number = re.sub(r"[^0-9]", "", phone_number)
        logger.info(f"Abrindo chat de WhatsApp via ADB para {clean_number}...")
        
        # Abre o chat do WhatsApp usando a URI oficial
        cmd = f"am start -a android.intent.action.VIEW -d \"https://api.whatsapp.com/send?phone={clean_number}\""
        output = self.execute_shell(cmd, device_id)
        
        if "Starting: Intent" in output:
            logger.info("WhatsApp aberto com sucesso via ADB. O agente de voz começará a escutar a ponte Bluetooth.")
            return True
        return False
        
    def end_call(self, device_id: str = None) -> bool:
        """
        Envia o sinal de pressionamento de tecla para desligar a chamada.
        """
        logger.info("Enviando comando para desligar chamada...")
        # Keyevent 6 representa a tecla ENDCALL no Android
        output = self.execute_shell("input keyevent 6", device_id)
        return True
