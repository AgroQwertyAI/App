const qrcode = require('qrcode-terminal');
const { Client, LocalAuth, MessageMedia } = require('whatsapp-web.js');
const axios = require('axios');
const fs = require('fs');
const express = require('express');
require('dotenv').config();

// Environment variables
const DATA_SERVICE_URI = process.env.DATA_SERVICE_URI;
const MESSAGE_PROCESSING_URI = process.env.MESSAGE_PROCESSING_URI;
const PORT = process.env.PORT || 52101;

if (!DATA_SERVICE_URI || !MESSAGE_PROCESSING_URI) {
  console.error('Environment variables DATA_SERVICE_URI and MESSAGE_PROCESSING_URI must be set');
  process.exit(1);
}

// Initialize Express server
const app = express();
app.use(express.json());
app.use(express.urlencoded({ extended: true }));

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
  

});

// Handle new messages
client.on('message', async (message) => {
  try {
    // Skip messages from ourselves
    if (message.fromMe) return;
    
    const chat = await message.getChat();
    const contact = await message.getContact();
    const lowerCaseText = message.body.toLowerCase();
    const isPrivate = !chat.isGroup;
    
    // Handle monitor command for group chats
    if (chat.isGroup && !registeredChats.has(chat.id._serialized) && 
        (message.body === '/monitor' || lowerCaseText.includes('следи за этим чатом'))) {
      await registerChat(chat);
      await client.sendMessage(chat.id._serialized, 'Chat monitoring has been activated. I will now process messages from this group.');
      return; // Skip further processing of the command message
    }
    
    // Only process messages from registered chats for groups
    // For private messages, process them regardless of registration
    if (!isPrivate && !registeredChats.has(chat.id._serialized)) {
      return; // Skip processing for unregistered group chats
    }
    
    // Prepare message data
    const messageData = {
      message_id: message.id.id,
      source_name: "whatsapp",
      chat_id: chat.id._serialized,
      text: message.body,
      sender_id: contact.id._serialized,
      sender_name: contact.name || contact.pushname || contact.number || "Unknown",
      is_private: isPrivate
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
    console.log(`${isPrivate ? 'Private message' : 'Group message'} from ${messageData.sender_name} forwarded to processing service`);
    
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
// Endpoint to send a message
app.post('/send_message', async (req, res) => {
  try {
    const { user, text } = req.body;
    
    if (!user || !text) {
      return res.status(400).json({ 
        success: false, 
        error: 'Both user and text parameters are required' 
      });
    }

    // Check if user is a valid phone number or chat ID
    let chatId = user;
    
    // Send the message
    await client.sendMessage(chatId, text);
    
    console.log(`Message sent to ${chatId}: ${text}`);
    return res.status(200).json({ success: true });
  } catch (error) {
    console.error('Error sending message:', error.message);
    return res.status(500).json({ 
      success: false, 
      error: error.message 
    });
  }
});

// Start Express server
app.listen(PORT, () => {
  console.log(`WhatsApp service listening on port ${PORT}`);
});

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