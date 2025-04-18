import { NextRequest, NextResponse } from "next/server";
import clientPromise from "@/util/mongodb";

// Get chat by ID
export async function GET(
  request: NextRequest,
  { params }: { params: Promise<{ id: string }> }
) {
  try {
    const resolvedParams = await params;
    const id = resolvedParams.id;
    
    const client = await clientPromise;
    const db = client.db();
    
    const chat = await db.collection("chats").findOne({ chat_id: id });
    
    if (!chat) {
      return NextResponse.json({ 
        error: "Chat not found" 
      }, { status: 404 });
    }
    
    return NextResponse.json(chat);
  } catch (error: any) {
    console.error("Failed to retrieve chat:", error);
    return NextResponse.json({ error: error.message }, { status: 500 });
  }
}

// Update chat active status and template association
export async function PATCH(
  request: NextRequest,
  { params }: { params: Promise<{ id: string }> }
) {
  try {
    const resolvedParams = await params;
    const id = resolvedParams.id;
    const body = await request.json();
    const { active, template_id, setting_id } = body;
    
    // Validate active if provided
    if (active !== undefined && typeof active !== "boolean") {
      return NextResponse.json({ 
        error: "active status must be a boolean" 
      }, { status: 400 });
    }
    
    const client = await clientPromise;
    const db = client.db();
    
    // Build update object - only include fields that were provided
    const updateFields: any = { updated_at: new Date() };
    if (active !== undefined) updateFields.active = active;
    if (template_id !== undefined) updateFields.template_id = template_id;
    if (setting_id !== undefined) updateFields.setting_id = setting_id;
    
    const result = await db.collection("chats").updateOne(
      { chat_id: id },
      { $set: updateFields }
    );
    
    if (result.matchedCount === 0) {
      return NextResponse.json({ 
        error: "Chat not found" 
      }, { status: 404 });
    }
    
    return NextResponse.json({
      success: true,
      updated: result.modifiedCount > 0
    });
  } catch (error: any) {
    console.error("Failed to update chat:", error);
    return NextResponse.json({ error: error.message }, { status: 500 });
  }
}

export async function DELETE(
  request: NextRequest,
  { params }: { params: Promise<{ id: string }> }
) {
  try {
    const resolvedParams = await params;
    const id = resolvedParams.id;
    
    const client = await clientPromise;
    const db = client.db();
    
    const result = await db.collection("chats").deleteOne({ chat_id: id });
    
    if (result.deletedCount === 0) {
      return NextResponse.json({ 
        error: "Chat not found" 
      }, { status: 404 });
    }
    
    return NextResponse.json({
      success: true,
      deleted: true
    });
  } catch (error: any) {
    console.error("Failed to delete chat:", error);
    return NextResponse.json({ error: error.message }, { status: 500 });
  }
}