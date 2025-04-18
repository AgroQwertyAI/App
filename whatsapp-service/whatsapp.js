const qrcode = require('qrcode-terminal');
const { Client, LocalAuth, MessageMedia } = require('whatsapp-web.js');
const axios = require('axios');
const fs = require('fs');
const express = require('express');
require('dotenv').config();

// Environment variables
const DATA_SERVICE_URL = process.env.DATA_SERVICE_URL;
const MESSAGE_PROCESSING_SERVICE_URL = process.env.MESSAGE_PROCESSING_SERVICE_URL;
const PORT = process.env.PORT || 52101;

if (!DATA_SERVICE_URL || !MESSAGE_PROCESSING_SERVICE_URL) {
  console.error('Environment variables DATA_SERVICE_URL and MESSAGE_PROCESSING_SERVICE_URL must be set');
  process.exit(1);
}

// Initialize Express server
const app = express();
app.use(express.json());
app.use(express.urlencoded({ extended: true }));


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
    await axios.post(`${DATA_SERVICE_URL}/api/settings/whatsapp_qr`, { qr_code: qr });
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
    if (chat.isGroup  && 
        (message.body === '/monitor' || lowerCaseText.includes('следи за этим чатом'))) {
      await registerChat(chat);
      await client.sendMessage(chat.id._serialized, 'Chat monitoring has been activated. I will now process messages from this group.');
      return; // Skip further processing of the command message
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
        // Check if this is a voice message (ptt = Push To Talk)
        if (message.type === 'ptt') {
          messageData['voice'] = `data:${media.mimetype};base64,${media.data}`;
          console.log('Voice message detected and processed');
        } else {
          messageData['image'] = `data:${media.mimetype};base64,${media.data}`;
        }
      }
    }
    
    // Send to message processing service
    await axios.post(`${MESSAGE_PROCESSING_SERVICE_URL}/new_message`, messageData);
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
    
    const response = await axios.post(`${DATA_SERVICE_URL}/api/chats`, {
      chat_id: chatId,
      chat_name: chat.name || "Unknown Group",
      source_name: "whatsapp"
    });
    
    if (response.data.success || response.status === 409) { // Success or already exists
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

app.post('/send_image', async (req, res) => {
  try {
    const { user, image } = req.body;
    
    if (!user || !image) {
      return res.status(400).json({ 
        success: false, 
        error: 'Both user and image parameters are required' 
      });
    }

    let media;
    
    // Handle different image formats
    if (typeof image === 'string') {
      // If image is a URL
      if (image.startsWith('http://') || image.startsWith('https://')) {
        try {
          const response = await axios.get(image, { responseType: 'arraybuffer' });
          const mimeType = response.headers['content-type'];
          const imageBuffer = Buffer.from(response.data, 'binary').toString('base64');
          media = new MessageMedia(mimeType, imageBuffer);
        } catch (error) {
          return res.status(400).json({
            success: false,
            error: `Failed to download image from URL: ${error.message}`
          });
        }
      } 
      // If image is a base64 string (possibly with data URI)
      else {
        try {
          // Handle data URI format (data:image/jpeg;base64,...)
          if (image.startsWith('data:')) {
            const matches = image.match(/^data:([A-Za-z-+\/]+);base64,(.+)$/);
            if (matches && matches.length === 3) {
              const mimeType = matches[1];
              const base64Data = matches[2];
              media = new MessageMedia(mimeType, base64Data);
            } else {
              throw new Error('Invalid data URI format');
            }
          } 
          // Plain base64 string
          else {
            media = new MessageMedia('image/jpeg', image); // Default to JPEG if no MIME type provided
          }
        } catch (error) {
          return res.status(400).json({
            success: false,
            error: `Invalid image data: ${error.message}`
          });
        }
      }
    } else {
      return res.status(400).json({
        success: false,
        error: 'Image must be a URL or base64 encoded string'
      });
    }
    
    // Send the image
    await client.sendMessage(user, media);
    
    console.log(`Image sent to ${user}`);
    return res.status(200).json({ success: true });
  } catch (error) {
    console.error('Error sending image:', error.message);
    return res.status(500).json({ 
      success: false, 
      error: error.message 
    });
  }
});

// Add this endpoint for sending files
app.post('/send_file', async (req, res) => {
  try {
    const { user, file, filename, caption } = req.body;
    
    if (!user || !file) {
      return res.status(400).json({ 
        success: false, 
        error: 'Both user and file parameters are required' 
      });
    }

    let media;
    
    // Handle different file formats
    if (typeof file === 'string') {
      // If file is a URL
      if (file.startsWith('http://') || file.startsWith('https://')) {
        try {
          const response = await axios.get(file, { responseType: 'arraybuffer' });
          const mimeType = response.headers['content-type'];
          const fileBuffer = Buffer.from(response.data, 'binary').toString('base64');
          media = new MessageMedia(mimeType, fileBuffer, filename || 'file');
        } catch (error) {
          return res.status(400).json({
            success: false,
            error: `Failed to download file from URL: ${error.message}`
          });
        }
      } 
      // If file is a base64 string (possibly with data URI)
      else if (file.startsWith('data:')) {
        try {
          const matches = file.match(/^data:([A-Za-z-+.\/]+);base64,(.+)$/);
          if (matches && matches.length === 3) {
            const mimeType = matches[1];
            const base64Data = matches[2];
            media = new MessageMedia(mimeType, base64Data, filename || 'file');
          } else {
            throw new Error('Invalid data URI format');
          }
        } catch (error) {
          return res.status(400).json({
            success: false,
            error: `Invalid file data: ${error.message}`
          });
        }
      }
      // Plain base64 string
      else {
        const mimeType = req.body.mimetype || 'application/octet-stream';
        media = new MessageMedia(mimeType, file, filename || 'file');
      }
    } else {
      return res.status(400).json({
        success: false,
        error: 'File must be a URL or base64 encoded string'
      });
    }
    
    // Send the file with optional caption
    const options = {};
    if (caption) {
      options.caption = caption;
    }
    
    await client.sendMessage(user, media, options);
    
    console.log(`File sent to ${user}${filename ? ` (${filename})` : ''}`);
    return res.status(200).json({ success: true });
  } catch (error) {
    console.error('Error sending file:', error.message);
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