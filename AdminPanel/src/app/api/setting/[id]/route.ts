import { NextRequest, NextResponse } from 'next/server';

const SERVICE_URL = process.env.SAVE_SERVICE_URL || 'http://localhost:52001/api';

type Params = Promise<{ id: string }>;

export async function PUT(
  request: NextRequest,
  segmentData: { params: Params }
) {
  const params = await segmentData.params;
  const id = params.id;
  
  try {
    const body = await request.json();
    
    const response = await fetch(`${SERVICE_URL}/setting/${id}`, {
      method: 'PUT',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(body),
    });
    
    if (!response.ok) {
      const error = await response.json();
      return NextResponse.json(
        { error: error.detail || 'Failed to update setting' }, 
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

export async function DELETE(
  request: NextRequest,
  segmentData: { params: Params }
) {
  const params = await segmentData.params;
  const id = params.id;
  
  try {
    const response = await fetch(`${SERVICE_URL}/setting/${id}`, {
      method: 'DELETE',
    });
    
    if (!response.ok) {
      const error = await response.json();
      return NextResponse.json(
        { error: error.detail || 'Failed to delete setting' }, 
        { status: response.status }
      );
    }
    
    return new NextResponse(null, { status: 204 });
  } catch (error) {
    return NextResponse.json(
      { error: 'Failed to connect to service' }, 
      { status: 500 }
    );
  }
}