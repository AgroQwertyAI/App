import { NextRequest, NextResponse } from "next/server";
import clientPromise from "@/util/mongodb";

type Params = Promise<{ chat_id: string }>;

export async function GET(
  request: NextRequest,
  { params }: { params: Params }
) {
  try {
    const chat_id = (await params).chat_id;
    const { searchParams } = new URL(request.url);
    
    const client = await clientPromise;
    const db = client.db();
    
    const messages = await db.collection("messages")
      .find({ chat_id })
      .sort({ timestamp: 1 })
      .toArray();
    
    return NextResponse.json(messages);
  } catch (error: any) {
    console.error("Failed to fetch messages:", error);
    return NextResponse.json({ error: error.message }, { status: 500 });
  }
}

