import clientPromise from "@/util/mongodb";
import { NextResponse } from "next/server";

export async function GET() {
  try {
    const client = await clientPromise;
    const db = client.db("agro_admin");
    const settingsCollection = db.collection("settings");
    
    // Get the LLM endpoint setting or create with default if it doesn't exist
    const setting = await settingsCollection.findOne({ key: "llm_endpoint" });
    
    if (!setting) {
      return NextResponse.json({ llm_endpoint: "" }, { status: 200 });
    }
    
    return NextResponse.json({ llm_endpoint: setting.value }, { status: 200 });
  } catch (error) {
    console.error("Failed to get LLM endpoint:", error);
    return NextResponse.json({ error: "Failed to get LLM endpoint" }, { status: 500 });
  }
}

export async function POST(request: Request) {
  try {
    const { url } = await request.json();
    
    if (!url || typeof url !== 'string') {
      return NextResponse.json({ error: "Invalid URL provided" }, { status: 400 });
    }
    
    const client = await clientPromise;
    const db = client.db("agro_admin");
    const settingsCollection = db.collection("settings");
    
    // Upsert the LLM endpoint setting
    await settingsCollection.updateOne(
      { key: "llm_endpoint" },
      { $set: { key: "llm_endpoint", value: url } },
      { upsert: true }
    );
    
    return NextResponse.json({ success: true }, { status: 200 });
  } catch (error) {
    console.error("Failed to update LLM endpoint:", error);
    return NextResponse.json({ error: "Failed to update LLM endpoint" }, { status: 500 });
  }
}