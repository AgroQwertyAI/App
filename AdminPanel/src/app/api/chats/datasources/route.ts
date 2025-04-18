import { NextRequest, NextResponse } from "next/server";

export async function GET(request: NextRequest) {
  // Hardcoded list of available data sources
  const datasources = ["whatsapp", "telegram"];
  
  return NextResponse.json( { datasources });
}