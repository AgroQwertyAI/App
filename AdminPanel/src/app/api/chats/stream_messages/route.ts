import { NextRequest } from "next/server";
import { clients, getNextClientId, broadcastMessage } from "@/utils/sse";

export async function GET(request: NextRequest) {
  const encoder = new TextEncoder();
  const clientId = getNextClientId();
  
  console.log(`[SSE] New client connected: ${clientId}. Total clients: ${clients.size + 1}`);

  // Create a new readable stream
  const stream = new ReadableStream({
    start(controller) {
      // Add this client to the map of connections
      clients.set(clientId, controller);

      // Send initial connection message
      const data = encoder.encode(`data: ${JSON.stringify({ 
        type: "connection_established", 
        clientId,
        timestamp: new Date().toISOString() 
      })}\n\n`);
      controller.enqueue(data);
      
      // Remove client when connection closes
      request.signal.addEventListener("abort", () => {
        clients.delete(clientId);
        console.log(`[SSE] Client ${clientId} disconnected. Remaining clients: ${clients.size}`);
      });
    }
  });

  return new Response(stream, {
    headers: {
      "Content-Type": "text/event-stream",
      "Cache-Control": "no-cache, no-transform",
      "Connection": "keep-alive",
      "Access-Control-Allow-Origin": "*"
    }
  });
}

// Send heartbeat to all clients periodically to keep connections alive
setInterval(() => {
  const timestamp = new Date().toISOString();
  console.log(`[SSE] Sending heartbeat to ${clients.size} clients`);
  
  broadcastMessage({
    type: "heartbeat",
    timestamp
  });
}, 30000); // Every 30 seconds