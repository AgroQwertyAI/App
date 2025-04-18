import { NextRequest, NextResponse } from 'next/server';
import clientPromise from '@/util/mongodb';
import { ObjectId } from 'mongodb';
import { hash } from 'bcrypt';

type Params = Promise<{ id: string }>;

export async function GET(
    req: NextRequest,
    { params }: { params: Params }
) {
    try {
        const resolvedParams = await params;
        const id = resolvedParams.id;

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

        const user = await usersCollection.findOne(
            { _id: objectId },
            { projection: { password: 0 } }
        );

        if (!user) {
            return NextResponse.json(
                { error: 'User not found' },
                { status: 404 }
            );
        }

        return NextResponse.json(user);
    } catch (error) {
        console.error('Error fetching user:', error);
        return NextResponse.json(
            { error: 'Internal server error' },
            { status: 500 }
        );
    }
}

export async function PATCH(
    req: NextRequest,
    { params }: { params: Params }
) {
    try {
        const resolvedParams = await params;
        const id = resolvedParams.id;

        if (!id) {
            return NextResponse.json(
                { error: 'User ID is required' },
                { status: 400 }
            );
        }

        const { name, password } = await req.json();

        // Validate at least one field to update is provided
        if (!name && !password) {
            return NextResponse.json(
                { error: 'At least one field (name or password) is required for update' },
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

        // Check if user exists
        const existingUser = await usersCollection.findOne({ _id: objectId });
        if (!existingUser) {
            return NextResponse.json(
                { error: 'User not found' },
                { status: 404 }
            );
        }

        // Prepare update document
        const updateDoc: { name?: string; password?: string; updatedAt: Date } = {
            updatedAt: new Date()
        };

        if (name) {
            updateDoc.name = name;
        }

        if (password) {
            // Hash the password
            updateDoc.password = await hash(password, 10);
        }

        // Update the user
        await usersCollection.updateOne(
            { _id: objectId },
            { $set: updateDoc }
        );

        return NextResponse.json(
            { message: 'User updated successfully' },
            { status: 200 }
        );
    } catch (error) {
        console.error('Error updating user:', error);
        return NextResponse.json(
            { error: 'Internal server error' },
            { status: 500 }
        );
    }
}