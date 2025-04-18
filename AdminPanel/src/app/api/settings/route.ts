import { NextRequest, NextResponse } from 'next/server';

const SERVICE_URL = process.env.SAVE_SERVICE_URL || 'http://localhost:52001/api';

export async function GET(request: NextRequest) {
  const { searchParams } = new URL(request.url);
  const offset = searchParams.get('offset') || '0';
  const limit = searchParams.get('limit') || '10';
  const showDeleted = searchParams.get('show_deleted') || 'false';
  
  try {
    const response = await fetch(
      `${SERVICE_URL}/settings?offset=${offset}&limit=${limit}&show_deleted=${showDeleted}`,
      { method: 'GET' }
    );
    
    if (!response.ok) {
      const error = await response.json();
      return NextResponse.json({ error: error.detail || 'Failed to fetch settings' }, 
        { status: response.status });
    }
    
    const data = await response.json();
    return NextResponse.json(data);
  } catch (error) {
    return NextResponse.json(
      { error: 'Failed to connect to service' }, 
      { status: 500 }
    );
  }
}