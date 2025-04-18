// Client management and log distribution functionality

// Map to store connected clients
export const clients = new Set<{
  id: string;
  controller: ReadableStreamDefaultController;
}>();

// Function to send log to all connected clients
export function sendLogToClients(log: any) {
  clients.forEach(client => {
    try {
      const data = `data: ${JSON.stringify(log)}\n\n`;
      client.controller.enqueue(data);
    } catch (error) {
      console.error("Error sending log to client:", error);
    }
  });
}