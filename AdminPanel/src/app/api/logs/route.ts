import { NextResponse } from 'next/server';
import clientPromise from '@/util/mongodb';

export async function GET() {
  try {
    const client = await clientPromise;
    const db = client.db("admin-panel");
    
    // Get the most recent logs (limited to 100)
    const logs = await db.collection("logs")
      .find({})
      .sort({ timestamp: -1 })
      .limit(100)
      .toArray();
    
    return NextResponse.json(logs);
  } catch (error) {
    console.error("Failed to fetch logs:", error);
    return NextResponse.json(
      { error: "Failed to fetch logs" },
      { status: 500 }
    );
  }
}