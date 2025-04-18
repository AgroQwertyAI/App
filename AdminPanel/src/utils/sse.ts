// Store active connections with unique IDs
let clientIdCounter = 0;
export const clients = new Map<number, ReadableStreamDefaultController<any>>();

// Export function to get a new client ID
export function getNextClientId(): number {
  return clientIdCounter++;
}

// Helper function to broadcast messages to all clients
export function broadcastMessage(message: any) {
  const encoder = new TextEncoder();
  const data = encoder.encode(`data: ${JSON.stringify(message)}\n\n`);
  
  // Create a copy of client entries to avoid issues if the map changes during iteration
  const clientEntries = Array.from(clients.entries());
  console.log(JSON.stringify(message));
  console.log(`[SSE] Broadcasting to ${clientEntries.length} clients`);
  
  for (const [clientId, controller] of clientEntries) {
    try {
      controller.enqueue(data);
    } catch (error) {
      console.error(`[SSE] Error broadcasting to client ${clientId}:`, error);
      
      // Remove failed client
      clients.delete(clientId);
    }
  }
}

// Helper function to send a message to a single client
export function sendMessageToClient(clientId: number, message: any) {
  const controller = clients.get(clientId);
  if (!controller) return false;
  
  try {
    const encoder = new TextEncoder();
    const data = encoder.encode(`data: ${JSON.stringify(message)}\n\n`);
    controller.enqueue(data);
    return true;
  } catch (error) {
    console.error(`[SSE] Error sending to client ${clientId}:`, error);
    clients.delete(clientId);
    return false;
  }
}