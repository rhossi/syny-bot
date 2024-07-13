from twilio.rest import Client
import asyncio
import time

TWILIO_AUTH_TOKEN = '29c51f74368c481a2cddf99640e91e27'
TWILIO_ACCOUNT_SID = 'ACc2fbd4e58e9b41d1afd01af1cf2c958a'

client = Client(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)

async def send_message():
    time.sleep(5)
    client.messages.create(to='whatsapp:+14043045909', from_='whatsapp:+14155238886', body='Hello there!')

async def main():
    await send_message()
    print("Processing a long request. I will be back in a moment.")

if __name__ == "__main__":
    asyncio.run(main())