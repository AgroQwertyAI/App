const qrcode = require('qrcode-terminal');
const { Client, LocalAuth, MessageMedia } = require('whatsapp-web.js');
const axios = require('axios');
const fs = require('fs');
require('dotenv').config();

// Environment variables
const DATA_SERVICE_URI = process.env.DATA_SERVICE_URI;
const MESSAGE_PROCESSING_URI = process.env.MESSAGE_PROCESSING_URI;

if (!DATA_SERVICE_URI || !MESSAGE_PROCESSING_URI) {
  console.error('Environment variables DATA_SERVICE_URI and MESSAGE_PROCESSING_URI must be set');
  process.exit(1);
}

// Track registered chats to avoid duplicates
const registeredChats = new Set();

// Initialize WhatsApp client with local authentication
const client = new Client({
  authStrategy: new LocalAuth({ dataPath: './whatsapp-session' }),
  puppeteer: {
    args: ['--no-sandbox', '--disable-setuid-sandbox'],
    headless: true,
  }
});

// Handle QR code generation
client.on('qr', async (qr) => {
  // Display QR in terminal for development purposes
  console.log('QR Code received, scan to authenticate:');
  qrcode.generate(qr, { small: true });
  
  // Send QR code to data service
  try {
    await axios.post(`${DATA_SERVICE_URI}/api/settings/whatsapp_qr`, { qr_code: qr });
    console.log('QR code sent to data service');
  } catch (error) {
    console.error('Failed to send QR code to data service:', error.message);
  }
});

// When authenticated
client.on('authenticated', () => {
  console.log('WhatsApp authentication successful');
});

// When auth fails
client.on('auth_failure', (msg) => {
  console.error('Authentication failure:', msg);
});

// When client is ready
client.on('ready', async () => {
  console.log('WhatsApp bot is ready and online!');
  
  // Register all existing chats
  try {
    const chats = await client.getChats();
    for (const chat of chats) {
      if (chat.isGroup) {
        await registerChat(chat);
      }
    }
    console.log(`Registered ${registeredChats.size} existing chats`);
  } catch (error) {
    console.error('Error registering existing chats:', error.message);
  }
});

// Handle new messages
client.on('message', async (message) => {
  try {
    // Skip messages from ourselves
    if (message.fromMe) return;
    
    const chat = await message.getChat();
    
    // Register chat if not already done
    if (!registeredChats.has(chat.id._serialized) && chat.isGroup) {
      await registerChat(chat);
    }
    
    const contact = await message.getContact();
    
    // Prepare message data
    const messageData = {
      message_id: message.id.id,
      source_name: "whatsapp",
      chat_id: chat.id._serialized,
      text: message.body,
      sender_id: contact.id._serialized,
      sender_name: contact.name || contact.pushname || contact.number || "Unknown"
    };
    
    // Handle media if present
    if (message.hasMedia) {
      const media = await message.downloadMedia();
      if (media) {
        messageData.image = `data:${media.mimetype};base64,${media.data}`;
      }
    }
    
    // Send to message processing service
    await axios.post(`${MESSAGE_PROCESSING_URI}/new_message`, messageData);
    console.log(`Message from ${messageData.sender_name} in ${chat.name} forwarded to processing service`);
    
  } catch (error) {
    console.error('Error processing message:', error.message);
  }
});

// Handle when bot is added to a group
client.on('group_join', async (notification) => {
  try {
    // Check if the bot was added
    const botNumber = client.info.wid._serialized;
    const addedParticipants = notification.recipientIds;
    
    if (addedParticipants.includes(botNumber)) {
      const chat = await notification.getChat();
      await registerChat(chat);
      console.log(`Bot was added to group: ${chat.name}`);
    }
  } catch (error) {
    console.error('Error handling group join event:', error.message);
  }
});

// Function to register a chat with the data service
async function registerChat(chat) {
  try {
    const chatId = chat.id._serialized;
    
    // Skip if already registered
    if (registeredChats.has(chatId)) return;
    
    const response = await axios.post(`${DATA_SERVICE_URI}/api/chats`, {
      chat_id: chatId,
      chat_name: chat.name || "Unknown Group",
      source_name: "whatsapp"
    });
    
    if (response.data.success || response.status === 409) { // Success or already exists
      registeredChats.add(chatId);
      console.log(`Registered chat: ${chat.name} (${chatId})`);
    }
  } catch (error) {
    console.error(`Failed to register chat ${chat.name}:`, error.message);
  }
}

// Initialize client
client.initialize().catch(error => {
  console.error('Failed to initialize WhatsApp client:', error.message);
});

// Handle process termination
process.on('SIGINT', async () => {
  console.log('Shutting down WhatsApp bot...');
  await client.destroy();
  process.exit(0);
});