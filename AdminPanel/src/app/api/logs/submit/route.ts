import { NextRequest, NextResponse } from 'next/server';
import clientPromise from '@/util/mongodb';
import { sendLogToClients } from '@/app/api/logs/stream/log-service';

export async function POST(req: NextRequest) {
  try {
    const body = await req.json();
    const { message, level = 'info', source = 'app' } = body;

    if (!message) {
      return NextResponse.json({ error: "Message is required" }, { status: 400 });
    }

    const client = await clientPromise;
    const db = client.db("admin-panel");
    
    const logEntry = {
      message,
      level,
      source,
      timestamp: new Date()
    };

    // Store in database
    await db.collection("logs").insertOne(logEntry);
    
    // Send to all connected clients
    sendLogToClients(logEntry);
    
    return NextResponse.json({ success: true });
  } catch (error) {
    console.error("Failed to submit log:", error);
    return NextResponse.json(
      { error: "Failed to submit log" },
      { status: 500 }
    );
  }
}