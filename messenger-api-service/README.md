This is a bridge api between telegram bot and message processing service. It does:

1. Receiving messages info and sending it to telegram private chat specified by phone number
2. Receiving messages from telegram bot, processing them and forwarding to message processing service
3. Storing recent conversation history in sqlite database
4. Giving feedback to users from telegram chat based on message processing service response