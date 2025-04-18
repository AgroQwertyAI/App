import { NextRequest } from 'next/server';
import { clients } from './log-service';

export async function GET(req: NextRequest) {
  const clientId = crypto.randomUUID();
  
  // Create a new ReadableStream
  const stream = new ReadableStream({
    start(controller) {
      // Store the client reference
      const client = { id: clientId, controller };
      clients.add(client);
      
      // Send initial connection message
      controller.enqueue('data: {"connected":true}\n\n');
      
      // Keep connection alive with comment every 30 seconds
      const keepAliveInterval = setInterval(() => {
        controller.enqueue(': keepalive\n\n');
      }, 30000);
      
      // Clean up when client disconnects
      req.signal.addEventListener('abort', () => {
        clearInterval(keepAliveInterval);
        clients.delete(client); // Use the stored reference
      });
    }
  });

  return new Response(stream, {
    headers: {
      'Content-Type': 'text/event-stream',
      'Cache-Control': 'no-cache',
      'Connection': 'keep-alive'
    }
  });
}