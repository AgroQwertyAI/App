import { NextRequest, NextResponse } from 'next/server';

const PRESENTATION_SERVICE_URL = process.env.PRESENTATION_SERVICE_URL || 'http://localhost:52003';

export async function POST(
  request: NextRequest,
  { params }: { params: Promise<{ chatId: string }> }
) {
  try {
    const {chatId} = await params;
    const body = await request.json();

    const response = await fetch(`${PRESENTATION_SERVICE_URL}/generate_chart/${chatId}`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(body),
    });

    if (!response.ok) {
      return NextResponse.json(
        { error: `Error from presentation service: ${response.statusText}` },
        { status: response.status }
      );
    }

    const data = await response.json();
    return NextResponse.json(data);
  } catch (error) {
    console.error('Chart generation API error:', error);
    return NextResponse.json(
      { error: 'Failed to generate chart' },
      { status: 500 }
    );
  }
}