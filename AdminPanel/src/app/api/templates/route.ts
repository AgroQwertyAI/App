// src/app/api/templates/route.ts
import { NextRequest, NextResponse } from 'next/server';
import { MongoClient, Db, Collection, ObjectId } from 'mongodb';
import clientPromise from '@/util/mongodb'; // Adjust path if needed

// Define the Template structure for the database
interface TemplateDocument {
    _id?: ObjectId;
    name: string;
    columns: string[];
    taskSplitPrompt: string;
    systemPrompt: string;
    createdAt: Date;
    updatedAt: Date;
}

let client: MongoClient;
let db: Db;
let templates: Collection<TemplateDocument>;

// Function to initialize DB connection (cached)
async function initDb() {
    if (db && client) {
         return;
    }
    try {
        client = await clientPromise;
        db = client.db();
        templates = db.collection<TemplateDocument>('templates');
    } catch (error) {
        console.error("Failed to connect to the database:", error);
        // @ts-ignore
        db = undefined;
        // @ts-ignore
        templates = undefined;
        throw new Error('Failed to connect to the database.');
    }
}

// Simplified handler wrapper that matches NextJS expected types
async function withDbConnection(req: NextRequest): Promise<Response> {
    try {
        await initDb();
        if (!db || !templates) {
            throw new Error('Database connection is not available.');
        }
        return Promise.resolve(new NextResponse('DB Connection successful', { status: 200 }));
    } catch (error: any) {
        console.error("API Route Error:", error);
        const message = error.message || 'An internal server error occurred.';
        const status = typeof error.status === 'number' ? error.status : 500;
        return NextResponse.json({ error: message }, { status });
    }
}

// --- API Handlers ---

// GET /api/templates - Fetch all templates
// GET /api/templates?id={templateId} - Fetch a single template
export async function GET(req: NextRequest): Promise<Response> {
    try {
        await initDb();
        if (!db || !templates) {
            throw new Error('Database connection is not available.');
        }
        
        const { searchParams } = new URL(req.url);
        const id = searchParams.get('id');
        
        if (id) {
            if (!ObjectId.isValid(id)) {
                return NextResponse.json({ error: 'Invalid template ID format' }, { status: 400 });
            }
            const template = await templates.findOne({ _id: new ObjectId(id) });
            if (!template) {
                return NextResponse.json({ error: 'Template not found' }, { status: 404 });
            }
            return NextResponse.json(template);
        } else {
            const allTemplates = await templates.find({}, { projection: { name: 1, _id: 1 } }).sort({ name: 1 }).toArray();
            return NextResponse.json(allTemplates);
        }
    } catch (error: any) {
        console.error("API Route Error:", error);
        const message = error.message || 'An internal server error occurred.';
        const status = typeof error.status === 'number' ? error.status : 500;
        return NextResponse.json({ error: message }, { status });
    }
}

// POST /api/templates - Create a new template
export async function POST(req: NextRequest): Promise<Response> {
    try {
        await initDb();
        if (!db || !templates) {
            throw new Error('Database connection is not available.');
        }
        
        let body;
        try {
            body = await req.json();
        } catch (e) {
            return NextResponse.json({ error: 'Invalid JSON body' }, { status: 400 });
        }
        
        const { name, columns, taskSplitPrompt, systemPrompt } = body;

        // Validation checks
        if (!name || typeof name !== 'string' || name.trim() === '' ||
            !Array.isArray(columns) ||
            typeof taskSplitPrompt !== 'string' ||
            typeof systemPrompt !== 'string') {
            return NextResponse.json({ error: 'Missing or invalid required fields (name, columns, taskSplitPrompt, systemPrompt)' }, { status: 400 });
        }

        if (columns.length === 0 || columns.some(col => typeof col !== 'string' || col.trim() === '')) {
             return NextResponse.json({ error: 'Columns array cannot be empty and must contain non-empty strings' }, { status: 400 });
        }

        const newTemplate: Omit<TemplateDocument, '_id'> = {
            name: name.trim(),
            columns,
            taskSplitPrompt,
            systemPrompt,
            createdAt: new Date(),
            updatedAt: new Date(),
        };

        try {
            const result = await templates.insertOne(newTemplate);
            const createdTemplate = await templates.findOne({ _id: result.insertedId });
            return NextResponse.json(createdTemplate, { status: 201 });
        } catch (error: any) {
             console.error("Error inserting template:", error);
             if (error.code === 11000) {
                 return NextResponse.json({ error: 'A template with this name might already exist.' }, { status: 409 });
             }
             return NextResponse.json({ error: 'Failed to create template.' }, { status: 500 });
        }
    } catch (error: any) {
        console.error("API Route Error:", error);
        const message = error.message || 'An internal server error occurred.';
        const status = typeof error.status === 'number' ? error.status : 500;
        return NextResponse.json({ error: message }, { status });
    }
}

