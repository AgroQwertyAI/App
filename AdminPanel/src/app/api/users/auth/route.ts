import { NextRequest, NextResponse } from 'next/server';
import clientPromise from '@/util/mongodb';
import { compare } from 'bcrypt';

export async function POST(req: NextRequest) {
  try {
    const { username, password } = await req.json();
    
    // Validate input
    if (!username || !password) {
      return NextResponse.json(
        { error: 'Username and password are required' },
        { status: 400 }
      );
    }
    
    const client = await clientPromise;
    const db = client.db('agro');
    const usersCollection = db.collection('users');
    
    // Find user by username
    const user = await usersCollection.findOne({ username });
    
    if (!user) {
      return NextResponse.json(
        { error: 'Invalid username or password' },
        { status: 401 }
      );
    }
    
    // Compare password
    const isValidPassword = await compare(password, user.password);
    
    if (!isValidPassword) {
      return NextResponse.json(
        { error: 'Invalid username or password' },
        { status: 401 }
      );
    }
    
    // Return user info (excluding password)
    return NextResponse.json({
      id: user._id.toString(),
      name: user.name,
      username: user.username,
      role: user.role,
    });
  } catch (error) {
    console.error('Auth error:', error);
    return NextResponse.json(
      { error: 'Internal server error' },
      { status: 500 }
    );
  }
}