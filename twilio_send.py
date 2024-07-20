from twilio.rest import Client
import asyncio
import time

TWILIO_AUTH_TOKEN = '29c51f74368c481a2cddf99640e91e27'
TWILIO_ACCOUNT_SID = 'ACc2fbd4e58e9b41d1afd01af1cf2c958a'

import json

class ComponentParameter:
    def __init__(self, type, text=None, currency=None, amount=None):
        self.type = type
        self.text = text
        self.currency = currency
        self.amount = amount

    def to_dict(self):
        return {k: v for k, v in self.__dict__.items() if v is not None}

class Component:
    def __init__(self, type, sub_type=None, index=None, parameters=None, url=None):
        self.type = type
        self.sub_type = sub_type
        self.index = index
        self.parameters = parameters if parameters is not None else []
        self.url = url

    def add_parameter(self, parameter):
        self.parameters.append(parameter)

    def to_dict(self):
        data = {k: v for k, v in self.__dict__.items() if v is not None and k != 'parameters'}
        if self.parameters:
            data['parameters'] = [p.to_dict() for p in self.parameters]
        return data

class Template:
    def __init__(self, name, language, components=None):
        self.name = name
        self.language = language
        self.components = components if components is not None else []

    def add_component(self, component):
        self.components.append(component)

    def to_dict(self):
        return {
            'name': self.name,
            'language': self.language,
            'components': [component.to_dict() for component in self.components]
        }

class WhatsAppCard:
    def __init__(self, to, from_, template):
        self.messaging_product = "whatsapp"
        self.to = to
        self.from_ = from_
        self.type = "template"
        self.template = template

    def to_dict(self):
        return {
            'messaging_product': self.messaging_product,
            'to': self.to,
            'from': self.from_,
            'type': self.type,
            'template': self.template.to_dict()
        }

    def __str__(self):
        return json.dumps(self.to_dict(), indent=4)

# Example usage
if __name__ == "__main__":
    client = Client(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)
    # Create a WhatsApp card template
    card = {
        "messaging_product": "whatsapp",
        "to": "whatsapp:+14043045909",
        "from": "whatsapp:+14155238886",  # Your Twilio WhatsApp number
}
    
    card2 = {
        "friendly_name": "owl_coupon_code",
        "language": "en",
        "variables": {
            "1": "coupon_code"
        },
        "types": {
            "whatsapp/card": {
                        "body": "Congratulations, you have reached Elite status! Add code {{1}} for 10% off.",
                        "header_text": "This is a {{1}} card",
                        "footer": "To unsubscribe, reply Stop",
                        "actions": [
                            {
                                "url": "https://owlair.example.com/",
                                "title": "Order Online",
                                "type": "URL"
                            },
                            {
                                "phone": "+15555554567",
                                "title": "Call Us",
                                "type": "PHONE_NUMBER"
                            }
                        ]
                    }
        }
    }

    # # Send the WhatsApp card
    # message = client.messages.create(to="whatsapp:+14043045909", from_="whatsapp:+14155238886", body=card2)

    # print(message.sid)

    import requests
from requests.auth import HTTPBasicAuth


url = 'https://content.twilio.com/v1/Content'

headers = {
    'Content-Type': 'application/json',
}

data = {
    "friendly_name": "owl_air_qr",
    "language": "en",
    "variables": {"1": "Owl Air Customer"},
    "types": {
        "twilio/quick-reply": {
            "body": "Hi, {{1}} 👋 \nThanks for contacting Owl Air Support. How can I help?",
            "actions": [
                {"title": "Check flight status", "id": "flightid1"},
                {"title": "Check gate number", "id": "gateid1"},
                {"title": "Speak with an agent", "id": "agentid1"}
            ]
        },
        "twilio/text": {
            "body": "Hi, {{1}}. \n Thanks for contacting Owl Air Support. How can I help?."
        }
    }
}

response = requests.post(url, json=data, auth=HTTPBasicAuth(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN), headers=headers)

message = client.messages.create(to="whatsapp:+14043045909", from_="whatsapp:+14155238886", body=response.text)

print(message.sid)