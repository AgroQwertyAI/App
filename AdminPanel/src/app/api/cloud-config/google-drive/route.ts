import { NextRequest, NextResponse } from 'next/server';

const SERVICE_URL = process.env.FILE_SERVICE_URL + "/api" || 'http://localhost:52001/api';


export async function GET() {
  try {
    const response = await fetch(`${SERVICE_URL}/google-drive-credentials`);
    
    if (!response.ok) {
      const error = await response.json();
      return NextResponse.json(
        { error: error.detail || 'Failed to fetch Google Drive credentials' }, 
        { status: response.status }
      );
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

export async function POST(request: NextRequest) {
  try {
    const body = await request.json();
    
    const response = await fetch(`${SERVICE_URL}/google-drive-credentials`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(body),
    });
    
    if (!response.ok) {
      const error = await response.json();
      return NextResponse.json(
        { error: error.detail || 'Failed to save Google Drive credentials' }, 
        { status: response.status }
      );
    }
    
    const data = await response.json();
    return NextResponse.json(data, { status: 201 });
  } catch (error) {
    return NextResponse.json(
      { error: 'Failed to connect to service' }, 
      { status: 500 }
    );
  }
}