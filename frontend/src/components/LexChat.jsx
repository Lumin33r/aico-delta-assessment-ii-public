import { CognitoIdentityClient, GetCredentialsForIdentityCommand, GetIdCommand } from '@aws-sdk/client-cognito-identity'
import { LexRuntimeV2Client, RecognizeTextCommand } from '@aws-sdk/client-lex-runtime-v2'
import { useEffect, useRef, useState } from 'react'
import { v4 as uuidv4 } from 'uuid'

/**
 * LexChat Component
 *
 * Provides a chat interface for interacting with the Amazon Lex bot.
 * Uses Cognito Identity Pool for unauthenticated access.
 */

// Runtime config (injected at build or runtime)
const config = window.__RUNTIME_CONFIG__ || {
  AWS_REGION: import.meta.env.VITE_AWS_REGION || 'us-east-1',
  COGNITO_IDENTITY_POOL_ID: import.meta.env.VITE_COGNITO_IDENTITY_POOL_ID || '',
  LEX_BOT_ID: import.meta.env.VITE_LEX_BOT_ID || '',
  LEX_BOT_ALIAS_ID: import.meta.env.VITE_LEX_BOT_ALIAS_ID || '',
}

function LexChat({ onSessionCreated, onLessonStart }) {
  const [messages, setMessages] = useState([
    {
      id: 'welcome',
      type: 'bot',
      text: "Hi! I'm your AI Tutor assistant. Share a URL with me and I'll create engaging podcast-style lessons for you. What would you like to learn about today?"
    }
  ])
  const [inputValue, setInputValue] = useState('')
  const [isLoading, setIsLoading] = useState(false)
  const [sessionId] = useState(() => uuidv4())
  const [lexClient, setLexClient] = useState(null)
  const [error, setError] = useState(null)
  const messagesEndRef = useRef(null)

  // Initialize Lex client with Cognito credentials
  useEffect(() => {
    async function initLexClient() {
      if (!config.COGNITO_IDENTITY_POOL_ID || !config.LEX_BOT_ID) {
        setError('Lex configuration not available. Using demo mode.')
        return
      }

      try {
        // Get Cognito identity
        const cognitoClient = new CognitoIdentityClient({ region: config.AWS_REGION })

        const getIdResponse = await cognitoClient.send(new GetIdCommand({
          IdentityPoolId: config.COGNITO_IDENTITY_POOL_ID
        }))

        // Get credentials
        const getCredsResponse = await cognitoClient.send(new GetCredentialsForIdentityCommand({
          IdentityId: getIdResponse.IdentityId
        }))

        const credentials = {
          accessKeyId: getCredsResponse.Credentials.AccessKeyId,
          secretAccessKey: getCredsResponse.Credentials.SecretKey,
          sessionToken: getCredsResponse.Credentials.SessionToken,
        }

        // Create Lex client
        const client = new LexRuntimeV2Client({
          region: config.AWS_REGION,
          credentials
        })

        setLexClient(client)
        setError(null)

      } catch (err) {
        console.error('Failed to initialize Lex client:', err)
        setError('Could not connect to Lex. Using demo mode.')
      }
    }

    initLexClient()
  }, [])

  // Auto-scroll to bottom
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages])

  // Send message to Lex
  const sendMessage = async (text) => {
    if (!text.trim()) return

    // Add user message
    const userMessage = {
      id: uuidv4(),
      type: 'user',
      text: text.trim()
    }
    setMessages(prev => [...prev, userMessage])
    setInputValue('')
    setIsLoading(true)

    try {
      let botResponse = ''

      if (lexClient && config.LEX_BOT_ID) {
        // Send to Lex
        const command = new RecognizeTextCommand({
          botId: config.LEX_BOT_ID,
          botAliasId: config.LEX_BOT_ALIAS_ID,
          localeId: 'en_US',
          sessionId: sessionId,
          text: text.trim()
        })

        const response = await lexClient.send(command)

        // Extract response messages
        const responseMessages = response.messages || []
        botResponse = responseMessages.map(m => m.content).join('\n\n')

        // Check for session creation
        const sessionAttrs = response.sessionState?.sessionAttributes || {}
        if (sessionAttrs.tutor_session_id) {
          onSessionCreated?.({
            sessionId: sessionAttrs.tutor_session_id,
            lessons: JSON.parse(sessionAttrs.lessons || '[]')
          })
        }

        // Check for lesson start
        if (sessionAttrs.audio_url) {
          onLessonStart?.({
            audioUrl: sessionAttrs.audio_url,
            lessonNumber: sessionAttrs.current_lesson
          })
        }

      } else {
        // Demo mode - simulate responses
        botResponse = await simulateResponse(text)
      }

      // Add bot response
      const botMessage = {
        id: uuidv4(),
        type: 'bot',
        text: botResponse || "I'm processing your request..."
      }
      setMessages(prev => [...prev, botMessage])

    } catch (err) {
      console.error('Failed to send message:', err)
      setMessages(prev => [...prev, {
        id: uuidv4(),
        type: 'bot',
        text: "I encountered an error. Please try again."
      }])
    } finally {
      setIsLoading(false)
    }
  }

  // Simulate response for demo mode
  const simulateResponse = async (text) => {
    await new Promise(resolve => setTimeout(resolve, 1000))

    const lowerText = text.toLowerCase()

    if (lowerText.includes('http') || lowerText.includes('www')) {
      return "Great! I've received your URL. In production, I would analyze this content and create personalized lessons. For now, check out the demo lessons below!"
    }

    if (lowerText.includes('start') || lowerText.includes('lesson')) {
      return "I'd love to start a lesson for you! In production with Lex configured, I would begin the podcast-style lesson with Alex and Sam."
    }

    if (lowerText.includes('help')) {
      return "Here's how I can help:\n\n1️⃣ Share a URL - Paste any webpage and I'll create lessons\n2️⃣ Start a lesson - Say 'start lesson 1' to begin\n3️⃣ Ask questions - I'm here to help!"
    }

    return "I understand! In production mode with Lex configured, I would process your request and help you learn. Try sharing a URL to get started!"
  }

  // Handle form submit
  const handleSubmit = (e) => {
    e.preventDefault()
    sendMessage(inputValue)
  }

  return (
    <div className="flex flex-col h-full">
      {/* Error banner */}
      {error && (
        <div className="bg-yellow-500/10 border border-yellow-500/30 rounded-lg p-3 mb-4 text-sm text-yellow-400">
          ⚠️ {error}
        </div>
      )}

      {/* Messages */}
      <div className="flex-1 overflow-y-auto space-y-4 mb-4 pr-2">
        {messages.map((message) => (
          <div
            key={message.id}
            className={`chat-message max-w-[85%] rounded-2xl px-4 py-3 ${
              message.type === 'user' ? 'user' : 'bot'
            }`}
          >
            <p className="whitespace-pre-wrap">{message.text}</p>
          </div>
        ))}

        {isLoading && (
          <div className="chat-message bot max-w-[85%] rounded-2xl px-4 py-3">
            <div className="flex items-center gap-2">
              <div className="w-2 h-2 bg-indigo-400 rounded-full animate-pulse-slow" />
              <div className="w-2 h-2 bg-indigo-400 rounded-full animate-pulse-slow delay-100" />
              <div className="w-2 h-2 bg-indigo-400 rounded-full animate-pulse-slow delay-200" />
            </div>
          </div>
        )}

        <div ref={messagesEndRef} />
      </div>

      {/* Input */}
      <form onSubmit={handleSubmit} className="flex gap-3">
        <input
          type="text"
          value={inputValue}
          onChange={(e) => setInputValue(e.target.value)}
          placeholder="Paste a URL or type a message..."
          className="input flex-1"
          disabled={isLoading}
        />
        <button
          type="submit"
          disabled={isLoading || !inputValue.trim()}
          className="btn btn-primary px-6 disabled:opacity-50 disabled:cursor-not-allowed"
        >
          Send
        </button>
      </form>
    </div>
  )
}

export default LexChat
