import clientPromise from "@/util/mongodb";
import { NextResponse } from "next/server";

export async function GET() {
  try {
    const client = await clientPromise;
    const db = client.db("agro_admin");
    const settingsCollection = db.collection("settings");
    
    const setting = await settingsCollection.findOne({ key: "dashboard_chat_id" });
    
    if (!setting) {
      return NextResponse.json({ dashboard_chat_id: "" }, { status: 200 });
    }
    
    return NextResponse.json({ dashboard_chat_id: setting.value }, { status: 200 });
  } catch (error) {
    console.error("Failed to get dashboard chat ID:", error);
    return NextResponse.json({ error: "Failed to get dashboard chat ID" }, { status: 500 });
  }
}

export async function POST(request: Request) {
  try {
    const { dashboard_chat_id } = await request.json();
    
    if (typeof dashboard_chat_id !== 'string') {
      return NextResponse.json({ error: "Dashboard chat ID must be a string" }, { status: 400 });
    }
    
    const client = await clientPromise;
    const db = client.db("agro_admin");
    const settingsCollection = db.collection("settings");
    
    await settingsCollection.updateOne(
      { key: "dashboard_chat_id" },
      { $set: { key: "dashboard_chat_id", value: dashboard_chat_id } },
      { upsert: true }
    );
    
    return NextResponse.json({ success: true }, { status: 200 });
  } catch (error) {
    console.error("Failed to update dashboard chat ID:", error);
    return NextResponse.json({ error: "Failed to update dashboard chat ID" }, { status: 500 });
  }
}