import requests
from console_ui import show_message_sent, show_message_failed


class MessageSender:
    def __init__(self, base_url, instance, api_key):
        self.base_url = base_url
        self.instance = instance
        self.api_key = api_key

    def send_message(self, remote_jid: str, message: str, name: str = "") -> bool:
        url = f"{self.base_url}/message/sendText/{self.instance}"
        headers = {
            "Content-Type": "application/json",
            "apikey": self.api_key,
        }
        payload = {
            "number": remote_jid,
            "text": message,
        }
        try:
            response = requests.post(url, json=payload, headers=headers)
            response.raise_for_status()
            show_message_sent(name or remote_jid, remote_jid)
            return True
        except requests.exceptions.RequestException as e:
            show_message_failed(name or remote_jid, remote_jid, str(e))
            return False
