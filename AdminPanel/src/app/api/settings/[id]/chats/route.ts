import { NextRequest, NextResponse } from "next/server";
import clientPromise from "@/util/mongodb";

type Params = Promise<{ id: string }>;

export async function GET(
  request: NextRequest,
  { params }: { params: Params }
) {
  try {
    const resolvedParams = await params;
    const settingId = resolvedParams.id;
    
    const client = await clientPromise;
    const db = client.db();
    
    // Find all chats associated with this setting
    const chats = await db.collection("chats")
      .find({ setting_id: settingId })
      .project({ 
        chat_id: 1, 
        chat_name: 1, 
        source_name: 1,
        _id: 0 
      })
      .toArray();
    
    return NextResponse.json({
      chats: chats.map(chat => chat.chat_id)
    });
  } catch (error: any) {
    console.error("Failed to fetch setting chats:", error);
    return NextResponse.json({ error: error.message }, { status: 500 });
  }
}