import { NextRequest, NextResponse } from 'next/server';

const PRESENTATION_SERVICE_URL = process.env.PRESENTATION_SERVICE_URL || 'http://localhost:52003';

export async function GET(request: NextRequest) {
  try {
    // Extract query parameters
    const searchParams = request.nextUrl.searchParams;
    const chat_id = searchParams.get('chat_id');
    const format = searchParams.get('format');

    // Validate required parameters
    if (!chat_id) {
      return NextResponse.json(
        { error: 'Missing required parameter: chat_id' },
        { status: 400 }
      );
    }

    // Construct the target URL
    const targetUrl = `${PRESENTATION_SERVICE_URL}/generate_table?chat_id=${encodeURIComponent(chat_id)}&format=${format || 'csv'}`;

    // Forward the request
    const response = await fetch(targetUrl);

    if (!response.ok) {
      const errorText = await response.text();
      return NextResponse.json(
        { error: errorText || `Service error: ${response.status}` },
        { status: response.status }
      );
    }

    // Get content type for proper response formatting
    const contentType = response.headers.get('content-type');
    const blob = await response.blob();

    // Create appropriate response with correct content type
    const result = new NextResponse(blob);
    
    // Set appropriate content type header based on the format
    if (format === 'xlsx') {
      result.headers.set('content-type', 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet');
      result.headers.set('content-disposition', `attachment; filename="report.xlsx"`);
    } else {
      result.headers.set('content-type', 'text/csv');
      result.headers.set('content-disposition', `attachment; filename="report.csv"`);
    }

    return result;

  } catch (error: any) {
    console.error('Error in generate_table API route:', error);
    return NextResponse.json(
      { error: error.message || 'Internal server error' },
      { status: 500 }
    );
  }
}