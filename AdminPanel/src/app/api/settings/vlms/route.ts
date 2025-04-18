import clientPromise from "@/util/mongodb";
import { NextResponse } from "next/server";

export async function GET() {
  try {
    const client = await clientPromise;
    const db = client.db("agro_admin");
    const settingsCollection = db.collection("settings");
    
    const setting = await settingsCollection.findOne({ key: "vlms_list" });
    
    if (!setting) {
      return NextResponse.json({ vlms: [] }, { status: 200 });
    }
    
    return NextResponse.json({ vlms: setting.value }, { status: 200 });
  } catch (error) {
    console.error("Failed to get VLMs list:", error);
    return NextResponse.json({ error: "Failed to get VLMs list" }, { status: 500 });
  }
}

export async function POST(request: Request) {
  try {
    const { vlms } = await request.json();
    
    if (!Array.isArray(vlms)) {
      return NextResponse.json({ error: "Invalid VLMs list format" }, { status: 400 });
    }
    
    // Validate all items are strings
    if (!vlms.every(item => typeof item === 'string')) {
      return NextResponse.json({ error: "All items in VLMs list must be strings" }, { status: 400 });
    }
    
    const client = await clientPromise;
    const db = client.db("agro_admin");
    const settingsCollection = db.collection("settings");
    
    await settingsCollection.updateOne(
      { key: "vlms_list" },
      { $set: { key: "vlms_list", value: vlms } },
      { upsert: true }
    );
    
    return NextResponse.json({ success: true }, { status: 200 });
  } catch (error) {
    console.error("Failed to update VLMs list:", error);
    return NextResponse.json({ error: "Failed to update VLMs list" }, { status: 500 });
  }
}