// PUT /api/templates?id={templateId} - Update an existing template
export async function PUT(req: NextRequest): Promise<Response> {
    try {
        await initDb();
        if (!db || !templates) {
            throw new Error('Database connection is not available.');
        }
        
        const { searchParams } = new URL(req.url);
        const id = searchParams.get('id');
        
        if (!id || !ObjectId.isValid(id)) {
            return NextResponse.json({ error: 'Invalid or missing template ID' }, { status: 400 });
        }

        let body;
        try {
            body = await req.json();
        } catch (e) {
            return NextResponse.json({ error: 'Invalid JSON body' }, { status: 400 });
        }
        
        const { name, columns, taskSplitPrompt, systemPrompt } = body;

        // Validation logic 
        if (!name || typeof name !== 'string' || name.trim() === '' ||
            !Array.isArray(columns) ||
            typeof taskSplitPrompt !== 'string' ||
            typeof systemPrompt !== 'string') {
            return NextResponse.json({ error: 'Missing or invalid required fields for update (name, columns, taskSplitPrompt, systemPrompt)' }, { status: 400 });
        }
        
        if (columns.length === 0 || columns.some(col => typeof col !== 'string' || col.trim() === '')) {
            return NextResponse.json({ error: 'Columns array cannot be empty and must contain non-empty strings' }, { status: 400 });
        }

        const updateData = {
            name: name.trim(),
            columns,
            taskSplitPrompt,
            systemPrompt,
            updatedAt: new Date(),
        };

        try {
            const result = await templates.updateOne(
                { _id: new ObjectId(id) },
                { $set: updateData }
            );

            if (result.matchedCount === 0) {
                return NextResponse.json({ error: 'Template not found' }, { status: 404 });
            }
            
            const updatedTemplate = await templates.findOne({ _id: new ObjectId(id) });
            if (!updatedTemplate) {
                return NextResponse.json({ error: 'Template found but failed to retrieve after update.' }, { status: 500 });
            }
            
            return NextResponse.json(updatedTemplate);
        } catch (error: any) {
            console.error(`Error updating template ${id}:`, error);
            if (error.code === 11000) {
                return NextResponse.json({ error: 'Update failed, potentially due to duplicate name.' }, { status: 409 });
            }
            return NextResponse.json({ error: 'Failed to update template.' }, { status: 500 });
        }
    } catch (error: any) {
        console.error("API Route Error:", error);
        const message = error.message || 'An internal server error occurred.';
        const status = typeof error.status === 'number' ? error.status : 500;
        return NextResponse.json({ error: message }, { status });
    }
}

// DELETE /api/templates?id={templateId} - Delete a template
export async function DELETE(req: NextRequest): Promise<Response> {
    try {
        await initDb();
        if (!db || !templates) {
            throw new Error('Database connection is not available.');
        }
        
        const { searchParams } = new URL(req.url);
        const id = searchParams.get('id');
        
        if (!id || !ObjectId.isValid(id)) {
            return NextResponse.json({ error: 'Invalid or missing template ID' }, { status: 400 });
        }

        try {
            const result = await templates.deleteOne({ _id: new ObjectId(id) });

            if (result.deletedCount === 0) {
                return NextResponse.json({ error: 'Template not found' }, { status: 404 });
            }

            return NextResponse.json({ message: 'Template deleted successfully' }, { status: 200 });
        } catch (error: any) {
            console.error(`Error deleting template ${id}:`, error);
            return NextResponse.json({ error: 'Failed to delete template.' }, { status: 500 });
        }
    } catch (error: any) {
        console.error("API Route Error:", error);
        const message = error.message || 'An internal server error occurred.';
        const status = typeof error.status === 'number' ? error.status : 500;
        return NextResponse.json({ error: message }, { status });
    }
}