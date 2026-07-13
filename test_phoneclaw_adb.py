import pytest
from unittest.mock import patch, MagicMock
from client_adb.adb_controller import AdbController
from client_adb.mimo_client import MimoClient
from client_adb.audio_bridge import find_device_index

# --- MOCKS DO CONTROLE ADB ---

@patch("subprocess.run")
def test_adb_get_connected_devices_success(mock_run):
    # Mock do retorno do comando 'adb devices'
    mock_response = MagicMock()
    mock_response.stdout = "List of devices attached\nemulator-5554\tdevice\n\n"
    mock_run.return_value = mock_response

    controller = AdbController()
    devices = controller.get_connected_devices()

    assert len(devices) == 1
    assert devices[0] == "emulator-5554"
    mock_run.assert_called_with(["adb", "devices"], stdout=-1, stderr=-1, text=True, check=True)


@patch("subprocess.run")
def test_make_gsm_call_success(mock_run):
    mock_response = MagicMock()
    mock_response.stdout = "Starting: Intent { act=android.intent.action.CALL dat=tel:xxx }"
    mock_run.return_value = mock_response

    controller = AdbController()
    result = controller.make_gsm_call("+5511999999999", "emulator-5554")

    assert result is True


# --- MOCK DA API CLIENTE XIAOMI ---

@patch("requests.post")
def test_transcribe_audio_success(mock_post):
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {"choices": [{"message": {"content": "Teste de transcrição"}}]}
    mock_post.return_value = mock_response

    client = MimoClient()
    with patch("builtins.open", MagicMock()):
        result = client.transcribe_audio("fake_file.wav")

    assert result == "Teste de transcrição"
    mock_post.assert_called_once()


@patch("requests.post")
def test_synthesize_speech_stream(mock_post):
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.iter_lines.return_value = [
        b"data: " + b'{"choices": [{"delta": {"audio": {"data": "SGVsbG8="}}}]}',
        b"data: [DONE]"
    ]
    mock_post.return_value = mock_response

    client = MimoClient()
    chunks = list(client.synthesize_speech_stream("Texto"))

    assert len(chunks) == 1
    assert chunks[0] == b"Hello"


# --- MOCK DA SELEÇÃO DE DISPOSITIVOS DE SOM ---

@patch("sounddevice.query_devices")
def test_find_device_index(mock_query):
    mock_query.return_value = [
        {"name": "Default Speaker", "max_input_channels": 0, "max_output_channels": 2},
        {"name": "Bluetooth Hands-Free Audio", "max_input_channels": 1, "max_output_channels": 1}
    ]

    idx = find_device_index("Bluetooth", is_input=True)
    assert idx == 1
