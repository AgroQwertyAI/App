import { NextRequest, NextResponse } from "next/server";
import clientPromise from "@/util/mongodb";

// Get chats for a specific data source
export async function GET(request: NextRequest) {
  try {
    const { searchParams } = new URL(request.url);
    const source_name = searchParams.get("source_name");
    
    if (!source_name) {
      return NextResponse.json({ error: "source_name parameter is required" }, { status: 400 });
    }
    
    const client = await clientPromise;
    const db = client.db();
    
    const chats = await db.collection("chats")
      .find({ source_name })
      .project({ 
        chat_id: 1, 
        chat_name: 1, 
        active: 1, 
        source_name: 1,
        setting_id: 1,  // Add this line to include setting_id
        _id: 0 
      })
      .toArray();
    
    return NextResponse.json({ chats });
  } catch (error: any) {
    console.error("Failed to fetch chats:", error);
    return NextResponse.json({ error: error.message }, { status: 500 });
  }
}

// Create a new chat
export async function POST(request: NextRequest) {
  try {
    const body = await request.json();
    const { chat_id, chat_name, source_name } = body;
    
    if (!chat_id || !chat_name || !source_name) {
      return NextResponse.json({ 
        error: "chat_id, chat_name, and source_name are required" 
      }, { status: 400 });
    }
    
    const client = await clientPromise;
    const db = client.db();
    
    // Check if chat already exists
    const existingChat = await db.collection("chats").findOne({ 
      chat_id, 
      source_name 
    });
    
    if (existingChat) {
      return NextResponse.json({ 
        error: "Chat with this ID and source already exists" 
      }, { status: 409 });
    }
    
    // Create new chat with active=true by default
    const result = await db.collection("chats").insertOne({
      chat_id,
      chat_name,
      source_name,
      active: false,
      created_at: new Date()
    });
    
    return NextResponse.json({
      success: true,
      chat_id,
      insertedId: result.insertedId
    });
  } catch (error: any) {
    console.error("Failed to create chat:", error);
    return NextResponse.json({ error: error.message }, { status: 500 });
  }
}