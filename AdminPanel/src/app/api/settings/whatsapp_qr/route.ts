import { NextResponse } from 'next/server';
import clientPromise from '@/util/mongodb';

export async function POST(request: Request) {
  try {
    // Parse the request body to get the QR code
    const { qr_code } = await request.json();
    
    if (!qr_code) {
      return NextResponse.json(
        { success: false, message: 'QR code is required' },
        { status: 400 }
      );
    }

    // Connect to MongoDB
    const client = await clientPromise;
    const db = client.db('agro'); // Replace with your actual database name
    
    // Update or insert the QR code in settings collection
    // Using upsert to create if not exists
    const result = await db.collection('settings').updateOne(
      { setting_type: 'whatsapp_qr' },
      { 
        $set: { 
          value: qr_code,
          updated_at: new Date()
        }
      },
      { upsert: true }
    );

    return NextResponse.json({ 
      success: true, 
      message: 'WhatsApp QR code saved successfully'
    });
    
  } catch (error) {
    console.error('Error saving WhatsApp QR code:', error);
    return NextResponse.json(
      { success: false, message: 'Failed to save QR code' },
      { status: 500 }
    );
  }
}

export async function GET() {
    try {
      // Connect to MongoDB
      const client = await clientPromise;
      const db = client.db('agro');
      
      // Query for the WhatsApp QR code setting
      const qrSetting = await db.collection('settings').findOne({ setting_type: 'whatsapp_qr' });
      
      if (!qrSetting) {
        return NextResponse.json(
          { success: false, message: 'WhatsApp QR code not found' },
          { status: 404 }
        );
      }
      
      return NextResponse.json({ 
        success: true, 
        data: { qr_code: qrSetting.value }
      });
      
    } catch (error) {
      console.error('Error retrieving WhatsApp QR code:', error);
      return NextResponse.json(
        { success: false, message: 'Failed to retrieve QR code' },
        { status: 500 }
      );
    }
  }