import clientPromise from "@/util/mongodb";
import { NextResponse } from "next/server";

export async function GET() {
  try {
    const client = await clientPromise;
    const db = client.db("agro_admin");
    const settingsCollection = db.collection("settings");
    
    const setting = await settingsCollection.findOne({ key: "llms_list" });
    
    if (!setting) {
      return NextResponse.json({ llms: [] }, { status: 200 });
    }
    
    return NextResponse.json({ llms: setting.value }, { status: 200 });
  } catch (error) {
    console.error("Failed to get LLMs list:", error);
    return NextResponse.json({ error: "Failed to get LLMs list" }, { status: 500 });
  }
}

export async function POST(request: Request) {
  try {
    const { llms } = await request.json();
    
    if (!Array.isArray(llms)) {
      return NextResponse.json({ error: "Invalid LLMs list format" }, { status: 400 });
    }
    
    // Validate all items are strings
    if (!llms.every(item => typeof item === 'string')) {
      return NextResponse.json({ error: "All items in LLMs list must be strings" }, { status: 400 });
    }
    
    const client = await clientPromise;
    const db = client.db("agro_admin");
    const settingsCollection = db.collection("settings");
    
    await settingsCollection.updateOne(
      { key: "llms_list" },
      { $set: { key: "llms_list", value: llms } },
      { upsert: true }
    );
    
    return NextResponse.json({ success: true }, { status: 200 });
  } catch (error) {
    console.error("Failed to update LLMs list:", error);
    return NextResponse.json({ error: "Failed to update LLMs list" }, { status: 500 });
  }
}