'use client'

import { useState } from 'react'

export default function Home() {
  const [text, setText] = useState('')

  return (
    <main className="min-h-screen flex items-center justify-center bg-gray-50">
      <div className="max-w-md w-full space-y-6 p-8">
        <div className="text-center">
          <h1 className="text-3xl font-bold text-gray-900 mb-8">
            QuantForge
          </h1>
        </div>
        
        <div className="space-y-4">
          <textarea
            value={text}
            onChange={(e) => setText(e.target.value)}
            placeholder="Type your message here..."
            className="w-full p-4 border border-gray-300 rounded-lg shadow-sm focus:ring-2 focus:ring-blue-500 focus:border-blue-500 resize-none min-h-32 text-gray-900"
            rows={4}
          />
          
          <div className="text-center">
            <p className="text-sm text-gray-500">
              {text.length} characters
            </p>
          </div>
        </div>
      </div>
    </main>
  )
} 