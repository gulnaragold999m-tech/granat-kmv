import { NextRequest, NextResponse } from 'next/server';

export async function POST(request: NextRequest) {
  try {
    const body = await request.json();
    const { name, phone, email, consent } = body;

    if (!name || !phone || !consent) {
      return NextResponse.json(
        { error: 'Missing required fields or consent not given' },
        { status: 400 }
      );
    }

    console.log('Lead received:', { name, phone, email, timestamp: new Date() });

    return NextResponse.json(
      { success: true, message: 'Заявка получена' },
      { status: 200 }
    );
  } catch (error) {
    console.error('Error processing lead:', error);
    return NextResponse.json(
      { error: 'Internal server error' },
      { status: 500 }
    );
  }
}
