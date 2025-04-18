import { NextRequest, NextResponse } from 'next/server';

const PRESENTATION_SERVICE_URL = process.env.PRESENTATION_SERVICE_URL || 'http://localhost:52003';

type Params = Promise<{ chatId: string }>;

export async function POST(
  request: NextRequest,
  { params }: { params: Params }
) {
  try {
    const resolvedParams = await params;
    const chatId = resolvedParams.chatId;
    const body = await request.json();
    const format = body.format || 'csv';

    const response = await fetch(`${PRESENTATION_SERVICE_URL}/generate_table/${chatId}`, {
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

    // Get the response as blob/text depending on the format
    if (format === 'csv') {
      const text = await response.text();
      return new NextResponse(text, {
        headers: {
          'Content-Type': 'text/csv',
        },
      });
    } else {
      const blob = await response.blob();
      return new NextResponse(blob, {
        headers: {
          'Content-Type': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        },
      });
    }
  } catch (error) {
    console.error('Table generation API error:', error);
    return NextResponse.json(
      { error: 'Failed to generate table' },
      { status: 500 }
    );
  }
}