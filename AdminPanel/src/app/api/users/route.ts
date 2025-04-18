import { NextRequest, NextResponse } from 'next/server';
import clientPromise from '@/util/mongodb';
import { hash } from 'bcrypt';

import {ObjectId} from 'mongodb';

export async function GET() {
  try {
    const client = await clientPromise;
    const db = client.db('agro');
    const usersCollection = db.collection('users');
    
    // Find all users but exclude password field
    const users = await usersCollection.find({}).project({ password: 0 }).toArray();
    
    return NextResponse.json(users);
  } catch (error) {
    console.error('Error fetching users:', error);
    return NextResponse.json(
      { error: 'Internal server error' },
      { status: 500 }
    );
  }
}

export async function POST(req: NextRequest) {
  try {
    const { username, password, name, role } = await req.json();
    
    // Validate input
    if (!username || !password || !name || !role) {
      return NextResponse.json(
        { error: 'Missing required fields' },
        { status: 400 }
      );
    }
    
    const client = await clientPromise;
    const db = client.db('agro');
    const usersCollection = db.collection('users');
    
    // Check if user already exists
    const existingUser = await usersCollection.findOne({ username });
    if (existingUser) {
      return NextResponse.json(
        { error: 'Username already exists' },
        { status: 409 }
      );
    }
    
    // Hash the password
    const hashedPassword = await hash(password, 10);
    
    // Create user
    const result = await usersCollection.insertOne({
      username,
      password: hashedPassword,
      name,
      role,
      createdAt: new Date(),
    });
    
    return NextResponse.json({
      id: result.insertedId.toString(),
      username,
      name,
      role,
    }, { status: 201 });
  } catch (error) {
    console.error('Error creating user:', error);
    return NextResponse.json(
      { error: 'Internal server error' },
      { status: 500 }
    );
  }
}

export async function DELETE(req: NextRequest) {
  try {
    const { searchParams } = new URL(req.url);
    const id = searchParams.get('id');
    
    if (!id) {
      return NextResponse.json(
        { error: 'User ID is required' },
        { status: 400 }
      );
    }
    
    const client = await clientPromise;
    const db = client.db('agro');
    const usersCollection = db.collection('users');
    
    let objectId;
    
    try {
      objectId = new ObjectId(id);
    } catch (error) {
      return NextResponse.json(
        { error: 'Invalid user ID format' },
        { status: 400 }
      );
    }
    
    const result = await usersCollection.deleteOne({ _id: objectId });
    
    if (result.deletedCount === 0) {
      return NextResponse.json(
        { error: 'User not found' },
        { status: 404 }
      );
    }
    
    return NextResponse.json(
      { message: 'User deleted successfully' },
      { status: 200 }
    );
  } catch (error) {
    console.error('Error deleting user:', error);
    return NextResponse.json(
      { error: 'Internal server error' },
      { status: 500 }
    );
  }
}